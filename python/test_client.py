"""
自动化测试客户端：用于验证 A ↔ B 聊天流程
用法：python test_client.py --name A --role initiator --target B
"""
import argparse
import asyncio
import json

async def send_json(writer, obj):
    writer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode())
    await writer.drain()

async def read_loop(r, queue):
    while True:
        line = await r.readline()
        if not line:
            await queue.put({"type":"disconnect"})
            break
        try:
            msg = json.loads(line.decode())
        except Exception:
            continue
        await queue.put(msg)

async def initiator_flow(name, target, reader, writer, queue):
    await asyncio.sleep(0.2)
    await send_json(writer, {"type":"list"})
    await asyncio.sleep(0.2)
    print(f"[{name}] 邀请 {target}")
    await send_json(writer, {"type":"invite", "to": target})
    while True:
        msg = await queue.get()
        print(f"[{name}] 收到: {msg}")
        if msg.get('type') == 'accepted' and msg.get('with') == target:
            # send a message
            await asyncio.sleep(0.2)
            await send_json(writer, {"type":"message", "to": target, "text": f"Hello from {name}"})
        if msg.get('type') == 'message' and msg.get('from') == target:
            # reply then leave
            await asyncio.sleep(0.2)
            await send_json(writer, {"type":"message", "to": target, "text": f"Got your message, {target}. Bye"})
            await asyncio.sleep(0.2)
            await send_json(writer, {"type":"leave"})
            return
        if msg.get('type') == 'peer_disconnected' or msg.get('type') == 'disconnect':
            return

async def responder_flow(name, reader, writer, queue):
    while True:
        msg = await queue.get()
        print(f"[{name}] 收到: {msg}")
        if msg.get('type') == 'invite':
            frm = msg.get('from')
            print(f"[{name}] 接受邀请来自 {frm}")
            await send_json(writer, {"type":"accept", "from": frm})
        if msg.get('type') == 'message':
            # reply
            frm = msg.get('from')
            await asyncio.sleep(0.2)
            await send_json(writer, {"type":"message", "to": frm, "text": f"Hi {frm}, this is {name}"})
        if msg.get('type') == 'left' or msg.get('type') == 'peer_disconnected' or msg.get('type') == 'disconnect':
            return

async def main(host, port, name, role, target=None):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        print(f"[{name}] connected", flush=True)
        queue = asyncio.Queue()
        # register
        await send_json(writer, {"type":"register", "username": name})
        print(f"[{name}] register sent", flush=True)
        # start reader task
        asyncio.create_task(read_loop(reader, queue))
        if role == 'initiator':
            await initiator_flow(name, target, reader, writer, queue)
        else:
            await responder_flow(name, reader, writer, queue)
    except Exception as e:
        print(f"[{name}] EXCEPTION: {e}", flush=True)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8888)
    parser.add_argument('--name', required=True)
    parser.add_argument('--role', choices=['initiator','responder'], required=True)
    parser.add_argument('--target')
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port, args.name, args.role, args.target))
