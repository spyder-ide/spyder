# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Working Directory widget.
"""

# Standard library imports
import os
import os.path as osp

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.widgets.toolbars import ApplicationToolbar
from spyder.config.base import get_home_dir
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.comboboxes import PathComboBox


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class WorkingDirectoryActions:
    Previous = 'previous_action'
    Next = "next_action"
    Browse = "browse_action"
    Parent = "parent_action"


class WorkingDirectoryToolbarSections:
    Main = "main_section"


# --- Widgets
# ----------------------------------------------------------------------------
class WorkingDirectoryToolbar(ApplicationToolbar):
    ID = 'working_directory_toolbar'


# --- Container
# ----------------------------------------------------------------------------
class WorkingDirectoryContainer(PluginMainContainer):
    """Container for the working directory toolbar."""

    # Signals
    sig_current_directory_changed = Signal(str)
    """
    This signal is emitted when the current directory has changed.

    Parameters
    ----------
    new_working_directory: str
        The new new working directory path.
    """

    # ---- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self):

        # Variables
        self.history = self.get_conf('history', [])
        self.histindex = None

        # Widgets
        title = _('Current working directory')
        self.toolbar = WorkingDirectoryToolbar(self, title)
        self.pathedit = PathComboBox(
            self,
            adjust_to_contents=self.get_conf('working_dir_adjusttocontents'),
        )

        # Widget Setup
        self.toolbar.setWindowTitle(title)
        self.toolbar.setObjectName(title)
        self.pathedit.setToolTip(
            _(
                "This is the working directory for newly\n"
                "opened IPython consoles, for the Files\n"
                "and Find panes and for new files\n"
                "created in the editor"
            )
        )
        self.pathedit.setMaxCount(self.get_conf('working_dir_history'))
        self.pathedit.selected_text = self.pathedit.currentText()

        # Signals
        self.pathedit.open_dir.connect(self.chdir)
        self.pathedit.activated[str].connect(self.chdir)

        # Actions
        self.previous_action = self.create_action(
            WorkingDirectoryActions.Previous,
            text=_('Back'),
            tip=_('Back'),
            icon=self.create_icon('previous'),
            triggered=self.previous_directory,
        )
        self.next_action = self.create_action(
            WorkingDirectoryActions.Next,
            text=_('Next'),
            tip=_('Next'),
            icon=self.create_icon('next'),
            triggered=self.next_directory,
        )
        browse_action = self.create_action(
            WorkingDirectoryActions.Browse,
            text=_('Browse a working directory'),
            tip=_('Browse a working directory'),
            icon=self.create_icon('DirOpenIcon'),
            triggered=self.select_directory,
        )
        parent_action = self.create_action(
            WorkingDirectoryActions.Parent,
            text=_('Change to parent directory'),
            tip=_('Change to parent directory'),
            icon=self.create_icon('up'),
            triggered=self.parent_directory,
        )

        for item in [self.pathedit,
                     browse_action, parent_action]:
            self.add_item_to_toolbar(
                item,
                self.toolbar,
                section=WorkingDirectoryToolbarSections.Main,
            )

    def update_actions(self):
        self.previous_action.setEnabled(
            self.histindex is not None and self.histindex > 0)
        self.next_action.setEnabled(
            self.histindex is not None
            and self.histindex < len(self.history) - 1
        )

    @on_conf_change(option='history')
    def on_history_update(self, value):
        self.history = value

    # --- API
    # ------------------------------------------------------------------------
    def get_workdir(self):
        """
        Get the working directory from our config system or return the user
        home directory if none could be found.

        Returns
        -------
        str:
            The current working directory.
        """
        if self.get_conf('startup/use_fixed_directory', ''):
            workdir = self.get_conf('startup/fixed_directory')
        elif self.get_conf('console/use_project_or_home_directory', ''):
            workdir = get_home_dir()
        else:
            workdir = self.get_conf('console/fixed_directory', '')

        if not osp.isdir(workdir):
            workdir = get_home_dir()

        return workdir

    @Slot()
    def select_directory(self, directory=None):
        """
        Select working directory.

        Parameters
        ----------
        directory: str, optional
            The directory to change to.

        Notes
        -----
        If directory is None, a get directory dialog will be used.
        """
        if directory is None:
            self.sig_redirect_stdio_requested.emit(False)
            directory = getexistingdirectory(
                self,
                _("Select directory"),
                getcwd_or_home(),
            )
            self.sig_redirect_stdio_requested.emit(True)

        if directory:
            self.chdir(directory)

    @Slot()
    def previous_directory(self):
        """Select the previous directory."""
        self.histindex -= 1
        self.chdir(directory='', browsing_history=True)

    @Slot()
    def next_directory(self):
        """Select the next directory."""
        self.histindex += 1
        self.chdir(directory='', browsing_history=True)

    @Slot()
    def parent_directory(self):
        """Change working directory to parent one."""
        self.chdir(osp.join(getcwd_or_home(), osp.pardir))

    @Slot(str)
    @Slot(str, bool)
    @Slot(str, bool, bool)
    def chdir(self, directory, browsing_history=False, emit=True):
        """
        Set `directory` as working directory.

        Parameters
        ----------
        directory: str
            The new working directory.
        browsing_history: bool, optional
            Add the new `directory` to the browsing history. Default is False.
        emit: bool, optional
            Emit a signal when changing the working directory.
            Default is True.
        """
        if directory:
            directory = osp.abspath(str(directory))

        # Working directory history management
        if browsing_history:
            directory = self.history[self.histindex]
        elif directory in self.history:
            self.histindex = self.history.index(directory)
        else:
            if self.histindex is None:
                self.history = []
            else:
                self.history = self.history[:self.histindex + 1]

            self.history.append(directory)
            self.histindex = len(self.history) - 1

        # Changing working directory
        try:
            os.chdir(directory)
            self.pathedit.add_text(directory)
            self.update_actions()

            if emit:
                self.sig_current_directory_changed.emit(directory)

        except OSError:
            self.history.pop(self.histindex)

    def get_history(self):
        """
        Get the current history list.

        Returns
        -------
        list
            List of string paths.
        """
        return [str(self.pathedit.itemText(index)) for index
                in range(self.pathedit.count())]

    def set_history(self, history):
        """
        Set the current history list.

        Parameters
        ----------
        history: list
            List of string paths.
        """
        self.set_conf('history', history)
        if history:
            self.pathedit.addItems(history)

        if self.get_conf('workdir', None) is None:
            workdir = self.get_workdir()
        else:
            workdir = self.get_conf('workdir')

        self.chdir(workdir)
