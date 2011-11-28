# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""SCM utilities"""

import os
import os.path as osp

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils import programs


SCM_INFOS = {
             '.hg':  dict(name="Mercurial",
                          commit=( ('thg', ['commit']),
                                   ('hgtk', ['commit']) ),
                          browse=( ('thg', ['log']),
                                   ('hgtk', ['log']) )
                          ),
             '.git': dict(name="git",
                          commit=( ('gitk', []), ),
                          browse=( ('git', ['gui']) )
                          ),
             }


def get_scm_infos(path):
    """Return SCM infos if path is a supported SCM repository"""
    for dirname, infos in SCM_INFOS.iteritems():
        scm_path = osp.join(path, dirname)
        if osp.isdir(scm_path):
            return infos


def abspardir(path):
    """Return absolute parent dir"""
    return osp.abspath(osp.join(path, os.pardir))


def get_scm_root(path):
    """Return SCM root directory path
    Return None if path is not within a supported SCM repository"""
    previous_path = path
    while get_scm_infos(path) is None:
        path = abspardir(path)
        if path == previous_path:
            return
        else:
            previous_path = path
    return osp.abspath(path)


def is_scm_repository(path):
    """Return True if path is a supported SCM repository"""
    return get_scm_root(path) is not None


def run_scm_tool(path, tool):
    """If path is a valid SCM repository, run the corresponding SCM tool
    Supported SCM tools: 'commit', 'browse'
    Return False if the SCM tool is not installed"""
    infos = get_scm_infos(get_scm_root(path))
    for name, args in infos[tool]:
        if programs.find_program(name):
            programs.run_program(name, args, cwd=path)
            return
    else:
        raise RuntimeError(_("Please install the %s tool named '%s'")
                           % (infos['name'], name))


if __name__ == '__main__':
    print get_scm_root(osp.dirname(__file__))
    print get_scm_root(r'D:\Python\ipython\IPython\frontend')
    run_scm_tool(r'D:\Python\userconfig\userconfig', 'commit')
