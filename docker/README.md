# Docker Environment with Claude Code & Agentize

This Docker environment provides a complete setup for **AI-powered development workflows** using **Claude Code CLI** and **agentize**, plus tools for P4-RESTART Ansible automation.

## What's Included

### Core Tools
- **Claude Code CLI**: Latest version for AI-powered code analysis and development
- **Agentize**: AI agent SDK with native PR and issue resolution workflows
- **p4tenant**: CLI tool for managing P4-RESTART tenants
- **Ansible Core**: 2.18.3 (matching host system)

### Supporting Tools
- **Python**: 3.13
- **GitHub CLI**: For PR and issue management
- **System tools**: Git, Make, jq, ripgrep, SSH client, rsync

### Dependencies
- **For p4tenant**: typer, rich, ruamel.yaml, pydantic
- **For agentize**: PyYAML, anthropic
- **For Claude Code**: ripgrep (included)

## Use Cases

This environment is designed for:

- **Automated Issue Resolution**: Use agentize's `/issue-to-impl` workflow
- **Code Reviews**: Built-in `/code-review` commands
- **Planning & Architecture**: Multi-agent `/ultra-planner` for complex tasks
- **Parallel Development**: Advanced workflows for handling multiple tasks
- **Ansible Testing**: Test playbooks in isolated environment
- **Tenant Management**: p4tenant operations

## Quick Start

### 1. Build and start the container

```bash
cd docker
./docker-test.sh start
```

### 2. Install and authenticate all tools

```bash
# Install p4tenant, agentize, and set up Claude Code
./docker-test.sh setup-all

# Authenticate GitHub CLI (required for PR/issue access)
./docker-test.sh gh-login
```

### 3. Use agentize for automated workflows

```bash
# Enter the container
./docker-test.sh shell

# Inside container - activate agentize
source ~/.agentize/setup.sh

# Now use agentize commands
claude  # Start interactive session with agentize commands available
```

## Agentize Native Workflows

Agentize provides built-in commands for automated development:

### Issue to Implementation

Convert GitHub issues directly to implemented solutions:

```bash
# In Claude Code with agentize loaded
/issue-to-impl

# This will:
# 1. Fetch the issue from GitHub
# 2. Plan the implementation
# 3. Write the code
# 4. Run tests
# 5. Create a PR
```

### Ultra Planner

Multi-agent debate-based planning for complex tasks:

```bash
/ultra-planner

# Creates detailed implementation plans
# Plans are tracked as GitHub Issues
# Uses multiple AI agents for better planning
```

### Code Review

Automated code review workflows:

```bash
/code-review

# Reviews code changes
# Provides feedback and suggestions
# Can automatically apply fixes
```

### Advanced Parallel Workflows

