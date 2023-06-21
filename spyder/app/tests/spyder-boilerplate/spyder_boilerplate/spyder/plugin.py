# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2021, Spyder Bot
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------
"""
Spyder Boilerplate Plugin.
"""

# Third party imports
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QHBoxLayout, QLabel

# Spyder imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.preferences import PluginConfigPage
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.layout.layouts import VerticalSplitLayout2


class SpyderBoilerplateConfigPage(PluginConfigPage):

    # --- PluginConfigPage API
    # ------------------------------------------------------------------------
    def setup_page(self):
        pass


class SpyderBoilerplateActions:
    ExampleAction = "example_action"


class SpyderBoilerplateToolBarSections:
    ExampleSection = "example_section"


class SpyderBoilerplateOptionsMenuSections:
    ExampleSection = "example_section"


class SpyderBoilerplateWidget(PluginMainWidget):

    # PluginMainWidget class constants

    # Signals

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Create an example label
        self._example_label = QLabel("Example Label")

        # Add example label to layout
        layout = QHBoxLayout()
        layout.addWidget(self._example_label)
        self.setLayout(layout)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return "Spyder Boilerplate"

    def get_focus_widget(self):
        pass

    def setup(self):
        # Create an example action
        example_action = self.create_action(
            name=SpyderBoilerplateActions.ExampleAction,
            text="Example action",
            tip="Example hover hint",
            icon=self.create_icon("spyder"),
            triggered=lambda: print("Example action triggered!"),
        )

        # Add an example action to the plugin options menu
        menu = self.get_options_menu()
        self.add_item_to_menu(
            example_action,
            menu,
            SpyderBoilerplateOptionsMenuSections.ExampleSection,
        )

        # Add an example action to the plugin toolbar
        toolbar = self.get_main_toolbar()
        self.add_item_to_toolbar(
            example_action,
            toolbar,
            SpyderBoilerplateOptionsMenuSections.ExampleSection,
        )

    def update_actions(self):
        pass

    @on_conf_change
    def on_section_conf_change(self, section):
        pass

    # --- Public API
    # ------------------------------------------------------------------------


class SpyderBoilerplate(SpyderDockablePlugin):
    """
    Spyder Boilerplate plugin.
    """

    NAME = "spyder_boilerplate"
    REQUIRES = []
    OPTIONAL = []
    WIDGET_CLASS = SpyderBoilerplateWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = SpyderBoilerplateConfigPage
    CUSTOM_LAYOUTS = [VerticalSplitLayout2]

    # --- Signals

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return "Spyder Boilerplate"

    def get_description(self):
        return "Boilerplate needed to create a Spyder Plugin."

    def get_icon(self):
        return QIcon()

    def on_initialize(self):
        pass

    def check_compatibility(self):
        valid = True
        message = ""  # Note: Remember to use _("") to localize the string
        return valid, message

    def on_close(self, cancellable=True):
        return True

    # --- Public API
    # ------------------------------------------------------------------------
