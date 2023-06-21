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

# Standard library imports
from distutils.command.install_data import install_data
import io
import os
import os.path as osp
import subprocess
import sys

# Third party imports
from setuptools import setup, find_packages
from setuptools.command.install import install


# =============================================================================
# Minimal Python version sanity check
# Taken from the notebook setup.py -- Modified BSD License
# =============================================================================
v = sys.version_info
if v[0] >= 3 and v[:2] < (3, 7):
    error = "ERROR: Spyder requires Python version 3.7 and above."
    print(error, file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================
NAME = 'spyder'
LIBNAME = 'spyder'
WINDOWS_INSTALLER_NAME = os.environ.get('EXE_NAME')

from spyder import __version__, __website_url__  #analysis:ignore


# =============================================================================
# Auxiliary functions
# =============================================================================
def get_package_data(name, extlist):
    """
    Return data files for package *name* with extensions in *extlist*.
    """
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
    """
    Return subpackages of package *name*.
    """
    splist = []
    for dirpath, _dirnames, _filenames in os.walk(name):
        if 'tests' not in dirpath:
            if osp.isfile(osp.join(dirpath, '__init__.py')):
                splist.append(".".join(dirpath.split(os.sep)))

    return splist


def get_data_files():
    """
    Return data_files in a platform dependent manner.
    """
    if sys.platform.startswith('linux'):
        data_files = [('share/applications', ['scripts/spyder.desktop']),
                      ('share/icons', ['img_src/spyder.png']),
                      ('share/metainfo',
                       ['scripts/org.spyder_ide.spyder.appdata.xml'])]
    elif os.name == 'nt':
        data_files = [('scripts', ['img_src/spyder.ico',
                                   'img_src/spyder_reset.ico'])]
    else:
        data_files = []

    return data_files


def get_packages():
    """
    Return package list.
    """
    packages = get_subpackages(LIBNAME)
    return packages


# =============================================================================
# Make Linux detect Spyder desktop file (will not work with wheels)
# =============================================================================
class CustomInstallData(install_data):

    def run(self):
        install_data.run(self)
        if sys.platform.startswith('linux'):
            try:
                subprocess.call(['update-desktop-database'])
            except:
                print("ERROR: unable to update desktop database",
                      file=sys.stderr)


CMDCLASS = {'install_data': CustomInstallData}


# =============================================================================
# Main scripts
# =============================================================================
# NOTE: the '[...]_win_post_install.py' script is installed even on non-Windows
# platforms due to a bug in pip installation process
# See spyder-ide/spyder#1158.
SCRIPTS = ['%s_win_post_install.py' % NAME]

SCRIPTS.append('spyder')

if os.name == 'nt':
    SCRIPTS += ['spyder.bat']


# =============================================================================
# Files added to the package
# =============================================================================
EXTLIST = ['.pot', '.po', '.mo', '.svg', '.png', '.css', '.html', '.js',
           '.ini', '.txt', '.qss', '.ttf', '.json', '.rst', '.bloom',
           '.ico', '.gif', '.mp3', '.ogg', '.sfd', '.bat', '.sh']


# =============================================================================
# Use Readme for long description
# =============================================================================
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
    author_email="spyder.python@gmail.com",
    url=__website_url__,
    license='MIT',
    keywords='PyQt5 editor console widgets IDE science data analysis IPython',
    platforms=["Windows", "Linux", "Mac OS-X"],
    packages=get_packages(),
    package_data={LIBNAME: get_package_data(LIBNAME, EXTLIST)},
    scripts=[osp.join('scripts', fname) for fname in SCRIPTS],
    data_files=get_data_files(),
    python_requires='>=3.7',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Widget Sets',
    ],
    cmdclass=CMDCLASS,
)


install_requires = [
    'applaunchservices>=0.3.0;platform_system=="Darwin"',
    'atomicwrites>=1.2.0',
    'chardet>=2.0.0',
    'cloudpickle>=0.5.0',
    'cookiecutter>=1.6.0',
    'diff-match-patch>=20181111',
    'intervaltree>=3.0.2',
    'ipython>=7.31.1,<9.0.0,!=8.8.0,!=8.9.0,!=8.10.0,!=8.11.0,!=8.12.0,!=8.12.1',
    'jedi>=0.17.2,<0.19.0',
    'jellyfish>=0.7',
    'jsonschema>=3.2.0',
    'keyring>=17.0.0',
    'nbconvert>=4.0',
    'numpydoc>=0.6.0',
    # Required to get SSH connections to remote kernels
    'paramiko>=2.4.0;platform_system=="Windows"',
    'parso>=0.7.0,<0.9.0',
    'pexpect>=4.4.0',
    'pickleshare>=0.4',
    'psutil>=5.3',
    'pygments>=2.0',
    'pylint>=2.5.0,<3.0',
    'pylint-venv>=3.0.2',
    'python-lsp-black>=1.2.0,<3.0.0',
    'pyls-spyder>=0.4.0',
    'pyqt5<5.16',
    'pyqtwebengine<5.16',
    'python-lsp-server[all]>=1.7.2,<1.8.0',
    'pyxdg>=0.26;platform_system=="Linux"',
    'pyzmq>=22.1.0',
    'qdarkstyle>=3.0.2,<3.2.0',
    'qstylizer>=0.2.2',
    'qtawesome>=1.2.1',
    'qtconsole>=5.4.2,<5.5.0',
    'qtpy>=2.1.0',
    'rtree>=0.9.7',
    'setuptools>=49.6.0',
    'sphinx>=0.6.6',
    'spyder-kernels>=3.0.0b1,<3.0.0b2',
    'textdistance>=4.2.0',
    'three-merge>=0.1.1',
    'watchdog>=0.10.3'
]

