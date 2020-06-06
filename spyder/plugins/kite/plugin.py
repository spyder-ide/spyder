# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite completion HTTP provider."""

# Standard library imports
import logging

# Third party imports
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.api.menus import ApplicationMenus
from spyder.plugins.completion.api import LSPRequestTypes
from spyder.plugins.kite.container import KiteCompletionContainer
from spyder.plugins.kite.utils.install import check_if_kite_installed

# Logging
logger = logging.getLogger(__name__)

# Localization
_ = get_translation('spyder')


class KiteCompletion(SpyderPluginV2):
    """
    Language server completion client plugin.
    """
    NAME = 'kite'
    REQUIRES = [Plugins.CodeCompletion, Plugins.Editor,
                Plugins.LanguageServerCompletion]
    CONTAINER_CLASS = KiteCompletionContainer
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        'code_snippets': ('lsp-server', 'code_snippets')
    }

    # --- SpyderPlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Kite completion provider')

    def get_description(self):
        return _('Provide Kite completions')

    def get_icon(self):
        return self.create_icon('kite')

    def register(self):
        container = self.get_container()

        # Register client
        completion = self.get_plugin(Plugins.CodeCompletion)
        completion.register_completion_provider(container.provider)
        completion.set_wait_for_source_requests(
            self.NAME,
            [
                LSPRequestTypes.DOCUMENT_COMPLETION,
                LSPRequestTypes.DOCUMENT_SIGNATURE,
                LSPRequestTypes.DOCUMENT_HOVER,
            ]
        )
        completion.set_request_type_priority(
            self.NAME,
            LSPRequestTypes.DOCUMENT_COMPLETION,
        )

        # Connect to editor
        editor = self.get_plugin(Plugins.Editor)
        editor.open_file_update.connect(container.send_status_request)

        # Add the status widget
        self.add_application_status_widget(
            'kite_status', container.status_widget)

        install_kite_action = self.create_action(
            "install_action",
            text=_("Install Kite completion engine"),
            # icon=self.create_icon('kite'),
            triggered=self.show_installation_dialog,
            register_shortcut=False,
        )
        is_kite_installed, __ = check_if_kite_installed()
        if not is_kite_installed:
            menu = self.get_application_menu(ApplicationMenus.Tools)
            self.add_item_to_application_menu(menu, install_kite_action)
            # self.tools_menu_actions.append(install_kite_action)

    def on_close(self, cancelable=False):
        container = self.get_container()
        if cancelable and container.is_installing():
            reply = QMessageBox.critical(
                self.get_main(),
                "Spyder",
                _("Kite installation process has not finished. "
                  "Do you really want to exit?"),
                QMessageBox.Yes,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                return False

        return True

    def on_mainwindow_visible(self):
        container = self.get_container()
        container._kite_onboarding()
        if self.get_conf_option('show_installation_dialog'):
            # Only show the dialog once at startup
            self.set_conf_option('show_installation_dialog', False)
            container.show_installation_dialog()

    # --- Public API
    # ------------------------------------------------------------------------
    def show_installation_dialog(self):
        self.get_container().show_installation_dialog()
