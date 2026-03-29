# Deer Me

A quadruped deer animation system for Blender, built in Python with a testable three-layer architecture.

## What It Does

Deer Me provides a high-level API for creating realistic deer locomotion in Blender. Instead of manually keyframing dozens of bones, you write simple commands:

```python
from deer_me.api.deer import Deer
from deer_me.api.sequence import Sequence

seq = Sequence()
seq.at(frame=0).walk(speed=1.0)
seq.at(frame=120).trot(speed=1.5)
seq.at(frame=240).idle(variation="graze")
seq.render_to_blender()
```

The system handles gait cycles, foot placement, spine dynamics, IK solving, and smooth transitions between states automatically.

## Architecture

The codebase is split into three layers so the core math can be tested without Blender:

```
Layer 3: Animator API        High-level commands (walk, trot, idle, turn)
Layer 2: Locomotion Engine   Pure Python — gaits, IK, spine, state machine
Layer 1: Blender Adapter     Reads/writes bone transforms and keyframes via bpy
```

**Layer 2 has zero Blender imports.** This is what makes the unit tests fast (~0.4s for 147 tests).

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
tests/
    unit/           Fast tests — no Blender needed
    integration/    Blender headless tests
examples/           Runnable demo scripts
```

## Setup

### Requirements

- Python 3.11+
- Blender 4.x (for rendering — not needed for core development/testing)

### Install

```bash
# Clone the repo
git clone https://github.com/mortgoldman/deer_me.git
cd deer_me

# Install in development mode
pip install -e ".[dev]"
```

### Run Tests

```bash
# Unit tests (fast, no Blender needed)
pytest tests/unit/ -v

# All tests (integration tests auto-skip if Blender not installed)
pytest tests/ -v

# Integration tests inside Blender (requires Blender 4.x)
blender --background --python scripts/run_in_blender.py -- pytest tests/integration/ -v
```

## Current Status

- **Phase 1** — Foundation: types, skeleton, interpolation
- **Phase 2** — Locomotion engine: gaits, IK solver, spine dynamics
- **Phase 3** — State machine with cross-fade blending
- **Phase 4** — Blender adapter (armature, keyframes, scene, skinning)
- Phase 5 — Animator API (next)
- Phase 6 — Polish and onboarding

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
