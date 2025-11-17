# Butha-Buthe Digital Library
# Quick Setup Script for Windows

@echo off
echo ====================================
echo Butha-Buthe Digital Library Setup
echo ====================================
echo.

echo Step 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
) else (
    echo Python is installed
)

echo.
echo Step 2: Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

echo.
echo Step 3: Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Step 4: Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Step 5: Setting up configuration...
if not exist ".env" (
    copy ".env.example" ".env"
    echo Configuration file created from template
    echo Please edit .env file with your database settings
) else (
    echo Configuration file already exists
)

echo.
echo Step 6: Creating directories...
if not exist "uploads" mkdir uploads
if not exist "uploads\books" mkdir uploads\books
if not exist "uploads\covers" mkdir uploads\covers
if not exist "logs" mkdir logs

echo.
echo ====================================
echo Setup completed!
echo ====================================
echo.
echo Next steps:
echo 1. Install and configure MySQL database
echo 2. Edit .env file with your database settings
echo 3. Run: flask init-db
echo 4. Run: flask create-admin
echo 5. Run: python run.py
echo.
echo For detailed instructions, see README.md
echo.
pause