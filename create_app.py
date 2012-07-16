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

from spyderlib.utils.programs import find_program

#==============================================================================
# App creation
#==============================================================================

shutil.copyfile('scripts/spyder', 'Spyder.py')

APP = ['Spyder.py']
pylint_deps = ['pylint', 'logilab_astng', 'logilab_common']

OPTIONS = {
    'argv_emulation': True,
    'compressed' : False,
    'optimize': 2,
    'packages': ['spyderlib', 'spyderplugins', 'sphinx', 'jinja2',
                 'docutils', 'IPython', 'zmq', 'pygments'],
    'includes': ['cProfile', 'fileinput'],
    'excludes': pylint_deps + ['mercurial'],
    'plist': { 'CFBundleIdentifier': 'org.spyder-ide'},
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

# Add pylint executable to the app
system_pylint = find_program('pylint')
dest = 'dist/Spyder.app/Contents/Resources/'
pylint_dest = dest + 'pylint'
shutil.copy2(system_pylint, pylint_dest)

# Add pylint deps to the app
sp_dir = get_python_lib() + '/'
system_deps = []
for package in os.listdir(sp_dir):
    for pd in pylint_deps:
        if package.startswith(pd):
            system_deps.append(package)

dest_lib = dest + 'lib/python2.7/'
for i in system_deps:
    shutil.copytree(sp_dir + i, dest_lib + i)

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

# Add our modifications to __boot__.py so that they can be taken into
# account when the app is started
run_cmd = "_run('Spyder.py')"
boot = 'dist/Spyder.app/Contents/Resources/__boot__.py'
for line in fileinput.input(boot, inplace=True):
    if line.startswith(run_cmd):
        print change_pylint_interpreter
        print new_path + run_cmd
    else:
        print line,
