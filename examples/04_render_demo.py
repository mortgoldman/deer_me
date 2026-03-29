"""Example 04: Render a Demo Video

Renders the full deer animation sequence to PNG frames, then optionally
combines them into an MP4 with ffmpeg.

Run inside Blender:
    blender --background --python examples/04_render_demo.py

Output: renders/frames/0001.png through NNNN.png

To combine into video (requires ffmpeg):
    ffmpeg -framerate 24 -i renders/frames/%04d.png -c:v libx264 -pix_fmt yuv420p renders/deer_demo.mp4
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import bpy
import mathutils

from deer_me.api.deer import Deer
from deer_me.api.sequence import Sequence
from deer_me.api import presets

# ---------------------------------------------------------------------------
# Output settings
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.path.join(PROJECT_ROOT, "renders", "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Build the animation
# ---------------------------------------------------------------------------

deer = Deer(name="DemoDeer", fps=24)
seq = Sequence(deer)

# Act 1: Walk in from the right (frames 1-96, 4 seconds)
seq.at(1).walk(speed=0.8)

# Act 2: Slow to idle, look around (frames 97-192, 4 seconds)
seq.at(97).idle()
seq.hold(24)
presets.look_around(seq, duration_frames=72)

# Act 3: Start grazing (frames 193-288, 4 seconds)
seq.hold(0)
presets.graze(seq, duration_frames=96)

# Act 4: Startle and flee! (frames 289-432, 6 seconds)
seq.hold(0)
presets.startle(seq, pause_frames=18)
presets.flee(seq, duration_frames=120)

# Bake
arm_obj = seq.bake_to_blender(extra_frames=12, setup_scene=True, create_proxy=True)

# ---------------------------------------------------------------------------
# Camera setup — side view tracking the deer
# ---------------------------------------------------------------------------

scene = bpy.context.scene
cam = scene.camera

# Position camera for a nice 3/4 side view
cam.location = mathutils.Vector((3.5, -5.0, 1.8))
look_at = mathutils.Vector((0, 0, 0.7))
direction = look_at - cam.location
rot_quat = direction.to_track_quat("-Z", "Y")
cam.rotation_euler = rot_quat.to_euler()

# Wider lens to see the full scene
cam.data.lens = 35.0

# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24

# Output format: PNG frames
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = os.path.join(FRAMES_DIR, "")

# EEVEE quality settings
scene.eevee.taa_render_samples = 32
scene.render.film_transparent = False

# Background color — light sky blue
scene.world.use_nodes = True
world_nodes = scene.world.node_tree.nodes
bg_node = world_nodes.get("Background")
if bg_node:
    bg_node.inputs["Color"].default_value = (0.53, 0.72, 0.90, 1.0)
    bg_node.inputs["Strength"].default_value = 1.0

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

total_frames = scene.frame_end - scene.frame_start + 1
duration_sec = total_frames / scene.render.fps

print("=" * 60)
print("  Deer Me — Rendering Demo Frames")
print("=" * 60)
print(f"  Frames:     {scene.frame_start} - {scene.frame_end} ({total_frames} frames)")
print(f"  Duration:   {duration_sec:.1f} seconds")
print(f"  Resolution: {scene.render.resolution_x}x{scene.render.resolution_y}")
print(f"  Output:     {FRAMES_DIR}/")
print("=" * 60)
print()

bpy.ops.render.render(animation=True)

print()
print(f"Done! {total_frames} frames rendered to: {FRAMES_DIR}/")
print()
print("To combine into MP4 (requires ffmpeg):")
print(f'  ffmpeg -framerate 24 -i "{FRAMES_DIR}/%04d.png" -c:v libx264 -pix_fmt yuv420p renders/deer_demo.mp4')
