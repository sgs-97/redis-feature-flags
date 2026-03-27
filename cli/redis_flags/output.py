from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from datetime import datetime, timezone

console = Console()


def format_enabled(value: str) -> str:
    """Format enabled field as colored yes/no."""
    if value == "1":
        return "[green]yes[/green]"
    return "[red]no[/red]"


def format_rollout(value: str) -> str:
    """Format rollout as percentage string."""
    return f"{value}%"

def format_timestamp(value: str) -> str:
    if not value or value == "0":
        return "never"
    try:
        dt = datetime.fromtimestamp(int(value), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OSError):
        return value


def print_flags_table(flags: List[Dict[str, Any]]) -> None:
    """
    Print a list of flags as a rich table.
    Used by: redis-flags list
    """
    if not flags:
        console.print("[yellow]No flags found.[/yellow]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Flag", style="bold")
    table.add_column("Enabled")
    table.add_column("Rollout")
    table.add_column("Updated by")
    table.add_column("Updated at")

    for flag in flags:
        table.add_row(
            flag.get("name", ""),
            format_enabled(flag.get("enabled", "0")),
            format_rollout(flag.get("rollout", "0")),
            flag.get("updated_by", ""),
            format_timestamp(flag.get("updated_at", "0")),
        )

    console.print(table)


def print_flag_panel(
    flag: Dict[str, Any],
    users: List[str],
    cohorts: List[str],
) -> None:
    """
    Print detailed flag info as a rich panel.
    Used by: redis-flags inspect {flag_name}
    """
    lines = []
    lines.append(f"[bold]Enabled[/bold]      {format_enabled(flag.get('enabled', '0'))}")
    lines.append(f"[bold]Rollout[/bold]      {format_rollout(flag.get('rollout', '0'))}")
    lines.append(f"[bold]Version[/bold]      {flag.get('flag_version', '1')}")
    lines.append(f"[bold]Expires[/bold]      {format_timestamp(flag.get('expires_at', '0'))}")
    lines.append(f"[bold]Created by[/bold]   {flag.get('created_by', '')}")
    lines.append(f"[bold]Created at[/bold]   {format_timestamp(flag.get('created_at', '0'))}")
    lines.append(f"[bold]Updated by[/bold]   {flag.get('updated_by', '')}")
    lines.append(f"[bold]Updated at[/bold]   {format_timestamp(flag.get('updated_at', '0'))}")

    if users:
        lines.append("")
        lines.append("[bold]Users[/bold]")
        for user in sorted(users):
            lines.append(f"  {user}")
    else:
        lines.append("")
        lines.append("[bold]Users[/bold]      [dim]none[/dim]")

    if cohorts:
        lines.append("")
        lines.append("[bold]Cohorts[/bold]")
        for cohort in sorted(cohorts):
            lines.append(f"  {cohort}")
    else:
        lines.append("")
        lines.append("[bold]Cohorts[/bold]    [dim]none[/dim]")

    console.print(Panel(
        "\n".join(lines),
        title=f"[bold cyan]{flag.get('name', '')}[/bold cyan]",
        expand=False,
    ))


def print_cohorts_table(cohorts: List[str]) -> None:
    """
    Print a list of cohorts as a rich table.
    Used by: redis-flags list-cohorts
    """
    if not cohorts:
        console.print("[yellow]No cohorts found.[/yellow]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Cohort", style="bold")

    for cohort in sorted(cohorts):
        table.add_row(cohort)

    console.print(table)


def print_cohort_panel(cohort_name: str, members: List[str]) -> None:
    """
    Print detailed cohort info as a rich panel.
    Used by: redis-flags inspect-cohort {cohort_name}
    """
    lines = []
    lines.append(f"[bold]Members[/bold]   {len(members)}")

    if members:
        lines.append("")
        for member in sorted(members):
            lines.append(f"  {member}")
    else:
        lines.append("")
        lines.append("  [dim]no members[/dim]")

    console.print(Panel(
        "\n".join(lines),
        title=f"[bold cyan]{cohort_name}[/bold cyan]",
        expand=False,
    ))


def print_success(message: str) -> None:
    """Print a green success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print a red error message."""
    console.print(f"[red]Error:[/red] {message}")


def print_warning(message: str) -> None:
    """Print a yellow warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")