# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Working Directory Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt import PYQT5
from spyderlib.qt.QtGui import (QToolBar, QLabel, QGroupBox, QVBoxLayout,
                                QHBoxLayout, QButtonGroup)
from spyderlib.qt.QtCore import Signal, Slot
from spyderlib.qt.compat import getexistingdirectory
from spyderlib.qt import qta

import os
import os.path as osp

# Local imports
from spyderlib.utils import encoding
from spyderlib.baseconfig import get_conf_path, _
from spyderlib.utils.qthelpers import get_icon, get_std_icon, create_action

# Package local imports
from spyderlib.widgets.comboboxes import PathComboBox
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage
from spyderlib.py3compat import to_text_string, getcwd


class WorkingDirectoryConfigPage(PluginConfigPage):
    def setup_page(self):
        about_label = QLabel(_("The <b>global working directory</b> is "
                    "the working directory for newly opened <i>consoles</i> "
                    "(Python/IPython consoles and terminals), for the "
                    "<i>file explorer</i>, for the <i>find in files</i> "
                    "plugin and for new files created in the <i>editor</i>."))
        about_label.setWordWrap(True)
        
        startup_group = QGroupBox(_("Startup"))
        startup_bg = QButtonGroup(startup_group)
        startup_label = QLabel(_("At startup, the global working "
                                       "directory is:"))
        startup_label.setWordWrap(True)
        lastdir_radio = self.create_radiobutton(
                                _("the same as in last session"),
                                'startup/use_last_directory', True,
                                _("At startup, Spyder will restore the "
                                        "global directory from last session"),
                                button_group=startup_bg)
        thisdir_radio = self.create_radiobutton(
                                _("the following directory:"),
                                'startup/use_fixed_directory', False,
                                _("At startup, the global working "
                                        "directory will be the specified path"),
                                button_group=startup_bg)
        thisdir_bd = self.create_browsedir("", 'startup/fixed_directory',
                                           getcwd())
        thisdir_radio.toggled.connect(thisdir_bd.setEnabled)
        lastdir_radio.toggled.connect(thisdir_bd.setDisabled)
        thisdir_layout = QHBoxLayout()
        thisdir_layout.addWidget(thisdir_radio)
        thisdir_layout.addWidget(thisdir_bd)

        editor_o_group = QGroupBox(_("Open file"))
        editor_o_label = QLabel(_("Files are opened from:"))
        editor_o_label.setWordWrap(True)
        editor_o_bg = QButtonGroup(editor_o_group)
        editor_o_radio1 = self.create_radiobutton(
                                _("the current file directory"),
                                'editor/open/browse_scriptdir',
                                button_group=editor_o_bg)
        editor_o_radio2 = self.create_radiobutton(
                                _("the global working directory"),
                                'editor/open/browse_workdir', 
                                button_group=editor_o_bg)
        
        editor_n_group = QGroupBox(_("New file"))
        editor_n_label = QLabel(_("Files are created in:"))
        editor_n_label.setWordWrap(True)
        editor_n_bg = QButtonGroup(editor_n_group)
        editor_n_radio1 = self.create_radiobutton(
                                _("the current file directory"),
                                'editor/new/browse_scriptdir',
                                button_group=editor_n_bg)
        editor_n_radio2 = self.create_radiobutton(
                                _("the global working directory"),
                                'editor/new/browse_workdir',
                                button_group=editor_n_bg)
        # Note: default values for the options above are set in plugin's
        #       constructor (see below)
        
        other_group = QGroupBox(_("Change to file base directory"))
        newcb = self.create_checkbox
        open_box = newcb(_("When opening a file"),
                         'editor/open/auto_set_to_basedir')
        save_box = newcb(_("When saving a file"),
                         'editor/save/auto_set_to_basedir')
        
        startup_layout = QVBoxLayout()
        startup_layout.addWidget(startup_label)
        startup_layout.addWidget(lastdir_radio)
        startup_layout.addLayout(thisdir_layout)
        startup_group.setLayout(startup_layout)

        editor_o_layout = QVBoxLayout()
        editor_o_layout.addWidget(editor_o_label)
        editor_o_layout.addWidget(editor_o_radio1)
        editor_o_layout.addWidget(editor_o_radio2)
        editor_o_group.setLayout(editor_o_layout)

        editor_n_layout = QVBoxLayout()
        editor_n_layout.addWidget(editor_n_label)
        editor_n_layout.addWidget(editor_n_radio1)
        editor_n_layout.addWidget(editor_n_radio2)
        editor_n_group.setLayout(editor_n_layout)
        
        other_layout = QVBoxLayout()
        other_layout.addWidget(open_box)
        other_layout.addWidget(save_box)
        other_group.setLayout(other_layout)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(about_label)
        vlayout.addSpacing(10)
        vlayout.addWidget(startup_group)
        vlayout.addWidget(editor_o_group)
        vlayout.addWidget(editor_n_group)
        vlayout.addWidget(other_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class WorkingDirectory(QToolBar, SpyderPluginMixin):
    """
    Working directory changer widget
    """
    CONF_SECTION = 'workingdir'
    CONFIGWIDGET_CLASS = WorkingDirectoryConfigPage
    LOG_PATH = get_conf_path(CONF_SECTION)

    sig_option_changed = Signal(str, object)
    set_previous_enabled = Signal(bool)
    set_next_enabled = Signal(bool)
    redirect_stdio = Signal(bool)
    set_explorer_cwd = Signal(str)
    refresh_findinfiles = Signal()
    set_current_console_wd = Signal(str)
    
    def __init__(self, parent, workdir=None, **kwds):
        if PYQT5:
            super(WorkingDirectory, self).__init__(parent, **kwds)
        else:
            QToolBar.__init__(self, parent)
            SpyderPluginMixin.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()
        
        self.setWindowTitle(self.get_plugin_title()) # Toolbar title
        self.setObjectName(self.get_plugin_title()) # Used to save Window state
        
        # Previous dir action
        self.history = []
        self.histindex = None
        self.previous_action = create_action(self, "previous", None,
                                     qta.icon('fa.arrow-left'), _('Back'),
                                     triggered=self.previous_directory)
        self.addAction(self.previous_action)
        
        # Next dir action
        self.history = []
        self.histindex = None
        self.next_action = create_action(self, "next", None,
                                     qta.icon('fa.arrow-right'), _('Next'),
                                     triggered=self.next_directory)
        self.addAction(self.next_action)
        
        # Enable/disable previous/next actions
        self.set_previous_enabled.connect(self.previous_action.setEnabled)
        self.set_next_enabled.connect(self.next_action.setEnabled)
        
        # Path combo box
        adjust = self.get_option('working_dir_adjusttocontents')
        self.pathedit = PathComboBox(self, adjust_to_contents=adjust)
        self.pathedit.setToolTip(_("This is the working directory for newly\n"
                               "opened consoles (Python/IPython consoles and\n"
                               "terminals), for the file explorer, for the\n"
                               "find in files plugin and for new files\n"
                               "created in the editor"))
        self.pathedit.open_dir.connect(self.chdir)
        self.pathedit.setMaxCount(self.get_option('working_dir_history'))
        wdhistory = self.load_wdhistory( workdir )
        if workdir is None:
            if self.get_option('startup/use_last_directory'):
                if wdhistory:
                    workdir = wdhistory[0]
                else:
                    workdir = "."
            else:
                workdir = self.get_option('startup/fixed_directory', ".")
                if not osp.isdir(workdir):
                    workdir = "."
        self.chdir(workdir)
        self.pathedit.addItems( wdhistory )
        self.refresh_plugin()
        self.addWidget(self.pathedit)
        
        # Browse action
        browse_action = create_action(self, "browse", None,
                                      qta.icon('fa.folder'),
                                      _('Browse a working directory'),
                                      triggered=self.select_directory)
        self.addAction(browse_action)
        
        # Set current console working directory action
        setwd_action = create_action(self, icon=qta.icon('fa.check'),
                                     text=_("Set as current console's "
                                                  "working directory"),
                                     triggered=self.set_as_current_console_wd)
        self.addAction(setwd_action)
        
        # Parent dir action
        parent_action = create_action(self, "parent", None,
                                      qta.icon('fa.arrow-up'),
                                      _('Change to parent directory'),
                                      triggered=self.parent_directory)
        self.addAction(parent_action)
                
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _('Global working directory')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_std_icon('DirOpenIcon')
        
    def get_plugin_actions(self):
        """Setup actions"""
        return (None, None)
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.redirect_stdio.connect(self.main.redirect_internalshell_stdio)
        self.main.console.shell.refresh.connect(self.refresh_plugin)
        self.main.addToolBar(self)
        
    def refresh_plugin(self):
        """Refresh widget"""
        curdir = getcwd()
        self.pathedit.add_text(curdir)
        self.save_wdhistory()
        self.set_previous_enabled.emit(
                             self.histindex is not None and self.histindex > 0)
        self.set_next_enabled.emit(self.histindex is not None and \
                                   self.histindex < len(self.history)-1)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    #------ Public API ---------------------------------------------------------
    def load_wdhistory(self, workdir=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.LOG_PATH):
            wdhistory, _ = encoding.readlines(self.LOG_PATH)
            wdhistory = [name for name in wdhistory if os.path.isdir(name)]
        else:
            if workdir is None:
                workdir = getcwd()
            wdhistory = [ workdir ]
        return wdhistory
    
    def save_wdhistory(self):
        """Save history to a text file in user home directory"""
        text = [ to_text_string( self.pathedit.itemText(index) ) \
                 for index in range(self.pathedit.count()) ]
        encoding.writelines(text, self.LOG_PATH)
    
    @Slot()
    def select_directory(self):
        """Select directory"""
        self.redirect_stdio.emit(False)
        directory = getexistingdirectory(self.main, _("Select directory"),
                                         getcwd())
        if directory:
            self.chdir(directory)
        self.redirect_stdio.emit(True)
    
    @Slot()
    def previous_directory(self):
        """Back to previous directory"""
        self.histindex -= 1
        self.chdir(browsing_history=True)
    
    @Slot()
    def next_directory(self):
        """Return to next directory"""
        self.histindex += 1
        self.chdir(browsing_history=True)
    
    @Slot()
    def parent_directory(self):
        """Change working directory to parent directory"""
        self.chdir(os.path.join(getcwd(), os.path.pardir))
        
    def chdir(self, directory=None, browsing_history=False,
              refresh_explorer=True):
        """Set directory as working directory"""
        # Working directory history management
        if directory is not None:
            directory = osp.abspath(to_text_string(directory))
        if browsing_history:
            directory = self.history[self.histindex]
        elif directory in self.history:
            self.histindex = self.history.index(directory)
        else:
            if self.histindex is None:
                self.history = []
            else:
                self.history = self.history[:self.histindex+1]
            self.history.append(directory)
            self.histindex = len(self.history)-1
        
        # Changing working directory
        os.chdir( to_text_string(directory) )
        self.refresh_plugin()
        if refresh_explorer:
            self.set_explorer_cwd.emit(directory)
        self.refresh_findinfiles.emit()
    
    @Slot()
    def set_as_current_console_wd(self):
        """Set as current console working directory"""
        self.set_current_console_wd.emit(getcwd())
