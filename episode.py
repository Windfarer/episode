from jinja2 import Environment, FileSystemLoader
import markdown
import argparse
import os
import re
import http.server
import shutil

PROJECT_FOLDER = "project"
TEMPLATE_FOLDER = "templates"
POST_FOLDER = "posts"
SITE_FOLDER = "site"
static_folders = ["css", "js"]
EXT_LIST = [".md", ".markdown"]


def create_site():
    env = Environment(loader=FileSystemLoader("project/templates"))

    template = env.get_template("index.html")


    md = open('project/posts/index.md', 'r').read()
    content = markdown.markdown(md)

    f = open('project/site/index.html', 'w')
    f.write(template.render(content=content))
    f.close()

    for d in static_folders:
        tpl_dir = os.path.join(PROJECT_FOLDER, TEMPLATE_FOLDER, d)
        site_dir = os.path.join(PROJECT_FOLDER, SITE_FOLDER, d)
        if os.path.exists(tpl_dir):
            if os.path.exists(site_dir):
                shutil.rmtree(site_dir)
            shutil.copytree(tpl_dir, site_dir)


def walk_md():
    env = Environment(loader=FileSystemLoader("project/templates"))
    template = env.get_template("index.html")
    file_name_pattern = re.compile(r"(?P<year>(\d{4}))\-(?P<month>(\d{1,2}))\-(?P<day>(\d{1,2}))\-(?P<title>(.+))")
    post_dir = os.path.join(PROJECT_FOLDER, POST_FOLDER)
    for file in os.listdir(post_dir):
        file_name, file_ext = os.path.splitext(file)
        if file_ext in EXT_LIST:
            p = re.match(file_name_pattern, file_name)
            year = p.group("year")
            month = "{:02}".format(int(p.group("month")))
            day = "{:02}".format(int(p.group("day")))
            title = p.group("title")
            print(year, month, day)
            md = open(os.path.join(post_dir, file), 'r').read()
            content = markdown.markdown(md)
            render_folder = os.path.join(PROJECT_FOLDER, SITE_FOLDER, year, month, day)
            if not os.path.exists(render_folder):
                os.makedirs(render_folder)
            f = open(os.path.join(render_folder, title+".html"), 'w')
            f.write(template.render(content=content))
            f.close()

    for file in os.listdir(PROJECT_FOLDER):
        file_name, file_ext = os.path.splitext(file)
        if file_ext in EXT_LIST:
            md = open(os.path.join(PROJECT_FOLDER, file), 'r').read()
            content = markdown.markdown(md)
            render_folder = os.path.join(PROJECT_FOLDER, SITE_FOLDER)
            if not os.path.exists(render_folder):
                os.makedirs(render_folder)
            f = open(os.path.join(render_folder, file_name+".html"), 'w')
            f.write(template.render(content=content))
            f.close()

if __name__ == "__main__":
    walk_md()