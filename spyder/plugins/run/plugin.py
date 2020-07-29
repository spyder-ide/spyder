# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Run Plugin.
"""

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.plugins.run.confpage import RunConfigPage

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Run(SpyderPluginV2):
    """
    Run Plugin.
    """

    NAME = "run"
    # TODO: Fix requires to reflect the desired order in the preferences
    REQUIRES = []
    CONTAINER_CLASS = None
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = RunConfigPage
    CONF_FILE = False

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Run")

    def get_description(self):
        return _("Manage run configuration.")

    def get_icon(self):
        return self.create_icon('run')

    def register(self):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
