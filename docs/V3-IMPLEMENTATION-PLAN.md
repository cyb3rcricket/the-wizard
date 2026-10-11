# Wizard V3 implementation plan

## Handoff contract

**This is a plan, not an implementation.** The planning pass creates only this file and `V3-AUDIT.md`. The implementation agent must work in a new V3 entry point when separately authorized; preserve every V1 HTML file and `wizard-v2.html` as reference baselines. Do not edit V2 to test this plan.

Deliver a browser-based stylized fantasy vignette retaining the bent hat, beard, robe, staff/gem, moonlit stage and IDLE → CHARGE → CAST → RECOVER loop. Immediate V3 must run with a procedural wizard and generated textures. No GLB, HDR image, texture pack or other unavailable asset is a prerequisite.

**Three priorities:** character silhouette/readability; color-managed materials/lighting/bloom; coherent spell choreography with dependable effects.

### Decisions already made

- Stay with Three.js WebGLRenderer; pin **three 0.180.0 (r180)** and matching addons. This is an intentionally fixed implementation target, not “latest.”
- Keep a static HTML entry point with an import map and module script. Map `three` to the pinned `build/three.module.js` and `three/addons/` to that same package's `examples/jsm/`. A pinned CDN is acceptable initially, as in V2; a future vendored copy must include transitive module dependencies. No bundler/framework is required.
- Retain the existing class responsibilities. Add only a small SpellDirector and a character adapter boundary. Add post-processing methods to App rather than inventing a general render framework.
- Use HDR-threshold bloom first. Do not build a second-scene selective bloom system unless measured art tests prove it necessary.
- Keep one projectile, bounded effects and a fixed target. No new gameplay, spells or world systems.
- Primary presentation gates: Cinematic and Classic full spell views; Hero is an optional portrait with a readable face. Orbit remains functional.
- Values below are **initial tuning targets** unless described as invariants. Acceptance images and timings determine final art tuning, not blind adherence to arbitrary intensities.

## Phase 0 — Baseline, safety and visible correctness

### Goal

Establish a trustworthy comparison and prevent existing defects from undermining the V3 art work.

### Existing Systems Involved

Entire V2; especially `WizardCharacter.buildWizard/setPoseIdle` (1272), `ParticleEngine` (1799), `ProjectileSystem.update` (2118), `App.animate` (2555).

### Changes

1. Before future implementation, record repository status and hashes of existing HTML files. Keep V2 immutable. Make all implementation changes only in the separately authorized V3 surface.
2. Capture baseline frames/video at 1280×720 and 1920×1080: idle, CHARGE 30/80/100%, release, mid-flight, impact +0.1 s and recovered idle. Include Cinematic, Classic and a Hero portrait; use identical viewport/preset for comparisons.
3. Add a development-only deterministic seed and a simulation inspection/step hook in V3, not a production timeline editor. Expose state, normalized progress, event counts, pool occupancy and render statistics. Seed procedural textures, particles and noise for repeatable comparisons.
4. Initialize a finite rest pose with an explicit time/breath value. Validate transforms/light scalars before the first render.
5. For the two small dynamic Points pools, set `frustumCulled=false`; skip drawing inactive clouds through visibility/active counts rather than Y=-100 alone. This deliberately avoids stale bounds without an O(N) bounding-sphere rebuild every frame.
6. In `spawnBurst`, copy the origin once into dedicated private storage before the loop; never reuse it for cone randomness. Mark vortex color data dirty when colors change.
7. Reset projectile trail timer/history at launch. Keep these repairs small; defer the new trail design to Phase 6.
8. Add a regression checklist for all existing controls. Loop OFF means finish the current cycle and then idle, not pause. Correct help text to say Cast button/Space and drag orbit/wheel zoom; right-drag pan is not currently implemented and need not become a new feature.

### Preserve

V2 files, identity, all five preset choices, 0.25×/1×/1.8× speeds, manual early release, recovery retrigger, automatic looping, audio unlock/mute and H/UI visibility.

### Acceptance Criteria

- Original file hashes match; V3 changes are isolated.
- All initial transforms are finite.
- Vortex/sparks appear when active from Cinematic, Classic, Hero and Orbit views.
- A three-particle directional burst receives three identical initial positions even when its caller uses a scratch vector.
- Repeated launches start with empty trail history and a reset emission timer.
- Baseline captures distinguish actual observations from source-derived risks.

### Performance Notes

Do not add a test framework or profiler dependency. Existing browser instrumentation and a small development hook suffice. No optimization claim without recorded hardware, browser, viewport and settings.

## Phase 1 — Modern rendering and HDR foundation

### Goal

Make color, illumination and optical glow predictable before tuning art.

### Existing Systems Involved

