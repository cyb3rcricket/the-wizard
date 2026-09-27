# WIZARD V3+ — CHARACTER ASSET CONTRACT & BLENDER/GLB HANDOFF SPECIFICATION

```
Document Version: 1.0.0
Status: APPROVED PRODUCTION SPECIFICATION
Baseline: Wizard V3 (commit 24ec0baf0236bb24c0eb2f0a2f6ed487d6c851f9)
Target Pipeline: Blender 4.x+ -> glTF 2.0 Binary (.glb) -> Three.js r180
Validator Tool: tools/validate_wizard_glb.py
```

---

## 1. Executive Summary & Core Architectural Principle

Wizard V3 is **COMPLETE** and functions as a frozen production baseline. This specification defines the exact, production-grade technical and artistic contract required to introduce an authored, rigged 3D wizard character into the **Wizard V3+** runtime.

### Core Invariant

> **The authored asset must conform to the world; the world must NOT be redesigned around the asset.**

All existing world-space coordinates, fixed-step simulation systems, spell timing, particle vortexes, projectile trajectories, impact detonations, audio events, camera choreography, and lighting hierarchies are preserved without regression.

When an authored asset (`assets/wizard/wizard.glb`) is provided:
- If it passes all validation requirements, the application atomically swaps the procedural character for the authored character adapter (`GLBCharacter`).
- If no asset is present, or if an asset fails any required contract check, the complete procedural V3 character remains active indefinitely as the reliable fallback.
- Magic must **never** launch from `(0, 0, 0)` or the character root.

---

## 2. Character Boundary Audit: Current Architecture vs Contract

An exhaustive audit of the frozen V3 implementation (`wizard-v3.html`) reveals the current character boundaries, dependencies, and integration gaps:

### 2.1 Current Implementation Summary

| Component | Current Class | Responsibilities & Ownership |
|---|---|---|
| **Procedural Character** | `WizardCharacter` (lines 1244–2763) | Procedural node hierarchy (`this.nodes`), rest pose caching (`this.restPose`), pose interpolation (`setPoseIdle`, `setPoseCharge`, `setPoseCast`, `setPoseRecover`), secondary physics for beard lock damping and hat spine curvature, embedded gem light (`this.nodes.gemLight`), and orbital metallic rings. |
| **Character Adapter** | `CharacterAdapter` (lines 2766–2829) | Bridges the simulation sample to the character instance. Implements `applyPose()`, `capturePoseSnapshot()`, `resetToRest()`, `getGemWorldPosition()`, `getSpellDirection()`, `getAttachment()`, `getBounds()`, and `dispose()`. |
| **Spell Timeline** | `SpellDirector` (lines 4742–4864) | Authoritative owner of state machine (`IDLE`, `CHARGE`, `CAST`, `RECOVER`), normalized phase progress ($0.0 \to 1.0$), simulation delta accumulator, cast ID, and event-once guards. Holds **zero** rendering meshes or materials. |
| **Projectile System** | `ProjectileSystem` (lines 4280–4488) | Consumes `launch(origin, target, normal, castId)`. Computes ballistic arc and ribbon history independently from character pose. |
| **VFX Engine** | `ParticleEngine` (lines 3522–4278) | Samples `gemWorldPos` each fixed step to draw charge vortex particles inward; emits release burst at `gemWorldPos` along `strikeDir`. |
| **Camera Director** | `CameraDirector` (lines 4495–4740) | Controls camera presets (`cinematic`, `classic`, `hero`, `target`, `orbit`). Currently hardcodes Hero look-at target to `(-4.3, 3.2, 0.0)`. |
| **App Coordination** | `App` (lines 5046–5676) | Drives 120Hz fixed simulation loop, orchestrates systems, manages render mode switching, HUD, and lifecycle disposal. |

### 2.2 Interface Conformance & Architectural Gaps

The V3 implementation plan defined the intended adapter boundary:
```typescript
interface CharacterAdapter {
  applyPose(sample: SpellSample, simDt: number, blendSnapshot?: PoseSnapshot, recoverySnapshot?: PoseSnapshot): void;
  getGemWorldPosition(outVec: THREE.Vector3): THREE.Vector3;
  getSpellDirection(outVec: THREE.Vector3, targetPos: THREE.Vector3): THREE.Vector3;
  getAttachment(name: string, outTransform: THREE.Matrix4): THREE.Matrix4;
  getBounds(outBox: THREE.Box3): THREE.Box3;
  dispose(): void;
}
```

