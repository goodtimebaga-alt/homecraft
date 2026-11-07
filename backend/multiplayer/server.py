import asyncio
import ipaddress
import json
import logging
import math
import os
import secrets
import time
from collections import defaultdict, deque

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

# Do not write handshake tracebacks or untrusted Origin values to logs.
logging.getLogger('websockets.server').setLevel(logging.CRITICAL)

HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', '13033'))
ORIGIN = os.environ['ORIGIN']
MAX_PLAYERS = max(1, min(32, int(os.environ.get('MAX_PLAYERS', '8'))))
MAX_PER_IP = 6
peers = {}
counts = defaultdict(int)
attempts = defaultdict(deque)


def payload(obj):
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=True)


def broadcast(obj, except_id=None):
    msg = payload(obj)
    for key, peer in list(peers.items()):
        if key != except_id:
            if peer['pending'] >= 16:
                asyncio.create_task(peer['ws'].close(1013, 'slow connection'))
            else:
                peer['pending'] += 1
                asyncio.create_task(send(peer, msg))


async def send(peer, msg):
    try:
        await peer['ws'].send(msg)
    except ConnectionClosed:
        pass
    finally:
        peer['pending'] -= 1


def remote_ip(ws):
    raw = ws.request.headers.get('X-Visitor-IP', '')
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return str(ws.remote_address[0])


def allowed_attempt(ip):
    now = time.monotonic()
    if ip not in attempts and len(attempts) >= 2048:
        for key, history in list(attempts.items()):
            if not history or now - history[-1] > 30:
                attempts.pop(key, None)
    if ip not in attempts and len(attempts) >= 8192:
        return False
    q = attempts[ip]
    while q and now - q[0] > 30:
        q.popleft()
    if len(q) >= 25:
        return False
    q.append(now)
    if len(attempts) > 2048:
        for k, v in list(attempts.items()):
            if not v or now - v[-1] > 30:
                attempts.pop(k, None)
    return True


def validate(data):
    if not isinstance(data, dict) or set(data) != {'type', 'x', 'y', 'z', 'heading', 'moving'} or data['type'] != 'move':
        return None
    for key, lo, hi in [('x', -100, 100), ('y', -20, 120), ('z', -120, 100), ('heading', -7, 7)]:
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            return None
    if type(data['moving']) is not bool:
        return None
    return {k: round(data[k], 3) if k != 'moving' else data[k] for k in ('x','y','z','heading','moving')}


async def handle(ws):
    if ws.request.path != '/multiplayer/':
        await ws.close(1008, 'invalid path'); return
    ip = remote_ip(ws)
    if not allowed_attempt(ip) or counts[ip] >= MAX_PER_IP:
        await ws.close(1008, 'connection limit'); return
    if len(peers) >= MAX_PLAYERS:
        await ws.send(payload({'type': 'full'})); await ws.close(1000, 'room full'); return
    ident = secrets.token_hex(8)
    used = {p['slot'] for p in peers.values()}
    slot = next(i for i in range(1, MAX_PLAYERS + 1) if i not in used)
    peer = {'ws': ws, 'slot': slot, 'state': None, 'pending': 0}
    peers[ident] = peer; counts[ip] += 1
    try:
        initial = [{'id': k, 'slot': p['slot'], **p['state']} for k, p in peers.items() if k != ident and p['state'] is not None]
        await ws.send(payload({'type': 'welcome', 'id': ident, 'slot': slot, 'players': initial, 'count': len(peers)}))
        broadcast({'type': 'count', 'count': len(peers)}, ident)
        recent = deque()
        async for raw in ws:
            now = time.monotonic()
            while recent and now - recent[0] > 1:
                recent.popleft()
            recent.append(now)
            if len(recent) > 15:
                await ws.close(1008, 'rate limit'); break
            try:
                state = validate(json.loads(raw)) if isinstance(raw, str) else None
            except (ValueError, TypeError, RecursionError):
                state = None
            if state is None:
                await ws.close(1008, 'invalid message'); break
            is_new = peer['state'] is None
            peer['state'] = state
            broadcast({'type': 'join' if is_new else 'move', 'id': ident, 'slot': slot, **state}, ident)
    except ConnectionClosed:
        pass
    finally:
        peers.pop(ident, None)
        counts[ip] -= 1
        if counts[ip] <= 0:
            counts.pop(ip, None)
        broadcast({'type': 'leave', 'id': ident, 'count': len(peers)})


async def main():
    async with serve(handle, HOST, PORT, origins=[ORIGIN], max_size=512, max_queue=4,
                     compression=None, ping_interval=20, ping_timeout=20, open_timeout=5):
        print(f'Multiplayer server listening on {PORT}', flush=True)
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
