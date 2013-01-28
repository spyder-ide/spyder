# -*- coding: utf-8 -*-
#
# Copyright © 2012 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Create a stand-alone Mac OS X app using py2app

To be used like this:
$ python create_app.py py2app
"""

from setuptools import setup

from distutils.sysconfig import get_python_lib
import fileinput
import inspect
import shutil
import os
import os.path as osp
import subprocess
import sys

from IPython.core.completerlib import module_list
from spyderlib.utils.programs import find_program
from spyderlib import __version__ as spy_version

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

def change_interpreter(program):
    """
    Change the interpreter path of the Python scripts included in the app.
    This assumes Spyder was properly installed in Applications
    """
    for line in fileinput.input(program, inplace=True):
        if line.startswith('#!'):
            interpreter_path = osp.join('/Applications', 'Spyder.app',
                                        'Contents', 'MacOs', 'python')
            print '#!' + interpreter_path
        else:
            print line,

#==============================================================================
# App creation
#==============================================================================

shutil.copyfile('scripts/spyder', 'Spyder.py')

APP = ['Spyder.py']
DEPS = ['pylint', 'logilab_astng', 'logilab_common', 'pep8', 'setuptools']
EXCLUDES = DEPS + ['mercurial', 'nose']
PACKAGES = ['spyderlib', 'spyderplugins', 'sphinx', 'jinja2', 'docutils',
            'IPython', 'zmq', 'pygments', 'rope', 'distutils', 'PIL', 'PyQt4',
            'sklearn', 'skimage', 'pandas', 'sympy', 'mpmath', 'statsmodels']
INCLUDES = get_stdlib_modules()

OPTIONS = {
    'argv_emulation': True,
    'compressed' : False,
    'optimize': 1,
    'packages': PACKAGES,
    'includes': INCLUDES,
    'excludes': EXCLUDES,
    'plist': {'CFBundleIdentifier': 'org.spyder-ide',
              'CFBundleShortVersionString': spy_version},
    'iconfile': 'img_src/spyder.icns'
}

setup(
    app=APP,
    options={'py2app': OPTIONS}
)

os.remove('Spyder.py')

#==============================================================================
# Post-app creation
#==============================================================================

# Main paths
resources = 'dist/Spyder.app/Contents/Resources'
system_python_lib = get_python_lib()
app_python_lib = osp.join(resources, 'lib', 'python2.7')

# Uncompress the app site-packages to have code completion on import
# statements
zip_file = app_python_lib + osp.sep + 'site-packages.zip'
subprocess.call(['unzip', zip_file, '-d',
                 osp.join(app_python_lib, 'site-packages')])
os.remove(zip_file)

# Add our docs to the app
docs = osp.join(system_python_lib, 'spyderlib', 'doc')
docs_dest = osp.join(app_python_lib, 'spyderlib', 'doc')
shutil.copytree(docs, docs_dest)

# Add necessary Python programs to the app
PROGRAMS = ['pylint', 'pep8']
system_progs = [find_program(p) for p in PROGRAMS]
progs_dest = [resources + osp.sep + p for p in PROGRAMS]
for i in range(len(PROGRAMS)):
    shutil.copy2(system_progs[i], progs_dest[i])

# Change PROGRAMS interpreter path to use the one shipped
# with the app
for pd in progs_dest:
    change_interpreter(pd)

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

# Hack to make pep8 work inside the app
pep8_egg = filter(lambda d: d.startswith('pep8'), deps)[0]
pep8_script = osp.join(app_python_lib, pep8_egg, 'pep8.py')
for line in fileinput.input(pep8_script, inplace=True):
    if line.strip().startswith('codes = ERRORCODE_REGEX.findall'):
        print "            codes = ERRORCODE_REGEX.findall(function.__doc__ or 'W000')"
    else:
        print line,

# Function to change the interpreter of PROGRAMS if the app
# is ran outside Applications
# (to be added to __boot.py__)
change_interpreter = \
"""
PROGRAMS = %s

def _change_interpreter(program):
    import fileinput
    try:
        for line in fileinput.input(program, inplace=True):
           if line.startswith('#!'):
               l = len('Spyder')
               interpreter_path = os.environ['EXECUTABLEPATH'][:-l] + 'python'
               print '#!' + interpreter_path
           else:
               print line,
    except:
        pass

for p in PROGRAMS:
    _change_interpreter(p)
""" % str(PROGRAMS)

# Add RESOURCEPATH to PATH, so that Spyder can find PROGRAMS inside the app
new_path = "os.environ['PATH'] += os.pathsep + os.environ['RESOURCEPATH']\n"

# Add IPYTHONDIR to the app env because it seems IPython gets confused
# about its location when running inside the app
ip_dir = \
"""
from IPython.utils.path import get_ipython_dir
os.environ['IPYTHONDIR'] = get_ipython_dir()
"""

# Add our modifications to __boot__.py so that they can be taken into
# account when the app is started
run_cmd = "_run('Spyder.py')"
boot = 'dist/Spyder.app/Contents/Resources/__boot__.py'
for line in fileinput.input(boot, inplace=True):
    if line.startswith(run_cmd):
        print change_interpreter
        print new_path
        print ip_dir
        print run_cmd
    else:
        print line,

# Run macdeployqt so that the app can use the internal Qt Framework
subprocess.call(['macdeployqt', 'dist/Spyder.app'])
