// NWO MR — Immersive viewer (splat / mesh / world / image / video)
// Renders inside the media modal. Provides navigation overlay
// (forward, back, left, right, look-up, look-down) + WebXR VR/AR
// for content types where it makes sense.
//
// Public API:
//   openImmersive({ url, kind?, title? }, container)
//   closeImmersive()
//   detectKind(url) → 'glb' | 'lumalabs' | 'marble' | 'pano' | 'image' | 'video' | 'iframe'

let _threeCleanup = null;
let _xrSession = null;
let _navCleanup = null;

export function openImmersive(content, container) {
    closeImmersive();
    container.innerHTML = '';
    const kind = content.kind || detectKind(content.url);
    const url  = content.url;
    if (!url) return;

    if (kind === 'glb')                                return renderGlbModelViewer(url, container);
    if (kind === 'lumalabs' || kind === 'marble' ||
        kind === 'splat-iframe' || kind === 'splat4d' ||
        kind === 'iframe')                              return renderIframeViewer(url, container, kind);
    if (kind === 'pano')                                return renderEquirectThree(url, container);
    if (kind === 'video')                               return renderVideo(url, container);
    if (kind === 'image')                               return renderImage(url, container);
    return renderIframeViewer(url, container, 'unknown');
}

export function closeImmersive() {
    if (_threeCleanup) { try { _threeCleanup(); } catch (_) {} _threeCleanup = null; }
    if (_xrSession)    { try { _xrSession.end?.(); } catch (_) {} _xrSession = null; }
    if (_navCleanup)   { try { _navCleanup(); } catch (_) {} _navCleanup = null; }
}

export function detectKind(url) {
    if (!url) return 'iframe';
    if (/\.(glb|gltf)(\?|$)/i.test(url))                 return 'glb';
    if (url.includes('lumalabs.ai/capture/') ||
        url.includes('lumalabs.ai/embed/'))              return 'lumalabs';
    if (url.includes('worldlabs.ai/') ||
        url.includes('marble.worldlabs.ai/'))            return 'marble';
    // 4DGS — dynamic Gaussian splat from our RunPod pod or LichtFeld viewer
    if (/\.splat4d(\?|$)/i.test(url) ||
        url.includes('lichtfeld.io/view/') ||
        url.includes('/files/') && /\.splat4d/i.test(url)) return 'splat4d';
    if (/\.(splat|ply)(\?|$)/i.test(url))                return 'splat-iframe';
    if (/equirect|panorama|skybox|2048x1024/i.test(url)) return 'pano';
    if (/\.(png|jpe?g|webp|gif|svg|avif)(\?|$)/i.test(url) || url.startsWith('data:image/'))
                                                          return 'image';
    if (/\.(mp4|webm|mov|m4v)(\?|$)/i.test(url))         return 'video';
    return 'iframe';
}

// ─── GLB / GLTF ────────────────────────────────
function renderGlbModelViewer(url, container) {
    const mv = document.createElement('model-viewer');
    mv.setAttribute('src', url);
    mv.setAttribute('auto-rotate', '');
    mv.setAttribute('camera-controls', '');
    mv.setAttribute('exposure', '1.2');
    mv.setAttribute('shadow-intensity', '0.8');
    mv.setAttribute('ar', '');
    mv.setAttribute('ar-modes', 'webxr scene-viewer quick-look');
    mv.style.width = '100%';
    mv.style.height = '100%';
    mv._orbit = { theta: 0, phi: 75, radius: 2.5 };
    container.appendChild(mv);
    container.appendChild(buildNavOverlay({
        onMove: (dir) => stepGlbCamera(mv, dir),
        onVR:   () => activateXR(mv),
        onReset:() => { mv._orbit = { theta: 0, phi: 75, radius: 2.5 }; mv.cameraOrbit = '0deg 75deg 2.5m'; },
        vrSupported: true,
    }));
}

function stepGlbCamera(mv, dir) {
    const o = mv._orbit;
    const dDeg = 12, dZoom = 0.25;
    if (dir === 'left')    o.theta -= dDeg;
    if (dir === 'right')   o.theta += dDeg;
    if (dir === 'up')      o.phi = Math.max(5, o.phi - dDeg);
    if (dir === 'down')    o.phi = Math.min(175, o.phi + dDeg);
    if (dir === 'forward') o.radius = Math.max(0.4, o.radius - dZoom);
    if (dir === 'back')    o.radius = Math.min(20, o.radius + dZoom);
    mv.cameraOrbit = `${o.theta}deg ${o.phi}deg ${o.radius}m`;
}

async function activateXR(mv) {
    if (!('xr' in navigator)) return toast('WebXR not available in this browser');
    try { if (mv.activateAR) await mv.activateAR(); }
    catch (e) { toast('XR launch failed: ' + (e.message || '')); }
}

