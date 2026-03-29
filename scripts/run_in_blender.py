"""Helper script to run pytest inside Blender's Python environment.

Usage:
    blender --background --python scripts/run_in_blender.py -- pytest tests/integration/ -v

Everything after '--' is passed to pytest as arguments.
"""

import sys
import subprocess


def main():
    # Find the '--' separator in sys.argv
    try:
        sep_idx = sys.argv.index("--")
        pytest_args = sys.argv[sep_idx + 1:]
    except ValueError:
        # No '--' found, default to running integration tests
        pytest_args = ["pytest", "tests/integration/", "-v"]

    if pytest_args and pytest_args[0] != "pytest":
        pytest_args.insert(0, "pytest")

    # Run pytest with the remaining arguments
    import pytest

    exit_code = pytest.main(pytest_args[1:])  # Skip 'pytest' itself
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
