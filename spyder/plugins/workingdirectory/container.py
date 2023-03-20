# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Working Directory widget.
"""

# Standard library imports
import logging
import os
import os.path as osp

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Signal, Slot
from qtpy.QtWidgets import QSizePolicy, QWidget

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.widgets.toolbars import ApplicationToolbar
from spyder.config.base import get_home_dir
from spyder.utils.misc import getcwd_or_home
from spyder.utils.stylesheet import APP_TOOLBAR_STYLESHEET
from spyder.widgets.comboboxes import PathComboBox


# Logging
logger = logging.getLogger(__name__)


# ---- Constants
# ----------------------------------------------------------------------------
class WorkingDirectoryActions:
    Previous = 'previous_action'
    Next = "next_action"
    Browse = "browse_action"
    Parent = "parent_action"


class WorkingDirectoryToolbarSections:
    Main = "main_section"


class WorkingDirectoryToolbarItems:
    PathComboBox = 'path_combo'


# ---- Widgets
# ----------------------------------------------------------------------------
class WorkingDirectoryToolbar(ApplicationToolbar):
    ID = 'working_directory_toolbar'


class WorkingDirectoryComboBox(PathComboBox):

    def __init__(self, parent):
        super().__init__(
            parent,
            adjust_to_contents=False,
            id_=WorkingDirectoryToolbarItems.PathComboBox,
            elide_text=True
        )

        # Set min width
        self.setMinimumWidth(140)

    def sizeHint(self):
        """Recommended size when there are toolbars to the right."""
        return QSize(400, 10)

    def enterEvent(self, event):
        """Set current path as the tooltip of the widget on hover."""
        self.setToolTip(self.currentText())


class WorkingDirectorySpacer(QWidget):
    ID = 'working_directory_spacer'

    def __init__(self, parent):
        super().__init__(parent)

        # Make it expand
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Set style
        self.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))


# ---- Container
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
        self.pathedit = WorkingDirectoryComboBox(self)
        spacer = WorkingDirectorySpacer(self)

        # Widget Setup
        self.toolbar.setWindowTitle(title)
        self.toolbar.setObjectName(title)
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
            triggered=self._previous_directory,
        )
        self.next_action = self.create_action(
            WorkingDirectoryActions.Next,
            text=_('Next'),
            tip=_('Next'),
            icon=self.create_icon('next'),
            triggered=self._next_directory,
        )
        browse_action = self.create_action(
            WorkingDirectoryActions.Browse,
            text=_('Browse a working directory'),
            tip=_('Browse a working directory'),
            icon=self.create_icon('DirOpenIcon'),
            triggered=self._select_directory,
        )
        parent_action = self.create_action(
            WorkingDirectoryActions.Parent,
            text=_('Change to parent directory'),
            tip=_('Change to parent directory'),
            icon=self.create_icon('up'),
            triggered=self._parent_directory,
        )

        for item in [spacer, self.pathedit, browse_action, parent_action]:
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

    # ---- Private API
    # ------------------------------------------------------------------------
    def _get_init_workdir(self):
        """
        Get the working directory from our config system or return the user
        home directory if none can be found.

        Returns
        -------
        str:
            The initial working directory.
        """
        workdir = get_home_dir()

        if self.get_conf('startup/use_project_or_home_directory'):
            workdir = get_home_dir()
        elif self.get_conf('startup/use_fixed_directory'):
            workdir = self.get_conf('startup/fixed_directory')

            # If workdir can't be found, restore default options.
            if not osp.isdir(workdir):
                self.set_conf('startup/use_project_or_home_directory', True)
                self.set_conf('startup/use_fixed_directory', False)
                workdir = get_home_dir()

        return workdir

    @Slot()
    def _select_directory(self, directory=None):
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
    def _previous_directory(self):
        """Select the previous directory."""
        self.histindex -= 1
        self.chdir(directory='', browsing_history=True)

    @Slot()
    def _next_directory(self):
        """Select the next directory."""
        self.histindex += 1
        self.chdir(directory='', browsing_history=True)

    @Slot()
    def _parent_directory(self):
        """Change working directory to parent one."""
        self.chdir(osp.join(getcwd_or_home(), osp.pardir))

    # ---- Public API
    # ------------------------------------------------------------------------
    def get_workdir(self):
        """
        Get the current working directory.

        Returns
        -------
        str:
            The current working directory.
        """
        return self.pathedit.currentText()

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
            logger.debug(f'Setting cwd to {directory}')
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

    def set_history(self, history, cli_workdir=None):
        """
        Set the current history list.

        Parameters
        ----------
        history: list
            List of string paths.
        cli_workdir: str or None
            Working directory passed on the command line.
        """
        self.set_conf('history', history)
        if history:
            self.pathedit.addItems(history)

        if cli_workdir is None:
            workdir = self._get_init_workdir()
        else:
            logger.debug('Setting cwd passed from the command line')
            workdir = cli_workdir

            # In case users pass an invalid directory on the command line
            if not osp.isdir(workdir):
                workdir = get_home_dir()

        self.chdir(workdir)
