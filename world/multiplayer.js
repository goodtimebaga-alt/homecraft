import * as THREE from 'three';
import { createAvatar } from '@engine/world/avatar.js';

// Anonymous room presence. This module is optional: failures never block play.
export function createMultiplayer({ stage, player, avatar }) {
  const remotes = new Map();
  const badge = document.createElement('div');
  badge.setAttribute('role', 'status');
  badge.style.cssText = 'position:fixed;top:58px;right:12px;z-index:20;pointer-events:none;padding:5px 8px;background:rgba(38,31,24,.82);border:2px solid #94734b;color:#f4e5c5;font:12px monospace;text-shadow:1px 1px #21180f';
  document.body.appendChild(badge);
  const label = (zh, en) => { badge.textContent = document.documentElement.lang.startsWith('zh') ? zh : en; };
  let socket = null, retryTimer = 0, retry = 0, sendClock = 1, stopped = false, full = false;
  let myId = null, count = 0;
  function status() {
    if (full) label('多人房间已满 · 单人游览', 'Room full · solo');
    else if (myId) label(`在线游客 ${count}`, `Visitors ${count}`);
    else label('多人连接中 · 单人游览', 'Connecting · solo');
  }
  function createName(slot) {
    const c = document.createElement('canvas'); c.width = 128; c.height = 32;
    const ctx = c.getContext('2d');
    ctx.fillStyle = 'rgba(35,28,21,.85)'; ctx.fillRect(0, 1, 128, 30);
    ctx.strokeStyle = '#c9aa75'; ctx.strokeRect(1, 2, 126, 28);
    ctx.font = 'bold 18px sans-serif'; ctx.fillStyle = '#f5e6c2';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(document.documentElement.lang.startsWith('zh') ? `游客 ${slot}` : `Guest ${slot}`, 64, 17);
    const tex = new THREE.CanvasTexture(c); tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.NearestFilter;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    sprite.scale.set(1.2, .3, 1); sprite.position.y = 2.15;
    return sprite;
  }
  function remove(id) {
    const r = remotes.get(id); if (!r) return;
    stage.scene.remove(r.body.root, r.body.blob);
    const geometries = new Set(), materials = new Set(), textures = new Set();
    for (const obj of [r.body.root, r.body.blob]) obj.traverse(child => {
      if (child.geometry) geometries.add(child.geometry);
      for (const m of (Array.isArray(child.material) ? child.material : [child.material])) if (m) {
        materials.add(m); if (m.map) textures.add(m.map);
      }
    });
    for (const t of textures) t.dispose(); for (const m of materials) m.dispose(); for (const g of geometries) g.dispose();
    remotes.delete(id);
  }
  function clear() { for (const id of [...remotes.keys()]) remove(id); }
  function apply(data) {
    if (!data || data.id === myId || typeof data.id !== 'string' || !Number.isInteger(data.slot)) return;
    if (![data.x, data.y, data.z, data.heading].every(Number.isFinite)) return;
    let r = remotes.get(data.id);
    if (!r) {
      const body = createAvatar('');
      body.root.add(createName(data.slot));
      body.root.position.set(data.x, data.y, data.z); body.root.rotation.y = data.heading;
      body.blob.visible = false; stage.scene.add(body.root, body.blob);
      r = { body, x:data.x, y:data.y, z:data.z, heading:data.heading, moving:false };
      remotes.set(data.id, r);
    }
    r.x=data.x; r.y=data.y; r.z=data.z; r.heading=data.heading; r.moving=!!data.moving;
  }
  function onMessage(event) {
    let data; try { data=JSON.parse(event.data); } catch { return; }
    if (data.type === 'full') { full=true; status(); return; }
    if (data.type === 'welcome') {
      myId=data.id; count=data.count; retry=0; full=false; clear();
      for (const p of data.players || []) apply(p); status(); sendClock=1;
    } else if (data.type === 'join' || data.type === 'move') apply(data);
    else if (data.type === 'leave') { remove(data.id); count=data.count; status(); }
    else if (data.type === 'count') { count=data.count; status(); }
  }
  function connect() {
    if (stopped || document.hidden || socket) return;
    full=false; status();
    try { socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/multiplayer/`); }
    catch { schedule(); return; }
    const current=socket;
    current.onmessage=onMessage;
    current.onclose=() => {
      if (socket !== current) return;
      socket=null; myId=null; count=0; clear(); status(); schedule();
    };
    current.onerror=() => {};
  }
  function schedule() {
    if (stopped || document.hidden || retryTimer) return;
    const delay=full ? 30000 : Math.min(30000, 1000 * 2 ** Math.min(retry++, 5)) + Math.random()*500;
    retryTimer=setTimeout(() => { retryTimer=0; connect(); }, delay);
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { clearTimeout(retryTimer); retryTimer=0; if (socket) socket.close(1000, 'hidden'); }
    else if (!socket) connect();
  });
  addEventListener('pagehide', () => { stopped=true; clearTimeout(retryTimer); if (socket) socket.close(1000, 'pagehide'); clear(); });
  addEventListener('pageshow', event => { if (event.persisted) { stopped=false; if (!socket) connect(); } });
  status(); connect();
  return { update(dt) {
    sendClock += dt;
    if (myId && socket?.readyState === WebSocket.OPEN && sendClock >= .125) {
      sendClock=0;
      const pos=avatar.root.position;
      const heading=Math.atan2(Math.sin(player.heading), Math.cos(player.heading));
      socket.send(JSON.stringify({type:'move',x:pos.x,y:pos.y,z:pos.z,heading,moving:!!player.moving}));
    }
    const k=1-Math.exp(-Math.min(dt,.1)*12);
    for (const r of remotes.values()) {
      const b=r.body, pos=b.root.position;
      pos.x+=(r.x-pos.x)*k; pos.y+=(r.y-pos.y)*k; pos.z+=(r.z-pos.z)*k;
      const angle=r.heading-b.root.rotation.y;
      b.root.rotation.y+=Math.atan2(Math.sin(angle),Math.cos(angle))*k;
      b.update(Math.min(dt,.1), {speed:r.moving ? .7 : 0, fly:-1});
    }
  }};
}
