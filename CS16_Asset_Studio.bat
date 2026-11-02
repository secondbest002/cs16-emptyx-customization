@echo off
setlocal enabledelayedexpansion
title CS 1.6 Asset Studio - EmptyX Customization Suite

:: Check for Desktop shortcut request
if /i "%~1"=="--shortcut" goto :create_shortcut_standalone
if /i "%~1"=="/shortcut" goto :create_shortcut_standalone
if /i "%~1"=="-s" goto :create_shortcut_standalone

:: Change directory to script folder (workspace root)
cd /d "%~dp0"

echo =======================================================================
echo     CS 1.6 EMPTYX CUSTOMIZATION - ASSET STUDIO ^& MOD SUITE
echo =======================================================================
echo.

:: Detect Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found on your system!
        echo Please install Python 3.9+ from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    ) else (
        set PY_CMD=py -3
    )
) else (
    set PY_CMD=python
)

echo [1/3] Verifying Python environment...
%PY_CMD% --version
if %errorlevel% neq 0 (
    echo [ERROR] Failed to run Python.
    pause
    exit /b 1
)

:: Check if desktop shortcut exists; offer prompt if missing
set "DESKTOP_LNK=%USERPROFILE%\Desktop\CS 1.6 Asset Studio.lnk"
if not exist "!DESKTOP_LNK!" (
    echo [2/3] Checking Windows desktop integration...
    echo Tip: You can create a 1-click Desktop shortcut now.
    choice /c YN /t 3 /d N /m "Create a Desktop shortcut now? [Y/N] (continues in 3s)"
    if !errorlevel! equ 1 (
        call :do_create_shortcut
    )
) else (
    echo [2/3] Windows Desktop shortcut verified: !DESKTOP_LNK!
)

:: Sync web static assets if not yet present
%PY_CMD% -c "from scripts.cs16_studio.web.server import ensure_static_assets; ensure_static_assets()" 2>nul

echo.
echo [3/3] Launching CS 1.6 Asset Studio Web Dashboard...
echo Dashboard URL: http://127.0.0.1:5160/
echo (Opening directly in your default browser...)
echo.
echo Tip: Run "CS16_Asset_Studio.bat --shortcut" anytime to recreate the Desktop shortcut.
echo Press Ctrl+C in this console window to stop the server when done.
echo =======================================================================
echo.

:: Run studio web UI
%PY_CMD% scripts\cs16_studio.py --ui --port 5160
goto :eof

:create_shortcut_standalone
cd /d "%~dp0"
call :do_create_shortcut
echo.
pause
goto :eof

:do_create_shortcut
echo Creating Desktop shortcut for CS 1.6 Asset Studio (EmptyX Customization)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = [System.Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut([System.IO.Path]::Combine($desktop, 'CS 1.6 Asset Studio.lnk')); $s.TargetPath = '%~dp0CS16_Asset_Studio.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'CS 1.6 Asset Studio - EmptyX Customization Suite'; $s.Save(); Write-Host '[Success] Shortcut updated on Desktop: ' $s.FullName -ForegroundColor Green"
goto :eof
