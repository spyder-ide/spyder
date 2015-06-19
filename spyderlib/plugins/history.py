# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Console History Plugin"""

from spyderlib.qt.QtGui import (QVBoxLayout, QFontDialog, QInputDialog,
                                QToolButton, QMenu, QFontComboBox, QGroupBox,
                                QHBoxLayout, QWidget)
from spyderlib.qt.QtCore import SIGNAL

import os.path as osp
import sys

# Local imports
from spyderlib.utils import encoding
from spyderlib.baseconfig import _
from spyderlib.config import CONF
from spyderlib.guiconfig import get_color_scheme
from spyderlib.utils.qthelpers import (get_icon, create_action,
                                       create_toolbutton, add_actions)
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.sourcecode import codeeditor
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage
from spyderlib.py3compat import to_text_string, is_text_string


class HistoryConfigPage(PluginConfigPage):
    def get_icon(self):
        return get_icon('history24.png')
    
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
        font_group = self.create_fontgroup(option=None,
                                    text=_("Font style"),
                                    fontfilters=QFontComboBox.MonospacedFonts)
        names = CONF.get('color_schemes', 'names')
        choices = list(zip(names, names))
        cs_combo = self.create_combobox(_("Syntax color scheme: "),
                                        choices, 'color_scheme_name')

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(hist_spin)
        settings_group.setLayout(settings_layout)

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(go_to_eof_box)
        sourcecode_layout.addWidget(cs_combo)
        sourcecode_group.setLayout(sourcecode_layout)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(settings_group)
        vlayout.addWidget(font_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class HistoryLog(SpyderPluginWidget):
    """
    History log widget
    """
    CONF_SECTION = 'historylog'
    CONFIGWIDGET_CLASS = HistoryConfigPage
    def __init__(self, parent):
        self.tabwidget = None
        self.menu_actions = None
        self.dockviewer = None
        self.wrap_action = None
        
        self.editors = []
        self.filenames = []
        self.icons = []
        
        SpyderPluginWidget.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()
        
        self.set_default_color_scheme()
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh_plugin)
        self.connect(self.tabwidget, SIGNAL('move_data(int,int)'),
                     self.move_tab)

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
        options_button = create_toolbutton(self, text=_("Options"),
                                           icon=get_icon('tooloptions.png'))
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.menu_actions)
        options_button.setMenu(menu)
        self.tabwidget.setCornerWidget(options_button)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        self.register_widget_shortcuts("Editor", self.find_widget)
        
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)
            
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _('History log')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('history.png')
    
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
                                       None, 'history.png',
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        font_action = create_action(self, _("&Font..."), None,
                                    'font.png', _("Set shell font style"),
                                    triggered=self.change_font)
        self.wrap_action = create_action(self, _("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        self.wrap_action.setChecked( self.get_option('wrap') )
        self.menu_actions = [history_action, font_action, self.wrap_action]
        return self.menu_actions

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.extconsole, self)
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        self.main.add_dockwidget(self)
#        self.main.console.set_historylog(self)
        self.connect(self.main.console.shell, SIGNAL("refresh()"),
                     self.refresh_plugin)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = get_color_scheme(self.get_option(color_scheme_n))
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
        icon = self.icons.pop(index_from)
        
        self.filenames.insert(index_to, filename)
        self.editors.insert(index_to, editor)
        self.icons.insert(index_to, icon)
        
    #------ Public API ---------------------------------------------------------
    def add_history(self, filename):
        """
        Add new history tab
        Slot for SIGNAL('add_history(QString)') emitted by shell instance
        """
        filename = encoding.to_unicode_from_fs(filename)
        if filename in self.filenames:
            return
        editor = codeeditor.CodeEditor(self)
        if osp.splitext(filename)[1] == '.py':
            language = 'py'
            icon = get_icon('python.png')
        else:
            language = 'bat'
            icon = get_icon('cmdprompt.png')
        editor.setup_editor(linenumbers=False, language=language,
                            scrollflagarea=False)
        self.connect(editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        editor.setReadOnly(True)
        color_scheme = get_color_scheme(self.get_option('color_scheme_name'))
        editor.set_font( self.get_plugin_font(), color_scheme )
        editor.toggle_wrap_mode( self.get_option('wrap') )

        text, _ = encoding.read(filename)
        editor.set_text(text)
        editor.set_cursor_position('eof')
        
        self.editors.append(editor)
        self.filenames.append(filename)
        self.icons.append(icon)
        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.find_widget.set_editor(editor)
        self.tabwidget.setTabToolTip(index, filename)
        self.tabwidget.setTabIcon(index, icon)
        self.tabwidget.setCurrentIndex(index)
        
    def append_to_history(self, filename, command):
        """
        Append an entry to history filename
        Slot for SIGNAL('append_to_history(QString,QString)')
        emitted by shell instance
        """
        if not is_text_string(filename): # filename is a QString
            filename = to_text_string(filename.toUtf8(), 'utf-8')
        command = to_text_string(command)
        index = self.filenames.index(filename)
        self.editors[index].append(command)
        if self.get_option('go_to_eof'):
            self.editors[index].set_cursor_position('eof')
        self.tabwidget.setCurrentIndex(index)
        
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, _('History'),
                                       _('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(self.get_plugin_font(),
                       self, _("Select a new font"))
        if valid:
            for editor in self.editors:
                editor.set_font(font)
            self.set_plugin_font(font)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for editor in self.editors:
            editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)
