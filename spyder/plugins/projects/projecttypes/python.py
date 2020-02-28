# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Python project type"""

import os
import os.path as osp

from spyder.config.base import _
from spyder.plugins.projects.projecttypes import EmptyProject


class PythonProject(EmptyProject):
    """Python project."""

    PROJECT_TYPE_NAME = _('Python project')
    IGNORE_FILE = """"""

    def _get_relative_pythonpath(self):
        """Return PYTHONPATH list as relative paths"""
        # Workaround to replace os.path.relpath (new in Python v2.6):
        offset = len(self.root_path)+len(os.pathsep)
        return [path[offset:] for path in self.pythonpath]

    def _set_relative_pythonpath(self, value):
        """Set PYTHONPATH list relative paths"""
        self.pythonpath = [osp.abspath(osp.join(self.root_path, path))
                           for path in value]

    relative_pythonpath = property(_get_relative_pythonpath,
                                   _set_relative_pythonpath)

    # --- Python Path
    def is_in_pythonpath(self, dirname):
        """Return True if dirname is in project's PYTHONPATH"""
        return fixpath(dirname) in [fixpath(_p) for _p in self.pythonpath]

    def get_pythonpath(self):
        """Return a copy of pythonpath attribute"""
        return self.pythonpath[:]

    def set_pythonpath(self, pythonpath):
        """Set project's PYTHONPATH"""
        self.pythonpath = pythonpath
        self.save()

    def remove_from_pythonpath(self, path):
        """Remove path from project's PYTHONPATH
        Return True if path was removed, False if it was not found"""
        pathlist = self.get_pythonpath()
        if path in pathlist:
            pathlist.pop(pathlist.index(path))
            self.set_pythonpath(pathlist)
            return True
        else:
            return False

    def add_to_pythonpath(self, path):
        """Add path to project's PYTHONPATH
        Return True if path was added, False if it was already there"""
        pathlist = self.get_pythonpath()
        if path in pathlist:
            return False
        else:
            pathlist.insert(0, path)
            self.set_pythonpath(pathlist)
            return True


class PythonPackageProject(PythonProject):
    """ """
    PROJECT_TYPE = 'python-package'
    PROJECT_TYPE_NAME = _('Python package')
