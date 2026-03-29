# Deer Me

A quadruped deer animation system for Blender, built in Python with a testable three-layer architecture.

## What It Does

Deer Me provides a high-level API for creating realistic deer locomotion in Blender. Instead of manually keyframing dozens of bones, you write simple commands:

```python
from deer_me.api.deer import Deer
from deer_me.api.sequence import Sequence
from deer_me.api import presets

deer = Deer(fps=24)
seq = Sequence(deer)

seq.at(1).walk(speed=1.0)       # Start walking
seq.at(120).trot(speed=1.5)     # Speed up to a trot
seq.at(240).idle()              # Slow to a stop

# One call to bake into Blender (creates scene, armature, mesh, keyframes)
seq.bake_to_blender()
```

The system handles gait cycles, foot placement, spine dynamics, IK solving, and smooth transitions between states automatically.

## Architecture

The codebase is split into three layers so the core math can be tested without Blender:

```
Layer 3: Animator API        High-level commands (walk, trot, idle, turn)
Layer 2: Locomotion Engine   Pure Python — gaits, IK, spine, state machine
Layer 1: Blender Adapter     Reads/writes bone transforms and keyframes via bpy
```

**Layer 2 has zero Blender imports.** This is what makes the unit tests fast (~0.8s for 191 tests).

## Project Structure

```
src/deer_me/
    core/           Pure Python locomotion engine (no Blender)
        types.py        Vec3, Quaternion, Pose, skeleton data classes
        skeleton.py     27-bone deer rig with anatomical proportions
        gaits.py        Walk, trot, gallop cycle definitions
        ik_solver.py    Two-bone IK for leg placement
        spine.py        Procedural spine, neck, and tail dynamics
        interpolation.py  Easing functions, pose blending, splines
        state_machine.py  Locomotion states with cross-fade blending
    adapter/        Blender bridge (lazy bpy imports — works without Blender)
        rig.py          Create armature from skeleton, apply/reset poses
        keyframe.py     Insert pose keyframes, batch fcurve writer
        scene.py        Ground plane, 3-point lighting, camera
        skin.py         Mesh binding, proxy deer mesh generator
    api/            Animator-facing commands and sequencer
        deer.py         High-level Deer class: walk(), trot(), idle(), turn()
        sequence.py     Fluent timeline builder for scripted animations
        presets.py      Compound behaviors: graze, startle, flee, patrol
tests/
    unit/           Fast tests — no Blender needed (191 tests)
    integration/    Blender headless tests (15 tests, auto-skipped without bpy)
examples/           Runnable demo scripts
scripts/            Blender setup and runner helpers
```

## Getting Started

### Requirements

- **Python 3.11+**
- **Blender 4.x or 5.x** (for rendering — not needed for core development/testing)

### Install for Development

```bash
git clone https://github.com/mortgoldman/deer_me.git
cd deer_me
pip install -e ".[dev]"
```

### Set Up Blender (one time)

After installing Blender, run the setup script to install deer_me into Blender's bundled Python:

```bash
blender --background --python scripts/setup_blender.py
```

### Run Tests

```bash
# Unit tests (fast, no Blender needed)
pytest tests/unit/ -v

# All tests (integration tests auto-skip if Blender not installed)
pytest tests/ -v

# Integration tests inside Blender
blender --background --python scripts/run_in_blender.py -- pytest tests/integration/ -v
```

## Examples

Three example scripts are included in the `examples/` folder. Run them inside Blender:

### 01 — Basic Walk

A 10-second walk cycle. The simplest possible animation.

```bash
blender --python examples/01_basic_walk.py
```

### 02 — Walk and Graze

A deer walks in, slows down, and grazes. Uses the Sequence API and the `graze` preset.

```bash
blender --python examples/02_walk_and_graze.py
```

### 03 — Full Sequence: A Day in the Life

A complete 18-second story combining multiple presets:
1. Cautious approach (slow walk, looking around)
2. Peaceful grazing
3. Startle at a noise (freeze)
4. Flee at full gallop

```bash
blender --python examples/03_full_sequence.py
```

## Quick Reference

### Deer Class

```python
deer = Deer(fps=24)

deer.walk(speed=1.0)      # Lateral sequence gait
deer.trot(speed=1.3)      # Diagonal pair gait
deer.gallop(speed=2.0)    # Gathered gallop (must trot first)
deer.idle()               # Stand still (must slow down from gallop first)
deer.turn_left(speed=1.0) # Walk-based left turn
deer.turn_right(speed=1.0)

deer.update(dt)           # Advance by dt seconds
deer.pose()               # Get current Pose
deer.bake_to_blender(240) # One-call Blender export
```

### Sequence API

```python
seq = Sequence(deer)
seq.at(0).walk()          # Command at frame 0
seq.at(120).trot()        # Command at frame 120
seq.hold(60).idle()       # Wait 60 frames, then idle
frames = seq.bake()       # Returns [(frame, Pose), ...]
seq.bake_to_blender()     # Direct Blender export
```

### Presets

```python
from deer_me.api import presets

seq = Sequence(deer)
seq.at(0)
presets.graze(seq, duration_frames=120)       # Walk slowly, then graze
presets.startle(seq, pause_frames=18)         # Alert freeze
presets.flee(seq, duration_frames=96)         # Walk → trot → gallop
presets.look_around(seq, duration_frames=96)  # Turn left → right → forward
presets.patrol(seq, duration_frames=240)      # Walk → pause → look → walk
presets.approach_and_graze(seq, duration_frames=240)
```

## The Deer Rig

The skeleton is a 27-bone quadruped rig scaled to a white-tailed deer (~1m shoulder height):

- 3 spine bones with lateral sway and vertical undulation
- 3 neck/head bones with pitch compensation and head stabilization
- 4 legs (4 bones each) with two-bone IK and gait-driven foot placement
- 2 ear bones
- 2 tail bones with trailing sway

Three gaits are supported with anatomically correct timing:

| Gait   | Pattern           | Duty Factor | Stride  |
|--------|-------------------|-------------|---------|
| Walk   | Lateral sequence  | 65%         | 0.55m   |
| Trot   | Diagonal pairs    | 50%         | 0.80m   |
| Gallop | Gathered          | 35%         | 1.40m   |

## License

MIT
