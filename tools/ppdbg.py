"""Cliente minimo do depurador remoto do PPSSPP (WebSocket) usando so a biblioteca padrao.

Exemplos:
  ppdbg.py shot saida.png
  ppdbg.py press circle
  ppdbg.py seq circle:30 down:10 shot:saida.png
"""
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time

PORT = 54321


class Debugger:
    def __init__(self, port=PORT):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /debugger HTTP/1.1\r\nHost: localhost:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Protocol: debugger.ppsspp.org\r\n"
                        "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        assert b" 101 " in buf.split(b"\r\n")[0], buf[:200]
        self.rest = buf.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.rest) < n:
            chunk = self.s.recv(1 << 16)
            if not chunk:
                raise ConnectionError
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _recv(self):
        data = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            op = b0 & 0x0F
            if op == 9:
                self._send(payload, 10)
                continue
            if op in (0, 1, 2):
                data += payload
                if b0 & 0x80:
                    return json.loads(data)

    def _send(self, data, op=1):
        mask = os.urandom(4)
        head = bytes([0x80 | op])
        n = len(data)
        if n < 126:
            head += bytes([0x80 | n])
        else:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        self.s.sendall(head + mask + bytes(c ^ mask[i & 3] for i, c in enumerate(data)))

    def call(self, event, **args):
        ticket = str(time.time())
        self._send(json.dumps({"event": event, "ticket": ticket, **args}).encode())
        while True:
            m = self._recv()
            if m.get("ticket") == ticket or m.get("event") in ("error", event):
                return m

    def press(self, button, duration=6):
        return self.call("input.buttons.press", button=button, duration=duration)

    def shot(self, path):
        here = os.path.dirname(os.path.abspath(__file__))
        out = os.path.abspath(path)
        if os.path.exists(out):
            os.remove(out)
        for _ in range(3):
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(here, "winshot.ps1"), "-Out", out], capture_output=True)
            if os.path.exists(out):
                return
            time.sleep(1)
        raise RuntimeError(f"print falhou: {r.stdout[-300:]!r} {r.stderr[-600:]!r}")


def main(argv):
    dbg = Debugger()
    for item in argv:
        name, _, arg = item.partition(":")
        if name == "shot":
            dbg.shot(arg)
        elif name == "wait":
            time.sleep(float(arg))
        else:
            dbg.press(name)
            time.sleep(float(arg or 0.4))


if __name__ == "__main__":
    main(sys.argv[1:])