#### Actual Gaps Identified in Current Codebase:

1. **Direct Coupling in App Fixed Loop**:
   - In `App.fixedUpdate`, lines 5486 and 5530 invoke `this.wizard.getGemWorldPosition(this.gemWorldPos)` directly on the concrete procedural instance instead of delegating through `this.characterAdapter.getGemWorldPosition(...)`.
   - Line 5479 invokes `this.wizard.group.updateMatrixWorld(true)` directly on the procedural group.
2. **Transform Diagnostic Coupling**:
   - `App.checkFiniteTransforms` (lines 5337–5340) checks `this.wizard.nodes.body.position.y`, `this.wizard.nodes.gemMesh.material.emissiveIntensity`, and `this.wizard.nodes.gemLight.intensity`. A future `GLBCharacter` adapter must expose a generic finite/health check or adapter-level status method.
3. **Attachment Name Coverage**:
   - Current `CharacterAdapter.getAttachment` only maps `'gem'` and `'head'`. The contract requires standardized naming: `'spell_origin'`, `'staff_grip'`, `'head'`, and `'camera_target'`.
4. **Camera Framing Coupling**:
   - `CameraDirector.setPreset('hero')` hardcodes `baseLookAt` to `(-4.3, 3.2, 0.0)`. It should query `characterAdapter.getAttachment('camera_target', mat)` to dynamically adapt to varying character heights.
5. **Pose Snapshot Semantic Representation**:
   - `capturePoseSnapshot()` in procedural V3 returns an object containing procedural Euler rotations for body, arms, beard segments, and hat segments. For a skeletal GLB, snapshots must capture bone transforms or AnimationMixer action weights/times for early-release crossfading.

---

## 3. Coordinate & Normalization Contract

The authored character model must export cleanly from Blender into a self-contained GLB file without altering world coordinates.

```
                           +Y (World Up)
                             ^
                             |       Staff Gem (spell_origin)
                             |          [O] ~3.2m - 3.6m
                             |         / |
                      Head   |     (o)   |
                  ~2.9m-3.2m |    / | \  |
                             |   /  |  \ |
                             |  *   *   *|  Staff Grip ~1.8m - 2.2m
                             |     / \   |
                             |    /   \  |
                             |   [Robe ] |
                             |  /       \|
    -------------------------+-----------+--------------------> +X (Toward Monolith Target)
      Ground Origin (0,0,0)  |  Feet/Hem
```

### 3.1 Spatial Conventions

| Dimension | Specification | Standard glTF Rule |
|---|---|---|
| **World Up Axis** | **+Y** | `+Y` is Up in both Blender glTF exporter and Three.js. |
| **Character Forward** | **+Z** in local asset space | Facing positive Z in local space (or negative Z matching glTF camera conventions). The normalization wrapper orients the model toward world **+X** (facing the target monolith). |
| **Character Ground** | **Y = 0.0** at soles / robe hem | The character's feet / bottom of robe must rest precisely on the ground plane ($Y=0.0$). The origin $(0, 0, 0)$ must be positioned horizontally centered between the feet. |
| **World Stance Position** | `(-4.5, 0.0, 0.0)` | The character stands at $(-4.5, 0, 0)$ on the dais in world space. |
| **Root World Rotation** | Yaw = $0.44 \times \pi$ rad ($\approx 79.2^\circ$) | Three-quarter heroic spellcaster stance angled toward the monolith at $(10.2, 3.4, 0.0)$. |

### 3.2 Normalization Wrapper Behavior

The runtime `GLBCharacter` adapter must wrap the loaded GLB scene inside an outer normalization container:

```javascript
const wrapper = new THREE.Group();
wrapper.name = 'AuthoredWizard_NormalizationWrapper';
wrapper.position.set(-4.5, 0.0, 0.0);
wrapper.rotation.y = Math.PI * 0.44; // Align 3/4 heroic stance facing +X target
```

1. **Auto-Centering**: If the model base is slightly offset from local $(0,0,0)$, the wrapper adjusts internal position so the ground contact sits at local $Y=0.0$.
2. **Height Normalization**:
   - The reference height for the procedural wizard is **3.8m** (measured from ground to the tip of the curved hat).
   - If the authored character's bounding height deviates significantly (e.g. exported in centimeters where height is 380 units instead of 3.8), the wrapper automatically applies a uniform scale factor:
     $$S = \frac{3.8}{\text{bbox.max.y} - \text{bbox.min.y}}$$
   - If scale is already within $3.0\text{m} \le \text{height} \le 4.5\text{m}$, uniform scale remains $1.0$.

