from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

CONFIG_PATH = Path.home() / ".redis-flags.toml"


def read_config() -> dict:
    """
    Read config from ~/.redis-flags.toml.
    Returns empty dict if file does not exist.
    """
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def write_config(data: dict) -> None:
    """
    Write config to ~/.redis-flags.toml.
    Creates the file if it does not exist.
    """
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(data, f)


def get_env(env_override: Optional[str] = None) -> str:
    """
    Resolve the active environment.

    Priority:
        1. --env flag passed directly to command
        2. env saved in ~/.redis-flags.toml
        3. Neither set → raise error with helpful message

    Args:
        env_override: value from --env flag. None if not passed.

    Returns:
        The active environment string e.g. "prod", "staging", "dev"

    Raises:
        SystemExit: if no environment is set anywhere.
    """
    if env_override:
        return env_override

    config = read_config()
    env = config.get("env")

    if not env:
        from rich.console import Console
        console = Console()
        console.print("\n[red]Error:[/red] No environment set.\n")
        console.print("  Set a default environment:")
        console.print("    [cyan]redis-flags use prod[/cyan]")
        console.print("    [cyan]redis-flags use staging[/cyan]")
        console.print("    [cyan]redis-flags use dev[/cyan]\n")
        console.print("  Or specify for this command:")
        console.print("    [cyan]redis-flags --env prod list[/cyan]\n")
        raise SystemExit(1)

    return env


def get_redis_url(url_override: Optional[str] = None) -> str:
    """
    Resolve the Redis URL.

    Priority:
        1. --redis-url flag passed directly to command
        2. redis_url saved in ~/.redis-flags.toml
        3. Default: redis://localhost:6379

    Args:
        url_override: value from --redis-url flag. None if not passed.

    Returns:
        Redis URL string.
    """
    if url_override:
        return url_override

    config = read_config()
    return config.get("redis_url", "redis://localhost:6379")