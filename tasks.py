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
    cmd_parts = ["uv", "run", "pytest"]

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
def m10_test(c, verbose=True):
    """
    Run M10-specific tests only (includes pause/resume functionality).

    M10 cluster creation takes ~9 minutes, so these tests are isolated
    for faster development iteration.

    Args:
        verbose: Run tests in verbose mode (default: True)
    """
    print("=" * 80)
    print("Running M10 Test Suite")
    print("=" * 80)
    print("⚠️  M10 cluster creation takes ~9 minutes")
    print("")

    # Run M10 browser tests
    print("\n[1/1] Running M10 browser tests...")
    print("-" * 80)
    m10_cmd = ["uv", "run", "pytest", "tests/", "-m", '"browser and m10"']

    if verbose:
        m10_cmd.append("-v")

    result = c.run(" ".join(m10_cmd), warn=True)
    m10_passed = result.ok

    # Summary
    print("\n" + "=" * 80)
    print("M10 Test Suite Summary")
    print("=" * 80)
    print(f"M10 tests: {'✓ PASSED' if m10_passed else '✗ FAILED'}")
    print("=" * 80)

    if not m10_passed:
        print("\n⚠ M10 tests failed!")
        raise SystemExit(1)
    else:
        print("\n✓ M10 tests passed!")


