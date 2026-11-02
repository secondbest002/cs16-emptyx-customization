@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Counter-Strike 1.6 Mod Hub - Modern Unified Web Launcher
:: High-Performance Local Dashboard (Port 5170)
:: ============================================================================

title Counter-Strike 1.6 Mod Hub - Web Dashboard

:: Check for Desktop shortcut request
if /i "%~1"=="--shortcut" goto :create_shortcut_standalone
if /i "%~1"=="/shortcut" goto :create_shortcut_standalone
if /i "%~1"=="-s" goto :create_shortcut_standalone

:: Anchor working directory to game root
cd /d "%~dp0"

echo =======================================================================
echo          COUNTER-STRIKE 1.6 MOD HUB - MODERN WEB DASHBOARD
echo =======================================================================
echo.

:: Detect Python installation
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
set "DESKTOP_LNK=%USERPROFILE%\Desktop\CS 1.6 Mod Hub.lnk"
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

echo.
echo [3/3] Launching CS 1.6 Mod Hub Web Dashboard...
echo Dashboard URL: http://127.0.0.1:5170/
echo (Opening in system default web browser...)
echo.
echo Tip: Run "CS16_Mod_Manager.bat --shortcut" anytime to recreate the Desktop shortcut.
echo Press Ctrl+C in this console window to stop the server when done.
echo =======================================================================
echo.

:: Launch Mod Hub Web Server
%PY_CMD% tools\cs16_mod_hub\server.py --port 5170 %*
goto :eof

:create_shortcut_standalone
cd /d "%~dp0"
call :do_create_shortcut
echo.
pause
goto :eof

:do_create_shortcut
echo Creating Desktop shortcut for CS 1.6 Mod Hub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = [System.Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut([System.IO.Path]::Combine($desktop, 'CS 1.6 Mod Hub.lnk')); $s.TargetPath = '%~dp0CS16_Mod_Manager.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Counter-Strike 1.6 Mod Hub - Modern Web Dashboard'; $s.Save(); Write-Host '[Success] Shortcut created on Desktop: ' $s.FullName -ForegroundColor Green"
goto :eof
