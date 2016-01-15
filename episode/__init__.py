"""Usage:
    episode new <project_name>
    episode server <port>
    episode build
    episode deploy
    episode watch
    episode -h | --help | --version
"""

__version__ = '0.1.0'

import os
import re
import sys
import yaml
import time
import math
import uuid
import shutil
import subprocess
import http.server
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from markdown2 import Markdown
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from docopt import docopt

EPISODE_PATH = os.path.dirname(__file__)
SEED_PATH = os.path.join(EPISODE_PATH, "seed")
TMP_ROOT_PATH = "/tmp"
TMP_FOLDER_PREFIX = "episode"
PAGINATION_PATH = "p"
TEMPLATE_PATH = "templates"
PAGE_FILE_EXT = [".md", ".markdown"]


CONTENT_CONF = {
    # content_type(path): attribute
    "posts": "posts",
    "pages": "pages"
}

md_pattern = re.compile(r"(\n)*(?P<meta>(.*?\n)*?)\-+\n*?")
post_name_pattern = re.compile(r"(?P<year>(\d{4}))\-(?P<month>(\d{1,2}))\-(?P<day>(\d{1,2}))\-(?P<alias>(.+))")

md = Markdown(extras=["fenced-code-blocks", "tables"])


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i+n]


class Page:
    """
    Generate a Page(or post) object, contains meta info and content.

    if obj.type is 'post', an example of page obj's useful data can be shown as follows:

    obj.data = {
        "title": "i'm a title",
        "date": "2015-01-01",
        "content": "This is the content",
        "path": "/2015/01/01/test-post.html",
        "alias": "test-post",
        "template": "post",
        "url": "http://example.com/2015/01/01/test-post.html"
    }

    """
    def __init__(self, file, config, path_templete="", date_template="%Y/%m/%d"):
        self._path_template = path_templete
        self._date_template = date_template
        self.config = config
        self._filename, self._filename_extension = os.path.splitext(os.path.basename(file))
        self.date = None
        self.formatted_date = None

        self._file = open(file, "r").read()
        self._parse_file_name()
        self._parse_file()

    @property
    def path(self):
        if self.type == "post":
            return self.formatted_date
        else:
            return ""

    def _parse_file_name(self):
        matched = post_name_pattern.match(self._filename)
        if matched:
            year = int(matched.group("year"))
            month = int(matched.group("month"))
            day = int(matched.group("day"))
            self.date = datetime(year=year, month=month, day=day)
            self.alias = matched.group("alias")
            self.formatted_date = self.date.strftime(self._date_template)
            self.type = "post"
        else:
            self.alias = self._filename
            self.type = "page"

    def _parse_file(self):
        matched = md_pattern.match(self._file)
        meta = yaml.load(matched.group("meta"))
        self.data = {
            "title": meta.get("title"),
            "content": md.convert(self._file[matched.end():]),
            "path": self.path,
            "alias": self.alias,
            "template": ".".join([meta["template"], "html"]) if meta.get("template") else "default.html",
            "url": os.path.join(self.config.get("url"), self.path, self.alias),
        }
        if meta.get("date"):
            self.data["date"] = meta.get("date")
        else:
            self.data["date"] = self.date


class GitRepo:
    def __init__(self, repo_address=None, dst=None):
        self.repo_address = repo_address
        self.dst = dst

    def clone(self):
        subprocess.check_call(["git", "clone", self.repo_address, self.dst])

    def add_and_commit(self, message="Update posts"):
        subprocess.check_call(["git", "add", "."])
        try:
            subprocess.check_call(["git", "commit", "-m", message])
        except subprocess.CalledProcessError as e:
            pass

    def checkout_or_create(self, branch="source"):
        try:
            subprocess.check_call(["git", "checkout", branch])
        except subprocess.CalledProcessError as e:
            subprocess.check_call(["git", "checkout", "-b", branch])

    def branch(self, branch):
        try:
            subprocess.check_call(["git", "checkout", branch])
        except subprocess.CalledProcessError as e:
            subprocess.check_call(["git", "checkout", "-b", branch])

    def push(self, branch, force=False):
        if force:
            subprocess.check_call(["git", "push", "origin", branch, "-f"])
        else:
            subprocess.check_call(["git", "push", "origin", branch])

    def pull(self, branch):
        subprocess.check_call(["git", "pull", "origin", branch])

    def fetch(self):
        subprocess.check_call(["git", "fetch"])

    def add_remote(self, address):
        subprocess.check_call(["git", "remote", "add", "origin", address])

    def init(self):
        subprocess.check_call(["git", "init"])


class Initializer:
    """
    To initialize a site project.
    """
    def __init__(self, project_name):
        if os.path.exists(project_name):
            print("folder already exists.")
            return
        shutil.copytree(SEED_PATH, project_name)
        os.chdir(project_name)
        for content_type in CONTENT_CONF.keys():
            os.mkdir(content_type)
        self.git_repo = GitRepo()
        self.git_repo.init()
        self.git_repo.checkout_or_create()
        print("Done! Enjoy it!")


