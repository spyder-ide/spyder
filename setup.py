# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder
======

The Scientific Python Development Environment

Spyder is a powerful scientific environment written in Python, for Python,
and designed by and for scientists, engineers and data analysts.

It features a unique combination of the advanced editing, analysis, debugging
and profiling functionality of a comprehensive development tool with the data
exploration, interactive execution, deep inspection and beautiful visualization
capabilities of a scientific package.
"""

from __future__ import print_function

import io
import os
import os.path as osp
import subprocess
import sys
import shutil

from distutils.core import setup
from distutils.command.install_data import install_data


#==============================================================================
# Check for Python 3
#==============================================================================
PY3 = sys.version_info[0] == 3


#==============================================================================
# Minimal Python version sanity check
# Taken from the notebook setup.py -- Modified BSD License
#==============================================================================
v = sys.version_info
if v[:2] < (2, 7) or (v[0] >= 3 and v[:2] < (3, 5)):
    error = "ERROR: Spyder requires Python version 2.7 or 3.5 and above."
    print(error, file=sys.stderr)
    sys.exit(1)


#==============================================================================
# Constants
#==============================================================================
NAME = 'spyder'
LIBNAME = 'spyder'
from spyder import __version__, __website_url__  #analysis:ignore


#==============================================================================
# Auxiliary functions
#==============================================================================
def get_package_data(name, extlist):
    """Return data files for package *name* with extensions in *extlist*"""
    flist = []
    # Workaround to replace os.path.relpath (not available until Python 2.6):
    offset = len(name)+len(os.pathsep)
    for dirpath, _dirnames, filenames in os.walk(name):
        if 'tests' not in dirpath:
            for fname in filenames:
                if (not fname.startswith('.') and
                        osp.splitext(fname)[1] in extlist):
                    flist.append(osp.join(dirpath, fname)[offset:])
    return flist


def get_subpackages(name):
    """Return subpackages of package *name*"""
    splist = []
    for dirpath, _dirnames, _filenames in os.walk(name):
        if 'tests' not in dirpath:
            if osp.isfile(osp.join(dirpath, '__init__.py')):
                splist.append(".".join(dirpath.split(os.sep)))
    return splist


def get_data_files():
    """Return data_files in a platform dependent manner"""
    if sys.platform.startswith('linux'):
        if PY3:
            data_files = [('share/applications', ['scripts/spyder3.desktop']),
                          ('share/icons', ['img_src/spyder3.png']),
                          ('share/metainfo', ['scripts/spyder3.appdata.xml'])]
        else:
            data_files = [('share/applications', ['scripts/spyder.desktop']),
                          ('share/icons', ['img_src/spyder.png'])]
    elif os.name == 'nt':
        data_files = [('scripts', ['img_src/spyder.ico',
                                   'img_src/spyder_reset.ico'])]
    else:
        data_files = []
    return data_files


def get_packages():
    """Return package list"""
    packages = get_subpackages(LIBNAME)
    return packages


#==============================================================================
# Make Linux detect Spyder desktop file
#==============================================================================
class MyInstallData(install_data):
    def run(self):
        install_data.run(self)
        if sys.platform.startswith('linux'):
            try:
                subprocess.call(['update-desktop-database'])
            except:
                print("ERROR: unable to update desktop database",
                      file=sys.stderr)
CMDCLASS = {'install_data': MyInstallData}


#==============================================================================
# Main scripts
#==============================================================================
# NOTE: the '[...]_win_post_install.py' script is installed even on non-Windows
# platforms due to a bug in pip installation process
# See spyder-ide/spyder#1158.
SCRIPTS = ['%s_win_post_install.py' % NAME]
if PY3 and sys.platform.startswith('linux'):
    SCRIPTS.append('spyder3')
else:
    SCRIPTS.append('spyder')


#==============================================================================
# Files added to the package
#==============================================================================
EXTLIST = ['.pot', '.po', '.mo', '.svg', '.png', '.css', '.html', '.js',
           '.ini', '.txt', '.qss', '.ttf', '.json', '.rst', '.bloom']
if os.name == 'nt':
    SCRIPTS += ['spyder.bat']
    EXTLIST += ['.ico']


#==============================================================================
# Use Readme for long description
#==============================================================================
with io.open('README.md', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()


#==============================================================================
# Setup arguments
#==============================================================================
setup_args = dict(
    name=NAME,
    version=__version__,
    description='The Scientific Python Development Environment',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    download_url=__website_url__ + "#fh5co-download",
    author="The Spyder Project Contributors",
    author_email="spyderlib@googlegroups.com",
    url=__website_url__,
    license='MIT',
    keywords='PyQt5 editor console widgets IDE science data analysis IPython',
    platforms=["Windows", "Linux", "Mac OS-X"],
    packages=get_packages(),
    package_data={LIBNAME: get_package_data(LIBNAME, EXTLIST)},
    scripts=[osp.join('scripts', fname) for fname in SCRIPTS],
    data_files=get_data_files(),
    classifiers=['License :: OSI Approved :: MIT License',
                 'Operating System :: MacOS',
                 'Operating System :: Microsoft :: Windows',
                 'Operating System :: POSIX :: Linux',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Development Status :: 5 - Production/Stable',
                 'Intended Audience :: Education',
                 'Intended Audience :: Science/Research',
                 'Intended Audience :: Developers',
                 'Topic :: Scientific/Engineering',
                 'Topic :: Software Development :: Widget Sets'],
    cmdclass=CMDCLASS)


#==============================================================================
# Setuptools deps
#==============================================================================
if any(arg == 'bdist_wheel' for arg in sys.argv):
    import setuptools     # analysis:ignore

install_requires = [
    'applaunchservices;platform_system=="Darwin"',
    'atomicwrites',
    'chardet>=2.0.0',
    'cloudpickle',
    'diff-match-patch',
    # This is here until Jedi 0.15+ fixes completions for
    # Numpy and Pandas
    'jedi==0.14.1',
    # Don't require keyring for Python 2 and Linux
    # because it depends on system packages
    'keyring;sys_platform!="linux2"',
    'nbconvert',
    'numpydoc',
    # Required to get SSH connections to remote kernels
    'paramiko;platform_system=="Windows"',
    'pexpect',
    'pickleshare',
    'psutil',
    'pygments>=2.0',
    'pylint',
    'pympler',
    'pyqt5<5.13;python_version>="3"',
    'pyqtwebengine<5.13;python_version>="3"',
    'python-language-server[all]>=0.29.3,<0.30.0',
    'pyxdg>=0.26;platform_system=="Linux"',
    'pyzmq',
    'qdarkstyle>=2.7',
    'qtawesome>=0.5.7',
    'qtconsole>=4.5.5',
    'qtpy>=1.5.0',
    'sphinx',
    'spyder-kernels>=1.7.0,<1.8.0',
    'watchdog',
]

extras_require = {
    'test:python_version == "2.7"': ['mock'],
    'test:platform_system == "Windows"': ['pywin32'],
    'test': ['pytest<5.0',
             'pytest-qt',
             'pytest-mock',
             'pytest-cov',
             'pytest-xvfb;platform_system=="Linux"',
             'pytest-ordering',
             'pytest-lazy-fixture',
             'pytest-faulthandler',
             'mock',
             'flaky',
             'pandas',
             'scipy',
             'sympy',
             'pillow',
             'matplotlib',
             'cython'],
}

if 'setuptools' in sys.modules:
    setup_args['install_requires'] = install_requires
    setup_args['extras_require'] = extras_require

    setup_args['entry_points'] = {
        'gui_scripts': [
            '{} = spyder.app.start:main'.format(
                'spyder3' if PY3 else 'spyder')
        ]
    }

    setup_args.pop('scripts', None)


#==============================================================================
# Main setup
#==============================================================================
setup(**setup_args)
