"""Core tenant management logic."""

from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .config import (
    DEFAULT_ANSIBLE_USER,
    GROUP_VARS_ALL,
    HOST_VARS_DIR,
    HOST_VARS_RESTSRV01,
    INVENTORY_FILE,
    PROXY_COMMAND,
    get_host_vars_path,
    get_vm_name,
)
from .ip_allocator import allocate_ip_pair
from .models import IPAllocation, TenantInput
from .yaml_editor import load_yaml, save_yaml


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class TenantManager:
    """Manages tenant creation and removal."""

    def validate_new_tenant(self, username: str) -> list[str]:
        """Validate that a new tenant can be created.

        Args:
            username: The username to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check restart_users
        all_data = load_yaml(GROUP_VARS_ALL)
        if username in all_data.get("restart_users", []):
            errors.append(f"Username '{username}' already exists in restart_users")

        # Check VM name in restsrv01
        vm_name = get_vm_name(username)
        srv_data = load_yaml(HOST_VARS_RESTSRV01)
        if vm_name in srv_data.get("vms", []):
            errors.append(f"VM '{vm_name}' already exists in restsrv01 vms list")

        # Check host_vars file
        host_vars_path = get_host_vars_path(vm_name)
        if host_vars_path.exists():
            errors.append(f"Host vars file already exists: {host_vars_path.name}")

        # Check inventory
        inv_data = load_yaml(INVENTORY_FILE)
        vms_hosts = inv_data.get("vms", {}).get("hosts", {})
        if vm_name in vms_hosts:
            errors.append(f"VM '{vm_name}' already exists in inventory")

        return errors

    def add_tenant(
        self, tenant: TenantInput, ip_alloc: IPAllocation, dry_run: bool = False
    ) -> list[tuple[str, str]]:
        """Add a new tenant to all configuration files.

        Args:
            tenant: Validated tenant input
            ip_alloc: Allocated IPs for the tenant
            dry_run: If True, only return changes without applying

        Returns:
            List of (file_path, description) for changes made
        """
        vm_name = get_vm_name(tenant.username)
        changes = []

        # 1. Add to restart_users in group_vars/all.yaml
        changes.append(
            (
                "group_vars/all.yaml",
                f"Add '{tenant.username}' to restart_users",
            )
        )
        if not dry_run:
            self._add_to_restart_users(tenant.username)

        # 2. Add VM to vms list in host_vars/restsrv01.yaml
        changes.append(
            (
                "host_vars/restsrv01.yaml",
                f"Add '{vm_name}' to vms list",
            )
        )
        if not dry_run:
            self._add_to_restsrv01_vms(vm_name)

        # 3. Create host_vars/restvm-{user}-01.yaml
        host_vars_path = get_host_vars_path(vm_name)
        changes.append(
            (
                f"host_vars/{vm_name}.yaml",
                "[NEW] Create with dataplane_ipv4 and host_users",
            )
        )
        if not dry_run:
            self._create_host_vars(tenant.username, vm_name, ip_alloc)

        # 4. Add to inventory.yaml
        changes.append(
            (
                "inventory.yaml",
                f"Add '{vm_name}' to vms.hosts",
            )
        )
        if not dry_run:
            self._add_to_inventory(vm_name)

        return changes

    def remove_tenant(self, username: str, dry_run: bool = False) -> list[tuple[str, str]]:
        """Remove a tenant from all configuration files.

        Args:
            username: Username to remove
            dry_run: If True, only return changes without applying

        Returns:
            List of (file_path, description) for changes made
        """
        vm_name = get_vm_name(username)
        changes = []

        # 1. Remove from restart_users
        all_data = load_yaml(GROUP_VARS_ALL)
        if username in all_data.get("restart_users", []):
            changes.append(
                (
                    "group_vars/all.yaml",
                    f"Remove '{username}' from restart_users",
                )
            )
            if not dry_run:
                self._remove_from_restart_users(username)

        # 2. Remove from restsrv01 vms
        srv_data = load_yaml(HOST_VARS_RESTSRV01)
        if vm_name in srv_data.get("vms", []):
            changes.append(
                (
                    "host_vars/restsrv01.yaml",
                    f"Remove '{vm_name}' from vms list",
                )
            )
            if not dry_run:
                self._remove_from_restsrv01_vms(vm_name)

        # 3. Delete host_vars file
        host_vars_path = get_host_vars_path(vm_name)
        if host_vars_path.exists():
            changes.append(
                (
                    f"host_vars/{vm_name}.yaml",
                    "[DELETE] Remove host vars file",
                )
            )
            if not dry_run:
                self._delete_host_vars(vm_name)

        # 4. Remove from inventory
        inv_data = load_yaml(INVENTORY_FILE)
        vms_hosts = inv_data.get("vms", {}).get("hosts", {})
        if vm_name in vms_hosts:
            changes.append(
                (
                    "inventory.yaml",
                    f"Remove '{vm_name}' from vms.hosts",
                )
            )
            if not dry_run:
                self._remove_from_inventory(vm_name)

        return changes

    def get_tenant_info(self, username: str) -> dict | None:
        """Get information about an existing tenant.

        Args:
            username: Username to look up

        Returns:
            Dictionary with tenant info or None if not found
        """
        vm_name = get_vm_name(username)

        # Check restart_users
        all_data = load_yaml(GROUP_VARS_ALL)
        in_restart_users = username in all_data.get("restart_users", [])

        # Check restsrv01 vms
        srv_data = load_yaml(HOST_VARS_RESTSRV01)
        in_vms_list = vm_name in srv_data.get("vms", [])

        # Check host_vars
        host_vars_path = get_host_vars_path(vm_name)
        has_host_vars = host_vars_path.exists()
        ips = []
        if has_host_vars:
            hv_data = load_yaml(host_vars_path)
            ips = list(hv_data.get("dataplane_ipv4", []))

        # Check inventory
        inv_data = load_yaml(INVENTORY_FILE)
        vms_hosts = inv_data.get("vms", {}).get("hosts", {})
        in_inventory = vm_name in vms_hosts

        # Only return if tenant exists in at least one place
        if not any([in_restart_users, in_vms_list, has_host_vars, in_inventory]):
            return None

        return {
            "username": username,
            "vm_name": vm_name,
            "ips": ips,
            "in_restart_users": in_restart_users,
            "in_vms_list": in_vms_list,
            "in_inventory": in_inventory,
            "has_host_vars": has_host_vars,
        }

    def list_all_tenants(self) -> list[dict]:
        """List all tenants found in the system.

        Returns:
            List of tenant info dictionaries
        """
        tenants = []
        seen_usernames = set()

        # Get usernames from restart_users
        all_data = load_yaml(GROUP_VARS_ALL)
        for username in all_data.get("restart_users", []):
            seen_usernames.add(username)

        # Get usernames from host_vars files
        for hv_file in HOST_VARS_DIR.glob("restvm-*-01.yaml"):
            # Extract username from filename like restvm-jdoe-01.yaml
            parts = hv_file.stem.split("-")
            if len(parts) >= 3:
                username = "-".join(parts[1:-1])
                seen_usernames.add(username)

        # Get info for each username
        for username in sorted(seen_usernames):
            info = self.get_tenant_info(username)
            if info:
                tenants.append(info)

        return tenants

    def _add_to_restart_users(self, username: str) -> None:
        """Add username to restart_users list."""
        data = load_yaml(GROUP_VARS_ALL)
        if "restart_users" not in data:
            data["restart_users"] = []
        if username not in data["restart_users"]:
            data["restart_users"].append(username)
        save_yaml(GROUP_VARS_ALL, data)

    def _remove_from_restart_users(self, username: str) -> None:
        """Remove username from restart_users list."""
        data = load_yaml(GROUP_VARS_ALL)
        if "restart_users" in data and username in data["restart_users"]:
            data["restart_users"].remove(username)
        save_yaml(GROUP_VARS_ALL, data)

    def _add_to_restsrv01_vms(self, vm_name: str) -> None:
        """Add VM to restsrv01 vms list."""
        data = load_yaml(HOST_VARS_RESTSRV01)
        if "vms" not in data:
            data["vms"] = []
        if vm_name not in data["vms"]:
            data["vms"].append(vm_name)
        save_yaml(HOST_VARS_RESTSRV01, data)

    def _remove_from_restsrv01_vms(self, vm_name: str) -> None:
        """Remove VM from restsrv01 vms list."""
        data = load_yaml(HOST_VARS_RESTSRV01)
        if "vms" in data and vm_name in data["vms"]:
            data["vms"].remove(vm_name)
        save_yaml(HOST_VARS_RESTSRV01, data)

    def _create_host_vars(
        self, username: str, vm_name: str, ip_alloc: IPAllocation
    ) -> None:
        """Create host_vars file for new VM."""
        data = CommentedMap()
        data["dataplane_ipv4"] = [ip_alloc.ip1, ip_alloc.ip2]

        # Add comment before host_users
        data["host_users"] = [username]
        data.yaml_set_comment_before_after_key(
            "host_users",
            before="NOTE: this must be a list (even with single entry) or it will fail",
        )

        host_vars_path = get_host_vars_path(vm_name)
        save_yaml(host_vars_path, data, backup=False)

    def _delete_host_vars(self, vm_name: str) -> None:
        """Delete host_vars file for a VM."""
        from .yaml_editor import create_backup

        host_vars_path = get_host_vars_path(vm_name)
        if host_vars_path.exists():
            # Create backup before deletion
            create_backup(host_vars_path)
            host_vars_path.unlink()

    def _add_to_inventory(self, vm_name: str) -> None:
        """Add VM to inventory vms.hosts."""
        data = load_yaml(INVENTORY_FILE)

        if "vms" not in data:
            data["vms"] = CommentedMap()
        if "hosts" not in data["vms"]:
            data["vms"]["hosts"] = CommentedMap()

        # Add the new VM host entry
        host_entry = CommentedMap()
        host_entry["ansible_host"] = vm_name
        host_entry["ansible_user"] = DEFAULT_ANSIBLE_USER

        data["vms"]["hosts"][vm_name] = host_entry

        save_yaml(INVENTORY_FILE, data)

    def _remove_from_inventory(self, vm_name: str) -> None:
        """Remove VM from inventory vms.hosts."""
        data = load_yaml(INVENTORY_FILE)

        if "vms" in data and "hosts" in data["vms"]:
            if vm_name in data["vms"]["hosts"]:
                del data["vms"]["hosts"][vm_name]

        save_yaml(INVENTORY_FILE, data)
