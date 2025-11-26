#!/usr/bin/env python3
"""
AtlasUI Server Management Script
Usage: atlasui {start|stop|restart|status}
"""

import sys
import os
import signal
import subprocess
import time
import argparse
import atexit
from pathlib import Path
from typing import Optional

from atlasui import __version__

# Configuration
SERVER_MODULE = "atlasui.server"
PID_FILE = Path("atlasui.pid")
LOG_FILE = Path("atlasui.log")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def cleanup_pid_file() -> None:
    """Clean up PID file on exit if process is not running."""
    if PID_FILE.exists():
        pid = get_pid()
        if pid is not None:
            try:
                # Check if process is still running
                os.kill(pid, 0)
                # Process is running, don't delete PID file
            except (OSError, ProcessLookupError):
                # Process is not running, safe to delete PID file
                PID_FILE.unlink()


# Register cleanup function to run on exit
atexit.register(cleanup_pid_file)


def print_msg(color: str, *args) -> None:
    """Print colored message to terminal."""
    message = ' '.join(str(arg) for arg in args)
    print(f"{color}{message}{Colors.NC}")


def get_pid() -> Optional[int]:
    """Get the server PID from PID file."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def is_running() -> bool:
    """Check if server is running."""
    pid = get_pid()
    if pid is None:
        return False

    try:
        # Check if process exists (doesn't kill it, just checks)
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        # Process doesn't exist, clean up stale PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        return False


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        # lsof not available
        return False


def start_server() -> int:
    """Start the AtlasUI server."""
    if is_running():
        print_msg(Colors.YELLOW, f"⚠️  Server is already running (PID: {get_pid()})")
        return 1

    # Check if port is already in use
    if is_port_in_use(PORT):
        print_msg(Colors.RED, f"✗ Port {PORT} is already in use by another process")
        print_msg(Colors.YELLOW, "  Run the following to see what's using the port:")
        print_msg(Colors.YELLOW, f"  lsof -i :{PORT}")
        print_msg(Colors.YELLOW, "\n  To use a different port:")
        print_msg(Colors.YELLOW, f"  atlasui start --port <PORT>")
        return 1

    print_msg(Colors.BLUE, "🚀 Starting AtlasUI server...")
    print_msg(Colors.BLUE, f"   Host: {HOST}")
    print_msg(Colors.BLUE, f"   Port: {PORT}")
    print_msg(Colors.BLUE, f"   Log: {LOG_FILE}")

    # Start server in background
    try:
        with open(LOG_FILE, 'w') as log:
            process = subprocess.Popen(
                ["uv", "run", "python", "-m", SERVER_MODULE],
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # Detach from parent
                env={**os.environ, "HOST": HOST, "PORT": str(PORT)}
            )

        # Save PID
        PID_FILE.write_text(str(process.pid))

        # Wait a moment and check if it started successfully
        time.sleep(2)

        if is_running():
            print_msg(Colors.GREEN, f"✓ Server started successfully (PID: {process.pid})")
            print_msg(Colors.GREEN, f"  Access at: http://localhost:{PORT}")
            print_msg(Colors.BLUE, f"  PID file: {PID_FILE.absolute()}")
            print_msg(Colors.BLUE, f"  Log file: {LOG_FILE.absolute()}")
            return 0
        else:
            print_msg(Colors.RED, f"✗ Server failed to start. Check {LOG_FILE} for errors.")
            if PID_FILE.exists():
                PID_FILE.unlink()
            return 1
    except Exception as e:
        print_msg(Colors.RED, f"✗ Failed to start server: {e}")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return 1


def stop_server() -> int:
    """Stop the AtlasUI server."""
    if not is_running():
        print_msg(Colors.YELLOW, "⚠️  Server is not running")
        return 1

    pid = get_pid()
    print_msg(Colors.BLUE, f"🛑 Stopping AtlasUI server (PID: {pid})...")

    try:
        # Try graceful shutdown first (SIGTERM)
        os.kill(pid, signal.SIGTERM)

        # Wait up to 5 seconds for graceful shutdown
        for _ in range(5):
            if not is_running():
                break
            time.sleep(1)

        # Force kill if still running (SIGKILL)
        if is_running():
            print_msg(Colors.YELLOW, "⚠️  Forcing shutdown...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)

    except (OSError, ProcessLookupError):
        pass

    # Clean up
    if PID_FILE.exists():
        PID_FILE.unlink()

    print_msg(Colors.GREEN, "✓ Server stopped")
    return 0


def restart_server() -> int:
    """Restart the AtlasUI server."""
    print_msg(Colors.BLUE, "🔄 Restarting AtlasUI server...")
    stop_server()
    time.sleep(1)
    return start_server()


def show_status() -> int:
    """Show server status."""
    if is_running():
        pid = get_pid()
        print_msg(Colors.GREEN, "✓ Server is running")
        print_msg(Colors.GREEN, f"  PID: {pid}")
        print_msg(Colors.GREEN, f"  URL: http://localhost:{PORT}")

        # Check if port is actually listening
        if is_port_in_use(PORT):
            print_msg(Colors.GREEN, f"  Port {PORT}: Listening")
        else:
            print_msg(Colors.YELLOW, f"  Port {PORT}: Not listening (server may be starting)")

        # Show recent logs
        if LOG_FILE.exists():
            print()
            print_msg(Colors.BLUE, "Recent logs (last 5 lines):")
            with open(LOG_FILE) as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    print(line.rstrip())
        return 0
    else:
        print_msg(Colors.RED, "✗ Server is not running")

        # Check if port is in use by another process
        if is_port_in_use(PORT):
            print_msg(Colors.YELLOW, f"⚠️  Warning: Port {PORT} is in use by another process:")
            subprocess.run(["lsof", "-i", f":{PORT}", "-sTCP:LISTEN"])
        return 1


def main() -> int:
    """Main entry point."""
    # Get default values from environment or constants
    default_host = os.environ.get("HOST", "0.0.0.0")
    default_port = int(os.environ.get("PORT", "8000"))

    parser = argparse.ArgumentParser(
        description='AtlasUI Server Management',
        epilog=f"""
Environment Variables:
  HOST     Server host (default: 0.0.0.0)
  PORT     Server port (default: 8000)

Examples:
  atlasui start
  PORT=8080 atlasui start
  atlasui status
  atlasui restart

atlasui version {__version__}
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'atlasui {__version__}'
    )

    parser.add_argument(
        'command',
        choices=['start', 'stop', 'restart', 'status'],
        help='Command to execute'
    )

    parser.add_argument(
        '--host',
        default=default_host,
        help=f'Server host (default: {default_host})'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=default_port,
        help=f'Server port (default: {default_port})'
    )

    args = parser.parse_args()

    # Update globals with command-line args
    global HOST, PORT
    HOST = args.host
    PORT = args.port

    commands = {
        'start': start_server,
        'stop': stop_server,
        'restart': restart_server,
        'status': show_status,
    }

    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main())
