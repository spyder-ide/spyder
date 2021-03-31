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

    def __init__(self, root_path, parent_plugin=None):
        self.plugin = parent_plugin
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

        # Check if recent_files in [main] (Spyder 4)
        recent_files = self.get_option("recent_files", 'main', [])
        if recent_files:
            # Move to [workspace] (Spyder 5)
            self.config.remove_option('main', 'recent_files')
            self.set_recent_files(recent_files)
        else:
            recent_files = self.get_option("recent_files", default=[])

        recent_files = [recent_file if os.path.isabs(recent_file)
                        else os.path.join(self.root_path, recent_file)
                        for recent_file in recent_files]
        for recent_file in recent_files[:]:
            if not os.path.isfile(recent_file):
                recent_files.remove(recent_file)

        return list(OrderedDict.fromkeys(recent_files))

    # --- API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        """
        Provide a human readable version of NAME.
        """
        raise NotImplementedError("Must implement a `get_name` method!")

    @staticmethod
    def validate_name(path, name):
        """
        Validate the project's name.

        Returns
        -------
        tuple
            The first item (bool) indicates if the name was validated
            successfully, and the second item (str) indicates the error
            message, if any.
        """
        return True, ""

    def create_project(self):
        """
        Create a project and do any additional setup for this project type.

        Returns
        -------
        tuple
            The first item (bool) indicates if the project was created
            successfully, and the second item (str) indicates the error
            message, if any.
        """
        return False, "A ProjectType must define a `create_project` method!"

    def open_project(self):
        """
        Open a project and do any additional setup for this project type.

        Returns
        -------
        tuple
            The first item (bool) indicates if the project was opened
            successfully, and the second item (str) indicates the error
            message, if any.
        """
        return False, "A ProjectType must define an `open_project` method!"

    def close_project(self):
        """
        Close a project and do any additional setup for this project type.

        Returns
        -------
        tuple
            The first item (bool) indicates if the project was closed
            successfully, and the second item (str) indicates the error
            message, if any.
        """
        return False, "A ProjectType must define a `close_project` method!"


class EmptyProject(BaseProjectType):
    ID = 'empty-project-type'

    @staticmethod
    def get_name():
        return _("Empty project")

    def create_project(self):
        return True, ""

    def open_project(self):
        return True, ""

    def close_project(self):
        return True, ""
