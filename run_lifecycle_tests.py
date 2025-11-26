#!/usr/bin/env python3
"""
Script to run cluster lifecycle tests.

These tests create real clusters on MongoDB Atlas and wait for them
to complete before deleting them.

Usage:
    python run_lifecycle_tests.py [m0|flex|m10|all|smoke]

Examples:
    python run_lifecycle_tests.py m0      # Run M0 test only
    python run_lifecycle_tests.py flex    # Run Flex test only
    python run_lifecycle_tests.py m10     # Run M10 test only
    python run_lifecycle_tests.py all     # Run all tests
    python run_lifecycle_tests.py smoke   # Run quick smoke test
"""
import sys
import subprocess
import requests
import argparse


def check_server_running():
    """Check if AtlasUI server is running."""
    try:
        response = requests.get("http://localhost:8100", timeout=5)
        return True
    except requests.exceptions.RequestException:
        return False


def run_test(test_name):
    """Run the specified test."""
    if test_name == "smoke":
        print("Running smoke test (quick validation)...")
        cmd = ["uv", "run", "pytest", "tests/test_cluster_lifecycle_smoke.py", "-v", "-s"]
    elif test_name == "m0":
        print("Running M0 cluster lifecycle test...")
        print("Expected duration: 10-15 minutes")
        cmd = ["uv", "run", "pytest", "tests/test_cluster_lifecycle.py::test_m0_cluster_lifecycle", "-v", "-s"]
    elif test_name == "flex":
        print("Running Flex cluster lifecycle test...")
        print("Expected duration: 10-15 minutes")
        cmd = ["uv", "run", "pytest", "tests/test_cluster_lifecycle.py::test_flex_cluster_lifecycle", "-v", "-s"]
    elif test_name == "m10":
        print("Running M10 cluster lifecycle test...")
        print("Expected duration: 10-20 minutes")
        cmd = ["uv", "run", "pytest", "tests/test_cluster_lifecycle.py::test_m10_cluster_lifecycle", "-v", "-s"]
    elif test_name == "all":
        print("Running all cluster lifecycle tests...")
        print("Expected duration: 30-50 minutes total")
        print()
        response = input("Press Enter to continue or Ctrl+C to cancel... ")
        cmd = ["uv", "run", "pytest", "tests/test_cluster_lifecycle.py", "-v", "-s", "-m", "integration"]
    else:
        print(f"Unknown test: {test_name}")
        return 1

    print()
    print("Starting test...")
    print("=" * 80)
    print()

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 130


def main():
    parser = argparse.ArgumentParser(
        description="Run cluster lifecycle tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_lifecycle_tests.py m0      # Run M0 test only (10-15 min)
  python run_lifecycle_tests.py flex    # Run Flex test only (10-15 min)
  python run_lifecycle_tests.py m10     # Run M10 test only (10-20 min)
  python run_lifecycle_tests.py all     # Run all tests (30-50 min)
  python run_lifecycle_tests.py smoke   # Run quick smoke test (~30 sec)

These tests create real clusters on MongoDB Atlas and wait for them
to complete before deleting them.
        """
    )
    parser.add_argument(
        "test",
        nargs="?",
        default="smoke",
        choices=["m0", "flex", "m10", "all", "smoke"],
        help="Which test to run (default: smoke)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Cluster Lifecycle Tests")
    print("=" * 80)
    print()
    print("These tests create real clusters on MongoDB Atlas")
    print("and wait for them to complete before deleting them.")
    print()
    print("Expected duration:")
    print("  - M0 test:   10-15 minutes")
    print("  - Flex test: 10-15 minutes")
    print("  - M10 test:  10-20 minutes")
    print("  - Smoke test: ~30 seconds")
    print("  - All tests: 30-50 minutes")
    print()
    print("=" * 80)
    print()

    # Check if server is running
    print("Checking if AtlasUI server is running...")
    if not check_server_running():
        print("❌ Error: AtlasUI server is not running on port 8100")
        print("   Please start the server first:")
        print("     uv run atlasui start")
        print("   or")
        print("     inv start")
        return 1

    print("✓ Server is running")
    print()

    # Run the test
    return run_test(args.test)


if __name__ == "__main__":
    sys.exit(main())