---

## 4. Attachment Contract

Named attachment points are empty nodes, locator objects, or dedicated bones exported within the glTF scene hierarchy.

### 4.1 Required Attachments

| Attachment Name | Required | Parent / Location | Expected Coordinates (Local) | Consuming System | Failure / Fallback Behavior |
|---|---|---|---|---|---|
| `spell_origin` | **YES (P0)** | Child of Staff bone or Gem bone, at the geometric center of the focus crystal. | $X \approx 0.3 - 0.7$, $Y \approx 3.0 - 3.6$, $Z \approx 0.2 - 0.6$ (staff raised stance) | `ParticleEngine` (vortex anchor & release burst), `ProjectileSystem` (launch origin), `PointLight` (gem glow). | **FATAL CONTRACT BREACH.** Model rejected immediately. Procedural wizard remains active. **NEVER** launch from $(0,0,0)$ or root. |
| `staff_grip` | **YES (P0)** | Child of Right Hand bone (`hand.R` / `RightHand`). Located at palm center. | Matches right hand palm transform. | Attaches staff geometry if exported as separate node; establishes arm-to-weapon kinematics. | Model rejected or warning issued if staff is embedded. |
| `head` | **YES (P0)** | Child of Head bone (`head`). Located at face/eye level. | $X \approx 0.0$, $Y \approx 2.8 - 3.2$, $Z \approx 0.0 - 0.2$ | `CameraDirector` (Hero portrait framing), character accent lighting. | Falls back to bounding box center $(0, 2.8, 0)$ with warning. |
| `camera_target` | Recommended | Child of Chest or Neck bone. Centered at upper chest / collarbone. | $X \approx 0.0$, $Y \approx 2.5 - 2.8$, $Z \approx 0.0$ | `CameraDirector` (Cinematic, Classic, and Hero look-at target). | Falls back to `head` attachment position minus $0.3\text{m}$ Y offset. |
| `somatic_hand` | Optional | Child of Left Hand bone (`hand.L` / `LeftHand`). Located at fingertips / palm. | $X \approx -0.4 - -0.8$, $Y \approx 2.0 - 2.6$, $Z \approx 0.2 - 0.5$ | Optional somatic spell charging sparks / runes. | Ignored if absent. |

### 4.2 Invariant: Missing `spell_origin` Protection

```
                                  [GLB Loaded]
                                       |
                         Does 'spell_origin' node exist?
                                  /          \
                             YES /            \ NO
                                /              \
        Is dist(spell_origin, (0,0,0)) > 0.5?   [REJECT ASSET]
                     /             \                    |
                YES /               \ NO        [Log Fatal Error]
                   /                 \                  |
        [Accept Attachment]      [REJECT ASSET] [Retain Procedural V3]
```

Under no circumstances may a missing or origin-coincident `spell_origin` be tolerated.

---

## 5. Rig Contract

The character must be rigged using a standard humanoid/fantasy skeletal armature.

### 5.1 Semantic Bone Hierarchy

Artists may use Blender Rigify, Auto-Rig Pro, or a custom armature, provided nodes or bones map cleanly to these semantic functions:

```
Root (Ground level 0,0,0)
 └── Pelvis / Hips
      ├── Spine_01 -> Spine_02 -> Chest
      │    ├── Neck -> Head
      │    │    └── [Optional] Beard_Chain (Beard_01 -> Beard_02 -> Beard_03)
      │    │    └── [Optional] Hat_Chain (Hat_01 -> Hat_02 -> Hat_03 -> Hat_Tip)
      │    ├── Left_Clavicle -> Left_UpperArm -> Left_Forearm -> Left_Hand
      │    └── Right_Clavicle -> Right_UpperArm -> Right_Forearm -> Right_Hand (staff_grip)
      │         └── [Optional] Staff_Root -> Staff_Gem (spell_origin)
      ├── Left_Thigh -> Left_Calf -> Left_Foot -> Left_Toe
      └── Right_Thigh -> Right_Calf -> Right_Foot -> Right_Toe
```

### 5.2 Rig Semantic Aliases (Mapping Table)

The future `GLBCharacter` adapter uses the following dictionary for bone resolution:

