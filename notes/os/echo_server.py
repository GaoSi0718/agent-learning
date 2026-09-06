# -*- coding: utf-8 -*-
# notes/os/echo_server.py
"""D2 配套：selectors 实现的 IO 多路复用 echo server（单线程同时服务多连接）。
用法：
  python notes/os/echo_server.py                 # 前台运行，监听 127.0.0.1:9000，Ctrl+C 退出
  python notes/os/echo_server.py --selftest      # 一键自测：起单线程服务 + 5 个并发客户端
                                                 #   各发 20 条消息，校验全部原样返回
演示要点：服务端只用一个线程，靠 selectors 同时挂起全部连接的「可读事件」——
这就是 epoll/select 模型「单线程扛万级连接」的最小可运行版本（呼应 l0_bank/os_50 题 28/37）。
零第三方依赖、零 API 成本。"""
import argparse, socket, selectors, threading

HOST, PORT = "127.0.0.1", 9000

class EchoServer:
    """selectors 版单线程 echo server：注册 accept 与已建连接的读事件。"""

    def __init__(self, host=HOST, port=PORT):
        self.sel = selectors.DefaultSelector()
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind((host, port))
        self.lsock.listen()
        self.lsock.setblocking(False)
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)
        self.connections_served = 0
        self._stop = False

    def _accept(self, sock):
        conn, addr = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, data=addr)
        self.connections_served += 1

    def _read(self, conn):
        try:
            data = conn.recv(4096)
        except (ConnectionResetError, OSError):
            data = b""
        if data:
            conn.sendall(data)              # echo：原样回写
        else:
            self.sel.unregister(conn)
            conn.close()

    def serve_forever(self):
        while not self._stop:
            for key, _mask in self.sel.select(timeout=0.2):
                if key.data is None:
                    self._accept(key.fileobj)
                else:
                    self._read(key.fileobj)

    def stop(self):
        self._stop = True

def selftest(clients: int = 5, messages: int = 20) -> int:
    """单线程服务 + 多客户端并发：验证全部消息原样返回。"""
    server = EchoServer()
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    errors = []
    def client(cid: int):
        try:
            with socket.create_connection((HOST, PORT), timeout=5) as s:
                s.settimeout(5)
                for i in range(messages):
                    msg = f"client-{cid}-msg-{i}".encode()
                    s.sendall(msg)
                    got = b""
                    while len(got) < len(msg):
                        chunk = s.recv(4096)
                        if not chunk:
                            raise ConnectionError("连接被服务端关闭")
                        got += chunk
                    if got != msg:
                        errors.append(f"c{cid}#{i} 回显不一致: {got!r}")
        except Exception as e:
            errors.append(f"c{cid}: {type(e).__name__}: {e}")

    threads = [threading.Thread(target=client, args=(i,)) for i in range(clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    server.stop()

    total = clients * messages
    ok = not errors and server.connections_served >= clients
    print(f"[selftest] 服务端单线程累计受理连接 {server.connections_served} 个；"
          f"客户端 {clients}×{messages} 条消息")
    for e in errors[:5]:
        print("  错误:", e)
    print(f"[PASS] 单线程 echo server：{total} 条消息全部原样返回，多连接并发无串扰"
          if ok else "[FAIL] 自测未通过")
    return 0 if ok else 1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="一键自测模式")
    ap.add_argument("--clients", type=int, default=5)
    ap.add_argument("--messages", type=int, default=20)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest(args.clients, args.messages))
    print(f"echo server 监听 {HOST}:{PORT}（Ctrl+C 退出）；自测请加 --selftest")
    EchoServer().serve_forever()
