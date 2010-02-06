# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Running programs utilities
"""

import os, sys, subprocess, imp, os.path as osp


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
    
def run_program(name, args=''):
    """Run program in a separate process"""
    path = is_program_installed(name, get_path=True)
    if not path:
        raise RuntimeError("Program %s was not found" % name)
    command = [path]
    if args:
        command.append(args)
    subprocess.Popen(" ".join(command) )
    
def is_python_gui_script_installed(package, module, get_path=False):
    path = osp.join(imp.find_module(package)[1], module)+'.py'
    if not osp.isfile(path):
        path += 'w'
    if osp.isfile(path):
        if get_path:
            return path
        else:
            return True
    
def run_python_gui_script(package, module, args=''):
    """Run GUI-based Python script in a separate process"""
    path = is_python_gui_script_installed(package, module, get_path=True)
    command = [sys.executable, '"'+path+'"']
    if args:
        command.append(args)
    subprocess.Popen(" ".join(command) )

def is_python_module_installed(module_name):
    """Return True if module *module_name* is installed"""
    try:
        imp.find_module(module_name)
        return True
    except ImportError:
        return False