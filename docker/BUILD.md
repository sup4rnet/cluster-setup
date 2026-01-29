# Building and Using the Docker Environment

## First-Time Setup

1. **Navigate to the docker directory**
   ```bash
   cd docker
   ```

2. **Build and start the container**
   ```bash
   ./docker-test.sh start
   ```

3. **Install all tools (p4tenant + agentize + Claude Code)**
   ```bash
   ./docker-test.sh setup-all
   ```

4. **Authenticate GitHub CLI** (required for issue/PR access)
   ```bash
   ./docker-test.sh gh-login
   ```

## Using Agentize for Automated Development

Agentize provides native commands for issue resolution and PR management.

### Quick Start

```bash
# Enter container
./docker-test.sh shell

# Activate agentize
source ~/.agentize/setup.sh

# Start Claude Code in your project
cd /workspace
claude

# Use agentize commands:
# /issue-to-impl    - Implement solution from GitHub issue
# /ultra-planner    - Multi-agent planning for complex tasks
# /code-review      - Automated code review workflow
```

### Example: Implement from GitHub Issue

1. Create an issue on GitHub describing what needs to be done
2. In the container with agentize activated:
   ```bash
   claude
   ```
3. Use the command:
   ```
   /issue-to-impl
   ```
4. Agentize will:
   - Fetch the issue
   - Plan implementation
   - Write code
   - Run tests
   - Create a PR

## Daily Usage

### Quick Commands (from docker directory)

```bash
# Start container if not running
./docker-test.sh start

# Enter the container
./docker-test.sh shell

# Inside container - activate agentize
source ~/.agentize/setup.sh

# Test everything works
ansible --version
p4tenant --help
claude --version
```

### Running Commands Without Entering Container

```bash
# Test p4tenant
./docker-test.sh p4tenant list

# Run Ansible playbook
./docker-test.sh ansible-playbook playbooks/adduser.yaml --syntax-check

# Use Claude Code directly
./docker-test.sh claude -p "Review the authentication module"

# Check versions
./docker-test.sh test
```

## What Gets Installed

The container includes:
- ✅ Python 3.13
- ✅ Ansible Core 2.18.3
- ✅ Claude Code CLI (latest)
- ✅ Agentize (with native issue/PR workflows)
- ✅ GitHub CLI (gh)
- ✅ Git, Make, SSH client, jq, ripgrep
- ✅ p4tenant dependencies (typer, rich, ruamel.yaml, pydantic)
- ✅ agentize dependencies (PyYAML, anthropic)

## Agentize Workflows

### /issue-to-impl
Implements solutions from GitHub issues automatically.

### /ultra-planner
Multi-agent planning for complex features.

### /code-review
Automated code review and improvement suggestions.

### Advanced Parallel Workflows
Handle multiple tasks simultaneously (see agentize docs).

## Troubleshooting

**Container won't start?**
```bash
./docker-test.sh clean
./docker-test.sh build
./docker-test.sh start
```

**Need to reinstall tools?**
```bash
./docker-test.sh setup-all
```

**GitHub CLI not working?**
```bash
./docker-test.sh gh-login
```

**Agentize commands not showing?**
```bash
# Inside container
source ~/.agentize/setup.sh
claude plugin list  # Verify agentize is loaded
```

For complete documentation, see [README.md](README.md)
