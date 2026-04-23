"""
并发会话测试：同时运行 A-B 和 C-D 两组一对一聊天，验证服务器能正确处理多组并发会话。
用法：python test_multi_pairs.py
"""
import asyncio
import json
from server import handle_client

async def send_json(writer, obj):
    writer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode())
    await writer.drain()

async def read_loop(reader, queue):
    while True:
        line = await reader.readline()
        if not line:
            await queue.put({"type": "disconnect"})
            break
        try:
            msg = json.loads(line.decode())
        except Exception:
            continue
        await queue.put(msg)

async def initiator(name, target, host, port):
    reader, writer = await asyncio.open_connection(host, port)
    q = asyncio.Queue()
    await send_json(writer, {"type": "register", "username": name})
    asyncio.create_task(read_loop(reader, q))
    await asyncio.sleep(0.1)
    await send_json(writer, {"type": "list"})
    await asyncio.sleep(0.1)
    print(f"[{name}] 邀请 {target}")
    await send_json(writer, {"type": "invite", "to": target})
    accepted = False
    while True:
        msg = await q.get()
        print(f"[{name}] 收到: {msg}")
        if msg.get('type') == 'accepted' and msg.get('with') == target:
            accepted = True
            await asyncio.sleep(0.1)
            await send_json(writer, {"type": "message", "to": target, "text": f"Hello from {name}"})
        if msg.get('type') == 'message' and msg.get('from') == target:
            await asyncio.sleep(0.1)
            await send_json(writer, {"type": "message", "to": target, "text": f"Got your message, {target}. Bye"})
            await asyncio.sleep(0.1)
            await send_json(writer, {"type": "leave"})
            break
        if msg.get('type') in ('peer_disconnected', 'disconnect'):
            break
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    return accepted

async def responder(name, host, port):
    reader, writer = await asyncio.open_connection(host, port)
    q = asyncio.Queue()
    await send_json(writer, {"type": "register", "username": name})
    asyncio.create_task(read_loop(reader, q))
    accepted = False
    while True:
        msg = await q.get()
        print(f"[{name}] 收到: {msg}")
        if msg.get('type') == 'invite':
            frm = msg.get('from')
            print(f"[{name}] 接受邀请来自 {frm}")
            await send_json(writer, {"type": "accept", "from": frm})
            accepted = True
        if msg.get('type') == 'message':
            frm = msg.get('from')
            await asyncio.sleep(0.1)
            await send_json(writer, {"type": "message", "to": frm, "text": f"Hi {frm}, this is {name}"})
        if msg.get('type') in ('left', 'peer_disconnected', 'disconnect'):
            break
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    return accepted

async def run_test():
    host = '127.0.0.1'
    # 启动临时 server，端口 0 表示自动分配空闲端口
    server = await asyncio.start_server(handle_client, host, 0)
    port = server.sockets[0].getsockname()[1]
    print(f"测试服务器运行在 {host}:{port}")

    async with server:
        # 并行运行两组会话：A->B 与 C->D
        tasks = [
            asyncio.create_task(initiator('A', 'B', host, port)),
            asyncio.create_task(responder('B', host, port)),
            asyncio.create_task(initiator('C', 'D', host, port)),
            asyncio.create_task(responder('D', host, port)),
        ]
        done, pending = await asyncio.wait(tasks, timeout=20)
        for t in pending:
            t.cancel()
        results = [t.result() for t in done if not t.cancelled()]
        print('结果:', results)
        # 简单断言：两个 responder 应该都接受过邀请 -> 至少两个 True
        accepted_count = sum(1 for r in results if r)
        if accepted_count >= 2:
            print('OK: 同时支持多组一对一会话')
            return 0
        else:
            print('FAIL: 未同时建立预期的会话')
            return 1

if __name__ == '__main__':
    exit_code = asyncio.run(run_test())
    raise SystemExit(exit_code)