CDN loaders (333–345), `App.constructor` renderer setup (2330), resize listener (2428), final render (2623), `Textures`.

### Changes

1. In V3 replace global r128 loading with the pinned module/import-map setup. Preserve a visible load/WebGL error message. WebGL2 is the supported baseline; do not silently fall back to a mixed-version renderer.
2. Set explicit output color space to `THREE.SRGBColorSpace`; keep color management enabled. Assign sRGB to canvas color textures (stone, moon, colored runes/sprites). Masks, roughness, AO and normal data remain `NoColorSpace`. Do not gamma-correct numeric linear shader/vertex values twice.
3. Retain ACES at an initial exposure of 1.0. Recalibrate the scene rather than copying r128 light numbers blindly. Modern lighting defaults differ; do not carry obsolete `physicallyCorrectLights` or `outputEncoding` assignments into r180.
4. Add `App.initPostProcessing()`, `resizeRendering()`, `renderFrame()` and `dispose()` responsibilities:
   - Create a half-float WebGLRenderTarget and EffectComposer.
   - Chain **RenderPass → UnrealBloomPass → OutputPass**.
   - Start bloom threshold around 1.1 scene-linear luminance, strength 0.35 and radius 0.35. Tune using gem/bolt highlights and moon/robe exclusion.
   - OutputPass performs the final tone mapping/display conversion. Do not add GammaCorrectionShader or another output conversion.
   - Use 4× multisampling on the composer target if supported within budget; cap by renderer capabilities. Canvas antialiasing alone does not antialias an offscreen target.
5. Provide a development post-processing bypass that uses direct renderer output with the same color space, exposure and tone mapper. Bloom OFF inside the composer is a separate comparison.
6. Set internal pixel ratio to min(device DPR, 1.5) initially. Resize renderer, composer and camera coherently using CSS dimensions; do not multiply DPR twice. Update the effective ratio when viewport/DPR changes.
7. Tag intended strong emitters semantically (gem, projectile core, limited rune/flash layers). Raise their linear radiance above the bloom threshold. Keep ordinary material highlights and moon away from sustained strong bloom. Start with no extra bloom render.
8. Reduce the existing CSS vignette's opacity/extent so the wizard at the left edge remains visible; keep one vignette treatment.

### Preserve

ACES visual direction, CSS UI overlay, fog, shadows, resize behavior, existing renderer/camera ownership and post-processing-free operation.

### Acceptance Criteria

- Idle and full spell render with composer ON, bloom OFF and direct-render bypass.
- Bloom OFF versus direct render differs only by expected antialiasing, not a gamma/brightness jump.
- Gem/bolt bloom strongly at peaks; robe, beard, moon and ordinary stone remain readable.
- Resize and DPR changes preserve aspect ratio and crisp controls; no black border or oversized render target.
- Missing module/WebGL support produces a clear error rather than an inert blank canvas.

### Performance Notes

UnrealBloomPass already downsamples through its own mip chain. Start with that implementation; do not introduce an additional bloom-only scene or allocation per frame. Dispose composer passes/targets explicitly. Reduce MSAA or internal DPR before adding another antialiasing pass.

## Phase 2 — Material identity and lighting hierarchy

### Goal

Make cloth, skin, beard, wood, stone, gold and magical energy visibly different at the normal camera distance.

### Existing Systems Involved

`WizardCharacter.buildWizard` material declarations (884 onward), `Textures`, `EnvironmentBuilder.buildEnvironment`, `App.initLighting`, gem/monolith light controls.

### Changes

1. Define a compact palette/material table: deep plum cloth, lighter magenta shoulder accents, warm skin, cool ivory beard, brown wood, muted slate stone, restrained antique gold and cyan magic. Keep these reusable material instances.
2. Set cloth/skin/beard/wood/stone metalness to 0. Start roughness at cloth 0.8–0.95, skin/beard 0.65–0.85, wood 0.75–0.9 and stone 0.8–1. Gold alone starts at metalness 0.85–1 and roughness 0.35–0.5.
3. Add broad vertex-color or generated UV color gradients to robe/hat: dark undersides, lighter upper planes and a few designed fold accents. Avoid noisy all-over detail. Beard gets shaded roots and warmer tips; wood gets longitudinal variation.
4. Keep faceting on rock/crystal, but use deliberate smooth normals on cloth, skin and beard surfaces. Split edges only where the silhouette/material design needs a hard break.
5. Generate one reusable stone color map with larger coherent variation and less brick/checker contrast. Add subtle roughness/bump variation only after the color-only result reads correctly. Share masks where appropriate; do not reuse an sRGB color texture object as non-color data.
6. For grazing stone/rune textures, set anisotropy to min(8, renderer maximum); retain mip filtering. Future AO/normal maps need explicit UV/data roles, not a blanket shader rewrite.
7. Bake a small procedural environment once using PMREMGenerator.fromScene: dark blue enclosure/sky plus broad, dim cool and neutral bright cards. Use it only as `scene.environment`, preserving the authored background/moon. Start environmentIntensity around 0.15–0.3. Dispose temporary bake geometry/materials and the generator; retain the PMREM texture until App disposal. No external HDRI is required.
8. Rebalance lights in this order: moon key/shadow → faint frontal fill sufficient for the face → restrained cool rim → weak ambient/IBL → gem light. Visually associate the stronger rim with the moon; the visible moon is behind the scene whereas V2's “moonLight” sits in front, so treat the latter as an intentional key instead of pretending exact physical alignment.
9. Disable gem point-light shadows by default; retain moon shadows and unshadowed gem/projectile/impact lights. Tighten moon shadow coverage to the wizard, stage and target; use normalBias/bias sparingly after inspecting acne/contact.
10. Reduce idle floor rune opacity from the current dominant presentation; target roughly 0.15–0.25 initially, then allow a localized charge response. Keep moon/crater detail below the wizard/gem focal contrast.
11. Expose baseline and spell-peak light/emissive/exposure values as named art parameters. Phase 4 will own their envelopes; pose methods must stop independently choosing light intensity.

