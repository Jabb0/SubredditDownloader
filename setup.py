from setuptools import setup, find_packages
from subredditdownloader.utils.constants import VERSION


def read_file(file_name):
    with open(file_name, encoding='utf-8') as fh:
        text = fh.read()
    return text


setup(
    name='subredditdownloader',
    version=VERSION,
    packages=find_packages(),
    url='https://github.com/Jabb0/SubredditDownloader',
    license='MIT',
    author='Jabb0',
    description='A simple tool to scrape subreddits and store submissions',
    entry_points={
        'console_scripts': [
            'subredditdownloader=subredditdownloader.__main__:main'
        ]
    },
    install_requires=read_file('./requirements.txt').split('\n'),
)
