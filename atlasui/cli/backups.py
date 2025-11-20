"""
CLI commands for managing Atlas backups.
"""

import typer
from rich.console import Console
from rich.table import Table

from atlasui.client import AtlasClient

app = typer.Typer()
console = Console()


@app.command("list")
def list_snapshots(
    project_id: str = typer.Argument(..., help="Project ID"),
    cluster_name: str = typer.Argument(..., help="Cluster name"),
) -> None:
    """List all backup snapshots for a cluster."""
    try:
        with console.status(
            f"[bold green]Fetching snapshots for cluster {cluster_name}..."
        ):
            with AtlasClient() as client:
                response = client.get(
                    f"/groups/{project_id}/clusters/{cluster_name}/backup/snapshots"
                )

        snapshots = response.get("results", [])

        if not snapshots:
            console.print("[yellow]No snapshots found.[/yellow]")
            return

        table = Table(title=f"Snapshots for {cluster_name}")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="blue")
        table.add_column("Created", style="magenta")

        for snapshot in snapshots:
            table.add_row(
                snapshot.get("id", "N/A"),
                snapshot.get("snapshotType", "N/A"),
                snapshot.get("status", "N/A"),
                snapshot.get("createdAt", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("schedule")
def get_schedule(
    project_id: str = typer.Argument(..., help="Project ID"),
    cluster_name: str = typer.Argument(..., help="Cluster name"),
) -> None:
    """Get backup schedule for a cluster."""
    try:
        with console.status(
            f"[bold green]Fetching backup schedule for {cluster_name}..."
        ):
            with AtlasClient() as client:
                schedule = client.get(
                    f"/groups/{project_id}/clusters/{cluster_name}/backup/schedule"
                )

        console.print("\n[bold cyan]Backup Schedule[/bold cyan]")
        console.print(f"Cluster: {cluster_name}")

        if "policies" in schedule:
            for policy in schedule["policies"]:
                console.print(f"\nPolicy ID: {policy.get('id')}")
                for item in policy.get("policyItems", []):
                    console.print(
                        f"  - Frequency: {item.get('frequencyType')} "
                        f"every {item.get('frequencyInterval')} "
                        f"({item.get('retentionUnit')}: {item.get('retentionValue')})"
                    )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
