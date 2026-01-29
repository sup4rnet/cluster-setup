"""Typer CLI commands for p4tenant."""

import getpass
import os
import subprocess
from typing import Optional

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from .config import BASE_DIR, HOST_VARS_RESTSRV01, get_vm_name
from .yaml_editor import load_yaml
from .inventory import (
    create_minimal_inventory,
    get_admin_users,
    remove_from_admin_inventories,
    sync_admin_inventory,
)
from .ip_allocator import allocate_ip_pair, get_ip_status, get_ip_to_vm_mapping
from .models import TenantInput
from .tenant import TenantManager
from .ui import (
    console,
    create_ip_status_table,
    create_tenant_table,
    print_changes_panel,
    print_error,
    print_info,
    print_success,
    print_warning,
)

app = typer.Typer(
    name="p4tenant",
    help="CLI tool for managing P4-RESTART tenants",
    no_args_is_help=True,
)

# Create 'add' subcommand group
add_app = typer.Typer(
    name="add",
    help="Add new users or VMs",
    no_args_is_help=True,
)
app.add_typer(add_app, name="add")

# Help texts for interactive prompts
HELP_ADMIN_USER = """[bold cyan]Admin User[/bold cyan]
Your SSH username for accessing restsrv01.polito.it.
This is used for:
  - SSH connections to the physical server
  - ProxyCommand for VM access
  - Running ansible playbooks

Each admin has their own inventory file (inventory-{username}.yaml)
that will be kept in sync when adding/removing tenants."""

HELP_TENANT_USERNAME = """[bold cyan]Tenant Username[/bold cyan]
The username for the new P4-RESTART tenant.
Requirements:
  - 3-16 characters long
  - Lowercase letters, numbers, underscores, or hyphens
  - Must start with a letter

This will create:
  - A VM named restvm-{username}-01
  - User account on the VM
  - Allocated IP addresses for the dataplane"""

HELP_TENANT_EMAIL = """[bold cyan]Email Address[/bold cyan]
Optional contact email for the tenant.
Used for documentation purposes only."""

HELP_RUN_ANSIBLE = """[bold cyan]Run Ansible Playbook[/bold cyan]
Execute the ansible playbook to provision the new tenant.
This will:
  - Create the VM on restsrv01
  - Configure networking with allocated IPs
  - Set up user accounts

A minimal inventory is used containing only:
  - p4switches (both switches)
  - servers (restsrv01)
  - The new VM only

This is much faster than running against all VMs."""

HELP_NUM_VMS = """[bold cyan]Number of VMs[/bold cyan]
How many VMs to create for this new tenant.

Each VM will:
  - Have a unique name (restvm-{username}-01, restvm-{username}-02, etc.)
  - Get its own pair of IP addresses from the dataplane network
  - Be added to the inventory and host_vars

Most tenants only need 1 VM. Create more if the tenant needs
separate environments for different experiments."""


def show_help(topic: str) -> None:
    """Display help for a specific topic."""
    help_texts = {
        "admin": HELP_ADMIN_USER,
        "username": HELP_TENANT_USERNAME,
        "email": HELP_TENANT_EMAIL,
        "ansible": HELP_RUN_ANSIBLE,
        "num_vms": HELP_NUM_VMS,
    }
    if topic in help_texts:
        console.print(Panel(help_texts[topic], border_style="blue"))


def prompt_with_help(
    prompt_text: str,
    help_topic: str,
    default: str = "",
    password: bool = False,
) -> str:
    """Prompt for input with help option.

    Type '?' to see help for this field.
    """
    while True:
        result = Prompt.ask(
            f"{prompt_text} [dim](? for help)[/dim]",
            default=default,
            password=password,
        )
        if result == "?":
            show_help(help_topic)
            continue
        return result


