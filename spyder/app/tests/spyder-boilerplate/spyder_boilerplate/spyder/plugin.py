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
import qtawesome as qta
from qtpy.QtWidgets import QHBoxLayout, QTextEdit

# Spyder imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.plugins import SpyderDockablePlugin
from spyder.api.preferences import PluginConfigPage
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.layout.layouts import VerticalSplitLayout2
from spyder.utils.palette import SpyderPalette


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

        # Create example widgets
        self._example_widget = QTextEdit(self)
        self._example_widget.setText("Example text")

        # Add example label to layout
        layout = QHBoxLayout()
        layout.addWidget(self._example_widget)
        self.setLayout(layout)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return "Spyder boilerplate plugin"

    def get_focus_widget(self):
        return self

    def setup(self):
        # Create an example action
        example_action = self.create_action(
            name=SpyderBoilerplateActions.ExampleAction,
            text="Example action",
            tip="Example hover hint",
            icon=self.create_icon("python"),
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

        # Shortcuts
        self.register_shortcut_for_widget(
            "Change text",
            self.change_text,
        )

        self.register_shortcut_for_widget(
            "new text",
            self.new_text,
            context="editor",
            plugin_name=self._plugin.NAME,
        )

    def update_actions(self):
        pass

    @on_conf_change
    def on_section_conf_change(self, section):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
    def change_text(self):
        if self._example_widget.toPlainText() == "":
            self._example_widget.setText("Example text")
        else:
            self._example_widget.setText("")

    def new_text(self):
        if self._example_widget.toPlainText() != "Another text":
            self._example_widget.setText("Another text")


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
    CONF_DEFAULTS = [
        (CONF_SECTION, {}),
        (
            "shortcuts",
            # Note: These shortcut names are capitalized to check we can
            # set/get/reset them correctly.
            {f"{NAME}/Change text": "Ctrl+B", "editor/New text": "Ctrl+H"},
        ),
    ]

    # --- Signals

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return "Spyder boilerplate plugin"

    @staticmethod
    def get_description():
        return "A boilerplate plugin for testing."

    @staticmethod
    def get_icon():
        return qta.icon('mdi6.alpha-b-box', color=SpyderPalette.ICON_1)

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
