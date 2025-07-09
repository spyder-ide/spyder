# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Explorer Main Widget.
"""

# Standard library imports
import logging
import os.path as osp
import sys

# Third-party imports
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.main import NAME_FILTERS
from spyder.plugins.explorer.widgets.remote_explorer import RemoteExplorer
from spyder.plugins.explorer.widgets.explorer import (
    DirViewActions,
    ExplorerTreeWidget,
)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home

logger = logging.getLogger(__name__)


# ---- Constants
class ExplorerWidgetOptionsMenuSections:
    Files = 'files_section'
    Header = 'header_section'
    Common = 'common_section'


class ExplorerWidgetMainToolbarSections:
    Main = 'main_section'


class ExplorerWidgetActions:
    # Toggles
    ToggleFilter = 'toggle_filter_files_action'

    # Triggers
    Next = 'next_action'
    Parent = 'parent_action'
    Previous = 'previous_action'
    Refresh = 'refresh_action'
    EditNameFilters = 'edit_name_filters_action'


# ---- Main widget
class ExplorerWidget(PluginMainWidget):
    """Explorer widget"""

    # --- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str, str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The path to the directory opened.
    server_id: str
        The server identification from where the directory path is reachable.
    """

    sig_module_created = Signal(str)
    """
    This signal is emitted when a new python module is created.

    Parameters
    ----------
    module: str
        Path to the new module created.
    """

    sig_file_created = Signal(str)
    """
    This signal is emitted to request creating a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to create.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_removed = Signal(str)
    """
    This signal is emitted when a file is removed.

    Parameters
    ----------
    path: str
        File path removed.
    """

    sig_renamed = Signal(str, str)
    """
    This signal is emitted when a file is renamed.

    Parameters
    ----------
    old_path: str
        Old path for renamed file.
    new_path: str
        New path for renamed file.
    """

    sig_tree_removed = Signal(str)
    """
    This signal is emitted when a folder is removed.

    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_tree_renamed = Signal(str, str)
    """
    This signal is emitted when a folder is renamed.

    Parameters
    ----------
    old_path: str
        Old path for renamed folder.
    new_path: str
        New path for renamed folder.
    """

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_open_interpreter_requested = Signal(str)
    """
    This signal is emitted to request opening an interpreter with the given
    path as working directory.

    Parameters
    ----------
    path: str
        Path to use as working directory of interpreter.
    """

    ENABLE_SPINNER = True

    def __init__(self, name, plugin, parent=None):
        """
        Initialize the widget.

        Parameters
        ----------
        name: str
            Name of the container.
        plugin: SpyderDockablePlugin
            Plugin of the container
        parent: QWidget
            Parent of this widget
        """
        super().__init__(name, plugin=plugin, parent=parent)

        # Widgets
        self.stackwidget = QStackedWidget(parent=self)
        self.treewidget = ExplorerTreeWidget(parent=self)
        self.remote_treewidget = RemoteExplorer(parent=self)
        self.stackwidget.addWidget(self.remote_treewidget)
        self.stackwidget.addWidget(self.treewidget)

        # Layouts
        layout = QHBoxLayout()
        layout.addWidget(self.stackwidget)
        self.setLayout(layout)

        # Signals
        self.treewidget.sig_dir_opened.connect(self.sig_dir_opened)
        self.remote_treewidget.sig_dir_opened.connect(self.sig_dir_opened)
        self.remote_treewidget.sig_start_spinner_requested.connect(
            self.start_spinner
        )
        self.remote_treewidget.sig_stop_spinner_requested.connect(
            self.stop_spinner
        )
        self.treewidget.sig_file_created.connect(self.sig_file_created)
        self.treewidget.sig_open_file_requested.connect(
            self.sig_open_file_requested)
        self.treewidget.sig_module_created.connect(self.sig_module_created)
        self.treewidget.sig_open_interpreter_requested.connect(
            self.sig_open_interpreter_requested)
        self.treewidget.sig_renamed.connect(self.sig_renamed)
        self.treewidget.sig_removed.connect(self.sig_removed)
        self.treewidget.sig_run_requested.connect(self.sig_run_requested)
        self.treewidget.sig_tree_removed.connect(self.sig_tree_removed)
        self.treewidget.sig_tree_renamed.connect(self.sig_tree_renamed)
        self.treewidget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_focus_widget(self):
        """Define the widget to focus."""
        return self.treewidget

    def get_title(self):
        """Return the title of the plugin tab."""
        return _("Files")

    def setup(self):
        """Perform the setup of the plugin's menu and actions."""
        # Common actions
        self.previous_action = self.create_action(
            ExplorerWidgetActions.Previous,
            text=_("Previous"),
            icon=self.create_icon('previous'),
            triggered=self.go_to_previous_directory,
        )
        self.next_action = self.create_action(
            ExplorerWidgetActions.Next,
            text=_("Next"),
            icon=self.create_icon('next'),
            triggered=self.go_to_next_directory,
        )
        self.parent_action = self.create_action(
            ExplorerWidgetActions.Parent,
            text=_("Parent"),
            icon=self.create_icon('up'),
            triggered=self.go_to_parent_directory
        )
        self.refresh_action = self.create_action(
            ExplorerWidgetActions.Refresh,
            text=_("Refresh"),
            icon=self.create_icon('refresh'),
            triggered=lambda: self.refresh(force_current=True)
        )
        filters_action = self.create_action(
            ExplorerWidgetActions.EditNameFilters,
            text=_("Edit filter settings..."),
            icon=self.create_icon('filter'),
            triggered=self.edit_filter,
        )

        # Common toolbuttons
        self.filter_button = self.create_action(
            ExplorerWidgetActions.ToggleFilter,
            text="",
            icon=ima.icon('filter'),
            toggled=self.change_filter_state
        )
        self.filter_button.setCheckable(True)

        # Set actions for tree widgets
        self.treewidget.previous_action = self.previous_action
        self.treewidget.next_action = self.next_action
        self.treewidget.filter_button = self.filter_button

        self.remote_treewidget.previous_action = self.previous_action
        self.remote_treewidget.next_action = self.next_action
        self.remote_treewidget.filter_button = self.filter_button

        # Setup widgets
        self.treewidget.setup()
        self.chdir(getcwd_or_home())

        # Menu
        menu = self.get_options_menu()

        hidden_action = self.get_action(DirViewActions.ToggleHiddenFiles)
        for item in [hidden_action, filters_action]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Common,
            )

        # Header actions
        size_column_action = self.get_action(DirViewActions.ToggleSizeColumn)
        type_column_action = self.get_action(DirViewActions.ToggleTypeColumn)
        date_column_action = self.get_action(DirViewActions.ToggleDateColumn)

        for item in [
            size_column_action,
            type_column_action,
            date_column_action,
        ]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Header,
            )

        single_click_action = self.get_action(DirViewActions.ToggleSingleClick)
        self.add_item_to_menu(
            single_click_action,
            menu=menu, section=ExplorerWidgetOptionsMenuSections.Files)

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [
            self.previous_action,
            self.next_action,
            self.parent_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=ExplorerWidgetMainToolbarSections.Main,
            )

        for action in [
            self.remote_treewidget.upload_file_action,
            self.refresh_action,
            self.filter_button,
        ]:
            self.add_corner_widget(action, before=self._options_button)

    def update_actions(self):
        """Handle the update of actions of the plugin."""
        visible_remote_actions = (
            self.get_current_widget() == self.remote_treewidget
        )
        self.refresh_action.setVisible(visible_remote_actions)
        self.remote_treewidget.upload_file_action.setVisible(
            visible_remote_actions
        )

    # ---- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True, server_id=None):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            Directory to set as working directory.
        emit: bool, optional
            Default is True.
        server_id: str, optional
            The server identification from where the directory is reachable.
            Default is None.
        """
        if not server_id:
            self.treewidget.chdir(directory, emit=emit)
            self.stackwidget.setCurrentWidget(self.treewidget)
        else:
            self.start_spinner()
            logger.debug(f"Request ls for {server_id} at {directory}")

            @AsyncDispatcher.QtSlot
            def remote_ls(future):
                self.remote_treewidget.chdir(
                    directory,
                    server_id=server_id,
                    emit=emit,
                    remote_files_manager=future.result()
                )

            self._plugin._get_remote_files_manager(server_id).connect(
                remote_ls
            )
            self.stackwidget.setCurrentWidget(self.remote_treewidget)

        self.update_actions()

    def get_current_folder(self):
        """Get current folder in the tree widget."""
        return self.stackwidget.currentWidget().get_current_folder()

    def set_current_folder(self, folder):
        """
        Set the current folder in the tree widget.

        Parameters
        ----------
        folder: str
            Folder path to set as current folder.
        """
        self.get_current_widget().set_current_folder(folder)

    def go_to_parent_directory(self):
        """Move to parent directory."""
        self.get_current_widget().go_to_parent_directory()

    def go_to_previous_directory(self):
        """Move to previous directory in history."""
        self.get_current_widget().go_to_previous_directory()

    def go_to_next_directory(self):
        """Move to next directory in history."""
        self.get_current_widget().go_to_next_directory()

    def refresh(self, new_path=None, force_current=False):
        """
        Refresh history.

        Parameters
        ----------
        new_path: str, optional
            Path to add to history. Default is None.
        force_current: bool, optional
            Default is True.
        """
        self.get_current_widget().refresh(new_path, force_current)

    def get_current_widget(self):
        """Get the current widget in stackwidget."""
        return self.stackwidget.currentWidget()

    @Slot()
    def edit_filter(self):
        """Edit name filters."""
        # Create Dialog
        dialog = QDialog(self)
        dialog.resize(500, 300)
        dialog.setWindowTitle(_('Edit filter settings'))

        # Create dialog contents
        description_label = QLabel(
            _(
                "Filter files by name, extension, or more using "
                '<a href="https://en.wikipedia.org/wiki/Glob_(programming)">'
                "glob patterns.</a> Please enter the glob patterns of the "
                "files you want to show, separated by commas."
            )
        )
        description_label.setOpenExternalLinks(True)
        description_label.setWordWrap(True)
        filters = QTextEdit(
            ", ".join(self.get_conf('name_filters')),
            parent=self
        )
        layout = QVBoxLayout()
        layout.addWidget(description_label)
        layout.addWidget(filters)

        def handle_ok():
            filter_text = filters.toPlainText()
            filter_text = [f.strip() for f in str(filter_text).split(',')]
            self.get_current_widget().set_name_filters(filter_text)
            dialog.accept()

        def handle_reset():
            self.get_current_widget().set_name_filters(NAME_FILTERS)
            filters.setPlainText(", ".join(self.get_conf('name_filters')))

        # Dialog buttons
        button_box = SpyderDialogButtonBox(
            QDialogButtonBox.Reset
            | QDialogButtonBox.Ok
            | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(handle_ok)
        button_box.rejected.connect(dialog.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(handle_reset)
        layout.addWidget(button_box)
        dialog.setLayout(layout)
        dialog.show()

    def change_filter_state(self):
        self.stackwidget.currentWidget().change_filter_state()

    def update_history(self, directory):
        """
        Update history with directory.

        Parameters
        ----------
        directory: str
            Path to add to history.
        """
        self.treewidget.update_history(directory)


# =============================================================================
# Tests
# =============================================================================
class FileExplorerTest(QWidget):
    def __init__(self, directory=None, file_associations=None):

        self.CONF_SECTION = 'explorer'
        super().__init__()

        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))

        file_associations = (
            {} if file_associations is None else file_associations
        )

        self.explorer = ExplorerWidget('explorer', self, parent=self)
        self.explorer.set_conf('file_associations', file_associations)
        self.explorer._setup()
        self.explorer.setup()
        self.label_dir = QLabel("<b>Open dir:</b>")
        self.label_file = QLabel("<b>Open file:</b>")
        self.label1 = QLabel()
        self.label_dir.setAlignment(Qt.AlignRight)
        self.label2 = QLabel()
        self.label_option = QLabel("<b>Option changed:</b>")
        self.label3 = QLabel()

        # Setup
        self.explorer.set_current_folder(self.directory)
        self.label_file.setAlignment(Qt.AlignRight)
        self.label_option.setAlignment(Qt.AlignRight)

        # Layout
        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.label_file)
        hlayout1.addWidget(self.label1)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.label_dir)
        hlayout2.addWidget(self.label2)

        hlayout3 = QHBoxLayout()
        hlayout3.addWidget(self.label_option)
        hlayout3.addWidget(self.label3)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.explorer)
        vlayout.addLayout(hlayout1)
        vlayout.addLayout(hlayout2)
        vlayout.addLayout(hlayout3)
        self.setLayout(vlayout)

        # Signals
        self.explorer.sig_dir_opened.connect(self.label2.setText)
        self.explorer.sig_dir_opened.connect(
            lambda: self.explorer.treewidget.refresh('..'))
        self.explorer.sig_open_file_requested.connect(self.label1.setText)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    test = FileExplorerTest()
    test.resize(640, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()
