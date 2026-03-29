"""One-time Blender setup — install deer_me into Blender's Python.

Run this script once after installing Blender to set up the project:

    blender --background --python scripts/setup_blender.py

What it does:
1. Verifies Blender's Python version is compatible
2. Installs deer_me (and numpy) into Blender's bundled Python
3. Verifies the installation works
"""

import subprocess
import sys
import os


def main():
    print("=" * 60)
    print("  Deer Me — Blender Setup")
    print("=" * 60)
    print()

    # Step 1: Check Python version
    py_version = sys.version_info
    print(f"Blender Python: {sys.version}")
    print(f"Python path:    {sys.executable}")
    print()

    if py_version < (3, 11):
        print(f"WARNING: Python {py_version.major}.{py_version.minor} detected.")
        print("Deer Me requires Python 3.11+. Blender 4.x ships with 3.11+.")
        print("Please update Blender to version 4.0 or later.")
        return False

    # Step 2: Find the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    print(f"Project root: {project_root}")
    print()

    # Step 3: Install deer_me into Blender's Python
    print("Installing deer_me into Blender's Python...")
    print("-" * 40)

    try:
        # Use pip to install in editable mode
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-e", project_root
        ])
        print()
        print("Installation successful!")
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        print()
        print("Try manually:")
        print(f'  "{sys.executable}" -m pip install -e "{project_root}"')
        return False

    # Step 4: Verify
    print()
    print("Verifying installation...")
    print("-" * 40)

    try:
        import deer_me
        print(f"deer_me version: {deer_me.__version__}")

        from deer_me.core.skeleton import Skeleton
        skel = Skeleton()
        print(f"Skeleton loaded: {len(skel.bone_names)} bones")

        from deer_me.api.deer import Deer
        deer = Deer()
        deer.walk()
        deer.update(0.5)
        pose = deer.pose()
        print(f"Test pose generated: {len(pose.joints)} joints")

        import bpy
        print(f"Blender version: {bpy.app.version_string}")

        print()
        print("All checks passed!")
        print()
        print("You're ready to go. Try running an example:")
        print("  blender --python examples/01_basic_walk.py")

    except ImportError as e:
        print(f"Verification failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
