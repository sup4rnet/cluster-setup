"""Inventory management for faster ansible execution and admin user support."""

import os
import uuid
from pathlib import Path

from ruamel.yaml.comments import CommentedMap

from .config import BASE_DIR, DEFAULT_ANSIBLE_USER, INVENTORY_FILE
from .yaml_editor import get_yaml, load_yaml, save_yaml

# Temp inventory prefix - in project root so Ansible finds group_vars/
TEMP_INVENTORY_PREFIX = ".p4tenant-inventory-"


# Known admin users (auto-discovered from inventory-*.yaml files)
def get_admin_users() -> list[str]:
    """Discover admin users from existing inventory files.

    Returns:
        List of admin usernames found in inventory-{user}.yaml files
    """
    admins = []
    for inv_file in BASE_DIR.glob("inventory-*.yaml"):
        # Extract username from inventory-{user}.yaml
        name = inv_file.stem.replace("inventory-", "")
        if name:
            admins.append(name)

    # Also check main inventory for the default admin
    try:
        main_inv = load_yaml(INVENTORY_FILE)
        default_admin = main_inv.get("servers", {}).get("hosts", {}).get("restsrv01", {}).get("ansible_user")
        if default_admin and default_admin not in admins:
            admins.insert(0, default_admin)
    except Exception:
        pass

    return sorted(set(admins))


def get_admin_inventory_path(admin_user: str) -> Path:
    """Get the inventory file path for an admin user.

    Args:
        admin_user: Admin username

    Returns:
        Path to inventory-{admin_user}.yaml
    """
    return BASE_DIR / f"inventory-{admin_user}.yaml"


def create_minimal_inventory(
    vm_name: str,
    admin_user: str,
    output_path: Path | None = None,
) -> Path:
    """Create a minimal inventory for a single VM operation.

    This creates a temporary inventory with:
    - The p4switches group (for switch configuration)
    - The servers group (for VM provisioning)
    - Only the specific VM being added

    Args:
        vm_name: Name of the VM (e.g., restvm-jdoe-01)
        admin_user: Admin username for SSH connections
        output_path: Optional output path, uses temp file if not provided

    Returns:
        Path to the created inventory file
    """
    # Build minimal inventory structure
    inventory = CommentedMap()

    # P4 switches section - copy from main inventory
    inventory["p4switches"] = CommentedMap()
    inventory["p4switches"]["hosts"] = CommentedMap()
    inventory["p4switches"]["hosts"]["rest-bfsw01"] = CommentedMap()
    inventory["p4switches"]["hosts"]["rest-bfsw01"]["ansible_host"] = "rest-bfsw01.polito.it"
    inventory["p4switches"]["hosts"]["rest-bfsw01"]["ansible_user"] = "p4-restart"
    inventory["p4switches"]["hosts"]["rest-bfsw02"] = CommentedMap()
    inventory["p4switches"]["hosts"]["rest-bfsw02"]["ansible_host"] = "rest-bfsw02.polito.it"
    inventory["p4switches"]["hosts"]["rest-bfsw02"]["ansible_user"] = "p4-restart"

    # Servers section - needed for VM provisioning
    inventory["servers"] = CommentedMap()
    inventory["servers"]["hosts"] = CommentedMap()
    inventory["servers"]["hosts"]["restsrv01"] = CommentedMap()
    inventory["servers"]["hosts"]["restsrv01"]["ansible_host"] = "restsrv01.polito.it"
    inventory["servers"]["hosts"]["restsrv01"]["ansible_user"] = admin_user

    # VMs section - only the new VM
    inventory["vms"] = CommentedMap()
    inventory["vms"]["hosts"] = CommentedMap()
    inventory["vms"]["hosts"][vm_name] = CommentedMap()
    inventory["vms"]["hosts"][vm_name]["ansible_host"] = vm_name
    inventory["vms"]["hosts"][vm_name]["ansible_user"] = DEFAULT_ANSIBLE_USER
    inventory["vms"]["vars"] = CommentedMap()
    inventory["vms"]["vars"]["ansible_ssh_common_args"] = (
        f'-o ProxyCommand="ssh {admin_user}@restsrv01.polito.it -W %h:%p"'
    )

    # Determine output path
    if output_path is None:
        # Create temp file in project root so Ansible finds group_vars/
        output_path = BASE_DIR / f"{TEMP_INVENTORY_PREFIX}{uuid.uuid4().hex[:8]}.yaml"

    # Write the inventory
    yaml = get_yaml()
    with open(output_path, "w") as f:
        f.write("---\n")
        yaml.dump(inventory, f)

    return output_path


def sync_admin_inventory(admin_user: str, vm_name: str) -> Path | None:
    """Sync an admin-specific inventory with a new VM.

    Creates or updates inventory-{admin_user}.yaml with the new VM.

    Args:
        admin_user: Admin username
        vm_name: Name of the VM to add

    Returns:
        Path to the admin inventory file, or None if main inventory
    """
    inv_path = get_admin_inventory_path(admin_user)

    # Check main inventory to see who the default admin is
    main_inv = load_yaml(INVENTORY_FILE)
    default_admin = main_inv.get("servers", {}).get("hosts", {}).get("restsrv01", {}).get("ansible_user")

    # If this is the default admin, we already updated inventory.yaml
    if admin_user == default_admin:
        return None

    if inv_path.exists():
        # Update existing admin inventory
        inv_data = load_yaml(inv_path)
    else:
        # Create new admin inventory based on main inventory
        inv_data = load_yaml(INVENTORY_FILE)

        # Update admin user in servers section
        if "servers" in inv_data and "hosts" in inv_data["servers"]:
            if "restsrv01" in inv_data["servers"]["hosts"]:
                inv_data["servers"]["hosts"]["restsrv01"]["ansible_user"] = admin_user

        # Update ProxyCommand in vms vars
        if "vms" in inv_data and "vars" in inv_data["vms"]:
            inv_data["vms"]["vars"]["ansible_ssh_common_args"] = (
                f'-o ProxyCommand="ssh {admin_user}@restsrv01.polito.it -W %h:%p"'
            )

    # Add the new VM if not already present
    if "vms" not in inv_data:
        inv_data["vms"] = CommentedMap()
    if "hosts" not in inv_data["vms"]:
        inv_data["vms"]["hosts"] = CommentedMap()

    if vm_name not in inv_data["vms"]["hosts"]:
        vm_entry = CommentedMap()
        vm_entry["ansible_host"] = vm_name
        vm_entry["ansible_user"] = DEFAULT_ANSIBLE_USER
        inv_data["vms"]["hosts"][vm_name] = vm_entry

    save_yaml(inv_path, inv_data, backup=True)
    return inv_path


def remove_from_admin_inventories(vm_name: str) -> list[Path]:
    """Remove a VM from all admin-specific inventories.

    Args:
        vm_name: Name of the VM to remove

    Returns:
        List of paths to inventories that were modified
    """
    modified = []

    for inv_file in BASE_DIR.glob("inventory-*.yaml"):
        try:
            inv_data = load_yaml(inv_file)
            if "vms" in inv_data and "hosts" in inv_data["vms"]:
                if vm_name in inv_data["vms"]["hosts"]:
                    del inv_data["vms"]["hosts"][vm_name]
                    save_yaml(inv_file, inv_data, backup=True)
                    modified.append(inv_file)
        except Exception:
            continue

    return modified
