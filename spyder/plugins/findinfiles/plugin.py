# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
Find in Files Plugin.
"""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.findinfiles.widgets.main_widget import FindInFilesWidget
from spyder.plugins.mainmenu.api import ApplicationMenus
from spyder.utils.misc import getcwd_or_home


# --- Constants
# ----------------------------------------------------------------------------
class FindInFilesActions:
    FindInFiles = 'find in files'


# --- Plugin
# ----------------------------------------------------------------------------
class FindInFiles(SpyderDockablePlugin):
    """
    Find in files DockWidget.
    """
    NAME = 'find_in_files'
    REQUIRES = []
    OPTIONAL = [Plugins.Editor, Plugins.Projects, Plugins.MainMenu]
    TABIFY = [Plugins.VariableExplorer]
    WIDGET_CLASS = FindInFilesWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    RAISE_AND_FOCUS = True

    # --- SpyderDocakblePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Find")

    def get_description(self):
        return _("Search for strings of text in files.")

    def get_icon(self):
        return self.create_icon('findf')

    def on_initialize(self):
        self.create_action(
            FindInFilesActions.FindInFiles,
            text=_("Find in files"),
            tip=_("Search text in multiple files"),
            triggered=self.find,
            register_shortcut=True,
            context=Qt.WindowShortcut
        )
        self.refresh_search_directory()

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.connect(
            lambda filename, lineno, search_text, colno, colend: editor.load(
                filename, lineno, start_column=colno, end_column=colend))
        editor.sig_file_opened_closed_or_updated.connect(
            self.set_current_opened_file)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self.set_project_path)
        projects.sig_project_closed.connect(self.unset_project_path)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        findinfiles_action = self.get_action(FindInFilesActions.FindInFiles)

        mainmenu.add_item_to_application_menu(
            findinfiles_action,
            menu_id=ApplicationMenus.Search,
        )

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.disconnect()
        editor.sig_file_opened_closed_or_updated.disconnect(
            self.set_current_opened_file)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardon_plugin_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self.set_project_path)
        projects.sig_project_closed.disconnect(self.unset_project_path)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.remove_item_from_application_menu(
            FindInFilesActions.FindInFiles,
            menu_id=ApplicationMenus.Search,
        )

    def on_close(self, cancelable=False):
        self.get_widget()._update_options()
        if self.get_widget().running:
            self.get_widget()._stop_and_reset_thread(ignore_results=True)
        return True

    # --- Public API
    # ------------------------------------------------------------------------
    def refresh_search_directory(self):
        """
        Refresh search directory.
        """
        self.get_widget().set_directory(getcwd_or_home())

    def set_current_opened_file(self, path, _language):
        """
        Set path of current opened file in editor.

        Parameters
        ----------
        path: str
            Path of editor file.
        """
        self.get_widget().set_file_path(path)

    def set_project_path(self, path):
        """
        Set and refresh current project path.

        Parameters
        ----------
        path: str
            Opened project path.
        """
        self.get_widget().set_project_path(path)

    def set_max_results(self, value=None):
        """
        Set maximum amount of results to add to the result browser.

        Parameters
        ----------
        value: int, optional
            Number of results. If None an input dialog will be used.
            Default is None.
        """
        self.get_widget().set_max_results(value)

    def unset_project_path(self):
        """
        Unset current project path.
        """
        self.get_widget().disable_project_search()

    def find(self):
        """
        Search text in multiple files.

        Notes
        -----
        Find in files using the currently selected text of the focused widget.
        """
        focus_widget = QApplication.focusWidget()
        text = ''
        try:
            if focus_widget.has_selected_text():
                text = focus_widget.get_selected_text()
        except AttributeError:
            # This is not a text widget deriving from TextEditBaseWidget
            pass

        self.switch_to_plugin()
        widget = self.get_widget()

        if text:
            widget.set_search_text(text)

        widget.find()


def test():
    import sys

    from spyder.config.manager import CONF
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    widget = FindInFiles(None, CONF)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
