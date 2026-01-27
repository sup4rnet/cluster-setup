"""Rich console helpers for terminal UI."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_success(message: str) -> None:
    """Print a success message with checkmark."""
    console.print(f"[green]\u2713[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message with X."""
    console.print(f"[red]\u2717[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]\u2139[/blue] {message}")


def print_step(number: int, message: str) -> None:
    """Print a numbered step."""
    console.print(f"  [dim]{number}.[/dim] {message}")


def print_changes_panel(changes: list[tuple[str, str]]) -> None:
    """Print a panel showing planned changes.

    Args:
        changes: List of (file_path, description) tuples
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Num", style="dim")
    table.add_column("File", style="cyan")
    table.add_column("Change", style="white")

    for i, (file_path, description) in enumerate(changes, 1):
        table.add_row(f"{i}.", file_path, description)

    panel = Panel(table, title="[bold]Changes to apply[/bold]", border_style="blue")
    console.print(panel)


def create_tenant_table(tenants: list[dict]) -> Table:
    """Create a table showing tenant information.

    Args:
        tenants: List of tenant info dictionaries

    Returns:
        Rich Table object
    """
    table = Table(title="P4-RESTART Tenants")
    table.add_column("Username", style="cyan")
    table.add_column("VMs", style="green")
    table.add_column("IPs", style="yellow")
    table.add_column("Status", style="white")

    for tenant in tenants:
        status_parts = []
        if tenant.get("in_restart_users"):
            status_parts.append("[green]\u2713 users[/green]")
        else:
            status_parts.append("[red]\u2717 users[/red]")

        if tenant.get("in_vms_list"):
            status_parts.append("[green]\u2713 vms[/green]")
        else:
            status_parts.append("[red]\u2717 vms[/red]")

        if tenant.get("in_inventory"):
            status_parts.append("[green]\u2713 inv[/green]")
        else:
            status_parts.append("[red]\u2717 inv[/red]")

        if tenant.get("has_host_vars"):
            status_parts.append("[green]\u2713 host[/green]")
        else:
            status_parts.append("[red]\u2717 host[/red]")

        status = " ".join(status_parts)
        ips = "\n".join(tenant.get("ips", []))

        # Show VM names (or count if multiple)
        vm_names = tenant.get("vm_names", [])
        if len(vm_names) <= 1:
            vms_display = tenant.get("vm_name", "")
        else:
            vms_display = "\n".join(vm_names)

        table.add_row(
            tenant.get("username", ""),
            vms_display,
            ips,
            status,
        )

    return table


def create_ip_status_table(status: dict) -> Table:
    """Create a table showing IP allocation status.

    Args:
        status: IP status dictionary from ip_allocator

    Returns:
        Rich Table object
    """
    table = Table(title="IP Allocation Status")
    table.add_column("Category", style="cyan")
    table.add_column("Value", style="white")

    start, end = status["total_range"]
    table.add_row("IP Range", f"10.10.0.{start} - 10.10.0.{end}")
    table.add_row("Reserved IPs", ", ".join(f".{ip}" for ip in status["reserved"]))
    table.add_row("Used IPs", ", ".join(f".{ip}" for ip in status["used"]) or "None")
    table.add_row("Available IPs", str(status["available_count"]))
    table.add_row("Available Pairs", str(status["available_pairs_count"]))

    if status["next_pair"]:
        ip1, ip2 = status["next_pair"]
        table.add_row("Next Available Pair", f"10.10.0.{ip1}, 10.10.0.{ip2}")
    else:
        table.add_row("Next Available Pair", "[red]None available[/red]")

    return table