| Semantic Slot | Common Blender Rigify Names | Mixamo / Generic Names |
|---|---|---|
| `root` | `root`, `Armature` | `Root`, `CharacterRoot` |
| `hips` | `hips`, `pelvis`, `spine` | `Hips`, `Pelvis` |
| `chest` | `chest`, `spine.002`, `spine.003` | `Spine2`, `Chest` |
| `head` | `head`, `head_socket` | `Head` |
| `staff_arm` | `upper_arm.R`, `forearm.R`, `hand.R` | `RightArm`, `RightForeArm`, `RightHand` |
| `somatic_arm` | `upper_arm.L`, `forearm.L`, `hand.L` | `LeftArm`, `LeftForeArm`, `LeftHand` |
| `legs` | `thigh.L/R`, `shin.L/R`, `foot.L/R` | `LeftUpLeg`, `LeftLeg`, `LeftFoot` |

---

## 6. Animation Contract

The authored character must export four primary skeletal animation clips.

### 6.1 Required Clips Specification

| Clip Name | Loop Mode | Nominal Duration | Visual Stance & Semantic Function |
|---|---|---|---|
| `idle` | Loop | $2.0\text{s} - 4.0\text{s}$ | Heroic standing 3/4 posture. Gentle breathing in chest, subtle sway in beard and robe, staff held firmly with gem elevated to side of hat (clear silhouette separation from head). |
| `charge` | Clamp / Hold | $1.0\text{s} - 2.0\text{s}$ | Casting preparation. Staff drawn back and upward, chest expanding, left somatic hand extending toward target with fingers flexing, leaning slightly back into rear foot. |
| `cast` | Play Once | $1.0\text{s} - 1.5\text{s}$ | **Primary spell release.** Snap thrust forward peaking at exactly **15% phase** (`progress = 0.15`), staff drives forward pointing directly at monolith, followed by recoil from 15%–35%, and relaxing follow-through from 35%–100%. |
| `recover` | Play Once | $0.8\text{s} - 1.2\text{s}$ | Resetting from casting follow-through back to steady `idle` stance. Weight shifts back to center, arms return to rest positions. |

### 6.2 Event Authority Rule

> **CRITICAL RULE: Animation clips NEVER own spell events.**

- The `SpellDirector` owns all simulation timing, state transitions, and event dispatches.
- The projectile release occurs strictly when `SpellDirector` reaches **15% of CAST** (`sample.progress >= 0.15`).
- Do **NOT** fire projectiles or trigger audio/VFX from:
  - AnimationMixer callbacks (`'finished'`, `'loop'`)
  - Blender animation markers / event tracks
  - Clip completion percentages
  - Hard-coded animation frame numbers

### 6.3 Phase Remapping Strategy

Rather than letting Three.js `AnimationMixer.update(realDt)` run on its own unsynchronized clock, the `GLBCharacter` adapter explicitly sets action time derived from the `SpellDirector` sample:

$$\text{action.time} = \text{sample.progress} \times \text{clip.duration}$$

Benefits of phase remapping:
1. **Speed Invariance**: When the user switches playback speed to $0.25\times$, $1.0\times$, or $1.8\times$, the skeletal animation stays locked frame-for-frame to the charge vortex and projectile release.
2. **Fixed-Step Determinism**: 120Hz fixed simulation guarantees identical skeletal poses across any hardware frame rate.
3. **Early Manual Release**: If the user clicks "Release" early during `CHARGE`, the adapter captures the current skeletal pose snapshot and uses `Action.crossFadeTo()` over $0.15\text{s}$ to blend smoothly into the forward thrust without popping.
4. **Recovery Retriggering**: If the user clicks "Charge" during `RECOVER`, the adapter smoothly blends from the current pose into `charge`.

---

## 7. Secondary Motion Contract

### 7.1 Motion Layer Ownership

1. **Layer 0 (Base Pose — AnimationMixer)**:
   - Owns all core skeletal bones: Pelvis, Spine, Chest, Neck, Head, Clavicles, Arms, Hands, Legs, Feet.
   - Authored keyframes in the glTF clips dictate 100% of these base transforms.
2. **Layer 1 (Additive Secondary Motion — Procedural Spring Physics)**:
   - Evaluated **strictly after** the mixer update on designated leaf nodes.
   - Permitted nodes only:
     - Beard tips (`beard_02`, `beard_03`)
     - Hat tip (`hat_04`, `hat_tip`)
     - Robe fringe / hem dangling accessories
     - Staff hanging talisman / ribbon

