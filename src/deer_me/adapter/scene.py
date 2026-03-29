"""Blender scene setup — ground plane, lighting, camera.

Provides sensible defaults for rendering a deer animation.
All bpy access is lazy-imported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    import bpy


def _bpy():
    import bpy as _bpy

    return _bpy


def _mathutils():
    import mathutils as _mu

    return _mu


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------


def setup_scene(
    fps: int = 24,
    frame_start: int = 1,
    frame_end: int = 250,
    engine: str = "EEVEE",
) -> None:
    """Configure basic scene settings for animation rendering.

    Args:
        fps: Frames per second.
        frame_start: First frame of the animation.
        frame_end: Last frame of the animation.
        engine: Render engine — "EEVEE", "CYCLES", or "WORKBENCH".
    """
    bpy = _bpy()
    scene = bpy.context.scene

    scene.render.fps = fps
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.frame_set(frame_start)

    engine_map = {
        "EEVEE": "BLENDER_EEVEE_NEXT",
        "CYCLES": "CYCLES",
        "WORKBENCH": "BLENDER_WORKBENCH",
    }
    scene.render.engine = engine_map.get(engine.upper(), "BLENDER_EEVEE_NEXT")


def clear_default_objects() -> None:
    """Remove the default cube, camera, and light that Blender starts with."""
    bpy = _bpy()

    for name in ("Cube", "Camera", "Light"):
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)


# ---------------------------------------------------------------------------
# Ground plane
# ---------------------------------------------------------------------------


def create_ground_plane(
    size: float = 20.0,
    location: Tuple[float, float, float] = (0, 0, 0),
    name: str = "Ground",
    color: Tuple[float, float, float, float] = (0.25, 0.35, 0.15, 1.0),
) -> "bpy.types.Object":
    """Create a ground plane with a basic material.

    Args:
        size: Side length of the plane.
        location: World position of the plane center.
        name: Object name.
        color: RGBA base color (default: muted green/grass).

    Returns:
        The created plane object.
    """
    bpy = _bpy()

    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    plane = bpy.context.active_object
    plane.name = name

    # Create a simple material
    mat = bpy.data.materials.new(name=f"{name}_Material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.9

    plane.data.materials.append(mat)

    return plane


# ---------------------------------------------------------------------------
# Lighting
# ---------------------------------------------------------------------------


def create_three_point_lighting(
    key_energy: float = 5.0,
    fill_energy: float = 2.0,
    rim_energy: float = 3.0,
) -> list:
    """Create a three-point lighting setup suitable for character animation.

    Args:
        key_energy: Intensity of the main key light.
        fill_energy: Intensity of the fill light.
        rim_energy: Intensity of the rim/back light.

    Returns:
        List of the three light objects [key, fill, rim].
    """
    bpy = _bpy()
    mu = _mathutils()
    lights = []

    configs = [
        ("KeyLight", "SUN", key_energy, (3, -3, 5), (-0.6, 0.1, 0.8)),
        ("FillLight", "AREA", fill_energy, (-3, -2, 3), (-0.5, -0.2, -0.5)),
        ("RimLight", "SPOT", rim_energy, (-1, 4, 4), (-2.3, 0.0, -0.3)),
    ]

    for name, light_type, energy, location, rotation in configs:
        light_data = bpy.data.lights.new(name=name, type=light_type)
        light_data.energy = energy

        if light_type == "AREA":
            light_data.size = 3.0
        elif light_type == "SPOT":
            light_data.spot_size = 1.2

        light_obj = bpy.data.objects.new(name=name, object_data=light_data)
        light_obj.location = mu.Vector(location)
        light_obj.rotation_euler = mu.Euler(rotation)

        bpy.context.scene.collection.objects.link(light_obj)
        lights.append(light_obj)

    return lights


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------


def create_camera(
    location: Tuple[float, float, float] = (4, -4, 2),
    look_at: Tuple[float, float, float] = (0, 0, 0.8),
    name: str = "DeerCamera",
    focal_length: float = 50.0,
) -> "bpy.types.Object":
    """Create and configure a camera aimed at the deer.

    Args:
        location: Camera world position.
        look_at: Point the camera should aim at (approximately deer shoulder height).
        name: Camera object name.
        focal_length: Lens focal length in mm.

    Returns:
        The camera object.
    """
    bpy = _bpy()
    mu = _mathutils()

    cam_data = bpy.data.cameras.new(name=name)
    cam_data.lens = focal_length

    cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
    cam_obj.location = mu.Vector(location)

    # Point camera at the target
    direction = mu.Vector(look_at) - mu.Vector(location)
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()

    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    return cam_obj


# ---------------------------------------------------------------------------
# Complete scene setup
# ---------------------------------------------------------------------------


def setup_deer_scene(
    fps: int = 24,
    frame_end: int = 250,
    engine: str = "EEVEE",
) -> dict:
    """One-call scene setup with ground, lights, and camera.

    Returns a dict of created objects for further customization.
    """
    clear_default_objects()
    setup_scene(fps=fps, frame_end=frame_end, engine=engine)

    ground = create_ground_plane()
    lights = create_three_point_lighting()
    camera = create_camera()

    return {
        "ground": ground,
        "lights": lights,
        "camera": camera,
    }
