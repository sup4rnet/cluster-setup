#!/bin/bash
# Helper script for managing the Docker test environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.yml"
CONTAINER_NAME="p4-restart-ansible-test"

case "$1" in
    start)
        echo "Starting Docker test environment..."
        docker-compose up -d
        echo "Container started. Use './docker-test.sh shell' to enter."
        ;;

    stop)
        echo "Stopping Docker test environment..."
        docker-compose down
        ;;

    restart)
        echo "Restarting Docker test environment..."
        docker-compose restart
        ;;

    shell|bash)
        echo "Entering container shell..."
        docker-compose exec ansible-test bash
        ;;

    build)
        echo "Building Docker image..."
        docker-compose build --no-cache
        ;;

    logs)
        docker-compose logs -f
        ;;

    install-p4tenant)
        echo "Installing p4tenant CLI in container..."
        docker-compose exec ansible-test bash -c "cd /workspace/p4tenant && pip install -e ."
        echo "p4tenant installed successfully!"
        ;;

    install-agentize)
        echo "Installing agentize in container..."
        docker-compose exec ansible-test install-agentize
        echo ""
        echo "To use agentize, enter the container and run:"
        echo "  source ~/.agentize/setup.sh"
        ;;

    setup-claude)
        echo "Setting up Claude Code authentication..."
        docker-compose exec -it ansible-test setup-claude
        ;;

    setup-all)
        echo "Installing all tools (p4tenant + agentize + Claude Code)..."
        docker-compose exec ansible-test bash -c "cd /workspace/p4tenant && pip install -e ."
        docker-compose exec ansible-test install-agentize
        echo ""
        echo "Now setting up Claude Code authentication..."
        docker-compose exec -it ansible-test setup-claude
        echo ""
        echo "Setup complete!"
        echo ""
        echo "To use agentize:"
        echo "  1. Enter container: ./docker-test.sh shell"
        echo "  2. Activate agentize: source ~/.agentize/setup.sh"
        echo "  3. Use commands like: /issue-to-impl, /ultra-planner, /code-review"
        ;;

    test)
        echo "Running basic tests..."
        docker-compose exec ansible-test bash -c "ansible --version && python --version && gh --version && claude --version"
        ;;

    gh-login)
        echo "Authenticating GitHub CLI..."
        docker-compose exec -it ansible-test gh auth login
        ;;

    ansible)
        shift
        docker-compose exec ansible-test ansible "$@"
        ;;

    ansible-playbook)
        shift
        docker-compose exec ansible-test ansible-playbook "$@"
        ;;

    p4tenant)
        shift
        docker-compose exec ansible-test /workspace/p4tenant-cli "$@"
        ;;

    claude)
        shift
        docker-compose exec ansible-test claude "$@"
        ;;

    clean)
        echo "Removing container and volumes..."
        docker-compose down -v
        echo "Removing image..."
        docker rmi p4-restart-ansible:latest 2>/dev/null || true
        echo "Cleanup complete!"
        ;;

    *)
        echo "P4-RESTART Docker Test Environment Helper"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Container Management:"
        echo "  start              - Start the Docker container"
        echo "  stop               - Stop the Docker container"
        echo "  restart            - Restart the Docker container"
        echo "  shell|bash         - Enter the container shell"
        echo "  build              - Rebuild the Docker image"
        echo "  logs               - Show container logs"
        echo "  clean              - Remove container, volumes, and image"
        echo ""
        echo "Installation:"
        echo "  install-p4tenant       - Install p4tenant CLI in the container"
        echo "  install-agentize       - Install agentize in the container"
        echo "  setup-claude           - Set up Claude Code authentication"
        echo "  setup-all              - Install all tools and authenticate"
        echo "  gh-login               - Authenticate GitHub CLI (for agentize)"
        echo ""
        echo "Testing:"
        echo "  test                   - Run basic version checks"
        echo ""
        echo "Tool Execution:"
        echo "  ansible [args]           - Run ansible command in container"
        echo "  ansible-playbook [args]  - Run ansible-playbook in container"
        echo "  p4tenant [args]          - Run p4tenant CLI in container"
        echo "  claude [args]            - Run Claude Code CLI in container"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 setup-all"
        echo "  $0 shell"
        echo "  $0 ansible-playbook playbooks/adduser.yaml -i inventory.yaml --syntax-check"
        echo "  $0 p4tenant list"
        exit 1
        ;;
esac
