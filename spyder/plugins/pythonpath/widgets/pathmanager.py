# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder path manager."""

# Standard library imports
from collections import OrderedDict
import os
import os.path as osp
import sys

# Third party imports
from qtpy import PYSIDE2
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
)

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.plugins.pythonpath.utils import check_path, get_system_pythonpath
from spyder.utils.environ import (
    get_user_environment_variables,
    get_user_env,
    set_user_env,
)
from spyder.utils.misc import getcwd_or_home
from spyder.utils.stylesheet import (
    AppStyle,
    MAC,
    PANES_TOOLBAR_STYLESHEET,
    WIN
)
from spyder.widgets.emptymessage import EmptyMessageWidget


class PathManagerToolbuttons:
    MoveTop = 'move_top'
    MoveUp = 'move_up'
    MoveDown = 'move_down'
    MoveToBottom = 'move_to_bottom'
    AddPath = 'add_path'
    RemovePath = 'remove_path'
    ImportPaths = 'import_paths'
    ExportPaths = 'export_paths'
    Prioritize = 'prioritize'


class PathManager(QDialog, SpyderWidgetMixin):
    """Path manager dialog."""

    redirect_stdio = Signal(bool)
    sig_path_changed = Signal(object, object, bool)

    # This is required for our tests
    CONF_SECTION = 'pythonpath_manager'

    def __init__(self, parent, sync=True):
        """Path manager dialog."""
        if not PYSIDE2:
            super().__init__(parent, class_parent=parent)
        else:
            QDialog.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        # Style
        # NOTE: This needs to be here so all buttons are styled correctly
        self.setStyleSheet(self._stylesheet)

        self.last_path = getcwd_or_home()

        # Widgets
        self.add_button = None
        self.remove_button = None
        self.movetop_button = None
        self.moveup_button = None
        self.movedown_button = None
        self.movebottom_button = None
        self.export_button = None
        self.prioritize_button = None
        self.user_header = None
        self.project_header = None
        self.system_header = None
        self.headers = []
        self.selection_widgets = []
        self.right_buttons = self._setup_right_toolbar()
        self.listwidget = QListWidget(self)
        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)

        # Create a loading message
        self.loading_pane = EmptyMessageWidget(
            parent=self,
            text=_("Retrieving environment variables..."),
            bottom_stretch=1,
            spinner=True,
        )

        # Create a QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.listwidget)
        self.stacked_widget.addWidget(self.loading_pane)
        self.stacked_widget.setCurrentWidget(self.listwidget)

        # Widget setup
        self.setWindowTitle(_("PYTHONPATH manager"))
        self.setWindowIcon(self.create_icon('pythonpath'))
        self.resize(500, 400)
        self.export_button.setVisible(os.name == 'nt' and sync)

        # Description
        description = QLabel(
            _("The paths listed below will be passed to the IPython console "
              "and to the Editor as additional locations to search for Python "
              "modules.")
        )
        description.setWordWrap(True)

        # Buttons layout
        buttons_layout = QVBoxLayout()
        self._add_buttons_to_layout(self.right_buttons, buttons_layout)
        buttons_layout.addStretch(1)

        # Middle layout
        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(4 if WIN else 5, 0, 0, 0)
        middle_layout.addWidget(self.stacked_widget)
        middle_layout.addLayout(buttons_layout)

        # Widget layout
        layout = QVBoxLayout()
        layout.addWidget(description)
        layout.addSpacing(2 * AppStyle.MarginSize)
        layout.addLayout(middle_layout)
        layout.addSpacing((-1 if MAC else 2) * AppStyle.MarginSize)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        # Signals
        self.listwidget.currentRowChanged.connect(lambda x: self.refresh())
        self.listwidget.itemChanged.connect(lambda x: self.refresh())
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Attributes
        self.project_path = None
        self.user_paths = None
        self.system_paths = None
        self.prioritize = None

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _add_buttons_to_layout(self, widgets, layout):
        """Helper to add buttons to its layout."""
        for widget in widgets:
            layout.addWidget(widget)

    def _setup_right_toolbar(self):
        """Create top toolbar and actions."""
        self.movetop_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveTop,
            text=_("Move path to the top"),
            icon=self.create_icon('2uparrow'),
            triggered=lambda: self.move_to(absolute=0))
        self.moveup_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveUp,
            tip=_("Move path up"),
            icon=self.create_icon('1uparrow'),
            triggered=lambda: self.move_to(relative=-1))
        self.movedown_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveDown,
            tip=_("Move path down"),
            icon=self.create_icon('1downarrow'),
            triggered=lambda: self.move_to(relative=1))
        self.movebottom_button = self.create_toolbutton(
            PathManagerToolbuttons.MoveToBottom,
            text=_("Move path to the bottom"),
            icon=self.create_icon('2downarrow'),
            triggered=lambda: self.move_to(absolute=1))
        self.add_button = self.create_toolbutton(
            PathManagerToolbuttons.AddPath,
            tip=_('Add path'),
            icon=self.create_icon('edit_add'),
            triggered=lambda x: self.add_path())
        self.remove_button = self.create_toolbutton(
            PathManagerToolbuttons.RemovePath,
            tip=_('Remove path'),
            icon=self.create_icon('editclear'),
            triggered=lambda x: self.remove_path())
        self.import_button = self.create_toolbutton(
            PathManagerToolbuttons.ImportPaths,
            tip=_('Import from PYTHONPATH environment variable'),
            icon=self.create_icon('fileimport'),
            triggered=self.import_pythonpath)
        self.export_button = self.create_toolbutton(
            PathManagerToolbuttons.ExportPaths,
            icon=self.create_icon('fileexport'),
            triggered=self.export_pythonpath,
            tip=_("Export to PYTHONPATH environment variable"))
        self.prioritize_button = self.create_toolbutton(
            PathManagerToolbuttons.Prioritize,
            option='prioritize',
            triggered=self.refresh,
        )
        self.prioritize_button.setCheckable(True)

        self.selection_widgets = [self.movetop_button, self.moveup_button,
                                  self.movedown_button, self.movebottom_button]
        return (
            [self.add_button, self.remove_button] +
            self.selection_widgets + [self.import_button, self.export_button] +
            [self.prioritize_button]
        )

    def _create_item(self, path, active):
        """Helper to create a new list item."""
        item = QListWidgetItem(path)

        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if active else Qt.Unchecked)

        return item

    def _create_header(self, text):
        """Create a header for a given path section."""
        header_item = QListWidgetItem()
        header_widget = QLabel(text)

        # Disable item so we can remove its background color
        header_item.setFlags(header_item.flags() & ~Qt.ItemIsEnabled)

        # Header is centered
        header_widget.setAlignment(Qt.AlignHCenter)

        # Make header appear in bold
        font = header_widget.font()
        font.setBold(True)
        header_widget.setFont(font)

        # Increase height to make header stand over paths
        fm = QFontMetrics(font)
        header_item.setSizeHint(
            QSize(20, fm.capHeight() + 6 * AppStyle.MarginSize)
        )

        return header_item, header_widget

    @property
    def _stylesheet(self):
        """Style for the list of paths"""
        # This is necessary to match the buttons style with the rest of Spyder
        toolbar_stylesheet = PANES_TOOLBAR_STYLESHEET.get_copy()
        css = toolbar_stylesheet.get_stylesheet()

        css.QListView.setValues(
            padding=f"{AppStyle.MarginSize + 1}px"
        )

        css["QListView::item"].setValues(
            padding=f"{AppStyle.MarginSize + (1 if WIN else 0)}px"
        )

        css["QListView::item:disabled"].setValues(
            backgroundColor="transparent"
        )

        return css.toString()

    def _setup_system_paths(self, paths):
        """Add system paths, creating system header if necessary"""
        if not paths:
            return

        if not self.system_header:
            self.system_header, system_widget = (
                self._create_header(_("System PYTHONPATH"))
            )
            self.headers.append(self.system_header)
            self.listwidget.addItem(self.system_header)
            self.listwidget.setItemWidget(self.system_header, system_widget)

        for path, active in paths.items():
            item = self._create_item(path, active)
            self.listwidget.addItem(item)

    # ---- Public methods
    # -------------------------------------------------------------------------
    @property
    def editable_bottom_row(self):
        """Maximum bottom row count that is editable."""
        bottom_row = 0

        if self.project_header:
            bottom_row += len(self.project_path) + 1
        if self.user_header:
            bottom_row += len(self.get_user_paths())

        return bottom_row

    @property
    def editable_top_row(self):
        """Maximum top row count that is editable."""
        top_row = 0

        if self.project_header:
            top_row += len(self.project_path) + 1
        if self.user_header:
            top_row += 1

        return top_row

    def setup(self):
        """Populate list widget."""
        self.listwidget.clear()
        self.headers.clear()
        self.project_header = None
        self.user_header = None
        self.system_header = None

        # Project path
        if self.project_path:
            self.project_header, project_widget = (
                self._create_header(_("Project path"))
            )
            self.headers.append(self.project_header)
            self.listwidget.addItem(self.project_header)
            self.listwidget.setItemWidget(self.project_header, project_widget)

            for path, active in self.project_path.items():
                item = self._create_item(path, active)

                # Project path should not be editable
                item.setFlags(Qt.NoItemFlags | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)

                self.listwidget.addItem(item)

        # Paths added by the user
        if self.user_paths:
            self.user_header, user_widget = (
                self._create_header(_("User paths"))
            )
            self.headers.append(self.user_header)
            self.listwidget.addItem(self.user_header)
            self.listwidget.setItemWidget(self.user_header, user_widget)

            for path, active in self.user_paths.items():
                item = self._create_item(path, active)
                self.listwidget.addItem(item)

        # System paths
        self._setup_system_paths(self.system_paths)

        # Prioritize
        self.prioritize_button.setChecked(self.prioritize)

        self.listwidget.setCurrentRow(0)
        self.refresh()

    @Slot()
    def export_pythonpath(self):
        """
        Export to PYTHONPATH environment variable
        Only apply to: current user.

        If the user chooses to clear the contents of the system PYTHONPATH,
        then the active user paths are prepended to active system paths and
        the resulting list is saved to the system PYTHONPATH. Inactive system
        paths are discarded. If the user chooses not to clear the contents of
        the system PYTHONPATH, then the new system PYTHONPATH comprises the
        inactive system paths + active user paths + active system paths, and
        inactive system paths remain inactive. With either choice, inactive
        user paths are retained in the user paths and remain inactive.
        """
        answer = QMessageBox.question(
            self,
            _("Export"),
            _("This will export Spyder's path list to the "
              "<b>PYTHONPATH</b> environment variable for the current user, "
              "allowing you to run your Python modules outside Spyder "
              "without having to configure sys.path. "
              "<br><br>"
              "Do you want to clear the contents of PYTHONPATH before "
              "adding Spyder's path list?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        if answer == QMessageBox.Cancel:
            return

        user_paths = self.get_user_paths()
        active_user_paths = OrderedDict(
            {p: v for p, v in user_paths.items() if v}
        )
        new_user_paths = OrderedDict(
            {p: v for p, v in user_paths.items() if not v}
        )

        system_paths = self.get_system_paths()
        active_system_paths = OrderedDict(
            {p: v for p, v in system_paths.items() if v}
        )
        inactive_system_paths = OrderedDict(
            {p: v for p, v in system_paths.items() if not v}
        )

        # Desired behavior is active_user | active_system, but Python 3.8 does
        # not support | operator for OrderedDict.
        new_system_paths = OrderedDict(reversed(active_system_paths.items()))
        new_system_paths.update(reversed(active_user_paths.items()))
        if answer == QMessageBox.No:
            # Desired behavior is inactive_system | active_user | active_system
            new_system_paths.update(reversed(inactive_system_paths.items()))
        new_system_paths = OrderedDict(reversed(new_system_paths.items()))

        env = get_user_env()
        env['PYTHONPATH'] = list(new_system_paths.keys())
        set_user_env(env, parent=self)

        self.update_paths(
            user_paths=new_user_paths, system_paths=new_system_paths
        )

    def get_user_paths(self):
        """Get current user paths as displayed on listwidget."""
        paths = OrderedDict()

        if self.user_header is None:
            return paths

        start = self.listwidget.row(self.user_header) + 1
        stop = self.listwidget.count()
        if self.system_header is not None:
            stop = self.listwidget.row(self.system_header)

        for row in range(start, stop):
            item = self.listwidget.item(row)
            paths.update({item.text(): item.checkState() == Qt.Checked})

        return paths

    def get_system_paths(self):
        """Get current system paths as displayed on listwidget."""
        paths = OrderedDict()

        if self.system_header is None:
            return paths

        start = self.listwidget.row(self.system_header) + 1
        for row in range(start, self.listwidget.count()):
            item = self.listwidget.item(row)
            paths.update({item.text(): item.checkState() == Qt.Checked})

        return paths

    def update_paths(
        self,
        project_path=None,
        user_paths=None,
        system_paths=None,
        prioritize=None
    ):
        """
        Update path attributes.

        These attributes should only be set in this method and upon activating
        the dialog. They should remain fixed while the dialog is active and are
        used to compare with what is shown in the listwidget in order to detect
        changes.
        """
        if project_path is not None:
            self.project_path = project_path
        if user_paths is not None:
            self.user_paths = user_paths
        if system_paths is not None:
            self.system_paths = system_paths
        if prioritize is not None:
            self.prioritize = prioritize

        self.setup()

    def refresh(self):
        """Refresh toolbar widgets."""
        current_item = self.listwidget.currentItem()
        enabled = current_item is not None
        for widget in self.selection_widgets:
            widget.setEnabled(enabled)

        # Main variables
        row = self.listwidget.currentRow()
        disable_widgets = []

        # Move up/top disabled for less than top editable item.
        if row <= self.editable_top_row:
            disable_widgets.extend([self.movetop_button, self.moveup_button])

        # Move down/bottom disabled for bottom item
        if row == self.editable_bottom_row:
            disable_widgets.extend([self.movebottom_button,
                                    self.movedown_button])

        # Disable almost all buttons on headers or system PYTHONPATH
        if current_item in self.headers or row > self.editable_bottom_row:
            disable_widgets.extend(
                [self.movetop_button, self.moveup_button,
                 self.movebottom_button, self.movedown_button]
            )

        for widget in disable_widgets:
            widget.setEnabled(False)

        # Enable remove button only for user paths
        self.remove_button.setEnabled(
            current_item not in self.headers
            and (self.editable_top_row <= row <= self.editable_bottom_row)
        )

        if self.prioritize_button.isChecked():
            self.prioritize_button.setIcon(self.create_icon('prepend'))
            self.prioritize_button.setToolTip(
                _("Paths are prepended to sys.path")
            )
        else:
            self.prioritize_button.setIcon(self.create_icon('append'))
            self.prioritize_button.setToolTip(
                _("Paths are appended to sys.path")
            )

        self.export_button.setEnabled(self.listwidget.count() > 0)

        # Ok button only enabled if actual changes occur
        self.button_ok.setEnabled(
            self.user_paths != self.get_user_paths()
            or self.system_paths != self.get_system_paths()
            or self.prioritize != self.prioritize_button.isChecked()
        )

    @Slot()
    def add_path(self, directory=None):
        """
        Add path to list widget.

        If `directory` is provided, the folder dialog is overridden.
        """
        if directory is None:
            self.redirect_stdio.emit(False)
            directory = getexistingdirectory(self, _("Select directory"),
                                             self.last_path)
            self.redirect_stdio.emit(True)
            if not directory:
                return

        directory = osp.abspath(directory)
        self.last_path = directory

        if directory in self.get_user_paths():
            # Always take the last item to avoid retrieving the project path
            item = self.listwidget.findItems(directory, Qt.MatchExactly)[-1]
            item.setCheckState(Qt.Checked)
            answer = QMessageBox.question(
                self,
                _("Add path"),
                _("This directory is already included in the list."
                  "<br> "
                  "Do you want to move it to the top of the list?"),
                QMessageBox.Yes | QMessageBox.No)

            if answer == QMessageBox.Yes:
                item = self.listwidget.takeItem(self.listwidget.row(item))
                self.listwidget.insertItem(self.editable_top_row, item)
                self.listwidget.setCurrentRow(self.editable_top_row)
        else:
            if check_path(directory):
                if not self.user_header:
                    self.user_header, user_widget = (
                        self._create_header(_("User paths"))
                    )
                    self.headers.append(self.user_header)

                    if self.editable_top_row > 0:
                        header_row = self.editable_top_row - 1
                    else:
                        header_row = 0
                    self.listwidget.insertItem(header_row, self.user_header)
                    self.listwidget.setItemWidget(
                        self.user_header, user_widget
                    )

                # Add new path
                item = self._create_item(directory, True)
                self.listwidget.insertItem(self.editable_top_row, item)
                self.listwidget.setCurrentRow(self.editable_top_row)
            else:
                answer = QMessageBox.warning(
                    self,
                    _("Add path"),
                    _("This directory cannot be added to the path!"
                      "<br><br>"
                      "If you want to set a different Python interpreter, "
                      "please go to <tt>Preferences > Main interpreter</tt>"
                      "."),
                    QMessageBox.Ok)

        # Widget moves to back and loses focus on macOS,
        # see spyder-ide/spyder#20808
        if sys.platform == 'darwin':
            self.activateWindow()
            self.raise_()
            self.setFocus()

        self.refresh()

    @Slot()
    def remove_path(self, force=False):
        """
        Remove path from list widget.

        If `force` is True, the message box is overridden.
        """
        if self.listwidget.currentItem():
            if not force:
                answer = QMessageBox.warning(
                    self,
                    _("Remove path"),
                    _("Do you really want to remove the selected path?"),
                    QMessageBox.Yes | QMessageBox.No)

            if force or answer == QMessageBox.Yes:
                # Remove selected item from view
                self.listwidget.takeItem(self.listwidget.currentRow())

                # Remove user header if there are no more user paths
                if len(self.get_user_paths()) == 0:
                    self.listwidget.takeItem(
                        self.listwidget.row(self.user_header)
                    )
                    self.headers.remove(self.user_header)
                    self.user_header = None

                # Refresh widget
                self.refresh()

    @Slot()
    def import_pythonpath(self):
        future = get_user_environment_variables()
        future.connect(self._import_pythonpath)
        self.stacked_widget.setCurrentWidget(self.loading_pane)

    @AsyncDispatcher.QtSlot
    def _import_pythonpath(self, future):
        """Import PYTHONPATH from environment."""
        current_system_paths = self.get_system_paths()
        system_paths = get_system_pythonpath(future.result())

        # Inherit active state from current system paths
        system_paths = OrderedDict(
            {p: current_system_paths.get(p, True) for p in system_paths}
        )

        # Remove system paths
        if self.system_header:
            header_row = self.listwidget.row(self.system_header)
            for row in range(self.listwidget.count(), header_row, -1):
                self.listwidget.takeItem(row)

            # Also remove system header
            if not system_paths:
                self.listwidget.takeItem(header_row)
                self.headers.remove(self.system_header)
                self.system_header = None

        self._setup_system_paths(system_paths)

        self.stacked_widget.setCurrentWidget(self.listwidget)

        self.refresh()

    def move_to(self, absolute=None, relative=None):
        """Move items of list widget."""
        index = self.listwidget.currentRow()
        if absolute is not None:
            if absolute:
                new_index = self.editable_bottom_row
            else:
                new_index = self.editable_top_row
        else:
            new_index = index + relative

        new_index = max(1, min(self.editable_bottom_row, new_index))
        item = self.listwidget.takeItem(index)
        self.listwidget.insertItem(new_index, item)
        self.listwidget.setCurrentRow(new_index)

        self.refresh()

    def current_row(self):
        """Returns the current row of the list."""
        return self.listwidget.currentRow()

    def set_current_row(self, row):
        """Set the current row of the list."""
        self.listwidget.setCurrentRow(row)

    def row_check_state(self, row):
        """Return the checked state for item in row."""
        item = self.listwidget.item(row)
        return item.checkState()

    def set_row_check_state(self, row, value):
        """Set the current checked state for item in row."""
        item = self.listwidget.item(row)
        item.setCheckState(value)

    def count(self):
        """Return the number of items."""
        return self.listwidget.count()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accept(self):
        """Override Qt method."""
        self.sig_path_changed.emit(
            self.get_user_paths(),
            self.get_system_paths(),
            self.prioritize_button.isChecked()
        )
        super().accept()


def test():
    """Run path manager test."""
    from spyder.utils.qthelpers import qapplication

    _ = qapplication()
    dlg = PathManager(
        None,
    )
    dlg.update_paths(
        user_paths={p: True for p in sys.path[1:-2]},
        project_path={p: True for p in sys.path[:1]},
        system_paths={p: True for p in sys.path[-2:]},
        prioritize=False
    )

    def callback(user_paths, system_paths, prioritize):
        sys.stdout.write(f"Prioritize: {prioritize}")
        sys.stdout.write("\n---- User paths ----\n")
        sys.stdout.write(
            '\n'.join([f'{k}: {v}' for k, v in user_paths.items()])
        )
        sys.stdout.write("\n---- System paths ----\n")
        sys.stdout.write(
            '\n'.join([f'{k}: {v}' for k, v in system_paths.items()])
        )
        sys.stdout.write('\n')

    dlg.sig_path_changed.connect(callback)
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()
