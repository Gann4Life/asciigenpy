#!/usr/bin/env bash

# Exit on error
set -e

echo "Starting AsciigenPy..."

# Check if git is installed and update repo
if ! command -v git &> /dev/null; then
    echo "Warning: Git is not installed."
    read -p "Do you want to install git to receive updates? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v apt &> /dev/null; then
            echo "Installing git via apt..."
            sudo apt update && sudo apt install -y git
        elif command -v dnf &> /dev/null; then
            echo "Installing git via dnf..."
            sudo dnf install -y git
        elif command -v pacman &> /dev/null; then
            echo "Installing git via pacman..."
            sudo pacman -S --noconfirm git
        else
            echo "Error: Unsupported package manager. Skipping update check."
        fi
    fi
fi

if command -v git &> /dev/null; then
    echo "Checking for updates..."
    git fetch -q
    if git status -uno | grep -q 'Your branch is behind'; then
        echo "Updates found!"
        read -p "Do you want to update AsciigenPy to the latest version? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Pulling latest changes..."
            git pull
        else
            echo "Skipping update."
        fi
    else
        echo "AsciigenPy is up to date."
    fi
fi

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
python -m asciigenpy
