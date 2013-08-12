# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Miscellaneous utilities"""

import os
import os.path as osp
import sys
import stat


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
    import shutil
    shutil.copy(source, dest)
    remove_file(source)


def onerror(function, path, excinfo):
    """Error handler for `shutil.rmtree`.
    
    If the error is due to an access error (read-only file), it 
    attempts to add write permission and then retries.
    If the error is for another reason, it re-raises the error.
    
    Usage: `shutil.rmtree(path, onerror=onerror)"""
    if not os.access(path, os.W_OK):
        # Is the error an access error?
        os.chmod(path, stat.S_IWUSR)
        function(path)
    else:
        raise


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
        except socket.error as _msg:  # analysis:ignore
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
    name = str(name)
    if not name:
        name = "data"
    if blacklist is not None and name in blacklist:
        get_new_name = lambda index: name+('%03d' % index)
        index = 0
        while get_new_name(index) in blacklist:
            index += 1
        name = get_new_name(index)
    return name


def remove_backslashes(path):
    """Remove backslashes in *path*

    For Windows platforms only.
    Returns the path unchanged on other platforms.    
    
    This is especially useful when formatting path strings on 
    Windows platforms for which folder paths may contain backslashes 
    and provoke unicode decoding errors in Python 3 (or in Python 2
    when future 'unicode_literals' symbol has been imported)."""
    if os.name == 'nt':
        # Removing trailing single backslash
        if path.endswith('\\') and not path.endswith('\\\\'):
            path = path[:-1]
        # Replacing backslashes by slashes
        path = path.replace('\\', '/')
    return path


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


def monkeypatch_method(cls, patch_name):
    # This function's code was inspired from the following thread:
    # "[Python-Dev] Monkeypatching idioms -- elegant or ugly?"
    # by Robert Brewer <fumanchu at aminus.org>
    # (Tue Jan 15 19:13:25 CET 2008)
    """
    Add the decorated method to the given class; replace as needed.
    
    If the named method already exists on the given class, it will
    be replaced, and a reference to the old method is created as 
    cls._old<patch_name><name>. If the "_old_<patch_name>_<name>" attribute 
    already exists, KeyError is raised.
    """
    def decorator(func):
        fname = func.__name__
        old_func = getattr(cls, fname, None)
        if old_func is not None:
            # Add the old func to a list of old funcs.
            old_ref = "_old_%s_%s" % (patch_name, fname)
            #print old_ref, old_func
            old_attr = getattr(cls, old_ref, None)
            if old_attr is None:
                setattr(cls, old_ref, old_func)
            else:
                raise KeyError("%s.%s already exists."
                               % (cls.__name__, old_ref))
        setattr(cls, fname, func)
        return func
    return decorator


def is_python_script(fname):
    """Is it a valid Python script?"""
    return osp.isfile(fname) and fname.endswith(('.py', '.pyw', '.ipy'))


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
                            'D:\\Python\\spyder\\spyderlib\\utils',
                            'D:\\Python\\spyder\\spyderlib\\widgets',
                            'D:\\Python\\spyder-v21\\spyderlib\\utils',
                            ]) == 'D:\\Python'