### Preserve

Plum/gold/cyan identity, visible moonlight, character shadows, nearby surfaces responding to gem light, target rune ignition.

### Acceptance Criteria

- At idle and with bloom disabled, a viewer can distinguish cloth, gold, wood and beard.
- Face/beard remain legible without glowing eyes serving as a substitute for modeling.
- Charge visibly lights the hand, staff and nearby robe without flattening all colors to cyan.
- Gold has a controlled reflected highlight; cloth does not look metallic.
- Floor/columns support the wizard rather than becoming the brightest large region.

### Performance Notes

One small PMREM bake at initialization; no real-time reflection probes. Do not add shadow-casting lights. AO remains off until Phase 9 demonstrates an unresolved contact-shading need.

## Phase 3 — Procedural character presentation

### Goal

Deliver the largest immediately visible improvement without waiting for a GLB.

### Existing Systems Involved

`WizardCharacter.buildWizard`, `nodes`, `getGemWorldPosition`; `CameraDirector.setPreset` Cinematic/Classic/Hero.

### Changes

1. Tune the wizard's root yaw and camera target together so the face, beard, leading hand and staff form separate shapes in Cinematic and Classic. Aim for a full wizard roughly 50–65% of viewport height, with room for raised hat/gem and the target. Exact screen-space framing wins over keeping V2 coordinates.
2. Start with silhouette sheets from rest, maximum charge, release and recovery. Keep negative space between staff and face and between off-hand and torso. Correct the pose/camera before adding detail.
3. Replace the hat's visibly separate cylinder contour with a connected ring-built BufferGeometry following the existing five-segment bend. Preserve the bend controls using fixed vertex weights across adjacent control transforms, updating this small mesh's positions/normals without rebuilding geometry. Use a slightly asymmetric brim and restrained sewn-band treatment.
4. Keep the beard's three motion controls but attach 3–5 tapered overlapping locks with different lengths and an uninterrupted main silhouette. Avoid exposed stacked-cylinder joints. Keep most hair detail in broad color/value variation.
5. Shape the skirt with 5–7 broad vertical folds, slight left/right asymmetry and an uneven but grounded hem. Improve shoulder/sleeve overlap and collar shape. Do not add cloth simulation.
6. Use a softened, tapered head profile with simple brow/cheek masses and a stronger nose. Reposition/scale eye glow to retain face expression. No facial rig is required.
7. Replace hand spheres with a palm/mitten and thumb wedge. Set the staff grip to visibly enclose the shaft. The somatic hand must form a readable open gesture.
8. Give the staff a few intentional bends and taper; improve crown/claw silhouette. Keep the gem opaque/faceted and remove reliance on the hidden internal white core for brightness; use surface emissive contrast plus a small visible halo/core highlight.
9. Establish stable rest-transform data for every animated node and attachment. Phase 4 will apply complete pose samples and additive secondary offsets.
10. Introduce the narrow character adapter described below. Continue using the procedural implementation throughout this release.

### Preserve

Recognizable hat bend, beard length, robe palette, staff/gem, existing accessories, hierarchy-driven world-space origin and ability to view from orbit.

### Acceptance Criteria

- In small grayscale thumbnails of Cinematic and Classic, hat, beard, staff and casting hand remain recognizable.
- Face/beard are not crossed by the shaft/gem in idle or principal charge/release poses.
- No holes or disjoint segments appear at maximum hat/beard deformation.
- Hem stays visually grounded; thrust does not look like the entire robe skating freely.
- Hero portrait shows the face; full-body views retain the hem and raised gem within a safe frame margin.

