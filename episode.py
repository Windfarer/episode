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
from datetime import date
from jinja2 import Environment, FileSystemLoader
from markdown import Markdown
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from docopt import docopt
import yaml


SEED_PATH = os.path.abspath("seed")

md_pattern = re.compile(r"(\n)*\-+(\n)*(?P<meta>(.*?\n)*?)\-+\n*?")
post_name_pattern = re.compile(r"(?P<year>(\d{4}))\-(?P<month>(\d{1,2}))\-(?P<day>(\d{1,2}))\-(?P<alias>(.+))")

md = Markdown()


class Page:
    def __init__(self, file, path_templete="", site_path="site", date_template="%Y/%m/%d"):

        self._path_template = path_templete
        self._date_template = date_template
        self.site_path = site_path
        self._filename, self._filename_extension = os.path.splitext(os.path.basename(file))

        self.formatted_date = None

        self._file = open(file, "r").read()
        self._parse_file_name()
        self._parse_file()


    @property
    def path(self):
        if self.type == "post":
            return os.path.join(self.site_path, self._path_template.format(year=self.date.year,
                                                           month=self.date.month,
                                                           day=self.date.day))
        else:
            return self.site_path

    def _parse_file_name(self):
        matched = re.match(post_name_pattern, self._filename)
        if matched:
            year = int(matched.group("year"))
            month = int(matched.group("month"))
            day = int(matched.group("day"))
            self.date = date(year, month, day)
            self.alias = matched.group("alias")
            self.formatted_date = self.date.strftime(self._date_template)
            self.type = "post"
        else:
            self.alias = self._filename
            self.type = "page"

    def _parse_file(self):
        matched = md_pattern.match(self._file)
        meta = matched.group("meta")
        self.data = yaml.load(meta)
        self.data["date"] = self.formatted_date if self.formatted_date else None
        self.data["content"] = md.convert(self._file[matched.end():])
        self.data["path"] = self.path
        self.data["alias"] = self.alias
        self.data["template"] += ".html"


class Episode:
    def __init__(self):
        self.project_path = os.getcwd()
        self.env = Environment(loader=FileSystemLoader(self._get_path(self.config.get("template_folder"))))
        self.posts = []
        self.pages = []
        self._get_config()

    def _get_path(self, folder):
        return os.path.join(self.project_path, folder)

    def _get_config(self):
        config_path = os.path.join(self.project_path, "config.yaml")
        stream = open(config_path, "r")
        self.config = yaml.load(stream)
        print("="*10)
        print(self.config)

    def _get_template_by_name(self, template_name):
        return self.env.get_template("{}.html".format(template_name))

    def _walk_files(self):
        for dirpath, dirnames, filenames in os.walk(self.project_path):
            for name in filenames:
                if os.path.splitext(name)[-1] in self.config.get("file_ext"):
                    file_obj = Page(os.path.join(dirpath, name), path_templete=self.config.get("path_template"))
                    if file_obj.type == "post":
                        self.posts.append(file_obj.data)
                    else:
                        self.pages.append(file_obj.data)

        for page in self.pages:
            self._render_html_file(page)
        for post in self.posts:
            self._render_html_file(post)

    def _render_html_file(self, page):
        target_file = os.path.join(page.get("path"), page.get("alias")) + ".html"
        print(target_file)
        if not os.path.exists(page.get("path")):
            os.makedirs(page.get("path"))
        f = open(target_file, 'w')
        f.write(self.env.get_template(page.get("template")).render(title=page.get("title"),
                                                                   content=page.get("cotent"),
                                                                   site=self.config,
                                                                   posts=self.posts,
                                                                   pages=self.pages))
        f.close()

    def _copy_static_files(self):
        for d in self.config.get("static_folders"):
            from_dir = os.path.join(self.project_path, d)
            to_dir = os.path.join(self._get_path(self.config.get("destination")), d)
            if os.path.exists(from_dir):
                if os.path.exists(to_dir):
                    shutil.rmtree(to_dir)
                shutil.copytree(from_dir, to_dir)

    def generate_project(self, project_name):
        if os.path.exists(project_name):
            shutil.rmtree(project_name)
        shutil.copytree(SEED_PATH, project_name)

    def build(self):
        shutil.rmtree(self._get_path(self.config.get("destination")))
        self._copy_static_files()
        self._walk_files()

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
        if os.path.isdir(item) and item != "site":
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