// ─── Iframe viewers (Luma, Marble) ────────────
function renderIframeViewer(url, container, kind) {
    const iframe = document.createElement('iframe');
    iframe.className = 'mm-iframe';
    iframe.allow = 'fullscreen; xr-spatial-tracking; accelerometer; gyroscope; magnetometer; autoplay';
    iframe.allowFullscreen = true;
    if (kind === 'lumalabs') {
        const capId = url.match(/capture\/([\w-]+)/)?.[1] || url.match(/embed\/([\w-]+)/)?.[1];
        iframe.src = capId ? `https://lumalabs.ai/embed/${capId}` : url;
    } else if (kind === 'splat4d') {
        // 4DGS from our RunPod pod. If already a viewer URL, embed directly.
        // Otherwise wrap the raw .splat4d through LichtFeld's web viewer.
        if (url.includes('lichtfeld.io/view/')) {
            iframe.src = url;
        } else {
            iframe.src = `https://lichtfeld.io/view/?src=${encodeURIComponent(url)}`;
        }
    } else {
        iframe.src = url;
    }
    container.appendChild(iframe);

    const hint = document.createElement('div');
    hint.className = 'mm-nav-hint';
    const label = kind === 'lumalabs' ? 'LUMA'
               : kind === 'marble'   ? 'MARBLE'
               : kind === 'splat4d'  ? '4DGS · VOLUMETRIC'
               : 'EMBEDDED';
    const tip = kind === 'splat4d'
        ? 'Drag to look · scrub timeline · scene evolves over time'
        : 'Drag to look · scroll to zoom · pinch on mobile';
    hint.innerHTML = `
        <div class="mm-hint-row">
            <span class="mm-hint-label">${label} · IMMERSIVE</span>
            <span class="mm-hint-text">${tip}</span>
        </div>
        <button class="mm-nav-fullscreen" title="Fullscreen">⛶</button>
    `;
    hint.querySelector('.mm-nav-fullscreen').addEventListener('click', () => {
        if (iframe.requestFullscreen) iframe.requestFullscreen();
        else if (iframe.webkitRequestFullscreen) iframe.webkitRequestFullscreen();
    });
    container.appendChild(hint);
}

// ─── 360° equirect panorama via Three.js ──────
function renderEquirectThree(url, container) {
    if (!window.THREE) {
        const s = document.createElement('script');
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
        s.onload = () => renderEquirectThree(url, container);
        document.head.appendChild(s);
        container.innerHTML = '<div class="mm-loading">Loading 3D viewer…</div>';
        return;
    }
    const THREE = window.THREE;
    container.innerHTML = '';

    const w = container.clientWidth || 800, h = container.clientHeight || 600;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, w / h, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h);
    renderer.xr.enabled = true;
    container.appendChild(renderer.domElement);

    const geom = new THREE.SphereGeometry(50, 64, 32);
    geom.scale(-1, 1, 1);
    const loader = new THREE.TextureLoader();
    loader.crossOrigin = 'anonymous';
    const mat = new THREE.MeshBasicMaterial({ map: loader.load(url) });
    scene.add(new THREE.Mesh(geom, mat));

    const state = { lon: 0, lat: 0, fov: 75, dragging: false, lastX: 0, lastY: 0 };
    const onDown = (e) => { state.dragging = true; state.lastX = e.clientX; state.lastY = e.clientY; };
    const onMove = (e) => {
        if (!state.dragging) return;
        state.lon -= (e.clientX - state.lastX) * 0.25;
        state.lat = Math.max(-85, Math.min(85, state.lat + (e.clientY - state.lastY) * 0.25));
        state.lastX = e.clientX; state.lastY = e.clientY;
    };
    const onUp = () => { state.dragging = false; };
    renderer.domElement.addEventListener('mousedown', onDown);
    renderer.domElement.addEventListener('mousemove', onMove);
    renderer.domElement.addEventListener('mouseup', onUp);
    renderer.domElement.addEventListener('mouseleave', onUp);
    renderer.domElement.addEventListener('touchstart', (e) => onDown(e.touches[0]), { passive: true });
    renderer.domElement.addEventListener('touchmove',  (e) => onMove(e.touches[0]),  { passive: true });
    renderer.domElement.addEventListener('touchend', onUp);
    renderer.domElement.addEventListener('wheel', (e) => {
        state.fov = Math.max(20, Math.min(110, state.fov + e.deltaY * 0.05));
        camera.fov = state.fov; camera.updateProjectionMatrix();
        e.preventDefault();
    }, { passive: false });

    renderer.setAnimationLoop(() => {
        const phi = THREE.MathUtils.degToRad(90 - state.lat);
        const theta = THREE.MathUtils.degToRad(state.lon);
        camera.lookAt(new THREE.Vector3(
            Math.sin(phi) * Math.cos(theta),
            Math.cos(phi),
            Math.sin(phi) * Math.sin(theta),
        ));
        renderer.render(scene, camera);
    });

    const onResize = () => {
        const W = container.clientWidth, H = container.clientHeight;
        camera.aspect = W / H; camera.updateProjectionMatrix();
        renderer.setSize(W, H);
    };
    window.addEventListener('resize', onResize);

    container.appendChild(buildNavOverlay({
        onMove: (dir) => {
            const d = 15, fovStep = 6;
            if (dir === 'left')    state.lon -= d;
            if (dir === 'right')   state.lon += d;
            if (dir === 'up')      state.lat = Math.min(85, state.lat + d);
            if (dir === 'down')    state.lat = Math.max(-85, state.lat - d);
            if (dir === 'forward') { state.fov = Math.max(20, state.fov - fovStep); camera.fov = state.fov; camera.updateProjectionMatrix(); }
            if (dir === 'back')    { state.fov = Math.min(110, state.fov + fovStep); camera.fov = state.fov; camera.updateProjectionMatrix(); }
        },
        onReset: () => { state.lon = 0; state.lat = 0; state.fov = 75; camera.fov = 75; camera.updateProjectionMatrix(); },
        onVR: async () => {
            if (!('xr' in navigator)) return toast('WebXR not available');
            try {
                const session = await navigator.xr.requestSession('immersive-vr', { optionalFeatures: ['local-floor'] });
                renderer.xr.setSession(session); _xrSession = session;
            } catch (e) { toast('VR launch failed: ' + (e.message || 'no headset')); }
        },
        vrSupported: true,
    }));

    _threeCleanup = () => {
        window.removeEventListener('resize', onResize);
        renderer.setAnimationLoop(null);
        renderer.dispose();
        geom.dispose();
        if (mat.map) mat.map.dispose();
        mat.dispose();
        container.innerHTML = '';
    };
}

