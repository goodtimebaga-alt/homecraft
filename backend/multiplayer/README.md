# Anonymous multiplayer

An optional, in-memory WebSocket presence service for a small Homecraft world.
It synchronizes position, heading, basic movement, and generated guest labels.
It does not synchronize pets, weather, cards, chat, or specialized poses, and
it is not an authoritative game server or a complete anti-cheat system.

## Enable the client

The starter world integrates `world/multiplayer.js` through its `setup()` hook.
Set `multiplayer: { enabled: true }` in `home.config.js` to opt in. For a custom
world, integrate `createMultiplayer({ stage, player, avatar })` into its
existing `setup()` and call its `update(dt)` alongside existing updates.
The client connects to `/multiplayer/` on the current origin. If unavailable,
the site remains playable in solo mode. Hidden pages disconnect and reconnect
when visible again.

## Run the server

Use Python 3.10+ and install `requirements.txt`, or build the included Docker
image. Supply `ORIGIN` as the **exact** public site origin including scheme,
for example `https://example.com` (replace with your own). There is no default
origin; the process will refuse to start without it. Configure an HTTPS reverse
proxy for `/multiplayer/`, WebSocket upgrades, and timeouts longer than the
20-second ping interval. The example Compose file binds the backend only to
loopback; do not expose the backend directly to the internet. For example:

```sh
cd backend/multiplayer
export MULTIPLAYER_ORIGIN=https://example.com
docker compose -f compose.example.yaml up -d --build
```

The reverse proxy must overwrite `X-Visitor-IP` with a verified client IP and
must never pass through an arbitrary client-supplied value. The server trusts
this header because the backend is assumed to be reachable only by the trusted
proxy. For a directly connected Nginx proxy, use `$remote_addr`; behind a CDN,
configure trusted proxy ranges and real-IP handling before relying on IP-based
limits. Do not blindly trust forwarded headers, and check proxy access-log and
CDN logging policies for your privacy requirements. Configure TLS/WSS and
origin validation; do not allow untrusted clients to reach the backend directly.

Default limits: 8 connections per room, 6 concurrent connections per visitor
IP, 25 connection attempts per IP per 30 seconds, 15 messages per second,
512-byte maximum message size, and a 20-second WebSocket ping. MAX_PLAYERS is
configurable from 1 through 32; no concurrency capacity is guaranteed. The
initial coordinates accepted by the server are bounded to a small world; adjust
and test these bounds for your own layout. IDs and state are ephemeral.

Test the reverse-proxy origin checks, reconnects, room limit, phone performance,
and existing site behavior in your own deployment before enabling this feature.
Each visible remote avatar adds rendering work and may exceed the project's
normal draw-call budget. The server is designed for small trusted social spaces,
not for competitive gameplay or strong protection against all abuse.
