"""
tools/cs16_mod_hub/build_exe.py
Compiles the Modern Web Desktop CS 1.6 Mod Hub into a standalone CS16_Mod_Manager.exe.
"""

import os
from pathlib import Path
import subprocess
import sys

def build():
    root = Path(__file__).resolve().parent.parent.parent
    web_dir = root / "tools" / "cs16_mod_hub" / "web"
    main_script = root / "tools" / "cs16_mod_hub" / "main_webview.py"
    output_name = "CS16_Mod_Manager"

    print("==================================================================")
    print("Building CS16_Mod_Manager.exe (Standalone Modern Webview App)")
    print("==================================================================")
    print(f"Project root: {root}")
    print(f"Web assets: {web_dir}")

    import webview
    webview_lib = Path(webview.__file__).resolve().parent / "lib"
    runtimes_dir = webview_lib / "runtimes"

    extra_data = [
        f"{web_dir};web",
        f"{root / '.agents'};.agents",
    ]
    if runtimes_dir.is_dir():
        extra_data.append(f"{runtimes_dir};runtimes")
        extra_data.append(f"{runtimes_dir};webview/lib/runtimes")
    if (runtimes_dir / "win-arm64").is_dir():
        extra_data.append(f"{runtimes_dir / 'win-arm64'};win-arm64")
    if (runtimes_dir / "win-x64").is_dir():
        extra_data.append(f"{runtimes_dir / 'win-x64'};win-x64")
    if (runtimes_dir / "win-x86").is_dir():
        extra_data.append(f"{runtimes_dir / 'win-x86'};win-x86")
    for dll in webview_lib.glob("*.dll"):
        extra_data.append(f"{dll};.")
        extra_data.append(f"{dll};webview/lib")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", output_name,
        "--distpath", str(root),
        "--workpath", str(root / "tools" / "cs16_mod_hub" / "build"),
        "--specpath", str(root / "tools" / "cs16_mod_hub"),
        "--collect-all", "webview",
        "--hidden-import", "PIL",
        "--hidden-import", "numpy",
        "--hidden-import", "runpy",
        "--hidden-import", "colorsys",
        "--hidden-import", "dataclasses",
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "webview.platforms.edgechromium",
        "--clean",
        "-y",
    ]

    for d in extra_data:
        cmd.extend(["--add-data", d])

    cmd.append(str(main_script))

    print("Running PyInstaller...")
    res = subprocess.run(cmd, cwd=str(root))
    if res.returncode == 0:
        exe_path = root / f"{output_name}.exe"
        if exe_path.is_file():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\nBUILD SUCCESSFUL!")
            print(f"Generated standalone executable: {exe_path} ({size_mb:.2f} MB)")
            return 0
    print("\nBUILD FAILED with returncode:", res.returncode)
    return res.returncode

if __name__ == "__main__":
    sys.exit(build())
