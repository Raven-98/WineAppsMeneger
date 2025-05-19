#!/bin/bash

## Підготовка

if ! sudo -v >/dev/null 2>&1; then
    echo "This script requires sudo privileges. Please run as a user with sudo access."
    exit 1
fi

PYTHON_BIN="$(command -v python3)"

if [ -z "$PYTHON_BIN" ]; then
    echo "Python 3 not found. Please install Python 3 before proceeding."
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Python >= $REQUIRED_VERSION is required. Found: $PYTHON_VERSION"
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

echo "Configuring system for Wine environment compatibility..."

if ! dpkg --print-foreign-architectures | grep -q i386; then
    echo "Adding i386 architecture support..."
    sudo dpkg --add-architecture i386
    sudo apt update
fi

REQUIRED_PKGS=(libc6:i386 libncurses6:i386 libstdc++6:i386 libx11-6:i386 libxext6:i386 libfreetype6:i386 libglu1-mesa:i386)

echo "Installing base 32-bit libraries required for Wine prefixes..."
sudo apt install -y "${REQUIRED_PKGS[@]}"

if ! command -v winetricks >/dev/null 2>&1; then
    echo "Installing winetricks..."
    sudo apt install -y winetricks
else
    echo "winetricks already installed."
fi

echo "Checking for system Wine installation..."

if ! command -v wine >/dev/null 2>&1; then
    echo "Wine is not installed on your system."
    read -p "Would you like to install Wine from the official WineHQ repository? (y/n): " INSTALL_WINE
    if [ "$INSTALL_WINE" == "y" ]; then
        echo "Installing Wine from WineHQ..."

        sudo mkdir -pm755 /etc/apt/keyrings
        DISTRO_ID=""
        DISTRO_CODENAME=""

        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO_ID=$ID
            DISTRO_CODENAME=$VERSION_CODENAME
        fi

        if ! command -v wget >/dev/null 2>&1; then
            echo "wget is required but not installed. Installing wget..."
            sudo apt install -y wget
        fi

        sudo wget -qO /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
        sudo wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/${DISTRO_ID}/dists/${DISTRO_CODENAME}/winehq-${DISTRO_CODENAME}.sources

        sudo apt update
        sudo apt install --install-recommends winehq-stable

        if command -v wine >/dev/null 2>&1; then
            echo "Wine successfully installed: $(wine --version)"
        else
            echo "Wine installation failed or not available for this system."
        fi
    else
        echo "Skipping Wine installation."
    fi
else
    echo "Wine is already installed: $(wine --version)"
fi


## Встановлення

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
INSTALL_DIR="$HOME/.wineappsmanager"
VENV_DIR="$INSTALL_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
DESKTOP_FILE="$HOME/.local/share/applications/WineAppsManager.desktop"

if [ -d "$INSTALL_DIR" ]; then
    echo "WineAppsManager is already installed in $INSTALL_DIR."
    read -p "Do you want to reinstall it? (y/n): " REINSTALL
    if [ "$REINSTALL" != "y" ]; then
        echo "Installation aborted."
        exit 0
    else
        echo "Removing the old installation..."
        rm -rf "$INSTALL_DIR"
        rm -f "$DESKTOP_FILE"
    fi
fi

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
    python -m pip  install --upgrade pip
    python -m pip  install -r "$REQUIREMENTS_FILE"
else
    echo "requirements.txt not found. Skipping dependency installation."
fi

echo "Copying program files..."
cp "$PROJECT_DIR/main.py" "$INSTALL_DIR"
cp "$PROJECT_DIR/main.qml" "$INSTALL_DIR"
cp "$PROJECT_DIR/wineappsmanager" "$INSTALL_DIR"
cp "$PROJECT_DIR/icon.png" "$INSTALL_DIR"

chmod +x "$INSTALL_DIR/wineappsmanager"

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