### Performance Notes

Spend geometry on outer contours and folds, not hidden detail. Aim for a procedural character below roughly 30k triangles and no more articulated mesh draws than needed; measure rather than turning the target into a rigid polygon quota.

## Phase 4 — SpellDirector and animation timing

### Goal

Make pose, release, travel, impact, lighting, audio and HUD describe the same event.

### Existing Systems Involved

`App.setState/animate/initEventListeners`, all four `WizardCharacter.setPose*` methods, `ProjectileSystem.detonate`, `EnvironmentBuilder` impact methods, `ProceduralAudioEngine`, `CameraDirector.addTrauma`.

### Changes

1. Extract state/time/event ownership from App into a small SpellDirector. Keep App as constructor, input router, subsystem update orchestrator and renderer owner.
2. Retain initial phase durations: IDLE 2.0 s, CHARGE 1.8 s, CAST 1.3 s, RECOVER 1.0 s. Define named normalized curves and events rather than burying them inside mesh code.
3. Use a fixed simulation step of 1/120 s. Add clamped real delta (≤0.1 s) × selected speed to an accumulator; consume at most 24 steps per rendered frame, carrying normal remainder and dropping excessive backlog after suspension. Render the latest completed simulation state initially; at 120 Hz this avoids inventing a separate interpolated pose/event timeline. Add interpolation only if a measured high-refresh presentation issue justifies it. Camera UI damping uses real delta; authored spell offsets use simulation phase.
4. Carry time across state boundaries. Process threshold crossings in order, including multiple crossings in one update. Fire each event once per cast ID.
5. Remove the forced `setPoseCast(0.10)` entry hack. CAST release occurs at **15% (0.195 s)**, after the forward gesture:
   - CHARGE 0–30%: slight compression, stable hem/weight, off-hand gathers.
   - CHARGE 30–80%: torso/staff lift and twist; head follows; beard/hat tips lag.
   - CHARGE 80–100%: near-held anticipation; energy tightens rather than endlessly increasing movement.
   - CAST 0–15%: accelerate through the forward strike; release at the endpoint.
   - CAST 15–35%: brief clear follow-through silhouette; light falls from peak.
   - CAST 35–100%: recoil relaxes while projectile/impact aftermath remains independent.
   - RECOVER 0–60%: torso/staff return; 60–100%: tip motion settles.
6. Every pose sample specifies all owned translations/rotations from stored rest transforms. Apply secondary offsets afterward. Do not let omitted channels inherit an old state. Capture the current pose on manual early release or recovery retrigger, then blend to the same strike target; never jump to an assumed full-charge pose.
7. Replace per-frame orbit increments with dt-based angular velocity; replace drag/decay lerp factors with exponential damping. Use deterministic low-frequency noise for magic jitter/trauma. No negative light intensity on a slow 1.8× frame.
8. Update order per simulation step:
   - Advance director and identify due events.
   - Apply character pose/secondary motion; update world matrices.
   - Resolve release by sampling the current gem attachment once; send the same immutable origin/forward direction to burst, projectile and audio/camera events.
   - Integrate projectile; resolve an exact impact crossing and queue its event once.
   - Apply event reactions, update effect lifetimes/particle buffers, environment and light envelopes.
   - Publish one consistent state/progress snapshot for the HUD.
   The event is resolved at its exact simulation boundary; subsequent substeps advance both pose and projectile normally. Never advance only one subsystem or sample an old gem matrix.
9. Projectile owns motion/collision only. Replace direct calls to audio/environment/`window.director` in `detonate` with an impact event containing cast ID, point and normal.
10. Keep manual input semantics: idle/recover starts a charge; charge requests release through the short CAST gesture; CAST ignores extra release input. Do not permit a new active projectile to overwrite an old one. Loop OFF finishes the current cycle.
11. Charge audio becomes a retained voice whose frequency/gain follows the sampled charge envelope; cancel/fade it on release, reset or mute. Keep cast/impact transients in real time, triggered at simulation events, without pitch-scaling every sound. Cache the cast noise buffer.
12. On document hide, stop advancing simulation, clear accumulated backlog, fade/suspend audio and reset real-time reference. On return, resume the same phase with no catch-up burst. Resume AudioContext subject to browser gesture requirements.

### Preserve

Recognizable four-state loop, early release, recovery retrigger, speed controls, muted initial audio and a single active spell.

### Acceptance Criteria

- One release and one impact per cast ID; no duplicate events at low FPS or boundary crossings.
- At 0.25×, the visible gem, burst origin and projectile origin coincide at release, with no backward thrust jump.
- After repeated complete and interrupted cycles, controlled base transforms return to rest; secondary motion is bounded and does not accumulate.
- Equal simulated time at 30/60/120 Hz produces equivalent particle travel, orbit angles and event order.
- HUD state/progress come from the same snapshot.
- Mid-charge speed changes do not leave the charge sound continuing after release.
- Hide/resume does not skip impact or emit a backlog; loop OFF settles into idle.

