#!/bin/bash
#
# FireflyTX Installation Script
# 
# Quick install: curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash
# Or with options: curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash -s -- --dev
#
# Copyright (c) 2025 Firefly Software Solutions Inc.
# Licensed under the Apache License, Version 2.0
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
INSTALL_METHOD="source"  # Changed from "pip" - PyPI package not yet published
INSTALL_DEV=false
PYTHON_CMD="python3"
SKIP_DEPS=false
QUIET=false
FORCE=false
USE_VENV=false
VENV_PATH=""
USE_USER_INSTALL=false
PIP_INSTALL_FLAGS=""

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to show help
show_help() {
    cat << EOF
🔥 FireflyTX Installation Script

USAGE:
    ./install.sh [OPTIONS]
    curl -fsSL <script-url> | bash -s -- [OPTIONS]

OPTIONS:
    --dev               Install in development mode with source code
    --source            Install from source (clone repository) - DEFAULT
    --python COMMAND    Python command to use (default: python3)
    --skip-deps         Skip dependency installation
    --quiet             Quiet installation (minimal output)
    --force             Force installation even if already installed
    --venv PATH         Use or create virtual environment at PATH
    --user              Install to user site-packages (pip install --user)
    --help              Show this help message

NOTE:
    PyPI package is not yet published. Installation is currently source-only.

EXAMPLES:
    # Quick install from source (default)
    curl -fsSL <script-url> | bash

    # Development install (editable mode)
    curl -fsSL <script-url> | bash -s -- --dev

    # Install with virtual environment (recommended for externally-managed systems)
    ./install.sh --venv ~/.fireflytx-venv

    # Install to user site-packages (for externally-managed systems)
    ./install.sh --user

    # Source install with custom Python
    ./install.sh --source --python python3.11

    # Quiet install
    ./install.sh --quiet --skip-deps

REQUIREMENTS:
    - Python 3.9+
    - pip
    - git (for source installation)
    - Java 11+ (for full functionality)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev)
                INSTALL_METHOD="dev"
                shift
                ;;
            --venv)
                USE_VENV=true
                VENV_PATH="$2"
                shift 2
                ;;
            --user)
                USE_USER_INSTALL=true
                shift
                ;;
            --source)
                INSTALL_METHOD="source"
                shift
                ;;
            --python)
                PYTHON_CMD="$2"
                shift 2
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --quiet)
                QUIET=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_requirements() {
    print_step "Checking system requirements..."
    
    # Check Python
    if ! command_exists "$PYTHON_CMD"; then
        print_error "Python not found. Please install Python 3.9+ or specify with --python"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info[0])")
    PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info[1])")
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 9 ]]; then
        print_error "Python 3.9+ required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    print_status "Python $PYTHON_VERSION found ✓"
    
    # Check pip
    if ! command_exists pip && ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
        print_error "pip not found. Please install pip first."
        exit 1
    fi
    
    print_status "pip found ✓"
    
    # Check git for source installations
    if [[ "$INSTALL_METHOD" == "source" || "$INSTALL_METHOD" == "dev" ]]; then
        if ! command_exists git; then
            print_error "git is required for source installation. Please install git first."
            exit 1
        fi
        print_status "git found ✓"
    fi
    
    # Check Java (optional but recommended)
    if command_exists java; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
        if [[ $JAVA_VERSION -ge 11 ]] 2>/dev/null; then
            print_status "Java $JAVA_VERSION found ✓"
        else
            print_warning "Java 11+ recommended for full functionality. Found: $JAVA_VERSION"
        fi
    else
        print_warning "Java not found. Install Java 11+ for full functionality."
    fi
}

# Detect if Python environment is externally managed (PEP 668)
detect_externally_managed() {
    # Check if we're in a virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        print_status "Running in virtual environment: $VIRTUAL_ENV"
        return 1  # Not externally managed
    fi

    # Check for EXTERNALLY-MANAGED marker file
    local python_lib_path=$($PYTHON_CMD -c "import sysconfig; print(sysconfig.get_path('stdlib'))")
    if [ -f "$python_lib_path/EXTERNALLY-MANAGED" ]; then
        return 0  # Externally managed
    fi

    return 1  # Not externally managed
}

# Setup virtual environment if needed
setup_venv() {
    if $USE_VENV; then
        if [ -z "$VENV_PATH" ]; then
            VENV_PATH="$HOME/.fireflytx-venv"
        fi

        if [ ! -d "$VENV_PATH" ]; then
            print_step "Creating virtual environment at $VENV_PATH..."
            $PYTHON_CMD -m venv "$VENV_PATH"
            print_status "Virtual environment created ✓"
        else
            print_status "Using existing virtual environment at $VENV_PATH"
        fi

        # Activate virtual environment
        source "$VENV_PATH/bin/activate"
        PYTHON_CMD="$VENV_PATH/bin/python"
        print_status "Virtual environment activated ✓"
    fi
}

