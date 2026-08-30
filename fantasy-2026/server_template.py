#!/usr/bin/env python3
"""
On the Clock - 2026 fantasy football draft assistant, served from your own machine.

    python3 fantasy-draft.py

Opens http://127.0.0.1:8712 in your browser. Every pick is written straight to
disk, so nothing depends on a browser remembering anything.

    python3 fantasy-draft.py --dir ~/Documents/fantasy    where to keep the files
    python3 fantasy-draft.py --port 9000                  use a different port
    python3 fantasy-draft.py --no-browser                 don't open a browser

Needs nothing but Python 3.8+. No pip install, no internet.
Listens on 127.0.0.1 only - it is not reachable from anywhere else on your network.
"""
import argparse, base64, http.server, json, os, pathlib, re, shutil, socket
import sys, threading, time, webbrowser

PAGE = base64.b64decode("@@PAGE@@")
CURRENT, HISTORY_EVERY, MAX_BODY = "fantasy-draft-2026.json", 60, 1 << 20
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


class Store:
    def __init__(self, root):
        self.root = pathlib.Path(root).expanduser().resolve()
        self.hist = self.root / "history"
        self.root.mkdir(parents=True, exist_ok=True)
        self.hist.mkdir(exist_ok=True)
        self.file = self.root / CURRENT
        self.lock = threading.Lock()
        self.last_hist = 0.0

    def read(self):
        with self.lock:
            try:
                return json.loads(self.file.read_text("utf-8"))
            except (OSError, ValueError):
                return None

    def write(self, data):
        with self.lock:
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1), "utf-8")
            os.replace(tmp, self.file)          # atomic: never a half-written draft
            now = time.time()
            if now - self.last_hist > HISTORY_EVERY:
                self.last_hist = now
                shutil.copy2(self.file, self.hist / time.strftime("draft-%Y%m%d-%H%M%S.json"))
                self.prune()

    def prune(self, keep=60):
        snaps = sorted(self.hist.glob("draft-*.json"))
        for old in snaps[:-keep]:
            try: old.unlink()
            except OSError: pass


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "OnTheClock/1.0"
    protocol_version = "HTTP/1.1"

    def local_only(self):
        """Reject anything that isn't this machine talking to itself.

        Binding to loopback stops other machines, but a web page you visit can
        still aim requests at 127.0.0.1, so check Host and Origin too."""
        host = re.sub(r":\d+$", "", self.headers.get("Host", ""))
        if host not in LOCAL_HOSTS:
            self.fail(403, "bad host"); return False
        origin = self.headers.get("Origin")
        if origin:
            o = re.sub(r"^https?://", "", origin)
            if re.sub(r":\d+$", "", o) not in LOCAL_HOSTS:
                self.fail(403, "bad origin"); return False
        return True

    def send(self, code, body, ctype):
        if isinstance(body, str): body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True      # browser navigated away mid-response; not our problem

    def fail(self, code, msg):
        self.send(code, json.dumps({"error": msg}), "application/json")

    def do_GET(self):
        if not self.local_only(): return
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self.send(200, PAGE, "text/html; charset=utf-8")
        if path == "/favicon.ico":
            return self.send(204, b"", "image/x-icon")
        if path == "/api/draft":
            return self.send(200, json.dumps({
                "dir": str(STORE.root), "file": CURRENT, "draft": STORE.read()
            }), "application/json")
        self.fail(404, "not found")

    def do_POST(self):
        if not self.local_only(): return
        if self.path.split("?", 1)[0] != "/api/draft":
            return self.fail(404, "not found")
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self.fail(400, "bad length")
        if n <= 0 or n > MAX_BODY:
            return self.fail(413, "body too large")
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self.fail(400, "bad json")
        if not isinstance(data, dict) or not isinstance(data.get("h"), list):
            return self.fail(400, "not a draft")
        try:
            STORE.write(data)
        except OSError as e:
            return self.fail(500, f"could not write: {e}")
        picked = len(data.get("roster", []))
        print(f"  saved · {picked} of your picks · {time.strftime('%H:%M:%S')}", flush=True)
        self.send(200, json.dumps({"ok": True}), "application/json")

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def log_message(self, *a): pass          # the saves above are the only log worth having

    def log_error(self, *a): pass


def free_port(port):
    for p in range(port, port + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return port


def main():
    ap = argparse.ArgumentParser(description="Serve the 2026 draft assistant from this machine.")
    ap.add_argument("--dir", default=str(pathlib.Path(__file__).resolve().parent / "fantasy-draft-data"),
                    help="folder to keep drafts in (default: fantasy-draft-data next to this script)")
    ap.add_argument("--port", type=int, default=8712)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    global STORE
    STORE = Store(a.dir)
    port = free_port(a.port)

    print("\n  On the Clock - 2026 draft assistant")
    print(f"  open      http://127.0.0.1:{port}")
    print(f"  saving to {STORE.root}")
    print(f"  backups   {STORE.hist}")
    print("  stop      Ctrl-C\n")

    class Server(http.server.ThreadingHTTPServer):
        daemon_threads = True
        def handle_error(self, request, addr):
            kind = sys.exc_info()[0]
            if kind not in (BrokenPipeError, ConnectionResetError):
                super().handle_error(request, addr)

    srv = Server(("127.0.0.1", port), Handler)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped - your draft is saved at")
        print(f"  {STORE.file}\n")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
