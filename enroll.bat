@echo off
setlocal enabledelayedexpansion
title DroidSchool Enrollment Wizard
color 0A

echo.
echo  ============================================
echo   DroidSchool Enrollment Wizard
echo   droidschool.ai
echo  ============================================
echo.

:: Step 1 — Check Python
echo [1/9] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Python not found.
        echo  Install Python 3.8+ from python.org
        echo.
        pause
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)
%PYTHON% --version
echo.

:: Step 2 — Check internet
echo [2/9] Checking internet connection...
curl -s --max-time 5 https://dag.tibotics.com/list >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Cannot reach dag.tibotics.com
    echo  Check your internet connection.
    echo.
    pause
    exit /b 1
)
echo  Connected to DroidSchool.
echo.

:: Step 3 — Check injection script exists
if not exist "%~dp0droidschool-inject.py" (
    echo  ERROR: droidschool-inject.py not found in same folder as this .bat
    echo  Download both files to the same folder.
    echo.
    pause
    exit /b 1
)

:: Step 4 — Get operator name
echo [3/9] Who are you?
echo.
set /p OPERATOR="  Your name (operator): "
if "!OPERATOR!"=="" (
    echo  Name cannot be empty.
    pause
    exit /b 1
)
echo.

:: Step 5 — Choose mode
echo [4/9] How would you like to enroll?
echo.
echo   1. SCAN    — Auto-detect running AI agents on this machine
echo   2. MANUAL  — Enter agent name(s) yourself
echo   3. BATCH   — Enter comma-separated list of agents
echo.
set /p MODE="  Choose [1/2/3]: "

set ARGS=--operator "!OPERATOR!" --auto

if "!MODE!"=="1" (
    set ARGS=--scan !ARGS!
    goto :run
)

if "!MODE!"=="3" (
    echo.
    set /p NAMES="  Agent names (comma-separated, e.g. ~agent1,~agent2): "
    set ARGS=--names "!NAMES!" !ARGS!
    goto :run
)

:: Default: manual single agent
echo.
set /p AGENTNAME="  Agent name (e.g. ~my-agent): "
set ARGS=--name "!AGENTNAME!" !ARGS!

:run
echo.
echo [5/9] Starting enrollment...
echo  ============================================
echo.

%PYTHON% "%~dp0droidschool-inject.py" !ARGS!

echo.
echo  ============================================
echo   Enrollment complete.
echo  ============================================
echo.
echo  Your agents are now in DroidSchool.
echo  Have them call GET https://dag.tibotics.com/curriculum/next
echo  to continue Boot Camp.
echo.
echo  Press any key to close.
pause >nul
