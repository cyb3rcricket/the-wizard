# Wizard V3 audit

## 1. Executive Summary

V2 has the right ingredients and a recognizable identity, but its complexity is not consistently visible in the final image. The largest barriers are:

1. **Character construction and presentation.** The bent hat, plum robe, long beard and oversized focus crystal establish the character. Cylindrical garment pieces, a box head, spherical hands and segmented beard still read as assembled primitives. More critically, the staff, brim and camera orientation obscure the face and beard. Better framing and larger, deliberate forms will outperform additional accessories.
2. **Uncontrolled surface and lighting hierarchy.** Almost every important surface is a solid color; cloth, skin and wood have unnecessary metallic response, while gold has no environment to reflect. The luminous floor attracts attention away from the wizard. Explicit color management, material differentiation and selective use of brightness are foundational.
3. **Broken synchronization and incomplete pose ownership.** CAST emits from a forced 10% pose and then rewinds toward the start of CAST on the next update. Some transforms never return to rest. Several motions depend on rendered frame count. These are correctness problems, not a shortage of animation ideas.
4. **VFX reliability and shape hierarchy.** Dynamic particle bounds remain stale, trail emission aliases its own scratch position, and the spell largely reuses stars, spheres and hard rings. Repairing visibility and emitter correctness precedes ribbons, bloom or greater particle density.
5. **No HDR post-processing or authored cinematic arc.** ACES alone does not spread light into neighboring pixels. The camera has presets, drift and trauma, but no charge framing or recovery composition. A restrained bloom pipeline and a shared spell timeline can make existing systems cooperate.

**Recommendation:** evolve the existing scene, not its engine. Make a procedural V3 that visibly improves silhouette, surfaces, illumination and spell timing. Preserve an adapter boundary for a later rigged character. A polished stylized game vignette is realistic; detailed MMO character close-ups remain an asset-authoring problem that rendering alone cannot solve.

**Evidence and limits.** All 2,662 lines of `wizard-v2.html` were read. Read-only browser checks at 1280×720 inspected Cinematic and Hero Low idle views and a recovery view. Those views confirmed primitive surfaces, staff/face overlap, a cropped Hero composition and a dominant floor pattern. No warnings/errors were returned by the sampled browser console. Precise release, collision and particle findings below come from code tracing; this was not an exhaustive frame capture, audio listening session or GPU benchmark. No measured FPS or draw-call claims are made.

## 2. What V2 Already Does Well

- **Identity and palette:** exaggerated backward hat, silver beard, plum/magenta cloth, antique gold and cyan magic are a coherent starting point. Keep them.
- **Actual 3D articulation:** `WizardCharacter.nodes` separates torso, head, upper arms, forearms, staff, beard and hat segments. This is useful control structure, not something to discard for architectural fashion.
- **Moving spell origin:** `getGemWorldPosition(targetVec)` derives the origin from the character hierarchy. Preserve this contract through any asset replacement.
- **Recognizable spell grammar:** anticipation, thrust, travel, target response and recovery already exist. Projectile light and monolith rune ignition connect effects to physical surfaces.
- **Bounded effects:** typed arrays for 280 vortex particles, a 220-spark pool and four reusable shockwaves avoid per-particle scene objects.
- **Staged environment:** dais, target, ruin columns, distant mountains, moon and stars already provide foreground-to-background structure.
- **Useful controls:** five camera presets, drag orbit, wheel zoom, 0.25×/1×/1.8× speed, manual/automatic casting, muted-by-default audio and UI hiding. Preserve actual behavior, not inaccurate help text.
- **Reasonable baseline renderer:** antialiasing, capped DPR, ACES, PCF shadows and fog are already present. V3 needs calibration and compositing, not a replacement engine.

## 3. Visual Bottlenecks