### 7.2 Explicit Prohibitions

- **No Competing Transform Writers**: Secondary physics must never write to bones that are actively driven by the base animation without additive blending.
- **No Runtime Cloth Simulation**: Do not introduce Verlet cloth or particle grids for robes. Robe movement must be authored in the skeleton or handled by skinning weights.
- **No Runtime Hair Simulation**: Hair/beard strands must be rigged to bones or sculpted geometry.

---

## 8. Material & Art Direction Contract

The authored wizard must preserve the visual identity established in V3:

```
  +--------------------------------------------------------------+
  |                   WIZARD VISUAL HIERARCHY                    |
  +--------------------------------------------------------------+
  |  HAT:         Crooked/bent pointed hat, midnight plum wool   |
  |  FACE/BEARD:  Readable facial features, flowing silver beard |
  |  ROBE:        Deep plum / magenta family, heavy woven wool   |
  |  ACCENTS:     Restrained antique gold embroidery & clasp     |
  |  STAFF:       Gnarled ancient dark wood with bronze fittings |
  |  FOCUS GEM:   Large multifaceted cyan crystal (emissive HDR) |
  |  SILHOUETTE:  High negative space between staff, head & hand |
  +--------------------------------------------------------------+
```

### 8.1 Three.js r180 Color Management Compatibility

- **Linear Working Color Space**: Three.js r180 operates strictly in Linear-sRGB.
- **Texture Color Spaces**:
  - Base Color / Albedo maps: `sRGB` transfer function (`texture.colorSpace = THREE.SRGBColorSpace`).
  - Roughness / Metalness / Normal / Occlusion maps: Linear (`texture.colorSpace = THREE.NoColorSpace`).
  - Emissive maps: `sRGB` transfer function.
- **Tone Mapping**: ACESFilmic tone mapping with exposure $1.0$.
- **Environment Lighting**: Image-Based Lighting via scene PMREM cubemap/HDR. Materials must use Standard PBR Metallic-Roughness.

### 8.2 Bloom & Emissive Discipline

- The scene uses a UnrealBloomPass with threshold **1.0** and strength **0.55**.
- **Ordinary Materials** (Cloth, leather, wood, beard, skin):
  - Emissive intensity must be **0.0**.
  - Base color luminance must not exceed $0.85$ in linear space to prevent blooming under key moonlight.
- **Magic Surfaces** (Staff crystal gem core, orbital runes):
  - Emissive color: Cyan (`#00e5ff` to `#7df9ff`).
  - Emissive intensity: Allowed to exceed $1.0$ (e.g. $1.5 - 3.5$) during peak charge and release to trigger HDR bloom deliberately.

---

## 9. Geometry & Texture Complexity Guidance

| Metric | Target Budget | Upper Warning Threshold | Rationale |
|---|---|---|---|
| **Triangle Count** | $25,000 - 45,000$ | $60,000$ | Balances rich silhouette and facial definition without exceeding V3's $\le 150\text{k}$ total scene budget. |
| **Vertices** | $15,000 - 30,000$ | $45,000$ | Efficient vertex reuse with smooth shading. |
| **Material Count** | $2 - 3$ | $4$ | e.g. `M_WizardBody` (Robe, Face, Beard), `M_StaffProps` (Wood, Gold), `M_GemFX` (Glass/Emissive Crystal). |
| **Texture Sets** | $1 - 2$ PBR sets | $3$ | 2048x2048 for Body/Robe, 1024x1024 for Staff/Gem. Formatted as PNG or WebP inside GLB. |
| **Skeletal Joints** | $25 - 45$ bones | $60$ bones | Covers full humanoid skeleton plus 3-bone beard and 4-bone hat. |
| **Skinned Meshes** | $1 - 2$ meshes | $3$ | Single combined skinned mesh preferred to minimize draw calls. |
| **File Size** | $\le 15\text{ MB}$ | $30\text{ MB}$ | Fast loading without network stall. |

---

## 10. GLB Validation Design & Automated Tooling

Deterministic validation is implemented via `tools/validate_wizard_glb.py`. It inspects the binary GLB container and parses glTF JSON metadata with zero external dependencies.

### 10.1 Validation Suite Rules

