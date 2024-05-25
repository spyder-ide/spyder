# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2021, Spyder Bot
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------

from setuptools import find_packages
from setuptools import setup

from spyder_boilerplate import __version__


setup(
    # See: https://setuptools.readthedocs.io/en/latest/setuptools.html
    name="spyder-boilerplate",
    version=__version__,
    author="Spyder Bot",
    author_email="spyder.python@gmail.com",
    description="Plugin that registers a programmatic custom layout",
    license="MIT license",
    python_requires='>= 3.8',
    install_requires=[
        "qtpy",
        "qtawesome",
        "spyder>=5.1.1",
    ],
    packages=find_packages(),
    entry_points={
        "spyder.plugins": [
            "spyder_boilerplate = spyder_boilerplate.spyder.plugin:SpyderBoilerplate"
        ],
    },
    classifiers=[
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
    ],
)
