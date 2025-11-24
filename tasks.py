"""
Invoke tasks for AtlasUI project management.

Run `inv --list` to see all available tasks.
"""

from invoke import task
import shutil
from pathlib import Path


@task
def install(c):
    """Install the package."""
    print("Installing AtlasUI...")
    c.run("uv pip install -e .")


@task
def dev_install(c):
    """Install with development dependencies."""
    print("Installing AtlasUI with development dependencies...")
    c.run("uv pip install -e '.[dev,docs]'")


@task
def test(c, verbose=True, coverage=True):
    """
    Run tests.

    Args:
        verbose: Run tests in verbose mode (default: True)
        coverage: Generate coverage report (default: True)
    """
    print("Running tests...")
    cmd_parts = ["pytest"]

    if verbose:
        cmd_parts.append("-v")

    if coverage:
        cmd_parts.extend([
            "--cov=atlasui",
            "--cov-report=html",
            "--cov-report=term"
        ])

    c.run(" ".join(cmd_parts))


@task
def lint(c):
    """Run linting checks."""
    print("Running linting checks...")
    print("\n→ Running ruff...")
    c.run("ruff check atlasui tests", warn=True)

    print("\n→ Running mypy...")
    c.run("mypy atlasui", warn=True)


@task
def format(c, check=False):
    """
    Format code with black and ruff.

    Args:
        check: Only check formatting without making changes (default: False)
    """
    print("Formatting code...")

    if check:
        print("\n→ Checking formatting with black...")
        c.run("black --check atlasui tests")
        print("\n→ Checking with ruff...")
        c.run("ruff check atlasui tests")
    else:
        print("\n→ Formatting with black...")
        c.run("black atlasui tests")
        print("\n→ Fixing with ruff...")
        c.run("ruff check --fix atlasui tests")


@task
def docs(c, open_browser=False):
    """
    Build documentation.

    Args:
        open_browser: Open documentation in browser after building (default: False)
    """
    print("Building documentation...")
    c.run("uv run sphinx-build -M html docs docs/_build", pty=True)

    docs_path = Path("docs/_build/html/index.html").absolute()
    print(f"\n✓ Documentation built in docs/_build/html/")
    print(f"  View at: file://{docs_path}")

    if open_browser:
        import webbrowser
        webbrowser.open(f"file://{docs_path}")


@task
def clean(c):
    """Clean build artifacts."""
    print("Cleaning build artifacts...")

    # Directories to remove
    dirs_to_remove = [
        "build",
        "dist",
        "docs/_build",
        ".pytest_cache",
        "htmlcov",
    ]

    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_path, ignore_errors=True)

    # Remove .egg-info directories
    for egg_info in Path(".").glob("*.egg-info"):
        print(f"  Removing {egg_info}/")
        shutil.rmtree(egg_info, ignore_errors=True)

    # Remove __pycache__ directories
    for pycache in Path(".").rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)

    # Remove .pyc files
    for pyc in Path(".").rglob("*.pyc"):
        pyc.unlink()

    # Remove coverage files
    coverage_file = Path(".coverage")
    if coverage_file.exists():
        coverage_file.unlink()

    print("✓ Cleanup complete")


@task
def start(c, host="0.0.0.0", port=8000):
    """
    Start the web server.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8000)
    """
    print(f"Starting AtlasUI server on {host}:{port}...")
    c.run(f"uv run atlasui start --host={host} --port={port}", pty=True)


@task
def stop(c):
    """Stop the web server."""
    print("Stopping AtlasUI server...")
    c.run("uv run atlasui stop", pty=True)


@task
def kill_port(c, port=8000):
    """
    Kill any process running on a specific port.

    Args:
        port: Port number to kill process on (default: 8000)
    """
    print(f"Killing process on port {port}...")
    result = c.run(f"lsof -ti:{port}", warn=True, hide=True)

    if result and result.stdout.strip():
        pids = result.stdout.strip()
        print(f"  Found process(es): {pids}")
        c.run(f"lsof -ti:{port} | xargs kill -9", warn=True)
        print(f"✓ Process(es) on port {port} killed")
    else:
        print(f"  No process found on port {port}")


