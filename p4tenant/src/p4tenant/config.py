"""Configuration and constants for p4tenant."""

import os
from pathlib import Path


def find_repo_root() -> Path:
    """Find the repository root by looking for inventory.yaml or .git.

    Starts from current working directory and walks up.
    """
    # Start from current working directory
    current = Path.cwd()

    while current != current.parent:
        # Check for inventory.yaml (our marker file)
        if (current / "inventory.yaml").exists():
            return current
        # Also check for .git as fallback
        if (current / ".git").exists():
            return current
        current = current.parent

    # Fallback: use environment variable or current directory
    if "P4TENANT_ROOT" in os.environ:
        return Path(os.environ["P4TENANT_ROOT"])

    raise RuntimeError(
        "Could not find repository root. Run from within the p4-restart-polito "
        "directory or set P4TENANT_ROOT environment variable."
    )


# Base directory (repository root)
BASE_DIR = find_repo_root()

# YAML file paths relative to BASE_DIR
GROUP_VARS_ALL = BASE_DIR / "group_vars" / "all.yaml"
HOST_VARS_DIR = BASE_DIR / "host_vars"
HOST_VARS_RESTSRV01 = HOST_VARS_DIR / "restsrv01.yaml"
INVENTORY_FILE = BASE_DIR / "inventory.yaml"

# Backup directory
BACKUP_DIR = BASE_DIR / ".p4tenant-backups"

# IP allocation settings
IP_NETWORK = "10.10.0"
IP_SUBNET_MASK = 24

# Reserved IPs (switches, servers, etc.)
RESERVED_IPS = {2, 3, 4, 5, 10, 101}

# VM IP range
VM_IP_START = 11
VM_IP_END = 100

# VM naming
VM_PREFIX = "restvm"
VM_SUFFIX = "01"

# Ansible settings
DEFAULT_ANSIBLE_USER = "p4-restart"
PROXY_COMMAND = '-o ProxyCommand="ssh ubuntu@restsrv01.polito.it -W %h:%p"'


def get_vm_name(username: str, vm_number: int = 1) -> str:
    """Generate VM name from username and VM number.

    Args:
        username: The tenant username
        vm_number: The VM number (1-indexed), defaults to 1

    Returns:
        VM name like restvm-{username}-01, restvm-{username}-02, etc.
    """
    suffix = f"{vm_number:02d}"
    return f"{VM_PREFIX}-{username}-{suffix}"


def get_next_vm_number(username: str, existing_vms: list[str]) -> int:
    """Get the next available VM number for a user.

    Args:
        username: The tenant username
        existing_vms: List of existing VM names for the user

    Returns:
        Next available VM number (1-indexed)
    """
    import re

    pattern = rf"^{VM_PREFIX}-{re.escape(username)}-(\d+)$"
    used_numbers = set()

    for vm in existing_vms:
        match = re.match(pattern, vm)
        if match:
            used_numbers.add(int(match.group(1)))

    # Find the next available number
    next_num = 1
    while next_num in used_numbers:
        next_num += 1

    return next_num


def get_host_vars_path(vm_name: str) -> Path:
    """Get the host_vars file path for a VM."""
    return HOST_VARS_DIR / f"{vm_name}.yaml"
