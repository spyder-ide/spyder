# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Miscellaneous utilities"""

from __future__ import with_statement
import os
import os.path as osp
import shutil
import sys


def __remove_pyc_pyo(fname):
    """Eventually remove .pyc and .pyo files associated to a Python script"""
    if osp.splitext(fname)[1] == '.py':
        for ending in ('c', 'o'):
            if osp.exists(fname+ending):
                os.remove(fname+ending)

def rename_file(source, dest):
    """
    Rename file from *source* to *dest*
    If file is a Python script, also rename .pyc and .pyo files if any
    """
    os.rename(source, dest)
    __remove_pyc_pyo(source)

def remove_file(fname):
    """
    Remove file *fname*
    If file is a Python script, also rename .pyc and .pyo files if any
    """
    os.remove(fname)
    __remove_pyc_pyo(fname)

def move_file(source, dest):
    """
    Move file from *source* to *dest*
    If file is a Python script, also rename .pyc and .pyo files if any
    """
    shutil.copy(source, dest)
    remove_file(source)


def select_port(default_port=20128):
    """Find and return a non used port"""
    import socket
    while True:
        try:
            sock = socket.socket(socket.AF_INET,
                                 socket.SOCK_STREAM,
                                 socket.IPPROTO_TCP)
#            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind( ("127.0.0.1", default_port) )
        except socket.error, _msg:
            default_port += 1
        else:
            break
        finally:
            sock.close()
            sock = None
    return default_port


def count_lines(path, extensions=None, excluded_dirnames=None):
    """Return number of source code lines for all filenames in subdirectories
    of *path* with names ending with *extensions*
    Directory names *excluded_dirnames* will be ignored"""
    if extensions is None:
        extensions = ['.py', '.pyw', '.ipy', '.c', '.h', '.cpp', '.hpp',
                      '.inc', '.', '.hh', '.hxx', '.cc', '.cxx', '.cl',
                      '.f', '.for', '.f77', '.f90', '.f95', '.f2k']
    if excluded_dirnames is None:
        excluded_dirnames = ['build', 'dist', '.hg', '.svn']
    def get_filelines(path):
        dfiles, dlines = 0, 0
        if osp.splitext(path)[1] in extensions:
            dfiles = 1
            with open(path, 'rb') as textfile:
                dlines = len(textfile.read().strip().splitlines())
        return dfiles, dlines
    lines = 0
    files = 0
    if osp.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for d in dirnames[:]:
                if d in excluded_dirnames:
                    dirnames.remove(d)
            if excluded_dirnames is None or \
               osp.dirname(dirpath) not in excluded_dirnames:
                for fname in filenames:
                    dfiles, dlines = get_filelines(osp.join(dirpath, fname))
                    files += dfiles
                    lines += dlines
    else:
        dfiles, dlines = get_filelines(path)
        files += dfiles
        lines += dlines
    return files, lines


def fix_reference_name(name, blacklist=None):
    """Return a syntax-valid Python reference name from an arbitrary name"""
    import re
    name = "".join(re.split(r'[^0-9a-zA-Z_]', name))
    while name and not re.match(r'([a-zA-Z]+[0-9a-zA-Z_]*)$', name):
        if not re.match(r'[a-zA-Z]', name[0]):
            name = name[1:]
            continue
    name = str(name.lower())
    if not name:
        name = "data"
    if blacklist is not None and name in blacklist:
        get_new_name = lambda index: name+('%03d' % index)
        index = 0
        while get_new_name(index) in blacklist:
            index += 1
        name = get_new_name(index)
    return name


def remove_trailing_single_backslash(text):
    """Remove trailing single backslash in *text*
    
    This is especially useful when formatting path strings on 
    Windows platforms for which folder paths may end with such 
    a character"""
    if text.endswith('\\') and not text.endswith('\\\\'):
        text = text[:-1]
    return text


def get_error_match(text):
    """Return error match"""
    import re
    return re.match(r'  File "(.*)", line (\d*)', text)


def get_python_executable():
    """Return path to Python executable"""
    executable = sys.executable.replace("pythonw.exe", "python.exe")
    if executable.endswith("spyder.exe"):
        # py2exe distribution
        executable = "python.exe"
    return executable


def abspardir(path):
    """Return absolute parent dir"""
    return osp.abspath(osp.join(path, os.pardir))


def get_common_path(pathlist):
    """Return common path for all paths in pathlist"""
    common = osp.normpath(osp.commonprefix(pathlist))
    if len(common) > 1:
        if not osp.isdir(common):
            return abspardir(common)
        else:
            for path in pathlist:
                if not osp.isdir(osp.join(common, path[len(common)+1:])):
                    # `common` is not the real common prefix
                    return abspardir(common)
            else:
                return osp.abspath(common)

if __name__ == '__main__':
    assert get_common_path([
                            'D:\\Python\\spyder-v21\\spyderlib\\widgets',
                            u'D:\\Python\\spyder\\spyderlib\\utils',
                            u'D:\\Python\\spyder\\spyderlib\\widgets',
                            'D:\\Python\\spyder-v21\\spyderlib\\utils',
                            ]) == 'D:\\Python'
