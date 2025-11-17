#!/bin/bash

# Butha-Buthe Digital Library
# Quick Setup Script for Linux/macOS

echo "===================================="
echo "Butha-Buthe Digital Library Setup"
echo "===================================="
echo

echo "Step 1: Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
else
    echo "Python 3 is installed"
fi

echo
echo "Step 2: Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

echo
echo "Step 3: Activating virtual environment..."
source venv/bin/activate

echo
echo "Step 4: Installing Python dependencies..."
pip install -r requirements.txt

echo
echo "Step 5: Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Configuration file created from template"
    echo "Please edit .env file with your database settings"
else
    echo "Configuration file already exists"
fi

echo
echo "Step 6: Creating directories..."
mkdir -p uploads/books uploads/covers logs

echo
echo "===================================="
echo "Setup completed!"
echo "===================================="
echo
echo "Next steps:"
echo "1. Install and configure MySQL database"
echo "2. Edit .env file with your database settings"
echo "3. Run: flask init-db"
echo "4. Run: flask create-admin"
echo "5. Run: python run.py"
echo
echo "For detailed instructions, see README.md"
echo