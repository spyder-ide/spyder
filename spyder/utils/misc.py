# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Miscellaneous utilities"""

import functools
import logging
import os
import os.path as osp
import re
import sys
import stat
import socket

from spyder.config.base import get_home_dir


logger = logging.getLogger(__name__)


def __remove_pyc_pyo(fname):
    """Eventually remove .pyc and .pyo files associated to a Python script"""
    if osp.splitext(fname)[1] == '.py':
        for ending in ('c', 'o'):
            if osp.exists(fname + ending):
                os.remove(fname + ending)


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
            sock.bind(("127.0.0.1", default_port))
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
        extensions = ['.py', '.pyw', '.ipy', '.enaml', '.c', '.h', '.cpp',
                      '.hpp', '.inc', '.', '.hh', '.hxx', '.cc', '.cxx',
                      '.cl', '.f', '.for', '.f77', '.f90', '.f95', '.f2k',
                      '.f03', '.f08']
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
        path = path.replace('/\'', '\\\'')
    return path


def get_error_match(text):
    """Check if text contains a Python error."""
    # For regular Python tracebacks and IPython 7 or less.
    match_python = re.match(r'  File "(.*)", line (\d*)', text)
    if match_python is not None:
        return match_python

    # For IPython 8+ tracebacks.
    # Fixes spyder-ide/spyder#20407
    ipython8_match = re.match(r'  File (.*):(\d*)', text)
    if ipython8_match is not None:
        return ipython8_match

    return False


def get_python_executable():
    """Return path to Spyder Python executable"""
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
                if not osp.isdir(osp.join(common, path[len(common) + 1:])):
                    # `common` is not the real common prefix
                    return abspardir(common)
            else:
                return osp.abspath(common)


def memoize(obj):
    """
    Memoize objects to trade memory for execution speed

    Use a limited size cache to store the value, which takes into account
    The calling args and kwargs

    See https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        # only keep the most recent 100 entries
        if len(cache) > 100:
            cache.popitem(last=False)
        return cache[key]
    return memoizer


def getcwd_or_home():
    """Safe version of getcwd that will fallback to home user dir.

    This will catch the error raised when the current working directory
    was removed for an external program.
    """
    try:
        return os.getcwd()
    except OSError:
        logger.debug("WARNING: Current working directory was deleted, "
                     "falling back to home dirertory")
        return get_home_dir()


def regexp_error_msg(pattern):
    """
    Return None if the pattern is a valid regular expression or
    a string describing why the pattern is invalid.
    """
    try:
        re.compile(pattern)
    except re.error as e:
        return str(e)
    return None


def check_connection_port(address, port):
    """Verify if `port` is available in `address`."""
    # Create a TCP socket
    s = socket.socket()
    s.settimeout(2)
    logger.debug("Attempting to connect to {} on port {}".format(
                 address, port))
    try:
        s.connect((address, port))
        logger.debug("Connected to {} on port {}".format(address, port))
        return True
    except socket.error as e:
        logger.debug("Connection to {} on port {} failed: {}".format(
                     address, port, e))
        return False
    finally:
        s.close()
