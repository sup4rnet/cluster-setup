#!/bin/bash
# Helper script to set up Claude Code authentication in the container

set -e

echo "====================================="
echo "Claude Code Authentication Setup"
echo "====================================="
echo ""

# Check if Claude Code is installed
if ! command -v claude &> /dev/null; then
    echo "ERROR: Claude Code CLI is not installed."
    echo "This should not happen in the Docker container."
    exit 1
fi

# Check Claude Code version
echo "Claude Code version:"
claude doctor
echo ""

# Check if already authenticated
if claude -p "test" --output-format json &> /dev/null; then
    echo "✓ Claude Code is already authenticated!"
    echo ""
    exit 0
fi

echo "Claude Code requires authentication. You have several options:"
echo ""
echo "1. RECOMMENDED: Mount Claude config from host machine"
echo "   - Authenticate on your host: Run 'claude' and complete login"
echo "   - Mount ~/.claude volume in docker-compose.yml:"
echo "     volumes:"
echo "       - \${HOME}/.claude:/root/.claude:ro"
echo ""
echo "2. Interactive authentication (one-time setup):"
echo "   - Run this script with TTY: docker-compose exec -it ansible-test setup-claude"
echo "   - Complete the OAuth flow in your browser"
echo "   - Authentication will persist in the docker volume"
echo ""
echo "3. Use Anthropic API key (if supported):"
echo "   - Set ANTHROPIC_API_KEY environment variable"
echo "   - Add to docker-compose.yml:"
echo "     environment:"
echo "       - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}"
echo ""

# Check if running interactively
if [ -t 0 ]; then
    echo "Starting interactive authentication..."
    echo "This will open a browser window for OAuth authentication."
    echo ""
    read -p "Press Enter to continue or Ctrl+C to cancel..."

    # Try to authenticate
    if claude; then
        echo ""
        echo "✓ Authentication successful!"
        echo "You can now use Claude Code in this container."
    else
        echo ""
        echo "✗ Authentication failed."
        echo "Please check the error messages above."
        exit 1
    fi
else
    echo "Not running in interactive mode. Cannot complete OAuth authentication."
    echo "Please use one of the methods above."
    exit 1
fi
