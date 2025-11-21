"""
Interactive configuration utility for AtlasUI.

Supports both API Key and Service Account authentication methods.
"""

import sys
from pathlib import Path
from typing import Optional, Literal
import getpass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

try:
    from atlasui.client import ServiceAccountManager
except ImportError:
    ServiceAccountManager = None


console = Console()

AuthMethod = Literal["api_key", "service_account"]


def print_banner():
    """Print welcome banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║                 AtlasUI Configuration                 ║
    ║                                                       ║
    ║          MongoDB Atlas Authentication Setup           ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_auth_comparison():
    """Print comparison of authentication methods."""
    table = Table(title="Authentication Methods Comparison", show_header=True)
    table.add_column("Feature", style="cyan", width=25)
    table.add_column("API Keys", style="green", width=30)
    table.add_column("Service Accounts", style="yellow", width=30)

    table.add_row(
        "Scope",
        "[bold green]Organization-level[/bold green]",
        "[bold yellow]Project-level only[/bold yellow]"
    )
    table.add_row(
        "AtlasUI Compatibility",
        "[bold green]Full (Recommended)[/bold green]",
        "[bold yellow]Limited[/bold yellow]"
    )
    table.add_row(
        "Setup Complexity",
        "[bold green]Simple[/bold green]",
        "[bold yellow]Moderate[/bold yellow]"
    )
    table.add_row(
        "Security",
        "Moderate (with rotation)",
        "High (JWT-based)"
    )
    table.add_row(
        "Use Case",
        "Managing all org resources",
        "Single project operations"
    )

    console.print("\n")
    console.print(table)
    console.print("\n")

    # Add important note
    note = Panel.fit(
        """[bold yellow]⚠️  Important Note About Service Accounts[/bold yellow]

Service accounts in MongoDB Atlas are [bold]project-scoped[/bold], meaning each service account
can only access resources within a single project.

[bold cyan]AtlasUI is designed to manage:[/bold cyan]
• [bold]All[/bold] organizations in your Atlas account
• [bold]All[/bold] projects across organizations
• [bold]All[/bold] clusters across all projects

[bold green]Recommendation:[/bold green] Use [bold]API Keys[/bold] for full AtlasUI functionality.

[bold yellow]Service accounts are suitable when:[/bold yellow]
• You only need to manage a single project
• You prefer OAuth 2.0 authentication
• You need fine-grained permissions for one project
        """,
        border_style="yellow",
        title="Service Account Limitations"
    )
    console.print(note)
    console.print("\n")


def choose_auth_method() -> AuthMethod:
    """Let user choose authentication method."""
    print_auth_comparison()

    choice = Prompt.ask(
        "[bold]Choose authentication method[/bold]",
        choices=["1", "2"],
        default="1",
        console=console,
        show_choices=False
    )

    console.print()

    if choice == "1":
        return "api_key"
    else:
        # Confirm they understand the limitation
        console.print("[bold yellow]You selected Service Account authentication.[/bold yellow]\n")
        console.print("Remember: Service accounts are [bold]project-scoped[/bold].")
        console.print("AtlasUI requires [bold]organization-level[/bold] access for full functionality.\n")

        continue_anyway = Confirm.ask(
            "[bold]Continue with Service Account setup anyway?[/bold]",
            default=False,
            console=console
        )

        if not continue_anyway:
            console.print("\n[green]Good choice! Switching to API Key setup...[/green]\n")
            return "api_key"

        return "service_account"


def configure_api_key() -> int:
    """Configure API Key authentication."""
    console.print("\n[bold cyan]═══ API Key Configuration ═══[/bold cyan]\n")

    instructions = Panel.fit(
        """[bold]To get your Atlas API keys:[/bold]

1. Go to: [bold]https://cloud.mongodb.com/v2#/preferences/organizations[/bold]
2. Select your organization from the list
3. In the sidebar, click [bold]Applications[/bold]
4. Choose [bold]API Key[/bold] (not Service Account)
5. Click [bold]Create API Key[/bold]
6. Enter a description (e.g., "AtlasUI Access")
7. Set permissions: [bold]Organization Owner[/bold] or [bold]Organization Project Creator[/bold]
8. Click [bold]Next[/bold]
9. Copy the [bold]Public Key[/bold] and [bold]Private Key[/bold]
   [yellow]⚠️  The Private Key is only shown once![/yellow]
