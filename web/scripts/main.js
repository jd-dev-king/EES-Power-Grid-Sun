import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const cfg = window.POWER_GRID_SUN_CONFIG;

let snapshot = null;
let scope = 'CAMPUS';
let selected = null;

let hasLiveSnapshot = false;
let fetchInProgress = false;

const $ = id => document.getElementById(id);
const demo = { timestamp: new Date().toISOString(), campus: { real_power_kw: 1048.4, reactive_power_kvar: 273.2, apparent_power_kva: 1083.4, power_factor: .968, open_alerts: 2 }, facilities: [{ code: 'PHARMA', name: 'Pharma Manufacturing Plant', real_power_kw: 394.2, assets_running: 6, faults: 0 }, { code: 'LOGISTICS', name: 'Global Supply Logistics Facility', real_power_kw: 285.7, assets_running: 5, faults: 1 }, { code: 'UTILITIES', name: 'Central Utilities Plant', real_power_kw: 344.6, assets_running: 6, faults: 1 }, { code: 'EXEC', name: 'EES Executive Suites', real_power_kw: 23.9, assets_running: 2, faults: 0 }], assets: [], alerts: [{ severity: 'HIGH', asset_code: 'COLD-420', title: 'Cold storage compressor current deviation', message: 'Current is 11% above learned operating baseline.' }, { severity: 'HIGH', asset_code: 'AC-01', title: 'Compressed-air leak signature', message: 'Loaded runtime increased while header demand remained stable.' }] };
const names = [['PHARMA', 'TAB-201', 'Tablet Press', 62.4, 78, .91, 54, 94], ['PHARMA', 'FILL-301', 'Bottle Filling Line', 31.8, 46, .90, 48, 98], ['LOGISTICS', 'CONV-401', 'Main Sortation Conveyor', 51.6, 74, .88, 55, 96], ['LOGISTICS', 'COLD-420', 'Cold Storage Compressors', 126.2, 181, .86, 74, 82], ['UTILITIES', 'CH-01', 'Process Chiller 1', 298.3, 44, .91, 69, 93], ['UTILITIES', 'AC-01', 'Plant Air Compressor 1', 179.7, 255, .85, 78, 84], ['EXEC', 'EOC-IT', 'Executive Data Systems', 22.8, 66, .98, 36, 99]];
demo.assets = names.map((x, i) => ({ asset_id: String(i), facility: x[0], code: x[1], name: x[2], area: 'Industrial Area', asset_type: 'motor', critical: i % 2 === 0, operating_state: 'RUNNING', voltage_v: x[0] === 'UTILITIES' && i === 4 ? 4160 : 480, current_a: x[4], real_power_kw: x[3], reactive_power_kvar: x[3] * .25, apparent_power_kva: x[3] / x[5], power_factor: x[5], frequency_hz: 59.99, breaker_utilization_pct: 63, temperature_c: x[6], health_pct: x[7], fault_code: x[7] < 90 ? 'ANOMALY_DETECTED' : null }));
async function fetchSnapshot() {
  if (fetchInProgress) return;

  fetchInProgress = true;

  try {
    const r = await fetch(
      cfg.apiBaseUrl + '/api/v1/system/current',
      {
        cache: 'no-store'
      }
    );

    if (!r.ok) {
      throw new Error(`HTTP ${r.status}`);
    }

    const liveSnapshot = await r.json();

    snapshot = liveSnapshot;
    hasLiveSnapshot = true;

    $('apiState').textContent =
      'Railway PostgreSQL Live';

    $('apiDot').style.background =
      '#58e8ff';

  } catch (e) {
    console.warn(
      'Power Grid API refresh failed:',
      e
    );

    if (!hasLiveSnapshot) {
      snapshot = demo;

      $('apiState').textContent =
        'Demo Telemetry';

      $('apiDot').style.background =
        '#ffc75a';

    } else {
      // Keep the last known-good Railway snapshot.
      $('apiState').textContent =
        'Railway Live · Refresh Delayed';

      $('apiDot').style.background =
        '#ffc75a';
    }

  } finally {
    fetchInProgress = false;
  }

  render();
}
function render() { let facilities = snapshot.facilities, assets = snapshot.assets; if (scope !== 'CAMPUS') { facilities = facilities.filter(f => f.code === scope); assets = assets.filter(a => a.facility === scope) } $('load').textContent = (scope === 'CAMPUS' ? snapshot.campus.real_power_kw : facilities.reduce((s, f) => s + f.real_power_kw, 0)).toFixed(1) + ' kW'; $('pf').textContent = snapshot.campus.power_factor.toFixed(3); $('kvar').textContent = snapshot.campus.reactive_power_kvar.toFixed(1) + ' kvar'; $('alerts').textContent = snapshot.campus.open_alerts; $('timestamp').textContent = new Date(snapshot.timestamp).toLocaleTimeString(); $('assets').innerHTML = assets.map(a => `<div class="asset" data-code="${a.code}"><div><b>${a.name}</b><small>${a.code} · ${a.area}</small></div><div><strong>${a.real_power_kw.toFixed(1)} kW</strong><small>${a.current_a.toFixed(1)} A · PF ${a.power_factor}</small></div></div>`).join('') || '<p>No live assets in scope.</p>'; $('alertList').innerHTML = snapshot.alerts.map(a => `<div class="alert ${a.severity.toLowerCase()}"><strong>${a.title}</strong><small>${a.message}</small></div>`).join('') || '<p>No active alerts.</p>'; document.querySelectorAll('.asset').forEach(el => el.onclick = () => openAsset(el.dataset.code)); drawChart(facilities); updateScene(scope) }
function openAsset(code) { selected = snapshot.assets.find(a => a.code === code); if (!selected) return; $('assetName').textContent = selected.name; $('assetMetrics').innerHTML = Object.entries({ 'Asset code': selected.code, 'Facility': selected.facility, 'Operating state': selected.operating_state, 'Real power': selected.real_power_kw + ' kW', 'Voltage': selected.voltage_v + ' V', 'Current': selected.current_a + ' A', 'Power factor': selected.power_factor, 'Frequency': selected.frequency_hz + ' Hz', 'Breaker utilization': selected.breaker_utilization_pct + '%', 'Temperature': selected.temperature_c + ' °C', 'Health': selected.health_pct + '%', 'Fault': selected.fault_code || 'None' }).map(([k, v]) => `<div class="metric"><span>${k}</span><b>${v}</b></div>`).join(''); $('drawer').classList.add('open') }
$('closeDrawer').onclick = () => $('drawer').classList.remove('open'); $('diagnose').onclick = async () => {
  if (!selected) return;

  try {
    const r = await fetch(
      cfg.apiBaseUrl + '/api/v1/diagnostics',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          asset_code: selected.code,
          diagnostic_type: 'electrical-health'
        })
      }
    );

    if (!r.ok) {
      throw new Error(`HTTP ${r.status}`);
    }

    const d = await r.json();

    // Preserve the production diagnostic response locally.
    localStorage.setItem(
      'eesRcDiagnostic',
      JSON.stringify(d)
    );

    // Build a packet the RC Controls digital twin already understands.
    const rcPacket = {
      assets: [
        {
          id: selected.asset_id,
          name: selected.name,
          scenario: 'Power Grid diagnostic request',
          health: selected.health_pct,
          fault: selected.fault_code || 'none',
          voltage: selected.voltage_v,
          loadWatts: (selected.real_power_kw || 0) * 1000,
          lineVoltage: selected.voltage_v,
          powerFactor: selected.power_factor,
          temperatureC: selected.temperature_c || 0,
          faultCode: selected.fault_code || 'none'
        }
      ],
      scope: 'RC'
    };

    const batchId = `power-grid-${Date.now()}`;

    sessionStorage.setItem(
      `ees.rc.batch.${batchId}`,
      JSON.stringify(rcPacket)
    );

    localStorage.setItem(
      `ees.rc.batch.${batchId}`,
      JSON.stringify(rcPacket)
    );

    const eventId =
      d?.rc_controls?.control_event_id || '';

    console.log(
      'RC Controls diagnostic forwarded:',
      eventId
    );

    // Redirect into the live RC Controls digital twin.
    window.location.href =
      'https://jd-dev-king.github.io/EES-RC-Controls/' +
      `?source=power-grid` +
      `&scope=RC` +
      `&batch=${encodeURIComponent(batchId)}` +
      `&assetIndex=0` +
      `&return=${encodeURIComponent(location.href)}`;

  } catch (error) {
    console.error(
      'RC Controls diagnostic handoff failed:',
      error
    );

    alert(
      'Unable to send diagnostic request to EES RC Controls.'
    );
  }
};
document.querySelectorAll('nav button').forEach(b => b.onclick = () => { document.querySelectorAll('nav button').forEach(x => x.classList.remove('active')); b.classList.add('active'); scope = b.dataset.scope; $('scopeTitle').textContent = b.textContent; render() }); $('simulate').onclick = async () => { try { await fetch(cfg.apiBaseUrl + '/api/v1/simulation/tick', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-API-Key': 'change-me' }, body: JSON.stringify({ minutes: 1, fault_probability: .01 }) }); await fetchSnapshot() } catch { demo.facilities.forEach(f => f.real_power_kw *= .96 + Math.random() * .08); demo.timestamp = new Date().toISOString(); render() } };
function drawChart(data) { const c = $('chart'), ctx = c.getContext('2d'), w = c.width = c.clientWidth * devicePixelRatio, h = c.height = 210 * devicePixelRatio; ctx.clearRect(0, 0, w, h); const max = Math.max(...data.map(x => x.real_power_kw), 1); data.forEach((d, i) => { const bw = w / (data.length * 1.7), x = (i + .35) * w / data.length, bh = d.real_power_kw / max * (h - 55); ctx.fillStyle = '#193b58'; ctx.fillRect(x, h - 30 - bh, bw, bh); ctx.fillStyle = '#58e8ff'; ctx.fillRect(x, h - 30 - bh, bw, 4); ctx.fillStyle = '#c9e8f5'; ctx.font = `${11 * devicePixelRatio}px sans-serif`; ctx.fillText(d.code, x, h - 10); ctx.fillText(d.real_power_kw.toFixed(0) + ' kW', x, h - 37 - bh) }) }
let scene, camera, renderer, controls, buildings = []; function init3d() { const host = $('scene'); scene = new THREE.Scene(); scene.fog = new THREE.Fog(0x050914, 40, 100); camera = new THREE.PerspectiveCamera(45, host.clientWidth / host.clientHeight, .1, 200); camera.position.set(28, 28, 34); renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(host.clientWidth, host.clientHeight); host.appendChild(renderer.domElement); controls = new OrbitControls(camera, renderer.domElement); controls.target.set(0, 0, 0); controls.enableDamping = true; scene.add(new THREE.HemisphereLight(0x78cfff, 0x07101d, 2.3)); const dl = new THREE.DirectionalLight(0xffffff, 2); dl.position.set(15, 30, 12); scene.add(dl); const ground = new THREE.Mesh(new THREE.BoxGeometry(46, .5, 34), new THREE.MeshStandardMaterial({ color: 0x0a1723, metalness: .5, roughness: .7 })); ground.position.y = -.3; scene.add(ground); const defs = [['PHARMA', -11, 0, 0, 12, 5, 13, 0x1b6381], ['LOGISTICS', 9, 0, -5, 15, 4, 9, 0x365981], ['UTILITIES', 8, 0, 9, 11, 6, 7, 0x6e5522], ['EXEC', -9, 0, 11, 9, 5, 6, 0x1c7b6f]]; defs.forEach(d => { const mesh = new THREE.Mesh(new THREE.BoxGeometry(d[4], d[5], d[6]), new THREE.MeshStandardMaterial({ color: d[7], metalness: .55, roughness: .35, emissive: d[7], emissiveIntensity: .12 })); mesh.position.set(d[1], d[5] / 2, d[3]); mesh.userData.code = d[0]; scene.add(mesh); buildings.push(mesh) }); for (let i = 0; i < 7; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(.25, .25, 6), new THREE.MeshBasicMaterial({ color: 0x58e8ff })); p.position.set(-3 + i, 0.4, -7 + i * .8); p.rotation.y = .6; scene.add(p) }; renderer.domElement.addEventListener('click', e => { const r = renderer.domElement.getBoundingClientRect(), m = new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), ray = new THREE.Raycaster(); ray.setFromCamera(m, camera); const hit = ray.intersectObjects(buildings)[0]; if (hit) { const b = document.querySelector(`nav button[data-scope="${hit.object.userData.code}"]`); b?.click() } }); new ResizeObserver(() => { if (host.clientWidth && host.clientHeight) { camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(host.clientWidth, host.clientHeight) } }).observe(host); (function loop() { requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera) })() }
function updateScene(s) { buildings.forEach(b => { b.material.emissiveIntensity = s === 'CAMPUS' || b.userData.code === s ? .35 : .05 }) }
init3d(); fetchSnapshot(); setInterval(fetchSnapshot, cfg.refreshMs);
