"""Blender mesh skinning helpers — bind mesh to armature.

Provides utilities for:
- Parenting a mesh to an armature with automatic weights
- Creating a basic proxy deer mesh for testing
- Weight painting utilities

All bpy access is lazy-imported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import bpy


def _bpy():
    import bpy as _bpy

    return _bpy


def _mathutils():
    import mathutils as _mu

    return _mu


# ---------------------------------------------------------------------------
# Mesh binding
# ---------------------------------------------------------------------------


def bind_mesh_to_armature(
    mesh_obj: "bpy.types.Object",
    arm_obj: "bpy.types.Object",
    method: str = "AUTOMATIC",
) -> None:
    """Parent a mesh to an armature with weight assignment.

    Args:
        mesh_obj: The mesh object to bind.
        arm_obj: The armature object to bind to.
        method: Weight assignment method:
            - "AUTOMATIC": Blender's automatic weights (good default)
            - "ENVELOPE": Bone envelope-based weights
            - "EMPTY": No weights (manual painting later)
    """
    bpy = _bpy()

    # Parent the mesh to the armature directly (avoids operator context issues)
    mesh_obj.parent = arm_obj
    mesh_obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    # Add an armature modifier
    mod = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj

    if method.upper() == "EMPTY":
        return

    # For AUTOMATIC/ENVELOPE, create vertex groups matching bone names
    # so the armature modifier can deform the mesh
    for bone in arm_obj.data.bones:
        if bone.name not in mesh_obj.vertex_groups:
            mesh_obj.vertex_groups.new(name=bone.name)

    if method.upper() == "AUTOMATIC":
        # Assign automatic weights based on proximity to bones
        _assign_automatic_weights(mesh_obj, arm_obj)


# ---------------------------------------------------------------------------
# Proxy deer mesh
# ---------------------------------------------------------------------------


def create_proxy_mesh(
    arm_obj: "bpy.types.Object",
    name: str = "DeerProxy",
    bind: bool = True,
) -> "bpy.types.Object":
    """Create a simple proxy deer mesh from the armature's bone positions.

    Generates a low-poly mesh by placing shapes at each bone — useful for
    testing skinning and animation before a proper model is available.

    Args:
        arm_obj: The deer armature object.
        name: Name for the proxy mesh.
        bind: If True, automatically bind the mesh to the armature.

    Returns:
        The created mesh object.
    """
    bpy = _bpy()
    mu = _mathutils()

    import bmesh

    bm = bmesh.new()

    # Walk the armature bones and add geometry
    for bone in arm_obj.data.bones:
        head = bone.head_local
        tail = bone.tail_local
        length = bone.length

        if length < 0.01:
            continue

        # Determine radius based on bone role
        radius = _proxy_radius(bone.name, length)

        # Create a tapered cylinder along the bone
        _add_bone_segment(bm, head, tail, radius, radius * 0.7)

    # Create mesh from bmesh
    mesh_data = bpy.data.meshes.new(name)
    bm.to_mesh(mesh_data)
    bm.free()

    mesh_obj = bpy.data.objects.new(name, mesh_data)
    bpy.context.scene.collection.objects.link(mesh_obj)

    # Add a basic material
    mat = bpy.data.materials.new(name=f"{name}_Material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        # Deer brown color
        bsdf.inputs["Base Color"].default_value = (0.45, 0.30, 0.15, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8

    mesh_obj.data.materials.append(mat)

    if bind:
        bind_mesh_to_armature(mesh_obj, arm_obj, method="AUTOMATIC")

    return mesh_obj


def _assign_automatic_weights(
    mesh_obj: "bpy.types.Object",
    arm_obj: "bpy.types.Object",
) -> None:
    """Assign vertex weights based on proximity to bones.

    A simple nearest-bone approach that doesn't require operator context.
    Each vertex is assigned to the closest bone with weight based on distance.
    """
    mu = _mathutils()

    bone_data = []
    for bone in arm_obj.data.bones:
        head = arm_obj.matrix_world @ mu.Vector(bone.head_local)
        tail = arm_obj.matrix_world @ mu.Vector(bone.tail_local)
        bone_data.append((bone.name, head, tail))

    mesh_verts = mesh_obj.data.vertices

    for vert in mesh_verts:
        world_co = mesh_obj.matrix_world @ vert.co
        weights = []

        for bone_name, head, tail in bone_data:
            dist = _point_to_segment_dist(world_co, head, tail)
            if dist < 1e-6:
                dist = 1e-6
            weights.append((bone_name, 1.0 / dist))

        # Normalize and keep the top contributors
        total = sum(w for _, w in weights)
        weights = [(name, w / total) for name, w in weights]
        weights.sort(key=lambda x: x[1], reverse=True)

        # Assign top 4 bone influences
        for bone_name, weight in weights[:4]:
            if weight > 0.01:
                vg = mesh_obj.vertex_groups.get(bone_name)
                if vg:
                    vg.add([vert.index], weight, "REPLACE")


def _point_to_segment_dist(point, seg_start, seg_end) -> float:
    """Distance from a point to a line segment."""
    mu = _mathutils()

    seg = mu.Vector(seg_end) - mu.Vector(seg_start)
    seg_len_sq = seg.length_squared
    if seg_len_sq < 1e-12:
        return (mu.Vector(point) - mu.Vector(seg_start)).length

    t = max(0.0, min(1.0, (mu.Vector(point) - mu.Vector(seg_start)).dot(seg) / seg_len_sq))
    projection = mu.Vector(seg_start) + seg * t
    return (mu.Vector(point) - projection).length


def _proxy_radius(bone_name: str, bone_length: float) -> float:
    """Determine proxy mesh radius for a bone based on its anatomical role."""
    # Body/spine: thicker
    if "spine" in bone_name:
        return bone_length * 0.6

    # Neck: medium
    if "neck" in bone_name:
        return bone_length * 0.35

    # Head: rounder
    if bone_name == "head":
        return bone_length * 0.4

    # Ears: thin
    if "ear" in bone_name:
        return bone_length * 0.15

    # Upper legs: medium-thick
    if "upper" in bone_name or "shoulder" in bone_name or "hip" in bone_name:
        return bone_length * 0.2

    # Lower legs: thinner
    if "lower" in bone_name:
        return bone_length * 0.12

    # Hooves: small
    if "hoof" in bone_name:
        return bone_length * 0.15

    # Tail: thin
    if "tail" in bone_name:
        return bone_length * 0.1

    return bone_length * 0.2


def _add_bone_segment(bm, head, tail, radius_head, radius_tail, segments=6):
    """Add a tapered cylinder between two points to a bmesh."""
    import bmesh
    from math import cos, sin, pi

    mu = _mathutils()

    direction = mu.Vector(tail) - mu.Vector(head)
    length = direction.length
    if length < 1e-6:
        return

    direction.normalize()

    # Build a local coordinate frame
    if abs(direction.z) < 0.99:
        up = mu.Vector((0, 0, 1))
    else:
        up = mu.Vector((1, 0, 0))

    right = direction.cross(up).normalized()
    up = right.cross(direction).normalized()

    # Create rings of vertices
    verts_head = []
    verts_tail = []

    for i in range(segments):
        angle = 2.0 * pi * i / segments
        offset = right * cos(angle) + up * sin(angle)

        v_h = bm.verts.new(mu.Vector(head) + offset * radius_head)
        v_t = bm.verts.new(mu.Vector(tail) + offset * radius_tail)
        verts_head.append(v_h)
        verts_tail.append(v_t)

    # Connect with faces
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new([verts_head[i], verts_head[j], verts_tail[j], verts_tail[i]])

    # Cap the ends
    bm.faces.new(verts_head)
    bm.faces.new(list(reversed(verts_tail)))
