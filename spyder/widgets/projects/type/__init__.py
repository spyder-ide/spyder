# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Project types"""

import os
import os.path as osp
from collections import OrderedDict

from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.widgets.projects.config import (ProjectConfig, CODESTYLE,
                                            CODESTYLE_DEFAULTS,
                                            CODESTYLE_VERSION, WORKSPACE,
                                            WORKSPACE_DEFAULTS,
                                            WORKSPACE_VERSION,
                                            ENCODING, ENCODING_DEFAULTS,
                                            ENCODING_VERSION,
                                            VCS, VCS_DEFAULTS, VCS_VERSION)


class BaseProject(object):
    """Spyder base project.

    This base class must not be used directly, but inherited from. It does not
    assume that python is specific to this project.
    """
    PROJECT_FOLDER = '.spyderproject'
    PROJECT_TYPE_NAME = None
    IGNORE_FILE = ""
    CONFIG_SETUP = {WORKSPACE: {'filename': '{0}.ini'.format(WORKSPACE),
                                'defaults': WORKSPACE_DEFAULTS,
                                'version': WORKSPACE_VERSION},
                    CODESTYLE: {'filename': '{0}.ini'.format(CODESTYLE),
                                'defaults': CODESTYLE_DEFAULTS,
                                'version': CODESTYLE_VERSION},
                    ENCODING: {'filename': '{0}.ini'.format(ENCODING),
                               'defaults': ENCODING_DEFAULTS,
                               'version': ENCODING_VERSION},
                    VCS: {'filename': '{0}.ini'.format(VCS),
                          'defaults': VCS_DEFAULTS,
                          'version': VCS_VERSION}
                    }

    def __init__(self, root_path):
        self.name = None
        self.root_path = root_path
        self.open_project_files = []
        self.open_non_project_files = []
        self.config_files = []
        self.CONF = {}

        # Configuration files

        self.related_projects = []  # storing project path, not project objects
#        self.pythonpath = []
        self.opened = True

        self.ioerror_flag = False
        self.create_project_config_files()

    # --- Helpers
    # -------------------------------------------------------------------------
    def set_recent_files(self, recent_files):
        """Set a list of files opened by the project."""
        for recent_file in recent_files[:]:
            if not os.path.isfile(recent_file):
                recent_files.remove(recent_file)
        self.CONF[WORKSPACE].set('main', 'recent_files',
                                 list(OrderedDict.fromkeys(recent_files)))

    def get_recent_files(self):
        """Return a list of files opened by the project."""
        recent_files = self.CONF[WORKSPACE].get('main', 'recent_files',
                                                default=[])
        for recent_file in recent_files[:]:
            if not os.path.isfile(recent_file):
                recent_files.remove(recent_file)
        return list(OrderedDict.fromkeys(recent_files))

    def create_project_config_files(self):
        """ """
        dic = self.CONFIG_SETUP
        for key in dic:
            name = key
            filename = dic[key]['filename']
            defaults = dic[key]['defaults']
            version = dic[key]['version']
            self.CONF[key] = ProjectConfig(name, self.root_path, filename,
                                           defaults=defaults, load=True,
                                           version=version)

    def get_conf_files(self):
        """ """
        return self.CONF

    def add_ignore_lines(self, lines):
        """ """
        text = self.IGNORE_FILE
        for line in lines:
            text += line
        self.IGNORE_FILE = text

    def set_root_path(self, root_path):
        """Set project root path."""
        if self.name is None:
            self.name = osp.basename(root_path)
        self.root_path = to_text_string(root_path)
        config_path = self.__get_project_config_path()
        if osp.exists(config_path):
            self.load()
        else:
            if not osp.isdir(self.root_path):
                os.mkdir(self.root_path)
            self.save()

    def rename(self, new_name):
        """Rename project and rename its root path accordingly."""
        old_name = self.name
        self.name = new_name
        pypath = self.relative_pythonpath  # ??
        self.root_path = self.root_path[:-len(old_name)]+new_name
        self.relative_pythonpath = pypath  # ??
        self.save()

    def __get_project_config_folder(self):
        """Return project configuration folder."""
        return osp.join(self.root_path, self.PROJECT_FOLDER)

    def __get_project_config_path(self):
        """Return project configuration path"""
        return osp.join(self.root_path, self.CONFIG_NAME)

    def load(self):
        """Load project data"""
#        fname = self.__get_project_config_path()
#        try:
#            # Old format (Spyder 2.0-2.1 for Python 2)
#            with open(fname, 'U') as fdesc:
#                data = pickle.loads(fdesc.read())
#        except (pickle.PickleError, TypeError, UnicodeDecodeError,
#                AttributeError):
#            try:
#                # New format (Spyder >=2.2 for Python 2 and Python 3)
#                with open(fname, 'rb') as fdesc:
#                    data = pickle.loads(fdesc.read())
#            except (IOError, OSError, pickle.PickleError):
#                self.ioerror_flag = True
#                return
        # Compatibilty with old project explorer file format:
#        if 'relative_pythonpath' not in data:
#            print("Warning: converting old configuration file "
#                  "for project '%s'" % data['name'], file=STDERR)
#            self.pythonpath = data['pythonpath']
#            data['relative_pythonpath'] = self.relative_pythonpath
#        for attr in self.CONFIG_ATTR:
#            setattr(self, attr, data[attr])
#        self.save()

    def save(self):
        """Save project data"""
#        data = {}
#        for attr in self.PROJECT_ATTR:
#            data[attr] = getattr(self, attr)
#        try:
#            with open(self.__get_project_config_path(), 'wb') as fdesc:
#                pickle.dump(data, fdesc, 2)
#        except (IOError, OSError):
#            self.ioerror_flag = True

#    def delete(self):
#        """Delete project"""
#        os.remove(self.__get_project_config_path())
#
#    # --- Misc.
#    def get_related_projects(self):
#        """Return related projects path list"""
#        return self.related_projects
#
#    def set_related_projects(self, related_projects):
#        """Set related projects"""
#        self.related_projects = related_projects
#        self.save()
#
#    def open(self):
#        """Open project"""
#        self.opened = True
#        self.save()
#
#    def close(self):
#        """Close project"""
#        self.opened = False
#        self.save()
#
#    def is_opened(self):
#        """Return True if project is opened"""
#        return self.opened
#
#    def is_file_in_project(self, fname):
#        """Return True if file *fname* is in one of the project subfolders"""
#        fixed_root = fixpath(self.root_path)
#        return fixpath(fname) == fixed_root or\
#            fixpath(osp.dirname(fname)).startswith(fixed_root)
#
#    def is_root_path(self, dirname):
#        """Return True if dirname is project's root path"""
#        return fixpath(dirname) == fixpath(self.root_path)


class EmptyProject(BaseProject):
    """Empty Project"""
    PROJECT_TYPE_NAME = _('Empty project')
