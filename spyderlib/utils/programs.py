# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Running programs utilities"""

import os
import os.path as osp
import sys
import subprocess
import imp


def is_program_installed(basename):
    """Return program absolute path if installed in PATH
    Otherwise, return None"""
    for path in os.environ["PATH"].split(os.pathsep):
        abspath = osp.join(path, basename)
        if osp.isfile(abspath):
            return abspath


def find_program(basename):
    """Find program in PATH and return absolute path
    Try adding .exe or .bat to basename on Windows platforms
    (return None if not found)"""
    names = [basename]
    if os.name == 'nt':
        # Windows platforms
        extensions = ('.exe', '.bat')
        if not basename.endswith(extensions):
            names = [basename+ext for ext in extensions]+[basename]
    for name in names:
        path = is_program_installed(name)
        if path:
            return path


def run_program(name, args=[]):
    """Run program in a separate process"""
    assert isinstance(args, (tuple, list))
    path = is_program_installed(name)
    if not path:
        raise RuntimeError("Program %s was not found" % name)
    subprocess.Popen([path]+args)


def start_file(filename):
    """Generalized os.startfile for all platforms supported by Qt
    (this function is simply wrapping QDesktopServices.openUrl)
    Returns True if successfull, otherwise returns False."""
    from spyderlib.qt.QtGui import QDesktopServices
    from spyderlib.qt.QtCore import QUrl
    url = QUrl()
    url.setPath(filename)
    return QDesktopServices.openUrl(url)


def python_script_exists(package=None, module=None):
    """Return absolute path if Python script exists (otherwise, return None)
    package=None -> module is in sys.path (standard library modules)"""
    assert module is not None
    try:
        if package is None:
            path = imp.find_module(module)[1]
        else:
            path = osp.join(imp.find_module(package)[1], module)+'.py'
    except ImportError:
        return
    if not osp.isfile(path):
        path += 'w'
    if osp.isfile(path):
        return path


def run_python_script(package=None, module=None, args=[], p_args=[]):
    """Run Python script in a separate process
    package=None -> module is in sys.path (standard library modules)"""
    assert module is not None
    assert isinstance(args, (tuple, list)) and isinstance(p_args, (tuple, list))
    path = python_script_exists(package, module)
    subprocess.Popen([sys.executable]+p_args+[path]+args)


def is_module_installed(module_name, version=None):
    """Return True if module *module_name* is installed
    
    If version is not None, checking module version 
    (module must have an attribute named '__version__')"""
    try:
        mod = __import__(module_name)
        if version is None:
            return True
        else:
            return getattr(mod, '__version__').startswith(version)
    except ImportError:
        return False


def split_clo(args):
    """Split command line options without breaking double-quoted strings"""
    assert isinstance(args, basestring)
    out = []
    quoted = False
    for txt in args.split('"'):
        if quoted:
            out.append('"'+txt.strip()+'"')
        else:
            out += txt.strip().split(' ')
        quoted = not quoted
    return out


if __name__ == '__main__':
    print find_program('hg')
    print split_clo('-q -o -a')
    print split_clo('-q "d:\\Python de xxxx\\t.txt" -o -a')
