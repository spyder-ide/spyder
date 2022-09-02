#!/usr/bin/env python

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# the name of the package
name = 'qtconsole'

#-----------------------------------------------------------------------------
# Minimal Python version sanity check
#-----------------------------------------------------------------------------

import sys

v = sys.version_info
if v[0] >= 3 and v[:2] < (3, 6):
    error = "ERROR: %s requires Python version 3.7 or above." % name
    print(error, file=sys.stderr)
    sys.exit(1)

PY3 = (sys.version_info[0] >= 3)

#-----------------------------------------------------------------------------
# get on with it
#-----------------------------------------------------------------------------

import io
import os

from setuptools import setup

pjoin = os.path.join
here = os.path.abspath(os.path.dirname(__file__))

packages = []
for d, _, _ in os.walk(pjoin(here, name)):
    if os.path.exists(pjoin(d, '__init__.py')):
        packages.append(d[len(here)+1:].replace(os.path.sep, '.'))

package_data = {
    'qtconsole' : ['resources/icon/*.svg'],
}

version_ns = {}
with open(pjoin(here, name, '_version.py')) as f:
    exec(f.read(), {}, version_ns)

with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup_args = dict(
    name                          = name,
    version                       = version_ns['__version__'],
    packages                      = packages,
    package_data                  = package_data,
    description                   = "Jupyter Qt console",
    long_description              = long_description,
    long_description_content_type = 'text/markdown',
    author                        = 'Jupyter Development Team',
    author_email                  = 'jupyter@googlegroups.com',
    maintainer                    = 'Spyder Development Team',
    url                           = 'http://jupyter.org',
    license                       = 'BSD',
    platforms                     = "Linux, Mac OS X, Windows",
    keywords                      = ['Interactive', 'Interpreter', 'Shell'],
    python_requires               = '>= 3.7',
    install_requires = [
        'traitlets!=5.2.1,!=5.2.2',
        'ipython_genutils',
        'jupyter_core',
        'jupyter_client>=4.1',
        'pygments',
        'ipykernel>=4.1', # not a real dependency, but require the reference kernel
        'qtpy>=2.0.1',
        'pyzmq>=17.1'
    ],
    extras_require = {
        'test': ['flaky', 'pytest', 'pytest-qt'],
        'doc': 'Sphinx>=1.3',
    },
    entry_points = {
        'gui_scripts': [
            'jupyter-qtconsole = qtconsole.qtconsoleapp:main',
        ]
    },
    classifiers = [
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)

if __name__ == '__main__':
    setup(**setup_args)
