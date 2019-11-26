# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Projects Types.
"""

# Standard library imports
import os
import os.path as osp
from collections import OrderedDict

# Local imports
from spyder.config.base import _, get_project_config_folder
from spyder.py3compat import to_text_string
from spyder.plugins.projects.utils.config import (ProjectMultiConfig,
                                                  PROJECT_NAME_MAP,
                                                  PROJECT_DEFAULTS,
                                                  PROJECT_CONF_VERSION)


class BaseProject(object):
    """Spyder base project.

    This base class must not be used directly, but inherited from. It does not
    assume that python is specific to this project.
    """
    PROJECT_TYPE_NAME = None
    PROJECT_TYPE = None

    def __init__(self, root_path):
        self.name = None
        self.root_path = root_path
        self.open_project_files = []
        self.open_non_project_files = []

        path = os.path.join(root_path, get_project_config_folder(), 'config')
        self.config = ProjectMultiConfig(
            PROJECT_NAME_MAP,
            path=path,
            defaults=PROJECT_DEFAULTS,
            load=True,
            version=PROJECT_CONF_VERSION,
            backup=True,
            raw_mode=True,
            remove_obsolete=False,
        )

    # --- Helpers
    # -------------------------------------------------------------------------
    def get_option(self, section, option):
        """Get project configuration option."""
        return self.config.get(section, option)

    def set_option(self, section, option, value):
        """Set project configuration option."""
        self.config.set(section, option, value)

    def set_recent_files(self, recent_files):
        """Set a list of files opened by the project."""
        processed_recent_files = []
        for recent_file in recent_files:
            if os.path.isfile(recent_file):
                try:
                    relative_recent_file = os.path.relpath(
                        recent_file, self.root_path)
                    processed_recent_files.append(relative_recent_file)
                except ValueError:
                    processed_recent_files.append(recent_file)
        files = list(OrderedDict.fromkeys(processed_recent_files))
        self.config.set('main', 'recent_files', files)

    def get_recent_files(self):
        """Return a list of files opened by the project."""
        recent_files = self.config.get('main', 'recent_files', default=[])
        recent_files = [recent_file if os.path.isabs(recent_file)
                        else os.path.join(self.root_path, recent_file)
                        for recent_file in recent_files]
        for recent_file in recent_files[:]:
            if not os.path.isfile(recent_file):
                recent_files.remove(recent_file)

        return list(OrderedDict.fromkeys(recent_files))


class EmptyProject(BaseProject):
    """Empty Project"""
    PROJECT_TYPE_NAME = _('Empty project')
    PROJECT_TYPE = 'empty'


if __name__ == '__main__':
    from spyder.config.base import get_home_dir
    project_path = osp.join(get_home_dir(), 'test_project')
    project = EmptyProject(project_path)
