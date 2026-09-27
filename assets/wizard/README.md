# Wizard V3+ Authored Asset Directory

This directory is designated for the future authored 3D character asset in **Wizard V3+**.

## Canonical Asset Path

```
assets/wizard/wizard.glb
```

## Status: Awaiting Authored Blender/GLB Asset

As of **Wizard V3+ Pass A**, no authored GLB model is present. This is expected.
The procedural character implementation in `wizard-v3.html` serves as the complete, frozen production baseline and the permanent runtime fallback.

**Do NOT commit placeholder binary files or random models.**

## Asset Requirements & Integration Contract

Before exporting and placing a model here, consult the complete specification:
- [`../../V3PLUS-CHARACTER-ASSET-CONTRACT.md`](../../V3PLUS-CHARACTER-ASSET-CONTRACT.md)

### Key Checklist Summary

1. **Format**: Binary glTF 2.0 (`.glb`).
2. **Coordinate System**:
   - Y-up world orientation.
   - Character feet grounded at `(0, 0, 0)`.
   - Character standing height ~3.6m–4.0m (to top of hat tip).
3. **Required Named Attachment Points**:
   - `spell_origin`: Center of the magical gem/crystal at the staff head (where projectiles launch and vortex particles converge). **Never place at `(0,0,0)`.**
   - `staff_grip`: Right hand socket node gripping the staff.
   - `head`: Head center / face orientation node (for hero camera framing and rim lighting).
   - `camera_target`: Look-at framing focus node (at chest/neck level, y ~2.6m–3.0m).
4. **Required Skeletal Animations**:
   - `idle` (looping breathing and idle stance)
   - `charge` (staff raised back, somatic hand extending)
   - `cast` (snap thrust at 15% phase, recoil, follow-through)
   - `recover` (relaxing back to rest stance)
5. **Event Ownership**:
   - The `SpellDirector` owns all spell timing, simulation steps, and projectile release events (strictly at 15% of CAST phase).
   - Animation clips **must not** fire spell events or projectiles from clip callbacks.

## Pre-Integration Validation

Run the standalone validation utility against any candidate asset:

```bash
python3 tools/validate_wizard_glb.py assets/wizard/wizard.glb
```

Only assets that achieve a clean `RESULT: PASS` exit code (`0`) are eligible for activation in the V3+ runtime.
