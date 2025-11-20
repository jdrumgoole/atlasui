"""
Main CLI application using Typer.
"""

import typer
from rich.console import Console
from rich.table import Table

from atlasui import __version__
from atlasui.cli import projects, clusters, alerts, backups

# Create main app
app = typer.Typer(
    name="atlasui",
    help="MongoDB Atlas Administration CLI",
    add_completion=True,
)

# Create console for rich output
console = Console()

# Add subcommands
app.add_typer(projects.app, name="projects", help="Manage Atlas projects")
app.add_typer(clusters.app, name="clusters", help="Manage Atlas clusters")
app.add_typer(alerts.app, name="alerts", help="Manage Atlas alerts")
app.add_typer(backups.app, name="backups", help="Manage Atlas backups")


@app.command()
def version() -> None:
    """Display the version of AtlasUI."""
    console.print(f"AtlasUI version: {__version__}", style="bold green")


@app.command()
def info() -> None:
    """Display Atlas API connection information."""
    from atlasui.config import settings
    from atlasui.client import AtlasClient

    table = Table(title="Atlas API Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Base URL", settings.atlas_base_url)
    table.add_row("API Version", settings.atlas_api_version)
    table.add_row("Public Key", settings.atlas_public_key[:8] + "..." if settings.atlas_public_key else "Not set")
    table.add_row("Timeout", f"{settings.timeout}s")

    console.print(table)

    # Test connection
    try:
        with console.status("[bold green]Testing Atlas API connection..."):
            with AtlasClient() as client:
                root = client.get_root()
                console.print("\n[bold green]✓[/bold green] Successfully connected to Atlas API", style="green")
    except Exception as e:
        console.print(f"\n[bold red]✗[/bold red] Failed to connect: {e}", style="red")


if __name__ == "__main__":
    app()
