"""
同步阻塞测试客户端（socket），更容易在终端捕获输出。
用法示例：
  python sync_test.py --name A --role initiator --target B
  python sync_test.py --name B --role responder
"""
import socket
import argparse
import json
import time

BUF = 4096

def send(sock, obj):
    data = json.dumps(obj, ensure_ascii=False) + "\n"
    sock.sendall(data.encode())

def recv_line(sock, timeout=5.0):
    sock.settimeout(timeout)
    data = b''
    while True:
        try:
            ch = sock.recv(1)
            if not ch:
                return None
            data += ch
            if ch == b'\n':
                break
        except socket.timeout:
            return None
    return data.decode().strip()

def initiator_flow(sock, name, target):
    time.sleep(0.2)
    send(sock, {"type": "list"})
    t = recv_line(sock); print(f"[{name}] recv: {t}")
    time.sleep(0.2)
    print(f"[{name}] invite {target}")
    send(sock, {"type": "invite", "to": target})
    while True:
        t = recv_line(sock, timeout=10)
        print(f"[{name}] recv: {t}")
        if t is None:
            print(f"[{name}] timeout or disconnected")
            return
        try:
            msg = json.loads(t)
        except Exception:
            continue
        if msg.get('type') == 'accepted' and msg.get('with') == target:
            send(sock, {"type":"message","to":target,"text":f"Hello from {name}"})
        if msg.get('type') == 'message' and msg.get('from') == target:
            send(sock, {"type":"message","to":target,"text":f"Got your message, {target}. Bye"})
            send(sock, {"type":"leave"})
            return


def responder_flow(sock, name):
    while True:
        t = recv_line(sock, timeout=30)
        print(f"[{name}] recv: {t}")
        if t is None:
            print(f"[{name}] timeout/disconnected")
            return
        try:
            msg = json.loads(t)
        except Exception:
            continue
        if msg.get('type') == 'invite':
            frm = msg.get('from')
            print(f"[{name}] accepting {frm}")
            send(sock, {"type":"accept","from":frm})
        if msg.get('type') == 'message':
            frm = msg.get('from')
            send(sock, {"type":"message","to":frm,"text":f"Hi {frm}, this is {name}"})
        if msg.get('type') == 'left' or msg.get('type') == 'peer_disconnected':
            return


def main(host, port, name, role, target=None):
    sock = socket.create_connection((host, port))
    sock.settimeout(1.0)
    print(f"[{name}] connected")
    send(sock, {"type":"register","username":name})
    t = recv_line(sock)
    print(f"[{name}] register reply: {t}")
    if role == 'initiator':
        initiator_flow(sock, name, target)
    else:
        responder_flow(sock, name)
    try:
        sock.close()
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
    main(args.host, args.port, args.name, args.role, args.target)
