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
            commit=(('thg', ['commit']),
                    ('hgtk', ['commit'])),
            browse=(('thg', ['log']),
                    ('hgtk', ['log'])),
            cstate=(('hg', ['status', '-A']), )
        ),
    }, {
        'name': 'Git',
        'rootdir': '.git',
        'actions': dict(
            commit=(('git', ['gui' if os.name == 'nt' else 'cola']), ),
            browse=(('gitk', []), ),
            cstate=(('git', ['status', '--ignored', '--porcelain']), )
        ),
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
            return None
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


def git_status(out_str, path):
    """Decode git status from the vcs output"""
    vcsst = {}
    for f_string in (x for x in out_str.split("\n") if x):
        status = f_string[:2]
        if "U" in status or status == "AA":
            status = 4
        elif status[1] == " ":
            index = 3
        elif status[1] in "MRC":
            index = 2
        else:
            try:
                index = ["??", "!!"].index(status)
            except ValueError:
                continue
        vcsst[osp.abspath(osp.join(path, f_string[3:]))] = index
    return vcsst


def hg_status(out_str, path):
    """Decode mercurial status from the vcs output"""
    stat = ["?", "I", "M", "A", "U"]
    vcsst = {}
    for f_string in (x for x in out_str.split("\n") if x):
        status = f_string[:1].strip()
        if len(status) > 1:
            status = status[1]
        try:
            index = stat.index(status)
        except ValueError:
            continue
        vcsst[osp.abspath(osp.join(path, f_string[2:]))] = index
    return vcsst


def get_vcs_status(vcs_path):
    """Return the commit status."""
    root_path = get_vcs_root(vcs_path)
    if not root_path:
        # look in subdirectories for repositories
        paths = []
        for subdir in os.listdir(root_path):
            if subdir is not None:
                root_path = get_vcs_root(subdir)
                if root_path:
                    paths.append(root_path)
        if paths == []:
            return []
    else:
        paths = [root_path]
    vcsst = {}
    for path in paths:
        # Status list (in Order): untracked, ignored, modified, added
        tool, args = get_vcs_info(path)['actions']['cstate'][0]
        if programs.find_program(tool):
            proc = programs.run_program(tool, args, cwd=path)
            out, err = proc.communicate()
            if proc.returncode >= 0 and err == b'' and out:
                if tool == 'git':
                    vcsst.update(git_status(out.decode("utf-8")[:-1], path))
                elif tool == 'hg':
                    vcsst.update(hg_status(out.decode("utf-8")[:-1], path))
            else:
                continue
    if vcsst == {}:
        return []
    return vcsst


def get_vcs_file_status(filename):
    """Return the commit status a of a single file"""
    if not is_vcs_repository(filename):
        return 0
    path = get_vcs_root(filename)
    tool, args = get_vcs_info(path)['actions']['cstate'][0]
    if programs.find_program(tool):
        proc = programs.run_program(tool, args + [filename], cwd=path)
        out, err = proc.communicate()
        if proc.returncode >= 0 and err == b'':
            if tool == 'git':
                vcsst = git_status(out.decode("utf-8")[:-1], path)
            elif tool == 'hg':
                vcsst = hg_status(out.decode("utf-8")[:-1], path)
            if vcsst:
                return [vcsst[b] for n, b in enumerate(vcsst)][0]
    return 0


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
