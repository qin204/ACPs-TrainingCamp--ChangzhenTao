"""
简单命令行聊天客户端（配合 server.py）
使用：python client.py [--host HOST] [--port PORT]
命令：
  /list                       列出在线用户
  /invite <user>              向用户发起邀请
  /accept <user>              接受来自用户的邀请
  /leave                      结束当前会话
  /msg <user> <message>       向 user 发送消息（必须处于会话中）
  /quit                       退出客户端

消息格式使用 JSON 行（每行一个 JSON 对象）
"""

import asyncio
import json
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor

async def send_json(writer: asyncio.StreamWriter, obj: dict):
    data = json.dumps(obj, ensure_ascii=False) + "\n"
    writer.write(data.encode())
    await writer.drain()

async def reader_task(reader: asyncio.StreamReader):
    while True:
        line = await reader.readline()
        if not line:
            print("[INFO] 服务器连接已关闭")
            break
        try:
            msg = json.loads(line.decode())
        except Exception:
            print("[WARN] 收到无法解析的消息: ", line)
            continue
        mtype = msg.get('type')
        if mtype == 'list':
            print("在线用户:", ', '.join(msg.get('users', [])))
        elif mtype == 'invite':
            print(f"[邀请] 来自 {msg.get('from')}: /accept {msg.get('from')}")
        elif mtype == 'accepted':
            print(f"[会话已建立] 与 {msg.get('with')} 可以聊天了。")
        elif mtype == 'message':
            print(f"[{msg.get('from')}] {msg.get('text')}")
        elif mtype == 'left':
            if msg.get('status') == 'ok':
                print("[会话结束] 你已退出会话")
            else:
                print(f"[通知] {msg}")
        elif mtype == 'peer_disconnected':
            print(f"[通知] 对方 {msg.get('user')} 已断开")
        elif mtype == 'register':
            if msg.get('status') == 'ok':
                print("[注册] 成功登录")
            else:
                print(f"[注册] 失败: {msg}")
        else:
            # generic
            print(f"[SERVER] {msg}")

async def input_loop(writer: asyncio.StreamWriter):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(1)
    while True:
        user_input = await loop.run_in_executor(executor, sys.stdin.readline)
        if not user_input:
            continue
        user_input = user_input.strip()
        if user_input == '':
            continue
        if user_input.startswith('/'):
            parts = user_input.split(' ', 2)
            cmd = parts[0][1:]
            if cmd == 'list':
                await send_json(writer, {"type": "list"})
            elif cmd == 'invite' and len(parts) >= 2:
                await send_json(writer, {"type": "invite", "to": parts[1]})
            elif cmd == 'accept' and len(parts) >= 2:
                await send_json(writer, {"type": "accept", "from": parts[1]})
            elif cmd == 'leave':
                await send_json(writer, {"type": "leave"})
            elif cmd == 'msg' and len(parts) >= 3:
                to_and_msg = parts[1]
                # allow /msg <user> <message>
                sub = parts[2]
                await send_json(writer, {"type": "message", "to": to_and_msg, "text": sub})
            elif cmd == 'quit':
                print("退出客户端")
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
                return
            else:
                print("未知命令或参数: ", user_input)
        else:
            print("请使用 /msg <user> <message> 来发送私聊消息，或使用 /help 查看帮助")

async def main(host: str, port: int):
    reader, writer = await asyncio.open_connection(host, port)
    loop = asyncio.get_event_loop()
    # register
    username = input('输入用户名: ').strip()
    await send_json(writer, {"type": "register", "username": username})
    # start reader
    tasks = [asyncio.create_task(reader_task(reader)), asyncio.create_task(input_loop(writer))]
    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in tasks:
        if not t.done():
            t.cancel()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8888)
    args = parser.parse_args()
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print('客户端退出')
