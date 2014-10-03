# -*- coding: utf-8 -*-
#
# Copyright © 2012 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Create a stand-alone Mac OS X app using py2app

To be used like this:
$ python setup.py build_doc     (to update the docs)
$ python create_app.py py2app   (to build the app)
"""

from __future__ import print_function

from setuptools import setup

from distutils.sysconfig import get_python_lib, get_config_var
import fileinput
import shutil
import os
import os.path as osp
import subprocess
import sys

from IPython.core.completerlib import module_list

from spyderlib import __version__ as spy_version
from spyderlib.config import EDIT_EXT
from spyderlib.utils.programs import find_program


PY2 = sys.version[0] == '2'

#==============================================================================
# Auxiliary functions
#==============================================================================

def get_stdlib_modules():
    """
    Returns a list containing the names of all the modules available in the
    standard library.
    
    Based on the function get_root_modules from the IPython project.
    Present in IPython.core.completerlib in v0.13.1
    
    Copyright (C) 2010-2011 The IPython Development Team.
    Distributed under the terms of the BSD License.
    """
    modules = list(sys.builtin_module_names)
    for path in sys.path[1:]:
        if 'site-packages' not in path:
            modules += module_list(path)
    
    modules = set(modules)
    if '__init__' in modules:
        modules.remove('__init__')
    modules = list(modules)
    return modules

#==============================================================================
# App creation
#==============================================================================

shutil.copyfile('scripts/spyder', 'Spyder.py')

APP = ['Spyder.py']
DEPS = ['pylint', 'logilab', 'astroid', 'pep8', 'setuptools']
EXCLUDES = DEPS + ['mercurial']
PACKAGES = ['spyderlib', 'spyderplugins', 'sphinx', 'jinja2', 'docutils',
            'IPython', 'zmq', 'pygments', 'rope', 'distutils', 'PIL', 'PyQt4',
            'sklearn', 'skimage', 'pandas', 'sympy', 'pyflakes', 'psutil',
            'mpl_toolkits', 'nose']
if PY2:
    PACKAGES.append('statsmodels')
INCLUDES = get_stdlib_modules()
EDIT_EXT = [ext[1:] for ext in EDIT_EXT]

OPTIONS = {
    'argv_emulation': True,
    'compressed' : False,
    'optimize': 0,
    'packages': PACKAGES,
    'includes': INCLUDES,
    'excludes': EXCLUDES,
    'iconfile': 'img_src/spyder.icns',
    'plist': {'CFBundleDocumentTypes': [{'CFBundleTypeExtensions': EDIT_EXT,
                                         'CFBundleTypeName': 'Text File',
                                         'CFBundleTypeRole': 'Editor'}],
              'CFBundleIdentifier': 'org.spyder-ide',
              'CFBundleShortVersionString': spy_version}
}

setup(
    app=APP,
    options={'py2app': OPTIONS}
)

os.remove('Spyder.py')

#==============================================================================
# Post-app creation
#==============================================================================

# Python version
py_ver = '%s.%s' % (sys.version[0], sys.version[2])

# Main paths
resources = 'dist/Spyder.app/Contents/Resources'
system_python_lib = get_python_lib()
app_python_lib = osp.join(resources, 'lib', 'python%s' % py_ver)

# Add our docs to the app
docs_orig = 'build/lib/spyderlib/doc'
docs_dest = osp.join(app_python_lib, 'spyderlib', 'doc')
shutil.copytree(docs_orig, docs_dest)

# Create a minimal library inside Resources to add it to PYTHONPATH instead of
# app_python_lib. This must be done when the user changes to an interpreter
# that's not the one that comes with the app, to forbid importing modules
# inside the app.
minimal_lib = osp.join(app_python_lib, 'minimal-lib')
os.mkdir(minimal_lib)
minlib_pkgs = ['spyderlib', 'spyderplugins']
for p in minlib_pkgs:
    shutil.copytree(osp.join(app_python_lib, p), osp.join(minimal_lib, p))

# Add necessary Python programs to the app
PROGRAMS = ['pylint', 'pep8']
system_progs = [find_program(p) for p in PROGRAMS]
progs_dest = [resources + osp.sep + p for p in PROGRAMS]
for i in range(len(PROGRAMS)):
    shutil.copy2(system_progs[i], progs_dest[i])

# Add deps needed for PROGRAMS to the app
deps = []
for package in os.listdir(system_python_lib):
    for d in DEPS:
        if package.startswith(d):
            deps.append(package)

for i in deps:
    if osp.isdir(osp.join(system_python_lib, i)):
        shutil.copytree(osp.join(system_python_lib, i),
                        osp.join(app_python_lib, i))
    else:
        shutil.copy2(osp.join(system_python_lib, i),
                     osp.join(app_python_lib, i))

# Function to adjust the interpreter used by PROGRAMS
# (to be added to __boot.py__)
change_interpreter = \
"""
PROGRAMS = %s

