from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from episode import GitRepo, Episode


class WebHookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        event_type = self.headers.get('X-Github-Event')
        if event_type != 'push':
            return

        length = int(self.headers.get('Content-Length'))
        http_body = self.rfile.read(length).decode('utf-8')
        data = json.loads(http_body)
        ref = data.get('ref')

        if ref != 'refs/heads/source':
            return

        # todo: pull repo & branch to source & build & push to master
        repo_addr = data.get("repository")['ssh_url']
        print('repo', repo_addr)

        repo = GitRepo(repo_address=repo_addr, dst='repo')

        repo.clone()
        os.chdir('repo')
        Episode().deploy()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # self.wfile.write(bytes("Hello World", "utf-8"))
        return


if __name__ == "__main__":
    port = 8000
    Handler = WebHookHandler
    httpd = HTTPServer(("0.0.0.0", port), Handler)
    print("Serving at http://127.0.0.1:{port}".format(port=port))
    httpd.serve_forever()