### Performance Notes

Do not build an event bus or timeline editor. A fixed-size event list or direct dispatch table for release/impact/state changes is enough. Avoid new arrays/vectors in each simulation step.

## Phase 5 — Charge VFX

### Goal

Make gathering energy visibly organized and increasingly tense.

### Existing Systems Involved

`ParticleEngine.updateVortex/resetVortexParticle`, gem/orbital rings, `EnvironmentBuilder.update` floor rune response, director charge envelope.

### Changes

1. Keep the 280-slot vortex pool; vary active count instead of showing every slot at full strength. Begin around 40 active particles and grow toward 160–220; tune for silhouette, not maximum capacity.
2. Give particles distinct roles within the same bounded system: small inward sparks plus a few larger soft wisps. Add per-particle size and alpha attributes with one small shader; V2's unused `size` field alone does nothing.
3. Build 2–3 intentional orbit paths around the moving focus, with different inclination/radius and staggered phase. Use a bounded ribbon/arc mesh only for the most visible path; avoid multiplying torus wireframes.
4. CHARGE 0–30%: sparse arrivals and a low local rune response. 30–80%: accelerate inward paths and brighten nearby cloth/hand. 80–100%: shrink the field toward the gem, reduce loose outer particles and briefly hold the core.
5. Keep a tiny near-white center, cyan mid-layer and faint violet periphery. Radius, opacity and light intensity have separate curves; increasing brightness is not a substitute for gathering shape.
6. At release, stop/recycle gathering particles quickly instead of continuing a broad charge cloud over the strike. Remaining wisps may dissolve over about 0.1–0.2 simulation seconds.
7. Floor response centers near the wizard with a masked gradient; leave the broad dais pattern quiet. This is a surface effect, not an added volumetric lighting system.

### Preserve

Vortex tracks the current world-space gem, charge increases nearby illumination, and pool limits remain explicit.

### Acceptance Criteria

- Three still frames at 20/60/95% CHARGE show gathering, acceleration and compression distinctly.
- Face, staff and hand remain readable through the effect.
- Strongest brightness is localized to the focus; the full floor does not wash out.
- Effects remain visible from Orbit and after returning from a hidden tab.
- Release clears the focus for the directional strike.

### Performance Notes

No new shadow light. Keep soft sprites modest in screen area; use active draw ranges/visibility and avoid uploads for fully inactive clouds.

## Phase 6 — Release, projectile and impact

### Goal

Create a coherent traveling spell and an impact with scale, contact and aftermath.

### Existing Systems Involved

`ProjectileSystem.launch/update/detonate`, `ParticleEngine.spawnBurst/spawnShockwave/updateSparks`, `EnvironmentBuilder.targetMonolith/triggerImpactFlash`, SpellDirector events.

### Changes

1. Define a target attachment and surface normal on the monolith's visible strike face. Store complete origin/end vectors, traveled distance and duration; interpolate the crossing to the endpoint. Keep the current nominal 28 units/s as a starting point. No X-only collision or terrain physics engine.
2. Orient projectile core and trail along velocity. Reshape the spherical mass into a compact directional core with a restrained plasma envelope; set transparent halo depthWrite=false and keep depth testing.
3. Use one preallocated 48-sample world-space ribbon history, sampled by distance (start around 0.2 units). Construct camera-facing strip vertices with tapered width/alpha; cap lifetime around 0.25 simulation seconds. Resample across low-FPS travel segments rather than leaving gaps.
4. Sparse residual sparks accompany the ribbon. Preserve emission remainder and spawn along the traveled segment. Never pass mutable input vectors into a function that reuses them internally.
5. Release envelope: small directional flash at the attachment, a focused cone burst and a short ring. One compact bright core plus a softer surrounding edge; do not hide the entire wizard in white.
6. Impact event, time relative to contact:
   - 0–0.06 s: compact near-white flash, strongest local light, short audio transient.
   - 0.03–0.25 s: surface-facing wave and outward directional sparks.
   - 0.05–0.5 s: separate ground ring centered at ground height, faint displaced mist and a few dark stone chips.
   - 0.2–0.9 s: embers and rune afterglow fade.
   Chips use a small preallocated/instanced pool (start 12), not new meshes per hit; no permanent monolith destruction.
