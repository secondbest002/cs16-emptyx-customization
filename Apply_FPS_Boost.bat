@echo off
setlocal enabledelayedexpansion
title CS 1.6 Potato FPS Boost Optimizer Suite

:MENU
cls
echo ======================================================================
echo           CS 1.6 POTATO FPS BOOST OPTIMIZER SUITE
echo          Designed for Laptops, Integrated GPUs, and YaPB Bots
echo ======================================================================
echo.

python scripts\cs16_studio\fps_booster.py --status

echo.
echo [1] Apply ESPORTS BALANCED Boost (Recommended: 100 FPS, Keeps Skins)
echo [2] Apply POTATO MAX PERFORMANCE (Extreme: 100 FPS, Minmodels, 0 Decals)
echo [3] RESTORE STOCK Settings (Original Default CS 1.6 Visuals)
echo [4] Check Status & Diagnostics
echo [5] Exit
echo.
set /p choice="Select an option [1-5]: "

if "%choice%"=="1" (
    cls
    python scripts\cs16_studio\fps_booster.py --apply balanced
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto MENU
)

if "%choice%"=="2" (
    cls
    python scripts\cs16_studio\fps_booster.py --apply extreme
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto MENU
)

if "%choice%"=="3" (
    cls
    python scripts\cs16_studio\fps_booster.py --apply stock
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto MENU
)

if "%choice%"=="4" (
    goto MENU
)

if "%choice%"=="5" (
    exit /b 0
)

goto MENU