@task
def restart(c, host="0.0.0.0", port=8000):
    """
    Restart the web server.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8000)
    """
    print(f"Restarting AtlasUI server on {host}:{port}...")
    c.run(f"uv run atlasui restart --host={host} --port={port}", pty=True)


@task
def status(c):
    """Check the web server status."""
    c.run("uv run atlasui status", pty=True)


@task
def cli(c):
    """Show CLI help."""
    c.run("uv run atlasui --help")


@task
def version(c):
    """Show AtlasUI version."""
    c.run("uv run atlasui version")


@task
def info(c):
    """Show Atlas API connection information."""
    c.run("uv run atlasui info")


@task
def atlascli(c, args=""):
    """
    Run atlascli with any arguments.

    Args:
        args: Arguments to pass to atlascli (e.g., "projects list", "clusters get <id>")

    Examples:
        inv atlascli --args="--version"
        inv atlascli --args="projects list"
        inv atlascli --args="clusters list <project-id>"
    """
    if args:
        c.run(f"uv run atlascli {args}", pty=True)
    else:
        c.run("uv run atlascli --help", pty=True)


@task
def atlasui(c, args=""):
    """
    Run atlasui with any arguments.

    Args:
        args: Arguments to pass to atlasui (e.g., "start", "stop", "status", "--version")

    Examples:
        inv atlasui --args="--version"
        inv atlasui --args="status"
        inv atlasui --args="start --port 8080"
    """
    if args:
        c.run(f"uv run atlasui {args}", pty=True)
    else:
        c.run("uv run atlasui --help", pty=True)


@task
def configure(c):
    """
    Interactively configure Atlas authentication.

    This task walks you through setting up authentication for MongoDB Atlas.
    Choose between API Keys or Service Account authentication.
    """
    print("Starting interactive configuration...\n")
    c.run("uv run atlasui-configure", pty=True)


@task(pre=[format, lint, test])
def check(c):
    """Run all checks (format, lint, test)."""
    print("\n✓ All checks passed!")


@task
def release(c, version_type="patch"):
    """
    Make a release.

    Args:
        version_type: Type of version bump (major, minor, patch) (default: patch)
    """
    print(f"Making a {version_type} release...")

    # Update docs
    print("\n→ Updating documentation...")
    docs(c)

    # Run tests
    print("\n→ Running tests...")
    test(c)

    # Bump version (you may want to add a version bumping tool like bump2version)
    print(f"\n→ Bumping {version_type} version...")
    print("  (Note: Install bump2version or similar for automatic version bumping)")

    # Build package
    print("\n→ Building package...")
    c.run("uv pip install build")
    c.run("python -m build")

    print("\n✓ Release prepared!")
    print("  Next steps:")
    print("  1. Review changes")
    print("  2. Commit: git add . && git commit -m 'Release vX.Y.Z'")
    print("  3. Tag: git tag vX.Y.Z")
    print("  4. Push: git push && git push --tags")


@task
def setup(c):
    """Set up the development environment."""
    print("Setting up development environment...")

    # Install dependencies
    dev_install(c)

    # Create .env if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        env_example = Path(".env.example")
        if env_example.exists():
            print("\n→ Creating .env file from .env.example...")
            shutil.copy(env_example, env_file)
            print("  ⚠ Please edit .env with your Atlas API credentials")
        else:
            print("\n  ⚠ .env.example not found")
    else:
        print("\n→ .env file already exists")

    print("\n✓ Development environment setup complete!")
    print("\nNext steps:")
    print("  1. Edit .env with your Atlas API credentials")
    print("  2. Run: inv info (to test connection)")
    print("  3. Run: inv run (to start web server)")
    print("  4. Run: inv --list (to see all commands)")
