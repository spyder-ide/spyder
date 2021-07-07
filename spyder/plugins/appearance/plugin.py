# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Appearance Plugin.
"""

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import get_translation
from spyder.plugins.appearance.confpage import AppearanceConfigPage

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Appearance(SpyderPluginV2):
    """
    Appearance Plugin.
    """

    NAME = "appearance"
    # TODO: Fix requires to reflect the desired order in the preferences
    REQUIRES = [Plugins.Preferences]
    CONTAINER_CLASS = None
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = AppearanceConfigPage
    CONF_FILE = False

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Appearance")

    def get_description(self):
        return _("Manage application appearance and themes.")

    def get_icon(self):
        return self.create_icon('eyedropper')

    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.Preferences)
    def register_preferences(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)
