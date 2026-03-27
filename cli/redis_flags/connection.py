from __future__ import annotations

import redis
from rich.console import Console

console = Console()


def get_client(redis_url: str) -> redis.Redis:
    """
    Create and verify a Redis client connection.

    Args:
        redis_url: Full Redis URL e.g. redis://localhost:6379
                   Supports auth: redis://:password@host:6379

    Returns:
        Connected Redis client.

    Raises:
        SystemExit: if Redis is unreachable.
    """
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=False)
        client.ping()
        return client
    except redis.ConnectionError:
        console.print(f"\n[red]Error:[/red] Cannot connect to Redis at {redis_url}\n")
        console.print("  Start Redis locally:")
        console.print("    [cyan]brew services start redis[/cyan]       (macOS)")
        console.print("    [cyan]sudo systemctl start redis[/cyan]      (Linux)")
        console.print("    [cyan]docker run -p 6379:6379 redis[/cyan]   (Docker)\n")
        console.print("  Or set a custom Redis URL:")
        console.print("    [cyan]redis-flags --redis-url redis://your-host:6379 list[/cyan]\n")
        raise SystemExit(1)
    except redis.AuthenticationError:
        console.print(f"\n[red]Error:[/red] Redis authentication failed.\n")
        console.print("  Provide credentials in the URL:")
        console.print("    [cyan]redis-flags --redis-url redis://:password@host:6379 list[/cyan]\n")
        raise SystemExit(1)