# Determine pip install flags based on environment
setup_pip_flags() {
    if detect_externally_managed; then
        if ! $USE_VENV && ! $USE_USER_INSTALL; then
            print_warning "Detected externally-managed Python environment (PEP 668)"
            print_status "Automatically using --user flag for installation"
            print_status "Alternatively, use --venv to create a virtual environment"
            USE_USER_INSTALL=true
        fi
    fi

    if $USE_USER_INSTALL; then
        PIP_INSTALL_FLAGS="--user"
        print_status "Installing to user site-packages"
    fi
}

# Check if FireflyTX is already installed
check_existing_installation() {
    if $PYTHON_CMD -c "import fireflytx" 2>/dev/null; then
        if ! $FORCE; then
            print_warning "FireflyTX is already installed."
            echo "Use --force to reinstall or uninstall first with: pip uninstall fireflytx"
            exit 1
        else
            print_status "Forcing reinstallation..."
        fi
    fi
}

# Install dependencies
install_dependencies() {
    if $SKIP_DEPS; then
        print_status "Skipping dependency installation"
        return
    fi

    print_step "Installing/updating pip and setuptools..."

    # Try to upgrade pip, but don't fail if it's externally managed
    if ! $QUIET; then
        $PYTHON_CMD -m pip install --upgrade $PIP_INSTALL_FLAGS pip setuptools wheel 2>&1 | grep -v "externally-managed-environment" || true
    else
        $PYTHON_CMD -m pip install --upgrade $PIP_INSTALL_FLAGS pip setuptools wheel >/dev/null 2>&1 || true
    fi

    print_status "Dependencies updated ✓"
}

# Install from PyPI (not yet available)
install_from_pip() {
    print_error "PyPI package not yet published."
    print_status "Please use source installation instead:"
    echo "  ./install.sh --source"
    echo "  or"
    echo "  curl -fsSL <script-url> | bash"
    exit 1
}

# Install from source
install_from_source() {
    print_step "Installing FireflyTX from source..."

    # Determine installation directory
    if [[ "$INSTALL_METHOD" == "dev" ]]; then
        # For dev mode, use current directory or clone to ~/Development/firefly
        if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
            INSTALL_DIR=$(pwd)
            print_status "Using current directory for development installation"
        else
            INSTALL_DIR="$HOME/Development/firefly"
            mkdir -p "$INSTALL_DIR"
            cd "$INSTALL_DIR"

            # Clone repository
            print_status "Cloning repository to $INSTALL_DIR..."
            if ! $QUIET; then
                git clone https://github.com/firefly-oss/python-transactional-engine.git
            else
                git clone https://github.com/firefly-oss/python-transactional-engine.git >/dev/null 2>&1
            fi

            cd python-transactional-engine
            INSTALL_DIR=$(pwd)
        fi
    else
        # For regular install, use temporary directory
        TEMP_DIR=$(mktemp -d)
        cd "$TEMP_DIR"

        # Clone repository
        print_status "Cloning repository..."
        if ! $QUIET; then
            git clone https://github.com/firefly-oss/python-transactional-engine.git
        else
            git clone https://github.com/firefly-oss/python-transactional-engine.git >/dev/null 2>&1
        fi

        cd python-transactional-engine
        INSTALL_DIR=$(pwd)
    fi

    # Install
    if [[ "$INSTALL_METHOD" == "dev" ]]; then
        print_status "Installing in development mode..."
        if ! $QUIET; then
            $PYTHON_CMD -m pip install $PIP_INSTALL_FLAGS -e .
        else
            $PYTHON_CMD -m pip install $PIP_INSTALL_FLAGS -e . >/dev/null 2>&1
        fi
        print_success "FireflyTX installed in development mode ✓"
        print_status "Installation directory: $INSTALL_DIR"
    else
        print_status "Installing from source..."
        if ! $QUIET; then
            $PYTHON_CMD -m pip install $PIP_INSTALL_FLAGS .
        else
            $PYTHON_CMD -m pip install $PIP_INSTALL_FLAGS . >/dev/null 2>&1
        fi
        print_success "FireflyTX installed from source ✓"

        # Cleanup for non-dev installs
        cd - >/dev/null
        rm -rf "$TEMP_DIR"
    fi
}

