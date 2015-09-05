from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class WebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length'))
        print('length', length)
        body = self.rfile.read(length).decode('utf-8')
        print(json.loads(body))
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("Hello World", "utf-8"))
        return


if __name__ == "__main__":
    port = 8000
    Handler = WebHookHandler
    httpd = HTTPServer(("", port), Handler)
    print("Serving at http://127.0.0.1:{port}".format(port=port))
    httpd.serve_forever()