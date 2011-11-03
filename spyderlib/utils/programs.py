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
        extensions = ('.exe', '.bat', '.cmd')
        if not basename.endswith(extensions):
            names = [basename+ext for ext in extensions]+[basename]
    for name in names:
        path = is_program_installed(name)
        if path:
            return path


def run_program(name, args=[], cwd=None):
    """Run program in a separate process"""
    assert isinstance(args, (tuple, list))
    path = find_program(name)
    if not path:
        raise RuntimeError("Program %s was not found" % name)
    subprocess.Popen([path]+args, cwd=cwd)


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


def get_python_args(fname, python_args, interact, debug, end_args):
    """Construct Python interpreter arguments"""
    p_args = []
    if python_args is not None:
        p_args += python_args.split()
    if interact:
        p_args.append('-i')
    if debug:
        p_args.extend(['-m', 'pdb'])
    if os.name == 'nt' and debug:
        # When calling pdb on Windows, one has to replace backslashes by
        # slashes to avoid confusion with escape characters (otherwise, 
        # for example, '\t' will be interpreted as a tabulation):
        p_args.append(osp.normpath(fname).replace(os.sep, '/'))
    else:
        p_args.append(fname)
    if end_args:
        p_args.extend(split_clo(end_args))
    return p_args


def run_python_script_in_terminal(fname, wdir, args, interact,
                                  debug, python_args):
    """Run Python script in an external system terminal"""
    p_args = ['python']
    p_args += get_python_args(fname, python_args, interact, debug, args)
    if os.name == 'nt':
        subprocess.Popen('start cmd.exe /c ' + ' '.join(p_args),
                         shell=True, cwd=wdir)
    elif os.name == 'posix':
        cmd = 'gnome-terminal'
        if is_program_installed(cmd):
            run_program(cmd, ['-x'] + p_args, cwd=wdir)
            return
        cmd = 'konsole'
        if is_program_installed(cmd):
            run_program(cmd, ['-e'] + p_args, cwd=wdir)
            return
    else:
        raise NotImplementedError


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
