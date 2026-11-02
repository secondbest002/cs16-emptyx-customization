"""
tools/cs16_mod_hub/core/cfg_utils.py
Atomic, non-destructive parser and writer for GoldSrc / AMX Mod X / YaPB .cfg configuration files.
Preserves line order, CRLF/LF line endings, comments, indentation, and quotation style.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional

RE_CVAR_LINE = re.compile(
    r"^(?P<indent>\s*)(?P<cvar>[a-zA-Z0-9_]+)\s+"
    r"(?:(?P<quote>[\"'])|(?P<noquote>))"
    r"(?P<val>(?(quote)[^\"'\r\n]*|(?:[^\s;/]|/(?!/))*))"
    r"(?(quote)(?P=quote)|)"
    r"(?P<rest>.*?)(?P<eol>\r?\n)?$"
)


def detect_line_ending(text: str) -> str:
    """Detects whether text uses Windows CRLF or Unix LF."""
    return "\r\n" if "\r\n" in text else "\n"


def atomic_write_file(target_path: Path, content: str, make_backup: bool = True) -> None:
    """
    Atomically writes content to target_path using tempfile and os.replace.
    Preserves existing permissions and prevents file corruption on power loss.
    """
    target_path = Path(target_path).resolve()
    target_dir = target_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Optional initial safety backup
    if make_backup and target_path.is_file():
        bak_path = target_path.with_suffix(target_path.suffix + ".bak")
        if not bak_path.exists():
            try:
                shutil.copy2(target_path, bak_path)
            except OSError:
                pass

    # Write to temporary file in the exact same directory (same drive/filesystem)
    temp_file = tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8", newline="")
    temp_path = Path(temp_file.name)
    try:
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()

        # Retry loop to gracefully handle transient Windows file locks
        for attempt in range(4):
            try:
                os.replace(temp_path, target_path)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(0.05)
    except Exception:
        temp_file.close()
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def parse_cfg_cvars(cfg_path: Path, target_keys: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Parses key-value CVAR pairs from a .cfg file.
    If target_keys is provided, only extracts those CVARs (case-insensitive).
    """
    cfg_path = Path(cfg_path)
    if not cfg_path.is_file():
        return {}

    filter_keys = {k.strip().lower() for k in target_keys} if target_keys else None
    results: Dict[str, str] = {}

    text = cfg_path.read_bytes().decode("utf-8", errors="replace")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith(";"):
            continue

        m = RE_CVAR_LINE.match(line)
        if m:
            cvar = m.group("cvar")
            cvar_lower = cvar.lower()
            if filter_keys is None or cvar_lower in filter_keys:
                results[cvar_lower] = m.group("val")

    return results


def get_cfg_cvar(cfg_path: Path, cvar_name: str) -> Optional[str]:
    """Reads a single CVAR value from a .cfg file."""
    cfg_path = Path(cfg_path)
    if not cfg_path.is_file():
        return None

    cvar_key = cvar_name.strip().lower()
    text = cfg_path.read_bytes().decode("utf-8", errors="replace")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith(";"):
            continue
        m = RE_CVAR_LINE.match(line)
        if m and m.group("cvar").lower() == cvar_key:
            return m.group("val")
    return None


def set_cfg_cvar(cfg_path: Path, cvar_name: str, value: Any, append_if_missing: bool = True) -> bool:
    """Updates a single CVAR value in a .cfg file atomically."""
    return set_cfg_cvars(cfg_path, {cvar_name: value}, append_if_missing=append_if_missing)


def set_cfg_cvars(cfg_path: Path, settings: Dict[str, Any], append_if_missing: bool = True) -> bool:
    """
    Batch updates multiple CVARs in a .cfg file in one atomic pass.
    Preserves whitespace, indentation, comments, quotes, and original line endings.
    """
    cfg_path = Path(cfg_path)
    if not cfg_path.is_file():
        if not append_if_missing:
            return False
        # Create empty file with default CRLF on Windows
        text = ""
        eol = "\r\n"
    else:
        text = cfg_path.read_bytes().decode("utf-8", errors="replace")
        eol = detect_line_ending(text)

    lines = text.splitlines(keepends=True)
    pending = {k.strip().lower(): (k.strip(), str(v).strip()) for k, v in settings.items()}
    found_cvars = set()
    changed = False
    new_lines: List[str] = []

    for line in lines:
        s = line.strip()
        if not s or s.startswith("//") or s.startswith(";"):
            new_lines.append(line)
            continue

        m = RE_CVAR_LINE.match(line)
        if m:
            cvar_lower = m.group("cvar").lower()
            if cvar_lower in pending:
                orig_key, str_val = pending[cvar_lower]
                found_cvars.add(cvar_lower)
                matched_quote = m.group("quote") or ""

                raw_val = str_val
                if (raw_val.startswith('"') and raw_val.endswith('"') and len(raw_val) >= 2) or (
                    raw_val.startswith("'") and raw_val.endswith("'") and len(raw_val) >= 2
                ):
                    raw_val = raw_val[1:-1]
                    quote = matched_quote or '"'
                elif " " in raw_val or raw_val == "":
                    quote = matched_quote or '"'
                else:
                    quote = matched_quote

                line_eol = m.group("eol") or eol
                new_line = f"{m.group('indent')}{m.group('cvar')} {quote}{raw_val}{quote}{m.group('rest')}{line_eol}"
                if new_line != line:
                    new_lines.append(new_line)
                    changed = True
                else:
                    new_lines.append(line)
                continue

        new_lines.append(line)

    if append_if_missing:
        # Check if file predominantly uses quotes
        quoted_count = sum(1 for line in lines if RE_CVAR_LINE.match(line) and RE_CVAR_LINE.match(line).group("quote"))
        total_cvars = sum(1 for line in lines if RE_CVAR_LINE.match(line))
        predominantly_quoted = (quoted_count >= total_cvars / 2) if total_cvars > 0 else True

        # Ensure existing content ends with newline before appending
        if new_lines and not new_lines[-1].endswith(("\n", "\r")):
            new_lines[-1] += eol

        for cvar_lower, (orig_key, str_val) in pending.items():
            if cvar_lower not in found_cvars:
                raw_val = str_val
                has_outer_quotes = (
                    (raw_val.startswith('"') and raw_val.endswith('"') and len(raw_val) >= 2)
                    or (raw_val.startswith("'") and raw_val.endswith("'") and len(raw_val) >= 2)
                )
                if has_outer_quotes:
                    raw_val = raw_val[1:-1]
                    quote = '"'
                elif " " in raw_val or raw_val == "" or predominantly_quoted:
                    quote = '"'
                else:
                    quote = ""

                new_lines.append(f"{orig_key} {quote}{raw_val}{quote}{eol}")
                changed = True

    if changed or not cfg_path.is_file():
        atomic_write_file(cfg_path, "".join(new_lines))
        return True
    return True
