from __future__ import annotations

from typing import Optional

import typer

from ..config import get_env, get_redis_url
from ..connection import get_client
from ..output import (
    print_cohorts_table, print_cohort_panel,
    print_success, print_error
)
from redis_feature_flags import FeatureFlags
from redis_feature_flags.exceptions import FlagNotFoundError

app = typer.Typer()


def get_flags(env: Optional[str], redis_url: Optional[str]) -> FeatureFlags:
    resolved_env = get_env(env)
    resolved_url = get_redis_url(redis_url)
    client = get_client(resolved_url)
    return FeatureFlags(client, env=resolved_env)


@app.command("create-cohort")
def create_cohort(
    cohort_name: str = typer.Argument(..., help="Cohort name"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Create a new cohort.

    Example:
        redis-flags create-cohort beta-testers
    """
    flags = get_flags(env, redis_url)
    flags.create_cohort(cohort_name)
    print_success(f"Created cohort [bold]{cohort_name}[/bold]")


@app.command("delete-cohort")
def delete_cohort(
    cohort_name: str = typer.Argument(..., help="Cohort name"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Delete a cohort and clean up all member reverse index entries.

    Example:
        redis-flags delete-cohort beta-testers
        redis-flags delete-cohort beta-testers --yes
    """
    if not confirm:
        typer.confirm(
            f"Delete cohort '{cohort_name}'? This cannot be undone.",
            abort=True,
        )
    flags = get_flags(env, redis_url)
    flags._cohorts.delete(cohort_name)
    print_success(f"Deleted cohort [bold]{cohort_name}[/bold]")


@app.command("add-to-cohort")
def add_to_cohort(
    cohort_name: str = typer.Argument(..., help="Cohort name"),
    user_id: str = typer.Argument(..., help="User ID to add"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Add a user to a cohort.

    Example:
        redis-flags add-to-cohort beta-testers alice
    """
    flags = get_flags(env, redis_url)
    flags.add_to_cohort(cohort_name, user_id)
    print_success(f"Added [bold]{user_id}[/bold] to cohort [bold]{cohort_name}[/bold]")


@app.command("remove-from-cohort")
def remove_from_cohort(
    cohort_name: str = typer.Argument(..., help="Cohort name"),
    user_id: str = typer.Argument(..., help="User ID to remove"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Remove a user from a cohort.

    Example:
        redis-flags remove-from-cohort beta-testers alice
    """
    flags = get_flags(env, redis_url)
    flags.remove_from_cohort(cohort_name, user_id)
    print_success(f"Removed [bold]{user_id}[/bold] from cohort [bold]{cohort_name}[/bold]")


@app.command("list-cohorts")
def list_cohorts(
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    List all cohorts.

    Example:
        redis-flags list-cohorts
    """
    flags = get_flags(env, redis_url)
    cohorts = flags._cohorts.list_cohorts()
    print_cohorts_table(cohorts)


@app.command("inspect-cohort")
def inspect_cohort(
    cohort_name: str = typer.Argument(..., help="Cohort name"),
    env: Optional[str] = typer.Option(None, "--env", help="Environment override"),
    redis_url: Optional[str] = typer.Option(None, "--redis-url", help="Redis URL override"),
):
    """
    Show all members of a cohort.

    Example:
        redis-flags inspect-cohort beta-testers
    """
    flags = get_flags(env, redis_url)
    members = flags._cohorts.get_members(cohort_name)
    print_cohort_panel(cohort_name, list(members))