7. Define shockwave radius in world units. Use a unit outer-radius base geometry or divide by its actual radius when scaling. Orient the surface ring to the target normal and ground ring to +Y; offset to avoid z-fighting.
8. Reserve impact capacity or recycle lowest-priority trail sparks when full. Keep the 220-spark cap initially, with a deliberate priority policy and development dropped-count display; no silent loss of the hero flash.
9. Make impact light/rune intensity, bloom and a tiny exposure rise envelopes of impact age. Start exposure rise at ≤0.2 EV and decay within 0.12 s. Release and impact contributions are combined with a cap, not additive unbounded spikes.
10. Flush new impact particle positions before rendering the impact frame. Clear/recycle completed projectile and effect state without adding/removing scene objects every cast.

### Preserve

One moving projectile, target illumination, shockwave, impact audio, physical direction and an aftermath that resolves to baseline.

### Acceptance Criteria

- At 1× and 0.25×, ribbon stays connected to the traveling core and has no camera-facing flips in normal presets.
- At a simulated slow frame, collision is at the target attachment, not beyond it; impact fires once.
- Surface ring stays on the target plane; ground response stays on the stage.
- Flash peaks briefly; wizard and monolith regain material detail immediately afterward.
- After repeated casts, pool counts/resource counts stabilize and all temporary light/exposure offsets return to baseline.
- Low quality preserves the core, ribbon and impact cue even when wisps/chips are reduced.

### Performance Notes

Pool every transient. Avoid scene-wide distortion, full-screen motion blur and another bloom scene. Count transparent overdraw before increasing sprite count.

## Phase 7 — Camera and cinematic response

### Goal

Support the action without hiding the wizard or overriding user camera control.

### Existing Systems Involved

`CameraDirector.setPreset/update/initMouseControls`, trauma, perspective camera, director phase/impact samples.

### Changes

1. Preserve each preset's base position/look-at separately from temporary spell offsets. Compose offsets each frame; never accumulate them into the saved preset.
2. Cinematic only: CHARGE 0–80% eases a 5–8% push-in and shifts attention slightly toward the raised focus. Hold during the last 20%. Start FOV modulation around 46° → 43°, contingent on keeping the gem/hat inside frame.
3. At release, use a small camera recoil along view direction and bounded deterministic trauma. Do not let trauma 0.85/0.95 remain the default answer to both events. Start with lower amplitudes and retain the wizard outline.
4. At impact, shift look target modestly toward the monolith, without chasing the projectile or cutting away from the caster. Recovery returns exactly to baseline position/look/FOV.
5. Use exponential damping with real delta for camera convergence; sample spell offsets from simulation time. Restore projection on FOV changes. Pointer drag/wheel enter manual orbit and suppress scripted framing offsets immediately.
6. Classic remains a stable side-on overview. Hero stays a portrait and does not attempt to frame the whole travel path. Impact preset retains its explicit target-centric intent.
7. Keep time dilation **off in the first V3 pass**. Existing 0.25× is sufficient for readability checks; adding another time scale complicates audio and control behavior before the choreography is proven.
8. Respect reduced-motion preference by disabling trauma and large camera offsets while preserving all spell events.

### Preserve

Preset buttons, drag orbit, zoom limits, smooth transitions and user ownership of manual framing.

### Acceptance Criteria

- Cinematic full spell keeps face/hat/gem and impact destination readable; no camera cut is required.
- Orbit interaction during charge immediately stops scripted repositioning.
- Recovery restores base position/look/FOV without drift across ten cycles.
- At 0.25×, camera remains responsive and does not shake for an uncomfortable real-time duration.
- Reduced-motion mode retains a complete understandable spell.

### Performance Notes

Camera work is inexpensive; visual restraint is the budget. No DOF, global motion blur or projectile-follow camera in this phase.

## Phase 8 — Environment polish

### Goal

Turn the existing stage into deliberate fantasy art with depth and negative space.

### Existing Systems Involved

`EnvironmentBuilder.buildEnvironment/update`, `Textures.createStoneTexture/createMoonTexture/createRuneDisc`, fog and lighting.

### Changes

1. Preserve wizard-left/target-right staging. Reposition or shorten columns whose silhouettes intersect the face, hat bend or raised focus in primary views.
2. Break the foundation's perfect tapered-cylinder outline with a small set of low-detail asymmetric masses. Keep the dais as the clean central performance surface.
3. Make a small ruin kit: intact shaft, broken shaft and fractured cap with coherent bevels/ornament. Place deliberately; do not scatter clutter across the projectile corridor.
4. Separate top-surface stone mapping from vertical masonry scale. Reduce repetitive checker/brick contrast; keep small detail subordinate to character value contrast.
5. Replace repeated cone mountains with two or three irregular ridge bands. Use quieter contrast with distance and fog; preserve moon negative space instead of filling the sky.
6. Replace the three untextured rectangular mist planes with a few masked noise patches at low opacity, mainly behind/below the stage. Reuse one generated mask; animate UV drift and a brief impact displacement. Keep transparent depthWrite off, depthTest on.
7. Replace the obvious moon halo shell with a soft radial billboard if it remains visible as a hard sphere boundary. Keep crater detail, reduce apparent size/framing conflict where necessary, and avoid strong moon bloom.
8. Keep starfield in one Points draw. Give stars stable individual brightness variation; replace the entire field's synchronized size pulsing with subtle phased modulation.
9. Add at most a few deliberate signs of age (one broken ruin silhouette, a worn rune region). No new environment subsystem.

