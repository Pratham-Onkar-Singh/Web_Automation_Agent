"""Small owned fixture server for offline demos and integration tests."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class FixtureHandler(BaseHTTPRequestHandler):
    records: list[dict] = []

    def do_GET(self):  # noqa: N802
        body = "<h1 id='success'>Saved</h1>" if urlsplit(self.path).path == "/result" else "<form method='post' action='/submit'><label>Name <input name='name'></label><button id='submit' type='submit'>Submit</button></form>"
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        values = parse_qs(self.rfile.read(length).decode())
        self.records.append({key: vals[0] for key, vals in values.items()})
        self.send_response(303)
        self.send_header("Location", "/result")
        self.end_headers()

    def log_message(self, *_args):
        pass


def serve(port: int = 8765):
    return ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)


if __name__ == "__main__":
    serve().serve_forever()
