"""
CLI commands for managing Atlas alerts.
"""

import typer
from rich.console import Console
from rich.table import Table

from atlasui.client import AtlasClient

app = typer.Typer()
console = Console()


@app.command("list")
def list_alerts(
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """List all alerts for a project."""
    try:
        with console.status(f"[bold green]Fetching alerts for project {project_id}..."):
            with AtlasClient() as client:
                response = client.get(f"/groups/{project_id}/alerts")

        alerts = response.get("results", [])

        if not alerts:
            console.print("[yellow]No alerts found.[/yellow]")
            return

        table = Table(title=f"Alerts for Project {project_id}")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="blue")
        table.add_column("Created", style="magenta")

        for alert in alerts:
            table.add_row(
                alert.get("id", "N/A"),
                alert.get("eventTypeName", "N/A"),
                alert.get("status", "N/A"),
                alert.get("created", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