// ─── Plain image / video ──────────────────────
function renderImage(url, container) {
    const img = document.createElement('img');
    img.className = 'mm-img'; img.src = url; img.referrerPolicy = 'no-referrer';
    container.appendChild(img);
}
function renderVideo(url, container) {
    const v = document.createElement('video');
    v.className = 'mm-video'; v.src = url; v.controls = true; v.autoplay = true; v.loop = true;
    container.appendChild(v);
}

// ─── Navigation overlay ───────────────────────
function buildNavOverlay({ onMove, onVR, onReset, vrSupported }) {
    const nav = document.createElement('div');
    nav.className = 'mm-nav';
    nav.innerHTML = `
        <div class="mm-nav-group mm-nav-look">
            <button class="mm-nav-btn" data-dir="up"    title="Look up (W / ↑)">↑</button>
            <div class="mm-nav-row">
                <button class="mm-nav-btn" data-dir="left"  title="Look left (A / ←)">←</button>
                <button class="mm-nav-btn mm-nav-reset" data-dir="reset" title="Reset view (R)">◎</button>
                <button class="mm-nav-btn" data-dir="right" title="Look right (D / →)">→</button>
            </div>
            <button class="mm-nav-btn" data-dir="down"  title="Look down (S / ↓)">↓</button>
        </div>
        <div class="mm-nav-group mm-nav-zoom">
            <button class="mm-nav-btn" data-dir="forward" title="Move forward / zoom in (+)">＋</button>
            <button class="mm-nav-btn" data-dir="back"    title="Move back / zoom out (-)">−</button>
            ${vrSupported ? `<button class="mm-nav-btn mm-nav-vr" data-dir="vr" title="Enter VR / AR">VR</button>` : ''}
        </div>
    `;
    nav.querySelectorAll('[data-dir]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const dir = btn.dataset.dir;
            if (dir === 'vr')    return onVR?.();
            if (dir === 'reset') return onReset?.();
            onMove?.(dir);
        });
    });

    const keyHandler = (e) => {
        if (e.target.matches('input, textarea')) return;
        const map = {
            'ArrowUp': 'up', 'ArrowDown': 'down', 'ArrowLeft': 'left', 'ArrowRight': 'right',
            'w': 'up', 's': 'down', 'a': 'left', 'd': 'right',
            '+': 'forward', '=': 'forward', '-': 'back', '_': 'back',
            'r': 'reset',
        };
        const dir = map[e.key];
        if (!dir) return;
        e.preventDefault();
        if (dir === 'reset') return onReset?.();
        onMove?.(dir);
    };
    document.addEventListener('keydown', keyHandler);
    _navCleanup = () => document.removeEventListener('keydown', keyHandler);
    return nav;
}

function toast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast show err';
    setTimeout(() => t.classList.remove('show'), 3000);
}
