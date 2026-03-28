@echo off
REM CertGuard SSL/TLS Scanner - Auto Start Script
REM This script starts the backend server and opens the frontend

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"

echo ========================================
echo  CertGuard SSL/TLS Security Scanner
echo  Starting Application...
echo ========================================
echo.

REM Change to backend directory
cd /d "%BACKEND_DIR%"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Install/verify dependencies
echo Checking dependencies...
set "REQ_FILE=%ROOT_DIR%requirements.txt"
if not exist "%REQ_FILE%" (
    set "REQ_FILE=%BACKEND_DIR%\requirements.txt"
)

if not exist "%REQ_FILE%" (
    echo ERROR: Requirements file not found in:
    echo   1. "%ROOT_DIR%requirements.txt"
    echo   2. "%BACKEND_DIR%\requirements.txt"
    pause
    exit /b 1
)

python -m pip install -r "%REQ_FILE%" --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Starting Flask backend server...
echo.

REM Start the backend server
start "CertGuard Backend Server" python app.py

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Open frontend in default browser
echo.
echo Opening CertGuard frontend...
start "" "%ROOT_DIR%index.html"

echo.
echo ========================================
echo  CertGuard is now running!
echo.
echo  Backend: http://localhost:5000
echo  Frontend: Opening in your browser
echo.
echo  To stop the server:
echo  1. Close the backend console window
echo  2. Or press CTRL+C in the terminal
echo ========================================
echo.
pause
