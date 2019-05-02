# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Console History Plugin."""

# Standard library imports
import os.path as osp
import sys
import re

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import (QHBoxLayout, QInputDialog,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.utils.sourcecode import normalize_eols
from spyder.widgets.tabs import Tabs
from spyder.plugins.editor.widgets import codeeditor
from spyder.widgets.findreplace import FindReplace

from spyder.plugins.history.confpage import HistoryConfigPage
#from spyder.plugins.history.widgets import History


class HistoryLog(SpyderPluginWidget):
    """History log plugin."""

    CONF_SECTION = 'historylog'
    CONFIGWIDGET_CLASS = HistoryConfigPage
    focus_changed = Signal()

    def __init__(self, parent):
        """Initialize plugin and create History main widget."""
        SpyderPluginWidget.__init__(self, parent)

        self.tabwidget = None
        self.dockviewer = None
        self.wrap_action = None
        self.linenumbers_action = None

        self.editors = []
        self.filenames = []

        # Initialize plugin actions, toolbutton and general signals
        self.initialize_plugin()

        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.plugin_actions)
        self.tabwidget.currentChanged.connect(self.refresh_plugin)
        self.tabwidget.move_data.connect(self.move_tab)

        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabwidget)

        # Menu as corner widget
        self.tabwidget.setCornerWidget(self.options_button)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        self.register_widget_shortcuts(self.find_widget)

        layout.addWidget(self.find_widget)

        self.setLayout(layout)

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title."""
        return _('History')
    
    def get_plugin_icon(self):
        """Return widget icon."""
        return ima.icon('history')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.tabwidget.currentWidget()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget()
        else:
            editor = None
        self.find_widget.set_editor(editor)

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        self.history_action = create_action(self, _("History..."),
                                       None, ima.icon('history'),
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.wrap_action = create_action(self, _("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        self.wrap_action.setChecked( self.get_option('wrap') )
        self.linenumbers_action = create_action(
                self, _("Show line numbers"), toggled=self.toggle_line_numbers)
        self.linenumbers_action.setChecked(self.get_option('line_numbers'))

        menu_actions = [self.history_action, self.wrap_action,
                        self.linenumbers_action]
        return menu_actions

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.ipyconsole, self)
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
#        self.main.console.set_historylog(self)
        self.main.console.shell.refresh.connect(self.refresh_plugin)

    def update_font(self):
        """Update font from Preferences"""
        color_scheme = self.get_color_scheme()
        font = self.get_plugin_font()
        for editor in self.editors:
            editor.set_font(font, color_scheme)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = self.get_color_scheme()
        font_n = 'plugin_font'
        font_o = self.get_plugin_font()
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        linenb_n = 'line_numbers'
        linenb_o = self.get_option(linenb_n)
        for editor in self.editors:
            if font_n in options:
                scs = color_scheme_o if color_scheme_n in options else None
                editor.set_font(font_o, scs)
            elif color_scheme_n in options:
                editor.set_color_scheme(color_scheme_o)
            if wrap_n in options:
                editor.toggle_wrap_mode(wrap_o)
            if linenb_n in options:
                editor.toggle_line_numbers(linenumbers=linenb_o, markers=False)

    #------ Private API --------------------------------------------------------
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        filename = self.filenames.pop(index_from)
        editor = self.editors.pop(index_from)

        self.filenames.insert(index_to, filename)
        self.editors.insert(index_to, editor)

    #------ Public API ---------------------------------------------------------
    def add_history(self, filename):
        """
        Add new history tab
        Slot for add_history signal emitted by shell instance
        """
        filename = encoding.to_unicode_from_fs(filename)
        if filename in self.filenames:
            return
        editor = codeeditor.CodeEditor(self)
        if osp.splitext(filename)[1] == '.py':
            language = 'py'
        else:
            language = 'bat'
        editor.setup_editor(linenumbers=self.get_option('line_numbers'),
                            language=language,
                            scrollflagarea=False)
        editor.focus_changed.connect(lambda: self.focus_changed.emit())
        editor.setReadOnly(True)
        color_scheme = self.get_color_scheme()
        editor.set_font( self.get_plugin_font(), color_scheme )
        editor.toggle_wrap_mode( self.get_option('wrap') )

        # Avoid a possible error when reading the history file
        try:
            text, _ = encoding.read(filename)
        except (IOError, OSError):
            text = "# Previous history could not be read from disk, sorry\n\n"
        text = normalize_eols(text)
        linebreaks = [m.start() for m in re.finditer('\n', text)]
        maxNline = self.get_option('max_entries')
        if len(linebreaks) > maxNline:
            text = text[linebreaks[-maxNline - 1] + 1:]
            # Avoid an error when trying to write the trimmed text to
            # disk.
            # See issue 9093
            try:
                encoding.write(text, filename)
            except (IOError, OSError):
                pass
        editor.set_text(text)
        editor.set_cursor_position('eof')

        self.editors.append(editor)
        self.filenames.append(filename)
        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.find_widget.set_editor(editor)
        self.tabwidget.setTabToolTip(index, filename)
        self.tabwidget.setCurrentIndex(index)

    @Slot(str, str)
    def append_to_history(self, filename, command):
        """
        Append an entry to history filename
        Slot for append_to_history signal emitted by shell instance
        """
        if not is_text_string(filename): # filename is a QString
            filename = to_text_string(filename.toUtf8(), 'utf-8')
        command = to_text_string(command)
        index = self.filenames.index(filename)
        self.editors[index].append(command)
        if self.get_option('go_to_eof'):
            self.editors[index].set_cursor_position('eof')
        self.tabwidget.setCurrentIndex(index)
    
    @Slot()
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInt(self, _('History'),
                                       _('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)

    @Slot(bool)
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for editor in self.editors:
            editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)

    @Slot(bool)
    def toggle_line_numbers(self, checked):
        """Toggle line numbers."""
        if self.tabwidget is None:
            return
        for editor in self.editors:
            editor.toggle_line_numbers(linenumbers=checked, markers=False)
        self.set_option('line_numbers', checked)
