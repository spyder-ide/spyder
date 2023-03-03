# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Switcher Plugin.
"""

# Third-party imports
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation

from spyder.plugins.switcher.confpage import SwitcherConfigPage
from spyder.plugins.switcher.container import SwitcherContainer

_ = get_translation("switcher.spyder")


class Switcher(SpyderPluginV2):
    """
    Switcher plugin.
    """

    NAME = "switcher"
    REQUIRES = []
    OPTIONAL = []
    CONTAINER_CLASS = SwitcherContainer
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = SwitcherConfigPage

    # --- Signals

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Switcher")

    def get_description(self):
        return _("A multi purpose switcher.")

    def get_icon(self):
        return QIcon()

    def on_initialize(self):
        container = self.get_container()
        print('Switcher initialized!')

    def check_compatibility(self):
        valid = True
        message = ""  # Note: Remember to use _("") to localize the string
        return valid, message

    def on_close(self, cancellable=True):
        return True

    # --- Public API
    # ------------------------------------------------------------------------
