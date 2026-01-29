#!/bin/bash

# Open-EGM4 Installation Script
# This script installs Open-EGM4 into a dedicated virtual environment
# and sets up the command line tool.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 1. Check Prerequisites
info "Checking prerequisites..."

if ! command -v git &> /dev/null; then
    error "Git is not installed. Please install Git and try again."
fi

if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install Python 3.10 or newer and try again."
fi

# Check Python version (>= 3.10)
python3 -c "import sys; exit(0) if sys.version_info >= (3, 10) else exit(1)" 2>/dev/null
if [ $? -ne 0 ]; then
    error "Open-EGM4 requires Python 3.10 or newer. Your python3 version is $(python3 --version). Please upgrade Python."
fi

# 2. Setup Directories
INSTALL_DIR="$HOME/.open-egm4"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"

# Detect if updating
if [ -d "$VENV_DIR" ]; then
    info "Existing installation detected. Updating..."
    IS_UPDATE=true
else
    info "Installing fresh to $INSTALL_DIR..."
    IS_UPDATE=false
    mkdir -p "$INSTALL_DIR"
fi

mkdir -p "$BIN_DIR"

# 3. Create/Verify Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment..."
    if ! python3 -m venv "$VENV_DIR"; then
        error "Failed to create virtual environment. Please check permissions."
    fi
else
    # Simple check if venv is valid
    if [ ! -f "$VENV_DIR/bin/pip" ]; then
        warn "Virtual environment appears broken. Recreating..."
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi
fi

# 4. Install/Update Package
# We want to be careful with the output so it doesn't look like it hung
info "Fetching latest version and installing dependencies..."
if ! "$VENV_DIR/bin/pip" install --upgrade pip > /dev/null 2>&1; then
     warn "Failed to upgrade pip, proceeding with current version..."
fi

# Install the package.
if ! "$VENV_DIR/bin/pip" install --upgrade git+https://github.com/mmorgans/open-egm4.git; then
    error "Failed to install Open-EGM4. Please check your internet connection and git configuration."
fi

# 5. Create Symlink
TARGET_BIN="$VENV_DIR/bin/open-egm4"
LINK_NAME="$BIN_DIR/open-egm4"

if [ -f "$TARGET_BIN" ]; then
    info "Linking executable to $LINK_NAME..."
    ln -sf "$TARGET_BIN" "$LINK_NAME"
else
    error "Installation failed: Binary not found at $TARGET_BIN"
fi

# 6. Check PATH
SHELL_CONFIG=""
case "$SHELL" in
    */zsh) SHELL_CONFIG="$HOME/.zshrc" ;;
    */bash) 
        if [ -f "$HOME/.bash_profile" ]; then
            SHELL_CONFIG="$HOME/.bash_profile"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_CONFIG="$HOME/.bashrc"
        else
            SHELL_CONFIG="$HOME/.profile"
        fi
        ;;
    */fish) SHELL_CONFIG="$HOME/.config/fish/config.fish" ;;
    *) SHELL_CONFIG="$HOME/.profile" ;;
esac

PATH_UPDATED=false
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    if [ -f "$SHELL_CONFIG" ] && [ -w "$SHELL_CONFIG" ]; then
        info "Adding $BIN_DIR to PATH in $SHELL_CONFIG..."
        echo "" >> "$SHELL_CONFIG"
        echo "# Added by Open-EGM4 installer" >> "$SHELL_CONFIG"
        
        # Fish syntax is different
        if [[ "$SHELL" == *"fish"* ]]; then
             echo "set -U fish_user_paths $BIN_DIR \$fish_user_paths" >> "$SHELL_CONFIG"
        else
             echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_CONFIG"
        fi
        
        PATH_UPDATED=true
    elif [ ! -f "$SHELL_CONFIG" ]; then
        # Try to create it if it doesn't exist but directory does
        touch "$SHELL_CONFIG" 2>/dev/null
        if [ $? -eq 0 ]; then
             info "Created $SHELL_CONFIG and adding PATH..."
             echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_CONFIG"
             PATH_UPDATED=true
        else
             warn "Could not create $SHELL_CONFIG. Please manually add $BIN_DIR to your PATH."
        fi
    else
        warn "Could not write to $SHELL_CONFIG. Please manually add $BIN_DIR to your PATH."
    fi
else
    info "PATH already correctly configured."
fi

# 7. Finish
echo ""
if [ "$IS_UPDATE" = true ]; then
    success "Update complete! You are now running the latest version."
else
    success "Installation complete!"
fi

echo ""
echo "To start the application, run:"
echo -e "${GREEN}open-egm4${NC}"
echo ""

if [ "$PATH_UPDATED" = true ]; then
    echo -e "${BLUE}NOTE:${NC} You may need to restart your terminal or run:"
    echo "source $SHELL_CONFIG"
    echo "for the command to become available."
elif [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then 
     # If we couldn't auto-update path
     echo -e "${YELLOW}WARNING:${NC} $BIN_DIR is not in your PATH."
     echo "Run this command to fix it temporarily:"
     echo "export PATH=\"\$PATH:$BIN_DIR\""
fi
