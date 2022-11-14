#!/bin/env python3

from setuptools import setup, find_packages
import os
import re

import insarviz
import insarviz.version as version

def local_file(name):
    return os.path.relpath(os.path.join(os.path.dirname(__file__), name))


def get_pattern(filename, pattern):
    """ extracting the pattern from the filename. If many patterns are
    found, return a string containing a comma separated list"""
    regex = re.compile(pattern)
    result = ""
    with open(filename, "r") as _f:
        searchs = (regex.search(line) for line in _f)
        auths = (m.group(1) for m in searchs if m)
        result = ",".join(auths)
    return result


# Get version number from _version.py
__version__ = version.__version__

assert __version__ is not None

authors = get_pattern(local_file('AUTHORS.rst'), r"^\*\s*(.*?)\(.*@")
contact = get_pattern(local_file('AUTHORS.rst'), r"Contact:.*<(.*?)>")

with open(local_file('requirements.txt')) as requirements_file:
    requirements = requirements_file.read().splitlines()

setup(name="insarviz",
      version=__version__,
      author=authors,
      author_email=contact,
      description='Python package for visualisation of InSar Data',
      long_description=open('README.rst').read(),
      long_description_content_type='text/markdown',
      url='https://gricad-gitlab.univ-grenoble-alpes.fr/deformvis/insarviz/',
      packages=find_packages(),
      install_requires=requirements,
      setup_requires=['wheel'],
      classifiers=[
          'Programming Language :: Python :: 3 :: Only',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Intended Audience :: Science/Research',
          'Topic :: Scientific/Engineering :: Data Visualisation'
      ],
      test_suite="testing",
      entry_points={'console_scripts': ['ts_viz = insarviz.ts_viz:main']}
      )
