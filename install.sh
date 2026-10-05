#!/usr/bin/env bash
set -e

APP_NAME="automagik"
DISPLAY_NAME="AutoMagik"
CONFIG_DIR="$HOME/.config/$APP_NAME"
DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "Checking system dependencies for $DISPLAY_NAME..."

# -----------------------------------------------------------------------------
# Dependency Management Function
# -----------------------------------------------------------------------------
install_dependencies() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID=$ID
        DISTRO_LIKE=${ID_LIKE:-""}
    else
        echo "Unable to detect Linux distribution via /etc/os-release."
        return
    fi

    echo "Detected distribution: $NAME"

    case "$DISTRO_ID" in
        fedora|rhel|centos)
            echo "Checking dependencies via dnf..."
            sudo dnf install -y python3 python3-pyside6 desktop-file-utils
            ;;
        ubuntu|debian|pop|mint)
            echo "Checking dependencies via apt..."
            sudo apt update
            sudo apt install -y python3 python3-pyside6 desktop-file-utils
            ;;
        arch|manjaro|endeavouros)
            echo "Checking dependencies via pacman..."
            sudo pacman -S --needed --noconfirm python python-pyside6 desktop-file-utils
            ;;
        opensuse*|suse)
            echo "Checking dependencies via zypper..."
            sudo zypper install -y python3 python3-pyside6 desktop-file-utils
            ;;
        *)
            if [[ "$DISTRO_LIKE" == *"debian"* ]]; then
                sudo apt update && sudo apt install -y python3 python3-pyside6 desktop-file-utils
            elif [[ "$DISTRO_LIKE" == *"fedora"* ]]; then
                sudo dnf install -y python3 python3-pyside6 desktop-file-utils
            elif [[ "$DISTRO_LIKE" == *"arch"* ]]; then
                sudo pacman -S --needed --noconfirm python python-pyside6 desktop-file-utils
            else
                echo "Unrecognized distribution. Please ensure 'python3' and 'PySide6' are installed manually."
            fi
            ;;
    esac
}

# Run dependency check/installation
install_dependencies

echo ""
echo "Installing $DISPLAY_NAME..."

# 1. Create target directories
mkdir -p "$CONFIG_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$AUTOSTART_DIR"

# 2. Copy application files to ~/.config/automagik/
echo "Copying application files to $CONFIG_DIR..."
cp automagik.py "$CONFIG_DIR/"
chmod +x "$CONFIG_DIR/automagik.py"

# Copy profiles.json only if it doesn't already exist to avoid overwriting user edits
if [ ! -f "$CONFIG_DIR/profiles.json" ]; then
    cp profiles.json "$CONFIG_DIR/"
    echo "  -> Installed default profiles.json"
else
    echo "  -> Existing profiles.json found, skipping overwrite."
fi

# Copy icon image
if [ -f "Automagikbig.png" ]; then
    cp Automagikbig.png "$CONFIG_DIR/"
    echo "  -> Installed icon Automagikbig.png"
elif [ -f "AutoMagik.png" ]; then
    cp AutoMagik.png "$CONFIG_DIR/"
    echo "  -> Installed icon AutoMagik.png"
fi

# Determine installed icon file for launcher entry
ICON_FILE="AutoMagik.png"
if [ -f "$CONFIG_DIR/Automagikbig.png" ]; then
    ICON_FILE="Automagikbig.png"
fi

# 3. Create the .desktop launcher file
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"

echo "Registering app launcher..."
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=$DISPLAY_NAME
Comment=Autostart Profile Selector for KDE Plasma
Exec=python3 $CONFIG_DIR/automagik.py
Icon=$CONFIG_DIR/$ICON_FILE
Terminal=false
Categories=Qt;System;Utility;
StartupWMClass=AutoMagik
X-KDE-autostart-after=panel
EOF

chmod +x "$DESKTOP_FILE"

# 4. Enable autostart on login
echo "Enabling autostart on login..."
cp "$DESKTOP_FILE" "$AUTOSTART_DIR/"

# 5. Refresh XDG Desktop database and KDE icon/desktop cache
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" &> /dev/null || true
fi

if command -v kbuildsycoca6 &> /dev/null; then
    echo "Refreshing KDE Plasma Application Launcher..."
    kbuildsycoca6 &> /dev/null || true
elif command -v kbuildsycoca5 &> /dev/null; then
    kbuildsycoca5 &> /dev/null || true
fi

echo ""
echo "$DISPLAY_NAME installation complete!"
echo "* Dependencies verified and installed."
echo "* AutoMagik is available in your Application Launcher."
echo "* AutoMagik will prompt you upon logging into KDE Plasma."