```
Rule 1: File & Container Integrity
  - File exists, size <= 60 MB
  - Magic == 0x46546C67 ('glTF'), Version == 2, Header length == file size
  - Chunk 0 is valid JSON

Rule 2: Scene & Graph Sanity
  - Default scene defined
  - Active nodes reachable from root
  - No NaN or Infinite transform components

Rule 3: Attachment Nodes (P0)
  - 'spell_origin' node present and NOT at (0,0,0) (dist >= 0.5, height >= 1.5m)
  - 'staff_grip' node present
  - 'head' node present

Rule 4: Skeletal Rig (P0)
  - Skin present with >= 15 joints
  - Semantic bone mappings detected (hips, spine, head, arms, hands, legs)

Rule 5: Animation Clips (P0)
  - Clips present: 'idle', 'charge', 'cast', 'recover'

Rule 6: Bounds & Dimensions
  - Estimated triangles <= 80,000
  - Height between 2.0m and 4.5m
  - Base resting near ground level (y_min >= -0.5m and <= 0.5m)
```

---

## 11. Runtime Integration Architecture (`GLBCharacter` Adapter)

When an authored asset is introduced in V3+ Pass B, it will integrate behind the `GLBCharacter` adapter using a **Two-Phase Atomic Swap**:

```
[BOOT]
  │
  ├─> 1. Initialize Procedural Wizard (V3 Baseline)
  │      - CharacterAdapter wraps WizardCharacter
  │      - App simulation & rendering begin immediately (Zero Delay)
  │
[ASYNC ASSET DISCOVERY]
  │
  ├─> 2. Fetch 'assets/wizard/wizard.glb' via Three.js r180 GLTFLoader
  │
  ├─> 3. Asset Found?
  │      ├── NO  ──> Log informational note; continue procedural V3 permanently.
  │      └── YES ──> Parse glTF structure.
  │
  ├─> 4. Run Contract Validation
  │      ├── FAILED ──> Log warning with failure details; retain procedural V3.
  │      └── PASSED ──> Proceed to staging.
  │
[STAGING & PREPARATION (Off-Screen)]
  │
  ├─> 5. Construct Normalization Wrapper Group (pos: -4.5, 0, 0; yaw: 0.44*PI)
  ├─> 6. Resolve Attachment Transforms ('spell_origin', 'staff_grip', 'head', 'camera_target')
  ├─> 7. Configure AnimationMixer & Actions ('idle', 'charge', 'cast', 'recover')
  ├─> 8. Ensure Material Color Spaces conform to r180
  ├─> 9. Create GLBCharacter instance wrapping the staged hierarchy
  │
[ATOMIC SWAP]
  │
  ├─> 10. Wait for IDLE state boundary in SpellDirector
  ├─> 11. Add authored character to scene; remove procedural character from scene
  ├─> 12. Switch active adapter: this.characterAdapter = glbAdapter
  ├─> 13. Dispose procedural character geometries and materials
  │
[STEADY STATE V3+]
  └─> Authored character drives all poses via phase-remapped AnimationMixer
```

### 11.1 Loading Implementation Detail

```javascript
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

class GLBCharacterAdapter {
  constructor(gltf, scene) {
    this.gltf = gltf;
    this.scene = scene;
    this.group = gltf.scene;
    this.mixer = new THREE.AnimationMixer(this.group);
    
    // Resolve attachments
    this.attachments = {
      spell_origin: this.findNode('spell_origin'),
      staff_grip: this.findNode('staff_grip'),
      head: this.findNode('head'),
      camera_target: this.findNode('camera_target') || this.findNode('head')
    };

    // Prepare action map
    this.actions = {};
    for (const clip of gltf.animations) {
      const name = clip.name.toLowerCase();
      this.actions[name] = this.mixer.clipAction(clip);
    }
  }

  applyPose(sample, simDt, blendSnapshot, recoverySnapshot) {
    const action = this.actions[this.getStateClipName(sample.state)];
    if (!action) return;

    // Phase remapping: SpellDirector owns progress
    const duration = action.getClip().duration;
    action.time = sample.progress * duration;
    this.mixer.update(0); // Evaluate pose at explicit time
  }

  getGemWorldPosition(outVec) {
    if (this.attachments.spell_origin) {
      this.attachments.spell_origin.getWorldPosition(outVec);
    } else {
      outVec.set(-4.5, 3.2, 0.0);
    }
    return outVec;
  }
}
```

---

