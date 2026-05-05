from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from .config import read_config, write_config, get_env, get_redis_url
from .connection import get_client
from .commands import flag, user, cohort, history

app = typer.Typer(
    name="redis-flags",
    help="Manage Redis feature flags from your terminal.",
    no_args_is_help=True,
)

app.add_typer(flag.app,    name="", help="")
app.add_typer(user.app,    name="", help="")
app.add_typer(cohort.app,  name="", help="")
app.add_typer(history.app, name="", help="")

console = Console()


@app.command("use")
def use_env(
    env: str = typer.Argument(..., help="Environment to use e.g. prod staging dev"),
):
    """
    Set the active environment for all subsequent commands.

    Example:
        redis-flags use prod
        redis-flags use staging
        redis-flags use dev
    """
    config = read_config()
    config["env"] = env
    write_config(config)
    console.print(f"[green]✓[/green] Environment set to [bold]{env}[/bold]")


@app.command("status")
def status(
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL"),
):
    """
    Show current context — environment and Redis connection.

    Example:
        redis-flags status
    """
    config = read_config()
    env = config.get("env", "[red]not set[/red]")
    url = get_redis_url(redis_url)

    connected = False
    try:
        client = get_client(url)
        connected = True
    except SystemExit:
        pass

    connection_status = "[green]connected ✓[/green]" if connected else "[red]unreachable ✗[/red]"

    lines = [
        f"[bold]Environment[/bold]   {env}",
        f"[bold]Redis URL[/bold]     {url}",
        f"[bold]Redis[/bold]         {connection_status}",
    ]

    console.print(Panel(
        "\n".join(lines),
        title="[bold cyan]Current context[/bold cyan]",
        expand=False,
    ))