# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Console History Plugin"""

# Standard library imports
import os.path as osp
import sys
import re

# Third party imports
from qtpy import PYQT5
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import (QGroupBox, QHBoxLayout, QInputDialog, QMenu,
                            QToolButton, QVBoxLayout, QWidget)


# Local imports
from spyder.config.base import _
from spyder.plugins import SpyderPluginWidget
from spyder.plugins.configdialog import PluginConfigPage
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton)
from spyder.utils.sourcecode import normalize_eols
from spyder.widgets.tabs import Tabs
from spyder.widgets.sourcecode import codeeditor
from spyder.widgets.findreplace import FindReplace


class HistoryConfigPage(PluginConfigPage):
    def get_icon(self):
        return ima.icon('history')
    
    def setup_page(self):
        settings_group = QGroupBox(_("Settings"))
        hist_spin = self.create_spinbox(
                            _("History depth: "), _(" entries"),
                            'max_entries', min_=10, max_=10000, step=10,
                            tip=_("Set maximum line count"))

        sourcecode_group = QGroupBox(_("Source code"))
        wrap_mode_box = self.create_checkbox(_("Wrap lines"), 'wrap')
        go_to_eof_box = self.create_checkbox(
                        _("Scroll automatically to last entry"), 'go_to_eof')

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(hist_spin)
        settings_group.setLayout(settings_layout)

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(go_to_eof_box)
        sourcecode_group.setLayout(sourcecode_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(settings_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class HistoryLog(SpyderPluginWidget):
    """
    History log widget
    """
    CONF_SECTION = 'historylog'
    CONFIGWIDGET_CLASS = HistoryConfigPage
    focus_changed = Signal()
    
    def __init__(self, parent):
        self.tabwidget = None
        self.menu_actions = None
        self.dockviewer = None
        self.wrap_action = None
        
        self.editors = []
        self.filenames = []
        if PYQT5:        
            SpyderPluginWidget.__init__(self, parent, main = parent)
        else:
            SpyderPluginWidget.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()

        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
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
        options_button = create_toolbutton(self, text=_('Options'),
                                           icon=ima.icon('tooloptions'))
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.menu_actions)
        options_button.setMenu(menu)
        self.tabwidget.setCornerWidget(options_button)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        self.register_widget_shortcuts(self.find_widget)

        layout.addWidget(self.find_widget)

        self.setLayout(layout)

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('History log')
    
    def get_plugin_icon(self):
        """Return widget icon"""
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
        history_action = create_action(self, _("History..."),
                                       None, ima.icon('history'),
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.wrap_action = create_action(self, _("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        self.wrap_action.setChecked( self.get_option('wrap') )
        self.menu_actions = [history_action, self.wrap_action]
        return self.menu_actions

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
        for editor in self.editors:
            if font_n in options:
                scs = color_scheme_o if color_scheme_n in options else None
                editor.set_font(font_o, scs)
            elif color_scheme_n in options:
                editor.set_color_scheme(color_scheme_o)
            if wrap_n in options:
                editor.toggle_wrap_mode(wrap_o)
        
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
        editor.setup_editor(linenumbers=False, language=language,
                            scrollflagarea=False)
        editor.focus_changed.connect(lambda: self.focus_changed.emit())
        editor.setReadOnly(True)
        color_scheme = self.get_color_scheme()
        editor.set_font( self.get_plugin_font(), color_scheme )
        editor.toggle_wrap_mode( self.get_option('wrap') )

        text, _ = encoding.read(filename)
        text = normalize_eols(text)
        linebreaks = [m.start() for m in re.finditer('\n', text)]
        maxNline = self.get_option('max_entries')
        if len(linebreaks) > maxNline:
            text = text[linebreaks[-maxNline - 1] + 1:]
            encoding.write(text, filename)
        editor.set_text(text)
        editor.set_cursor_position('eof')
        
        self.editors.append(editor)
        self.filenames.append(filename)
        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.find_widget.set_editor(editor)
        self.tabwidget.setTabToolTip(index, filename)
        self.tabwidget.setCurrentIndex(index)
        
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
