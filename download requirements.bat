@echo off
title Python Game Setup
echo Checking for Python installation...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Downloading Python...
    curl -o python_installer.exe https://www.python.org/ftp/python/3.12.1/python-3.12.1-amd64.exe
    echo Installing Python...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    echo Python installed successfully!
) else (
    echo Python is already installed.
)

:: Ensure pip is installed and up-to-date
echo Checking pip...
python -m ensurepip
python -m pip install --upgrade pip

:: Install requirements
echo Installing required dependencies...
python -m pip install -r requirements.txt

echo Installation complete! You can now run the game.
pause

