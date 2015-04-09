from jinja2 import Environment, FileSystemLoader
import markdown
import argparse
import os
import re
import http.server
import shutil

PROJECT_FOLDER = "project"
TEMPLATE_FOLDER = "templates"
SITE_FOLDER = "site"
static_folders = ["css", "js"]


def create_site():
    env = Environment(loader=FileSystemLoader("project/templates"))

    template = env.get_template("index.html")

    md = open('project/posts/index.md', 'r').read()
    content = markdown.markdown(md)

    f = open('project/site/index.html', 'w')
    f.write(template.render(content=content))
    f.close()

    for dir in static_folders:
        tpl_dir = os.path.join(PROJECT_FOLDER, TEMPLATE_FOLDER, dir)
        site_dir = os.path.join(PROJECT_FOLDER, SITE_FOLDER, dir)
        if os.path.exists(tpl_dir):
            if os.path.exists(site_dir):
                shutil.rmtree(site_dir)
            shutil.copytree(tpl_dir, site_dir)

if __name__ == "__main__":
    create_site()