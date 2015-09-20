from setuptools import setup, find_packages
import episode

setup(
    name='episode',  # todo: setup
    version=episode.__version__,
    packages=find_packages(),
    url='https://www.github.com/windfarer/episode',
    license='MIT',
    author='Windfarer',
    author_email='windfarer@gmail.com',
    description='A simple page generator.',
    install_requires=['docopt',
                      'Jinja2',
                      'markdown2',
                      'MarkupSafe',
                      'pathtools',
                      'Pygments',
                      'PyYAML',
                      'watchdog'],
    entry_points={
        'console_scripts': [
            'episode=episode:run',
            'episode-webhooks=episode.webhooks:run',
        ]
    }
)
