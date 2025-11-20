"""
Interactive setup utility for AtlasUI service accounts.
"""

import sys
from pathlib import Path
from typing import Optional
import getpass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

from atlasui.client import ServiceAccountManager


console = Console()


def print_banner():
    """Print welcome banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║              AtlasUI Service Account Setup            ║
    ║                                                       ║
    ║        MongoDB Atlas OAuth 2.0 Configuration          ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_instructions():
    """Print setup instructions."""
    instructions = Panel.fit(
        """[bold]Before you begin, you need:[/bold]

1. MongoDB Atlas account access
2. Permission to create service accounts (Organization Owner or Project Owner)
3. Service account credentials from Atlas:
   • Client ID
   • Client Secret

[bold yellow]To get credentials:[/bold yellow]
1. Go to: https://cloud.mongodb.com
2. Click Organization Settings → Access Manager
3. Click "Service Accounts" tab
4. Click "Create Service Account"
5. Assign roles and save
6. Copy the [bold]Client ID[/bold] and [bold]Client Secret[/bold] (shown only once!)
        """,
        title="📋 Prerequisites",
        border_style="blue"
    )
    console.print(instructions)
    console.print()


def validate_client_id(client_id: str) -> bool:
    """Validate client ID format."""
    if not client_id or len(client_id.strip()) == 0:
        return False
    # Basic validation - client IDs are typically UUID-like
    if len(client_id) < 20:
        return False
    return True


def validate_client_secret(client_secret: str) -> bool:
    """Validate client secret format."""
    if not client_secret or len(client_secret.strip()) == 0:
        return False
    # Client secrets should be reasonably long
    if len(client_secret) < 10:
        return False
    return True


def get_credentials() -> tuple[str, str]:
    """Interactively get service account credentials."""
    console.print("\n[bold cyan]Step 1: Enter Service Account Credentials[/bold cyan]\n")

    # Get Client ID
    while True:
        client_id = Prompt.ask(
            "[bold]Client ID[/bold]",
            console=console
        ).strip()

        if validate_client_id(client_id):
            break
        else:
            console.print("[red]Invalid Client ID. Please try again.[/red]")

    # Get Client Secret
    while True:
        console.print("\n[bold]Client Secret[/bold] (input will be hidden)")
        client_secret = getpass.getpass("Enter Client Secret: ").strip()

        if not client_secret:
            console.print("[red]Client Secret cannot be empty. Please try again.[/red]")
            continue

        # Confirm secret
        console.print("[dim]Confirm Client Secret[/dim] (input will be hidden)")
        client_secret_confirm = getpass.getpass("Confirm Client Secret: ").strip()

        if client_secret != client_secret_confirm:
            console.print("[red]Secrets don't match. Please try again.[/red]")
            continue

        if validate_client_secret(client_secret):
            break
        else:
            console.print("[red]Invalid Client Secret. Please try again.[/red]")

    return client_id, client_secret


def get_output_path() -> Path:
    """Get output file path for credentials."""
    console.print("\n[bold cyan]Step 2: Choose Credentials File Location[/bold cyan]\n")

    default_path = "./service-account.json"

    path_str = Prompt.ask(
        "[bold]Credentials file path[/bold]",
        default=default_path,
        console=console
    ).strip()

    path = Path(path_str).expanduser().resolve()

    # Check if file already exists
    if path.exists():
        overwrite = Confirm.ask(
            f"[yellow]File {path} already exists. Overwrite?[/yellow]",
            default=False,
            console=console
        )
        if not overwrite:
            console.print("[red]Setup cancelled.[/red]")
            sys.exit(1)

    return path


def get_token_url() -> str:
    """Get OAuth token URL."""
    use_default = Confirm.ask(
        "\n[bold]Use default Atlas OAuth endpoint?[/bold]",
        default=True,
        console=console
    )

    if use_default:
        return "https://cloud.mongodb.com/api/oauth/token"

    return Prompt.ask(
        "[bold]OAuth Token URL[/bold]",
        default="https://cloud.mongodb.com/api/oauth/token",
        console=console
    ).strip()


def create_credentials_file(
    client_id: str,
    client_secret: str,
    output_path: Path,
    token_url: str
) -> None:
    """Create the credentials file."""
    console.print("\n[bold cyan]Step 3: Creating Credentials File[/bold cyan]\n")

    with console.status("[bold green]Writing credentials file..."):
        ServiceAccountManager.create_credentials_file(
            client_id=client_id,
            client_secret=client_secret,
            output_file=str(output_path),
            token_url=token_url
        )

    console.print(f"[green]✓[/green] Credentials saved to: [bold]{output_path}[/bold]")

    # Show file permissions
    import stat
    try:
        mode = output_path.stat().st_mode
        perms = stat.filemode(mode)
        console.print(f"[green]✓[/green] File permissions set to: [bold]{perms}[/bold]")
    except Exception:
        pass


def update_env_file(credentials_path: Path) -> None:
    """Update or create .env file with service account configuration."""
    console.print("\n[bold cyan]Step 4: Configure .env File[/bold cyan]\n")

    env_path = Path(".env")

    # Check if .env exists
    if env_path.exists():
        update = Confirm.ask(
            "[bold]Update existing .env file?[/bold]",
            default=True,
            console=console
        )
        if not update:
            console.print("[yellow]Skipping .env update.[/yellow]")
            return

    # Read existing .env if it exists
    existing_lines = []
    if env_path.exists():
        with env_path.open('r') as f:
            existing_lines = f.readlines()

    # Remove old service account settings
    new_lines = []
    skip_next = False
    for line in existing_lines:
        if any(key in line for key in [
            'ATLAS_AUTH_METHOD',
            'ATLAS_SERVICE_ACCOUNT',
        ]):
            continue
        new_lines.append(line)

    # Add new service account configuration
    config_lines = [
        "\n# MongoDB Atlas Service Account Configuration\n",
        "ATLAS_AUTH_METHOD=service_account\n",
        f"ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE={credentials_path.absolute()}\n",
    ]

    # Write updated .env
    with env_path.open('w') as f:
        f.writelines(new_lines)
        f.writelines(config_lines)

    console.print(f"[green]✓[/green] Updated .env file: [bold]{env_path.absolute()}[/bold]")


def test_connection() -> bool:
    """Test the Atlas API connection."""
    console.print("\n[bold cyan]Step 5: Testing Connection[/bold cyan]\n")

    test = Confirm.ask(
        "[bold]Test Atlas API connection now?[/bold]",
        default=True,
        console=console
    )

    if not test:
        return False

    try:
        from atlasui.client import AtlasClient

        with console.status("[bold green]Testing Atlas API connection..."):
            with AtlasClient(auth_method="service_account") as client:
                # Try to get root API info
                result = client.get_root()

        console.print("[green]✓[/green] [bold green]Successfully connected to Atlas API![/bold green]")

        # Try to list projects
        with console.status("[bold green]Fetching projects..."):
            with AtlasClient(auth_method="service_account") as client:
                projects = client.list_projects(items_per_page=5)

        if projects.get('results'):
            console.print(f"\n[green]✓[/green] Found {projects.get('totalCount', 0)} projects")

            # Show first few projects
            table = Table(title="Your Projects", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("ID", style="green")
            table.add_column("Org ID", style="blue")

            for project in projects['results'][:5]:
                table.add_row(
                    project.get('name', 'N/A'),
                    project.get('id', 'N/A'),
                    project.get('orgId', 'N/A')
                )

            console.print(table)

        return True

    except Exception as e:
        console.print(f"\n[red]✗[/red] [bold red]Connection failed:[/bold red] {str(e)}")
        console.print("\n[yellow]Troubleshooting:[/yellow]")
        console.print("  • Verify your Client ID and Client Secret are correct")
        console.print("  • Check that the service account exists in Atlas")
        console.print("  • Ensure the service account has proper permissions")
        console.print("  • Verify network connectivity to cloud.mongodb.com")
        return False


def print_next_steps(credentials_path: Path, connection_ok: bool):
    """Print next steps for the user."""
    console.print("\n")

    if connection_ok:
        next_steps = Panel.fit(
            """[bold green]Setup Complete! 🎉[/bold green]

