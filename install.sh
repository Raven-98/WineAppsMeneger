#!/bin/bash

PYTHON_BIN="$(command -v python3)"

if [ -z "$PYTHON_BIN" ]; then
    echo "Python 3 not found. Please install Python 3 before proceeding."
    exit 1
fi

echo "Checking for venv module..."
if ! "$PYTHON_BIN" -m venv --help >/dev/null 2>&1; then
    echo "Your Python does not support 'venv'."
    read -p "Would you like to install the 'python3-venv' package? (y/n): " INSTALL_VENV
    if [ "$INSTALL_VENV" == "y" ]; then
        echo "Installing 'python3-venv'..."
        sudo apt update
        sudo apt install python3-venv
    else
        echo "You need 'python3-venv' to proceed. Exiting."
        exit 1
    fi
fi

echo "Checking for 32-bit support (ld-linux.so.2)..."
if [ ! -e /lib/ld-linux.so.2 ] && [ ! -e /lib32/ld-linux.so.2 ]; then
    echo "Missing 'ld-linux.so.2'. This file is required to run 32-bit applications."
    read -p "Would you like to install 'libc6:i386'? (y/n): " INSTALL_LIBC
    if [ "$INSTALL_LIBC" == "y" ]; then
        echo "Installing 'libc6:i386'..."
        sudo dpkg --add-architecture i386
        sudo apt update
        sudo apt install libc6-i386
    else
        echo "You need 'libc6:i386' to proceed. Exiting."
        exit 1
    fi
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
INSTALL_DIR="$HOME/.wineappsmanager"
VENV_DIR="$INSTALL_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
DESKTOP_FILE="$HOME/.local/share/applications/WineAppsManager.desktop"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating installation directory at $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
else
    echo "Installation directory already exists at $INSTALL_DIR."
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

source "$VENV_DIR/bin/activate"

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "requirements.txt not found. Skipping dependency installation."
fi

echo "Copying program files..."
cp "$PROJECT_DIR/main.py" "$INSTALL_DIR"
cp "$PROJECT_DIR/main.qml" "$INSTALL_DIR"
cp "$PROJECT_DIR/wineappsmanager" "$INSTALL_DIR"
cp "$PROJECT_DIR/icon.png" "$INSTALL_DIR"

echo "Creating desktop entry..."

cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Name=WineAppsManager
Comment=Manage Wine applications easily
Exec=$INSTALL_DIR/wineappsmanager
Icon=$INSTALL_DIR/icon.png
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
EOL

echo "Desktop file created at $DESKTOP_FILE"

echo "Installation complete."