10. Add your IP address to the API Key whitelist
11. Click [bold]Done[/bold]
        """,
        title="📋 Getting API Keys",
        border_style="cyan"
    )
    console.print(instructions)
    console.print()

    # Check if user is ready
    ready = Confirm.ask(
        "[bold]Do you have your API keys ready?[/bold]",
        default=True,
        console=console
    )

    if not ready:
        console.print("\n[yellow]Please get your API keys from Atlas first.[/yellow]")
        return 1

    console.print("\n[bold cyan]Step 1: Enter API Keys[/bold cyan]\n")

    # Get Public Key
    while True:
        public_key = Prompt.ask(
            "[bold]Public Key[/bold]",
            console=console
        ).strip()

        if public_key and len(public_key) > 5:
            break
        else:
            console.print("[red]Invalid Public Key. Please try again.[/red]")

    # Get Private Key
    while True:
        console.print("\n[bold]Private Key[/bold] (input will be hidden)")
        private_key = getpass.getpass("Enter Private Key: ").strip()

        if not private_key:
            console.print("[red]Private Key cannot be empty. Please try again.[/red]")
            continue

        # Confirm key
        console.print("[dim]Confirm Private Key[/dim] (input will be hidden)")
        private_key_confirm = getpass.getpass("Confirm Private Key: ").strip()

        if private_key != private_key_confirm:
            console.print("[red]Keys don't match. Please try again.[/red]")
            continue

        if len(private_key) > 5:
            break
        else:
            console.print("[red]Invalid Private Key. Please try again.[/red]")

    # Create or update .env file
    console.print("\n[bold cyan]Step 2: Configure .env File[/bold cyan]\n")

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
            console.print("\n[bold]Manual Configuration:[/bold]")
            console.print(f"Public Key: [green]{public_key}[/green]")
            console.print("Add these to your .env file:")
            console.print("[cyan]ATLAS_AUTH_METHOD=api_key[/cyan]")
            console.print(f"[cyan]ATLAS_PUBLIC_KEY={public_key}[/cyan]")
            console.print("[cyan]ATLAS_PRIVATE_KEY=<your_private_key>[/cyan]")
            return 0

    # Read existing .env if it exists
    existing_lines = []
    if env_path.exists():
        with env_path.open('r') as f:
            existing_lines = f.readlines()

    # Remove old Atlas authentication settings
    new_lines = []
    for line in existing_lines:
        if any(key in line for key in [
            'ATLAS_AUTH_METHOD',
            'ATLAS_PUBLIC_KEY',
            'ATLAS_PRIVATE_KEY',
            'ATLAS_SERVICE_ACCOUNT',
        ]):
            continue
        new_lines.append(line)

    # Add new API key configuration
    config_lines = [
        "\n# MongoDB Atlas API Key Configuration\n",
        "ATLAS_AUTH_METHOD=api_key\n",
        f"ATLAS_PUBLIC_KEY={public_key}\n",
        f"ATLAS_PRIVATE_KEY={private_key}\n",
        "ATLAS_BASE_URL=https://cloud.mongodb.com\n",
        "ATLAS_API_VERSION=v2\n",
    ]

    # Write updated .env
    with env_path.open('w') as f:
        f.writelines(new_lines)
        f.writelines(config_lines)

    console.print(f"[green]✓[/green] Updated .env file: [bold]{env_path.absolute()}[/bold]")

    # Set secure permissions
    try:
        env_path.chmod(0o600)
        console.print(f"[green]✓[/green] Set secure file permissions (600)")
    except Exception:
        console.print("[yellow]⚠[/yellow]  Could not set file permissions. Please run: [bold]chmod 600 .env[/bold]")

    # Test connection
    console.print("\n[bold cyan]Step 3: Testing Connection[/bold cyan]\n")

    test = Confirm.ask(
        "[bold]Test Atlas API connection now?[/bold]",
        default=True,
        console=console
    )

    connection_ok = False
    if test:
        try:
            from atlasui.client import AtlasClient

            with console.status("[bold green]Testing Atlas API connection..."):
                with AtlasClient(
                    public_key=public_key,
                    private_key=private_key,
                    auth_method="api_key"
                ) as client:
                    result = client.get_root()

            console.print("[green]✓[/green] [bold green]Successfully connected to Atlas API![/bold green]")

            # Try to list organizations
            with console.status("[bold green]Fetching organizations..."):
                with AtlasClient(
                    public_key=public_key,
                    private_key=private_key,
                    auth_method="api_key"
                ) as client:
                    orgs = client.list_organizations(items_per_page=5)

            if orgs.get('results'):
                console.print(f"\n[green]✓[/green] Found {orgs.get('totalCount', 0)} organizations")

                # Show organizations
                table = Table(title="Your Organizations", show_header=True)
                table.add_column("Name", style="cyan")
                table.add_column("ID", style="green")

                for org in orgs['results'][:5]:
                    table.add_row(
                        org.get('name', 'N/A'),
                        org.get('id', 'N/A')
                    )

                console.print(table)

            connection_ok = True

        except Exception as e:
            console.print(f"\n[red]✗[/red] [bold red]Connection failed:[/bold red] {str(e)}")
            console.print("\n[yellow]Troubleshooting:[/yellow]")
            console.print("  • Verify your Public Key and Private Key are correct")
            console.print("  • Check that your IP address is whitelisted in Atlas")
            console.print("  • Ensure the API key has proper permissions (Organization Owner)")
            console.print("  • Verify network connectivity to cloud.mongodb.com")

    # Print next steps
    print_api_key_next_steps(connection_ok)

    return 0


def print_api_key_next_steps(connection_ok: bool):
    """Print next steps for API key setup."""
    console.print("\n")

    if connection_ok:
        next_steps = Panel.fit(
            """[bold green]Setup Complete! 🎉[/bold green]

