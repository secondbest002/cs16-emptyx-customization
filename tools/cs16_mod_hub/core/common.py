"""
tools/cs16_mod_hub/core/common.py
Core execution utilities, project root resolution, and subprocess streaming runner.
"""

from dataclasses import dataclass
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import threading
from typing import Any, Callable, List, Optional, Union

# Process-level serialization lock for in-process script execution
_IN_PROCESS_LOCK = threading.RLock()


@dataclass
class AdapterResult:
    """Standardized execution result returned by all Mod Hub adapters."""

    success: bool
    message: str
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0

    def __bool__(self) -> bool:
        """Allow direct boolean evaluation: if result: ..."""
        return self.success

    @property
    def output(self) -> str:
        """Return primary output text (stdout if populated, else stderr)."""
        return self.stdout if self.stdout.strip() else self.stderr


def get_project_root() -> Path:
    """
    Resolves the Counter-Strike 1.6 game root directory.
    Hierarchy:
      tools/cs16_mod_hub/core/common.py -> parents[3] == Project Root
    Supports CS16_PROJECT_ROOT environment override and upward directory search.
    """
    if getattr(sys, "frozen", False):
        exe_parent = Path(sys.executable).resolve().parent
        if (exe_parent / "cstrike").is_dir():
            return exe_parent
        return exe_parent

    env_override = os.environ.get("CS16_PROJECT_ROOT")
    if env_override:
        p = Path(env_override).resolve()
        if p.is_dir():
            return p

    # Check config.json in customization workspace
    try:
        cfg_file = Path(__file__).resolve().parents[2] / "config.json"
        if cfg_file.is_file():
            import json
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            p = Path(cfg.get("game_directory", ""))
            if (p / "cstrike").is_dir():
                return p
    except Exception:
        pass

    # Check sibling folder
    try:
        sibling = Path(__file__).resolve().parents[3] / "Counter-Strike 1.6 Original"
        if (sibling / "cstrike").is_dir():
            return sibling
    except Exception:
        pass

    # Standard relative location from tools/cs16_mod_hub/core/common.py
    try:
        candidate = Path(__file__).resolve().parents[3]
        if (candidate / "cstrike").is_dir():
            return candidate
    except IndexError:
        pass

    # Fallback: search upward for 'cstrike' marker directory
    curr = Path(__file__).resolve().parent
    for parent in [curr] + list(curr.parents):
        if (parent / "cstrike").is_dir():
            return parent

    return Path.cwd().resolve()


class _StreamWriter(io.TextIOBase):
    """Captures stream output line-by-line, streaming to log_callback and accumulating lines."""

    def __init__(
        self,
        callback: Optional[Callable[[str], None]],
        accumulator: List[str],
        passthrough: Optional[Any] = None,
    ):
        self.callback = callback
        self.accumulator = accumulator
        self.passthrough = passthrough
        self._buf = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buf += str(s)
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line_clean = line.rstrip("\r")
            self.accumulator.append(line_clean + "\n")
            if self.passthrough:
                try:
                    self.passthrough.write(line_clean + "\n")
                    self.passthrough.flush()
                except Exception:
                    pass
            if self.callback:
                try:
                    self.callback(line_clean)
                except Exception:
                    pass
        return len(s)

    def flush(self) -> None:
        if self._buf:
            line_clean = self._buf.rstrip("\r\n")
            self.accumulator.append(line_clean + "\n")
            if self.passthrough:
                try:
                    self.passthrough.write(line_clean + "\n")
                    self.passthrough.flush()
                except Exception:
                    pass
            if self.callback:
                try:
                    self.callback(line_clean)
                except Exception:
                    pass
            self._buf = ""


def _run_script_in_process(
    script_path: Optional[Path],
    args: List[str],
    is_inline_c: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
    cwd: Optional[Union[str, Path]] = None,
) -> AdapterResult:
    """
    Executes a script or inline code directly within the current Python process.
    This guarantees execution inside PyInstaller standalone bundles without spawning
    new executable processes or depending on external Python installations.
    """
    saved_argv = list(sys.argv)
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    saved_cwd = os.getcwd()

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    out_writer = _StreamWriter(log_callback, stdout_lines, passthrough=saved_stdout)
    err_writer = _StreamWriter(log_callback, stderr_lines, passthrough=saved_stderr)

    work_dir = Path(cwd).resolve() if cwd else get_project_root()
    returncode = 0
    err_msg = ""

    with _IN_PROCESS_LOCK:
        try:
            os.chdir(str(work_dir))
            sys.stdout = out_writer
            sys.stderr = err_writer

            if is_inline_c:
                code_str = args[0] if args else ""
                sys.argv = ["-c"] + [str(a) for a in args[1:]]
                exec(code_str, {"__name__": "__main__"})
            else:
                sys.argv = [str(script_path)] + [str(a) for a in args]
                runpy.run_path(str(script_path.resolve()), run_name="__main__")
            returncode = 0
        except SystemExit as se:
            if isinstance(se.code, int):
                returncode = se.code
            elif se.code is None:
                returncode = 0
            else:
                returncode = 1
                err_writer.write(str(se.code) + "\n")
        except Exception as exc:
            import traceback
            returncode = -1
            err_msg = str(exc)
            tb = traceback.format_exc()
            err_writer.write(tb)
        finally:
            out_writer.flush()
            err_writer.flush()
            sys.argv = saved_argv
            sys.stdout = saved_stdout
            sys.stderr = saved_stderr
            try:
                os.chdir(saved_cwd)
            except Exception:
                pass

    full_stdout = "".join(stdout_lines)
    full_stderr = "".join(stderr_lines)
    success = (returncode == 0)

    if success:
        out_stripped = [l.strip() for l in stdout_lines if l.strip()]
        message = out_stripped[-1] if out_stripped else "Operation completed successfully."
    else:
        err_stripped = [l.strip() for l in stderr_lines if l.strip()]
        out_stripped = [l.strip() for l in stdout_lines if l.strip()]
        if err_stripped:
            message = err_stripped[-1]
        elif out_stripped:
            message = out_stripped[-1]
        elif err_msg:
            message = err_msg
        else:
            message = f"Process exited with error code {returncode}."

    return AdapterResult(
        success=success,
        message=message,
        stdout=full_stdout,
        stderr=full_stderr,
        returncode=returncode,
    )