| Priority / ID | Limitation and primary cause | Visible payoff / implementation phase |
|---|---|---|
| **P0 — transformational / A** | Character reads as primitives and its defining face/beard are hidden. **Geometry, art and composition.** | Clear three-quarter face, continuous hat/beard contours, shaped robe folds; Phase 3 and final framing in Phase 7. |
| **P0 — transformational / B** | Flat materials, inconsistent color pipeline, overcompetitive floor and no optical glow. **Materials, lighting and rendering.** | Rich plum cloth, readable gold/wood/skin, bright magic that illuminates geometry and blooms without bleaching it; Phases 1–2. |
| **P0 — transformational / C** | Release and pose disagree; residual transforms and frame-rate dependencies compromise weight and repeatability. **Animation and orchestration.** | One readable anticipation → release → impact gesture, consistent across speed/frame rate; Phase 4. |
| **P1 — major improvement / D** | Particle culling and scratch-vector aliasing can defeat effects before art tuning. **Implementation correctness.** | Reliable vortex and trail placement from every camera; Phase 0 fixes in the future V3 copy, then Phases 5–6. |
| **P1 — major improvement / E** | Uniform stars/spheres/rings lack a dominant core, coherent travel shape and grounded aftermath. **VFX art and timing.** | Distinct gather, compression, release, travel, impact and embers; Phases 5–6. |
| **P1 — major improvement / F** | Preset-plus-shake camera does not frame the spell; Hero Low hides face and cuts robe. **Direction and composition.** | Small motivated push-in/recoil/settle while keeping wizard and target legible; Phases 3 and 7. |
| **P1 — major improvement / G** | Uniform columns, tiled stone, cone mountains and untextured mist undermine depth. **Environment art.** | A quiet stage with intentional negative space, broken contours and layered atmosphere; Phase 8. |
| **P2 — polish / H** | Motion/audio lifecycle and future fill-rate cost lack explicit budgets. **Runtime discipline.** | Stable long sessions, predictable speed changes and quality scaling; Phases 4 and 9. |

More geometry everywhere, global blur, additional lights or more particles would not resolve these bottlenecks.

## 4. Architecture Audit

Line references describe the inspected V2 file, not proposed V3 code.

| Actual subsystem | Decision | Rationale |
|---|---|---|
| Global r128 loading and three CDN fallbacks, lines 333–345 | **REPLACE** in future V3 | Use one pinned ES-module version for core and addons. Keep a visible initialization error. No framework or bundler is required. |
| `App` renderer/scene setup, 2330–2395; `initLighting`, 2397 | **MODIFY** | Keep WebGL renderer, scene, fog and camera. Add explicit color management, HDR composer, resize/disposal and calibrated lights. |
| `Textures`, 604–843 | **MODIFY** | Keep one-time canvas generation; add deterministic palettes, gradients and masks. Correct texture color roles and reuse shared sprite textures. |
| `WizardCharacter`, 848–1493 | **MODIFY** + **OPTIONAL FUTURE ASSET** | Preserve hierarchy and world-space origin; improve visible forms and fully specified poses. Add a narrow character adapter, not a general animation framework. |
| `EnvironmentBuilder`, 1498–1790 | **KEEP / MODIFY** | Retain stage and target layout. Improve silhouette, material scale, mist and reactive channels without expanding the world. |
| `ParticleEngine`, 1799–2049 | **KEEP / MODIFY** | Keep typed-array pools; fix bounds, aliasing and timing. Add a small dedicated ribbon buffer and per-particle size/alpha only where visible. |
| `ProjectileSystem`, 2054–2177 | **MODIFY** | Keep one traveling spell; store start/end and bounded progress, interpolate exact impact and emit an event instead of directly invoking audio/camera/environment. |
| `CameraDirector`, 2182–2327 | **KEEP / MODIFY** | Preserve presets/orbit; layer modest timeline offsets and deterministic trauma on top. Do not replace with a cinematic framework. |
| `App.setState` / `animate`, 2501–2625 | **MODIFY** | Extract timing and one-shot events into a small SpellDirector. App remains lifecycle owner; individual systems retain geometry and simulation. |
| `ProceduralAudioEngine`, 412–599 | **KEEP / MODIFY** | Preserve gesture unlock and procedural sound. Retain/cancel charge voices and drive charge pitch/gain from current energy; cache cast noise. |
| HTML controls / CSS vignette, 35–404; listeners, 2428 | **KEEP / MODIFY** | Preserve controls. Reduce the existing vignette rather than adding a duplicate; fix misleading pan/click instructions and avoid UI covering the subject. |