# Setup lib-transactional-engine
setup_lib_engine() {
    print_step "Setting up lib-transactional-engine..."

    # Check if Maven is available
    if ! command_exists mvn; then
        print_warning "Maven not found. Skipping lib-transactional-engine build."
        print_status "Install Maven to build the Java components"
        return 1
    fi

    # Check if Java is available
    if ! command_exists java; then
        print_warning "Java not found. Skipping lib-transactional-engine build."
        print_status "Install Java 11+ for full functionality"
        return 1
    fi

    # Determine lib-transactional-engine directory
    # For dev mode, use sibling directory
    # For regular install, use ~/Development/firefly
    if [[ "$INSTALL_METHOD" == "dev" ]]; then
        LIB_ENGINE_DIR="$(dirname "$INSTALL_DIR")/lib-transactional-engine"
    else
        LIB_ENGINE_DIR="$HOME/Development/firefly/lib-transactional-engine"
        mkdir -p "$(dirname "$LIB_ENGINE_DIR")"
    fi

    # Clone or update lib-transactional-engine
    if [ ! -d "$LIB_ENGINE_DIR" ]; then
        print_status "Cloning lib-transactional-engine to $LIB_ENGINE_DIR..."
        if ! $QUIET; then
            git clone https://github.com/firefly-oss/lib-transactional-engine.git "$LIB_ENGINE_DIR"
        else
            git clone https://github.com/firefly-oss/lib-transactional-engine.git "$LIB_ENGINE_DIR" >/dev/null 2>&1
        fi
    else
        print_status "lib-transactional-engine already exists at $LIB_ENGINE_DIR"
        print_status "Updating lib-transactional-engine..."
        cd "$LIB_ENGINE_DIR"
        if ! $QUIET; then
            git pull origin main || print_warning "Could not update lib-transactional-engine"
        else
            git pull origin main >/dev/null 2>&1 || print_warning "Could not update lib-transactional-engine"
        fi
        cd - >/dev/null
    fi

    # Build lib-transactional-engine
    print_status "Building lib-transactional-engine (this may take a minute)..."
    cd "$LIB_ENGINE_DIR"
    if ! $QUIET; then
        mvn clean install -DskipTests
    else
        mvn clean install -DskipTests >/dev/null 2>&1
    fi

    if [ $? -eq 0 ]; then
        print_success "lib-transactional-engine built and installed to local Maven repository ✓"
        print_status "Location: $LIB_ENGINE_DIR"
        cd - >/dev/null

        # Export for use by build_java_bridge
        export LIB_ENGINE_DIR
        return 0
    else
        print_warning "lib-transactional-engine build failed"
        cd - >/dev/null
        return 1
    fi
}

# Build Java bridge
build_java_bridge() {
    print_step "Building Java bridge..."

    # Check if Maven is available
    if ! command_exists mvn; then
        print_warning "Maven not found. Java bridge will be built on first use."
        print_status "To build manually later: python -m fireflytx.cli build"
        return
    fi

    # Check if Java is available
    if ! command_exists java; then
        print_warning "Java not found. Java bridge will be built on first use."
        print_status "Install Java 11+ for full functionality"
        return
    fi

    # Setup lib-transactional-engine first
    setup_lib_engine
    LIB_ENGINE_SETUP=$?

    if [ $LIB_ENGINE_SETUP -ne 0 ]; then
        print_warning "Skipping Java bridge build due to lib-transactional-engine setup failure"
        return
    fi

    # Find the Java bridge directory
    JAVA_BRIDGE_DIR="$INSTALL_DIR/fireflytx/integration/java_bridge"

    if [ ! -d "$JAVA_BRIDGE_DIR" ]; then
        print_error "Java bridge directory not found at $JAVA_BRIDGE_DIR"
        return
    fi

    # Build the bridge
    print_status "Building Java subprocess bridge (this may take a minute)..."
    cd "$JAVA_BRIDGE_DIR"

    if ! $QUIET; then
        mvn clean package -DskipTests
    else
        mvn clean package -DskipTests >/dev/null 2>&1
    fi

    if [ $? -eq 0 ]; then
        # Copy the JAR to the expected location
        cp target/java-subprocess-bridge-1.0.0-SNAPSHOT.jar java-subprocess-bridge.jar
        print_success "Java bridge built successfully ✓"
        print_status "JAR size: $(du -h java-subprocess-bridge.jar | cut -f1)"
    else
        print_warning "Java bridge build failed. It will be built on first use."
    fi

    cd - >/dev/null
}

