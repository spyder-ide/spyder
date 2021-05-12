# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2021, Spyder Bot
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------
"""
Spyder Boilerplate Preferences Page.
"""
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import get_translation

_ = get_translation("spyder_boilerplate.spyder")


class SpyderBoilerplateConfigPage(PluginConfigPage):

    # --- PluginConfigPage API
    # ------------------------------------------------------------------------
    def setup_page(self):
        pass