For handling multiple tasks simultaneously, agentize supports parallel development workflows. See the [agentize documentation](https://github.com/Synthesys-Lab/agentize) for details.

## Claude Code Authentication

Claude Code requires authentication before use. You have **three options**:

### Option 1: Mount from Host (Recommended)

Authenticate Claude on your host machine, then mount the config:

```bash
# On your host machine
claude  # Complete authentication

# Edit docker-compose.yml and uncomment this line:
# - ${HOME}/.claude:/root/.claude:ro
```

### Option 2: Interactive Setup in Container

```bash
./docker-test.sh setup-claude
```

This opens an OAuth flow in your browser. Authentication persists in a Docker volume.

### Option 3: API Key (If Supported)

Set your Anthropic API key in docker-compose.yml:

```yaml
environment:
  - ANTHROPIC_API_KEY=your-api-key-here
```

**Note**: Check [Claude Code documentation](https://code.claude.com/docs/en/setup) for current API key support status.

## Usage Examples

### Using Agentize Workflows

```bash
# Enter container
./docker-test.sh shell

# Activate agentize
source ~/.agentize/setup.sh

# Start Claude Code in your project
cd /workspace
claude

# Inside Claude Code, use agentize commands:
# /issue-to-impl      - Implement from GitHub issue
# /ultra-planner      - Create detailed plans
# /code-review        - Review and improve code
```

### Manual Claude Code Operations

```bash
# From outside container
./docker-test.sh claude -p "Review the authentication module"
./docker-test.sh claude -p "Find and fix bugs in api.py" --allowedTools "Read,Edit,Bash"

# From inside container
claude -p "Analyze the codebase structure"
claude -p "Implement feature X from issue #123"
```

### Ansible and p4tenant

```bash
# Test p4tenant
./docker-test.sh p4tenant list

# Run Ansible playbook
./docker-test.sh ansible-playbook playbooks/adduser.yaml --syntax-check

# Check versions
./docker-test.sh test
```

## Helper Script Commands

### Container Management
```bash
./docker-test.sh start        # Start container
./docker-test.sh stop         # Stop container
./docker-test.sh restart      # Restart container
./docker-test.sh shell        # Enter container shell
./docker-test.sh build        # Rebuild image
./docker-test.sh logs         # View logs
./docker-test.sh clean        # Remove everything
```

### Installation & Setup
```bash
./docker-test.sh install-p4tenant   # Install p4tenant CLI
./docker-test.sh install-agentize   # Install agentize
./docker-test.sh setup-claude       # Set up Claude Code auth
./docker-test.sh setup-all          # Install and authenticate everything
./docker-test.sh gh-login           # Authenticate GitHub CLI
./docker-test.sh test               # Version checks
```

### Tool Execution
```bash
./docker-test.sh ansible [args]          # Run ansible
./docker-test.sh ansible-playbook [args] # Run ansible-playbook
./docker-test.sh p4tenant [args]         # Run p4tenant CLI
./docker-test.sh claude [args]           # Run Claude Code CLI
```

## Agentize Architecture

Agentize follows three core principles:

### 1. Planning First
Use AI to generate detailed plans before writing code. Plans are tracked as GitHub Issues.

### 2. Skills-Based Architecture
Modular, reusable components:
- `/commands` - User-facing interfaces (like /issue-to-impl)
- `/skills` - Implementation logic

### 3. Self-Improvement
Uses `.claude/` as the canonical rules directory, supporting both top-down design and bottom-up implementation.

## Volume Mounts

The container uses these volumes:

- `..:/workspace` - Project root (read/write)
- `~/.ssh:/root/.ssh:ro` - SSH keys (read-only)
- `~/.config/gh:/root/.config/gh:ro` - GitHub CLI config (read-only)
- `~/.claude:/root/.claude:ro` - Claude Code config (optional, read-only)
- `ansible-collections` - Persistent Ansible data
- `agentize-home` - Persistent agentize installation
- `claude-config` - Persistent Claude Code authentication

## Network & Security

- **Network mode**: Host (direct infrastructure access)
- **SSH keys**: Mounted read-only
- **GitHub/Claude auth**: Persisted in Docker volumes or mounted from host
- **Changes persist**: All edits in `/workspace` save to your host machine

## Troubleshooting

### Claude Code not authenticated

```bash
./docker-test.sh setup-claude
```

Or mount your host Claude config (see Authentication section).

### GitHub CLI not authenticated

```bash
./docker-test.sh gh-login
```

### Agentize commands not found

```bash
# Inside container
source ~/.agentize/setup.sh
```

Then start Claude Code again to load the agentize plugin.

### Agentize commands not appearing in Claude

Make sure agentize is properly registered:

```bash
# Inside container
source ~/.agentize/setup.sh
claude plugin list  # Should show agentize
```

If not registered:

```bash
claude plugin marketplace add "$HOME/.agentize"
claude plugin install agentize@agentize
```

### Container build fails

```bash
./docker-test.sh clean
./docker-test.sh build
./docker-test.sh start
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Automated Issue Resolution

on:
  issues:
    types: [labeled]
  workflow_dispatch:

jobs:
  resolve-issue:
    runs-on: ubuntu-latest
    if: contains(github.event.issue.labels.*.name, 'auto-implement')
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker environment
        run: |
          cd docker
          docker-compose build

      - name: Run agentize issue-to-impl
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cd docker
          docker-compose up -d
          docker-compose exec -T ansible-test bash -c "
            source ~/.agentize/setup.sh &&
            cd /workspace &&
            claude -p '/issue-to-impl for issue #${{ github.event.issue.number }}'
          "
```

## Typical Workflow

1. **Create GitHub Issue** with problem description
2. **Label it** appropriately (e.g., "bug", "feature")
3. **Enter container**: `./docker-test.sh shell`
4. **Activate agentize**: `source ~/.agentize/setup.sh`
5. **Start Claude**: `claude`
6. **Run workflow**: `/issue-to-impl` to implement from the issue
7. **Review & iterate**: Use `/code-review` for feedback
8. **Merge PR** created by agentize

## Documentation & Resources

- **Claude Code Docs**: https://code.claude.com/docs
- **Agentize GitHub**: https://github.com/Synthesys-Lab/agentize
- **GitHub CLI Docs**: https://cli.github.com/manual/

## Sources

- [Set up Claude Code](https://code.claude.com/docs/en/setup)
- [Run Claude Code programmatically](https://code.claude.com/docs/en/headless)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
- [Agentize Repository](https://github.com/Synthesys-Lab/agentize)