[bold]Your service account is configured and working.[/bold]

[bold cyan]Next Steps:[/bold cyan]

1. Start the web server:
   [bold]inv run[/bold]
   Then visit: http://localhost:8000

2. Use the CLI:
   [bold]atlasui projects list[/bold]
   [bold]atlasui clusters list <project-id>[/bold]

3. See all commands:
   [bold]inv --list[/bold]
   [bold]atlasui --help[/bold]

[bold yellow]Security Reminders:[/bold yellow]
• Never commit service-account.json to Git
• Never commit .env to Git
• Rotate credentials every 90 days
            """,
            title="✓ Success",
            border_style="green"
        )
    else:
        next_steps = Panel.fit(
            f"""[bold yellow]Setup completed with warnings[/bold yellow]

Credentials file created: [bold]{credentials_path}[/bold]

However, the connection test failed. Please:

1. Verify credentials in Atlas:
   https://cloud.mongodb.com

2. Check service account permissions

3. Test manually:
   [bold]inv info[/bold]

4. Review documentation:
   [bold]inv docs[/bold]
            """,
            title="⚠ Action Required",
            border_style="yellow"
        )

    console.print(next_steps)


def interactive_setup() -> int:
    """
    Run interactive service account setup.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print_banner()
        print_instructions()

        # Confirm user is ready
        ready = Confirm.ask(
            "\n[bold]Do you have your service account credentials ready?[/bold]",
            default=True,
            console=console
        )

        if not ready:
            console.print("\n[yellow]Please get your credentials from Atlas first.[/yellow]")
            console.print("Visit: [bold]https://cloud.mongodb.com[/bold]")
            return 1

        # Get credentials
        client_id, client_secret = get_credentials()

        # Get output path
        output_path = get_output_path()

        # Get token URL
        token_url = get_token_url()

        # Create credentials file
        create_credentials_file(client_id, client_secret, output_path, token_url)

        # Update .env
        update_env_file(output_path)

        # Test connection
        connection_ok = test_connection()

        # Print next steps
        print_next_steps(output_path, connection_ok)

        return 0 if connection_ok else 0  # Return 0 even if test fails, credentials are saved

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled by user.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error during setup:[/red] {str(e)}")
        return 1


def main():
    """Main entry point."""
    sys.exit(interactive_setup())


if __name__ == "__main__":
    main()