@task
def test_dev(c, verbose=True, coverage=True, parallel=True):
    """
    Run development test suite (excludes slow M10 tests).

    This is the fast test suite for development iteration. M10 tests are
    excluded because M10 cluster creation takes ~9 minutes.

    Use 'inv test-release' or 'inv m10-test' to run M10 tests.

    Args:
        verbose: Run tests in verbose mode (default: True)
        coverage: Generate coverage report (default: True)
        parallel: Run async and browser tests in parallel (default: True, use --no-parallel to disable)
    """
    print("=" * 80)
    print("Running Development Test Suite (excludes M10)")
    if parallel:
        print("(Async and Browser tests in PARALLEL)")
    print("=" * 80)

    if parallel:
        # Run async and browser tests in parallel
        import subprocess

        print("\n[1/2] Starting async tests (unit + integration) in background...")
        print("-" * 80)
        async_cmd = ["uv", "run", "pytest", "tests/", "-m", "not browser"]
        if verbose:
            async_cmd.append("-v")
        if coverage:
            async_cmd.extend([
                "--cov=atlasui",
                "--cov-report=html",
                "--cov-report=term"
            ])

        async_proc = subprocess.Popen(
            async_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        print("\n[2/2] Starting browser tests (excluding M10) in background...")
        print("-" * 80)
        browser_cmd = ["uv", "run", "pytest", "tests/", "-m", "browser and not m10"]
        if verbose:
            browser_cmd.append("-v")

        browser_proc = subprocess.Popen(
            browser_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Wait for both to complete
        print("\nWaiting for both test suites to complete...")
        async_output, _ = async_proc.communicate()
        browser_output, _ = browser_proc.communicate()

        async_passed = async_proc.returncode == 0
        browser_passed = browser_proc.returncode == 0

        # Print outputs
        print("\n" + "=" * 80)
        print("ASYNC TEST OUTPUT")
        print("=" * 80)
        print(async_output)

        print("\n" + "=" * 80)
        print("BROWSER TEST OUTPUT (M0/Flex)")
        print("=" * 80)
        print(browser_output)

    else:
        # Run sequentially (original behavior)
        print("\n[1/2] Running async tests (unit + integration)...")
        print("-" * 80)
        async_cmd = ["uv", "run", "pytest", "tests/", "-m", '"not browser"']

        if verbose:
            async_cmd.append("-v")

        if coverage:
            async_cmd.extend([
                "--cov=atlasui",
                "--cov-report=html",
                "--cov-report=term"
            ])

        result = c.run(" ".join(async_cmd), warn=True)
        async_passed = result.ok

        # Run browser tests (excluding M10)
        print("\n[2/2] Running browser tests (excluding M10)...")
        print("-" * 80)
        browser_cmd = ["uv", "run", "pytest", "tests/", "-m", '"browser and not m10"']

        if verbose:
            browser_cmd.append("-v")

        result = c.run(" ".join(browser_cmd), warn=True)
        browser_passed = result.ok

    # Summary
    print("\n" + "=" * 80)
    print("Development Test Suite Summary")
    print("=" * 80)
    print(f"Async tests:           {'✓ PASSED' if async_passed else '✗ FAILED'}")
    print(f"Browser tests (M0/Flex): {'✓ PASSED' if browser_passed else '✗ FAILED'}")
    print("=" * 80)
    print("ℹ️  M10 tests skipped (use 'inv m10-test' or 'inv test-release')")

    if not (async_passed and browser_passed):
        print("\n⚠ Some tests failed!")
        raise SystemExit(1)
    else:
        print("\n✓ Development tests passed!")
        if coverage:
            print(f"\nCoverage report: file://{Path('htmlcov/index.html').absolute()}")


@task
def test_release(c, verbose=True, coverage=True, parallel=True):
    """
    Run complete test suite for releases (includes all tests).

    This runs all tests including slow M10 tests. Use this before
    creating a release or merging to main.

    For faster development iteration, use 'inv test-dev' instead.

    Args:
        verbose: Run tests in verbose mode (default: True)
        coverage: Generate coverage report (default: True)
        parallel: Run test suites in parallel (default: True, use --no-parallel to disable)
    """
    print("=" * 80)
    print("Running COMPLETE Test Suite for Release")
    if parallel:
        print("(Async and Browser tests in PARALLEL)")
    print("=" * 80)
    print("⚠️  This includes M10 tests (~9 min cluster creation)")
    print("")

    if parallel:
        # Run async and browser tests in parallel
        # NOTE: Browser tests (M0/Flex/M10) run in single session to avoid race conditions
        # with session-scoped fixtures
        import subprocess

        print("\n[1/2] Starting async tests in background...")
        print("-" * 80)
        async_cmd = ["uv", "run", "pytest", "tests/", "-m", "not browser"]
        if verbose:
            async_cmd.append("-v")
        if coverage:
            async_cmd.extend([
                "--cov=atlasui",
                "--cov-report=html",
                "--cov-report=term"
            ])

        async_proc = subprocess.Popen(
            async_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        print("\n[2/2] Starting browser tests (M0/Flex/M10) in background...")
        print("-" * 80)
        print("⚠️  Browser tests run sequentially to share session-scoped cluster fixtures")
        browser_cmd = ["uv", "run", "pytest", "tests/", "-m", "browser"]
        if verbose:
            browser_cmd.append("-v")

        browser_proc = subprocess.Popen(
            browser_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Wait for both to complete
        print("\nWaiting for both test suites to complete...")
        async_output, _ = async_proc.communicate()
        browser_output, _ = browser_proc.communicate()

        async_passed = async_proc.returncode == 0
        browser_passed = browser_proc.returncode == 0

        # Print outputs
        print("\n" + "=" * 80)
        print("ASYNC TEST OUTPUT")
        print("=" * 80)
        print(async_output)

        print("\n" + "=" * 80)
        print("BROWSER TEST OUTPUT (M0/Flex/M10)")
        print("=" * 80)
        print(browser_output)

    else:
        # Run sequentially
        print("\n[1/2] Running async tests (unit + integration)...")
        print("-" * 80)
        async_cmd = ["uv", "run", "pytest", "tests/", "-m", '"not browser"']

        if verbose:
            async_cmd.append("-v")

        if coverage:
            async_cmd.extend([
                "--cov=atlasui",
                "--cov-report=html",
                "--cov-report=term"
            ])

        result = c.run(" ".join(async_cmd), warn=True)
        async_passed = result.ok

        # Run ALL browser tests (M0/Flex/M10) in single session
        print("\n[2/2] Running browser tests (M0/Flex/M10)...")
        print("-" * 80)
        browser_cmd = ["uv", "run", "pytest", "tests/", "-m", '"browser"']

        if verbose:
            browser_cmd.append("-v")

        result = c.run(" ".join(browser_cmd), warn=True)
        browser_passed = result.ok

    # Summary
    print("\n" + "=" * 80)
    print("Complete Test Suite Summary")
    print("=" * 80)
    print(f"Async tests:              {'✓ PASSED' if async_passed else '✗ FAILED'}")
    print(f"Browser tests (M0/Flex/M10): {'✓ PASSED' if browser_passed else '✗ FAILED'}")
    print("=" * 80)

    if not (async_passed and browser_passed):
        print("\n⚠ Some tests failed!")
        raise SystemExit(1)
    else:
        print("\n✓ All tests passed! Ready for release.")
        if coverage:
            print(f"\nCoverage report: file://{Path('htmlcov/index.html').absolute()}")


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
def start(c, host="0.0.0.0", port=8100):
    """
    Start the web server.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8100)
    """
    print(f"Starting AtlasUI server on {host}:{port}...")
    c.run(f"uv run atlasui start --host={host} --port={port}", pty=True)


@task
def stop(c):
    """Stop the web server."""
    print("Stopping AtlasUI server...")
    c.run("uv run atlasui stop", pty=True)


@task
def kill_port(c, port=8100):
    """
    Kill any process running on a specific port.

    Args:
        port: Port number to kill process on (default: 8100)
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
def restart(c, host="0.0.0.0", port=8100):
    """
    Restart the web server.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8100)
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


@task
def cleanup_tests(c, list_only=False, force=False, project_id=None):
    """
    Clean up leftover test resources from interrupted test runs.

    When browser tests are interrupted (Ctrl+C, crash, timeout), the test
    project and clusters may not be cleaned up. This task helps manage those
    leftover resources.

    Args:
        list_only: Only list test projects without deleting (default: False)
        force: Skip confirmation prompts (default: False)
        project_id: Delete a specific project by ID (optional)

    Examples:
        inv cleanup-tests --list-only        # List all test projects
        inv cleanup-tests                     # Delete all test projects (with confirmation)
        inv cleanup-tests --force             # Delete without confirmation
        inv cleanup-tests --project-id=ID    # Delete specific project
    """
    cmd = ["uv", "run", "python", "tests/cleanup_test_resources.py"]

    if list_only:
        cmd.append("--list")
    elif project_id:
        cmd.extend(["--project-id", project_id])
        if force:
            cmd.append("--force")
    else:
        cmd.append("--clean")
        if force:
            cmd.append("--force")

    c.run(" ".join(cmd), pty=True)