# Loosen constraints to ensure dev versions still work
if 'dev' in __version__:
    reqs_to_loosen = {'python-lsp-server[all]', 'qtconsole', 'spyder-kernels'}
    install_requires = [req for req in install_requires
                        if req.split(">")[0] not in reqs_to_loosen]
    install_requires.append('python-lsp-server[all]>=1.7.2,<1.9.0')
    install_requires.append('qtconsole>=5.4.2,<5.6.0')
    install_requires.append('spyder-kernels>=3.0.0b1,<3.1.0')

extras_require = {
    'test:platform_system == "Windows"': ['pywin32'],
    'test': [
        'coverage',
        'cython',
        'flaky',
        'matplotlib',
        'pandas',
        'pillow',
        'pytest<7.0',
        'pytest-cov',
        'pytest-lazy-fixture',
        'pytest-mock',
        'pytest-order',
        'pytest-qt',
        'pytest-timeout',
        'pyyaml',
        'scipy',
        'sympy',
    ],
}


spyder_plugins_entry_points = [
    'appearance = spyder.plugins.appearance.plugin:Appearance',
    'application = spyder.plugins.application.plugin:Application',
    'breakpoints = spyder.plugins.breakpoints.plugin:Breakpoints',
    'completions = spyder.plugins.completion.plugin:CompletionPlugin',
    'debugger = spyder.plugins.debugger.plugin:Debugger',
    'editor = spyder.plugins.editor.plugin:Editor',
    'explorer = spyder.plugins.explorer.plugin:Explorer',
    'external_console = spyder.plugins.externalconsole.plugin:ExternalConsole',
    'find_in_files = spyder.plugins.findinfiles.plugin:FindInFiles',
    'help = spyder.plugins.help.plugin:Help',
    'historylog = spyder.plugins.history.plugin:HistoryLog',
    'internal_console = spyder.plugins.console.plugin:Console',
    'ipython_console = spyder.plugins.ipythonconsole.plugin:IPythonConsole',
    'layout = spyder.plugins.layout.plugin:Layout',
    'main_interpreter = spyder.plugins.maininterpreter.plugin:MainInterpreter',
    'mainmenu = spyder.plugins.mainmenu.plugin:MainMenu',
    'onlinehelp = spyder.plugins.onlinehelp.plugin:OnlineHelp',
    'outline_explorer = spyder.plugins.outlineexplorer.plugin:OutlineExplorer',
    'plots = spyder.plugins.plots.plugin:Plots',
    'preferences = spyder.plugins.preferences.plugin:Preferences',
    'profiler = spyder.plugins.profiler.plugin:Profiler',
    'project_explorer = spyder.plugins.projects.plugin:Projects',
    'pylint = spyder.plugins.pylint.plugin:Pylint',
    'pythonpath_manager = spyder.plugins.pythonpath.plugin:PythonpathManager',
    'run = spyder.plugins.run.plugin:Run',
    'shortcuts = spyder.plugins.shortcuts.plugin:Shortcuts',
    'statusbar = spyder.plugins.statusbar.plugin:StatusBar',
    'switcher = spyder.plugins.switcher.plugin:Switcher',
    'toolbar = spyder.plugins.toolbar.plugin:Toolbar',
    'tours = spyder.plugins.tours.plugin:Tours',
    'variable_explorer = spyder.plugins.variableexplorer.plugin:VariableExplorer',
    'workingdir = spyder.plugins.workingdirectory.plugin:WorkingDirectory',
]

spyder_completions_entry_points = [
    ('fallback = spyder.plugins.completion.providers.fallback.provider:'
     'FallbackProvider'),
    ('snippets = spyder.plugins.completion.providers.snippets.provider:'
     'SnippetsProvider'),
    ('lsp = spyder.plugins.completion.providers.languageserver.provider:'
     'LanguageServerProvider'),
]


setup_args['install_requires'] = install_requires
setup_args['extras_require'] = extras_require
setup_args['entry_points'] = {
    'gui_scripts': [
            'spyder = spyder.app.start:main'
    ],
    'spyder.plugins': spyder_plugins_entry_points,
    'spyder.completions': spyder_completions_entry_points
}
setup_args.pop('scripts', None)


# =============================================================================
# Main setup
# =============================================================================
setup(**setup_args)
