@echo off
REM Build script for Kindle PDF Converter

echo ========================================
echo  Kindle PDF Converter - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo Error: Failed to install PyInstaller
    pause
    exit /b 1
)

REM Clean previous build
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build exe
echo.
echo Building executable...
python -m PyInstaller --clean kindle_pdf_converter.spec
if %errorlevel% neq 0 (
    echo Error: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\KindlePDFConverter.exe
echo.
pause
