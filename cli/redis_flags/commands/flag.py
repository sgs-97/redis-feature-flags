from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from ..config import get_env, get_redis_url
from ..connection import get_client
from ..output import (
    print_flags_table, print_flag_panel,
    print_success, print_error
)
from redis_feature_flags import FeatureFlags
from redis_feature_flags.exceptions import (
    FlagNotFoundError, InvalidRolloutError
)

import getpass

app = typer.Typer()
console = Console()


def get_flags(env: Optional[str], redis_url: Optional[str]) -> FeatureFlags:
    """Build FeatureFlags instance from CLI options."""
    resolved_env = get_env(env)
    resolved_url = get_redis_url(redis_url)
    client = get_client(resolved_url)
    return FeatureFlags(client, env=resolved_env)


@app.command("create")
def create(
    flag_name: str = typer.Argument(..., help="Flag name"),
    rollout: int = typer.Option(0, "--rollout", "-r", help="Rollout percentage 0-100"),
    created_by: str = typer.Option(getpass.getuser(), "--created-by", help="Who is creating this flag"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Create a new feature flag.

    Example:
        redis-flags create dark_mode
        redis-flags create dark_mode --rollout 10
        redis-flags create dark_mode --rollout 10 --created-by alice
    """
    try:
        flags = get_flags(env, redis_url)
        flags.create(flag_name, rollout=rollout, created_by=created_by)
        print_success(f"Created flag [bold]{flag_name}[/bold] (rollout: {rollout}%)")
    except InvalidRolloutError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("enable")
def enable(
    flag_name: str = typer.Argument(..., help="Flag name"),
    updated_by: str = typer.Option(getpass.getuser(), "--updated-by", help="Who is enabling this flag"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Enable a feature flag.

    Example:
        redis-flags enable dark_mode
        redis-flags enable dark_mode --updated-by alice
    """
    try:
        flags = get_flags(env, redis_url)
        flags.enable(flag_name, updated_by=updated_by)
        print_success(f"Enabled [bold]{flag_name}[/bold]")
    except FlagNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("disable")
def disable(
    flag_name: str = typer.Argument(..., help="Flag name"),
    updated_by: str = typer.Option(getpass.getuser(), "--updated-by", help="Who is disabling this flag"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Disable a feature flag — instant kill switch.

    Example:
        redis-flags disable dark_mode
        redis-flags disable dark_mode --updated-by alice
    """
    try:
        flags = get_flags(env, redis_url)
        flags.disable(flag_name, updated_by=updated_by)
        print_success(f"Disabled [bold]{flag_name}[/bold]")
    except FlagNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("set-rollout")
def set_rollout(
    flag_name: str = typer.Argument(..., help="Flag name"),
    percent: int = typer.Argument(..., help="Rollout percentage 0-100"),
    updated_by: str = typer.Option(getpass.getuser(), "--updated-by", help="Who is updating this flag"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Set the rollout percentage for a flag.

    Example:
        redis-flags set-rollout dark_mode 50
        redis-flags set-rollout dark_mode 100
    """
    try:
        flags = get_flags(env, redis_url)
        flags.set_rollout(flag_name, percent, updated_by=updated_by)
        print_success(f"Rollout for [bold]{flag_name}[/bold] set to {percent}%")
    except (FlagNotFoundError, InvalidRolloutError) as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("delete")
def delete(
    flag_name: str = typer.Argument(..., help="Flag name"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Delete a feature flag permanently.

    Example:
        redis-flags delete dark_mode
        redis-flags delete dark_mode --yes
    """
    if not confirm:
        typer.confirm(
            f"Delete flag '{flag_name}'? This cannot be undone.",
            abort=True,
        )
    try:
        flags = get_flags(env, redis_url)
        flags.delete(flag_name)
        print_success(f"Deleted flag [bold]{flag_name}[/bold]")
    except FlagNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("list")
def list_flags(
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    List all feature flags.

    Example:
        redis-flags list
        redis-flags --env prod list
    """
    flags = get_flags(env, redis_url)
    flag_names = flags.list_flags()
    flag_data = []
    for name in flag_names:
        data = flags.get(name)
        data["name"] = name
        flag_data.append(data)
    print_flags_table(flag_data)


@app.command("inspect")
def inspect(
    flag_name: str = typer.Argument(..., help="Flag name"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Show detailed information about a flag including users and cohorts.

    Example:
        redis-flags inspect dark_mode
    """
    try:
        flags = get_flags(env, redis_url)
        resolved_env = get_env(env)
        resolved_url = get_redis_url(redis_url)
        client = get_client(resolved_url)

        from redis_feature_flags.schema import SchemaKeys
        schema = SchemaKeys(env=resolved_env)

        data = flags.get(flag_name)
        data["name"] = flag_name

        users = [
            u.decode() for u in
            client.smembers(schema.flag_users(flag_name))
        ]
        cohorts = [
            c.decode() for c in
            client.smembers(schema.flag_cohorts(flag_name))
        ]
        print_flag_panel(data, users, cohorts)
    except FlagNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)