# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Projects Plugin API.
"""

# Standard library imports
import os
import os.path as osp
from collections import OrderedDict

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.translations import get_translation
from spyder.config.base import get_project_config_folder
from spyder.plugins.projects.utils.config import (ProjectMultiConfig,
                                                  PROJECT_NAME_MAP,
                                                  PROJECT_DEFAULTS,
                                                  PROJECT_CONF_VERSION,
                                                  WORKSPACE, CODESTYLE,
                                                  ENCODING, VCS)


# Localization
_ = get_translation("spyder")


class BaseProjectType:
    """
    Spyder base project.

    This base class must not be used directly, but inherited from. It does not
    assume that python is specific to this project.
    """
    ID = None

    def __init__(self, root_path, projects_plugin):
        self.projects_plugin = projects_plugin
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
        self.set_option("project_type", self.ID)

    # --- Helpers
    # -------------------------------------------------------------------------
    def get_option(self, option, section=WORKSPACE, default=None):
        """Get project configuration option."""
        return self.config.get(section=section, option=option, default=default)

    def set_option(self, option, value, section=WORKSPACE):
        """Set project configuration option."""
        self.config.set(section=section, option=option, value=value)

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
        self.set_option("recent_files", files)

    def get_recent_files(self):
        """Return a list of files opened by the project."""
        recent_files = self.get_option("recent_files", default=[])
        recent_files = [recent_file if os.path.isabs(recent_file)
                        else os.path.join(self.root_path, recent_file)
                        for recent_file in recent_files]
        for recent_file in recent_files[:]:
            if not os.path.isfile(recent_file):
                recent_files.remove(recent_file)

        return list(OrderedDict.fromkeys(recent_files))

    def get_plugin(self, plugin_name):
        """
        Return a plugin by unique `plugin_name`.
        """
        return self.projects_plugin.get_plugin(plugin_name)

    # --- API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name(self):
        """
        Provide a human readable version of NAME.
        """
        raise NotImplementedError("Must implement a `get_name` method!")

    def create_project(self):
        """
        Create a project and do any additional setup for this project type.
        """
        raise NotImplementedError("Must implement a `create_project` method!")

    def open_project(self):
        """
        Open a project and do any additional setup for this project type.
        """
        raise NotImplementedError("Must implement a `open_project` method!")

    def close_project(self):
        """
        Close a project and do any additional setup for this project type.
        """
        raise NotImplementedError("Must implement a `close_project` method!")


class EmptyProject(BaseProjectType):
    ID = 'empty-project-type'

    @staticmethod
    def get_name():
        return _("Empty project")

    def create_project(self):
        pass

    def open_project(self):
        pass

    def close_project(self):
        pass
