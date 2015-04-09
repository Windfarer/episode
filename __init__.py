from jinja2 import Environment, PackageLoader
import markdown
import argparse
import os
import re
import http.server

env = Environment(loader=PackageLoader(__name__, 'templates'))

template = env.get_template("default.html")
print(template.render(say="hello world"))

f = open('site/test.html', 'w')
f.write(template.render(say="hello world"))
f.close()