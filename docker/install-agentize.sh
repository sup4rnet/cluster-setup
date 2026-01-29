#!/bin/bash
# Helper script to install agentize inside the container

set -e

echo "Installing agentize..."

# Check if GitHub CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "WARNING: GitHub CLI is not authenticated."
    echo "You'll need to run 'gh auth login' before using agentize features that require GitHub access."
    echo ""
fi

# Install agentize
curl -fsSL https://raw.githubusercontent.com/SyntheSys-Lab/agentize/main/scripts/install | bash

# Source the setup
if [ -f "$HOME/.agentize/setup.sh" ]; then
    echo ""
    echo "Agentize installed successfully!"
    echo ""
    echo "To use agentize, run: source ~/.agentize/setup.sh"
    echo "Or add this line to your shell configuration (if you want it persistent across container restarts)"
else
    echo "Installation may have failed. Check the output above for errors."
    exit 1
fi
