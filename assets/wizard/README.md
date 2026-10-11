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
- [`../../docs/V3PLUS-CHARACTER-ASSET-CONTRACT.md`](../../docs/V3PLUS-CHARACTER-ASSET-CONTRACT.md)

### Key Checklist Summary

1. **Format**: Binary glTF 2.0 (`.glb`).
2. **Coordinate System & Scale**:
   - World up: `+Y`.
   - Local authored forward: `+Z` in Blender / asset space. (The runtime normalization wrapper handles rotating this local +Z forward convention into the established V3 world stance toward the +X target monolith; artists must NOT pre-rotate the character into world +X).
   - Character feet / robe hem grounded at local `Y = 0` (centered horizontally at `(0, 0, 0)`).
   - Preferred authored character height: `3.8 m ± 0.4 m` (approximately `3.4 m – 4.2 m`, measured from grounded feet/robe hem to top of hat). The runtime normalization wrapper may normalize different but otherwise valid authored scales.
3. **Named Attachment Points**:
   - **Required Attachments (P0)** (Missing any required attachment fails validation, rejects the authored asset, and retains procedural V3; no missing required attachment silently falls back to world origin):
     - `spell_origin`: Center of the magical gem/crystal at the staff head (where projectiles launch and vortex particles converge). **Never place at `(0,0,0)`.**
     - `staff_grip`: Right hand socket node gripping the staff. **Required.** If missing, validation fails, authored GLB is not activated, and procedural V3 remains active.
     - `head`: Head center / face orientation node (for hero camera framing and rim lighting). **Required.** If missing, validation fails, authored GLB is not activated, and procedural V3 remains active.
   - **Recommended Attachments**:
     - `camera_target`: Look-at framing focus node (at upper chest / collarbone level, `y ~2.5m–2.8m`). **Recommended, not required.** If absent, falls back to `head` attachment position minus a documented downward Y offset (~0.3m) for framing. Asset must NOT fail validation solely because `camera_target` is absent.
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
