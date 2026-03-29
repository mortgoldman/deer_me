"""Integration test configuration — Blender headless fixtures.

These tests require Blender to be installed and accessible. They are
automatically skipped if bpy is not available (i.e., not running inside
Blender's Python environment).
"""

from __future__ import annotations

import pytest

# Skip entire module if bpy is not available
try:
    import bpy

    HAS_BPY = True
except ImportError:
    HAS_BPY = False

pytestmark = pytest.mark.skipif(not HAS_BPY, reason="Blender (bpy) not available")


@pytest.fixture
def clean_scene():
    """Provide a clean Blender scene for each test.

    Removes all objects, then yields. After the test, cleans up again.
    """
    _clear_scene()
    yield
    _clear_scene()


@pytest.fixture
def skeleton():
    """Provide a fresh Skeleton instance."""
    from deer_me.core.skeleton import Skeleton

    return Skeleton()


def _clear_scene():
    """Remove all objects from the scene."""
    if not HAS_BPY:
        return

    # Remove all objects directly (avoids operator context issues in background mode)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # Clear orphan data
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in list(bpy.data.armatures):
        if block.users == 0:
            bpy.data.armatures.remove(block)
    for block in list(bpy.data.materials):
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in list(bpy.data.actions):
        if block.users == 0:
            bpy.data.actions.remove(block)
    for block in list(bpy.data.cameras):
        if block.users == 0:
            bpy.data.cameras.remove(block)
    for block in list(bpy.data.lights):
        if block.users == 0:
            bpy.data.lights.remove(block)
