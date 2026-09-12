# -*- coding: utf-8 -*-
"""_sse_demo.py — A6 交付：最小 SSE（Server-Sent Events）演示。

端口 8001（8000 留给 w6 主服务，避免与 test_b2_e2e.py 的 BASE 冲突 —— §十 #13）。
仅标准库，无第三方依赖。

用法：
    venv\\Scripts\\python.exe _sse_demo.py          # 监听 127.0.0.1:8001
    curl -N http://127.0.0.1:8001/stream            # 观察分块到达（-N 关闭缓冲）
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8001


def sse_stream():
    """生成 5 条事件 + [DONE]，每条间隔 0.5s，模拟逐 token 下发。"""
    events = [
        {"step": 1, "type": "status", "text": "SSE 连接已建立"},
        {"step": 2, "type": "token", "text": "这是一条"},
        {"step": 3, "type": "token", "text": "逐块推送的"},
        {"step": 4, "type": "token", "text": "演示消息。"},
        {"step": 5, "type": "done", "text": "[DONE]"},
    ]
    for ev in events:
        yield "id: %d\nevent: message\ndata: %s\n\n" % (ev["step"], json.dumps(ev, ensure_ascii=False))
        time.sleep(0.5)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/stream":
            body = "SSE demo. Try: curl -N http://127.0.0.1:%d/stream\n" % PORT
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            for chunk in sse_stream():
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
            self.close_connection = True  # 流结束主动断开，curl -N 正常退出
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass  # 客户端断开属正常（Ctrl+C curl）

    def log_message(self, fmt, *args):
        print("[sse_demo] " + fmt % args)


if __name__ == "__main__":
    print("SSE demo listening on http://127.0.0.1:%d/stream （Ctrl+C 退出）" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
