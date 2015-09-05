# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Find in Files Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import QApplication
from spyderlib.qt.QtCore import SIGNAL, Signal

# Local imports
from spyderlib.baseconfig import _
from spyderlib.utils.qthelpers import create_action
from spyderlib.widgets.findinfiles import FindInFilesWidget
from spyderlib.plugins import SpyderPluginMixin
from spyderlib.py3compat import getcwd


class FindInFiles(FindInFilesWidget, SpyderPluginMixin):
    """Find in files DockWidget"""
    CONF_SECTION = 'find_in_files'
    sig_option_changed = Signal(str, object)
    def __init__(self, parent=None):
        supported_encodings = self.get_option('supported_encodings')
        
        search_path = self.get_option('search_path', None)        
        self.search_text_samples = self.get_option('search_text_samples')
        search_text = self.get_option('search_text')
        search_text = [txt for txt in search_text \
                       if txt not in self.search_text_samples]
        search_text += self.search_text_samples
        
        search_text_regexp = self.get_option('search_text_regexp')
        include = self.get_option('include')
        include_idx = self.get_option('include_idx', None)
        include_regexp = self.get_option('include_regexp')
        exclude = self.get_option('exclude')
        exclude_idx = self.get_option('exclude_idx', None)
        exclude_regexp = self.get_option('exclude_regexp')
        in_python_path = self.get_option('in_python_path')
        more_options = self.get_option('more_options')
        FindInFilesWidget.__init__(self, parent,
                                   search_text, search_text_regexp, search_path,
                                   include, include_idx, include_regexp,
                                   exclude, exclude_idx, exclude_regexp,
                                   supported_encodings,
                                   in_python_path, more_options)
        SpyderPluginMixin.__init__(self, parent)
        
        # Initialize plugin
        self.initialize_plugin()
        
        self.connect(self, SIGNAL('toggle_visibility(bool)'), self.toggle)
        
    def toggle(self, state):
        """Toggle widget visibility"""
        if self.dockwidget:
            self.dockwidget.setVisible(state)
    
    def refreshdir(self):
        """Refresh search directory"""
        self.find_options.set_directory(getcwd())

    def findinfiles_callback(self):
        """Find in files callback"""
        widget = QApplication.focusWidget()
        if not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        text = ''
        try:
            if widget.has_selected_text():
                text = widget.get_selected_text()
        except AttributeError:
            # This is not a text widget deriving from TextEditBaseWidget
            pass
        self.set_search_text(text)
        if text:
            self.find()
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _("Find in files")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.find_options.search_text
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.get_pythonpath_callback = self.main.get_spyder_pythonpath
        self.main.add_dockwidget(self)
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.connect(self.main.workingdirectory,
                     SIGNAL("refresh_findinfiles()"), self.refreshdir)
        
        findinfiles_action = create_action(self, _("&Find in files"),
                                   icon='findf.png',
                                   triggered=self.findinfiles_callback,
                                   tip=_("Search text in multiple files"))        
        
        self.main.search_menu_actions += [None, findinfiles_action]
        self.main.search_toolbar_actions += [None, findinfiles_action]
    
    def refresh_plugin(self):
        """Refresh widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.closing_widget()  # stop search thread and clean-up
        options = self.find_options.get_options(all=True)
        if options is not None:
            search_text, text_re, search_path, \
            include, include_idx, include_re, \
            exclude, exclude_idx, exclude_re, \
            in_python_path, more_options = options
            hist_limit = 15
            search_text = search_text[:hist_limit]
            search_path = search_path[:hist_limit]
            include = include[:hist_limit]
            exclude = exclude[:hist_limit]
            self.set_option('search_text', search_text)
            self.set_option('search_text_regexp', text_re)
            self.set_option('search_path', search_path)
            self.set_option('include', include)
            self.set_option('include_idx', include_idx)
            self.set_option('include_regexp', include_re)
            self.set_option('exclude', exclude)
            self.set_option('exclude_idx', exclude_idx)
            self.set_option('exclude_regexp', exclude_re)
            self.set_option('in_python_path', in_python_path)
            self.set_option('more_options', more_options)
        return True
