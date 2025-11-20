"""
CLI commands for managing Atlas projects.
"""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional

from atlasui.client import AtlasClient

app = typer.Typer()
console = Console()


@app.command("list")
def list_projects(
    page: int = typer.Option(1, help="Page number"),
    limit: int = typer.Option(100, help="Items per page"),
) -> None:
    """List all MongoDB Atlas projects."""
    try:
        with console.status("[bold green]Fetching projects..."):
            with AtlasClient() as client:
                response = client.list_projects(page_num=page, items_per_page=limit)

        projects = response.get("results", [])
        total_count = response.get("totalCount", 0)

        if not projects:
            console.print("[yellow]No projects found.[/yellow]")
            return

        table = Table(title=f"MongoDB Atlas Projects (Total: {total_count})")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="green")
        table.add_column("Org ID", style="blue")
        table.add_column("Created", style="magenta")

        for project in projects:
            table.add_row(
                project.get("name", "N/A"),
                project.get("id", "N/A"),
                project.get("orgId", "N/A"),
                project.get("created", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("get")
def get_project(project_id: str = typer.Argument(..., help="Project ID")) -> None:
    """Get details of a specific project."""
    try:
        with console.status(f"[bold green]Fetching project {project_id}..."):
            with AtlasClient() as client:
                project = client.get_project(project_id)

        console.print("\n[bold cyan]Project Details[/bold cyan]")
        console.print(f"Name: {project.get('name')}")
        console.print(f"ID: {project.get('id')}")
        console.print(f"Org ID: {project.get('orgId')}")
        console.print(f"Created: {project.get('created')}")

        if "clusterCount" in project:
            console.print(f"Cluster Count: {project.get('clusterCount')}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
