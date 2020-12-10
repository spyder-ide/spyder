# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Main interpreter Plugin.
"""

# Standard library imports
import os.path as osp

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.plugins.maininterpreter.confpage import MainInterpreterConfigPage
from spyder.utils.misc import get_python_executable

# Localization
_ = get_translation('spyder')


class MainInterpreter(SpyderPluginV2):
    """
    Main interpreter Plugin.
    """

    NAME = "main_interpreter"
    # TODO: Fix requires to reflect the desired order in the preferences
    REQUIRES = []
    CONTAINER_CLASS = None
    CONF_WIDGET_CLASS = MainInterpreterConfigPage
    CONF_SECTION = NAME
    CONF_FILE = False

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Python interpreter")

    def get_description(self):
        return _("Main Python interpreter to open consoles.")

    def get_icon(self):
        return self.create_icon('python')

    def register(self):
        # Validate that the custom interpreter from the previous session
        # still exists
        if self.get_conf_option('custom'):
            interpreter = self.get_conf_option('custom_interpreter')
            if not osp.isfile(interpreter):
                self.set_conf_option('custom', False)
                self.set_conf_option('default', True)
                self.set_conf_option('executable', get_python_executable())

    # --- Public API
    # ------------------------------------------------------------------------
    def get_interpreter(self):
        """Get current interpreter."""
        if self.get_conf_option('default'):
            return get_python_executable()
        else:
            return self.get_conf_option('custom_interpreter')