# Create shell wrapper script
create_shell_wrapper() {
    print_step "Creating fireflytx-shell command..."

    # Determine the bin directory based on installation method
    if $USE_USER_INSTALL || [[ -n "$VIRTUAL_ENV" ]]; then
        # User install or venv - use user bin directory
        if [[ -n "$VIRTUAL_ENV" ]]; then
            BIN_DIR="$VIRTUAL_ENV/bin"
        else
            # User bin directory
            BIN_DIR="$HOME/.local/bin"
            mkdir -p "$BIN_DIR"

            # Check if ~/.local/bin is in PATH
            if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
                print_warning "~/.local/bin is not in your PATH"
                print_status "Add this to your ~/.bashrc or ~/.zshrc:"
                echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
            fi
        fi
    else
        # System-wide install - use system bin directory
        if command_exists sudo && [ -w /usr/local/bin ]; then
            BIN_DIR="/usr/local/bin"
        elif [ -w /usr/local/bin ]; then
            BIN_DIR="/usr/local/bin"
        else
            # Fallback to user bin
            BIN_DIR="$HOME/.local/bin"
            mkdir -p "$BIN_DIR"
            print_warning "No write access to /usr/local/bin, using ~/.local/bin"
        fi
    fi

    # Create the wrapper script
    WRAPPER_SCRIPT="$BIN_DIR/fireflytx-shell"

    cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
#
# FireflyTX Interactive Shell Launcher
# Auto-generated by install.sh
#

# Find Python command
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found" >&2
    exit 1
fi

# Launch FireflyTX shell
exec $PYTHON_CMD -m fireflytx.shell "$@"
EOF

    chmod +x "$WRAPPER_SCRIPT"

    print_success "fireflytx-shell command created ✓"
    print_status "Location: $WRAPPER_SCRIPT"
}

# Verify installation
verify_installation() {
    print_step "Verifying installation..."

    # Test import
    if ! $PYTHON_CMD -c "
import fireflytx
from fireflytx import saga, saga_step, SagaEngine, TccEngine
print('✓ FireflyTX imports successfully')
print(f'✓ Version: {fireflytx.__version__}')
print('✓ Core components available')
" 2>/dev/null; then
        print_error "Installation verification failed!"
        exit 1
    fi

    print_success "Installation verified ✓"
}

# Show post-installation information
show_post_install() {
    if $QUIET; then
        return
    fi

    echo
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║  🔥 FireflyTX Installation Complete!                      ║${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}📦 Installed Components:${NC}"
    echo "  ✓ FireflyTX Python package (system-wide)"
    echo "  ✓ lib-transactional-engine (Java library)"
    echo "  ✓ Java subprocess bridge"
    echo
    echo -e "${CYAN}🚀 Quick Start:${NC}"
    echo "  ${GREEN}fireflytx-shell${NC}                - Start interactive shell"
    echo "  ${GREEN}python -m fireflytx.shell${NC}     - Alternative shell command"
    echo "  ${GREEN}python -m fireflytx.cli status${NC} - Check system status"
    echo
    if [[ "$INSTALL_METHOD" == "dev" ]]; then
        echo -e "${CYAN}🛠️  Development Mode:${NC}"
        echo "  Installation directory: ${GREEN}$INSTALL_DIR${NC}"
        echo "  lib-transactional-engine: ${GREEN}$LIB_ENGINE_DIR${NC}"
        echo
        echo -e "${CYAN}📝 Using Task:${NC}"
        echo "  ${GREEN}task test${NC}   - Run all tests"
        echo "  ${GREEN}task shell${NC}  - Start interactive shell"
        echo
    fi
    echo -e "${CYAN}📚 Documentation:${NC}"
    echo "  • GitHub: https://github.com/firefly-oss/python-transactional-engine"
    echo "  • Examples: Run ${GREEN}examples()${NC} in the shell"
    echo "  • Tutorial: Run ${GREEN}quick_start()${NC} in the shell"
    echo
    echo -e "${CYAN}🔧 System Requirements:${NC}"
    echo "  ✓ Python 3.9+"
    echo "  ✓ Java 11+ (for SAGA/TCC execution)"
    echo "  ✓ Maven (for building Java components)"
    echo
    echo -e "${GREEN}Happy coding with FireflyTX! 🚀${NC}"
    echo -e "${CYAN}Python defines, Java executes.${NC}"
    echo
}

# Main installation function
main() {
    # Show banner
    if ! $QUIET; then
        echo -e "${PURPLE}"
        cat << "EOF"
🔥 FireflyTX Installation Script
Enterprise-grade distributed transactions for Python
EOF
        echo -e "${NC}"
        echo
    fi

    # Parse arguments
    parse_args "$@"

    # Check requirements
    check_requirements

    # Setup virtual environment if requested
    setup_venv

    # Setup pip install flags based on environment
    setup_pip_flags

    # Check existing installation
    check_existing_installation

    # Install dependencies
    install_dependencies

    # Install based on method
    case $INSTALL_METHOD in
        pip)
            install_from_pip
            ;;
        source|dev)
            install_from_source
            ;;
        *)
            print_error "Unknown installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac

    # Verify installation
    verify_installation

    # Build Java bridge
    build_java_bridge

    # Create shell wrapper command
    create_shell_wrapper

    # Show post-installation info
    show_post_install
}

# Handle script interruption
trap 'print_error "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"