### End-to-end V2 trace

1. `animate` clamps real delta to 0.1 seconds, multiplies by selected speed, and advances `stateTime` and `totalTime`. IDLE lasts 2.0 seconds when looping.
2. CHARGE lasts 1.8 seconds. A single smoothstep drives the main pose; beard flutter, brightening gem, faster orbits, 280 inward particles and stronger floor runes use the phase intensity. Charge audio is scheduled once for `DUR_CHARGE / timeScale`.
3. Entering CAST resets state time, forces `setPoseCast(0.10)`, reads the gem, then simultaneously emits burst/shockwave, plays sound, adds 0.85 trauma and launches toward (11, 3.5, 0).
4. Next frame, CAST pose uses its actual near-zero progress. The character can move backward along the thrust after the projectile has already left. The first 15% of the 1.3-second CAST is the nominal snap.
5. Projectile moves at 28 units per simulation second. Its timer emits three trail sparks after 0.018 seconds, discarding remainder. Impact uses an X-plane crossing rather than exact endpoint/surface intersection.
6. `detonate` hides the projectile, ignites monolith light/runes, requests two rings and 140 sparks, plays impact audio and reaches through `window.director` for 0.95 trauma.
7. RECOVER starts after CAST's fixed 1.3 seconds, independent of impact. It lasts 1.0 second. Lights/runes decay; only a subset of pose channels return to baseline.

This coupling is why a modest orchestration change has visible value.

## 5. Character / Asset Ceiling

The classification describes the preferred long-term treatment. “REPLACE WITH AUTHORED ASSET” is a V3+ recommendation, **not a dependency for immediate V3**.

| Part | Classification | Reason and immediate V3 action |
|---|---|---|
| Body / torso | **IMPROVE PROCEDURAL** | Mostly clothed and read at medium distance. Tune taper, shoulder width and waist relationship; extra anatomical topology has little payoff. |
| Face | **REPLACE WITH AUTHORED ASSET** | Box head/cone nose/unlidded luminous eyes cannot supply an expressive portrait. Immediately soften the head contour, add brows and cheek/nose planes, reduce eye glow and expose the face. Defer sculpted facial rig. |
| Beard | **REPLACE WITH AUTHORED ASSET** | Three matching cylinders bend independently and reveal mechanical joints. Immediately create a few tapered, overlapping curved locks with a continuous outer contour and delayed tip motion. A sculpted/skinned beard gives the larger future leap. |
| Hat | **IMPROVE PROCEDURAL** | The exaggerated bend is already distinctive. Use a continuous ring-built surface around the existing bend, asymmetric brim and controlled deformation; do not simply increase radial subdivisions. |
| Robe | **REPLACE WITH AUTHORED ASSET** | Cylinder skirt and disconnected sleeves cannot reproduce deliberate tailoring/fold flow at close range. Immediately shape broad longitudinal folds, an uneven hem and cleaner shoulder transitions. Future asset supplies coherent cloth topology and painted folds. |
| Hands | **REPLACE WITH AUTHORED ASSET** | Spheres cannot grip or articulate a casting gesture. Immediately use mitten/palm-plus-thumb silhouettes and a fixed staff grip; individual fingers matter only for later close-ups. |
| Staff | **IMPROVE PROCEDURAL** | Straight shaft contradicts the “gnarled” comment; bends, tapered wood, a designed crown and visible grip are feasible procedurally. Keep the large faceted gem. |
| Environment architecture / dais | **KEEP PROCEDURAL** | Repeated structural masses are suitable. Improve proportions, bevel catches and top-surface texture scale rather than replacing the builder. |
| Rocks / cliff | **IMPROVE PROCEDURAL** | The current foundation is a tapered cylinder, not a rock asset set. Sparse asymmetric fractured masses will break its outline without detail inflation. |
| Ruins | **IMPROVE PROCEDURAL** | Columns share pristine silhouettes and detached-looking caps. Add a few designed broken profiles and consistent ornament; vary a small kit rather than randomizing every vertex. |
| Mountains | **IMPROVE PROCEDURAL** | Distant silhouettes need better contours and atmospheric values, not GLBs. Replace repeated four-sided cone profiles with irregular low-detail ridge meshes. |

