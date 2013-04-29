# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Utilities for version control systems"""

import os.path as osp
import subprocess

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils import programs
from spyderlib.utils.misc import abspardir


VCS_INFOS = {
             '.hg':  dict(name="Mercurial",
                          commit=( ('thg', ['commit']),
                                   ('hgtk', ['commit']) ),
                          browse=( ('thg', ['log']),
                                   ('hgtk', ['log']) )
                          ),
             '.git': dict(name="git",
                          commit=( ('git', ['gui']), ),
                          browse=( ('gitk', []), )
                          ),
             }


def get_vcs_infos(path):
    """Return VCS infos if path is a supported VCS repository"""
    for dirname, infos in VCS_INFOS.iteritems():
        vcs_path = osp.join(path, dirname)
        if osp.isdir(vcs_path):
            return infos


def get_vcs_root(path):
    """Return VCS root directory path
    Return None if path is not within a supported VCS repository"""
    previous_path = path
    while get_vcs_infos(path) is None:
        path = abspardir(path)
        if path == previous_path:
            return
        else:
            previous_path = path
    return osp.abspath(path)


def is_vcs_repository(path):
    """Return True if path is a supported VCS repository"""
    return get_vcs_root(path) is not None


def run_vcs_tool(path, tool):
    """If path is a valid VCS repository, run the corresponding VCS tool
    Supported VCS tools: 'commit', 'browse'
    Return False if the VCS tool is not installed"""
    infos = get_vcs_infos(get_vcs_root(path))
    for name, args in infos[tool]:
        if programs.find_program(name):
            programs.run_program(name, args, cwd=path)
            return
    else:
        raise RuntimeError(_("For %s support, please install one of the<br/> "
                             "following tools:<br/><br/>  %s")
                           % (infos['name'],
                              ', '.join([name for name,cmd in infos['commit']])
                              ))


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
        output = subprocess.Popen([hg, 'id', '-nib', repopath],
                                  stdout=subprocess.PIPE).communicate()[0]
        # output is now: ('eba7273c69df+ 2015+ default\n', None)
        return tuple(output.strip().split())
    except (subprocess.CalledProcessError, AssertionError, AttributeError):
        # print("Error: Failed to get revision number from Mercurial - %s" % exc)
        return (None, None, None)


if __name__ == '__main__':
    print get_vcs_root(osp.dirname(__file__))
    print get_vcs_root(r'D:\Python\ipython\IPython\frontend')
    #run_vcs_tool(r'D:\Python\userconfig\userconfig', 'commit')
    print get_hg_revision(osp.dirname(__file__)+"/../..")
    print get_hg_revision('/')
