"""Typer CLI commands for p4tenant."""

import subprocess
import sys
from typing import Optional

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.prompt import Confirm, Prompt

from .config import BASE_DIR, INVENTORY_FILE, get_vm_name
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


@app.command()
def add(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username for the new tenant"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address (optional)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    run_ansible: bool = typer.Option(False, "--run-ansible", "-a", help="Run ansible-playbook after adding"),
) -> None:
    """Add a new tenant interactively."""
    console.print()

    # Get username
    if not username:
        username = Prompt.ask("[bold]Enter username[/bold]")

    # Get email (skip prompt in non-interactive mode)
    if email is None and not yes:
        email = Prompt.ask("[bold]Enter email[/bold] [dim](optional)[/dim]", default="")

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
    errors = manager.validate_new_tenant(tenant.username)

    if errors:
        for error in errors:
            print_error(error)
        raise typer.Exit(1)

    print_success(f"Username '{tenant.username}' is available")

    # Allocate IPs
    ip_alloc = allocate_ip_pair()
    if not ip_alloc:
        print_error("No IP addresses available in the allowed range")
        raise typer.Exit(1)

    print_success(f"Allocated IPs: {ip_alloc.ip1}, {ip_alloc.ip2}")

    # Show planned changes
    console.print()
    changes = manager.add_tenant(tenant, ip_alloc, dry_run=True)
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
    manager.add_tenant(tenant, ip_alloc, dry_run=False)
    print_success("All changes applied successfully")

    # Run ansible if requested
    if run_ansible or (not yes and Confirm.ask("[bold]Run ansible-playbook?[/bold]", default=False)):
        console.print()
        run_ansible_playbook()


@app.command()
def remove(
    username: str = typer.Argument(..., help="Username of the tenant to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
) -> None:
    """Remove a tenant and all associated configuration."""
    console.print()

    manager = TenantManager()

    # Check if tenant exists
    info = manager.get_tenant_info(username)
    if not info:
        print_error(f"Tenant '{username}' not found")
        raise typer.Exit(1)

    vm_name = get_vm_name(username)
    print_info(f"Found tenant: {username} (VM: {vm_name})")

    if info["ips"]:
        print_info(f"IPs: {', '.join(info['ips'])}")

    # Show planned changes
    console.print()
    changes = manager.remove_tenant(username, dry_run=True)

    if not changes:
        print_warning("No configuration found to remove")
        raise typer.Exit(0)

    print_changes_panel(changes)

    # Confirm
    if not yes:
        console.print()
        console.print("[bold red]Warning:[/bold red] This action cannot be undone (backups will be created)")
        if not Confirm.ask(f"[bold]Remove tenant '{username}'?[/bold]", default=False):
            print_warning("Aborted")
            raise typer.Exit(0)

    # Apply changes
    console.print()
    console.print("[dim]Removing tenant...[/dim]")
    manager.remove_tenant(username, dry_run=False)
    print_success(f"Tenant '{username}' removed successfully")


@app.command(name="list")
def list_tenants() -> None:
    """List all tenants and their configuration status."""
    console.print()

    manager = TenantManager()
    tenants = manager.list_all_tenants()

    if not tenants:
        print_info("No tenants found")
        raise typer.Exit(0)

    table = create_tenant_table(tenants)
    console.print(table)
    console.print()
    console.print(f"[dim]Total: {len(tenants)} tenant(s)[/dim]")


@app.command(name="ip-status")
def ip_status() -> None:
    """Show IP allocation status."""
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


def run_ansible_playbook() -> None:
    """Run the ansible-playbook command."""
    playbook = BASE_DIR / "playbooks" / "adduser.yaml"
    inventory = INVENTORY_FILE

    cmd = [
        "ansible-playbook",
        str(playbook),
        "-i",
        str(inventory),
    ]

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    console.print()

    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR))
        if result.returncode != 0:
            print_error(f"ansible-playbook exited with code {result.returncode}")
        else:
            print_success("ansible-playbook completed successfully")
    except FileNotFoundError:
        print_error("ansible-playbook not found. Is Ansible installed?")
    except Exception as e:
        print_error(f"Error running ansible-playbook: {e}")


if __name__ == "__main__":
    app()
