# Lessons Learned — Blender 5.x & Skeletal Animation

Hard-won fixes discovered while getting the deer animation pipeline working in Blender 5.1. These notes are for anyone contributing to this project or building similar Blender animation tools.

---

## Blender 5.x API Compatibility

### bpy.ops operators fail in background mode

`bpy.ops.object.select_all()`, `bpy.ops.object.delete()`, and `bpy.ops.object.parent_set()` all fail with "context is incorrect" in Blender 5.x background/headless mode.

**Why:** Blender 5.x tightened operator context requirements. Operators need a specific active area/context that doesn't exist in background mode.

**Fix:** Always use direct data API calls instead of operators:
- `bpy.data.objects.remove(obj, do_unlink=True)` instead of `select_all` + `delete`
- `mesh_obj.parent = arm_obj` + `modifiers.new("Armature", "ARMATURE")` instead of `bpy.ops.object.parent_set()`
- `bpy.ops.object.mode_set()` still works but check context first

### EEVEE engine renamed

`BLENDER_EEVEE_NEXT` (Blender 4.x) became `BLENDER_EEVEE` (Blender 5.x).

**Fix:** Try both names with `try/except TypeError` fallback. See `adapter/scene.py`.

### action.fcurves removed in layered actions

Blender 5.x uses layered actions. Direct `action.fcurves` no longer exists.

**Fix:** Use `keyframe_insert()` per bone per frame for writing (version-agnostic). For reading fcurves, use the helper in `adapter/keyframe.py`:
```python
def _get_action_fcurves(action):
    if hasattr(action, "is_action_layered") and action.is_action_layered:
        return list(action.layers[0].strips[0].channelbags[0].fcurves)
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    return []
```

### Blender's bundled Python doesn't have project dependencies

`pip install` into Blender's site-packages often fails (permissions, `ENABLE_USER_SITE=False`).

**Fix:** Use `sys.path.insert(0, src_dir)` at the top of scripts that run inside Blender. The `scripts/run_in_blender.py` helper adds both project `src/` and system site-packages so pytest and deer_me are found.

---

## Skeletal Animation Pipeline

### IK solver must be called — foot targets alone don't animate legs

The gait system computes foot target positions, but these are just Vec3 coordinates on hoof bones. Without actually calling the IK solver to compute upper/lower leg rotations, all leg bones stay at identity quaternion (no visible movement).

**Symptom:** Keyframes exist with correct frame counts, but the deer doesn't move its legs.

**Fix:** In `state_machine._apply_locomotion()`, after computing foot targets, call `solve_two_bone()` for each leg and set the resulting rotations on upper/lower bones. Front legs use `bend_axis=vec3(0,1,0)` (knees forward), rear legs use `vec3(0,-1,0)` (hocks backward).

### Only keyframe location for bones with explicit position changes

Writing `pose_bone.location` for every bone causes chaos. Most bones only have local parent-relative offsets from BoneDef. Subtracting Blender's world-space `head_local` from a local offset produces huge nonsensical displacements.

**Symptom:** The mesh is scattered/exploded — nothing looks like a deer.

**Fix:** `Pose._dirty_positions` (populated by `set_position()`) tracks which bones actually need location keyframes. Only root (body bob) and hooves (foot placement) get location keyframes. All other bones are rotation-only. See `adapter/keyframe.py`.

### Foot targets must use world-space rest positions

`compute_foot_target()` adds stride offset and foot lift to a rest position. If that rest position is a local offset instead of accumulated world-space, the targets end up near the origin instead of at the actual foot locations.

**Symptom:** IK targets are unreachable (legs fully extended or collapsed).

**Fix:** Use `skeleton.world_position(bone_name)` (sums `rest_position` up the parent chain) when computing foot targets for IK.

### Armature bones must be placed at world positions

Placing bone heads at local `rest_position` offsets and then using `use_connect` (which snaps child heads to parent tails) creates diagonal bone directions. The IK solver assumes leg bones point -Z (straight down), so rotations end up in the wrong coordinate frame.

**Symptom:** Legs rotate but in wrong directions — movement is visible but not recognizable as walking.

**Fix:** Use `skeleton.world_position()` for bone head placement in `create_armature()`. Point each bone's tail toward its chain child's world position. This ensures leg bones point approximately -Z, matching the IK solver's rest-direction assumption. See `adapter/rig.py`.
