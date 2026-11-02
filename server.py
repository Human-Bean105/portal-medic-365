import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from medi.config import API_KEY, MODEL
from medi.web import client_ip, handle_post, respond

HERE = Path(__file__).parent
PORT = int(os.environ.get("DOCTOR_PORT", 8785))
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/assets/logo.png": ("assets/logo.png", "image/png"),
    "/assets/medi-avatar.png": ("assets/medi-avatar.png", "image/png"),
    "/i18n/translations.json": ("i18n/translations.json", "application/json; charset=utf-8"),
    "/dev": ("dev.html", "text/html; charset=utf-8"),
    "/dev.html": ("dev.html", "text/html; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, content_type, data):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path not in STATIC:
            return self._send(404, "text/plain", b"Not found")
        file, content_type = STATIC[path]
        self._send(200, content_type, (HERE / file).read_bytes())

    def do_POST(self):
        if self.path not in ("/consult", "/stream", "/summary", "/voice", "/screen", "/speak", "/retrieve", "/inspect"):
            return self._send(404, "text/plain", b"Not found")
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        status, body = handle_post(self.path.strip("/"), raw, self.headers, client_ip(self))
        respond(self, status, body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if not API_KEY:
        raise SystemExit("Set OPENAI_API_KEY in a .env file first.")
    print(f"Medi is ready at http://localhost:{PORT}  (model: {MODEL})")
    ThreadingHTTPServer.allow_reuse_address = False
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
