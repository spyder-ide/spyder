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

# Local imports
from spyder.api.menus import ApplicationMenus
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.toolbars import ApplicationToolBars
from spyder.api.translations import get_translation
from spyder.plugins.findinfiles.widgets import (FindInFilesWidget,
                                                FindInFilesWidgetActions)
from spyder.utils.misc import getcwd_or_home

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class FindInFilesActions:
    FindInFiles = 'find_in_files_action'


# --- Plugin
# ----------------------------------------------------------------------------
class FindInFiles(SpyderDockablePlugin):
    """
    Find in files DockWidget.
    """
    NAME = 'find_in_files'
    OPTIONAL = [Plugins.Editor, Plugins.Projects, Plugins.WorkingDirectory]
    TABIFY = [Plugins.VariableExplorer]
    WIDGET_CLASS = FindInFilesWidget
    CONF_SECTION = NAME
    CONF_FILE = False

    # --- SpyderDocakblePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Find")

    def get_description(self):
        return _("Search for strings of text in files.")

    def get_icon(self):
        return self.create_icon('findf')

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        projects = self.get_plugin(Plugins.Projects)
        working_directory = self.get_plugin(Plugins.WorkingDirectory)

        if editor:
            widget.sig_edit_goto_requested.connect(editor.load)
            # TODO: improve name of signal open_file_update?
            editor.open_file_update.connect(self.set_current_opened_file)

        if projects:
            projects.sig_project_loaded.connect(self.set_project_path)
            projects.sig_project_closed.connect(self.unset_project_path)

        if working_directory:
            working_directory.sig_current_directory_changed.connect(
                self.refresh_search_directory)

        findinfiles_action = self.get_action(FindInFilesWidgetActions.Find)
        menu = self.get_application_menu(ApplicationMenus.Search)
        self.add_item_to_application_menu(
            findinfiles_action,
            menu=menu,
        )
        findinfiles_action.triggered.connect(lambda: self.switch_to_plugin())

        search_toolbar = self.get_application_toolbar(
            ApplicationToolBars.Search)
        self.add_item_to_application_toolbar(
            findinfiles_action,
            search_toolbar,
        )
        self.refresh_search_directory()

    def on_close(self, cancelable=False):
        self.get_widget()._update_options()
        self.get_widget()._stop_and_reset_thread(ignore_results=True)
        return True

    # --- Public API
    # ------------------------------------------------------------------------
    def refresh_search_directory(self):
        """
        Refresh search directory.
        """
        self.get_widget().set_directory(getcwd_or_home())

    def set_current_opened_file(self, path):
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
        """
        self.switch_to_plugin()
        self.get_widget().find()


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
