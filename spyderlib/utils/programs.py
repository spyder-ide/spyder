# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Running programs utilities
"""

import os, sys, subprocess, imp, os.path as osp


def get_nt_program_name(name):
    """Return Windows-specific program name, i.e. adding '.bat' or '.exe'"""
    if os.name == 'nt':
        for ext in ('.exe', '.bat'):
            if is_program_installed(name+ext):
                return name+ext
    return name

def is_program_installed(basename, get_path=False):
    """Return True if program is installed and present in PATH"""
    for path in os.environ["PATH"].split(os.pathsep):
        abspath = osp.join(path, basename)
        if osp.isfile(abspath):
            if get_path:
                return abspath
            else:
                return True
    else:
        return False
    
def run_program(name, args=[]):
    """Run program in a separate process"""
    assert isinstance(args, (tuple, list))
    path = is_program_installed(name, get_path=True)
    if not path:
        raise RuntimeError("Program %s was not found" % name)
    subprocess.Popen([path]+args)
    
def python_script_exists(package=None, module=None, get_path=False):
    """
    Return True if Python script exists
    package=None -> module is in sys.path (standard library modules)
    """
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
        if get_path:
            return path
        else:
            return True
    
def run_python_script(package=None, module=None, args=[], p_args=[]):
    """
    Run Python script in a separate process
    package=None -> module is in sys.path (standard library modules)
    """
    assert module is not None
    assert isinstance(args, (tuple, list)) and isinstance(p_args, (tuple, list))
    path = python_script_exists(package, module, get_path=True)
    subprocess.Popen([sys.executable]+p_args+[path]+args)

def is_module_installed(module_name):
    """Return True if module *module_name* is installed"""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False
