#!/usr/bin/env python

from distutils.core import setup

__version__ = "0.5.1"
__author__ = "the grugq"
__email__ = "<thegrugq@gmail.com>"

setup(
    name = "PyMaltego",
    version = __version__,
    author = __author__,
    author_email = __email__,
    packages=['maltego'],
    package_dir = {'maltego' : 'src'}
    )