def _change_interpreter(program):
    import fileinput
    import sys
    try:
        for line in fileinput.input(program, inplace=True):
            if line.startswith('#!'):
                print('#!' + sys.executable)
            else:
                print(line)
    except:
        pass

for p in PROGRAMS:
    _change_interpreter(p)
""" % str(PROGRAMS)

# Add RESOURCEPATH to PATH, so that Spyder can find PROGRAMS inside the app
new_path = \
"""
old_path = os.environ['PATH']
os.environ['PATH'] = os.environ['RESOURCEPATH'] + os.pathsep + old_path
"""

# Add IPYTHONDIR to the app env because it seems IPython gets confused
# about its location when running inside the app
ip_dir = \
"""
from IPython.utils.path import get_ipython_dir
os.environ['IPYTHONDIR'] = get_ipython_dir()
"""

# Add a way to grab environment variables inside the app.
# Thanks a lot to Ryan Clary for posting it here
# https://groups.google.com/forum/?fromgroups=#!topic/spyderlib/lCXOYk-FSWI
get_env = \
r"""
def _get_env():
    import os
    import os.path as osp
    import subprocess as sp
    user_profile = os.getenv('HOME') + osp.sep + '.profile'
    global_profile = '/etc/profile'
    if osp.isfile(global_profile) and not osp.isfile(user_profile):
        envstr = sp.Popen('source /etc/profile; printenv',
                          shell=True, stdout=sp.PIPE).communicate()[0]
    elif osp.isfile(global_profile) and osp.isfile(user_profile):
        envstr = sp.Popen('source /etc/profile; source ~/.profile; printenv',
                          shell=True, stdout=sp.PIPE).communicate()[0]
    else:
        envstr = sp.Popen('printenv', shell=True,
                          stdout=sp.PIPE).communicate()[0]
    env = [a.split('=') for a in envstr.decode().strip().split('\n')]
    os.environ.update(env)
try:
    _get_env()
except:
    print('Cannot grab environment variables!')
"""

# Add our modifications to __boot__.py so that they can be taken into
# account when the app is started
boot_file = 'dist/Spyder.app/Contents/Resources/__boot__.py'
reset_line = "_reset_sys_path()"
run_line = "_run()"
for line in fileinput.input(boot_file, inplace=True):
    if line.startswith(reset_line):
        print(reset_line)
        print(get_env)
    elif line.startswith(run_line):
        print(change_interpreter)
        print(new_path)
        print(ip_dir)
        print(run_line)
    else:
        print(line, end='')

# To use the app's own Qt framework
subprocess.call(['macdeployqt', 'dist/Spyder.app'])

# Workaround for what appears to be a bug with py2app and Homebrew
# See https://bitbucket.org/ronaldoussoren/py2app/issue/26#comment-2092445
PF_dir = get_config_var('PYTHONFRAMEWORKINSTALLDIR')
if not PY2:
    PF_dir = osp.join(PF_dir, 'Versions', py_ver)
app_python_interpreter = 'dist/Spyder.app/Contents/MacOS/python'
shutil.copyfile(osp.join(PF_dir, 'Resources/Python.app/Contents/MacOS/Python'),
                app_python_interpreter)
exec_path = '@executable_path/../Frameworks/Python.framework/Versions/%s/Python' % py_ver
subprocess.call(['install_name_tool', '-change', osp.join(sys.prefix, 'Python'),
                 exec_path, app_python_interpreter])
