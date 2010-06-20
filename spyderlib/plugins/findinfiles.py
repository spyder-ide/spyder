# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Find in Files Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os

# For debugging purpose:
STDOUT = sys.stdout

from PyQt4.QtCore import SIGNAL

# Local imports
from spyderlib.config import CONF
from spyderlib.widgets.findinfiles import FindInFilesWidget
from spyderlib.plugins import SpyderPluginMixin


class FindInFiles(FindInFilesWidget, SpyderPluginMixin):
    """Find in files DockWidget"""
    ID = 'find_in_files'
    def __init__(self, parent=None):
        supported_encodings = CONF.get(self.ID, 'supported_encodings')
        
        search_path = CONF.get(self.ID, 'search_path', None)        
        self.search_text_samples = CONF.get(self.ID, 'search_text_samples')
        search_text = CONF.get(self.ID, 'search_text')
        search_text = [txt for txt in search_text \
                       if txt not in self.search_text_samples]
        search_text += self.search_text_samples
        
        search_text_regexp = CONF.get(self.ID, 'search_text_regexp')
        include = CONF.get(self.ID, 'include')
        include_idx = CONF.get(self.ID, 'include_idx', None)
        include_regexp = CONF.get(self.ID, 'include_regexp')
        exclude = CONF.get(self.ID, 'exclude')
        exclude_idx = CONF.get(self.ID, 'exclude_idx', None)
        exclude_regexp = CONF.get(self.ID, 'exclude_regexp')
        in_python_path = CONF.get(self.ID, 'in_python_path')
        more_options = CONF.get(self.ID, 'more_options')
        FindInFilesWidget.__init__(self, parent,
                                   search_text, search_text_regexp, search_path,
                                   include, include_idx, include_regexp,
                                   exclude, exclude_idx, exclude_regexp,
                                   supported_encodings,
                                   in_python_path, more_options)
        SpyderPluginMixin.__init__(self, parent)
        
        self.connect(self, SIGNAL('toggle_visibility(bool)'), self.toggle)
        
    def toggle(self, state):
        """Toggle widget visibility"""
        if self.dockwidget:
            self.dockwidget.setVisible(state)
    
    def refreshdir(self):
        """Refresh search directory"""
        self.find_options.set_directory(os.getcwdu())
        
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr("Find in files")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.find_options.search_text
    
    def get_plugin_actions(self):
        """Setup actions"""
        return (None, None)
        
    def refresh_plugin(self):
        """Refresh widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
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
            CONF.set(self.ID, 'search_text', search_text)
            CONF.set(self.ID, 'search_text_regexp', text_re)
            CONF.set(self.ID, 'search_path', search_path)
            CONF.set(self.ID, 'include', include)
            CONF.set(self.ID, 'include_idx', include_idx)
            CONF.set(self.ID, 'include_regexp', include_re)
            CONF.set(self.ID, 'exclude', exclude)
            CONF.set(self.ID, 'exclude_idx', exclude_idx)
            CONF.set(self.ID, 'exclude_regexp', exclude_re)
            CONF.set(self.ID, 'in_python_path', in_python_path)
            CONF.set(self.ID, 'more_options', more_options)
        return True