def run_script_streaming(
    script_rel_path: Union[str, Path],
    args: List[str],
    log_callback: Optional[Callable[[str], None]] = None,
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[float] = 60.0,
) -> AdapterResult:
    """
    Executes a script safely, streaming lines to log_callback in real time.
    In frozen PyInstaller mode (sys.frozen is True), executes in-process to prevent
    spawning additional GUI window instances and avoid missing Python dependencies.
    """
    root = get_project_root()
    work_dir = Path(cwd).resolve() if cwd else root

    is_inline_c = str(script_rel_path) == "-c"
    script_path: Optional[Path] = None

    if not is_inline_c:
        cand = Path(script_rel_path)
        meipass = getattr(sys, "_MEIPASS", None)
        if cand.is_absolute() and cand.is_file():
            script_path = cand
        elif (root / script_rel_path).is_file():
            script_path = (root / script_rel_path).resolve()
        elif meipass and (Path(meipass) / script_rel_path).is_file():
            script_path = (Path(meipass) / script_rel_path).resolve()
        elif cand.is_file():
            script_path = cand.resolve()
        else:
            err_msg = f"Target script not found: {script_rel_path}"
            if log_callback:
                log_callback(f"[ERROR] {err_msg}")
            return AdapterResult(
                success=False,
                message=err_msg,
                stdout="",
                stderr=err_msg,
                returncode=-1,
            )

    # In frozen mode, ALWAYS execute in-process to avoid re-invoking CS16_Mod_Manager.exe GUI!
    if getattr(sys, "frozen", False) or not is_inline_c:
        return _run_script_in_process(
            script_path=script_path,
            args=args,
            is_inline_c=is_inline_c,
            log_callback=log_callback,
            cwd=work_dir,
        )

    # Windows GUI no-window flag
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    # Ensure unbuffered execution and UTF-8 encoding
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [sys.executable, "-u", "-c"] + [str(a) for a in args]

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )

        def _drain_stream(stream, accumulator: List[str]):
            try:
                for line in iter(stream.readline, ""):
                    accumulator.append(line)
                    if log_callback:
                        log_callback(line.rstrip("\r\n"))
            finally:
                stream.close()

        t_out = threading.Thread(target=_drain_stream, args=(proc.stdout, stdout_lines), daemon=True)
        t_err = threading.Thread(target=_drain_stream, args=(proc.stderr, stderr_lines), daemon=True)
        t_out.start()
        t_err.start()

        proc.wait(timeout=timeout)
        t_out.join(timeout=2.0)
        t_err.join(timeout=2.0)

        full_stdout = "".join(stdout_lines)
        full_stderr = "".join(stderr_lines)
        success = (proc.returncode == 0)

        if success:
            out_stripped = [l.strip() for l in stdout_lines if l.strip()]
            message = out_stripped[-1] if out_stripped else "Operation completed successfully."
        else:
            err_stripped = [l.strip() for l in stderr_lines if l.strip()]
            out_stripped = [l.strip() for l in stdout_lines if l.strip()]
            if err_stripped:
                message = err_stripped[-1]
            elif out_stripped:
                message = out_stripped[-1]
            else:
                message = f"Process exited with error code {proc.returncode}."

        return AdapterResult(
            success=success,
            message=message,
            stdout=full_stdout,
            stderr=full_stderr,
            returncode=proc.returncode,
        )

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        for s in (proc.stdout, proc.stderr):
            if s and not s.closed:
                try:
                    s.close()
                except Exception:
                    pass
        t_out.join(timeout=1.0)
        t_err.join(timeout=1.0)
        msg = f"Process execution timed out after {timeout} seconds."
        if log_callback:
            log_callback(f"[ERROR] {msg}")
        return AdapterResult(
            success=False,
            message=msg,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
            returncode=-1,
        )
    except Exception as exc:
        msg = f"Subprocess launch exception: {exc}"
        if log_callback:
            log_callback(f"[ERROR] {msg}")
        return AdapterResult(
            success=False,
            message=msg,
            stdout="".join(stdout_lines),
            stderr=str(exc),
            returncode=-1,
        )