class Episode:
    """
    The main obj of episode static site generator.
    the build workflow:
    1. cleaning the working folders.
    2. copy static files into site folders.
    3. walking markdown files.
    4. parsing them as Page objs and storing them in memory.
    5. rendering pages into html templates, generating html files.
    6. creating path out of the site's structure, putting html files into the correct destinations.
    """
    def __init__(self):
        self.posts = []
        self.pages = []
        tmp_build_folder = "_".join([TMP_FOLDER_PREFIX, str(uuid.uuid1())])  # todo: temp folder name needs to be considered
        self.destination = os.path.join(TMP_ROOT_PATH, tmp_build_folder)
        self.project_path = os.getcwd()
        self._get_config()
        self.env = Environment(loader=FileSystemLoader(self._get_path(TEMPLATE_PATH)))
        self.env.globals["site"] = self.config
        self.env.globals["pages"] = self.pages

        self.git_repo = GitRepo(self.config.get("deploy_repo"))

    def _get_path(self, folder):
        return os.path.join(self.project_path, folder)

    def _get_config(self):
        config_path = os.path.join(self.project_path, "config.yaml")
        stream = open(config_path, "r")
        self.config = yaml.load(stream)

    def _get_template_by_name(self, template_name):
        return self.env.get_template("{}.html".format(template_name))

    def _walk_files(self, content_type):
        for f in os.listdir(content_type):
            if os.path.splitext(f)[-1] in PAGE_FILE_EXT:
                file_obj = Page(os.path.join(content_type, f),
                                config=self.config)
                getattr(self, CONTENT_CONF[content_type]).append(file_obj.data)
        self.posts.sort(key=lambda x: x['date'], reverse=True)

    def _render_html_file(self, page):
        target_path = os.path.join(self.destination, page.get("path"))
        target_file = os.path.join(target_path, page.get("alias")) + ".html"
        if not os.path.exists(target_path):
            os.makedirs(target_path)
        with open(target_file, 'w') as f:
            f.write(self.env.get_template(page.get("template")).render(page))

    def _render_pagination(self):
        pagination = self.config.get("paginate")
        pagination_folder = os.path.join(self.destination, PAGINATION_PATH)
        post_count = len(self.posts)
        print(self.posts)
        total_pages = math.ceil(post_count/pagination)
        previous_page = next_page = None
        if post_count > pagination:
            os.makedirs(pagination_folder)
        for index, posts in enumerate(chunks(self.posts, pagination), start=1):
            try:
                if index == 1:
                    f = open(os.path.join(self.destination, "index.html"), 'w')
                else:
                    f = open(os.path.join(pagination_folder, "{}.html".format(str(index))), 'w')
                if index == 2:
                    previous_page = "index.html"
                elif index > 1:
                    previous_page = os.path.join(PAGINATION_PATH, "{}.html".format(str(index-2)))

                if index < total_pages:
                    next_page = os.path.join(PAGINATION_PATH, "{}.html".format(str(index+1)))

                f.write(self.env.get_template("index.html").render({
                    "pagination_posts": posts,
                    "current_page": index,
                    "total_pages": total_pages,
                    "previous_page": previous_page,
                    "next_page": next_page
                }))
            finally:
                f.close()

    def _render(self):
        for content_type in CONTENT_CONF.keys():
            for item in getattr(self, content_type):
                self._render_html_file(item)
        self._render_pagination()

    def _clean_folder(self):
        for path in os.listdir('.'):
            if not path.startswith('.'):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

    def _copy_files(self, from_path, to_path, only_dirs=False):
        for item in os.listdir(from_path):
            src = os.path.join(from_path, item)
            dst = os.path.join(to_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            elif not only_dirs:
                shutil.copy2(src, dst)

    def build(self):
        start = time.clock()
        os.makedirs(self.destination)

        self._copy_files(TEMPLATE_PATH, self.destination, only_dirs=True)

        for path in CONTENT_CONF.keys():
            if os.path.isdir(path):
                self._walk_files(path)
        self._render()
        print("Done!", "Result path:")
        print(self.destination)
        end = time.clock()
        print("run time: {time}s".format(time=end-start))

    def deploy(self):
        if not self.config.get("deploy_repo"):
            return print("not specify deploy repo.")
        self.git_repo.checkout_or_create('source')
        self.git_repo.add_and_commit()
        self.git_repo.push('source', force=True)  # todo: if conflict?
        self.build()
        self.git_repo.checkout_or_create("master")
        self._clean_folder()
        self._copy_files(self.destination, os.getcwd())
        self.git_repo.add_and_commit()
        self.git_repo.push("master")
        self.git_repo.checkout_or_create("source")

    def server(self, port=8000):
        self.build()
        print("start server")
        os.chdir(self.destination)
        Handler = http.server.SimpleHTTPRequestHandler
        httpd = http.server.HTTPServer(("", port), Handler)
        print("Serving at http://127.0.0.1:{port}".format(port=port))
        httpd.serve_forever()

    def watch(self):
        self.build()
        event_handler = FileChangeEventHandler(self)
        observer = Observer()
        observer.schedule(event_handler, self.config.get("root"), recursive=False)

        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()


class FileChangeEventHandler(FileSystemEventHandler):  # todo: watching
    def __init__(self, episode):
        self.episode = episode

    def on_created(self, event):
        self.episode.build()
        print("==create====src"+event.src_path)

    def on_deleted(self, event):
        self.episode.build()
        print("==delete====src"+event.src_path)

    def on_modified(self, event):
        self.episode.build()
        print("===modified===src"+event.src_path)


def start_server():
    print("start server")
    Episode().server()


def start_watch():
    print("start watch")
    Episode().watch()


def start_build():
    print("start build")
    Episode().build()


def start_new(project_name):
    print("create a new project")
    Initializer(project_name)


def start_deploy():
    print("deploy to github")
    Episode().deploy()


def command_options(arguments):
    if arguments["new"]:
        start_new(arguments["<project_name>"])
    elif arguments["build"]:
        start_build()
    elif arguments["server"]:
        start_server()
    elif arguments["watch"]:
        start_watch()
    elif arguments["deploy"]:
        start_deploy()


def run():
    arguments = docopt(__doc__, version=__version__)
    command_options(arguments)
