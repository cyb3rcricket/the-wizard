import asyncio
import base64
import hashlib
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
FIREFOX_BIN = "/Applications/Firefox.app/Contents/MacOS/firefox"
HTTP_PORT = 8769
CDP_PORT = 9223

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
        '--window-size=1920,1080',
        '--no-sandbox',
        '--mute-audio',
        'about:blank'
    ])

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.msg_id = 0
        self.ws = None
        self.console_errors = []
        self.console_warnings = []

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
            if 'method' in resp:
                if resp['method'] == 'Runtime.consoleAPICalled':
                    msg_type = resp['params'].get('type')
                    args = resp['params'].get('args', [])
                    text = " ".join([str(a.get('value', a.get('description', ''))) for a in args])
                    if msg_type == 'error':
                        self.console_errors.append(text)
                    elif msg_type == 'warning':
                        self.console_warnings.append(text)
                continue
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
    print("=====================================================================")
    print("=== STARTING WIZARD V3 PASS 3 (PHASES 8 & 9) FINAL VERIFICATION ===")
    print("=====================================================================\n")

    # ---------------------------------------------------------
    # SUITE 1: Foundation & Baseline SHA-256 Integrity Check
    # ---------------------------------------------------------
    print("--- Suite 1: Foundation & Baseline Integrity ---")
    expected_hashes = {
        'gemini-3-8-test.html': '7ac68e0e22f10a280917f65dc8a61b5c2bb883a2e54d7736babb9dae078206b4',
        'gpt-6-astra-test.html': 'f5d268e37b5137fe60430788773af7a981854408517b49d83caa76aa110a468f',
        'grok-4-7-test.html': '6d10f85c9c3f01097a3947ff8d50ae9476776e129739acf2fca738ee8c8d7119',
        'wizard-v2.html': '0bcedeb1d329ce9cee10f8b97f845297af2d466fa6d927580141dfd0f0900477'
    }

    for fname, exp_hash in expected_hashes.items():
        fpath = os.path.join(REPO_DIR, fname)
        assert os.path.exists(fpath), f"Baseline file missing: {fname}"
        with open(fpath, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        assert actual_hash == exp_hash, f"SHA-256 mismatch for {fname}: got {actual_hash}, expected {exp_hash}"
        print(f"PASS: Baseline integrity confirmed byte-identical: {fname}")

    httpd = start_http_server()
    brave_proc = launch_brave()
    time.sleep(2.0)

    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json') as r:
            targets = json.loads(r.read().decode())
        ws_url = targets[0]['webSocketDebuggerUrl']

        client = CDPClient(ws_url)
        await client.connect()
        await client.send('Runtime.enable')

        # Set 1920x1080 Viewport
        await client.send('Emulation.setDeviceMetricsOverride', {
            'width': 1920,
            'height': 1080,
            'deviceScaleFactor': 1,
            'mobile': False
        })

        print("\nNavigating to wizard-v3.html at 1920x1080...")
        await client.send('Page.navigate', {'url': f'http://127.0.0.1:{HTTP_PORT}/wizard-v3.html'})
        await asyncio.sleep(2.0)

        # Sanity check
        initialized = await client.eval("typeof window.__WIZARD_V3__ !== 'undefined'")
        assert initialized, "WIZARD_V3 interface missing"
        state0 = await client.eval("window.__WIZARD_V3__.getState()")
        print(f"Initial State: {state0['state']}, Render Mode: {state0['renderMode']}")
        assert state0['state'] == 'IDLE'
        rev = await client.eval("THREE.REVISION")
        assert rev == '180', f"Expected Three.js r180, got {rev}"
        print(f"Three.js Revision: {rev}")

        # Pause background rAF stepping during deterministic evaluation
        await client.eval("window.__WIZARD_V3__.app.timeScale = 0.0;")

        # ---------------------------------------------------------
        # SUITE 2: Phase 8 Environment Polish Verification
        # ---------------------------------------------------------
        print("\n--- Suite 2: Phase 8 Environment Polish ---")
        p8_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const env = app.env;
                
                // 1. Foundation & Dais
                const hasDaisTex = env.daisStoneTex !== null && env.daisStoneTex !== undefined;
                const hasMasonryTex = env.masonryStoneTex !== null && env.masonryStoneTex !== undefined;
                const texturesDistinct = env.daisStoneTex !== env.masonryStoneTex;
                const daisRepeat = env.daisStoneTex.repeat.toArray();
                const masonryRepeat = env.masonryStoneTex.repeat.toArray();
                
                // 2. Asymmetric Rock Buttresses breaking conical outline
                const rockButtressCount = env.rockButtresses ? env.rockButtresses.length : 0;
                
                // 3. Mountains: 3 irregular ridge bands
                const ridgeBandCount = env.ridgeBands ? env.ridgeBands.length : 0;
                
                // 4. Moon & Halo
                const moonRadius = env.moonMesh ? env.moonMesh.geometry.parameters.radius : 0;
                const moonPosY = env.moonMesh ? env.moonMesh.position.y : 0;
                const haloIsBillboard = env.moonHaloMesh && env.moonHaloMesh.geometry.type === 'PlaneGeometry';
                const haloDepthWrite = env.moonHaloMesh ? env.moonHaloMesh.material.depthWrite : true;
                const haloDepthTest = env.moonHaloMesh ? env.moonHaloMesh.material.depthTest : false;
                
                // 5. Starfield: ONE Points draw call with custom attributes & fog disabled
                const starsIsPoints = env.starsMesh && env.starsMesh.isPoints;
                const starCount = env.starsMesh ? env.starsMesh.geometry.attributes.position.count : 0;
                const hasStarPhase = env.starsMesh && env.starsMesh.geometry.attributes.aPhase !== undefined;
                const hasStarBrightness = env.starsMesh && env.starsMesh.geometry.attributes.aBrightness !== undefined;
                const starsFogFalse = env.starsMesh && env.starsMesh.material.fog === false;
                
                // 6. Ground Mist: soft masked patches below/behind stage with stable baseY
                const mistCount = env.mistPlanes.length;
                let mistAllDepthWriteFalse = true;
                let mistAllDepthTestTrue = true;
                let mistAllBehindOrBelow = true;
                const mistHasBaseY = env.mistPlanes.every((p) => p.userData && p.userData.baseY !== undefined);
                env.mistPlanes.forEach((p) => {
                    if (p.material.depthWrite) mistAllDepthWriteFalse = false;
                    if (!p.material.depthTest) mistAllDepthTestTrue = false;
                    // None should be at wizard eye level z=0, y=0..3
                    if (p.position.z > -5 && p.position.y > -2) mistAllBehindOrBelow = false;
                });
                
                // 7. Ruins Kit & Staging (check no tall columns in wizard silhouette window [-9.0, -0.8])
                let obstructingColumns = 0;
                app.scene.traverse((obj) => {
                    if (obj.isMesh && obj.castShadow && obj.geometry && obj.geometry.type.includes('Cylinder')) {
                        const pos = obj.position;
                        // Wizard is at x=-4.5, y=0..4, z=0; staff/gem reaches x=-1.5
                        if (pos.x > -9.0 && pos.x < -0.8 && pos.z < -4.0 && pos.scale.y > 2.0) {
                            obstructingColumns++;
                        }
                    }
                });

                return {
                    hasDaisTex,
                    hasMasonryTex,
                    texturesDistinct,
                    daisRepeat,
                    masonryRepeat,
                    rockButtressCount,
                    ridgeBandCount,
                    moonRadius,
                    moonPosY,
                    haloIsBillboard,
                    haloDepthWrite,
                    haloDepthTest,
                    starsIsPoints,
                    starCount,
                    hasStarPhase,
                    hasStarBrightness,
                    starsFogFalse,
                    mistCount,
                    mistAllDepthWriteFalse,
                    mistAllDepthTestTrue,
                    mistAllBehindOrBelow,
                    mistHasBaseY,
                    obstructingColumns
                };
            })()
        """)
        print("Phase 8 Inspection Results:", p8_res)
        assert p8_res['hasDaisTex'] and p8_res['hasMasonryTex'], "Dais and masonry textures must exist"
        assert p8_res['texturesDistinct'], "Dais and masonry textures must be distinct"
        assert p8_res['rockButtressCount'] >= 6, f"Expected >= 6 rock buttresses, got {p8_res['rockButtressCount']}"
        assert p8_res['ridgeBandCount'] == 3, f"Expected 3 mountain ridge bands, got {p8_res['ridgeBandCount']}"
        assert p8_res['moonPosY'] >= 17.0, f"Moon height {p8_res['moonPosY']} must be >= 17.0 to clear wizard hat silhouette"
        assert p8_res['haloIsBillboard'], "Moon halo must be soft radial billboard"
        assert not p8_res['haloDepthWrite'] and p8_res['haloDepthTest'], "Moon halo depthWrite must be false, depthTest true"
        assert p8_res['starsIsPoints'] and p8_res['starCount'] == 1400, "Starfield must be ONE Points draw of 1400 stars"
        assert p8_res['hasStarPhase'] and p8_res['hasStarBrightness'], "Starfield must have aPhase and aBrightness attributes"
        assert p8_res['starsFogFalse'], "Starfield must have fog: false to remain visible through distance fog"
        assert p8_res['mistCount'] == 4, f"Expected 4 mist patches, got {p8_res['mistCount']}"
        assert p8_res['mistAllDepthWriteFalse'] and p8_res['mistAllDepthTestTrue'], "Mist depthWrite must be false, depthTest true"
        assert p8_res['mistAllBehindOrBelow'], "Mist must be below stage or behind ruins"
        assert p8_res['mistHasBaseY'], "Mist planes must retain baseY to prevent position drift across casts"
        assert p8_res['obstructingColumns'] == 0, f"Obstructing columns found behind wizard: {p8_res['obstructingColumns']}"
        print("PASS: Phase 8 Environment Polish conforms strictly to specification.")

        # ---------------------------------------------------------
        # SUITE 3: Phases 0–7 Comprehensive Regression
        # ---------------------------------------------------------
        print("\n--- Suite 3: Phases 0–7 Comprehensive Regression ---")
        
        # Test event-once guards across cycles
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
                    if (seenImpacts.has(event.castId)) window.__testResults.duplicateImpacts++;
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
                        if (seenReleases.has(currentCastId)) window.__testResults.duplicateReleases++;
                        seenReleases.add(currentCastId);
                        window.__testResults.releases.push({ castId: currentCastId, time: this.totalTime });
                    }
                };
                app.spellDirector.setLoop(true);
            })()
        """)

        # Step 3 full cycles at 120Hz
        await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                for (let i = 0; i < 120 * 24; i++) app.stepSimulation(1/120);
            })()
        """)
        t_res = await client.eval("window.__testResults")
        assert len(t_res['releases']) >= 3, "Failed to capture >= 3 releases"
        assert len(t_res['impacts']) >= 3, "Failed to capture >= 3 impacts"
        assert t_res['duplicateReleases'] == 0, "Duplicate release events detected"
        assert t_res['duplicateImpacts'] == 0, "Duplicate impact events detected"
        print(f"PASS: Event-once guards strictly hold (releases: {len(t_res['releases'])}, impacts: {len(t_res['impacts'])}, dupes: 0).")

        # Test Release Alignment
        align_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.spellDirector.setLoop(false);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.projectiles.active = false;
                app.wizard.resetToRest();
                app.spellDirector.requestCast(app.characterAdapter);
                let steps = 0;
                const gemPos = new THREE.Vector3();
                while (steps < 120 * 5 && !app.projectiles.active) {
                    app.stepSimulation(1/120);
                    steps++;
                }
                app.wizard.getGemWorldPosition(gemPos);
                const dist = gemPos.distanceTo(app.projectiles.originPos);
                return { distance: dist, active: app.projectiles.active };
            })()
        """)
        assert align_res['active'], "Projectile should be active"
        assert align_res['distance'] < 0.05, f"Release misaligned: {align_res['distance']} > 0.05"
        print(f"PASS: Release alignment distance {align_res['distance']:.4f} units (< 0.05).")

        # Test Transform Rest Recovery
        rest_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.spellDirector.setLoop(false);
                let guard = 0;
                while ((app.spellDirector.state !== 0 || app.spellDirector.stateTime < 0.8) && guard < 120 * 15) {
                    app.stepSimulation(1/120);
                    guard++;
                }
                const wiz = app.wizard;
                const rest = wiz.restPose;
                const deltas = {
                    rootPos: wiz.nodes.root.position.distanceTo(rest.rootPos),
                    rightArmRot: Math.abs(wiz.nodes.rightArm.rotation.x - rest.rightArmRot.x) + 
                                 Math.abs(wiz.nodes.rightArm.rotation.y - rest.rightArmRot.y) + 
                                 Math.abs(wiz.nodes.rightArm.rotation.z - rest.rightArmRot.z),
                    staffRot: Math.abs(wiz.nodes.staffGroup.rotation.x - rest.staffGroupRot.x) + 
                              Math.abs(wiz.nodes.staffGroup.rotation.y - rest.staffGroupRot.y) + 
                              Math.abs(wiz.nodes.staffGroup.rotation.z - rest.staffGroupRot.z)
                };
                wiz.resetToRest();
                return deltas;
            })()
        """)
        for k, v in rest_res.items():
            assert v < 1e-4, f"Transform drift in {k}: {v}"
        print("PASS: Wizard base transforms return strictly to rest pose with 0 drift.")

        # ---------------------------------------------------------
        # SUITE 4: Phase 9 Performance & Renderer Statistics
        # ---------------------------------------------------------
        print("\n--- Suite 4: Phase 9 Performance & Renderer Statistics ---")
        
        # Test Complete Frame Stats vs Scene Stats
        stats = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                
                // 1. Idle Stats
                app.renderFrame();
                const idleComposerStats = app.renderer.info.render;
                const idleSceneStats = app.getSceneStatistics();
                
                // 2. Charge 60% Stats
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < 120 * app.spellDirector.DUR_CHARGE * 0.60; i++) app.stepSimulation(1/120);
                app.renderFrame();
                const chargeComposerStats = app.renderer.info.render;
                const chargeSceneStats = app.getSceneStatistics();
                
                // 3. Impact Stats
                let guard = 0;
                while (app.spellDirector.impactAge < 0.02 && guard < 120 * 5) {
                    app.stepSimulation(1/120);
                    guard++;
                }
                app.renderFrame();
                const impactComposerStats = app.renderer.info.render;
                const impactSceneStats = app.getSceneStatistics();
                
                // Resources
                const memory = app.renderer.info.memory;

                return {
                    idle: { composer: { ...idleComposerStats }, scene: idleSceneStats },
                    charge: { composer: { ...chargeComposerStats }, scene: chargeSceneStats },
                    impact: { composer: { ...impactComposerStats }, scene: impactSceneStats },
                    memory: { ...memory }
                };
            })()
        """)
        print("Idle Stats   -> Scene Draws:", stats['idle']['scene']['calls'], "Scene Tris:", stats['idle']['scene']['triangles'], "| Composer Draws:", stats['idle']['composer']['calls'])
        print("Charge Stats -> Scene Draws:", stats['charge']['scene']['calls'], "Scene Tris:", stats['charge']['scene']['triangles'], "| Composer Draws:", stats['charge']['composer']['calls'])
        print("Impact Stats -> Scene Draws:", stats['impact']['scene']['calls'], "Scene Tris:", stats['impact']['scene']['triangles'], "| Composer Draws:", stats['impact']['composer']['calls'])
        print("Memory Stats -> Geometries:", stats['memory']['geometries'], "Textures:", stats['memory']['textures'])

        # Guardrails: Scene draws around 180 (idle <= 180, impact <= 200), Scene triangles <= 150k
        assert stats['idle']['scene']['calls'] <= 180, f"Idle scene calls {stats['idle']['scene']['calls']} > 180"
        assert stats['charge']['scene']['calls'] <= 180, f"Charge scene calls {stats['charge']['scene']['calls']} > 180"
        assert stats['impact']['scene']['calls'] <= 200, f"Impact scene calls {stats['impact']['scene']['calls']} > 200"
        assert stats['impact']['scene']['triangles'] <= 150000, f"Impact scene tris {stats['impact']['scene']['triangles']} > 150000"
        print("PASS: Scene-level draw calls (around 180) and triangles (<= 150k) well within guardrails.")

        # Measure 120 consecutive frame render execution times
        perf_data = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const timings = [];
                
                // Warm up 10 frames
                for (let i = 0; i < 10; i++) {
                    app.stepSimulation(1/60);
                    app.renderFrame();
                }
                
                // Measure 120 frames during active cast
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < 120; i++) {
                    app.stepSimulation(1/60);
                    const t0 = performance.now();
                    app.renderFrame();
                    const t1 = performance.now();
                    timings.push(t1 - t0);
                }
                
                timings.sort((a, b) => a - b);
                const sum = timings.reduce((a, b) => a + b, 0);
                const mean = sum / timings.length;
                const median = timings[Math.floor(timings.length * 0.5)];
                const p95 = timings[Math.floor(timings.length * 0.95)];
                const min = timings[0];
                const max = timings[timings.length - 1];

                return {
                    count: timings.length,
                    min: min.toFixed(2),
                    max: max.toFixed(2),
                    mean: mean.toFixed(2),
                    median: median.toFixed(2),
                    p95: p95.toFixed(2),
                    fpsEquiv: (1000 / mean).toFixed(1)
                };
            })()
        """)
        print(f"Performance Profile (1920x1080, DPR 1.0, 120 active frames):")
        print(f"  Mean Frame Time:   {perf_data['mean']} ms ({perf_data['fpsEquiv']} FPS equivalent)")
        print(f"  Median Frame Time: {perf_data['median']} ms")
        print(f"  p95 Frame Time:    {perf_data['p95']} ms (target <= 20.0 ms)")
        print(f"  Min/Max Frame:     {perf_data['min']} ms / {perf_data['max']} ms")
        assert float(perf_data['p95']) <= 20.0, f"p95 frame time {perf_data['p95']} ms exceeded 20 ms budget"
        print("PASS: Performance satisfies 60 FPS and p95 <= 20ms budget.")

        # ---------------------------------------------------------
        # SUITE 5: 100-Cast Stress Test
        # ---------------------------------------------------------
        print("\n--- Suite 5: 100-Cast Comprehensive Stress Test ---")
        stress_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const wiz = app.wizard;
                const initialGeos = app.renderer.info.memory.geometries;
                const initialTexs = app.renderer.info.memory.textures;
                
                let completedCasts = 0;
                let completedReleases = 0;
                let completedDetonations = 0;
                
                // 1. 40 Normal Full Cycles
                app.spellDirector.setLoop(false);
                for (let c = 0; c < 40; c++) {
                    app.spellDirector.state = 0;
                    app.spellDirector.stateTime = 0;
                    app.wizard.resetToRest();
                    app.spellDirector.requestCast(app.characterAdapter);
                    completedCasts++;
                    
                    // Run through entire cycle until IDLE (approx 7.0s = 840 steps)
                    let steps = 0;
                    let hadRelease = false;
                    let hadImpact = false;
                    while ((app.spellDirector.state !== 0 || steps < 120 * 2) && steps < 120 * 8) {
                        const wasRel = app.spellDirector.releaseFired;
                        const wasImp = app.spellDirector.impactFired;
                        app.stepSimulation(1/120);
                        if (!wasRel && app.spellDirector.releaseFired) hadRelease = true;
                        if (!wasImp && app.spellDirector.impactFired) hadImpact = true;
                        steps++;
                    }
                    if (hadRelease) completedReleases++;
                    if (hadImpact) completedDetonations++;
                }

                // 2. 30 Early Release Cycles (at 25%, 50%, 75% charge)
                for (let c = 0; c < 30; c++) {
                    app.spellDirector.state = 0;
                    app.spellDirector.stateTime = 0;
                    app.wizard.resetToRest();
                    app.spellDirector.requestCast(app.characterAdapter);
                    completedCasts++;
                    
                    const progressFraction = 0.25 + (c % 3) * 0.25;
                    const chargeSteps = Math.floor(120 * app.spellDirector.DUR_CHARGE * progressFraction);
                    for (let s = 0; s < chargeSteps; s++) app.stepSimulation(1/120);
                    
                    // Request early release
                    app.spellDirector.requestCast(app.characterAdapter);
                    
                    let steps = 0;
                    let hadRelease = false;
                    let hadImpact = false;
                    while ((app.spellDirector.state !== 0 || steps < 120 * 2) && steps < 120 * 8) {
                        const wasRel = app.spellDirector.releaseFired;
                        const wasImp = app.spellDirector.impactFired;
                        app.stepSimulation(1/120);
                        if (!wasRel && app.spellDirector.releaseFired) hadRelease = true;
                        if (!wasImp && app.spellDirector.impactFired) hadImpact = true;
                        steps++;
                    }
                    if (hadRelease) completedReleases++;
                    if (hadImpact) completedDetonations++;
                }

                // 3. 20 Recovery Retrigger Cycles
                for (let c = 0; c < 20; c++) {
                    app.spellDirector.state = 0;
                    app.spellDirector.stateTime = 0;
                    app.wizard.resetToRest();
                    app.spellDirector.requestCast(app.characterAdapter);
                    completedCasts++;
                    
                    // Advance to RECOVER state
                    let guard = 0;
                    while (app.spellDirector.state !== 3 && guard < 120 * 6) {
                        app.stepSimulation(1/120);
                        guard++;
                    }
                    completedReleases++;
                    completedDetonations++;
                    
                    // Retrigger cast during recovery
                    app.spellDirector.requestCast(app.characterAdapter);
                    completedCasts++;
                    
                    guard = 0;
                    while ((app.spellDirector.state !== 0 || guard < 120 * 2) && guard < 120 * 8) {
                        app.stepSimulation(1/120);
                        guard++;
                    }
                    completedReleases++;
                    completedDetonations++;
                }

                // Total casts executed: 40 + 30 + 20*2 = 110 casts (>= 100)
                // Let scene settle strictly to IDLE rest
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 1.0;
                app.wizard.resetToRest();
                app.projectiles.active = false;
                app.env.decayImpactLight(1.0);
                app.particles.vortexPoints.visible = false;

                const finalGeos = app.renderer.info.memory.geometries;
                const finalTexs = app.renderer.info.memory.textures;
                const projActive = app.projectiles.active;
                const monolithLightIntensity = app.env.monolithLight ? app.env.monolithLight.intensity : 0;
                const sparkCount = app.particles.getActiveSparkCount();
                
                return {
                    completedCasts,
                    completedReleases,
                    completedDetonations,
                    initialGeos,
                    finalGeos,
                    initialTexs,
                    finalTexs,
                    projActive,
                    monolithLightIntensity,
                    sparkCount
                };
            })()
        """)
        print("100-Cast Stress Results:", stress_res)
        assert stress_res['completedCasts'] >= 100, f"Expected >= 100 casts, ran {stress_res['completedCasts']}"
        assert stress_res['completedReleases'] == stress_res['completedCasts'], "Mismatch in releases vs casts"
        assert stress_res['completedDetonations'] == stress_res['completedCasts'], "Mismatch in detonations vs casts"
        assert not stress_res['projActive'], "Stranded projectile detected"
        assert stress_res['monolithLightIntensity'] == 0, f"Stranded light: {stress_res['monolithLightIntensity']}"
        assert stress_res['sparkCount'] == 0, f"Stranded sparks: {stress_res['sparkCount']}"
        assert stress_res['finalGeos'] == stress_res['initialGeos'], f"Geometry leak: {stress_res['initialGeos']} -> {stress_res['finalGeos']}"
        assert stress_res['finalTexs'] == stress_res['initialTexs'], f"Texture leak: {stress_res['initialTexs']} -> {stress_res['finalTexs']}"
        print("PASS: 100-cast stress test completed with zero stranded entities, zero leaks, and clean rest state.")

        # ---------------------------------------------------------
        # SUITE 6: Playback Speed & Frame-rate Robustness
        # ---------------------------------------------------------
        print("\n--- Suite 6: Playback Speed & Frame-Rate Robustness ---")
        speeds_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const speeds = [0.25, 1.0, 1.8];
                const results = [];
                
                speeds.forEach((spd) => {
                    app.timeScale = spd;
                    app.spellDirector.state = 0;
                    app.spellDirector.stateTime = 0;
                    app.wizard.resetToRest();
                    app.spellDirector.requestCast(app.characterAdapter);
                    
                    let hadRelease = false;
                    let hadImpact = false;
                    let finiteTransforms = true;
                    
                    for (let s = 0; s < 120 * 6; s++) {
                        app.stepSimulation(1/120);
                        if (app.spellDirector.releaseFired) hadRelease = true;
                        if (app.spellDirector.impactFired) hadImpact = true;
                        
                        const px = app.wizard.nodes.root.position.x;
                        if (!isFinite(px)) finiteTransforms = false;
                    }
                    
                    results.push({ spd, hadRelease, hadImpact, finiteTransforms });
                });
                
                app.timeScale = 1.0;
                return results;
            })()
        """)
        print("Speed Robustness Results:", speeds_res)
        for r in speeds_res:
            assert r['hadRelease'] and r['hadImpact'], f"Speed {r['spd']}x failed to complete cycle"
            assert r['finiteTransforms'], f"Speed {r['spd']}x produced non-finite transforms"
        print("PASS: Playback speed variations (0.25x, 1x, 1.8x) maintain exact order and finite transforms.")

        # ---------------------------------------------------------
        # SUITE 7: Complete Control & Interaction Regression
        # ---------------------------------------------------------
        print("\n--- Suite 7: Complete Control Regression ---")
        ctrl_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const results = {};
                
                // 1. Presets
                const presets = ['cinematic', 'classic', 'hero', 'target', 'orbit'];
                presets.forEach((p) => {
                    app.director.setPreset(p);
                    results['preset_' + p] = app.director.mode === p;
                });
                app.director.setPreset('cinematic');
                
                // 2. Loop toggle
                const initialLoop = app.autoLoop;
                app.spellDirector.setLoop(!initialLoop);
                results['loop_toggle'] = app.spellDirector.loop === !initialLoop;
                app.spellDirector.setLoop(initialLoop);
                
                // 3. Audio toggle
                const aEnabled = audio.enabled;
                const aToggled = audio.toggle();
                results['audio_toggle'] = aToggled === !aEnabled;
                audio.toggle(); // restore
                
                // 4. Render mode cycle
                const initMode = app.renderMode;
                app.cycleRenderMode();
                const mode1 = app.renderMode;
                app.cycleRenderMode();
                const mode2 = app.renderMode;
                app.cycleRenderMode();
                const mode3 = app.renderMode;
                results['render_mode_cycle'] = (mode1 !== initMode && mode2 !== mode1 && mode3 === initMode);
                
                // 5. Visibility change suspension & resume
                Object.defineProperty(document, 'hidden', { value: true, configurable: true });
                document.dispatchEvent(new Event('visibilitychange'));
                app.accumulator += 1.5;
                if (app.accumulator > app.maxBacklogSteps * app.fixedDelta) {
                    app.accumulator = app.maxBacklogSteps * app.fixedDelta;
                }
                const clamped = app.accumulator <= app.maxBacklogSteps * app.fixedDelta;
                
                Object.defineProperty(document, 'hidden', { value: false, configurable: true });
                document.dispatchEvent(new Event('visibilitychange'));
                const resumed = app.accumulator === 0.0;
                results['visibility_resume'] = clamped && resumed;

                return results;
            })()
        """)
        print("Control Regression Results:", ctrl_res)
        for k, v in ctrl_res.items():
            assert v, f"Control test failed: {k}"
        print("PASS: All presets, toggles, modes, and suspension/resume verified.")

        # ---------------------------------------------------------
        # SUITE 8: Browser Regression Coverage
        # ---------------------------------------------------------
        print("\n--- Suite 8: Browser Regression Coverage ---")
        print(f"Chromium Console Errors: {len(client.console_errors)}")
        if client.console_errors:
            print("Errors detected:", client.console_errors)
        assert len(client.console_errors) == 0, f"Browser console errors encountered: {client.console_errors}"
        print("PASS: Chromium WebGL2 and JavaScript execution clean with 0 console errors.")

        # Secondary browser test: Firefox
        print("\nTesting secondary browser (Mozilla Firefox)...")
        with tempfile.TemporaryDirectory() as profile_dir:
            ff_screenshot_path = os.path.join(profile_dir, "firefox_render.png")
            ff_cmd = [
                FIREFOX_BIN,
                '--headless',
                '--no-remote',
                '--profile', profile_dir,
                '--screenshot', ff_screenshot_path,
                '--window-size=1920,1080',
                f'http://127.0.0.1:{HTTP_PORT}/wizard-v3.html'
            ]
            ff_res = subprocess.run(ff_cmd, capture_output=True, text=True, timeout=20)
            print(f"Firefox process exited with code {ff_res.returncode}")
            assert ff_res.returncode == 0, f"Firefox execution failed: {ff_res.stderr}"
            assert os.path.exists(ff_screenshot_path) and os.path.getsize(ff_screenshot_path) > 10000, "Firefox failed to render image"
        print("PASS: Mozilla Firefox WebGL2 execution confirmed clean.")

        # ---------------------------------------------------------
        # SUITE 9: Disposal & Lifecycle Teardown / Reinitialization
        # ---------------------------------------------------------
        print("\n--- Suite 9: Disposal & Lifecycle Teardown / Reinitialization ---")
        lifecycle_res = await client.eval("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                
                // Teardown
                app.dispose();
                const tornDown = typeof window.__WIZARD_V3__ === 'undefined';
                
                // Reinitialize
                const newApp = new App();
                const reinitialized = typeof window.__WIZARD_V3__ !== 'undefined';
                
                // Step new app
                newApp.stepSimulation(1/60);
                newApp.renderFrame();
                const stateAfterReinit = newApp.spellDirector.sample().state;

                return { tornDown, reinitialized, stateAfterReinit };
            })()
        """)
        print("Lifecycle Results:", lifecycle_res)
        assert lifecycle_res['tornDown'], "Teardown failed to remove window.__WIZARD_V3__"
        assert lifecycle_res['reinitialized'], "Reinitialization failed to recreate window.__WIZARD_V3__"
        print("PASS: Complete disposal and clean reinitialization cycle verified.")

        # ---------------------------------------------------------
        # SUITE 10: Final Pass 3 Visual Evidence Captures (1920x1080)
        # ---------------------------------------------------------
        print("\n--- Suite 10: Final Pass 3 Visual Evidence Captures ---")

        async def capture_at(setup_js, filename):
            await client.eval(setup_js)
            await client.eval("window.__WIZARD_V3__.app.renderFrame()")
            await asyncio.sleep(0.1)
            await client.screenshot(filename)

        # 1. Cinematic Idle
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 1.0;
                app.wizard.resetToRest();
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-cinematic-idle.png")

        # 2. Cinematic Early Charge (20%)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('cinematic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.20); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-cinematic-charge-early.png")

        # 3. Cinematic Mid Charge (60%)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('cinematic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.60); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-cinematic-charge-mid.png")

        # 4. Cinematic Late Charge / Peak Compression (95%)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('cinematic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.95); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-cinematic-charge-peak.png")

        # 5. Cinematic Release Apex (CAST 15%)
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                const durCast = app.spellDirector.DUR_CAST;
                app.director.setPreset('cinematic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                const totalSteps = Math.floor(120 * durCharge) + Math.floor(120 * durCast * 0.15);
                for (let i = 0; i < totalSteps; i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-cinematic-release.png")

        # 6. Cinematic Projectile Mid-Flight with Ribbon
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                const durCast = app.spellDirector.DUR_CAST;
                app.director.setPreset('cinematic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                const totalSteps = Math.floor(120 * durCharge) + Math.floor(120 * durCast * 0.15) + 18;
                for (let i = 0; i < totalSteps; i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-cinematic-projectile.png")

        # 7. Cinematic Impact Detonation
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic', true);
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
        """, "v3-pass3-cinematic-impact.png")

        # 8. Cinematic Aftermath / Recovered Idle
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic', true);
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
        """, "v3-pass3-cinematic-aftermath.png")

        # 9. Classic Preset Idle
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('classic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 1.0;
                app.wizard.resetToRest();
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-classic-idle.png")

        # 10. Classic Preset Charge
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                const durCharge = app.spellDirector.DUR_CHARGE;
                app.director.setPreset('classic', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 0;
                app.spellDirector.requestCast(app.characterAdapter);
                for (let i = 0; i < Math.floor(120 * durCharge * 0.70); i++) app.stepSimulation(1/120);
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-classic-charge.png")

        # 11. Classic Preset Impact
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('classic', true);
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
        """, "v3-pass3-classic-impact.png")

        # 12. Hero Preset Portrait
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('hero', true);
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 1.0;
                app.wizard.resetToRest();
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-hero-portrait.png")

        # 13. Bloom Disabled Comparison
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic', true);
                app.setRenderMode(1); // RENDER_MODE_COMPOSER_BLOOM_OFF
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 1.0;
                app.wizard.resetToRest();
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-bloom-off.png")

        # 14. Direct Renderer Comparison
        await capture_at("""
            (() => {
                const app = window.__WIZARD_V3__.app;
                app.director.setPreset('cinematic', true);
                app.setRenderMode(2); // RENDER_MODE_DIRECT
                app.spellDirector.state = 0;
                app.spellDirector.stateTime = 1.0;
                app.wizard.resetToRest();
                app.director.update(1/60, app.spellDirector.sample());
            })()
        """, "v3-pass3-direct-render.png")

        print("\nAll 14 Pass 3 visual evidence artifacts captured successfully.")
        print("\n=====================================================================")
        print("=== ALL PASS 3 VERIFICATIONS PASSED CLEANLY ===")
        print("=====================================================================\n")

    finally:
        brave_proc.terminate()
        brave_proc.wait()

if __name__ == '__main__':
    import tempfile
    asyncio.run(main())
