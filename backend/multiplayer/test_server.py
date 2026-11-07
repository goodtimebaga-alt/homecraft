"""Protocol checks for the optional multiplayer service (Python 3.10+)."""
import asyncio
import json
import os
import unittest

os.environ.setdefault('ORIGIN', 'http://test.local')
import server
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, InvalidStatus

MOVE = {'type': 'move', 'x': 1, 'y': 0, 'z': 2, 'heading': 0, 'moving': False}


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server.peers.clear(); server.counts.clear(); server.attempts.clear()
        self.listener = await serve(server.handle, '127.0.0.1', 0, origins=[server.ORIGIN],
                                    max_size=512, max_queue=4, compression=None)
        self.url = 'ws://127.0.0.1:%s/multiplayer/' % self.listener.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        self.listener.close()
        await self.listener.wait_closed()

    async def connect(self, origin=None):
        return await connect(self.url, origin=origin or server.ORIGIN)

    async def receive(self, ws):
        return json.loads(await asyncio.wait_for(ws.recv(), 2))

    async def test_join_snapshot_movement_and_leave(self):
        async with await self.connect() as first:
            welcome = await self.receive(first)
            await first.send(json.dumps(MOVE))
            await asyncio.sleep(.05)
            async with await self.connect() as second:
                initial = await self.receive(second)
                self.assertEqual(initial['players'][0]['id'], welcome['id'])
                self.assertEqual((await self.receive(first))['type'], 'count')
                await second.send(json.dumps({**MOVE, 'x': 4, 'moving': True}))
                joined = await self.receive(first)
                self.assertEqual((joined['type'], joined['x'], joined['moving']), ('join', 4, True))
                await second.send(json.dumps({**MOVE, 'x': 5}))
                moved = await self.receive(first)
                self.assertEqual((moved['type'], moved['x']), ('move', 5))
            self.assertEqual((await self.receive(first))['type'], 'leave')

    async def test_wrong_origin_rejected(self):
        with self.assertRaises(InvalidStatus):
            await self.connect('https://wrong.example')

    async def test_impersonation_and_invalid_coordinate_rejected(self):
        for data in ({**MOVE, 'id': 'other'}, {**MOVE, 'x': 9999}):
            async with await self.connect() as ws:
                await self.receive(ws)
                await ws.send(json.dumps(data))
                with self.assertRaises(ConnectionClosed) as result:
                    await ws.recv()
                self.assertEqual(result.exception.rcvd.code, 1008)

    async def test_message_size_limit(self):
        async with await self.connect() as ws:
            await self.receive(ws)
            await ws.send('x' * 600)
            with self.assertRaises(ConnectionClosed) as result:
                await ws.recv()
            self.assertEqual(result.exception.rcvd.code, 1009)

    async def test_rate_limit(self):
        async with await self.connect() as ws:
            await self.receive(ws)
            for _ in range(16):
                await ws.send(json.dumps(MOVE))
            with self.assertRaises(ConnectionClosed) as result:
                await ws.recv()
            self.assertEqual(result.exception.rcvd.code, 1008)

    async def test_room_full_and_reopens(self):
        clients = []
        try:
            for index in range(server.MAX_PLAYERS):
                # Direct loopback access is limited to this test fixture.
                ws = await connect(self.url, origin=server.ORIGIN,
                    additional_headers={'X-Visitor-IP': f'192.0.2.{index + 1}'})
                self.assertEqual((await self.receive(ws))['type'], 'welcome')
                clients.append(ws)
            async with await connect(self.url, origin=server.ORIGIN,
                    additional_headers={'X-Visitor-IP': '192.0.2.100'}) as extra:
                self.assertEqual((await self.receive(extra))['type'], 'full')
        finally:
            await asyncio.gather(*(ws.close() for ws in clients))
        async with await self.connect() as ws:
            self.assertEqual((await self.receive(ws))['type'], 'welcome')


if __name__ == '__main__':
    unittest.main()