def prompt_admin_user() -> str:
    """Prompt user to select an admin user with help support."""
    admins = get_admin_users()

    if not admins:
        console.print(Panel(
            "[yellow]No admin inventory files found.[/yellow]\n"
            "Enter your SSH username for restsrv01.polito.it.",
            title="Admin User",
            border_style="yellow",
        ))
        return prompt_with_help(
            "[bold]Enter your admin username[/bold]",
            "admin",
        )

    # Show help hint
    console.print()
    console.print("[bold]Select admin user[/bold] [dim](? for help)[/dim]")
    console.print()

    # Show available admins in a nice format
    for i, admin in enumerate(admins, 1):
        inv_file = f"inventory-{admin}.yaml"
        exists = (BASE_DIR / inv_file).exists()
        status = "[green]has inventory[/green]" if exists else "[dim]new[/dim]"
        console.print(f"  [bold cyan]{i}[/bold cyan]. {admin}  {status}")

    console.print(f"  [bold cyan]{len(admins) + 1}[/bold cyan]. [dim]Other (enter manually)[/dim]")
    console.print()

    # Get selection
    while True:
        choice = Prompt.ask("Choice", default="1")

        if choice == "?":
            show_help("admin")
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(admins):
                return admins[idx]
            elif idx == len(admins):
                return prompt_with_help(
                    "[bold]Enter admin username[/bold]",
                    "admin",
                )
        except ValueError:
            # User might have typed the username directly
            if choice in admins:
                return choice
            # Accept any non-empty string as username
            if choice.strip():
                return choice.strip()

        console.print("[red]Invalid choice. Please enter a number or username.[/red]")

    return admins[0] if admins else "alessandro"


def prompt_tenant_username() -> str:
    """Prompt for tenant username with help support."""
    return prompt_with_help(
        "[bold]Enter tenant username[/bold]",
        "username",
    )


def prompt_tenant_email() -> str:
    """Prompt for tenant email with help support."""
    return prompt_with_help(
        "[bold]Enter email[/bold] [dim](optional)[/dim]",
        "email",
        default="",
    )


def prompt_run_ansible() -> bool:
    """Prompt to run ansible with help support."""
    while True:
        result = Prompt.ask(
            "[bold]Run ansible-playbook?[/bold] [dim](y/n/? for help)[/dim]",
            default="n",
        )
        if result == "?":
            show_help("ansible")
            continue
        return result.lower() in ("y", "yes")


def prompt_num_vms() -> int:
    """Prompt for number of VMs to create with help support."""
    while True:
        result = Prompt.ask(
            "[bold]How many VMs to create?[/bold] [dim](? for help)[/dim]",
            default="1",
        )
        if result == "?":
            show_help("num_vms")
            continue
        try:
            num = int(result)
            if num < 1:
                console.print("[red]Number must be at least 1[/red]")
                continue
            if num > 10:
                console.print("[red]Maximum 10 VMs per tenant[/red]")
                continue
            return num
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")


def prompt_select_user(tenants: list[dict]) -> str | None:
    """Prompt user to select from a list of existing tenants.

    Args:
        tenants: List of tenant info dictionaries

    Returns:
        Selected username, or None if cancelled
    """
    if not tenants:
        print_error("No existing users found")
        return None

    console.print("[bold]Select user[/bold]")
    console.print()

    for i, tenant in enumerate(tenants, 1):
        vm_count = tenant.get("vm_count", 0)
        vm_info = f"{vm_count} VM(s)" if vm_count else "no VMs"
        console.print(f"  [bold cyan]{i}[/bold cyan]. {tenant['username']}  [dim]({vm_info})[/dim]")

    console.print()

    while True:
        choice = Prompt.ask("Choice")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tenants):
                return tenants[idx]["username"]
        except ValueError:
            # User might have typed the username directly
            matching = [t for t in tenants if t["username"] == choice]
            if matching:
                return choice

        console.print("[red]Invalid choice. Please enter a number or username.[/red]")


def get_tenant_vms(username: str) -> list[str]:
    """Get all VMs from restsrv01.yaml that contain the username.

    Args:
        username: The tenant username to search for

    Returns:
        List of VM names containing the username
    """
    try:
        data = load_yaml(HOST_VARS_RESTSRV01)
        all_vms = data.get("vms", [])
        return [vm for vm in all_vms if username in vm]
    except Exception:
        return []


