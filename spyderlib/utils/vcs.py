# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Utilities for version control systems"""

from __future__ import print_function

import os.path as osp
import subprocess

# Local imports
from spyderlib.utils import programs
from spyderlib.utils.misc import abspardir
from spyderlib.py3compat import PY3


SUPPORTED = [
{
    'name': 'Mercurial',
    'rootdir': '.hg',
    'actions': dict(
        commit=( ('thg', ['commit']),
                 ('hgtk', ['commit']) ),
        browse=( ('thg', ['log']),
                 ('hgtk', ['log']) ))
}, {
    'name': 'Git',
    'rootdir': '.git',
    'actions': dict(
        commit=( ('git', ['gui']), ),
        browse=( ('gitk', []), ))
}]


class ActionToolNotFound(RuntimeError):
    """Exception to transmit information about supported tools for
       failed attempt to execute given action"""
       
    def __init__(self, vcsname, action, tools):
        RuntimeError.__init__(self)
        self.vcsname = vcsname
        self.action = action
        self.tools = tools


def get_vcs_info(path):
    """Return support status dict if path is under VCS root"""
    for info in SUPPORTED:
        vcs_path = osp.join(path, info['rootdir'])
        if osp.isdir(vcs_path):
            return info


def get_vcs_root(path):
    """Return VCS root directory path
    Return None if path is not within a supported VCS repository"""
    previous_path = path
    while get_vcs_info(path) is None:
        path = abspardir(path)
        if path == previous_path:
            return
        else:
            previous_path = path
    return osp.abspath(path)


def is_vcs_repository(path):
    """Return True if path is a supported VCS repository"""
    return get_vcs_root(path) is not None


def run_vcs_tool(path, action):
    """If path is a valid VCS repository, run the corresponding VCS tool
    Supported VCS actions: 'commit', 'browse'
    Return False if the VCS tool is not installed"""
    info = get_vcs_info(get_vcs_root(path))
    tools = info['actions'][action]
    for tool, args in tools:
        if programs.find_program(tool):
            programs.run_program(tool, args, cwd=path)
            return
    else:
        cmdnames = [name for name, args in tools]
        raise ActionToolNotFound(info['name'], action, cmdnames)

def is_hg_installed():
    """Return True if Mercurial is installed"""
    return programs.find_program('hg') is not None


def get_hg_revision(repopath):
    """Return Mercurial revision for the repository located at repopath
       Result is a tuple (global, local, branch), with None values on error
       For example:
           >>> get_hg_revision(".")
           ('eba7273c69df+', '2015+', 'default')
    """
    try:
        hg = programs.find_program('hg')
        assert hg is not None and osp.isdir(osp.join(repopath, '.hg'))
        output, _err = subprocess.Popen([hg, 'id', '-nib', repopath],
                                        stdout=subprocess.PIPE).communicate()
        # output is now: ('eba7273c69df+ 2015+ default\n', None)
        # Split 2 times max to allow spaces in branch names.
        return tuple(output.decode().strip().split(None, 2))
    except (subprocess.CalledProcessError, AssertionError, AttributeError):
        # print("Error: Failed to get revision number from Mercurial - %s" % exc)
        return (None, None, None)


def get_git_revision(repopath):
    """Return Git revision for the repository located at repopath
       Result is the latest commit hash, with None on error
    """
    try:
        git = programs.find_program('git')
        assert git is not None and osp.isdir(osp.join(repopath, '.git'))
        commit = subprocess.Popen([git, 'rev-parse', '--short', 'HEAD'],
                                  stdout=subprocess.PIPE,
                                  cwd=repopath).communicate()
        if PY3:
            commit = str(commit[0][:-1])
            commit = commit[2:-1]
        else:
            commit = commit[0][:-1]
        return commit
    except (subprocess.CalledProcessError, AssertionError, AttributeError):
        return None


if __name__ == '__main__':
    print(get_vcs_root(osp.dirname(__file__)))
    print(get_vcs_root(r'D:\Python\ipython\IPython\kernel'))
    #run_vcs_tool(r'D:\Python\userconfig\userconfig', 'commit')
    print(get_git_revision(osp.dirname(__file__)+"/../.."))
    print(get_git_revision('/'))
