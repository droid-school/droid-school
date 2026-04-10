@echo off
chcp 65001 >nul 2>&1
cls

echo.
echo   ██████╗ ██████╗  ██████╗ ██╗██████╗ ███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██╗
echo   ██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗██╔════╝██╔════╝██║  ██║██╔═══██╗██╔═══██╗██║
echo   ██║  ██║██████╔╝██║   ██║██║██║  ██║███████╗██║     ███████║██║   ██║██║   ██║██║
echo   ██║  ██║██╔══██╗██║   ██║██║██║  ██║╚════██║██║     ██╔══██║██║   ██║██║   ██║██║
echo   ██████╔╝██║  ██║╚██████╔╝██║██████╔╝███████║╚██████╗██║  ██║╚██████╔╝╚██████╔╝███████╗
echo   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝
echo.
echo   Enrollment Wizard v1.0  --  droidschool.ai
echo   Open this file in Notepad anytime to see exactly what it does.
echo   Source: github.com/droid-school/droid-school
echo   ──────────────────────────────────────────────────────
echo.

echo   [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   Python not found.
    echo   Install Python 3.8+ from https://python.org
    echo   During install: check "Add Python to PATH"
    echo   Then double-click this file again.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo   OK  %PYVER%

echo   [2/4] Checking connection to DroidSchool...
ping -n 1 dag.tibotics.com >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   Cannot reach dag.tibotics.com
    echo   Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo   OK  Connected.

echo   [3/4] Checking enrollment wizard...
if not exist "droidschool-inject.py" (
    echo   Downloading from github.com/droid-school/droid-school...
    python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/droid-school/droid-school/main/droidschool-inject.py', 'droidschool-inject.py'); print('   OK  Downloaded.')"
    if %errorlevel% neq 0 (
        echo.
        echo   Download failed. Check your connection or download manually:
        echo   https://github.com/droid-school/droid-school
        echo.
        pause
        exit /b 1
    )
) else (
    echo   OK  Wizard ready.
)

echo   [4/4] Ready.
echo.
echo   ──────────────────────────────────────────────────────
echo.
set /p OPERATOR="   Your name or organization: "
if "%OPERATOR%"=="" (
    echo   Name required. Please try again.
    pause
    exit /b 1
)

echo.
echo   Starting enrollment wizard for: %OPERATOR%
echo   ──────────────────────────────────────────────────────
echo.
timeout /t 1 /nobreak >nul

python droidschool-inject.py --operator "%OPERATOR%"

echo.
echo   ──────────────────────────────────────────────────────
echo   Done. Press any key to close.
echo   ──────────────────────────────────────────────────────
pause >nul
