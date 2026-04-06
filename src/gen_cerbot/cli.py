"""CLI entry point for gen_cerbot using Typer."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from rich.console import Console

from gen_cerbot.core.exceptions import RootExecutionError
from gen_cerbot.domain.models import ServerType

app = typer.Typer(
    name="gen-cerbot",
    help="Automates TLS/SSL certificate configuration for web servers using Let's Encrypt/Certbot.",
    no_args_is_help=False,
)
console = Console()


def _check_not_root() -> None:
    """Reject execution as root."""
    if os.geteuid() == 0:
        raise RootExecutionError()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    lang: Annotated[
        str | None,
        typer.Option("--lang", help="Force language (en|es)."),
    ] = None,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show version and exit."),
    ] = False,
) -> None:
    """Main entry point. Without subcommands, launches interactive mode."""
    if version:
        console.print("gen-cerbot v1.0.0")
        raise typer.Exit()

    _check_not_root()

    if ctx.invoked_subcommand is None:
        console.print("[bold]Interactive mode not yet implemented.[/bold]")
        console.print("Use [green]gen-cerbot --help[/green] to see available commands.")


@app.command()
def generate(
    domain: Annotated[
        str, typer.Option("--domain", "-d", help="Domain name (e.g., sub.example.com)")
    ],
    email: Annotated[
        str, typer.Option("--email", "-e", help="Email for Let's Encrypt registration")
    ],
    server: Annotated[
        ServerType, typer.Option("--server", "-s", help="Web server type")
    ] = ServerType.NGINX,
    port: Annotated[int, typer.Option("--port", "-p", help="Port of the backend service")] = 8000,
    project: Annotated[
        str, typer.Option("--project", help="Project name for config file naming")
    ] = "",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be done without applying")
    ] = False,
    staging: Annotated[
        bool, typer.Option("--staging", help="Use Let's Encrypt staging server")
    ] = False,
    skip_dns_check: Annotated[
        bool, typer.Option("--skip-dns-check", help="Skip pre-flight DNS validation")
    ] = False,
    no_interactive: Annotated[
        bool, typer.Option("--no-interactive", help="Disable prompts (for CI/CD)")
    ] = False,
) -> None:
    """Generate TLS/SSL certificate and configure the web server."""
    _check_not_root()
    console.print(f"[bold green]generate[/bold green] — domain={domain}, server={server.value}")
    console.print("[yellow]Not yet implemented. Coming in Phase 4/5.[/yellow]")


@app.command(name="list")
def list_certs() -> None:
    """List all managed certificates with status and expiration."""
    _check_not_root()
    console.print("[bold green]list[/bold green] — Listing managed certificates...")
    console.print("[yellow]Not yet implemented. Coming in Phase 5.[/yellow]")


@app.command()
def renew(
    domain: Annotated[
        str | None,
        typer.Option("--domain", "-d", help="Specific domain to renew (omit to renew all)"),
    ] = None,
) -> None:
    """Renew certificates (all or specific domain)."""
    _check_not_root()
    target = domain or "all"
    console.print(f"[bold green]renew[/bold green] — target={target}")
    console.print("[yellow]Not yet implemented. Coming in Phase 5.[/yellow]")


@app.command()
def remove(
    domain: Annotated[str, typer.Option("--domain", "-d", help="Domain to remove")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Remove certificate and server configuration for a domain."""
    _check_not_root()
    console.print(f"[bold green]remove[/bold green] — domain={domain}")
    console.print("[yellow]Not yet implemented. Coming in Phase 5.[/yellow]")


if __name__ == "__main__":
    app()