### Preserve

Moonlit fantasy setting, altar, target monolith, mountain depth, sparse stars and a clear line of fire.

### Acceptance Criteria

- Wizard remains the focal point in grayscale and full color.
- Foreground stage, midground ruins and distant mountains separate without relying on heavy DOF.
- No large rectangular mist edge or giant additive plane crosses the wizard.
- Primary views avoid column/hat tangencies and UI overlap.
- Impact feels connected to the stage while the background remains quiet.

### Performance Notes

Share ruin materials/geometries where useful. Instance repeated static pieces only if profiling warrants it. No high-resolution terrain, volumetric raymarching or extra shadow maps.

## Phase 9 — Performance, regression and visual sign-off

### Goal

Prove a generational visual improvement that survives controls, repeated playback and a realistic rendering budget.

### Existing Systems Involved

All V3 systems derived from V2; App lifecycle, renderer/composer, pooled effects, director and audio.

### Changes

1. Repeat Phase 0 captures with matching seed, viewport and preset. Review both bloom-enabled and disabled results: post-processing must not conceal weak modeling.
2. Record browser, GPU/device, resolution, internal DPR, enabled passes and frame-time distribution. Target 1920×1080 output, DPR ≤1.5, 60 FPS and p95 ≤20 ms after warm-up on the documented modern desktop. If missed, identify CPU versus GPU cost before tuning.
3. Use renderer.info with autoReset disabled across a complete rendered frame, then reset once after all passes; otherwise composer statistics undercount work. Record peak draws/triangles/textures and compare idle/charge/impact. Start guardrails around 180 visible scene draws and 150k visible triangles, excluding shadow/post passes; measured render totals still include those costs and govern performance.
4. Run 100 casts, including early release and recovery retrigger. Check stable resource counts, bounded audio voices, no duplicate listeners, no stranded lights/projectiles and no heap growth trend after warm-up.
5. Exercise all presets, manual orbit/zoom, 0.25×/1×/1.8×, mid-phase speed change, loop OFF/ON, muted/unmuted interaction, H, resize, DPR change and background/resume. Test at least Chromium and one other WebGL2 browser available to the implementer.
6. Add Medium/Low internal settings only as needed: first lower DPR/MSAA, then reduce soft wisps and chips, then reduce bloom render resolution or disable bloom at Low; lowering strength alone does not remove its rendering cost. Preserve silhouette, light response, ribbon and impact even at Low.
7. Optional AO gate: only if contact still looks ungrounded after lighting/shadow/material work, prototype the pinned GTAOPass at reduced resolution on opaque geometry before bloom. Exclude transparent particles/runes from its geometry/AO contribution and verify compositing order. Keep it OFF by default unless a controlled before/after proves a meaningful improvement within budget. Do not ship SSAO plus GTAO or black halos around the beard.
8. Implement disposal for owned geometry/materials/textures, composer passes/targets, PMREM texture, listeners, animation frame handle and audio voices. Test one teardown/reinitialize cycle if such lifecycle is exposed.
9. Recheck original V1/V2 hashes and ensure all changed/created implementation files match the separately authorized V3 scope.

### Preserve

Every behavior listed in Phase 0 and every visual identity element in the handoff contract.

### Acceptance Criteria

- All three P0 priorities pass their visual gates; the result is visibly improved without requiring a GLB.
- Event/order/reset tests pass at multiple frame rates and playback speeds.
- No browser console errors, shader errors, disappearing pools or non-finite transforms.
- Performance evidence reports actual results and any quality tradeoff, not “optimized” without measurements.
- Original implementations remain byte-identical.
- No optional effect ships solely because it was implemented.

### Performance Notes

Keep the render path fixed during each measurement. Compare the same cast phase and seed after shader warm-up; do not interpret a smaller particle count as proof of a faster frame. Record the quality setting that actually meets the budget.

## Stable interfaces and ownership

These are implementation contracts, not a request for a framework.

