#!/bin/bash
# Open-EGM4 Installation Script
# Handles installation, updates, repairs, and uninstallation.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

INSTALL_DIR="$HOME/.open-egm4"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
GLOBAL_DB="$INSTALL_DIR/egm4_data.sqlite"
WRAPPER_PATH="$BIN_DIR/open-egm4"

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}   Open-EGM4 Installer & Manager (v1.4)   ${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# Check if installed
if [ -d "$VENV_DIR" ]; then
    info "Existing installation detected at $INSTALL_DIR"
    echo ""
    echo -e "  ${GREEN}1)${NC} Update    (Pull latest version, keep data)"
    echo -e "  ${GREEN}2)${NC} Repair    (Reinstall dependencies, keep data)"
    echo -e "  ${GREEN}3)${NC} Uninstall (Remove application)"
    echo -e "  ${GREEN}4)${NC} Quit"
    echo ""
    
    while true; do
        read -p "Select an option [1-4]: " choice < /dev/tty
        case $choice in
            1) ACTION="Update"; break ;;
            2) ACTION="Repair"; break ;;
            3) ACTION="Uninstall"; break ;;
            4) exit 0 ;;
            *) echo -e "${RED}Invalid option. Please try again.${NC}" ;;
        esac
    done
else
    ACTION="Install"
    info "Ready to install Open-EGM4 to $INSTALL_DIR"
    echo ""
    read -p "Press ENTER to continue, or Ctrl+C to cancel..." < /dev/tty
fi

# ==========================================
# WORKFLOW: UNINSTALL
# ==========================================
if [ "$ACTION" == "Uninstall" ]; then
    info "Uninstalling Open-EGM4..."
    
    if [ -f "$GLOBAL_DB" ]; then
        read -p "Keep database file ($GLOBAL_DB)? [Y/n] " keep_db
        if [[ $keep_db =~ ^[Nn]$ ]]; then
            rm -f "$GLOBAL_DB"
        else
            info "Preserving database..."
        fi
    fi
    
    rm -rf "$VENV_DIR"
    rm -f "$WRAPPER_PATH"
    
    # Remove install dir only if empty or db removed
    if [ ! -f "$GLOBAL_DB" ]; then
        # Check if dir is empty (ignoring hidden files? No, just check if empty)
        rmdir "$INSTALL_DIR" 2>/dev/null || true
    fi
    
    success "Uninstalled successfully."
    echo "Note: You may need to manually remove $BIN_DIR from your PATH if desired."
    exit 0
fi

# ==========================================
# WORKFLOW: INSTALL / UPDATE / REPAIR
# ==========================================

# 1. Prerequisites
info "Checking prerequisites..."
if ! command -v git &> /dev/null; then error "Git not found. Please install git."; fi
if ! command -v python3 &> /dev/null; then error "Python 3 not found."; fi

# Check Python version >= 3.10
python3 -c "import sys; exit(0) if sys.version_info >= (3, 10) else exit(1)" 2>/dev/null
if [ $? -ne 0 ]; then
    error "Python 3.10+ required. Found $(python3 --version)."
fi

# 2. Directories & Migration
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

LOCAL_DB="./egm4_data.sqlite"
if [ -f "$LOCAL_DB" ]; then
    if [ ! -f "$GLOBAL_DB" ]; then
        info "Migrating existing database from current folder to installation directory..."
        cp "$LOCAL_DB" "$GLOBAL_DB"
        success "Database migrated."
    else
        warn "Found local database but a global one already exists. Using global."
    fi
fi

# 3. Virtual Environment
if [ "$ACTION" == "Repair" ] || [ ! -d "$VENV_DIR" ]; then
    info "Creating/Recreating virtual environment..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR" || error "Failed to create venv."
fi

# 4. Install Package
info "Installing/Updating Open-EGM4..."
"$VENV_DIR/bin/pip" install --upgrade pip > /dev/null 2>&1
"$VENV_DIR/bin/pip" install --upgrade git+https://github.com/mmorgans/open-egm4.git || error "Install failed."

# 5. Wrapper
info "Creating command wrapper..."
# Create a robust wrapper script instead of just a symlink to handle VENV activation if needed
# But direct venv python call is usually fine. Symlink is simpler.
ln -sf "$VENV_DIR/bin/open-egm4" "$WRAPPER_PATH"

# 6. PATH Config (Simplified from original)
SHELL_CONFIG=""
case "$SHELL" in
    */zsh) SHELL_CONFIG="$HOME/.zshrc" ;;
    */bash) [ -f "$HOME/.bash_profile" ] && SHELL_CONFIG="$HOME/.bash_profile" || SHELL_CONFIG="$HOME/.bashrc" ;;
    */fish) SHELL_CONFIG="$HOME/.config/fish/config.fish" ;;
    *) SHELL_CONFIG="$HOME/.profile" ;;
esac

PATH_UPDATED=false
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    if [ -w "$SHELL_CONFIG" ]; then
        info "Adding $BIN_DIR to PATH in $SHELL_CONFIG..."
        if [[ "$SHELL" == *"fish"* ]]; then
             echo "set -U fish_user_paths $BIN_DIR \$fish_user_paths" >> "$SHELL_CONFIG"
        else
             echo >> "$SHELL_CONFIG"
             echo "# Added by Open-EGM4" >> "$SHELL_CONFIG"
             echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_CONFIG"
        fi
        PATH_UPDATED=true
    else
        warn "Could not automatically update PATH. Add $BIN_DIR manually."
    fi
else
    info "PATH correctly configured."
fi

success "$ACTION completed successfully!"
echo "Database Location: $GLOBAL_DB"
echo -e "Run with: ${GREEN}open-egm4${NC}"

if [ "$PATH_UPDATED" = true ]; then
    warn "Restart your terminal or run 'source $SHELL_CONFIG' to use the command."
fi
