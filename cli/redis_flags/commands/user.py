from __future__ import annotations

from typing import Optional

import typer

from ..config import get_env, get_redis_url
from ..connection import get_client
from ..output import print_success, print_error
from redis_feature_flags import FeatureFlags
from redis_feature_flags.exceptions import FlagNotFoundError

app = typer.Typer()


def get_flags(env: Optional[str], redis_url: Optional[str]) -> FeatureFlags:
    resolved_env = get_env(env)
    resolved_url = get_redis_url(redis_url)
    client = get_client(resolved_url)
    return FeatureFlags(client, env=resolved_env)


@app.command("add-user")
def add_user(
    flag_name: str = typer.Argument(..., help="Flag name"),
    user_id: str = typer.Argument(..., help="User ID to add"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Add a user to a flag's allowlist.

    Example:
        redis-flags add-user dark_mode alice
    """
    try:
        flags = get_flags(env, redis_url)
        flags.add_user(flag_name, user_id)
        print_success(f"Added [bold]{user_id}[/bold] to flag [bold]{flag_name}[/bold]")
    except FlagNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("remove-user")
def remove_user(
    flag_name: str = typer.Argument(..., help="Flag name"),
    user_id: str = typer.Argument(..., help="User ID to remove"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Remove a user from a flag's allowlist.

    Example:
        redis-flags remove-user dark_mode alice
    """
    flags = get_flags(env, redis_url)
    flags.remove_user(flag_name, user_id)
    print_success(f"Removed [bold]{user_id}[/bold] from flag [bold]{flag_name}[/bold]")