| Owner | Interface / responsibility |
|---|---|
| App | Own renderer, scene, camera, systems, RAF, real-time clock, resize and teardown. Dispatch UI requests and ordered events. |
| SpellDirector | `requestCast()`, `setLoop(enabled)`, `advance(simDt)`, `sample()`, `notifyImpact(event)`, `reset()`. Own phase time, normalized curves, cast ID and event-once guards. Store no meshes/materials. |
| Character adapter | `applyPose(frame, simDt)`, `getGemWorldPosition(outVec)`, `getSpellDirection(outVec)`, `getAttachment(name, outTransform)`, `getBounds(outBox)`, `dispose()`. Own pose representation and secondary motion. Preserve the existing gem method name. |
| ParticleEngine | Consume charge sample and release/impact events; own pools, buffers and visuals. Copy input vectors. No direct UI/audio/camera calls. |
| ProjectileSystem | `launch(origin, target, castId)`, `update(simDt)`, `reset()`; return/emit one impact point+normal+castId. Own travel and ribbon history, not global reactions. |
| EnvironmentBuilder | Expose target attachment/normal; accept charge/impact envelopes; own stage geometry, mist and target materials. |
| CameraDirector | Own base preset/manual orbit and additive camera response; consume timeline sample/events. No authority over spell state. |
| ProceduralAudioEngine | Own context, mute/unlock, retained charge voice and one-shot voices; consume envelope/events. No authority over simulation time. |

The frame sample should contain only useful shared values: cast ID, state, state age, normalized phase, charge energy, release/impact age, and named camera/light envelopes. Keep values derived from one timeline. The HUD reads this same sample.

Do not make the adapter leak procedural node indices into the director. For early-transition blending, pose snapshots are opaque character-owned data. Lighting ownership must be singular: director supplies intensities/envelopes, visual systems apply them to their own materials/lights.

## Optional asset-assisted V3+

No asset is assumed to exist. The procedural adapter is the default and a complete deliverable.

When an `assets/wizard/*.glb` is separately supplied:

1. Load it through the matching r180 GLTFLoader behind a GLBCharacter adapter. Keep the procedural character visible until loading and validation succeed; missing/invalid assets leave the complete procedural scene running.
2. Normalize scale, origin at ground level, forward axis and height in an outer wrapper. Do not change spell/world coordinates to accommodate an arbitrary export.
3. Map named attachments such as `spell_origin`, `staff_grip`, `head` and a framing target. Reject/retain procedural fallback if the spell origin is absent; do not silently launch from the model origin.
4. Use AnimationMixer for available idle/charge/cast/recover clips. Remap clip phase so release still occurs at the director's event; never fire a second projectile from a clip callback.
5. If clips are absent, use the procedural fallback for this release rather than pretending a static GLB has a casting rig. Skeleton-specific procedural animation can be a separately scoped follow-up.
6. Avoid competing writers: mixer owns base skeleton pose, secondary offsets apply afterward only on designated bones. Staff/gem effects attach through the adapter.
7. Dispose only resources owned by the replaced adapter after the new one is ready. Reuse the existing particles, camera, target and render pipeline unchanged.
8. Check silhouette, painted material hierarchy, clip timing and attachment coordinates with the same Phase 9 captures. A higher polygon count alone is not acceptance.

## P0 coverage and completion checklist

| Audit priority | Required phases | Evidence |
|---|---|---|
| A — character/readability | 3, 7 | Silhouette thumbnails; face/beard/staff separation; grounded full-body pose. |
| B — material/light/rendering | 1, 2 | Correct bypass comparison; differentiated surfaces; controlled bloom and local illumination. |
| C — synchronized choreography | 4, supported by 0 and 6 | Release alignment at 0.25×; one-shot event counts; reset and frame-rate equivalence tests. |

Do not mark V3 complete until those gates pass. AO, extra ornament and an external character cannot compensate for a failed P0 gate.

## Version-specific implementation references

Consult the pinned sources when implementing rather than mixing current examples from another revision.

- [r180 color-management guide](https://raw.githubusercontent.com/mrdoob/three.js/r180/manual/en/color-management.html): texture roles and linear working space.
- [r180 EffectComposer](https://raw.githubusercontent.com/mrdoob/three.js/r180/examples/jsm/postprocessing/EffectComposer.js), [OutputPass](https://raw.githubusercontent.com/mrdoob/three.js/r180/examples/jsm/postprocessing/OutputPass.js), [UnrealBloomPass](https://raw.githubusercontent.com/mrdoob/three.js/r180/examples/jsm/postprocessing/UnrealBloomPass.js): render-target and output behavior.
- [r180 WebGLRenderer](https://raw.githubusercontent.com/mrdoob/three.js/r180/src/renderers/WebGLRenderer.js): WebGL2, output and renderer APIs.
- [r180 GTAOPass](https://raw.githubusercontent.com/mrdoob/three.js/r180/examples/jsm/postprocessing/GTAOPass.js): optional AO only.
- [Three.js migration guide](https://github.com/mrdoob/three.js/wiki/Migration-Guide): relevant historical API changes between r128 and the chosen target.
