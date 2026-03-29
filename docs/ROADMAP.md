# Deer Me — Future Enhancement Roadmap

## Current State

The core deer animation system is complete and working in Blender 5.1:
- 27-bone quadruped rig with IK-driven legs
- 3 gaits (walk, trot, gallop) with procedural spine, neck, tail dynamics
- State machine with cross-fade blending between locomotion modes
- Fluent Sequence API and compound preset behaviors
- Proxy mesh with automatic bone weighting
- 191 unit tests + 15 integration tests, all passing

This roadmap captures future enhancement ideas, roughly ordered by impact and buildability. Each phase is independent — pick whichever is most interesting.

---

## Phase A: Visual Quality — Better Mesh & Materials

**Goal:** Replace the cylinder-proxy with something that looks like an actual deer.

1. **Import a real deer mesh** — find or model a low-to-mid-poly deer (OBJ/FBX), import into Blender, bind to the existing armature with proper weight painting
2. **Material/texture pass** — fur-like shader (brown coat, white belly/tail patch), simple eye material
3. **Shape keys** (optional) — breathing chest expansion, nostril flare, ear flatten for startle

**Files:** `adapter/skin.py` (import + bind), new asset files in `assets/`

**Why first:** The animation is working but hard to appreciate on cylinders. A real mesh makes everything else more rewarding to work on.

---

## Phase B: Motion Refinement — Make It Feel Alive

**Goal:** Improve the quality of existing motion to look more natural.

1. **Foot contact / ground plane constraint** — feet shouldn't penetrate the ground during stance; add a ground-clamp pass after IK
2. **Shoulder/hip counter-rotation** — shoulders and hips should rotate opposite to the leg swing for realism
3. **Secondary motion** — ear bounce on impacts, tail lag on acceleration/deceleration, subtle skin jiggle
4. **Head stabilization** — compensate head rotation so it stays level during body pitch changes (birds and deer do this)
5. **Gait tuning** — adjust stride lengths, swing arcs, body bob amplitudes based on visual reference (slow-mo deer videos)

**Files:** `core/state_machine.py` (`_apply_locomotion`), `core/spine.py`, `core/gaits.py`, `core/ik_solver.py`

---

## Phase C: Terrain & Environment Interaction

**Goal:** The deer reacts to terrain instead of walking on a flat plane.

1. **Terrain-aware foot placement** — raycast from hip down to terrain surface, adjust IK targets to ground height
2. **Slope adaptation** — body tilts to match terrain slope, stride shortens on inclines
3. **Path following** — deer follows a spline/curve path, auto-orienting to the curve tangent
4. **Procedural terrain** — generate simple hilly terrain with noise, grass particle system

**Files:** new `core/terrain.py`, `adapter/scene.py` (terrain mesh), `core/state_machine.py` (foot target adjustment)

---

## Phase D: Behavioral Animation — Intelligence & Personality

**Goal:** The deer makes decisions, not just follows scripted commands.

1. **Head tracking / look-at** — deer looks toward a target object (curiosity, alertness)
2. **Idle variations** — weight shifting, ear flicks, tail swish, head shake, stamping foot
3. **Awareness system** — detect nearby objects/sounds, transition to alert pose, decide fight-or-flight
4. **Herd behavior** (stretch goal) — multiple deer with flocking: maintain spacing, follow a leader, scatter on startle

**Files:** new `core/behavior.py`, `api/deer.py` (new methods), `api/presets.py` (richer presets)

---

## Phase E: Camera & Rendering Pipeline

**Goal:** One-click beautiful renders of deer animations.

1. **Camera presets** — tracking shot (follow deer), orbit, dolly zoom on startle, wide establishing shot
2. **Camera shake** — subtle handheld feel, intensify during gallop
3. **Depth of field** — auto-focus on deer, rack focus during transitions
4. **Render pipeline script** — set output path, resolution, frame range, render engine settings, batch render
5. **Compositing** — basic post-processing node setup (color grading, vignette, motion blur)

**Files:** `adapter/scene.py` (camera rigs), new `adapter/render.py`, new `examples/04_render_sequence.py`

---

## Phase F: Developer Experience & Collaboration

**Goal:** Make it easy for a beginner to create new animations.

1. **Visual debug overlay** — draw skeleton wireframe, foot contact markers, state labels, IK targets in the 3D viewport
2. **Blender panel UI** — custom sidebar panel with play/pause, gait selector, speed slider, preset buttons
3. **Live preview mode** — real-time animation preview in the viewport without baking all frames first
4. **Documentation** — illustrated guide with screenshots showing the workflow end-to-end
5. **Notebook examples** — Jupyter notebooks explaining the math (gait curves, IK, quaternions) with interactive plots

**Files:** new `adapter/debug_overlay.py`, new `adapter/ui_panel.py`, `examples/`, `docs/`

---

## Phase G: Advanced Locomotion

**Goal:** Expand the movement vocabulary.

1. **Canter gait** — 3-beat asymmetric gait between trot and gallop
2. **Bounding/pronking** — all four feet leave the ground simultaneously (deer alarm display)
3. **Jumping** — single leap over obstacle with ballistic arc, takeoff and landing poses
4. **Swimming** — modified walk cycle with buoyancy bob, head above water
5. **Lying down / getting up** — complex multi-phase transition with weight shifting

**Files:** `core/gaits.py` (new gait params), `core/state_machine.py` (new states + transitions), `api/deer.py` (new methods)

---

## Suggested Starting Order

For maximum visual payoff with minimum effort:

1. **Phase A** (better mesh) — biggest visual improvement, mostly asset work
2. **Phase B.5** (gait tuning) — tweak numbers in `gaits.py` watching real deer reference
3. **Phase B.1** (ground contact) — stops foot sliding, huge realism boost
4. **Phase F.1** (debug overlay) — makes all future work faster to iterate on
5. **Phase D.1** (head tracking) — adds life with relatively simple math

Then go wherever curiosity leads.

---

## Verification Checklist

After each phase:
1. `pytest tests/unit/` — core math tests still pass
2. `blender --background --python scripts/run_in_blender.py -- pytest tests/integration/` — adapter tests pass
3. `blender --python examples/03_full_sequence.py` — visual check in Blender viewport
4. New features should include both unit tests (core layer) and at least one example script