[bold]Your API keys are configured and working.[/bold]

[bold cyan]Next Steps:[/bold cyan]

1. Start the web server:
   [bold]atlasui start[/bold]
   Then visit: http://localhost:8000

2. Use the CLI:
   [bold]atlasui --help[/bold]

3. View your organizations, projects, and clusters in the web UI

[bold yellow]Security Reminders:[/bold yellow]
• Never commit .env to Git
• Rotate API keys every 90 days
• Keep your Private Key secure
• Consider using a secrets manager for production
            """,
            title="✓ Success",
            border_style="green"
        )
    else:
        next_steps = Panel.fit(
            """[bold yellow]Setup completed with warnings[/bold yellow]

.env file created with your API keys.

However, the connection test failed. Please:

1. Verify API keys in Atlas:
   https://cloud.mongodb.com

2. Check API key permissions (should be Organization Owner)

3. Verify your IP is whitelisted for the API key

4. Test manually:
   [bold]atlasui start[/bold]
            """,
            title="⚠ Action Required",
            border_style="yellow"
        )

    console.print(next_steps)


def configure_service_account() -> int:
    """Configure Service Account authentication."""
    console.print("\n[bold yellow]═══ Service Account Configuration ═══[/bold yellow]\n")

    # Show warning again
    warning = Panel.fit(
        """[bold yellow]⚠️  Remember: Service Account Limitations[/bold yellow]

Service accounts are [bold]project-scoped[/bold]. This means:

• Each service account can only access [bold]ONE[/bold] project
• AtlasUI needs access to [bold]ALL[/bold] organizations and projects
• You will have [bold]limited functionality[/bold] with service accounts

[bold green]Recommended:[/bold green] Cancel this and use API Keys instead.
        """,
        border_style="yellow"
    )
    console.print(warning)
    console.print()

    continue_sa = Confirm.ask(
        "[bold]Continue with Service Account setup?[/bold]",
        default=False,
        console=console
    )

    if not continue_sa:
        console.print("\n[green]Switching to API Key setup...[/green]\n")
        return configure_api_key()

    # Check if ServiceAccountManager is available
    if ServiceAccountManager is None:
        console.print("[red]Error: Service Account support not available.[/red]")
        return 1

    instructions = Panel.fit(
        """[bold]To get service account credentials:[/bold]

1. Go to: [bold]https://cloud.mongodb.com[/bold]
2. Select your organization
3. Click [bold]Access Manager[/bold] → [bold]Service Accounts[/bold]
4. Click [bold]Create Service Account[/bold]
5. Enter description and assign roles for [bold]ONE PROJECT[/bold]
6. Save and copy the [bold]Client ID[/bold] and [bold]Client Secret[/bold]
   [yellow]⚠️  The Client Secret is only shown once![/yellow]
        """,
        title="📋 Getting Service Account Credentials",
        border_style="yellow"
    )
    console.print(instructions)
    console.print()

    # Rest of service account setup (reuse existing code)
    # ... (continue with the existing service account setup logic)

    console.print("\n[yellow]Note: Full service account setup requires additional implementation.[/yellow]")
    console.print("[yellow]For now, please use API Key authentication for full functionality.[/yellow]\n")

    return configure_api_key()


def interactive_configure() -> int:
    """
    Run interactive configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print_banner()

        console.print("\n[bold]Welcome to AtlasUI Configuration![/bold]\n")
        console.print("This wizard will help you set up authentication for MongoDB Atlas.\n")

        console.print("[bold cyan]Available authentication methods:[/bold cyan]")
        console.print("  [bold]1.[/bold] API Keys (Recommended for AtlasUI)")
        console.print("  [bold]2.[/bold] Service Account (Limited - Project-scoped only)")
        console.print()

        # Choose authentication method
        auth_method = choose_auth_method()

        # Configure based on choice
        if auth_method == "api_key":
            return configure_api_key()
        else:
            return configure_service_account()

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Configuration cancelled by user.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error during configuration:[/red] {str(e)}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


def main():
    """Main entry point."""
    sys.exit(interactive_configure())


if __name__ == "__main__":
    main()
