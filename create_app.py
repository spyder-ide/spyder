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
import shutil
import os
import os.path as osp
import sys

from IPython.core.completerlib import module_list
from spyderlib.utils.programs import find_program

#==============================================================================
# Auxiliary functions
#==============================================================================

def get_stdlib_modules():
    """
    Returns a list containing the names of all the modules available in the
    standard library.
    
    Based on the function get_root_modules from the IPython project.
    Present in IPython.core.completerlib
    
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
PYLINT_DEPS = ['pylint', 'logilab_astng', 'logilab_common']
EXCLUDES = PYLINT_DEPS + ['mercurial']
PACKAGES = ['spyderlib', 'spyderplugins', 'sphinx', 'jinja2', 'docutils',
            'IPython', 'zmq', 'pygments']
INCLUDES = get_stdlib_modules()

OPTIONS = {
    'argv_emulation': True,
    'compressed' : False,
    'optimize': 2,
    'packages': PACKAGES,
    'includes': INCLUDES,
    'excludes': EXCLUDES,
    'plist': { 'CFBundleIdentifier': 'org.spyder-ide'},
    'iconfile': 'img_src/spyder.icns',
    'dylib_excludes': ['Qt3Support.framework', 'QtCore.framework',
                       'QtDBus.framework', 'QtDeclarative.framework',
                       'QtDesigner.framework', 'QtDesignerComponents.framework',
                       'QtGui.framework', 'QtHelp.framework',
                       'QtMultimedia.framework', 'QtNetwork.framework',
                       'QtOpenGL.framework', 'QtScript.framework',
                       'QtScriptTools.framework', 'QtSql.framework',
                       'QtSvg.framework', 'QtTest.framework',
                       'QtWebKit.framework', 'QtXml.framework',
                       'QtXmlPatterns.framework', 'phonon.framework']
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

# Add our docs to the app
docs = osp.join(system_python_lib, 'spyderlib', 'doc')
docs_dest = osp.join(app_python_lib, 'spyderlib', 'doc')
shutil.copytree(docs, docs_dest)

# Add pylint executable to the app
system_pylint = find_program('pylint')
pylint_dest = resources + osp.sep + 'pylint'
shutil.copy2(system_pylint, pylint_dest)

# Add pylint deps to the app
deps = []
for package in os.listdir(system_python_lib):
    for pd in PYLINT_DEPS:
        if package.startswith(pd):
            deps.append(package)

for i in deps:
    shutil.copytree(osp.join(system_python_lib, i),
                    osp.join(app_python_lib, i))

# Function to change the pylint interpreter
# (to be added to __boot.py__)
change_pylint_interpreter = \
"""
def _change_pylint_interpreter():
    import fileinput
    for line in fileinput.input('pylint', inplace=True):
        if line.startswith('#!'):
            l = len('Spyder')
            interpreter_path = os.environ['EXECUTABLEPATH'][:-l] + 'python'
            print '#!%s' % interpreter_path
        else:
            print line,
_change_pylint_interpreter()
"""

# Add RESOURCEPATH to PATH, so that Spyder can find pylint inside the app
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
        print change_pylint_interpreter
        print new_path + ip_dir + run_cmd
    else:
        print line,
