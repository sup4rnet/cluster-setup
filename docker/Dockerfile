FROM python:3.13-slim

# Install system dependencies for Ansible, p4tenant, agentize, and Claude Code
RUN apt-get update && apt-get install -y \
    openssh-client \
    sshpass \
    git \
    rsync \
    make \
    curl \
    wget \
    gnupg \
    ca-certificates \
    jq \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (required for agentize)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Ensure Claude Code is in PATH
ENV PATH="/root/.local/bin:${PATH}"

# Install Ansible (matching host version 2.18.3)
RUN pip install --no-cache-dir ansible-core==2.18.3

# Install p4tenant dependencies
RUN pip install --no-cache-dir \
    typer[all]>=0.9.0 \
    rich>=13.0.0 \
    ruamel.yaml>=0.18.0 \
    pydantic>=2.0.0

# Install agentize dependencies
RUN pip install --no-cache-dir \
    pyyaml \
    anthropic

# Install uv for faster Python package management (optional)
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /workspace

# Create directories for SSH keys, agentize, and Claude Code
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh
RUN mkdir -p /root/.agentize
RUN mkdir -p /root/.claude

# Configure git for safe directory (needed when mounting volumes)
RUN git config --global --add safe.directory /workspace

# Add helper scripts
COPY install-agentize.sh /usr/local/bin/install-agentize
COPY setup-claude.sh /usr/local/bin/setup-claude
RUN chmod +x /usr/local/bin/install-agentize /usr/local/bin/setup-claude

# Set default command
CMD ["/bin/bash"]
