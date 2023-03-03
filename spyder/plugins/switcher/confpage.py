# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Preferences Page."""

from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import get_translation

_ = get_translation("switcher.spyder")


class SwitcherConfigPage(PluginConfigPage):

    # --- PluginConfigPage API
    # ------------------------------------------------------------------------
    def setup_page(self):
        pass
