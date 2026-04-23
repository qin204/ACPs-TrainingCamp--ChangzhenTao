"""
简单异步聊天中转服务器（JSON over TCP）
功能：注册、列在线用户、邀请、接受、消息转发、离开
使用：python server.py [--host HOST] [--port PORT]
"""

import asyncio
import json
import argparse
from typing import Dict, Tuple

USERS: Dict[str, asyncio.StreamWriter] = {}
SESSIONS: Dict[str, str] = {}  # username -> peer username

async def send_json(writer: asyncio.StreamWriter, obj: dict):
    data = json.dumps(obj, ensure_ascii=False) + "\n"
    writer.write(data.encode())
    await writer.drain()

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info('peername')
    username = None
    try:
        # first message must be register
        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            return
        try:
            msg = json.loads(line.decode())
        except Exception:
            await send_json(writer, {"type": "error", "reason": "invalid_json"})
            writer.close()
            await writer.wait_closed()
            return
        if msg.get('type') != 'register' or 'username' not in msg:
            await send_json(writer, {"type": "error", "reason": "first_message_must_register"})
            writer.close()
            await writer.wait_closed()
            return
        username = msg['username']
        if username in USERS:
            await send_json(writer, {"type": "register", "status": "error", "reason": "username_taken"})
            writer.close()
            await writer.wait_closed()
            return
        USERS[username] = writer
        print(f"[CONNECT] {username} from {peer}")
        await send_json(writer, {"type": "register", "status": "ok"})

        # main loop
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode())
            except Exception:
                await send_json(writer, {"type": "error", "reason": "invalid_json"})
                continue
            mtype = msg.get('type')
            if mtype == 'list':
                users = [u for u in USERS.keys() if u != username]
                await send_json(writer, {"type": "list", "users": users})
            elif mtype == 'invite':
                to = msg.get('to')
                if not to or to not in USERS:
                    await send_json(writer, {"type": "invite", "status": "error", "reason": "user_not_online"})
                    continue
                if username in SESSIONS or to in SESSIONS:
                    await send_json(writer, {"type": "invite", "status": "error", "reason": "either_in_session"})
                    continue
                # forward invite
                await send_json(USERS[to], {"type": "invite", "from": username})
                await send_json(writer, {"type": "invite", "status": "sent"})
            elif mtype == 'accept':
                frm = msg.get('from')
                if not frm or frm not in USERS:
                    await send_json(writer, {"type": "accept", "status": "error", "reason": "user_not_online"})
                    continue
                if username in SESSIONS or frm in SESSIONS:
                    await send_json(writer, {"type": "accept", "status": "error", "reason": "either_in_session"})
                    continue
                # create session
                SESSIONS[username] = frm
                SESSIONS[frm] = username
                await send_json(USERS[frm], {"type": "accepted", "with": username})
                await send_json(writer, {"type": "accepted", "with": frm})
            elif mtype == 'message':
                to = msg.get('to')
                text = msg.get('text')
                if not to or not text:
                    await send_json(writer, {"type": "message", "status": "error", "reason": "invalid_message"})
                    continue
                # ensure session exists between them
                if SESSIONS.get(username) != to:
                    await send_json(writer, {"type": "message", "status": "error", "reason": "not_in_session"})
                    continue
                # forward
                if to in USERS:
                    await send_json(USERS[to], {"type": "message", "from": username, "text": text})
                    await send_json(writer, {"type": "message", "status": "sent"})
                else:
                    await send_json(writer, {"type": "message", "status": "error", "reason": "user_offline"})
            elif mtype == 'leave':
                with_user = msg.get('with')
                peer_user = SESSIONS.get(username)
                if peer_user:
                    # remove both
                    SESSIONS.pop(username, None)
                    SESSIONS.pop(peer_user, None)
                    if peer_user in USERS:
                        await send_json(USERS[peer_user], {"type": "left", "from": username})
                    await send_json(writer, {"type": "left", "status": "ok"})
                else:
                    await send_json(writer, {"type": "leave", "status": "error", "reason": "not_in_session"})
            else:
                await send_json(writer, {"type": "error", "reason": "unknown_type"})
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        # cleanup
        if username:
            print(f"[DISCONNECT] {username}")
            USERS.pop(username, None)
            peer_user = SESSIONS.pop(username, None)
            if peer_user:
                SESSIONS.pop(peer_user, None)
                if peer_user in USERS:
                    try:
                        await send_json(USERS[peer_user], {"type": "peer_disconnected", "user": username})
                    except Exception:
                        pass
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def main(host: str, port: int):
    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8888)
    args = parser.parse_args()
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print("Server shutting down")
