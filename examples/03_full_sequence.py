"""Example 03: Full Sequence — A Day in the Life

A complete deer animation combining multiple behaviors:
1. Deer approaches cautiously (slow walk)
2. Looks around for danger
3. Grazes peacefully
4. Startles at a noise
5. Flees at full gallop

Demonstrates chaining presets, manual commands, and the Sequence API together.

Run inside Blender:
    blender --python examples/03_full_sequence.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deer_me.api.deer import Deer
from deer_me.api.sequence import Sequence
from deer_me.api import presets

deer = Deer(name="StoryDeer", fps=24)
seq = Sequence(deer)

# --- Act 1: Cautious Approach (frames 1-144, ~6 seconds) ---
# The deer enters the clearing slowly, looking around
seq.at(1)
presets.approach_and_graze(seq, duration_frames=144)

# --- Act 2: Peaceful Grazing (frames 145-288, ~6 seconds) ---
# Continues grazing contentedly
seq.hold(0)  # Continue from where approach_and_graze left off
presets.graze(seq, duration_frames=144)

# --- Act 3: Startle and Flee (frames 289-432, ~6 seconds) ---
# A branch snaps! The deer freezes, then bolts
seq.hold(0)
presets.startle(seq, pause_frames=24)    # 1 second freeze
presets.flee(seq, duration_frames=120)   # 5 seconds of acceleration

# Bake the full 18-second animation
arm_obj = seq.bake_to_blender(extra_frames=24, setup_scene=True, create_proxy=True)

# Print the timeline
print("=" * 60)
print("  A Day in the Life — Deer Animation")
print("=" * 60)
print(seq.describe())
print()
print(f"Armature: '{arm_obj.name}'")
print("Press Space to play!")
