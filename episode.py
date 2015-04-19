"""Usage:
    episode new <project_name>
    episode server <host> <port>
    episode build
    episode watch
    episode -h | --help | --version
"""

import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import shutil
import time
from jinja2 import Environment, FileSystemLoader
from markdown import Markdown
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from docopt import docopt


TEMPLATE_FOLDER = "templates"
POST_FOLDER = "posts"
PAGE_FOLDER = ""
SITE_FOLDER = "site"
static_folders = ["css", "js"]
EXT_LIST = [".md", ".markdown"]
SEED_PATH = os.path.abspath("seed")
IGNORE_PATH = ["site"]

md_pattern = re.compile(r"(\n)*\-+(\n)*(?P<meta>(.*?\n)*?)\-+\n")
post_name_pattern = re.compile(r"(?P<year>(\d{4}))\-(?P<month>(\d{1,2}))\-(?P<day>(\d{1,2}))\-(?P<alias>(.+))")


class MarkdownFile:
    def __init__(self, file):
        self._filename, self._filename_extension = os.path.splitext(os.path.basename(file))
        self._markdown_render = Markdown()
        self._file = open(file, "r").read()
        self._parse_file_name()
        self._parse_file()
        self.type = "page"
        self.target_path = SITE_FOLDER

    def _parse_file_name(self):
        self.alias = self._filename

    def _parse_file(self):
        matched = md_pattern.match(self._file)
        meta = matched.group("meta").split("\n")
        payload = dict()
        for item in meta:
            if item:
                item = item.split(":")
                if len(item) == 2:
                    payload[item[0].lower()] = item[1].strip()

        self.meta = payload
        self.template = self.meta.get("template") + ".html"
        self.content = self._markdown_render.convert(self._file[matched.end():])


class PostMarkdownFile(MarkdownFile):
    def __init__(self, file):
        super().__init__(file)
        self.type = "post"
        self.target_path = os.path.join(SITE_FOLDER, "posts", self.year, self.month, self.day)

    def _parse_file_name(self):
        matched = re.match(post_name_pattern, self._filename)
        self.year = matched.group("year")
        self.month = "{:02}".format(int(matched.group("month")))
        self.day = "{:02}".format(int(matched.group("day")))
        self.alias = matched.group("alias")


class Episode:
    def __init__(self):
        self.project_path = os.getcwd()
        self.template_path = os.path.join(self.project_path, TEMPLATE_FOLDER)
        self.site_path = os.path.join(self.project_path, SITE_FOLDER)
        self.post_path = os.path.join(self.project_path, POST_FOLDER)
        self.page_path = os.path.join(self.project_path, PAGE_FOLDER)
        self.env = Environment(loader=FileSystemLoader(self.template_path))
        self.posts = []
        self.pages = []

    def _get_template_by_name(self, template_name):
        return self.env.get_template("{}.html".format(template_name))

    def _walk_pages(self):
        for file in os.listdir(self.project_path):
            if os.path.splitext(file)[-1] in EXT_LIST:
                file_obj = MarkdownFile(os.path.join(self.project_path, file))
                if file_obj:
                    self.pages.append(file_obj)
                    if not os.path.exists(file_obj.target_path):
                        os.makedirs(file_obj.target_path)
                    self._render_html_file(file_obj)

    def _walk_posts(self):
        for file in os.listdir(self.post_path):
            if os.path.splitext(file)[-1] in EXT_LIST:
                file_obj = PostMarkdownFile(os.path.join(self.post_path, file))
                if file_obj:
                    self.posts.append(file_obj)
                    if not os.path.exists(file_obj.target_path):
                        os.makedirs(file_obj.target_path)
                    self._render_html_file(file_obj)

    def _render_html_file(self, file_obj):
        target_file = os.path.join(self.project_path, file_obj.target_path, file_obj.alias) + ".html"
        print(target_file)
        f = open(target_file, 'w')
        f.write(self.env.get_template(file_obj.template).render(content=file_obj.content))
        f.close()

    def _copy_static_files(self):
        for d in static_folders:
            from_dir = os.path.join(self.project_path, d)
            to_dir = os.path.join(self.site_path, d)
            if os.path.exists(from_dir):
                if os.path.exists(to_dir):
                    shutil.rmtree(to_dir)
                shutil.copytree(from_dir, to_dir)

    def generate_project(self, project_name):
        if os.path.exists(project_name):
            shutil.rmtree(project_name)
        shutil.copytree(SEED_PATH, project_name)

    def build(self):
        self._copy_static_files()
        self._walk_pages()
        if os.path.exists(self.post_path):
            self._walk_posts()

    def server(self, address="0.0.0.0", port=8000, server_class=HTTPServer, handler_class=BaseHTTPRequestHandler):
        server_address = (address, port)
        httpd = server_class(server_address, handler_class)
        print("Serving at http://{address}:{port}".format(address=address, port=port))
        httpd.serve_forever()


class FileChangeEventHandler(FileSystemEventHandler):
    def __init__(self, episode_instance):
        self.episode_instance = episode_instance

    def on_moved(self, event):
        self.episode_instance.build()
        print("==move====src"+event.src_path)

    def on_created(self, event):
        self.episode_instance.build()
        print("==create====src"+event.src_path)

    def on_deleted(self, event):
        self.episode_instance.build()
        print("==delete====src"+event.src_path)

    def on_modified(self, event):
        self.episode_instance.build()
        print("===modified===src"+event.src_path)


def start_server():
    print("start server")
    Episode().server()


def start_watch():
    print("start watch")
    episode = Episode()
    episode.build()
    root_path = os.getcwd()
    event_handler = FileChangeEventHandler(episode)
    observer = Observer()
    observer.schedule(event_handler, root_path, recursive=False)
    for item in os.listdir("."):
        if os.path.isdir(item) and item not in IGNORE_PATH:
            observer.schedule(event_handler, item, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()


def start_build():
    print("start build")
    Episode().build()


def start_new(project_name):
    print("create a new project")
    Episode().generate_project(project_name)


def command_options(arguments):
    if arguments["new"]:
        start_new(arguments["<project_name>"])
    elif arguments["build"]:
        start_build()
    elif arguments["server"]:
        start_server()
    elif arguments["watch"]:
        start_watch()

if __name__ == '__main__':
    arguments = docopt(__doc__, version='0.0.1')
    command_options(arguments)