def prompt_vm_selection(vms: list[str]) -> list[str]:
    """Prompt user to select which VMs to delete.

    Shows a checkbox-style list where user can toggle selections.

    Args:
        vms: List of VM names to choose from

    Returns:
        List of selected VM names
    """
    if not vms:
        return []

    if len(vms) == 1:
        # Only one VM, just confirm
        console.print(f"  [green]✓[/green] {vms[0]}")
        return vms

    # Show VMs with selection status (all selected by default)
    selected = set(range(len(vms)))  # All selected by default

    console.print("[bold]VMs to delete:[/bold]")
    console.print("[dim]Enter numbers to toggle, 'all', 'none', or press Enter to confirm[/dim]")
    console.print()

    while True:
        # Display current selection
        for i, vm in enumerate(vms):
            if i in selected:
                console.print(f"  [green]✓[/green] [bold]{i + 1}[/bold]. {vm}")
            else:
                console.print(f"  [dim]○[/dim] [dim]{i + 1}. {vm}[/dim]")

        console.print()
        choice = Prompt.ask("Toggle selection", default="confirm").strip().lower()

        if choice in ("", "confirm", "done", "ok"):
            break
        elif choice == "all":
            selected = set(range(len(vms)))
            console.print()
        elif choice == "none":
            selected = set()
            console.print()
        else:
            # Parse numbers (comma or space separated)
            try:
                nums = [int(n.strip()) - 1 for n in choice.replace(",", " ").split() if n.strip()]
                for n in nums:
                    if 0 <= n < len(vms):
                        if n in selected:
                            selected.discard(n)
                        else:
                            selected.add(n)
                console.print()
            except ValueError:
                console.print("[red]Invalid input. Enter numbers, 'all', 'none', or press Enter.[/red]")
                console.print()

    return [vms[i] for i in sorted(selected)]


