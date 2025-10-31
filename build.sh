#!/bin/bash
# Build script for Kindle PDF Converter

echo "========================================"
echo " Kindle PDF Converter - Build Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Install PyInstaller
echo "Installing PyInstaller..."
pip install pyinstaller
if [ $? -ne 0 ]; then
    echo "Error: Failed to install PyInstaller"
    exit 1
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf build dist

# Build executable
echo ""
echo "Building executable..."
python3 -m PyInstaller --clean kindle_pdf_converter.spec
if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "========================================"
echo " Build completed successfully!"
echo "========================================"
echo ""
echo "Executable location: dist/KindlePDFConverter"
echo ""
