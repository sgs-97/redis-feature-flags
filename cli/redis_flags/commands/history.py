from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command("history")
def history(
    flag_name: str = typer.Argument(..., help="Flag name"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Show version history for a flag.

    Example:
        redis-flags history dark_mode
    """
    console.print("[yellow]History coming in v1.1[/yellow]")


@app.command("rollback")
def rollback(
    flag_name: str = typer.Argument(..., help="Flag name"),
    version: int = typer.Option(..., "--version", "-v", help="Version to roll back to"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Roll back a flag to a previous version.

    Example:
        redis-flags rollback dark_mode --version 2
    """
    console.print("[yellow]Rollback coming in v1.1[/yellow]")