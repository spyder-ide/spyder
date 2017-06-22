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
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Signal, Slot
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QHBoxLayout, QLabel,
                            QToolBar, QVBoxLayout)

# Local imports
from spyder.config.base import _, get_conf_path, get_home_dir
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.py3compat import to_text_string, getcwd
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.widgets.comboboxes import PathComboBox


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


class WorkingDirectory(SpyderPluginWidget):
    """Working directory changer plugin."""

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
        SpyderPluginWidget.__init__(self, parent)

        self.toolbar = QToolBar(self)

        # Initialize plugin
        self.initialize_plugin()
        
        self.toolbar.setWindowTitle(self.get_plugin_title())
        # Used to save Window state
        self.toolbar.setObjectName(self.get_plugin_title())

        # Previous dir action
        self.history = []
        self.histindex = None
        self.previous_action = create_action(self, "previous", None,
                                     ima.icon('previous'), _('Back'),
                                     triggered=self.previous_directory)
        self.toolbar.addAction(self.previous_action)

        # Next dir action
        self.history = []
        self.histindex = None
        self.next_action = create_action(self, "next", None,
                                     ima.icon('next'), _('Next'),
                                     triggered=self.next_directory)
        self.toolbar.addAction(self.next_action)

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
        self.toolbar.addWidget(self.pathedit)
        
        # Browse action
        browse_action = create_action(self, "browse", None,
                                      ima.icon('DirOpenIcon'),
                                      _('Browse a working directory'),
                                      triggered=self.select_directory)
        self.toolbar.addAction(browse_action)

        # Parent dir action
        parent_action = create_action(self, "parent", None,
                                      ima.icon('up'),
                                      _('Change to parent directory'),
                                      triggered=self.parent_directory)
        self.toolbar.addAction(parent_action)
                
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
        self.toolbar.setIconSize(QSize(iconsize, iconsize))
        self.main.addToolBar(self.toolbar)
        
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
    def chdir(self, directory, browsing_history=False,
              refresh_explorer=True):
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
            self.set_as_current_console_wd()
        self.refresh_findinfiles.emit()

    def set_as_current_console_wd(self):
        """Set as current console working directory"""
        self.set_current_console_wd.emit(getcwd())