@add_app.command("user")
def add_user(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username for the new tenant"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address (optional)"),
    num_vms: Optional[int] = typer.Option(None, "--num-vms", "-n", help="Number of VMs to create (default: 1)"),
    admin: Optional[str] = typer.Option(None, "--admin", "-A", help="Admin user for SSH/ansible operations"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    run_ansible: bool = typer.Option(False, "--run-ansible", "-a", help="Run ansible-playbook after adding"),
) -> None:
    """Add a new user (tenant) with one or more VMs.

    Creates all necessary configuration for a new P4-RESTART tenant:
    - Adds user to restart_users list
    - Creates VM configuration(s) with allocated IPs
    - Updates inventory files
    - Optionally runs ansible to provision the VM(s)
    """
    console.print()

    # Show welcome banner in interactive mode
    if not yes:
        console.print(Panel(
            "[bold]Add New P4-RESTART User[/bold]\n\n"
            "This wizard will guide you through creating a new user.\n"
            "Type [cyan]?[/cyan] at any prompt to see detailed help.",
            border_style="green",
        ))
        console.print()

    # Get admin user first
    if not admin:
        if yes:
            # In non-interactive mode, try to get default admin
            admins = get_admin_users()
            admin = admins[0] if admins else "alessandro"
        else:
            admin = prompt_admin_user()

    print_info(f"Operating as admin: [bold]{admin}[/bold]")
    console.print()

    # Get username
    if not username:
        if yes:
            print_error("Username is required in non-interactive mode (-u USERNAME)")
            raise typer.Exit(1)
        username = prompt_tenant_username()

    # Get email (skip prompt in non-interactive mode)
    if email is None and not yes:
        email = prompt_tenant_email()

    # Get number of VMs
    if num_vms is None:
        if yes:
            num_vms = 1
        else:
            console.print()
            num_vms = prompt_num_vms()

    # Validate input
    console.print()
    console.print("[dim]Validating...[/dim]")

    try:
        tenant = TenantInput(username=username, email=email if email else None)
    except PydanticValidationError as e:
        for error in e.errors():
            print_error(error["msg"])
        raise typer.Exit(1)

    # Check if tenant already exists
    manager = TenantManager()
    errors = manager.validate_new_tenant(tenant.username, num_vms)

    if errors:
        for error in errors:
            print_error(error)
        raise typer.Exit(1)

    print_success(f"Username '{tenant.username}' is available")

    # Allocate IPs for all VMs
    ip_allocations = []
    for i in range(num_vms):
        ip_alloc = allocate_ip_pair()
        if not ip_alloc:
            print_error(f"No IP addresses available for VM {i + 1}")
            raise typer.Exit(1)
        ip_allocations.append(ip_alloc)

    if num_vms == 1:
        print_success(f"Allocated IPs: {ip_allocations[0].ip1}, {ip_allocations[0].ip2}")
    else:
        print_success(f"Allocated IPs for {num_vms} VMs:")
        for i, ip_alloc in enumerate(ip_allocations, 1):
            console.print(f"  VM {i}: {ip_alloc.ip1}, {ip_alloc.ip2}")

    # Show planned changes
    console.print()
    changes = manager.add_tenant(tenant, ip_allocations, dry_run=True)

    # Add admin inventory sync to changes display
    admin_inv_path = BASE_DIR / f"inventory-{admin}.yaml"
    admins = get_admin_users()
    main_admin = admins[0] if admins else "alessandro"
    for vm_num in range(1, num_vms + 1):
        vm_name = get_vm_name(tenant.username, vm_num)
        if admin != main_admin:
            if admin_inv_path.exists():
                changes.append((f"inventory-{admin}.yaml", f"Add '{vm_name}' to vms.hosts"))
            else:
                changes.append((f"inventory-{admin}.yaml", f"[NEW] Create with '{vm_name}'"))

    print_changes_panel(changes)

    # Confirm
    if not yes:
        console.print()
        if not Confirm.ask("[bold]Apply changes?[/bold]", default=False):
            print_warning("Aborted")
            raise typer.Exit(0)

    # Apply changes
    console.print()
    console.print("[dim]Applying changes...[/dim]")
    manager.add_tenant(tenant, ip_allocations, dry_run=False)

    # Sync admin-specific inventory for all VMs
    for vm_num in range(1, num_vms + 1):
        vm_name = get_vm_name(tenant.username, vm_num)
        synced_inv = sync_admin_inventory(admin, vm_name)
        if synced_inv:
            print_success(f"Synced {synced_inv.name}")

    print_success("All changes applied successfully")

    # Run ansible if requested
    if run_ansible:
        should_run = True
    elif yes:
        should_run = False
    else:
        console.print()
        should_run = prompt_run_ansible()

    if should_run:
        console.print()
        # Run ansible for each VM
        for vm_num in range(1, num_vms + 1):
            vm_name = get_vm_name(tenant.username, vm_num)
            if num_vms > 1:
                console.print(f"[bold]Provisioning {vm_name}...[/bold]")
            run_ansible_for_vm(vm_name, admin)


