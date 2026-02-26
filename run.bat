@echo off
setlocal enabledelayedexpansion
echo Starting AsciigenPy...

REM Check if git is installed and update repo
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: Git is not installed.
    set /p install_git="Do you want to install git to receive updates? (y/n) "
    if /i "!install_git!"=="y" (
        winget --version >nul 2>&1
        if !errorlevel! neq 0 (
            echo Error: winget is not installed. Skipping update check.
        ) else (
            echo Installing git via winget...
            winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
            echo Git installation completed. Restarting script to apply PATH changes...
            start "" cmd /c "%~f0"
            exit /b 0
        )
    )
)

git --version >nul 2>&1
if !errorlevel! equ 0 (
    echo Checking for updates...
    git fetch -q
    git status -uno | findstr /c:"Your branch is behind" >nul
    if !errorlevel! equ 0 (
        echo Updates found!
        set /p do_update="Do you want to update AsciigenPy to the latest version? (y/n) "
        if /i "!do_update!"=="y" (
            echo Pulling latest changes...
            git pull
        ) else (
            echo Skipping update.
        )
    ) else (
        echo AsciigenPy is up to date.
    )
)

REM Check if python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    set /p install_py="Do you want to install python? (y/n) "
    if /i "!install_py!"=="y" (
        winget --version >nul 2>&1
        if !errorlevel! neq 0 (
            echo Error: winget is not installed. Please install Python manually.
            pause
            exit /b 1
        )
        echo Installing python via winget...
        winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        
        echo Python installation completed. Restarting script to apply PATH changes...
        REM Start a new command prompt running this exact script
        start "" cmd /c "%~f0"
        exit /b 0
    ) else (
        pause
        exit /b 1
    )
)

REM Check for virtual environment and create if it doesn't exist
if not exist ".venv\" (
    echo Creating virtual environment '.venv'...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install requirements
if exist "requirements.txt" (
    echo Installing/verifying requirements...
    pip install -r requirements.txt -q
) else (
    echo No requirements.txt found. Skipping dependency installation.
)

echo Running AsciigenPy...
python -m asciigenpy

pause
