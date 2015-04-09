from jinja2 import Environment, PackageLoader
import markdown
import argparse
import os
import re
import http.server
import shutil

TEMPLATE_FOLDER = "templates"
SITE_FOLDER = "site"
static_folders = ["css", "js"]


def create_site():
    env = Environment(loader=PackageLoader(__name__, 'templates'))

    template = env.get_template("index.html")

    md = open('posts/index.md', 'r').read()
    content = markdown.markdown(md)

    f = open('site/index.html', 'w')
    f.write(template.render(content=content))
    f.close()

    for dir in static_folders:
        tpl_dir = os.path.join(TEMPLATE_FOLDER, dir)
        site_dir = os.path.join(SITE_FOLDER, dir)
        if os.path.exists(tpl_dir):
            if os.path.exists(site_dir):
                shutil.rmtree(site_dir)
            shutil.copytree(tpl_dir, site_dir)

if __name__ == "__main__":
    create_site()