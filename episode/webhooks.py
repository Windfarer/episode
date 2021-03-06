from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import shutil
from episode import GitRepo, Episode

WORK_DIR = "repo"


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

        repo = GitRepo(repo_address=repo_addr, dst=WORK_DIR)

        repo.clone()
        os.chdir(WORK_DIR)
        repo.checkout_or_create("source")
        Episode().deploy()
        os.chdir("..")
        shutil.rmtree(WORK_DIR)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # self.wfile.write(bytes("Hello World", "utf-8"))
        return


def run():
    port = 8000
    handler = WebHookHandler
    httpd = HTTPServer(("0.0.0.0", port), handler)
    print("Serving at http://127.0.0.1:{port}".format(port=port))
    httpd.serve_forever()