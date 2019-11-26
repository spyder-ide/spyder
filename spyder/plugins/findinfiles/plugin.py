# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Find in Files Plugin."""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QApplication, QInputDialog, QVBoxLayout

# Local imports
from spyder.api.plugins import SpyderPluginWidget
from spyder.config.base import _
from spyder.utils.misc import getcwd_or_home
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action, MENU_SEPARATOR
from spyder.plugins.findinfiles.widgets import FindInFilesWidget


class FindInFiles(SpyderPluginWidget):
    """Find in files DockWidget."""

    CONF_SECTION = 'find_in_files'
    CONF_FILE = False
    toggle_visibility = Signal(bool)

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        supported_encodings = self.get_option('supported_encodings')
        self.search_text_samples = self.get_option('search_text_samples')
        search_text = self.get_option('search_text')
        search_text = [txt for txt in search_text
                       if txt not in self.search_text_samples]
        search_text += self.search_text_samples
        search_text_regexp = self.get_option('search_text_regexp')
        exclude = self.get_option('exclude')
        exclude_idx = self.get_option('exclude_idx', None)
        exclude_regexp = self.get_option('exclude_regexp')
        more_options = self.get_option('more_options')
        case_sensitive = self.get_option('case_sensitive')
        path_history = self.get_option('path_history', [])
        search_in_index = self.get_option('search_in_index', default=0)
        max_results = self.get_option('max_results')

        self.findinfiles = FindInFilesWidget(
            self,
            search_text,
            search_text_regexp,
            exclude,
            exclude_idx,
            exclude_regexp,
            supported_encodings,
            more_options,
            case_sensitive,
            path_history,
            search_in_index,
            options_button=self.options_button,
            text_color=ima.MAIN_FG_COLOR,
            max_results=max_results)

        layout = QVBoxLayout()
        layout.addWidget(self.findinfiles)
        self.setLayout(layout)

        self.toggle_visibility.connect(self.toggle)

    def toggle(self, state):
        """Toggle widget visibility"""
        if self.dockwidget:
            self.dockwidget.setVisible(state)
    
    def refreshdir(self):
        """Refresh search directory"""
        self.findinfiles.find_options.set_directory(
            getcwd_or_home())

    def set_project_path(self, path):
        """Refresh current project path"""
        self.findinfiles.find_options.set_project_path(path)

    def set_current_opened_file(self, path):
        """Get path of current opened file in editor"""
        self.findinfiles.find_options.set_file_path(path)

    def unset_project_path(self):
        """Refresh current project path"""
        self.findinfiles.find_options.disable_project_search()

    def findinfiles_callback(self):
        """Find in files callback"""
        widget = QApplication.focusWidget()
        text = ''
        try:
            if widget.has_selected_text():
                text = widget.get_selected_text()
        except AttributeError:
            # This is not a text widget deriving from TextEditBaseWidget
            pass
        self.findinfiles.set_search_text(text)
        if text:
            self.findinfiles.find()

    def show_max_results_input(self):
        """Show input dialog to set maximum amount of results."""
        value, valid = QInputDialog.getInt(
            self,
            self.get_plugin_title(),
            _('Set maximum number of results: '),
            value=self.get_option('max_results'),
            min=1,
            step=1,
        )
        if valid:
            self.set_max_results(value)

    def set_max_results(self, value):
        """Set maximum amount of results to add to result browser."""
        self.set_option('max_results', value)
        self.findinfiles.set_max_results(value)

    #------ SpyderPluginMixin API ---------------------------------------------
    def switch_to_plugin(self):
        """
        Switch to plugin.

        This method is called when pressing the plugin shortcut.
        """
        if self.dockwidget:
            super(FindInFiles, self).switch_to_plugin()
        self.findinfiles_callback()  # Necessary at least with PyQt5 on Windows

    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Find")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.findinfiles.find_options.search_text

    def get_plugin_actions(self):
        """Return a list of actions related to plugin."""
        set_max_results_action = create_action(
            self,
            _("Set maximum number of results"),
            triggered=self.show_max_results_input)
        browser_actions = self.findinfiles.result_browser.get_menu_actions()
        return [set_max_results_action, None] + browser_actions

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.add_dockwidget()
        self.findinfiles.result_browser.sig_edit_goto.connect(
                                                         self.main.editor.load)
        self.findinfiles.find_options.redirect_stdio.connect(
                                        self.main.redirect_internalshell_stdio)
        self.main.workingdirectory.refresh_findinfiles.connect(self.refreshdir)
        self.main.projects.sig_project_loaded.connect(self.set_project_path)
        self.main.projects.sig_project_closed.connect(self.unset_project_path)
        self.main.editor.open_file_update.connect(self.set_current_opened_file)

        findinfiles_action = create_action(
            self,
            _("&Find in files"),
            icon=ima.icon('findf'),
            triggered=self.switch_to_plugin,
            shortcut=QKeySequence(self.shortcut),
            context=Qt.WidgetShortcut,
            tip=_("Search text in multiple files"))

        self.main.search_menu_actions += [MENU_SEPARATOR, findinfiles_action]
        self.main.search_toolbar_actions += [MENU_SEPARATOR,
                                             findinfiles_action]
        self.refreshdir()

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.findinfiles.closing_widget()  # stop search thread and clean-up
        options = self.findinfiles.find_options.get_options(to_save=True)
        if options is not None:
            (search_text, text_re,
             exclude, exclude_idx, exclude_re,
             more_options, case_sensitive,
             path_history, search_in_index) = options
            hist_limit = 15
            search_text = search_text[:hist_limit]
            exclude = exclude[:hist_limit]
            path_history = path_history[-hist_limit:]
            self.set_option('search_text', search_text)
            self.set_option('search_text_regexp', text_re)
            self.set_option('exclude', exclude)
            self.set_option('exclude_idx', exclude_idx)
            self.set_option('exclude_regexp', exclude_re)
            self.set_option('more_options', more_options)
            self.set_option('case_sensitive', case_sensitive)
            self.set_option('path_history', path_history)
            self.set_option('search_in_index', search_in_index)
        return True

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.variableexplorer)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = FindInFiles()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