@add_app.command("vm")
def add_vm(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username of the existing user"),
    vm_name: Optional[str] = typer.Option(None, "--vm-name", "-v", help="Name for the new VM"),
    admin: Optional[str] = typer.Option(None, "--admin", "-A", help="Admin user for SSH/ansible operations"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    run_ansible: bool = typer.Option(False, "--run-ansible", "-a", help="Run ansible-playbook after adding"),
) -> None:
    """Add a new VM for an existing user.

    Creates a new VM for a user who already exists in the system:
    - Allocates new IP addresses for the VM
    - Creates VM host_vars file
    - Updates inventory files
    - Optionally runs ansible to provision the VM
    """
    console.print()

    manager = TenantManager()

    # Show welcome banner in interactive mode
    if not yes:
        console.print(Panel(
            "[bold]Add New VM for Existing User[/bold]\n\n"
            "This wizard will guide you through adding a VM to an existing user.\n"
            "Type [cyan]?[/cyan] at any prompt to see detailed help.",
            border_style="green",
        ))
        console.print()

    # Get admin user first
    if not admin:
        if yes:
            admins = get_admin_users()
            admin = admins[0] if admins else "alessandro"
        else:
            admin = prompt_admin_user()

    print_info(f"Operating as admin: [bold]{admin}[/bold]")
    console.print()

    # Get username (select from existing users)
    if not username:
        if yes:
            print_error("Username is required in non-interactive mode (-u USERNAME)")
            raise typer.Exit(1)

        # Get list of existing tenants
        tenants = manager.list_all_tenants()
        if not tenants:
            print_error("No existing users found. Use 'p4tenant add user' to create a new user first.")
            raise typer.Exit(1)

        username = prompt_select_user(tenants)
        if not username:
            raise typer.Exit(1)

    # Verify user exists
    user_info = manager.get_tenant_info(username)
    if not user_info or not user_info.get("in_restart_users"):
        print_error(f"User '{username}' not found in restart_users")
        print_info("Use 'p4tenant add user' to create a new user first")
        raise typer.Exit(1)

    print_info(f"Selected user: [bold]{username}[/bold]")

    # Show existing VMs for this user
    existing_vms = manager.get_user_vms(username)
    if existing_vms:
        console.print()
        console.print(f"[bold]Existing VMs for {username}:[/bold]")
        for vm in existing_vms:
            console.print(f"  - {vm}")
    else:
        console.print()
        console.print(f"[dim]No existing VMs found for {username}[/dim]")

    # Get or suggest VM name
    suggested_name = manager.get_suggested_vm_name(username)

    if not vm_name:
        if yes:
            vm_name = suggested_name
        else:
            console.print()
            vm_name = Prompt.ask(
                "[bold]Enter VM name[/bold]",
                default=suggested_name,
            )

    # Validate VM name
    console.print()
    console.print("[dim]Validating...[/dim]")

    errors = manager.validate_new_vm(vm_name)
    if errors:
        for error in errors:
            print_error(error)
        raise typer.Exit(1)

    print_success(f"VM name '{vm_name}' is available")

    # Allocate IPs
    ip_alloc = allocate_ip_pair()
    if not ip_alloc:
        print_error("No IP addresses available in the allowed range")
        raise typer.Exit(1)

    print_success(f"Allocated IPs: {ip_alloc.ip1}, {ip_alloc.ip2}")

    # Show planned changes
    console.print()
    changes = manager.add_vm(username, vm_name, ip_alloc, dry_run=True)

    # Add admin inventory sync to changes display
    admin_inv_path = BASE_DIR / f"inventory-{admin}.yaml"
    admins = get_admin_users()
    main_admin = admins[0] if admins else "alessandro"
    if admin != main_admin:
        if admin_inv_path.exists():
            changes.append((f"inventory-{admin}.yaml", f"Add '{vm_name}' to vms.hosts"))
        else:
            changes.append((f"inventory-{admin}.yaml", f"[NEW] Create with '{vm_name}'"))

    print_changes_panel(changes)

    # Confirm
    if not yes:
        console.print()
        if not Confirm.ask("[bold]Apply changes?[/bold]", default=False):
            print_warning("Aborted")
            raise typer.Exit(0)

    # Apply changes
    console.print()
    console.print("[dim]Applying changes...[/dim]")
    manager.add_vm(username, vm_name, ip_alloc, dry_run=False)

    # Sync admin-specific inventory
    synced_inv = sync_admin_inventory(admin, vm_name)
    if synced_inv:
        print_success(f"Synced {synced_inv.name}")

    print_success("All changes applied successfully")

    # Run ansible if requested
    if run_ansible:
        should_run = True
    elif yes:
        should_run = False
    else:
        console.print()
        should_run = prompt_run_ansible()

    if should_run:
        console.print()
        run_ansible_for_vm(vm_name, admin)


@app.command()
def remove(
    username: Optional[str] = typer.Argument(None, help="Username of the tenant to remove"),
    admin: Optional[str] = typer.Option(None, "--admin", "-A", help="Admin user for SSH/ansible operations"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    skip_ansible: bool = typer.Option(False, "--skip-ansible", "-s", help="Skip ansible playbook (only update config files)"),
    skip_config: bool = typer.Option(False, "--skip-config", "-c", help="Skip config file updates (only run ansible)"),
) -> None:
    """Remove a tenant and all associated configuration.

    By default, this command:
    1. Runs ansible to delete VMs and remove user from remote systems
    2. Updates configuration files (with confirmation prompt)

    Use --skip-ansible to only update config files.
    Use --skip-config to only run ansible without updating config files.

    Backups are created before any config files are modified.
    """
    console.print()

    manager = TenantManager()

    # If no username provided, show interactive selection
    if not username:
        if yes:
            print_error("Username is required in non-interactive mode")
            raise typer.Exit(1)

        tenants = manager.list_all_tenants()
        if not tenants:
            print_error("No tenants found")
            raise typer.Exit(1)

        console.print("[bold]Select tenant to remove[/bold]")
        console.print()

        for i, tenant in enumerate(tenants, 1):
            ips = ", ".join(tenant["ips"]) if tenant["ips"] else "no IPs"
            console.print(f"  [bold cyan]{i}[/bold cyan]. {tenant['username']}  [dim]({ips})[/dim]")

        console.print()

        while True:
            choice = Prompt.ask("Choice")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(tenants):
                    username = tenants[idx]["username"]
                    break
            except ValueError:
                # User might have typed the username directly
                matching = [t for t in tenants if t["username"] == choice]
                if matching:
                    username = choice
                    break

            console.print("[red]Invalid choice. Please enter a number or username.[/red]")

        console.print()

    # Check if tenant exists
    info = manager.get_tenant_info(username)
    if not info:
        print_error(f"Tenant '{username}' not found")
        raise typer.Exit(1)

    vm_name = info.get("vm_name", get_vm_name(username, 1))
    print_info(f"Removing tenant: {username}")

    if info["ips"]:
        print_info(f"IPs: {', '.join(info['ips'])}")

    # Determine what actions to take (from flags)
    run_ansible = not skip_ansible

    # === COLLECT ALL USER INPUT UPFRONT ===

    # 1. Find and select VMs to delete
    tenant_vms = get_tenant_vms(username)
    selected_vms = []

    if tenant_vms:
        console.print()
        if not yes:
            selected_vms = prompt_vm_selection(tenant_vms)
        else:
            # Non-interactive: select all VMs
            selected_vms = tenant_vms
            for vm in selected_vms:
                console.print(f"  [green]✓[/green] {vm}")

        if selected_vms:
            print_info(f"VMs to delete: {len(selected_vms)}")
        else:
            print_warning("No VMs selected for deletion")
    else:
        print_warning(f"No VMs found matching '{username}' in restsrv01.yaml")

    # 2. Show config file changes and ask about updating them
    config_changes = manager.remove_tenant(username, vm_names=selected_vms, dry_run=True)
    if config_changes:
        # Add admin inventories that will be modified
        for inv_file in BASE_DIR.glob("inventory-*.yaml"):
            # Show removal for each selected VM
            for selected_vm in selected_vms:
                config_changes.append((inv_file.name, f"Remove '{selected_vm}' if present"))

    should_update_config = not skip_config
    if config_changes and not skip_config:
        console.print()
        print_changes_panel(config_changes)

        if not yes:
            console.print()
            should_update_config = Confirm.ask(
                "[bold]Update configuration files?[/bold]",
                default=True,
            )

    # 3. Get admin user for ansible
    if run_ansible and selected_vms:
        if not admin:
            if yes:
                admins = get_admin_users()
                admin = admins[0] if admins else "alessandro"
            else:
                console.print()
                admin = prompt_admin_user()

        print_info(f"Operating as admin: [bold]{admin}[/bold]")

    # === EXECUTE ACTIONS ===

    # Run ansible removal playbook FIRST (default behavior)
    if run_ansible and selected_vms:
        console.print()
        ansible_success = run_ansible_remove_for_user(username, admin, selected_vms)
        if not ansible_success:
            print_warning("Ansible playbook failed")
            if should_update_config and not yes:
                # Ask if they still want to update config files
                console.print()
                if not Confirm.ask("[bold]Continue with config file cleanup anyway?[/bold]", default=False):
                    print_warning("Aborted")
                    raise typer.Exit(1)
        console.print()
    elif run_ansible and not selected_vms:
        print_info("Skipping ansible (no VMs selected)")

    # Update configuration files
    if should_update_config:
        console.print("[dim]Removing tenant from configuration files...[/dim]")
        manager.remove_tenant(username, vm_names=selected_vms, dry_run=False)

        # Remove from admin inventories (for each selected VM)
        for selected_vm in selected_vms:
            modified_invs = remove_from_admin_inventories(selected_vm)
            for inv_path in modified_invs:
                print_success(f"Removed from {inv_path.name}")

        print_success(f"Configuration files updated for '{username}'")
    else:
        print_info("Skipped configuration file updates")

    print_success(f"Tenant '{username}' removal completed")


@app.command()
def apply(
    username: str = typer.Argument(..., help="Username of the tenant to provision"),
    admin: Optional[str] = typer.Option(None, "--admin", "-A", help="Admin user for SSH/ansible operations"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
) -> None:
    """Run ansible playbook for an existing tenant.

    Use this to:
    - Provision a VM for a user already in the configuration
    - Re-run provisioning after configuration changes
    - Apply updates to an existing tenant's VM

    Uses a minimal inventory for fast execution.
    """
    console.print()

    manager = TenantManager()

    # Check if tenant exists
    info = manager.get_tenant_info(username)
    if not info:
        print_error(f"Tenant '{username}' not found")
        print_info("Use 'p4tenant add user' to create a new tenant first")
        raise typer.Exit(1)

    vm_name = info.get("vm_name", get_vm_name(username, 1))
    print_info(f"Tenant: {username} (VM: {vm_name})")

    if info["ips"]:
        print_info(f"IPs: {', '.join(info['ips'])}")

    # Show configuration status
    status_parts = []
    if info["in_restart_users"]:
        status_parts.append("[green]restart_users[/green]")
    if info["in_vms_list"]:
        status_parts.append("[green]vms list[/green]")
    if info["in_inventory"]:
        status_parts.append("[green]inventory[/green]")
    if info["has_host_vars"]:
        status_parts.append("[green]host_vars[/green]")

    if status_parts:
        print_info(f"Config: {', '.join(status_parts)}")

    # Check for missing configuration
    missing = []
    if not info["in_restart_users"]:
        missing.append("restart_users")
    if not info["in_vms_list"]:
        missing.append("vms list")
    if not info["in_inventory"]:
        missing.append("inventory")
    if not info["has_host_vars"]:
        missing.append("host_vars")

    if missing:
        print_warning(f"Missing config: {', '.join(missing)}")
        print_info("Consider running 'p4tenant add user' to complete the configuration")

    # Get admin user
    if not admin:
        if yes:
            admins = get_admin_users()
            admin = admins[0] if admins else "alessandro"
        else:
            console.print()
            admin = prompt_admin_user()

    print_info(f"Operating as admin: [bold]{admin}[/bold]")

    # Confirm
    if not yes:
        console.print()
        if not Confirm.ask(f"[bold]Run ansible-playbook for '{username}'?[/bold]", default=True):
            print_warning("Aborted")
            raise typer.Exit(0)

    # Run ansible
    console.print()
    run_ansible_for_vm(vm_name, admin)


@app.command(name="list")
def list_tenants() -> None:
    """List all tenants and their configuration status.

    Shows a table with:
    - Username and VM name
    - Allocated IP addresses
    - Configuration status (users, vms, inventory, host_vars)
    """
    console.print()

    manager = TenantManager()
    tenants = manager.list_all_tenants()

    if not tenants:
        print_info("No tenants found")
        raise typer.Exit(0)

    table = create_tenant_table(tenants)
    console.print(table)
    console.print()
    console.print("[dim]Status legend: users=restart_users, vms=restsrv01, inv=inventory, host=host_vars file[/dim]")
    console.print(f"[dim]Total: {len(tenants)} tenant(s)[/dim]")


@app.command(name="ip-status")
def ip_status() -> None:
    """Show IP allocation status.

    Displays:
    - Available IP range for VMs
    - Reserved and used IPs
    - Next available IP pair
    - Current IP-to-VM assignments
    """
    console.print()

    status = get_ip_status()
    table = create_ip_status_table(status)
    console.print(table)

    # Show IP to VM mapping
    console.print()
    ip_to_vm = get_ip_to_vm_mapping()

    if ip_to_vm:
        from rich.table import Table

        mapping_table = Table(title="IP Assignments")
        mapping_table.add_column("IP Address", style="yellow")
        mapping_table.add_column("VM Name", style="cyan")

        for ip in sorted(ip_to_vm.keys(), key=lambda x: int(x.split(".")[-1])):
            mapping_table.add_row(ip, ip_to_vm[ip])

        console.print(mapping_table)


def run_ansible_for_vm(vm_name: str, admin_user: str) -> None:
    """Run ansible-playbook for a single VM using minimal inventory.

    This creates a temporary inventory with only the necessary hosts,
    making ansible execution much faster than running against all hosts.

    Args:
        vm_name: Name of the VM to provision
        admin_user: Admin username for SSH connections
    """
    playbook = BASE_DIR / "playbooks" / "adduser.yaml"

    # Create minimal inventory for this VM only
    console.print("[dim]Creating minimal inventory for faster execution...[/dim]")
    temp_inventory = create_minimal_inventory(vm_name, admin_user)

    try:
        cmd = [
            "ansible-playbook",
            str(playbook),
            "-i",
            str(temp_inventory),
        ]

        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        console.print(f"[dim]Inventory: {temp_inventory}[/dim]")
        console.print()

        result = subprocess.run(cmd, cwd=str(BASE_DIR))

        if result.returncode != 0:
            print_error(f"ansible-playbook exited with code {result.returncode}")
        else:
            print_success("ansible-playbook completed successfully")

    except FileNotFoundError:
        print_error("ansible-playbook not found. Is Ansible installed?")
    except Exception as e:
        print_error(f"Error running ansible-playbook: {e}")
    finally:
        # Clean up temporary inventory
        try:
            temp_inventory.unlink()
        except Exception:
            pass


def run_ansible_remove_for_user(username: str, admin_user: str, vms_to_delete: list[str]) -> bool:
    """Run ansible-playbook to remove a user and their VMs from remote systems.

    This runs the removeuser.yaml playbook with the username and VMs passed as
    extra variables, bypassing the interactive prompts.

    Args:
        username: Username of the tenant to remove
        admin_user: Admin username for SSH connections
        vms_to_delete: List of VM names to delete

    Returns:
        True if playbook succeeded, False otherwise
    """
    import json

    playbook = BASE_DIR / "playbooks" / "removeuser.yaml"

    if not playbook.exists():
        print_error(f"Playbook not found: {playbook}")
        return False

    # Create minimal inventory for the removal operation
    console.print("[dim]Creating minimal inventory for ansible execution...[/dim]")
    temp_inventory = create_minimal_inventory(
        vm_name=vms_to_delete[0] if vms_to_delete else f"restvm-{username}-01",
        admin_user=admin_user,
    )

    try:
        # Pass VMs as JSON list
        vms_json = json.dumps(vms_to_delete)

        cmd = [
            "ansible-playbook",
            str(playbook),
            "-i",
            str(temp_inventory),
            "-e",
            f"user_to_delete={username}",
            "-e",
            "confirm_deletion=DELETE",
            "-e",
            f"vms_to_delete={vms_json}",
        ]

        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        console.print()

        result = subprocess.run(cmd, cwd=str(BASE_DIR))

        if result.returncode != 0:
            print_error(f"ansible-playbook exited with code {result.returncode}")
            return False
        else:
            print_success("ansible-playbook completed successfully")
            return True

    except FileNotFoundError:
        print_error("ansible-playbook not found. Is Ansible installed?")
        return False
    except Exception as e:
        print_error(f"Error running ansible-playbook: {e}")
        return False
    finally:
        # Clean up temporary inventory
        try:
            temp_inventory.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    app()
