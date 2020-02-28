# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Utilities for version control systems"""

from __future__ import print_function

import os
import os.path as osp
import subprocess
import sys

# Local imports
from spyder.config.base import running_under_pytest
from spyder.utils import programs
from spyder.utils.misc import abspardir
from spyder.py3compat import PY3


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
        commit=( ('git', ['gui' if os.name == 'nt' else 'cola']), ),
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
            if not running_under_pytest():
                programs.run_program(tool, args, cwd=path)
            else:
                return True
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
        assert osp.isdir(osp.join(repopath, '.hg'))
        proc = programs.run_program('hg', ['id', '-nib', repopath])
        output, _err = proc.communicate()
        # output is now: ('eba7273c69df+ 2015+ default\n', None)
        # Split 2 times max to allow spaces in branch names.
        return tuple(output.decode().strip().split(None, 2))
    except (subprocess.CalledProcessError, AssertionError, AttributeError,
            OSError):
        return (None, None, None)


def get_git_revision(repopath):
    """
    Return Git revision for the repository located at repopath

    Result is a tuple (latest commit hash, branch), with None values on
    error
    """
    try:
        git = programs.find_program('git')
        assert git is not None and osp.isdir(osp.join(repopath, '.git'))
        commit = programs.run_program(git, ['rev-parse', '--short', 'HEAD'],
                                      cwd=repopath).communicate()
        commit = commit[0].strip()
        if PY3:
            commit = commit.decode(sys.getdefaultencoding())

        # Branch
        branches = programs.run_program(git, ['branch'],
                                        cwd=repopath).communicate()
        branches = branches[0]
        if PY3:
            branches = branches.decode(sys.getdefaultencoding())
        branches = branches.split('\n')
        active_branch = [b for b in branches if b.startswith('*')]
        if len(active_branch) != 1:
            branch = None
        else:
            branch = active_branch[0].split(None, 1)[1]

        return commit, branch
    except (subprocess.CalledProcessError, AssertionError, AttributeError,
            OSError):
        return None, None


def get_git_refs(repopath):
    """
    Return Git active branch, state, branches (plus tags).
    """
    tags = []
    branches = []
    branch = ''
    files_modifed = []

    if os.path.isfile(repopath):
        repopath = os.path.dirname(repopath)

    git = programs.find_program('git')

    if git:
        try:
            # Files modified
            out, err = programs.run_program(
                git, ['status', '-s'],
                cwd=repopath,
            ).communicate()

            if PY3:
                out = out.decode(sys.getdefaultencoding())
            files_modifed = [line.strip() for line in out.split('\n') if line]

            # Tags
            out, err = programs.run_program(
                git, ['tag'],
                cwd=repopath,
            ).communicate()

            if PY3:
                out = out.decode(sys.getdefaultencoding())
            tags = [line.strip() for line in out.split('\n') if line]

            # Branches
            out, err = programs.run_program(
                git, ['branch', '-a'],
                cwd=repopath,
            ).communicate()

            if PY3:
                out = out.decode(sys.getdefaultencoding())

            lines = [line.strip() for line in out.split('\n') if line]
            for line in lines:
                if line.startswith('*'):
                    line = line.replace('*', '').strip()
                    branch = line

                branches.append(line)

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass

    return branches + tags, branch, files_modifed


def get_git_remotes(fpath):
    """Return git remotes for repo on fpath."""
    remote_data = {}
    data, __ = programs.run_program(
        'git',
        ['remote', '-v'],
        cwd=osp.dirname(fpath),
    ).communicate()

    if PY3:
        data = data.decode(sys.getdefaultencoding())

    lines = [line.strip() for line in data.split('\n') if line]
    for line in lines:
        if line:
            remote, value = line.split('\t')
            remote_data[remote] = value.split(' ')[0]

    return remote_data


def remote_to_url(remote):
    """Convert a git remote to a url."""
    url = ''
    if remote.startswith('git@'):
        url = remote.replace('git@', '')
        url = url.replace(':', '/')
        url = 'https://' + url.replace('.git', '')
    else:
        url = remote.replace('.git', '')

    return url
