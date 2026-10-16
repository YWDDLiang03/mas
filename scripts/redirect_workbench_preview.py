"""Keep the previous local preview bookmark pointing to the stable workbench."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Redirect(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header('Location', 'http://127.0.0.1:8769' + (self.path if self.path.startswith('/') else '/'))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', '0')
        self.end_headers()

    do_HEAD = do_GET

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8770), Redirect).serve_forever()
