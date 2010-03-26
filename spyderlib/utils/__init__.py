# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.utils
===============

Spyder's utilities
"""

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
    import os, os.path as osp
    if extensions is None:
        extensions = ['.py', '.pyw', '.c', '.h', '.cpp', '.hpp', '.inc',
                      '.f', '.for', '.f90', '.f77']
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
