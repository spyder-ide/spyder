# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Files and Directories Explorer"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement

# Standard library imports
import os
import os.path as osp
import re
import shutil
import sys

# Third party imports
from qtpy.compat import getexistingdirectory, getsavefilename
from qtpy.QtCore import (QDir, QMimeData, QSortFilterProxyModel, Qt, QTimer,
                         QUrl, Signal, Slot)
from qtpy.QtGui import QDrag
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QFileSystemModel, QInputDialog, QLabel, QLineEdit,
                            QMessageBox, QTextEdit, QTreeView, QVBoxLayout)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import get_home_dir, running_under_pytest
from spyder.config.main import NAME_FILTERS
from spyder.plugins.explorer.widgets.utils import (
    create_script, fixpath, IconProvider, show_in_external_file_explorer)
from spyder.py3compat import to_binary_string
from spyder.utils import encoding
from spyder.utils.icon_manager import ima
from spyder.utils import misc, programs, vcs
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import file_uri, start_file

try:
    from nbconvert import PythonExporter as nbexporter
except:
    nbexporter = None    # analysis:ignore


# Localization
_ = get_translation('spyder')


# ---- Constants
# ----------------------------------------------------------------------------
class DirViewColumns:
    Size = 1
    Type = 2
    Date = 3


class DirViewOpenWithSubMenuSections:
    Main = 'Main'


class DirViewActions:
    # Toggles
    ToggleDateColumn = 'toggle_date_column_action'
    ToggleSingleClick = 'toggle_single_click_to_open_action'
    ToggleSizeColumn = 'toggle_size_column_action'
    ToggleTypeColumn = 'toggle_type_column_action'
    ToggleHiddenFiles = 'toggle_show_hidden_action'

    # Triggers
    EditNameFilters = 'edit_name_filters_action'
    NewFile = 'new_file_action'
    NewModule = 'new_module_action'
    NewFolder = 'new_folder_action'
    NewPackage = 'new_package_action'
    OpenWithSpyder = 'open_with_spyder_action'
    OpenWithSystem = 'open_with_system_action'
    OpenWithSystem2 = 'open_with_system_2_action'
    Delete = 'delete_action'
    Rename = 'rename_action'
    Move = 'move_action'
    Copy = 'copy_action'
    Paste = 'paste_action'
    CopyAbsolutePath = 'copy_absolute_path_action'
    CopyRelativePath = 'copy_relative_path_action'
    ShowInSystemExplorer = 'show_system_explorer_action'
    VersionControlCommit = 'version_control_commit_action'
    VersionControlBrowse = 'version_control_browse_action'
    ConvertNotebook = 'convert_notebook_action'

    # TODO: Move this to the IPython Console
    OpenInterpreter = 'open_interpreter_action'
    Run = 'run_action'


class DirViewMenus:
    Context = 'context_menu'
    Header = 'header_menu'
    New = 'new_menu'
    OpenWith = 'open_with_menu'


class DirViewHeaderMenuSections:
    Main = 'main_section'


class DirViewNewSubMenuSections:
    General = 'general_section'
    Language = 'language_section'


class DirViewContextMenuSections:
    CopyPaste = 'copy_paste_section'
    Extras = 'extras_section'
    New = 'new_section'
    System = 'system_section'
    VersionControl = 'version_control_section'


class ExplorerTreeWidgetActions:
    # Toggles
    ToggleFilter = 'toggle_filter_files_action'

    # Triggers
    Next = 'next_action'
    Parent = 'parent_action'
    Previous = 'previous_action'


