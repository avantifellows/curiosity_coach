#!/bin/bash

# This script helps manage dependencies using uv

# Set up virtual environment path
VENV_PATH=".venv"
VENV_ACTIVATE="$VENV_PATH/bin/activate"

# Ensure venv exists and is activated
ensure_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo "Creating virtual environment..."
        uv venv
    fi
    
    # Activate virtual environment
    source "$VENV_ACTIVATE"
    
    # Check if uv is installed
    if ! command -v uv &>/dev/null; then
        echo "Error: uv is not installed. Installing uv..."
        pip install uv
    fi
}

# Function to display help
show_help() {
    echo "Dependencies Management Script"
    echo "------------------------------"
    echo "Usage: ./dependencies.sh [command]"
    echo ""
    echo "Commands:"
    echo "  update             Update all dependencies in requirements.lock"
    echo "  add [package]      Add a package to requirements.txt and update lock file"
    echo "  remove [package]   Remove a package from requirements.txt and update lock file"
    echo "  install            Install dependencies from requirements.lock"
    echo "  help               Show this help message"
    echo ""
}

# Function to update dependencies
update_deps() {
    ensure_venv
    echo "Updating dependencies..."
    uv pip compile requirements.txt -o requirements.lock --upgrade
    echo "Dependencies updated. Use './run.sh' to apply changes."
}

# Function to add a package
add_package() {
    if [ -z "$1" ]; then
        echo "Error: No package specified"
        echo "Usage: ./dependencies.sh add [package]"
        exit 1
    fi
    
    ensure_venv
    echo "Adding package: $1"
    # Add to requirements.txt if not already there
    if ! grep -q "^$1" requirements.txt; then
        echo "$1" >> requirements.txt
        # Sort requirements.txt alphabetically
        sort -o requirements.txt requirements.txt
    else
        echo "Package already in requirements.txt"
    fi
    
    # Update lock file
    uv pip compile requirements.txt -o requirements.lock
    echo "Package added and lock file updated. Use './run.sh' to apply changes."
}

# Function to remove a package
remove_package() {
    if [ -z "$1" ]; then
        echo "Error: No package specified"
        echo "Usage: ./dependencies.sh remove [package]"
        exit 1
    fi
    
    ensure_venv
    echo "Removing package: $1"
    # Remove from requirements.txt
    sed -i '' "/^$1/d" requirements.txt
    
    # Update lock file
    uv pip compile requirements.txt -o requirements.lock
    echo "Package removed and lock file updated. Use './run.sh' to apply changes."
}

# Function to install dependencies
install_deps() {
    ensure_venv
    echo "Installing dependencies from requirements.lock..."
    uv pip install -r requirements.lock
    echo "Dependencies installed."
}

# Main script logic
case "$1" in
    update)
        update_deps
        ;;
    add)
        add_package "$2"
        ;;
    remove)
        remove_package "$2"
        ;;
    install)
        install_deps
        ;;
    help|*)
        show_help
        ;;
esac

exit 0 