"""Example 01: Basic Walk Cycle

The simplest possible deer animation — a 10-second walk.

Run inside Blender:
    blender --python examples/01_basic_walk.py

Or from the Blender scripting tab: paste and press Run.
"""

# Add the project to Python path (needed when running inside Blender)
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deer_me.api.deer import Deer

# Create a deer and tell it to walk
deer = Deer(name="BasicWalk", fps=24)
deer.walk(speed=1.0)
deer.update(0.5)  # Let the idle→walk transition complete

# Bake 10 seconds of animation into Blender
# This creates: scene (ground, lights, camera), armature, proxy mesh, keyframes
arm_obj = deer.bake_to_blender(num_frames=240, setup_scene=True, create_proxy=True)

print(f"Created '{arm_obj.name}' with 240 frames of walk animation.")
print("Press Space in the 3D viewport to play!")
