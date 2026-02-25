#!/usr/bin/env bash

# Exit on error
set -e

echo "Starting AsciigenPy..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH."
    read -p "Do you want to install python? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v apt &> /dev/null; then
            echo "Installing python via apt..."
            sudo apt update && sudo apt install -y python3 python3-venv python3-pip
        elif command -v dnf &> /dev/null; then
            echo "Installing python via dnf..."
            sudo dnf install -y python3 python3-pip
        elif command -v pacman &> /dev/null; then
            echo "Installing python via pacman..."
            sudo pacman -S --noconfirm python python-pip
        else
            echo "Error: Unsupported package manager. Please install Python manually."
            exit 1
        fi
    else
        exit 1
    fi
fi

# Check for virtual environment and create if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment '.venv'..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing/verifying requirements..."
    pip install -r requirements.txt -q
else
    echo "No requirements.txt found. Skipping dependency installation."
fi

echo "Running AsciigenPy..."
python .
