# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Working Directory Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os
import os.path as osp

# Third party imports
from qtpy import PYQT5
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Signal, Slot
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QHBoxLayout, QLabel,
                            QToolBar, QVBoxLayout)

# Local imports
from spyder.config.base import _, get_conf_path, get_home_dir
from spyder.plugins import SpyderPluginMixin
from spyder.plugins.configdialog import PluginConfigPage
from spyder.py3compat import to_text_string, getcwd
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.widgets.comboboxes import PathComboBox


class WorkingDirectoryConfigPage(PluginConfigPage):
    def setup_page(self):
        about_label = QLabel(_("The <b>current working directory</b> is "
                    "the working directory for newly opened <i>consoles</i> "
                    "(Python/IPython consoles and terminals), for the "
                    "<i>file explorer</i>, for the <i>find in files</i> "
                    "plugin and for new files created in the <i>editor</i>."))
        about_label.setWordWrap(True)

        startup_group = QGroupBox(_("Startup"))
        startup_bg = QButtonGroup(startup_group)
        startup_label = QLabel(_("At startup, the current working "
                                 "directory is:"))
        startup_label.setWordWrap(True)
        lastdir_radio = self.create_radiobutton(
                                _("The current project directory "
                                  "or user home directory "
                                  "(if no project is active)"),
                                'startup/use_project_or_home_directory',
                                True,
                                _("At startup,"),  # TODO
                                button_group=startup_bg)
        thisdir_radio = self.create_radiobutton(
                                _("the following directory:"),
                                'startup/use_fixed_directory', False,
                                _("At startup, the current working "
                                  "directory will be the specified path"),
                                button_group=startup_bg)
        thisdir_bd = self.create_browsedir("", 'startup/fixed_directory',
                                           getcwd())
        thisdir_radio.toggled.connect(thisdir_bd.setEnabled)
        lastdir_radio.toggled.connect(thisdir_bd.setDisabled)
        thisdir_layout = QHBoxLayout()
        thisdir_layout.addWidget(thisdir_radio)
        thisdir_layout.addWidget(thisdir_bd)

        startup_layout = QVBoxLayout()
        startup_layout.addWidget(startup_label)
        startup_layout.addWidget(lastdir_radio)
        startup_layout.addLayout(thisdir_layout)
        startup_group.setLayout(startup_layout)

        # Console Directory

        console_group = QGroupBox(_("Console directory"))
        console_label = QLabel(_("The directory when a new console is open:"))
        console_label.setWordWrap(True)
        console_bg = QButtonGroup(console_group)
        console_project_radio = self.create_radiobutton(
                                _("The current project directory "
                                  "or user home directory "
                                  "(if no project is active)"),
                                'console/use_project_or_home_directory',
                                True,
                                button_group=console_bg)
        console_cwd_radio = self.create_radiobutton(
                                _("The current working directory"),
                                'console/use_cwd',
                                False,
                                button_group=console_bg)

        console_dir_radio = self.create_radiobutton(
                                _("the following directory:"),
                                'console/use_fixed_directory', False,
                                _("The directory when a new console "
                                  "is open will be the specified path"),
                                button_group=console_bg)
        console_dir_bd = self.create_browsedir("", 'console/fixed_directory',
                                               getcwd())
        console_dir_radio.toggled.connect(console_dir_bd.setEnabled)
        console_project_radio.toggled.connect(console_dir_bd.setDisabled)
        console_cwd_radio.toggled.connect(console_dir_bd.setDisabled)
        console_dir_layout = QHBoxLayout()
        console_dir_layout.addWidget(console_dir_radio)
        console_dir_layout.addWidget(console_dir_bd)

        console_layout = QVBoxLayout()
        console_layout.addWidget(console_label)
        console_layout.addWidget(console_project_radio)
        console_layout.addWidget(console_cwd_radio)
        console_layout.addLayout(console_dir_layout)
        console_group.setLayout(console_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(about_label)
        vlayout.addSpacing(10)
        vlayout.addWidget(startup_group)
        vlayout.addWidget(console_group)
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
                                     ima.icon('previous'), _('Back'),
                                     triggered=self.previous_directory)
        self.addAction(self.previous_action)
        
        # Next dir action
        self.history = []
        self.histindex = None
        self.next_action = create_action(self, "next", None,
                                     ima.icon('next'), _('Next'),
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
        self.pathedit.activated[str].connect(self.chdir)
        self.pathedit.setMaxCount(self.get_option('working_dir_history'))
        wdhistory = self.load_wdhistory(workdir)
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
        self.pathedit.addItems(wdhistory)
        self.pathedit.selected_text = self.pathedit.currentText()
        self.refresh_plugin()
        self.addWidget(self.pathedit)
        
        # Browse action
        browse_action = create_action(self, "browse", None,
                                      ima.icon('DirOpenIcon'),
                                      _('Browse a working directory'),
                                      triggered=self.select_directory)
        self.addAction(browse_action)

        # Parent dir action
        parent_action = create_action(self, "parent", None,
                                      ima.icon('up'),
                                      _('Change to parent directory'),
                                      triggered=self.parent_directory)
        self.addAction(parent_action)
                
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return _('Global working directory')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('DirOpenIcon')
        
    def get_plugin_actions(self):
        """Setup actions"""
        return (None, None)
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.redirect_stdio.connect(self.main.redirect_internalshell_stdio)
        self.main.console.shell.refresh.connect(self.refresh_plugin)
        iconsize = 24 
        self.setIconSize(QSize(iconsize, iconsize))
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
                workdir = get_home_dir()
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
        self.chdir(directory='', browsing_history=True)
    
    @Slot()
    def next_directory(self):
        """Return to next directory"""
        self.histindex += 1
        self.chdir(directory='', browsing_history=True)
    
    @Slot()
    def parent_directory(self):
        """Change working directory to parent directory"""
        self.chdir(os.path.join(getcwd(), os.path.pardir))

    @Slot(str)
    @Slot(str, bool)
    @Slot(str, bool, bool)
    @Slot(str, bool, bool, bool)
    def chdir(self, directory, browsing_history=False,
              refresh_explorer=True, refresh_console=True):
        """Set directory as working directory"""
        if directory:
            directory = osp.abspath(to_text_string(directory))

        # Working directory history management
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
        if refresh_console:
            self.set_as_current_console_wd()
        self.refresh_findinfiles.emit()

    def set_as_current_console_wd(self):
        """Set as current console working directory"""
        self.set_current_console_wd.emit(getcwd())
