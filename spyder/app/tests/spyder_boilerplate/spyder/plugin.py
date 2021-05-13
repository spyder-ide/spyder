# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2021, Spyder Bot
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------
"""
Spyder Boilerplate Plugin.
"""

# Third-party imports
from qtpy.QtGui import QIcon

# Spyder imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.layout.layouts import VerticalSplitLayout2

# Local imports
from spyder_boilerplate.spyder.confpage import SpyderBoilerplateConfigPage
from spyder_boilerplate.spyder.widgets import SpyderBoilerplateWidget

_ = get_translation("spyder_boilerplate.spyder")


class SpyderBoilerplate(SpyderDockablePlugin):
    """
    Spyder Boilerplate plugin.
    """

    NAME = "spyder_boilerplate"
    REQUIRES = []
    OPTIONAL = []
    WIDGET_CLASS = SpyderBoilerplateWidget
    CONF_SECTION = NAME
    CUSTOM_LAYOUTS = [VerticalSplitLayout2]

    # --- Signals

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Spyder Boilerplate")

    def get_description(self):
        return _("Boilerplate needed to create a Spyder Plugin.")

    def get_icon(self):
        return QIcon()

    def register(self):
        widget = self.get_widget()

    def check_compatibility(self):
        valid = True
        message = ""  # Note: Remember to use _("") to localize the string
        return valid, message

    def on_close(self, cancellable=True):
        return True

    # --- Public API
    # ------------------------------------------------------------------------
