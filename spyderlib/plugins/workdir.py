# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Working Directory widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QToolBar, QLabel, QFileDialog
from PyQt4.QtCore import SIGNAL

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import encoding
from spyderlib.config import CONF, get_conf_path, get_icon
from spyderlib.qthelpers import get_std_icon, create_action

# Package local imports
from spyderlib.widgets.comboboxes import PathComboBox
from spyderlib.plugins import PluginMixin
from spyderlib.plugins.explorer import Explorer


class WorkingDirectory(QToolBar, PluginMixin):
    """
    Working directory changer widget
    """
    ID = 'workingdir'
#    allowed_areas = Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea
#    location = Qt.TopDockWidgetArea
    log_path = get_conf_path('.workingdir')
    def __init__(self, parent, workdir=None):
        QToolBar.__init__(self, parent)
        PluginMixin.__init__(self, parent)
        
        self.setWindowTitle(self.get_widget_title()) # Toolbar title
        self.setObjectName(self.get_widget_title()) # Used to save Window state
        
        self.addWidget( QLabel(self.tr("Working directory:")+" ") )
        
        # Previous dir action
        self.history = []
        self.histindex = None
        self.previous_action = create_action(self, "previous", None,
                                     get_icon('previous.png'), self.tr('Back'),
                                     triggered=self.previous_directory)
        self.addAction(self.previous_action)
        
        # Next dir action
        self.history = []
        self.histindex = None
        self.next_action = create_action(self, "next", None,
                                     get_icon('next.png'), self.tr('Next'),
                                     triggered=self.next_directory)
        self.addAction(self.next_action)
        
        # Enable/disable previous/next actions
        self.connect(self, SIGNAL("set_previous_enabled(bool)"),
                     self.previous_action.setEnabled)
        self.connect(self, SIGNAL("set_next_enabled(bool)"),
                     self.next_action.setEnabled)
        
        # Path combo box
        adjust = CONF.get('shell', 'working_dir_adjusttocontents', False)
        self.pathedit = PathComboBox(self, adjust_to_contents=adjust)
        self.pathedit.setToolTip(self.tr("Working directory"))
        self.connect(self.pathedit, SIGNAL("open_dir(QString)"),
                     self.pathedit_activated)
        self.pathedit.setMaxCount(CONF.get('shell', 'working_dir_history'))
        wdhistory = self.load_wdhistory( workdir )
        if workdir is None:
            if wdhistory:
                workdir = wdhistory[0]
            else:
                workdir = "."
        self.chdir(workdir)
        self.pathedit.addItems( wdhistory )
        self.refresh()
        self.addWidget(self.pathedit)
        
        # Browse action
        browse_action = create_action(self, "browse", None,
                                      get_std_icon('DirOpenIcon'),
                                      self.tr('Browse a working directory'),
                                      triggered=self.select_directory)
        self.addAction(browse_action)
        
        # Parent dir action
        parent_action = create_action(self, "parent", None,
                                      get_icon('up.png'),
                                      self.tr('Change to parent directory'),
                                      triggered=self.parent_directory)
        self.addAction(parent_action)
                
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Working directory')
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def load_wdhistory(self, workdir=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            wdhistory, _ = encoding.readlines(self.log_path)
            wdhistory = [name for name in wdhistory if os.path.isdir(name)]
        else:
            if workdir is None:
                workdir = os.getcwdu()
            wdhistory = [ workdir ]
        return wdhistory
    
    def save_wdhistory(self):
        """Save history to a text file in user home directory"""
        text = [ unicode( self.pathedit.itemText(index) ) \
                 for index in range(self.pathedit.count()) ]
        encoding.writelines(text, self.log_path)
        
    def refresh(self):
        """Refresh widget"""
        curdir = os.getcwdu()
        index = self.pathedit.findText(curdir)
        while index!=-1:
            self.pathedit.removeItem(index)
            index = self.pathedit.findText(curdir)
        self.pathedit.insertItem(0, curdir)
        self.pathedit.setCurrentIndex(0)
        self.save_wdhistory()
        self.emit(SIGNAL("set_previous_enabled(bool)"),
                  self.histindex is not None and self.histindex > 0)
        self.emit(SIGNAL("set_next_enabled(bool)"),
                  self.histindex is not None and \
                  self.histindex < len(self.history)-1)
        
    def select_directory(self):
        """Select directory"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        directory = QFileDialog.getExistingDirectory(self.main,
                    self.tr("Select directory"), os.getcwdu())
        if not directory.isEmpty():
            self.chdir(directory)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        
    def previous_directory(self):
        """Back to previous directory"""
        self.histindex -= 1
        self.chdir(browsing_history=True)
        
    def next_directory(self):
        """Return to next directory"""
        self.histindex += 1
        self.chdir(browsing_history=True)
        
    def parent_directory(self):
        """Change working directory to parent directory"""
        self.chdir(os.path.join(os.getcwdu(), os.path.pardir))
        
    def chdir(self, directory=None, browsing_history=False):
        """Set directory as working directory"""
        # Working directory history management
        if browsing_history:
            directory = self.history[self.histindex]
        else:
            if self.histindex is None:
                self.history = []
            else:
                self.history = self.history[:self.histindex+1]
            self.history.append( osp.abspath((unicode(directory))) )
            self.histindex = len(self.history)-1
        
        # Changing working directory
        os.chdir( unicode(directory) )
        self.refresh()
        if not isinstance(self.sender(), Explorer):
            # Explorer is not the sender: let's refresh it
            self.emit(SIGNAL("refresh_explorer()"))
        self.emit(SIGNAL("refresh_findinfiles()"))
        
    def pathedit_activated(self, directory):
        """Path combo box activated"""
        if self.main is not None:
            # Give focus to interactive shell
            self.main.console.shell.setFocus()
        self.chdir(directory)

