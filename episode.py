from jinja2 import Environment, FileSystemLoader
from markdown import Markdown
import argparse
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import shutil

TEMPLATE_FOLDER = "templates"
POST_FOLDER = "posts"
PAGE_FOLDER = ""
SITE_FOLDER = "site"
static_folders = ["css", "js"]
EXT_LIST = [".md", ".markdown"]

md_pattern = re.compile(r"(\n)*\-+(\n)*(?P<meta>(.*?\n)*?)\-+\n")
post_name_pattern = re.compile(r"(?P<year>(\d{4}))\-(?P<month>(\d{1,2}))\-(?P<day>(\d{1,2}))\-(?P<alias>(.+))")


class MarkdownFile:
    def __init__(self, file):
        self.filename, self.filename_extension = os.path.splitext(os.path.basename(file))
        self.markdown_render = Markdown()
        self.file = open(file, "r").read()
        self._parse_file_name()
        self._parse_file()
        self.type = "page"
        self.target_path = SITE_FOLDER


    def _parse_file_name(self):
        self.alias = self.filename

    def _parse_file(self):
        matched = md_pattern.match(self.file)
        meta = matched.group("meta").split("\n")
        payload = dict()
        for item in meta:
            if item:
                item = item.split(":")
                if len(item) == 2:
                    payload[item[0].lower()] = item[1].strip()

        self.meta = payload
        self.template = self.meta.get("template") + ".html"
        self.content = self.markdown_render.convert(self.file[matched.end():])


class PostMarkdownFile(MarkdownFile):
    def __init__(self, file):
        super().__init__(file)
        self.type = "post"
        self.target_path = os.path.join(SITE_FOLDER, "posts", self.year, self.month, self.day)

    def _parse_file_name(self):
        matched = re.match(post_name_pattern, self.filename)
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

    def _get_template_by_name(self, template_name):
        return self.env.get_template("{}.html".format(template_name))

    def _walk_files(self, path, func, cls):
        for file in os.listdir(path):
            if os.path.splitext(file)[-1] in EXT_LIST:
                file_obj = cls(os.path.join(path, file))
                if file_obj:
                    if not os.path.exists(file_obj.target_path):
                        os.makedirs(file_obj.target_path)
                    func(file_obj)



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

    def generate_project(self):
        pass

    def build(self):
        # shutil.rmtree(self.project_path)
        self._copy_static_files()
        self._walk_files(self.project_path, self._render_html_file, MarkdownFile)
        if os.path.exists(self.post_path):
            self._walk_files(self.post_path, self._render_html_file, PostMarkdownFile)

    def watch(self):
        pass

    def server(self, address="0.0.0.0", port=8000, server_class=HTTPServer, handler_class=BaseHTTPRequestHandler):
        server_address = (address, port)
        httpd = server_class(server_address, handler_class)
        print("Serving at http://{address}:{port}".format(address=address, port=port))
        httpd.serve_forever()


# def create_site():
#     env = Environment(loader=FileSystemLoader("project/templates"))
#
#     template = env.get_template("index.html")
#
#
#     md = open('project/posts/index.md', 'r').read()
#     content = markdown.markdown(md)
#
#     f = open('project/site/index.html', 'w')
#     f.write(template.render(content=content))
#     f.close()
#
    # for d in static_folders:
    #     tpl_dir = os.path.join(PROJECT_FOLDER, TEMPLATE_FOLDER, d)
    #     site_dir = os.path.join(PROJECT_FOLDER, SITE_FOLDER, d)
    #     if os.path.exists(tpl_dir):
    #         if os.path.exists(site_dir):
    #             shutil.rmtree(site_dir)
    #         shutil.copytree(tpl_dir, site_dir)

# def walk_md():
#     env = Environment(loader=FileSystemLoader("project/templates"))
#     template = env.get_template("index.html")
#     file_name_pattern = re.compile(r"(?P<year>(\d{4}))\-(?P<month>(\d{1,2}))\-(?P<day>(\d{1,2}))\-(?P<title>(.+))")
#     post_dir = os.path.join(PROJECT_FOLDER, POST_FOLDER)
#     for file in os.listdir(post_dir):
#         file_name, file_ext = os.path.splitext(file)
#         if file_ext in EXT_LIST:
#             p = re.match(file_name_pattern, file_name)
#             year = p.group("year")
#             month = "{:02}".format(int(p.group("month")))
#             day = "{:02}".format(int(p.group("day")))
#             title = p.group("title")
#             print(year, month, day)
#             md = open(os.path.join(post_dir, file), 'r').read()
#             content = markdown.markdown(md)
#             render_folder = os.path.join(PROJECT_FOLDER, SITE_FOLDER, year, month, day)
#             if not os.path.exists(render_folder):
#                 os.makedirs(render_folder)
#             f = open(os.path.join(render_folder, title+".html"), 'w')
#             f.write(template.render(content=content))
#             f.close()
#
#     for file in os.listdir(PROJECT_FOLDER):
#         file_name, file_ext = os.path.splitext(file)
#         if file_ext in EXT_LIST:
#             md = open(os.path.join(PROJECT_FOLDER, file), 'r').read()
#             content = markdown.markdown(md)
#             render_folder = os.path.join(PROJECT_FOLDER, SITE_FOLDER)
#             if not os.path.exists(render_folder):
#                 os.makedirs(render_folder)
#             f = open(os.path.join(render_folder, file_name+".html"), 'w')
#             f.write(template.render(content=content))
#             f.close()

if __name__ == "__main__":
    os.chdir("project")
    print(os.getcwd())