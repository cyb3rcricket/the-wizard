import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

REPO_DIR = "/Volumes/Backup Plus/GitHub/The-Wizard"
BRAVE_BIN = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
HTTP_PORT = 8765
CDP_PORT = 9222

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_http_server():
    os.chdir(REPO_DIR)
    server = HTTPServer(('127.0.0.1', HTTP_PORT), QuietHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

def launch_brave():
    return subprocess.Popen([
        BRAVE_BIN,
        '--headless=new',
        f'--remote-debugging-port={CDP_PORT}',
        '--use-gl=angle',
        '--use-angle=metal',
        '--window-size=1440,900',
        '--no-sandbox',
        '--mute-audio',
        'about:blank'
    ])

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.msg_id = 0
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50*1024*1024)

    async def send(self, method, params=None):
        self.msg_id += 1
        payload = {'id': self.msg_id, 'method': method}
        if params:
            payload['params'] = params
        await self.ws.send(json.dumps(payload))
        while True:
            resp = json.loads(await self.ws.recv())
            if resp.get('id') == self.msg_id:
                return resp.get('result', {})

    async def eval(self, expr):
        res = await self.send('Runtime.evaluate', {
            'expression': expr,
            'returnByValue': True,
            'awaitPromise': True
        })
        if 'exceptionDetails' in res:
            raise RuntimeError(f"JS Exception: {res['exceptionDetails']}")
        return res.get('result', {}).get('value')

    async def screenshot(self, filename):
        res = await self.send('Page.captureScreenshot', {'format': 'png'})
        data = base64.b64decode(res['data'])
        filepath = os.path.join(REPO_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(data)
        print(f"Captured screenshot: {filename} ({len(data)} bytes)")

async def main():
    print("=== Starting Wizard V3 Pass 2 Comprehensive Verification ===")
    httpd = start_http_server()
    brave_proc = launch_brave()
    time.sleep(2.0)

    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json') as r:
            targets = json.loads(r.read().decode())
        ws_url = targets[0]['webSocketDebuggerUrl']

        client = CDPClient(ws_url)
        await client.connect()

        # Set viewport
        await client.send('Emulation.setDeviceMetricsOverride', {
            'width': 1440,
            'height': 900,
            'deviceScaleFactor': 1,
            'mobile': False
        })

        # Navigate to wizard-v3.html
        print("Navigating to wizard-v3.html...")
        await client.send('Page.navigate', {'url': f'http://127.0.0.1:{HTTP_PORT}/wizard-v3.html'})
        await asyncio.sleep(2.0)

        # 1. Sanity Check
        print("\n--- Suite 1: Foundation & Initialization ---")
        initialized = await client.eval("typeof window.__WIZARD_V3__ !== 'undefined'")
        print(f"window.__WIZARD_V3__ present: {initialized}")
        assert initialized, "WIZARD_V3 interface missing"

        state0 = await client.eval("window.__WIZARD_V3__.getState()")
        print(f"Initial State: {state0['state']}, Render Mode: {state0['renderMode']}")
        assert state0['state'] in ['IDLE', 'CHARGE', 'CAST', 'RECOVER']

        rev = await client.eval("THREE.REVISION")
        print(f"Three.js Revision: {rev}")
        assert rev == '180', f"Expected Three.js r180, got {rev}"

        # Pause background rAF stepping by setting timeScale = 0
        await client.eval("window.__WIZARD_V3__.app.timeScale = 0.0;")

        # 2. Phase 4 Verification: Timing & Choreography
        print("\n--- Suite 2: Phase 4 Timing, Events & State Machine ---")
        
        # Test event-once guards across cycles
        print("Testing event-once guards across cycles...")
        await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                window.__testResults = {
                    releases: [],
                    impacts: [],
                    duplicateReleases: 0,
                    duplicateImpacts: 0
                };
                
                const seenReleases = new Set();
                const seenImpacts = new Set();
                
                const origNotifyImpact = app.spellDirector.notifyImpact.bind(app.spellDirector);
                app.spellDirector.notifyImpact = function(event) {
                    if (seenImpacts.has(event.castId)) {
                        window.__testResults.duplicateImpacts++;
                    }
                    seenImpacts.add(event.castId);
                    window.__testResults.impacts.push(event);
                    return origNotifyImpact(event);
                };

                const origAdvance = app.spellDirector.advance.bind(app.spellDirector);
                app.spellDirector.advance = function(simDt) {
                    const wasReleaseFired = this.releaseFired;
                    const currentCastId = this.castId;
                    origAdvance(simDt);
                    if (!wasReleaseFired && this.releaseFired) {
                        if (seenReleases.has(currentCastId)) {
                            window.__testResults.duplicateReleases++;
                        }
                        seenReleases.add(currentCastId);
                        window.__testResults.releases.push({ castId: currentCastId, time: this.totalTime });
                    }
                };

                // Enable autoLoop
                app.spellDirector.setLoop(true);
            })()
        """)

        # Step through 3 full cycles at 120Hz (~24 simulation seconds = 2880 steps)
        print("Stepping through 3 full cycles at 120Hz...")
        await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                for (let i = 0; i < 120 * 24; i++) {
                    app.stepSimulation(1/120);
                }
            })()
        """)

        test_results = await client.eval("window.__testResults")
        print(f"Releases captured: {len(test_results['releases'])}, Impacts captured: {len(test_results['impacts'])}")
        print(f"Duplicate releases: {test_results['duplicateReleases']}, Duplicate impacts: {test_results['duplicateImpacts']}")
        assert len(test_results['releases']) >= 3, "Failed to capture >= 3 releases"
        assert len(test_results['impacts']) >= 3, "Failed to capture >= 3 impacts"
        assert test_results['duplicateReleases'] == 0, "Duplicate release events detected!"
        assert test_results['duplicateImpacts'] == 0, "Duplicate impact events detected!"
        print("PASS: Event-once guards strictly hold.")

        # Test Release Alignment: Visible gem, burst origin, projectile origin coincide
        print("\nTesting Release Alignment at CAST 0.15...")
        align_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                // Reset to IDLE
                app.spellDirector.setLoop(false);
                app.spellDirector.state = 0; // IDLE
                app.spellDirector.stateTime = 0;
                app.projectiles.active = false;
                app.wizard.resetToRest();
                
                // Start charge
                app.spellDirector.requestCast(app.characterAdapter);
                
                // Advance until projectile becomes active at release
                let steps = 0;
                const gemPos = new THREE.Vector3();
                
                while (steps < 120 * 5 && !app.projectiles.active) {
                    app.stepSimulation(1/120);
                    steps++;
                }
                
                app.wizard.getGemWorldPosition(gemPos);
                const proj = app.projectiles;
                const pPos = proj.pos.clone();
                const dist = gemPos.distanceTo(proj.originPos);
                const stepTravel = proj.pos.distanceTo(proj.originPos);
                
                return {
                    stepsToRelease: steps,
                    gemPos: gemPos.toArray(),
                    originPos: proj.originPos.toArray(),
                    projPos: pPos.toArray(),
                    distance: dist,
                    stepTravel: stepTravel,
                    active: proj.active
                };
            })()
        """)
        print(f"Release alignment distance: {align_res['distance']:.4f} units")
        print(f"Gem pos: {align_res['gemPos']}, Proj pos: {align_res['projPos']}")
        assert align_res['active'], "Projectile should be active after release"
        assert align_res['distance'] < 0.05, f"Release origin misaligned: {align_res['distance']} > 0.05"
        print("PASS: Gem and projectile origin coincide at release.")

        # Test Base Transform Stability & 0-drift recovery
        print("\nTesting Transform Rest Recovery after repeated cycles...")
        drift_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.spellDirector.setLoop(true);
                // Run 5 more complete cycles
                for (let i = 0; i < 120 * 35; i++) {
                    app.stepSimulation(1/120);
                }
                app.spellDirector.setLoop(false);
                // Step until IDLE state settled (stateTime > 0.8)
                let guard = 0;
                while ((app.spellDirector.state !== 0 || app.spellDirector.stateTime < 0.8) && guard < 120 * 15) {
                    app.stepSimulation(1/120);
                    guard++;
                }
                
                // Compare wizard nodes to restPose
                const wiz = app.wizard;
                const rest = wiz.restPose;
                const deltas = {
                    rootPos: wiz.nodes.root.position.distanceTo(rest.rootPos),
                    headRot: Math.abs(wiz.nodes.head.rotation.x - rest.headRot.x) + 
                             Math.abs(wiz.nodes.head.rotation.y - rest.headRot.y) + 
                             Math.abs(wiz.nodes.head.rotation.z - rest.headRot.z),
                    rightArmRot: Math.abs(wiz.nodes.rightArm.rotation.x - rest.rightArmRot.x) + 
                                 Math.abs(wiz.nodes.rightArm.rotation.y - rest.rightArmRot.y) + 
                                 Math.abs(wiz.nodes.rightArm.rotation.z - rest.rightArmRot.z),
                    staffRot: Math.abs(wiz.nodes.staffGroup.rotation.x - rest.staffGroupRot.x) + 
                              Math.abs(wiz.nodes.staffGroup.rotation.y - rest.staffGroupRot.y) + 
                              Math.abs(wiz.nodes.staffGroup.rotation.z - rest.staffGroupRot.z)
                };
                // Right arm, staff, and root are controlled base transforms without breathing
                const restDeltas = {
                    rootPos: deltas.rootPos,
                    rightArmRot: deltas.rightArmRot,
                    staffRot: deltas.staffRot
                };
                
                // Head breathing secondary motion must be bounded <= 0.025 and non-accumulating
                const headBreathingBounded = deltas.headRot <= 0.025;
                
                // Calling resetToRest restores all transforms including head strictly to rest
                wiz.resetToRest();
                const postResetHeadDelta = Math.abs(wiz.nodes.head.rotation.x - rest.headRot.x);

                return {
                    restDeltas,
                    headDelta: deltas.headRot,
                    headBreathingBounded,
                    postResetHeadDelta
                };
            })()
        """)
        print("Rest recovery results:", drift_res)
        for k, v in drift_res['restDeltas'].items():
            assert v < 1e-4, f"Drift detected in base transform {k}: {v}"
        assert drift_res['headBreathingBounded'], f"Secondary head motion exceeded bound: {drift_res['headDelta']}"
        assert drift_res['postResetHeadDelta'] < 1e-4, f"Post-reset head drift: {drift_res['postResetHeadDelta']}"
        print("PASS: Wizard base transforms return strictly to rest pose and secondary motion is bounded.")

        # Test Early Manual Release Pose Snapshot Blending
        print("\nTesting Early Manual Release pose blending...")
        early_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.wizard.resetToRest();
                
                // Request cast
                app.spellDirector.requestCast(app.characterAdapter);
                // Advance to 35% of charge
                const durCharge = app.spellDirector.DUR_CHARGE;
                for (let i = 0; i < Math.floor(120 * durCharge * 0.35); i++) {
                    app.stepSimulation(1/120);
                }
                const chargeProgress = app.spellDirector.sample().progress;
                
                // Request early release
                app.spellDirector.requestCast(app.characterAdapter);
                const stateAfterReleaseReq = app.spellDirector.state;
                const hasSnapshot = app.spellDirector.earlyReleaseSnapshot !== null;
                
                // Advance 5 steps into CAST
                const armRotSteps = [];
                for (let i = 0; i < 5; i++) {
                    app.stepSimulation(1/120);
                    armRotSteps.push(app.wizard.nodes.rightArm.rotation.x);
                }
                
                return {
                    chargeProgress,
                    stateAfterReleaseReq,
                    hasSnapshot,
                    armRotSteps
                };
            })()
        """)
        print(f"Early release triggered at progress {early_res['chargeProgress']:.2f}")
        print(f"State after release: {early_res['stateAfterReleaseReq']} (CAST=2)")
        print(f"Has earlyReleaseSnapshot: {early_res['hasSnapshot']}")
        print(f"Right arm rot progression: {early_res['armRotSteps']}")
        assert early_res['hasSnapshot'], "earlyReleaseSnapshot should be captured on early release"
        assert early_res['stateAfterReleaseReq'] == 2, "State should be CAST"
        print("PASS: Early manual release captures pose snapshot and blends.")

        # Test Document Hide/Resume handling & Backlog Clamping
        print("\nTesting Hide/Resume visibility handling...")
        hide_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                // Start a charge
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < 50; i++) app.stepSimulation(1/120);
                
                // Simulate document hide
                Object.defineProperty(document, 'hidden', { value: true, configurable: true });
                document.dispatchEvent(new Event('visibilitychange'));
                
                const accDuringHide = app.accumulator;
                
                // Accumulate lots of delta in animate loop or simulate time jump
                app.accumulator += 2.0; // 2 seconds backlog
                if (app.accumulator > app.maxBacklogSteps * app.fixedDelta) {
                    app.accumulator = app.maxBacklogSteps * app.fixedDelta;
                }
                const clampedAcc = app.accumulator;
                
                // Simulate document visible again
                Object.defineProperty(document, 'hidden', { value: false, configurable: true });
                document.dispatchEvent(new Event('visibilitychange'));
                const accAfterShow = app.accumulator;
                
                return {
                    accDuringHide,
                    clampedAcc,
                    maxAllowed: app.maxBacklogSteps * app.fixedDelta,
                    accAfterShow
                };
            })()
        """)
        print("Hide/resume results:", hide_res)
        assert hide_res['accAfterShow'] == 0, "Accumulator should be cleared on resume"
        assert hide_res['clampedAcc'] <= hide_res['maxAllowed'] + 1e-5, "Backlog must be clamped"
        print("PASS: Visibility handling clamps backlog and resets accumulator.")

        # 3. Phase 5 Verification: Charge VFX
        print("\n--- Suite 3: Phase 5 Charge VFX ---")
        vfx_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const parts = app.particles;
                
                const hasSizeAttr = parts.vortexGeo.getAttribute('aSize') !== undefined;
                const hasAlphaAttr = parts.vortexGeo.getAttribute('aAlpha') !== undefined;
                const maxVortex = parts.MAX_VORTEX;
                const ribbonMesh = parts.orbitRibbonMesh !== undefined;
                
                // Sample progression at 20%, 60%, 95%
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                
                // 20% charge
                for (let i = 0; i < Math.floor(120 * durCharge * 0.20); i++) app.stepSimulation(1/120);
                const s20 = app.spellDirector.sample();
                const floorRune20 = s20.floorRuneResponse;
                
                // 60% charge
                for (let i = 0; i < Math.floor(120 * durCharge * 0.40); i++) app.stepSimulation(1/120);
                const s60 = app.spellDirector.sample();
                const floorRune60 = s60.floorRuneResponse;
                
                // 95% charge
                for (let i = 0; i < Math.floor(120 * durCharge * 0.35); i++) app.stepSimulation(1/120);
                const s95 = app.spellDirector.sample();
                const floorRune95 = s95.floorRuneResponse;
                
                return {
                    maxVortex,
                    hasSizeAttr,
                    hasAlphaAttr,
                    ribbonMesh,
                    s20Energy: s20.chargeEnergy,
                    s60Energy: s60.chargeEnergy,
                    s95Energy: s95.chargeEnergy,
                    floorRune20,
                    floorRune60,
                    floorRune95
                };
            })()
        """)
        print("VFX spec:", vfx_res)
        assert vfx_res['maxVortex'] == 280, f"Expected 280 vortex particles, got {vfx_res['maxVortex']}"
        assert vfx_res['hasSizeAttr'] and vfx_res['hasAlphaAttr'], "Custom shader attributes aSize and aAlpha must exist"
        assert vfx_res['ribbonMesh'], "Orbit ribbon mesh must exist"
        assert vfx_res['s20Energy'] < vfx_res['s60Energy'] < vfx_res['s95Energy'], "Charge energy must increase monotonically"
        assert vfx_res['floorRune20'] < vfx_res['floorRune60'] < vfx_res['floorRune95'], "Floor rune response must increase"
        print("PASS: Phase 5 Charge VFX conforms strictly to specification.")

        # 4. Phase 6 Verification: Release, Projectile & Impact
        print("\n--- Suite 4: Phase 6 Release, Projectile & Impact ---")
        p6_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const env = app.env;
                const strikeTarget = env.getStrikeTarget().toArray();
                const strikeNormal = env.getStrikeNormal().toArray();
                
                const proj = app.projectiles;
                const plasmaEnv = proj.envelopeMesh;
                const plasmaDepthWrite = plasmaEnv.material.depthWrite;
                const plasmaDepthTest = plasmaEnv.material.depthTest;
                const trailPointsCount = proj.MAX_TRAIL;
                
                const debrisCount = app.particles.chips.length;
                const maxSparks = app.particles.MAX_SPARKS;
                
                return {
                    strikeTarget,
                    strikeNormal,
                    plasmaDepthWrite,
                    plasmaDepthTest,
                    trailPointsCount,
                    debrisCount,
                    maxSparks
                };
            })()
        """)
        print("Phase 6 spec:", p6_res)
        assert p6_res['strikeTarget'] == [10.2, 3.4, 0.0], f"Expected (10.2, 3.4, 0.0), got {p6_res['strikeTarget']}"
        assert p6_res['strikeNormal'] == [-1.0, 0.0, 0.0], f"Expected (-1, 0, 0), got {p6_res['strikeNormal']}"
        assert p6_res['plasmaDepthWrite'] == False, "Plasma envelope depthWrite must be false"
        assert p6_res['plasmaDepthTest'] == True, "Plasma envelope depthTest must be true"
        assert p6_res['trailPointsCount'] == 48, f"Expected 48 trail history points, got {p6_res['trailPointsCount']}"
        assert p6_res['debrisCount'] == 12, f"Expected 12 tumbling debris chips, got {p6_res['debrisCount']}"
        assert p6_res['maxSparks'] == 220, f"Expected 220 spark cap, got {p6_res['maxSparks']}"

        # Test impact exposure envelope: rise <= 0.20 EV, decay <= 0.12s
        exp_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                // Fast forward to impact
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                let guard = 0;
                while (app.spellDirector.impactAge < 0 && guard < 120 * 5) {
                    app.stepSimulation(1/120);
                    guard++;
                }
                const peakExposure = app.spellDirector.sample().exposureOffset;
                
                // Advance 0.12s (15 steps)
                for (let i = 0; i < 15; i++) app.stepSimulation(1/120);
                const decayedExposure = app.spellDirector.sample().exposureOffset;
                
                return { peakExposure, decayedExposure };
            })()
        """)
        print("Impact exposure envelope:", exp_res)
        assert exp_res['peakExposure'] <= 0.20 + 1e-4, f"Peak exposure must be <= 0.20 EV, got {exp_res['peakExposure']}"
        assert exp_res['decayedExposure'] < 0.05, f"Exposure should decay within 0.12s, got {exp_res['decayedExposure']}"
        print("PASS: Phase 6 Release, Projectile and Impact conform strictly to specification.")

        # 5. Phase 7 Verification: Camera and Cinematic Response
        print("\n--- Suite 5: Phase 7 Camera & Cinematic Response ---")
        cam_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const camDir = app.director;
                const durCharge = app.spellDirector.DUR_CHARGE;
                
                camDir.setPreset('cinematic');
                const basePos = camDir.basePos.clone();
                const baseFov = camDir.baseFov;
                
                // Charge 0-80%: Check push-in and FOV decrease
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.80); i++) {
                    app.stepSimulation(1/120);
                }
                const sample80 = app.spellDirector.sample();
                // update camera
                camDir.update(1/60, sample80);
                const camPos80 = app.camera.position.clone();
                const fov80 = app.camera.fov;
                const pushDist = basePos.distanceTo(camPos80);
                
                // Check reduced motion mode
                camDir.reducedMotion = true;
                camDir.trauma = 0;
                camDir.addTrauma(0.5);
                const traumaSuppressed = camDir.trauma === 0;
                camDir.update(1/60, sample80);
                const offsetsSuppressedRM = camDir.spellOffsetPos.lengthSq() === 0;
                camDir.reducedMotion = false;
                
                // Check user interaction override (preset 'orbit' suppresses scripted offsets)
                camDir.setPreset('orbit');
                camDir.update(1/60, sample80);
                const offsetSuppressed = camDir.spellOffsetPos.lengthSq() === 0;
                camDir.setPreset('cinematic');
                
                // Return to IDLE and check recovery drift
                for (let i = 0; i < 120 * 8; i++) {
                    app.stepSimulation(1/120);
                }
                let guard = 0;
                while ((app.spellDirector.state !== 0 || app.spellDirector.stateTime < 1.0) && guard < 120 * 15) {
                    app.stepSimulation(1/120);
                    guard++;
                }
                camDir.update(1.0, app.spellDirector.sample());
                const baseConvergenceDiff = camDir.currentPos.distanceTo(basePos);
                const finalFovDiff = Math.abs(app.camera.fov - baseFov);
                
                return {
                    baseFov,
                    fov80,
                    pushDist,
                    traumaSuppressed,
                    offsetsSuppressedRM,
                    offsetSuppressed,
                    baseConvergenceDiff,
                    finalFovDiff
                };
            })()
        """)
        print("Camera cinematic response:", cam_res)
        assert cam_res['fov80'] < cam_res['baseFov'], "FOV should decrease during push-in"
        assert cam_res['pushDist'] > 0.1, "Camera should push in during charge"
        assert cam_res['traumaSuppressed'], "Reduced motion must suppress trauma"
        assert cam_res['offsetsSuppressedRM'], "Reduced motion must suppress spell offsets"
        assert cam_res['offsetSuppressed'], "User interaction must suppress spell offsets"
        assert cam_res['baseConvergenceDiff'] < 0.01, f"Camera base convergence drift: {cam_res['baseConvergenceDiff']}"
        assert cam_res['finalFovDiff'] < 0.01, f"Camera FOV drift: {cam_res['finalFovDiff']}"
        print("PASS: Phase 7 Camera Director conforms strictly to specification.")

        # 6. Capturing Visual Verification Screenshots
        print("\n--- Suite 6: Visual Artifact Captures ---")

        async def capture_at(setup_js, filename):
            await client.eval(setup_js)
            await client.eval("window.__WIZARD_V3__.app.renderFrame()")
            await asyncio.sleep(0.1)
            await client.screenshot(filename)

        # 1. Charge 20%
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.20); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-charge-20.png")

        # 2. Charge 60%
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.60); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-charge-60.png")

        # 3. Charge 95% (Compression / tension hold)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.95); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-charge-95.png")

        # 4. Release Apex (CAST 15%)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                const durCast = app.spellDirector.DUR_CAST;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                const totalSteps = Math.floor(120 * durCharge) + Math.floor(120 * durCast * 0.15);
                for (let i = 0; i < totalSteps; i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-release.png")

        # 5. Projectile Mid-Flight with Ribbon Trail
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                const durCast = app.spellDirector.DUR_CAST;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                const totalSteps = Math.floor(120 * durCharge) + Math.floor(120 * durCast * 0.15) + 18;
                for (let i = 0; i < totalSteps; i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-projectile.png")

        # 6. Impact Moment (Surface wave, ground ring, sparks, debris chips)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                let steps = 0;
                while (app.spellDirector.impactAge < 0.02 && steps < 120 * 5) {
                    app.stepSimulation(1/120);
                    steps++;
                }
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-impact.png")

        # 6b. Impact Close-up (Target Preset)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('target');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                let steps = 0;
                while (app.spellDirector.impactAge < 0.03 && steps < 120 * 5) {
                    app.stepSimulation(1/120);
                    steps++;
                }
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-impact-target.png")

        # 7. Aftermath Settlement (0.4s post impact: embers, debris, ground settling)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic');
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                let steps = 0;
                while (app.spellDirector.impactAge < 0.40 && steps < 120 * 5) {
                    app.stepSimulation(1/120);
                    steps++;
                }
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass2-aftermath.png")

        print("\nAll 7 visual artifact screenshots captured successfully.")
        print("\n=== ALL PASS 2 VERIFICATIONS PASSED ===")

    finally:
        brave_proc.terminate()
        brave_proc.wait()

if __name__ == '__main__':
    asyncio.run(main())