**Screen-visible order:** face/beard visibility → hat/robe outer contour → arm/staff casting silhouette → material separation → minor accessories. The existing tome, vial and hat charm already suffice. Do not spend a phase adding buckles.

Near-term geometry must still support orbit inspection, but Cinematic and Classic are the primary composition gates. Asset-assisted V3+ can replace the character behind the adapter, using rigged clips with additive secondary motion; it should not require rewriting particles, camera or spell timing.

## 6. Rendering / Post-Processing Ceiling

### Current setup

- r128 is explicitly loaded. `App` enables ACES at exposure 1.18, PCFSoft shadows, DPR ≤2 and a 46° perspective camera. It renders directly with `renderer.render`.
- Neither output encoding nor texture encoding is assigned. In r128, output defaults to LinearEncoding and physically correct lights default off. Canvas-painted colors therefore lack an explicit input/output conversion contract. This is separate from tone mapping. See the [r128 renderer source](https://raw.githubusercontent.com/mrdoob/three.js/r128/src/renderers/WebGLRenderer.js).
- Lighting is indigo ambient plus moon, frontal fill and rim directionals; gem, projectile and target add three point lights. Only moon and gem cast shadows. The gem's 1024 point shadow is a six-face operation, not one cheap spotlight.
- There is no `scene.environment` or IBL. High-metalness gold has little reflected environment information. Cloth, beard, skin and wood are partly metallic without an artistic need.
- Stone is a 512² tiled color texture; there are no normal, roughness or AO maps. Rune anisotropy is hardcoded to 8; stone has none assigned. Rune disc is 1024², moon 512², glow/sparkle 128². These sizes are not themselves a crisis.
- FogExp2 provides distance attenuation, not volumetric light. “Volumetric Magic Illumination” is only a PointLight comment. Three uniform additive ground planes do not make convincing moving mist.
- The opaque gem encloses its smaller opaque white core: the interior does not automatically become a visible optical layer. The moon halo is another sphere silhouette. These are modeling/compositing issues.
- The CSS already supplies a strong vignette. Additional full-screen darkening would further hide the character.

### Recommended foundation

Pin **Three.js 0.180.0 / r180** for the future implementation and all its addons: a deliberate, inspected WebGL2 target, not a claim that it is the newest release. Keep ACES initially so material comparisons are meaningful. Adopt explicit sRGB color textures, linear lighting and a half-float composer with one final output conversion. Modernization enables supported addons and predictable colors; it does not author better art. ES modules, changed color/light defaults and WebGL2 support need a migration gate; old light intensities must be retuned. See the [official migration guide](https://github.com/mrdoob/three.js/wiki/Migration-Guide).

| Effect | Decision / purpose |
|---|---|
| EffectComposer + OutputPass | **Required.** Preserve HDR through effects and convert once for display. The pinned [OutputPass](https://raw.githubusercontent.com/mrdoob/three.js/r180/examples/jsm/postprocessing/OutputPass.js) handles renderer tone mapping and output conversion. |
| UnrealBloomPass | **Required, restrained.** Give gem, bolt, runes and flash an optical halo. Use scene-linear brightness above threshold; keep ordinary surfaces/moon below the strong-bloom range. The pinned [pass](https://raw.githubusercontent.com/mrdoob/three.js/r180/examples/jsm/postprocessing/UnrealBloomPass.js) already uses a mip chain. |
| Explicit selective bloom | **Deferred unless threshold calibration fails.** A second scene render and black-material substitution are not free. Brightness-selective bloom is sufficient first; keep semantic magic tags for possible later masks. |
| AO / GTAO / SSAO | **Optional quality gate.** Contact at robe/ground and joints can help. Start with shadows and authored vertex/cavity shading. If still needed, test GTAO alone at reduced resolution; do not stack AO algorithms or darken transparent magic. |
| Color grading | **Material/light palette first.** No LUT dependency. Optional subtle final grade only after neutral comparison; avoid hiding incorrect texture conversion. |
| Vignette | **Retain but reduce existing CSS treatment.** No duplicate pass. |
| DOF | **Defer.** Wizard, traveling spell and target should remain readable together; blur complicates transparent effects and mobile framing. |
| Grain / chromatic aberration | **Omit.** No clear payoff for this clean fantasy presentation. |
| Exposure flash | **Short, bounded timeline envelope.** Never automatic exposure pumping. Restore baseline exactly. |
| Spell streaks | **Use world-space ribbon geometry.** Do not use global motion blur or afterimage history that smears the character. |
| Custom shaders | **Small and local:** ribbon taper/alpha, per-point size/alpha and masked mist/rune flow. No wholesale custom PBR replacement. |

## 7. Animation / Cinematic Ceiling

**Concrete defects and limits:**

- `buildWizard` calls `setPoseIdle(0)` without its required `breath` argument (1272). Several initial transforms/light values become NaN until the first proper animation update.
- Poses do not own complete transforms. IDLE does not reset chest X rotation, beard X rotations or the charged hat X rotations. RECOVER does not restore body Y, beard-root X or the hat chain. A repeated cycle can leave visibly charged shapes at rest.
- CHARGE is one smoothstep applied to many joints simultaneously. CAST begins with forced progress 0.10, then near-zero progress; left-arm/body transitions also assume fixed preceding poses. Early manual release or recovery interruption exposes those assumptions.
- Orbital rotations increment per frame; spark drag multiplies by 0.96 per update. Their behavior changes with refresh rate and selected speed. Impact-light lerp can also overshoot below zero when scaled delta reaches 0.18 seconds. Random per-frame gem jitter/shake is not repeatable art direction.
- Root slides from -4.9 to -3.4 without a planted-foot/hem strategy. Stronger recoil will look weightless unless the base remains believable.
- `CameraDirector.update` lerps using scaled delta. Speed changes alter camera response, not only the spell. Shake is already substantial; increasing trauma is a poor substitute for staging.
- Charge audio is scheduled for speed at entry; early release or a mid-charge speed change does not cancel/reschedule it. Impact audio runs in real time while scene decay uses scaled time.
- Help promises right-drag pan, but `initMouseControls` does not distinguish buttons or implement pan. Canvas clicks are not cast triggers; the Cast button and Space are.

**Direction target:** CHARGE 0–30% establishes a low, weighted gathering pose; 30–80% raises/twists the torso and focus, with off-hand following; 80–100% holds tension and compresses the energy. CAST 0–15% is the forward gesture, with release at the end of that gesture, then a readable hold and recoil. Beard and hat tips lag the major action; recovery settles them last. Pose, emitter, audio, light and camera must agree on the release event.

A small SpellDirector is justified because it resolves actual ownership conflicts. It should own state/time/envelopes and event IDs, not geometry, rendering or every subsystem's internals.

## 8. VFX Ceiling

### Reliability before embellishment

- Vortex and spark positions start at Y=-100. Their BufferGeometry bounds are never recomputed or conservatively assigned, and Points frustum culling remains on. Three r128 computes a sphere only when absent; buffer uploads do not refresh it. Subsequent visible particles can remain culled by the initial hidden bounds. This is source-established; a full frame-by-frame visibility test remains a V3 gate. See [r128 Frustum.intersectsObject](https://raw.githubusercontent.com/mrdoob/three.js/r128/src/math/Frustum.js).
- Projectile trail passes `_scratchVec1` as burst origin. `spawnBurst` reuses that same vector for directional randomness after copying the first particle position. Later particles in that burst inherit the mutated origin. Separate input capture from scratch calculations.
- `resetVortexParticle` changes colors after initialization, but `updateVortex` marks only position for upload. Intended color variation does not reliably reach the GPU.
- Impact bursts are spawned after `updateSparks` has already uploaded the frame. Spark visuals lag the impact light/rings by an update.
- Shockwave `maxRadius` is used as scale on a RingGeometry with outer radius 0.45. A requested 8.5 radius is visually about 3.825 units. “Horizontal” impact ring is centered at impact height, not on the ground.
- Projectile uses endpoint X crossing and current Y/Z after overshoot. It does not hit a modeled surface precisely. Its transparent halo also retains default depth writing, risking occlusion artifacts.
- A trail made of three intermittent star sprites cannot communicate a continuous high-speed bolt; timer reset loses emission remainder and cannot catch up on a slow frame.

### Art direction

Keep cyan/turquoise dominant and reserve near-white for tiny cores and peak impact. Let violet appear in sparse peripheral wisps, not every layer. Use a tight energy core, a few organized orbit paths and a thinning inward field during charge; compress briefly before release. Travel needs one tapered ribbon and sparse sparks. Impact needs a brief local flash, a surface-aligned wave, a distinct ground response and dim residual embers. Separate directional energy from falling debris; the current “debris” is another luminous spark burst.

Layer by role and lifetime, not count. A visible 50-particle effect with a coherent silhouette is more useful than 500 invisible or competing particles.

## 9. Performance Risks

- **Shadows:** moving gem point shadow entails six views, alongside the 2048 directional shadow. Disable the gem shadow by default in V3; preserve actual light on surfaces. Tighten moon shadow bounds around relevant casters/receivers.
- **Fill rate:** DPR 2 means four times the pixels of DPR 1. Broad additive sprites, floor runes, mist, halo shells and future bloom compound cost. Half-float targets and optional AO add bandwidth.
- **Draw calls:** many small wizard meshes, column caps and separate torus ornaments are distinct draws and some cast shadows. Measure before merging; do not break articulation to save a few calls.
- **CPU/update:** pool scans are small (500 moving slots total), not a reason for GPU simulation. Fix idle uploads and frame-dependent math before introducing compute techniques.
- **Allocations:** one-shot shockwave/impact vectors and cast audio noise allocation exist. The loop is mostly reusable storage; it is inaccurate to call it a large per-frame allocation disaster. Cache noise and scratch vectors opportunistically.
- **Lifecycle:** there is no explicit dispose path for renderer resources/listeners/audio voices. Fine for one loaded page, but V3 quality switching or optional asset replacement needs ownership and cleanup.
- **Measurement guardrail:** target 60 FPS at 1920×1080 with a documented desktop/browser, internal DPR initially ≤1.5, bloom enabled and no AO/DOF. Target p95 frame time ≤20 ms after warm-up. These are V3 goals, not V2 benchmark results. Profile GPU/CPU separately where supported.

## 10. Recommended V3 Scope

**Commit to:** a color-managed HDR foundation with modest bloom; material and light calibration; better procedural wizard silhouette and face visibility; complete pose/reset semantics and one release timeline; correct pooled effects, a coherent ribbon projectile and layered impact; restrained cinematic offsets; a quieter, deeper environment; reproducible visual and performance acceptance checks.

**Defer:** required GLB production, facial rigging, finger animation, simulated cloth/hair, full volumetrics, global motion blur, DOF, grain, chromatic aberration, multiple spells, gameplay systems, larger world building, WebGPU migration, a framework/build-system rewrite and a general-purpose timeline editor.

The immediate release must work with no external character or texture assets. The companion implementation plan specifies the procedural path and a later GLB boundary. Every P0 item above is represented by an explicit phase and acceptance gate.