# ---- Widgets
# ----------------------------------------------------------------------------
class DirView(QTreeView, SpyderWidgetMixin):
    """Base file/directory tree view."""

    # Signals
    sig_file_created = Signal(str)
    """
    This signal is emitted when a file is created

    Parameters
    ----------
    module: str
        Path to the created file.
    """

    sig_open_interpreter_requested = Signal(str)
    """
    This signal is emitted when the interpreter opened is requested

    Parameters
    ----------
    module: str
        Path to use as working directory of interpreter.
    """

    sig_module_created = Signal(str)
    """
    This signal is emitted when a new python module is created.

    Parameters
    ----------
    module: str
        Path to the new module created.
    """

    sig_redirect_stdio_requested = Signal(bool)
    """
    This signal is emitted when redirect stdio is requested.

    Parameters
    ----------
    enable: bool
        Enable/Disable standard input/output redirection.
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

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

    Parameters
    ----------
    path: str
        File path to run.
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
    path: str
        Folder to remove.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    def __init__(self, parent=None):
        """Initialize the DirView.

        Parameters
        ----------
        parent: QWidget
            Parent QWidget of the widget.
        """
        super().__init__(parent=parent, class_parent=parent)

        # Attributes
        self._parent = parent
        self._last_column = 0
        self._last_order = True
        self._scrollbar_positions = None
        self._to_be_loaded = None
        self.__expanded_state = None
        self.common_actions = None
        self.filter_on = False

        # Widgets
        self.fsmodel = None
        self.menu = None
        self.header_menu = None
        header = self.header()

        # Signals
        header.customContextMenuRequested.connect(self.show_header_menu)

        # Setup
        self.setup_fs_model()
        self.setSelectionMode(self.ExtendedSelection)
        header.setContextMenuPolicy(Qt.CustomContextMenu)

    # ---- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def setup(self):
        self.setup_view()

        self.set_name_filters(self.get_conf('name_filters', []))
        self.set_name_filters(self.get_conf('file_associations', {}))

        # New actions
        new_file_action = self.create_action(
            DirViewActions.NewFile,
            text=_("File..."),
            icon=self.create_icon('TextFileIcon'),
            triggered=lambda: self.new_file(),
        )

        new_module_action = self.create_action(
            DirViewActions.NewModule,
            text=_("Python file..."),
            icon=self.create_icon('python'),
            triggered=lambda: self.new_module(),
        )

        new_folder_action = self.create_action(
            DirViewActions.NewFolder,
            text=_("Folder..."),
            icon=self.create_icon('folder_new'),
            triggered=lambda: self.new_folder(),
        )

        new_package_action = self.create_action(
            DirViewActions.NewPackage,
            text=_("Python Package..."),
            icon=self.create_icon('package_new'),
            triggered=lambda: self.new_package(),
        )

        # Open actions
        self.open_with_spyder_action = self.create_action(
            DirViewActions.OpenWithSpyder,
            text=_("Open in Spyder"),
            icon=self.create_icon('edit'),
            triggered=lambda: self.open(),
        )

        self.open_external_action = self.create_action(
            DirViewActions.OpenWithSystem,
            text=_("Open externally"),
            triggered=lambda: self.open_external(),
        )

        self.open_external_action_2 = self.create_action(
            DirViewActions.OpenWithSystem2,
            text=_("Default external application"),
            triggered=lambda: self.open_external(),
            register_shortcut=False,
        )

        # File management actions
        delete_action = self.create_action(
            DirViewActions.Delete,
            text=_("Delete..."),
            icon=self.create_icon('editdelete'),
            triggered=lambda: self.delete(),
        )

        rename_action = self.create_action(
            DirViewActions.Rename,
            text=_("Rename..."),
            icon=self.create_icon('rename'),
            triggered=lambda: self.rename(),
        )

        self.move_action = self.create_action(
            DirViewActions.Move,
            text=_("Move..."),
            icon=self.create_icon('move'),
            triggered=lambda: self.move(),
        )

        # Copy/Paste actions
        copy_action = self.create_action(
            DirViewActions.Copy,
            text=_("Copy"),
            icon=self.create_icon('editcopy'),
            triggered=lambda: self.copy_file_clipboard(),
        )

        self.paste_action = self.create_action(
            DirViewActions.Paste,
            text=_("Paste"),
            icon=self.create_icon('editpaste'),
            triggered=lambda: self.save_file_clipboard(),
        )

        copy_absolute_path_action = self.create_action(
            DirViewActions.CopyAbsolutePath,
            text=_("Copy Absolute Path"),
            triggered=lambda: self.copy_absolute_path(),
        )

        copy_relative_path_action = self.create_action(
            DirViewActions.CopyRelativePath,
            text=_("Copy Relative Path"),
            triggered=lambda: self.copy_relative_path(),
        )

        # Show actions
        if sys.platform == 'darwin':
            show_in_finder_text = _("Show in Finder")
        else:
            show_in_finder_text = _("Show in Folder")

        show_in_system_explorer_action = self.create_action(
            DirViewActions.ShowInSystemExplorer,
            text=show_in_finder_text,
            triggered=lambda: self.show_in_external_file_explorer(),
        )

        # Version control actions
        self.vcs_commit_action = self.create_action(
            DirViewActions.VersionControlCommit,
            text=_("Commit"),
            icon=self.create_icon('vcs_commit'),
            triggered=lambda: self.vcs_command('commit'),
        )
        self.vcs_log_action = self.create_action(
            DirViewActions.VersionControlBrowse,
            text=_("Browse repository"),
            icon=self.create_icon('vcs_browse'),
            triggered=lambda: self.vcs_command('browse'),
        )

        # Common actions
        self.hidden_action = self.create_action(
            DirViewActions.ToggleHiddenFiles,
            text=_("Show hidden files"),
            toggled=True,
            initial=self.get_conf('show_hidden', False),
            option='show_hidden'
        )

        self.filters_action = self.create_action(
            DirViewActions.EditNameFilters,
            text=_("Edit filter settings..."),
            icon=self.create_icon('filter'),
            triggered=lambda: self.edit_filter(),
        )

        self.create_action(
            DirViewActions.ToggleSingleClick,
            text=_("Single click to open"),
            toggled=True,
            initial=self.get_conf('single_click_to_open', False),
            option='single_click_to_open'
        )

        # IPython console actions
        # TODO: Move this option to the ipython console setup
        self.open_interpreter_action = self.create_action(
            DirViewActions.OpenInterpreter,
            text=_("Open IPython console here"),
            triggered=lambda: self.open_interpreter(),
        )

        # TODO: Move this option to the ipython console setup
        run_action = self.create_action(
            DirViewActions.Run,
            text=_("Run"),
            icon=self.create_icon('run'),
            triggered=lambda: self.run(),
        )

        # Notebook Actions
        ipynb_convert_action = self.create_action(
            DirViewActions.ConvertNotebook,
            _("Convert to Python script"),
            icon=ima.icon('python'),
            triggered=lambda: self.convert_notebooks()
        )

        # Header Actions
        size_column_action = self.create_action(
            DirViewActions.ToggleSizeColumn,
            text=_('Size'),
            toggled=True,
            initial=self.get_conf('size_column', False),
            register_shortcut=False,
            option='size_column'
        )
        type_column_action = self.create_action(
            DirViewActions.ToggleTypeColumn,
            text=_('Type') if sys.platform == 'darwin' else _('Type'),
            toggled=True,
            initial=self.get_conf('type_column', False),
            register_shortcut=False,
            option='type_column'
        )
        date_column_action = self.create_action(
            DirViewActions.ToggleDateColumn,
            text=_("Date modified"),
            toggled=True,
            initial=self.get_conf('date_column', True),
            register_shortcut=False,
            option='date_column'
        )

        # Header Context Menu
        self.header_menu = self.create_menu(DirViewMenus.Header)
        for item in [size_column_action, type_column_action,
                     date_column_action]:
            self.add_item_to_menu(
                item,
                menu=self.header_menu,
                section=DirViewHeaderMenuSections.Main,
            )

        # New submenu
        new_submenu = self.create_menu(
            DirViewMenus.New,
            _('New'),
        )
        for item in [new_file_action, new_folder_action]:
            self.add_item_to_menu(
                item,
                menu=new_submenu,
                section=DirViewNewSubMenuSections.General,
            )

        for item in [new_module_action, new_package_action]:
            self.add_item_to_menu(
                item,
                menu=new_submenu,
                section=DirViewNewSubMenuSections.Language,
            )

        # Open with submenu
        self.open_with_submenu = self.create_menu(
            DirViewMenus.OpenWith,
            _('Open with'),
        )

        # Context submenu
        self.context_menu = self.create_menu(DirViewMenus.Context)
        for item in [new_submenu, run_action,
                     self.open_with_spyder_action,
                     self.open_with_submenu,
                     self.open_external_action,
                     delete_action, rename_action, self.move_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.New,
            )

        # Copy/Paste section
        for item in [copy_action, self.paste_action, copy_absolute_path_action,
                     copy_relative_path_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.CopyPaste,
            )

        self.add_item_to_menu(
            show_in_system_explorer_action,
            menu=self.context_menu,
            section=DirViewContextMenuSections.System,
        )

        # Version control section
        for item in [self.vcs_commit_action, self.vcs_log_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.VersionControl
            )

        for item in [self.open_interpreter_action, ipynb_convert_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.Extras,
            )

        # Signals
        self.context_menu.aboutToShow.connect(self.update_actions)

    @on_conf_change(option=['size_column', 'type_column', 'date_column',
                            'name_filters', 'show_hidden'])
    def on_conf_update(self, option, value):
        if option == 'size_column':
            self.setColumnHidden(DirViewColumns.Size, not value)
        elif option == 'type_column':
            self.setColumnHidden(DirViewColumns.Type, not value)
        elif option == 'date_column':
            self.setColumnHidden(DirViewColumns.Date, not value)
        elif option == 'name_filters':
            if self.filter_on:
                self.filter_files(value)
        elif option == 'show_hidden':
            self.set_show_hidden(self.get_conf('show_hidden'))

    def update_actions(self):
        fnames = self.get_selected_filenames()
        if fnames:
            if osp.isdir(fnames[0]):
                dirname = fnames[0]
            else:
                dirname = osp.dirname(fnames[0])

            basedir = fixpath(osp.dirname(fnames[0]))
            only_dirs = fnames and all([osp.isdir(fname) for fname in fnames])
            only_files = all([osp.isfile(fname) for fname in fnames])
            only_valid = all([encoding.is_text_file(fna) for fna in fnames])
        else:
            only_files = False
            only_valid = False
            only_dirs = False
            dirname = ''
            basedir = ''

        vcs_visible = (only_files and len(fnames) == 1
                       and vcs.is_vcs_repository(dirname))

        # Make actions visible conditionally
        self.move_action.setVisible(
            all([fixpath(osp.dirname(fname)) == basedir for fname in fnames]))
        self.open_external_action.setVisible(False)
        self.open_interpreter_action.setVisible(only_dirs)
        self.open_with_spyder_action.setVisible(only_files and only_valid)
        self.open_with_submenu.menuAction().setVisible(False)
        self.paste_action.setDisabled(
            not QApplication.clipboard().mimeData().hasUrls())

        # VCS support is quite limited for now, so we are enabling the VCS
        # related actions only when a single file/folder is selected:
        self.vcs_commit_action.setVisible(vcs_visible)
        self.vcs_log_action.setVisible(vcs_visible)

        if only_files:
            if len(fnames) == 1:
                assoc = self.get_file_associations(fnames[0])
            elif len(fnames) > 1:
                assoc = self.get_common_file_associations(fnames)

            if len(assoc) >= 1:
                actions = self._create_file_associations_actions()
                self.open_with_submenu.menuAction().setVisible(True)
                self.open_with_submenu.clear()
                for action in actions:
                    self.add_item_to_menu(
                        action,
                        menu=self.open_with_submenu,
                        section=DirViewOpenWithSubMenuSections.Main,
                    )
            else:
                self.open_external_action.setVisible(True)

        fnames = self.get_selected_filenames()
        only_notebooks = all([osp.splitext(fname)[1] == '.ipynb'
                              for fname in fnames])
        only_modules = all([osp.splitext(fname)[1] in ('.py', '.pyw', '.ipy')
                            for fname in fnames])

        nb_visible = only_notebooks and nbexporter is not None
        self.get_action(DirViewActions.ConvertNotebook).setVisible(nb_visible)
        self.get_action(DirViewActions.Run).setVisible(only_modules)

    def _create_file_associations_actions(self, fnames=None):
        """
        Create file association actions.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        actions = []
        only_files = all([osp.isfile(fname) for fname in fnames])
        if only_files:
            if len(fnames) == 1:
                assoc = self.get_file_associations(fnames[0])
            elif len(fnames) > 1:
                assoc = self.get_common_file_associations(fnames)

            if len(assoc) >= 1:
                for app_name, fpath in assoc:
                    text = app_name
                    if not (os.path.isfile(fpath) or os.path.isdir(fpath)):
                        text += _(' (Application not found!)')

                    try:
                        # Action might have been created already
                        open_assoc = self.open_association
                        open_with_action = self.create_action(
                            app_name,
                            text=text,
                            triggered=lambda x, y=fpath: open_assoc(y),
                            register_shortcut=False,
                        )
                    except Exception:
                        open_with_action = self.get_action(app_name)

                        # Disconnect previous signal in case the app path
                        # changed
                        try:
                            open_with_action.triggered.disconnect()
                        except Exception:
                            pass

                        # Reconnect the trigger signal
                        open_with_action.triggered.connect(
                            lambda x, y=fpath: self.open_association(y)
                        )

                    if not (os.path.isfile(fpath) or os.path.isdir(fpath)):
                        open_with_action.setDisabled(True)

                    actions.append(open_with_action)

                actions.append(self.open_external_action_2)

        return actions

    # ---- Qt overrides
    # ------------------------------------------------------------------------
    def sortByColumn(self, column, order=Qt.AscendingOrder):
        """Override Qt method."""
        header = self.header()
        header.setSortIndicatorShown(True)
        QTreeView.sortByColumn(self, column, order)
        header.setSortIndicator(0, order)
        self._last_column = column
        self._last_order = not self._last_order

    def viewportEvent(self, event):
        """Reimplement Qt method"""

        # Prevent Qt from crashing or showing warnings like:
        # "QSortFilterProxyModel: index from wrong model passed to
        # mapFromSource", probably due to the fact that the file system model
        # is being built. See spyder-ide/spyder#1250.
        #
        # This workaround was inspired by the following KDE bug:
        # https://bugs.kde.org/show_bug.cgi?id=172198
        #
        # Apparently, this is a bug from Qt itself.
        self.executeDelayedItemsLayout()

        return QTreeView.viewportEvent(self, event)

    def contextMenuEvent(self, event):
        """Override Qt method"""
        # Needed to handle not initialized menu.
        # See spyder-ide/spyder#6975
        try:
            fnames = self.get_selected_filenames()
            if len(fnames) != 0:
                self.context_menu.popup(event.globalPos())
        except AttributeError:
            pass

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked()
        elif event.key() == Qt.Key_F2:
            self.rename()
        elif event.key() == Qt.Key_Delete:
            self.delete()
        elif event.key() == Qt.Key_Backspace:
            self.go_to_parent_directory()
        else:
            QTreeView.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        super().mouseDoubleClickEvent(event)
        self.clicked()

    def mouseReleaseEvent(self, event):
        """Reimplement Qt method."""
        super().mouseReleaseEvent(event)
        if self.get_conf('single_click_to_open', False):
            self.clicked()

    def dragEnterEvent(self, event):
        """Drag and Drop - Enter event"""
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """Drag and Drop - Move event"""
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def startDrag(self, dropActions):
        """Reimplement Qt Method - handle drag event"""
        data = QMimeData()
        data.setUrls([QUrl(fname) for fname in self.get_selected_filenames()])
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec_()

    # ---- Model
    # ------------------------------------------------------------------------
    def setup_fs_model(self):
        """Setup filesystem model"""
        self.fsmodel = QFileSystemModel(self)
        self.fsmodel.setNameFilterDisables(False)

    def install_model(self):
        """Install filesystem model"""
        self.setModel(self.fsmodel)

    def setup_view(self):
        """Setup view"""
        self.install_model()
        self.fsmodel.directoryLoaded.connect(
            lambda: self.resizeColumnToContents(0))
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.fsmodel.modelReset.connect(self.reset_icon_provider)
        self.reset_icon_provider()
        # Disable the view of .spyproject.
        self.filter_directories()

    # ---- File/Dir Helpers
    # ------------------------------------------------------------------------
    def get_filename(self, index):
        """Return filename associated with *index*"""
        if index:
            return osp.normpath(str(self.fsmodel.filePath(index)))

    def get_index(self, filename):
        """Return index associated with filename"""
        return self.fsmodel.index(filename)

    def get_selected_filenames(self):
        """Return selected filenames"""
        fnames = []
        if self.selectionMode() == self.ExtendedSelection:
            if self.selectionModel() is not None:
                fnames = [self.get_filename(idx) for idx in
                          self.selectionModel().selectedRows()]
        else:
            fnames = [self.get_filename(self.currentIndex())]

        return fnames

    def get_dirname(self, index):
        """Return dirname associated with *index*"""
        fname = self.get_filename(index)
        if fname:
            if osp.isdir(fname):
                return fname
            else:
                return osp.dirname(fname)

    # ---- General actions API
    # ------------------------------------------------------------------------
    def show_header_menu(self, pos):
        """Display header menu."""
        self.header_menu.popup(self.mapToGlobal(pos))

    @Slot()
    def clicked(self):
        """
        Selected item was single/double-clicked or enter/return was pressed.
        """
        fnames = self.get_selected_filenames()
        for fname in fnames:
            if osp.isdir(fname):
                self.directory_clicked(fname)
            else:
                if len(fnames) == 1:
                    assoc = self.get_file_associations(fnames[0])
                elif len(fnames) > 1:
                    assoc = self.get_common_file_associations(fnames)

                if assoc:
                    self.open_association(assoc[0][-1])
                else:
                    self.open([fname])

    def directory_clicked(self, dirname):
        """Directory was just clicked"""
        pass

    @Slot()
    def edit_filter(self):
        """Edit name filters."""
        # Create Dialog
        dialog = QDialog(self)
        dialog.resize(500, 300)
        dialog.setWindowTitle(_('Edit filter settings'))

        # Create dialog contents
        description_label = QLabel(
            _('Filter files by name, extension, or more using '
              '<a href="https://en.wikipedia.org/wiki/Glob_(programming)">glob'
              ' patterns.</a> Please enter the glob patterns of the files you '
              'want to show, separated by commas.'))
        description_label.setOpenExternalLinks(True)
        description_label.setWordWrap(True)
        filters = QTextEdit(", ".join(self.get_conf('name_filters', [])))
        layout = QVBoxLayout()
        layout.addWidget(description_label)
        layout.addWidget(filters)

        def handle_ok():
            filter_text = filters.toPlainText()
            filter_text = [
                f.strip() for f in str(filter_text).split(',')]
            self.set_name_filters(filter_text)
            dialog.accept()

        def handle_reset():
            self.set_name_filters(NAME_FILTERS)
            filters.setPlainText(", ".join(self.get_conf('name_filters', [])))

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Reset |
                                      QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel)
        button_box.accepted.connect(handle_ok)
        button_box.rejected.connect(dialog.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(handle_reset)
        layout.addWidget(button_box)
        dialog.setLayout(layout)
        dialog.show()

    @Slot()
    def open(self, fnames=None):
        """Open files with the appropriate application"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            if osp.isfile(fname) and encoding.is_text_file(fname):
                self.sig_open_file_requested.emit(fname)
            else:
                self.open_outside_spyder([fname])

    @Slot()
    def open_association(self, app_path):
        """Open files with given application executable path."""
        if not (os.path.isdir(app_path) or os.path.isfile(app_path)):
            return_codes = {app_path: 1}
            app_path = None
        else:
            return_codes = {}

        if app_path:
            fnames = self.get_selected_filenames()
            return_codes = programs.open_files_with_application(app_path,
                                                                fnames)
        self.check_launch_error_codes(return_codes)

    @Slot()
    def open_external(self, fnames=None):
        """Open files with default application"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            self.open_outside_spyder([fname])

    def open_outside_spyder(self, fnames):
        """
        Open file outside Spyder with the appropriate application.

        If this does not work, opening unknown file in Spyder, as text file.
        """
        for path in sorted(fnames):
            path = file_uri(path)
            ok = start_file(path)
            if not ok and encoding.is_text_file(path):
                self.sig_open_file_requested.emit(path)

    def remove_tree(self, dirname):
        """
        Remove whole directory tree

        Reimplemented in project explorer widget
        """
        while osp.exists(dirname):
            try:
                shutil.rmtree(dirname, onerror=misc.onerror)
            except Exception as e:
                # This handles a Windows problem with shutil.rmtree.
                # See spyder-ide/spyder#8567.
                if type(e).__name__ == "OSError":
                    error_path = str(e.filename)
                    shutil.rmtree(error_path, ignore_errors=True)

    def delete_file(self, fname, multiple, yes_to_all):
        """Delete file"""
        if multiple:
            buttons = (QMessageBox.Yes | QMessageBox.YesToAll |
                       QMessageBox.No | QMessageBox.Cancel)
        else:
            buttons = QMessageBox.Yes | QMessageBox.No
        if yes_to_all is None:
            answer = QMessageBox.warning(
                self, _("Delete"),
                _("Do you really want to delete <b>%s</b>?"
                  ) % osp.basename(fname), buttons)
            if answer == QMessageBox.No:
                return yes_to_all
            elif answer == QMessageBox.Cancel:
                return False
            elif answer == QMessageBox.YesToAll:
                yes_to_all = True
        try:
            if osp.isfile(fname):
                misc.remove_file(fname)
                self.sig_removed.emit(fname)
            else:
                self.remove_tree(fname)
                self.sig_tree_removed.emit(fname)
            return yes_to_all
        except EnvironmentError as error:
            action_str = _('delete')
            QMessageBox.critical(
                self, _("Project Explorer"),
                _("<b>Unable to %s <i>%s</i></b><br><br>Error message:<br>%s"
                  ) % (action_str, fname, str(error)))
        return False

    @Slot()
    def delete(self, fnames=None):
        """Delete files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            spyproject_path = osp.join(fname, '.spyproject')
            if osp.isdir(fname) and osp.exists(spyproject_path):
                QMessageBox.information(
                    self, _('File Explorer'),
                    _("The current directory contains a project.<br><br>"
                      "If you want to delete the project, please go to "
                      "<b>Projects</b> &raquo; <b>Delete Project</b>"))
            else:
                yes_to_all = self.delete_file(fname, multiple, yes_to_all)
                if yes_to_all is not None and not yes_to_all:
                    # Canceled
                    break

    def rename_file(self, fname):
        """Rename file"""
        path, valid = QInputDialog.getText(
            self, _('Rename'), _('New name:'), QLineEdit.Normal,
            osp.basename(fname))

        if valid:
            path = osp.join(osp.dirname(fname), str(path))
            if path == fname:
                return
            if osp.exists(path):
                answer = QMessageBox.warning(
                    self, _("Rename"),
                    _("Do you really want to rename <b>%s</b> and "
                      "overwrite the existing file <b>%s</b>?"
                      ) % (osp.basename(fname), osp.basename(path)),
                    QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.No:
                    return
            try:
                misc.rename_file(fname, path)
                if osp.isfile(path):
                    self.sig_renamed.emit(fname, path)
                else:
                    self.sig_tree_renamed.emit(fname, path)
                return path
            except EnvironmentError as error:
                QMessageBox.critical(
                    self, _("Rename"),
                    _("<b>Unable to rename file <i>%s</i></b>"
                      "<br><br>Error message:<br>%s"
                      ) % (osp.basename(fname), str(error)))

    @Slot()
    def show_in_external_file_explorer(self, fnames=None):
        """Show file in external file explorer"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        show_in_external_file_explorer(fnames)

    @Slot()
    def rename(self, fnames=None):
        """Rename files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        for fname in fnames:
            self.rename_file(fname)

    @Slot()
    def move(self, fnames=None, directory=None):
        """Move files/directories"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        orig = fixpath(osp.dirname(fnames[0]))
        while True:
            self.sig_redirect_stdio_requested.emit(False)
            if directory is None:
                folder = getexistingdirectory(
                    self, _("Select directory"), orig)
            else:
                folder = directory
            self.sig_redirect_stdio_requested.emit(True)
            if folder:
                folder = fixpath(folder)
                if folder != orig:
                    break
            else:
                return
        for fname in fnames:
            basename = osp.basename(fname)
            try:
                misc.move_file(fname, osp.join(folder, basename))
            except EnvironmentError as error:
                QMessageBox.critical(
                    self, _("Error"),
                    _("<b>Unable to move <i>%s</i></b>"
                      "<br><br>Error message:<br>%s"
                      ) % (basename, str(error)))

    def create_new_folder(self, current_path, title, subtitle, is_package):
        """Create new folder"""
        if current_path is None:
            current_path = ''
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        name, valid = QInputDialog.getText(self, title, subtitle,
                                           QLineEdit.Normal, "")
        if valid:
            dirname = osp.join(current_path, str(name))
            try:
                os.mkdir(dirname)
            except EnvironmentError as error:
                QMessageBox.critical(
                    self, title,
                    _("<b>Unable to create folder <i>%s</i></b>"
                      "<br><br>Error message:<br>%s"
                      ) % (dirname, str(error)))
            finally:
                if is_package:
                    fname = osp.join(dirname, '__init__.py')
                    try:
                        with open(fname, 'wb') as f:
                            f.write(to_binary_string('#'))
                        return dirname
                    except EnvironmentError as error:
                        QMessageBox.critical(
                            self, title,
                            _("<b>Unable to create file <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (fname, str(error)))

    def get_selected_dir(self):
        """ Get selected dir
        If file is selected the directory containing file is returned.
        If multiple items are selected, first item is chosen.
        """
        selected_path = self.get_selected_filenames()[0]
        if osp.isfile(selected_path):
            selected_path = osp.dirname(selected_path)
        return fixpath(selected_path)

    def new_folder(self, basedir=None):
        """New folder."""

        if basedir is None:
            basedir = self.get_selected_dir()

        title = _('New folder')
        subtitle = _('Folder name:')
        self.create_new_folder(basedir, title, subtitle, is_package=False)

    def create_new_file(self, current_path, title, filters, create_func):
        """Create new file
        Returns True if successful"""
        if current_path is None:
            current_path = ''
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        self.sig_redirect_stdio_requested.emit(False)
        fname, _selfilter = getsavefilename(self, title, current_path, filters)
        self.sig_redirect_stdio_requested.emit(True)
        if fname:
            try:
                create_func(fname)
                return fname
            except EnvironmentError as error:
                QMessageBox.critical(
                    self, _("New file"),
                    _("<b>Unable to create file <i>%s</i>"
                      "</b><br><br>Error message:<br>%s"
                      ) % (fname, str(error)))

    def new_file(self, basedir=None):
        """New file"""

        if basedir is None:
            basedir = self.get_selected_dir()

        title = _("New file")
        filters = _("All files")+" (*)"

        def create_func(fname):
            """File creation callback"""
            if osp.splitext(fname)[1] in ('.py', '.pyw', '.ipy'):
                create_script(fname)
            else:
                with open(fname, 'wb') as f:
                    f.write(to_binary_string(''))
        fname = self.create_new_file(basedir, title, filters, create_func)
        if fname is not None:
            self.open([fname])

    @Slot()
    def run(self, fnames=None):
        """Run Python scripts"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            self.sig_run_requested.emit(fname)

    def copy_path(self, fnames=None, method="absolute"):
        """Copy absolute or relative path to given file(s)/folders(s)."""
        cb = QApplication.clipboard()
        explorer_dir = self.fsmodel.rootPath()
        if fnames is None:
            fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        fnames = [_fn.replace(os.sep, "/") for _fn in fnames]
        if len(fnames) > 1:
            if method == "absolute":
                clipboard_files = ',\n'.join('"' + _fn + '"' for _fn in fnames)
            elif method == "relative":
                clipboard_files = ',\n'.join('"' +
                                             osp.relpath(_fn, explorer_dir).
                                             replace(os.sep, "/") + '"'
                                             for _fn in fnames)
        else:
            if method == "absolute":
                clipboard_files = fnames[0]
            elif method == "relative":
                clipboard_files = (osp.relpath(fnames[0], explorer_dir).
                                   replace(os.sep, "/"))
        copied_from = self._parent.__class__.__name__
        if copied_from == 'ProjectExplorerWidget' and method == 'relative':
            clipboard_files = [path.strip(',"') for path in
                               clipboard_files.splitlines()]
            clipboard_files = ['/'.join(path.strip('/').split('/')[1:]) for
                               path in clipboard_files]
            if len(clipboard_files) > 1:
                clipboard_files = ',\n'.join('"' + _fn + '"' for _fn in
                                             clipboard_files)
            else:
                clipboard_files = clipboard_files[0]
        cb.setText(clipboard_files, mode=cb.Clipboard)

    @Slot()
    def copy_absolute_path(self):
        """Copy absolute paths of named files/directories to the clipboard."""
        self.copy_path(method="absolute")

    @Slot()
    def copy_relative_path(self):
        """Copy relative paths of named files/directories to the clipboard."""
        self.copy_path(method="relative")

    @Slot()
    def copy_file_clipboard(self, fnames=None):
        """Copy file(s)/folders(s) to clipboard."""
        if fnames is None:
            fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        try:
            file_content = QMimeData()
            file_content.setUrls([QUrl.fromLocalFile(_fn) for _fn in fnames])
            cb = QApplication.clipboard()
            cb.setMimeData(file_content, mode=cb.Clipboard)
        except Exception as e:
            QMessageBox.critical(
                self, _('File/Folder copy error'),
                _("Cannot copy this type of file(s) or "
                  "folder(s). The error was:\n\n") + str(e))

    @Slot()
    def save_file_clipboard(self, fnames=None):
        """Paste file from clipboard into file/project explorer directory."""
        if fnames is None:
            fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        if len(fnames) >= 1:
            try:
                selected_item = osp.commonpath(fnames)
            except AttributeError:
                #  py2 does not have commonpath
                if len(fnames) > 1:
                    selected_item = osp.normpath(
                            osp.dirname(osp.commonprefix(fnames)))
                else:
                    selected_item = fnames[0]
            if osp.isfile(selected_item):
                parent_path = osp.dirname(selected_item)
            else:
                parent_path = osp.normpath(selected_item)
            cb_data = QApplication.clipboard().mimeData()
            if cb_data.hasUrls():
                urls = cb_data.urls()
                for url in urls:
                    source_name = url.toLocalFile()
                    base_name = osp.basename(source_name)
                    if osp.isfile(source_name):
                        try:
                            while base_name in os.listdir(parent_path):
                                file_no_ext, file_ext = osp.splitext(base_name)
                                end_number = re.search(r'\d+$', file_no_ext)
                                if end_number:
                                    new_number = int(end_number.group()) + 1
                                else:
                                    new_number = 1
                                left_string = re.sub(r'\d+$', '', file_no_ext)
                                left_string += str(new_number)
                                base_name = left_string + file_ext
                                destination = osp.join(parent_path, base_name)
                            else:
                                destination = osp.join(parent_path, base_name)
                            shutil.copy(source_name, destination)
                        except Exception as e:
                            QMessageBox.critical(self, _('Error pasting file'),
                                                 _("Unsupported copy operation"
                                                   ". The error was:\n\n")
                                                 + str(e))
                    else:
                        try:
                            while base_name in os.listdir(parent_path):
                                end_number = re.search(r'\d+$', base_name)
                                if end_number:
                                    new_number = int(end_number.group()) + 1
                                else:
                                    new_number = 1
                                left_string = re.sub(r'\d+$', '', base_name)
                                base_name = left_string + str(new_number)
                                destination = osp.join(parent_path, base_name)
                            else:
                                destination = osp.join(parent_path, base_name)
                            if osp.realpath(destination).startswith(
                                    osp.realpath(source_name) + os.sep):
                                QMessageBox.critical(self,
                                                     _('Recursive copy'),
                                                     _("Source is an ancestor"
                                                       " of destination"
                                                       " folder."))
                                continue
                            shutil.copytree(source_name, destination)
                        except Exception as e:
                            QMessageBox.critical(self,
                                                 _('Error pasting folder'),
                                                 _("Unsupported copy"
                                                   " operation. The error was:"
                                                   "\n\n") + str(e))
            else:
                QMessageBox.critical(self, _("No file in clipboard"),
                                     _("No file in the clipboard. Please copy"
                                       " a file to the clipboard first."))
        else:
            if QApplication.clipboard().mimeData().hasUrls():
                QMessageBox.critical(self, _('Blank area'),
                                     _("Cannot paste in the blank area."))
            else:
                pass

    def filter_directories(self):
        """Filter the directories to show"""
        index = self.get_index('.spyproject')
        if index is not None:
            self.setRowHidden(index.row(), index.parent(), True)

    def open_interpreter(self, fnames=None):
        """Open interpreter"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for path in sorted(fnames):
            self.sig_open_interpreter_requested.emit(path)

    def filter_files(self, name_filters=None):
        """Filter files given the defined list of filters."""
        if name_filters is None:
            name_filters = self.get_conf('name_filters', [])

        if self.filter_on:
            self.fsmodel.setNameFilters(name_filters)
        else:
            self.fsmodel.setNameFilters([])

    # ---- File Associations
    # ------------------------------------------------------------------------
    def get_common_file_associations(self, fnames):
        """
        Return the list of common matching file associations for all fnames.
        """
        all_values = []
        for fname in fnames:
            values = self.get_file_associations(fname)
            all_values.append(values)

        common = set(all_values[0])
        for index in range(1, len(all_values)):
            common = common.intersection(all_values[index])
        return list(sorted(common))

    def get_file_associations(self, fname):
        """Return the list of matching file associations for `fname`."""
        for exts, values in self.get_conf('file_associations', {}).items():
            clean_exts = [ext.strip() for ext in exts.split(',')]
            for ext in clean_exts:
                if fname.endswith((ext, ext[1:])):
                    values = values
                    break
            else:
                continue  # Only excecuted if the inner loop did not break
            break  # Only excecuted if the inner loop did break
        else:
            values = []

        return values

    # ---- File/Directory actions
    # ------------------------------------------------------------------------
    def check_launch_error_codes(self, return_codes):
        """Check return codes and display message box if errors found."""
        errors = [cmd for cmd, code in return_codes.items() if code != 0]
        if errors:
            if len(errors) == 1:
                msg = _('The following command did not launch successfully:')
            else:
                msg = _('The following commands did not launch successfully:')

            msg += '<br><br>' if len(errors) == 1 else '<br><br><ul>'
            for error in errors:
                if len(errors) == 1:
                    msg += '<code>{}</code>'.format(error)
                else:
                    msg += '<li><code>{}</code></li>'.format(error)
            msg += '' if len(errors) == 1 else '</ul>'

            QMessageBox.warning(self, 'Application', msg, QMessageBox.Ok)

        return not bool(errors)

    # ---- VCS actions
    # ------------------------------------------------------------------------
    def vcs_command(self, action):
        """VCS action (commit, browse)"""
        fnames = self.get_selected_filenames()
        try:
            for path in sorted(fnames):
                vcs.run_vcs_tool(path, action)
        except vcs.ActionToolNotFound as error:
            msg = _("For %s support, please install one of the<br/> "
                    "following tools:<br/><br/>  %s")\
                        % (error.vcsname, ', '.join(error.tools))
            QMessageBox.critical(
                self, _("Error"),
                _("""<b>Unable to find external program.</b><br><br>%s"""
                  ) % str(msg))

    # ---- Settings
    # ------------------------------------------------------------------------
    def get_scrollbar_position(self):
        """Return scrollbar positions"""
        return (self.horizontalScrollBar().value(),
                self.verticalScrollBar().value())

    def set_scrollbar_position(self, position):
        """Set scrollbar positions"""
        # Scrollbars will be restored after the expanded state
        self._scrollbar_positions = position
        if self._to_be_loaded is not None and len(self._to_be_loaded) == 0:
            self.restore_scrollbar_positions()

    def restore_scrollbar_positions(self):
        """Restore scrollbar positions once tree is loaded"""
        hor, ver = self._scrollbar_positions
        self.horizontalScrollBar().setValue(hor)
        self.verticalScrollBar().setValue(ver)

    def get_expanded_state(self):
        """Return expanded state"""
        self.save_expanded_state()
        return self.__expanded_state

    def set_expanded_state(self, state):
        """Set expanded state"""
        self.__expanded_state = state
        self.restore_expanded_state()

    def save_expanded_state(self):
        """Save all items expanded state"""
        model = self.model()
        # If model is not installed, 'model' will be None: this happens when
        # using the Project Explorer without having selected a workspace yet
        if model is not None:
            self.__expanded_state = []
            for idx in model.persistentIndexList():
                if self.isExpanded(idx):
                    self.__expanded_state.append(self.get_filename(idx))

    def restore_directory_state(self, fname):
        """Restore directory expanded state"""
        root = osp.normpath(str(fname))
        if not osp.exists(root):
            # Directory has been (re)moved outside Spyder
            return
        for basename in os.listdir(root):
            path = osp.normpath(osp.join(root, basename))
            if osp.isdir(path) and path in self.__expanded_state:
                self.__expanded_state.pop(self.__expanded_state.index(path))
                if self._to_be_loaded is None:
                    self._to_be_loaded = []
                self._to_be_loaded.append(path)
                self.setExpanded(self.get_index(path), True)
        if not self.__expanded_state:
            self.fsmodel.directoryLoaded.disconnect(
                self.restore_directory_state)

    def follow_directories_loaded(self, fname):
        """Follow directories loaded during startup"""
        if self._to_be_loaded is None:
            return
        path = osp.normpath(str(fname))
        if path in self._to_be_loaded:
            self._to_be_loaded.remove(path)
        if self._to_be_loaded is not None and len(self._to_be_loaded) == 0:
            self.fsmodel.directoryLoaded.disconnect(
                self.follow_directories_loaded)
            if self._scrollbar_positions is not None:
                # The tree view need some time to render branches:
                QTimer.singleShot(50, self.restore_scrollbar_positions)

    def restore_expanded_state(self):
        """Restore all items expanded state"""
        if self.__expanded_state is not None:
            # In the old project explorer, the expanded state was a
            # dictionary:
            if isinstance(self.__expanded_state, list):
                self.fsmodel.directoryLoaded.connect(
                    self.restore_directory_state)
                self.fsmodel.directoryLoaded.connect(
                    self.follow_directories_loaded)

    # ---- Options
    # ------------------------------------------------------------------------
    def set_single_click_to_open(self, value):
        """Set single click to open items."""
        self.set_conf('single_click_to_open', value)

    def set_file_associations(self, value):
        """Set file associations open items."""
        self.set_conf('file_associations', value)

    def set_name_filters(self, name_filters):
        """Set name filters"""
        if self.get_conf('name_filters', []) == ['']:
            self.set_conf('name_filters', [])
        else:
            if running_under_pytest():
                self.set_conf('name_filters', name_filters)
            else:
                self.set_conf('name_filters', name_filters)

    def set_show_hidden(self, state):
        """Toggle 'show hidden files' state"""
        filters = (QDir.AllDirs | QDir.Files | QDir.Drives |
                   QDir.NoDotAndDotDot)
        if state:
            filters = (QDir.AllDirs | QDir.Files | QDir.Drives |
                       QDir.NoDotAndDotDot | QDir.Hidden)
        self.fsmodel.setFilter(filters)

    def reset_icon_provider(self):
        """Reset file system model icon provider
        The purpose of this is to refresh files/directories icons"""
        self.fsmodel.setIconProvider(IconProvider(self))

    def convert_notebook(self, fname):
        """Convert an IPython notebook to a Python script in editor"""
        try:
            script = nbexporter().from_filename(fname)[0]
        except Exception as e:
            QMessageBox.critical(
                self, _('Conversion error'),
                _("It was not possible to convert this "
                  "notebook. The error is:\n\n") + str(e))
            return
        self.sig_file_created.emit(script)

    def convert_notebooks(self):
        """Convert IPython notebooks to Python scripts in editor"""
        fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        for fname in fnames:
            self.convert_notebook(fname)

    def new_package(self, basedir=None):
        """New package"""

        if basedir is None:
            basedir = self.get_selected_dir()

        title = _('New package')
        subtitle = _('Package name:')
        self.create_new_folder(basedir, title, subtitle, is_package=True)

    def new_module(self, basedir=None):
        """New module"""

        if basedir is None:
            basedir = self.get_selected_dir()

        title = _("New module")
        filters = _("Python files")+" (*.py *.pyw *.ipy)"

        def create_func(fname):
            self.sig_module_created.emit(fname)

        self.create_new_file(basedir, title, filters, create_func)

    def go_to_parent_directory(self):
        pass


class ProxyModel(QSortFilterProxyModel):
    """Proxy model: filters tree view."""
    def __init__(self, parent):
        """Initialize the proxy model."""
        super(ProxyModel, self).__init__(parent)
        self.root_path = None
        self.path_list = []
        self.setDynamicSortFilter(True)

    def setup_filter(self, root_path, path_list):
        """
        Setup proxy model filter parameters.

        Parameters
        ----------
        root_path: str
            Root path of the proxy model.
        path_list: list
            List with all the paths.
        """
        self.root_path = osp.normpath(str(root_path))
        self.path_list = [osp.normpath(str(p)) for p in path_list]
        self.invalidateFilter()

    def sort(self, column, order=Qt.AscendingOrder):
        """Reimplement Qt method."""
        self.sourceModel().sort(column, order)

    def filterAcceptsRow(self, row, parent_index):
        """Reimplement Qt method."""
        if self.root_path is None:
            return True
        index = self.sourceModel().index(row, 0, parent_index)
        path = osp.normcase(osp.normpath(
            str(self.sourceModel().filePath(index))))
        if osp.normcase(self.root_path).startswith(path):
            # This is necessary because parent folders need to be scanned
            return True
        else:
            for p in [osp.normcase(p) for p in self.path_list]:
                if path == p or path.startswith(p+os.sep):
                    return True
            else:
                return False

    def data(self, index, role):
        """Show tooltip with full path only for the root directory."""
        if role == Qt.ToolTipRole:
            root_dir = self.path_list[0].split(osp.sep)[-1]
            if index.data() == root_dir:
                return osp.join(self.root_path, root_dir)
        return QSortFilterProxyModel.data(self, index, role)

    def type(self, index):
        """
        Returns the type of file for the given index.

        Parameters
        ----------
        index: int
            Given index to search its type.
        """
        return self.sourceModel().type(self.mapToSource(index))


class FilteredDirView(DirView):
    """Filtered file/directory tree view."""
    def __init__(self, parent=None):
        """Initialize the filtered dir view."""
        super().__init__(parent)
        self.proxymodel = None
        self.setup_proxy_model()
        self.root_path = None

    # ---- Model
    def setup_proxy_model(self):
        """Setup proxy model."""
        self.proxymodel = ProxyModel(self)
        self.proxymodel.setSourceModel(self.fsmodel)

    def install_model(self):
        """Install proxy model."""
        if self.root_path is not None:
            self.setModel(self.proxymodel)

    def set_root_path(self, root_path):
        """
        Set root path.

        Parameters
        ----------
        root_path: str
            New path directory.
        """
        self.root_path = root_path
        self.install_model()
        index = self.fsmodel.setRootPath(root_path)
        self.proxymodel.setup_filter(self.root_path, [])
        self.setRootIndex(self.proxymodel.mapFromSource(index))

    def get_index(self, filename):
        """
        Return index associated with filename.

        Parameters
        ----------
        filename: str
            String with the filename.
        """
        index = self.fsmodel.index(filename)
        if index.isValid() and index.model() is self.fsmodel:
            return self.proxymodel.mapFromSource(index)

    def set_folder_names(self, folder_names):
        """
        Set folder names

        Parameters
        ----------
        folder_names: list
            List with the folder names.
        """
        assert self.root_path is not None
        path_list = [osp.join(self.root_path, dirname)
                     for dirname in folder_names]
        self.proxymodel.setup_filter(self.root_path, path_list)

    def get_filename(self, index):
        """
        Return filename from index

        Parameters
        ----------
        index: int
            Index of the list of filenames
        """
        if index:
            path = self.fsmodel.filePath(self.proxymodel.mapToSource(index))
            return osp.normpath(str(path))

    def setup_project_view(self):
        """Setup view for projects."""
        for i in [1, 2, 3]:
            self.hideColumn(i)
        self.setHeaderHidden(True)
        # Disable the view of .spyproject.
        self.filter_directories()


class ExplorerTreeWidget(DirView):
    """
    File/directory explorer tree widget.
    """

    sig_dir_opened = Signal(str)
    """
    This signal is emitted when the current directory of the explorer tree
    has changed.

    Parameters
    ----------
    new_root_directory: str
        The new root directory path.

    Notes
    -----
    This happens when clicking (or double clicking depending on the option)
    a folder, turning this folder in the new root parent of the tree.
    """

    def __init__(self, parent=None):
        """Initialize the widget.

        Parameters
        ----------
        parent: PluginMainWidget, optional
            Parent widget of the explorer tree widget.
        """
        super().__init__(parent=parent)

        # Attributes
        self._parent = parent
        self.__last_folder = None
        self.__original_root_index = None
        self.history = []
        self.histindex = None

        # Enable drag events
        self.setDragEnabled(True)

    # ---- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def setup(self):
        """
        Perform the setup of the widget.
        """
        super().setup()

        # Actions
        self.previous_action = self.create_action(
            ExplorerTreeWidgetActions.Previous,
            text=_("Previous"),
            icon=self.create_icon('previous'),
            triggered=self.go_to_previous_directory,
        )
        self.next_action = self.create_action(
            ExplorerTreeWidgetActions.Next,
            text=_("Next"),
            icon=self.create_icon('next'),
            triggered=self.go_to_next_directory,
        )
        self.create_action(
            ExplorerTreeWidgetActions.Parent,
            text=_("Parent"),
            icon=self.create_icon('up'),
            triggered=self.go_to_parent_directory
        )

        # Toolbuttons
        self.filter_button = self.create_action(
            ExplorerTreeWidgetActions.ToggleFilter,
            text="",
            icon=ima.icon('filter'),
            toggled=self.change_filter_state
        )
        self.filter_button.setCheckable(True)

    def update_actions(self):
        """Update the widget actions."""
        super().update_actions()

    # ---- API
    # ------------------------------------------------------------------------
    def change_filter_state(self):
        """Handle the change of the filter state."""
        self.filter_on = not self.filter_on
        self.filter_button.setChecked(self.filter_on)
        self.filter_button.setToolTip(_("Filter filenames"))
        self.filter_files()

    # ---- Refreshing widget
    def set_current_folder(self, folder):
        """
        Set current folder and return associated model index

        Parameters
        ----------
        folder: str
            New path to the selected folder.
        """
        index = self.fsmodel.setRootPath(folder)
        self.__last_folder = folder
        self.setRootIndex(index)
        return index

    def get_current_folder(self):
        return self.__last_folder

    def refresh(self, new_path=None, force_current=False):
        """
        Refresh widget

        Parameters
        ----------
        new_path: str, optional
            New path to refresh the widget.
        force_current: bool, optional
            If False, it won't refresh widget if path has not changed.
        """
        if new_path is None:
            new_path = getcwd_or_home()
        if force_current:
            index = self.set_current_folder(new_path)
            self.expand(index)
            self.setCurrentIndex(index)

        self.previous_action.setEnabled(False)
        self.next_action.setEnabled(False)

        if self.histindex is not None:
            self.previous_action.setEnabled(self.histindex > 0)
            self.next_action.setEnabled(self.histindex < len(self.history) - 1)

        # Disable the view of .spyproject.
        self.filter_directories()

    # ---- Events
    def directory_clicked(self, dirname):
        """
        Directory was just clicked.

        Parameters
        ----------
        dirname: str
            Path to the clicked directory.
        """
        self.chdir(directory=dirname)

    # ---- Files/Directories Actions
    @Slot()
    def go_to_parent_directory(self):
        """Go to parent directory"""
        self.chdir(osp.abspath(osp.join(getcwd_or_home(), os.pardir)))

    @Slot()
    def go_to_previous_directory(self):
        """Back to previous directory"""
        self.histindex -= 1
        self.chdir(browsing_history=True)

    @Slot()
    def go_to_next_directory(self):
        """Return to next directory"""
        self.histindex += 1
        self.chdir(browsing_history=True)

    def update_history(self, directory):
        """
        Update browse history.

        Parameters
        ----------
        directory: str
            The new working directory.
        """
        try:
            directory = osp.abspath(str(directory))
            if directory in self.history:
                self.histindex = self.history.index(directory)
        except Exception:
            user_directory = get_home_dir()
            self.chdir(directory=user_directory, browsing_history=True)

    def chdir(self, directory=None, browsing_history=False, emit=True):
        """
        Set directory as working directory.

        Parameters
        ----------
        directory: str
            The new working directory.
        browsing_history: bool, optional
            Add the new `directory`to the browsing history. Default is False.
        emit: bool, optional
            Emit a signal when changing the working directpory.
            Default is True.
        """
        if directory is not None:
            directory = osp.abspath(str(directory))
        if browsing_history:
            directory = self.history[self.histindex]
        elif directory in self.history:
            self.histindex = self.history.index(directory)
        else:
            if self.histindex is None:
                self.history = []
            else:
                self.history = self.history[:self.histindex+1]
            if len(self.history) == 0 or \
               (self.history and self.history[-1] != directory):
                self.history.append(directory)
            self.histindex = len(self.history)-1
        directory = str(directory)

        try:
            os.chdir(directory)
            self.refresh(new_path=directory, force_current=True)
            if emit:
                self.sig_dir_opened.emit(directory)
        except PermissionError:
            QMessageBox.critical(self._parent, "Error",
                                 _("You don't have the right permissions to "
                                   "open this directory"))
        except FileNotFoundError:
            # Handle renaming directories on the fly.
            # See spyder-ide/spyder#5183
            self.history.pop(self.histindex)