## 12. Camera & Framing Contract

Authored models must maintain the composition of all 5 camera presets:

1. **Cinematic**: Full-body view showing wizard on left, dais, moonlight, projectile trajectory, and monolith target on right.
2. **Classic**: Centered presentation view showing wizard, dais, and target with wide negative space.
3. **Hero**: Close-up 3/4 portrait framing wizard's face, beard, and hat brim.
   - Camera look-at dynamically targets `characterAdapter.getAttachment('camera_target', tempMat)`.
4. **Target**: Monolith vantage point looking back at the wizard along the line of fire.
5. **Orbit**: Free mouse/touch orbit around `camera_target`.

---

## 13. Visual Acceptance Contract (Pass 3 Capture Gates)

When an authored asset is introduced, visual acceptance requires capturing the identical 14 camera/phase angles used in Pass 3 and proving superior artistic quality:

| Capture Gate | Viewport / Camera | State / Phase | Visual Acceptance Criteria |
|---|---|---|---|
| `cinematic-idle` | Cinematic ($1920\times 1080$) | IDLE ($t=0.0\text{s}$) | Grounded stance, distinct hat curve, readable hands, staff gem separated from hat. |
| `cinematic-charge-early` | Cinematic | CHARGE ($20\%$ energy) | Staff begins rising, somatic hand extends toward target. |
| `cinematic-charge-peak` | Cinematic | CHARGE ($95\%$ energy) | Maximum tension, arched back, vortex particles converging directly on gem. |
| `cinematic-release` | Cinematic | CAST ($15\%$ phase) | **Snap forward thrust.** Gem perfectly aligns with projectile origin ($d < 0.05$). |
| `cinematic-projectile` | Cinematic | CAST ($25\%$ phase) | Recoil posture along thrust line, wizard readable behind traveling plasma bolt. |
| `cinematic-impact` | Cinematic | CAST ($35\%$ phase) | Shockwave illumination reflects off robe folds and staff wood. |
| `cinematic-aftermath` | Cinematic | CAST ($80\%$ phase) | Settling relaxation, lingering smoke/sparks, clean rest posture. |
| `classic-idle` | Classic | IDLE | Balanced composition, robe hem grounded cleanly on dais masonry. |
| `classic-charge` | Classic | CHARGE | Dynamic silhouette, runes glowing on floor dais. |
| `classic-impact` | Classic | IMPACT | Monolith detonation illuminating wizard's right side. |
| `hero-portrait` | Hero | IDLE | Detailed facial expression, sculpted beard locks, hat brim depth, rim moonlight. |
| `bloom-off` | Cinematic | Render Mode 2 | PBR material differentiation verified without bloom masking. |
| `direct-render` | Cinematic | Render Mode 3 | Lighting balance and shadow penumbra verified against neutral gray. |

---

## 14. Performance Contract

Integrating an authored character must not compromise the verified V3 performance budget:

| Performance Metric | V3 Procedural Baseline | Authored Asset Budget | Hard Gate Limit |
|---|---|---|---|
| **Mean Frame Time (1080p)** | $2.72\text{ ms}$ | $\le 5.0\text{ ms}$ | $\le 16.6\text{ ms}$ ($60\text{ FPS}$) |
| **p95 Frame Time** | $13.30\text{ ms}$ | $\le 16.0\text{ ms}$ | $\le 20.0\text{ ms}$ |
| **Scene Draw Calls** | $\sim 160$ draws | $\le 175$ draws | $\le 220$ draws |
| **Scene Triangles** | $\sim 14,000$ tris | $35,000 - 65,000$ tris | $\le 100,000$ tris |
| **Geometries / Textures** | $100\text{ geos} / 25\text{ texs}$ | $105\text{ geos} / 28\text{ texs}$ | $\le 120\text{ geos} / 35\text{ texs}$ |
| **100-Cast Stress Test** | Zero entity/memory leaks | Zero entity/memory leaks | Zero entity/memory leaks |

---

## 15. Summary of Next Steps for Pass B

1. **Asset Creation**: Author wizard character in Blender adhering strictly to this contract.
2. **Export**: Export as binary glTF (`wizard.glb`) with embedded textures and 4 animation clips.
3. **Pre-Validation**: Run `python3 tools/validate_wizard_glb.py assets/wizard/wizard.glb`.
4. **Pass B Implementation**: Implement `GLBCharacter` adapter and two-phase atomic loader.
