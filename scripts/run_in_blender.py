"""Helper script to run pytest inside Blender's Python environment.

Usage:
    blender --background --python scripts/run_in_blender.py -- pytest tests/integration/ -v

Everything after '--' is passed to pytest as arguments.

This script adds the project's src/ directory and the system Python's
site-packages to Blender's sys.path so that both deer_me and pytest
are importable without installing them into Blender's bundled Python.
"""

import os
import sys
import site


def _setup_paths():
    """Add project src/ and system site-packages to sys.path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Add src/ so deer_me is importable
    src_dir = os.path.join(project_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Add system Python's site-packages so pytest (and other dev deps) are found
    # Try common locations for the user's Python installation
    for path in site.getsitepackages() if hasattr(site, "getsitepackages") else []:
        if path not in sys.path:
            sys.path.append(path)

    # Also try the user site-packages
    user_site = site.getusersitepackages() if hasattr(site, "getusersitepackages") else None
    if user_site and user_site not in sys.path:
        sys.path.append(user_site)


def main():
    _setup_paths()

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
