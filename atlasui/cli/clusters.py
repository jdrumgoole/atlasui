"""
CLI commands for managing Atlas clusters.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import print_json
import json

from atlasui.client import AtlasClient

app = typer.Typer()
console = Console()


@app.command("list")
def list_clusters(
    project_id: str = typer.Argument(..., help="Project ID"),
    page: int = typer.Option(1, help="Page number"),
    limit: int = typer.Option(100, help="Items per page"),
) -> None:
    """List all clusters in a project."""
    try:
        with console.status(f"[bold green]Fetching clusters for project {project_id}..."):
            with AtlasClient() as client:
                response = client.list_clusters(
                    project_id=project_id, page_num=page, items_per_page=limit
                )

        clusters = response.get("results", [])
        total_count = response.get("totalCount", 0)

        if not clusters:
            console.print("[yellow]No clusters found.[/yellow]")
            return

        table = Table(title=f"Clusters in Project {project_id} (Total: {total_count})")
        table.add_column("Name", style="cyan")
        table.add_column("State", style="green")
        table.add_column("MongoDB Version", style="blue")
        table.add_column("Provider", style="magenta")
        table.add_column("Region", style="yellow")

        for cluster in clusters:
            provider_settings = cluster.get("providerSettings", {})
            table.add_row(
                cluster.get("name", "N/A"),
                cluster.get("stateName", "N/A"),
                cluster.get("mongoDBVersion", "N/A"),
                provider_settings.get("providerName", "N/A"),
                provider_settings.get("regionName", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("get")
def get_cluster(
    project_id: str = typer.Argument(..., help="Project ID"),
    cluster_name: str = typer.Argument(..., help="Cluster name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get details of a specific cluster."""
    try:
        with console.status(f"[bold green]Fetching cluster {cluster_name}..."):
            with AtlasClient() as client:
                cluster = client.get_cluster(project_id, cluster_name)

        if json_output:
            print_json(json.dumps(cluster))
        else:
            console.print("\n[bold cyan]Cluster Details[/bold cyan]")
            console.print(f"Name: {cluster.get('name')}")
            console.print(f"State: {cluster.get('stateName')}")
            console.print(f"MongoDB Version: {cluster.get('mongoDBVersion')}")
            console.print(f"Cluster Type: {cluster.get('clusterType')}")

            provider_settings = cluster.get("providerSettings", {})
            console.print(f"\nProvider: {provider_settings.get('providerName')}")
            console.print(f"Region: {provider_settings.get('regionName')}")
            console.print(f"Instance Size: {provider_settings.get('instanceSizeName')}")

            if "connectionStrings" in cluster:
                console.print(f"\nConnection String: {cluster['connectionStrings'].get('standard')}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_cluster(
    project_id: str = typer.Argument(..., help="Project ID"),
    cluster_name: str = typer.Argument(..., help="Cluster name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a cluster."""
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete cluster '{cluster_name}'? This cannot be undone."
        )
        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            raise typer.Exit()

    try:
        with console.status(f"[bold red]Deleting cluster {cluster_name}..."):
            with AtlasClient() as client:
                client.delete_cluster(project_id, cluster_name)

        console.print(f"[bold green]✓[/bold green] Cluster '{cluster_name}' deletion initiated.")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
