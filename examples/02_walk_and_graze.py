"""Example 02: Walk and Graze

A deer walks into frame, slows down, and starts grazing.
Demonstrates the Sequence API and the graze preset.

Run inside Blender:
    blender --python examples/02_walk_and_graze.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deer_me.api.deer import Deer
from deer_me.api.sequence import Sequence
from deer_me.api import presets

# Create a deer and a timeline
deer = Deer(name="GrazingDeer", fps=24)
seq = Sequence(deer)

# Frame 1-72 (3 seconds): Walk in at normal speed
seq.at(1).walk(speed=1.0)

# Frame 73-120 (2 seconds): Slow to a gentle walk
seq.at(73).walk(speed=0.4)

# Frame 121 onward: Graze for 5 seconds (120 frames)
seq.at(121)
presets.graze(seq, duration_frames=120)

# Bake it all into Blender
arm_obj = seq.bake_to_blender(extra_frames=24, setup_scene=True, create_proxy=True)

print(f"Created '{arm_obj.name}' — walk → slow walk → graze")
print(f"Timeline: {seq.describe()}")
