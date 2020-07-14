# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Files and Directories Explorer.
"""

from __future__ import with_statement

# Standard library imports
import os
import os.path as osp
import re
import shutil
import subprocess
import sys

# Third party imports
from qtpy.compat import getexistingdirectory, getsavefilename
from qtpy.QtCore import (QDir, QFileInfo, QMimeData, QSize,
                         QSortFilterProxyModel, Qt, QTimer, QUrl, Signal, Slot)
from qtpy.QtGui import QDrag, QKeySequence
from qtpy.QtWidgets import (QApplication, QFileIconProvider, QFileSystemModel,
                            QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                            QMenu, QMessageBox, QToolButton, QTreeView,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainWidget, SpyderWidgetMixin
from spyder.config.base import get_home_dir
from spyder.py3compat import str_lower, to_binary_string, to_text_string
from spyder.utils import encoding, misc, programs, vcs
from spyder.utils import icon_manager as ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import file_uri

try:
    from nbconvert import PythonExporter as nbexporter
except:
    nbexporter = None    # analysis:ignore


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class DirViewColumns:
    Size = 1
    Kind = 2
    Date = 3


class DirViewActions:
    # Triggers
    Copy = 'copy_action'
    CopyAbsolutePath = 'copy_absolute_path_action'
    CopyRelativePath = 'copy_relative_path_action'
    Delete = 'delete_action'
    NameFilters = 'name_filters_action'
    Move = 'move_action'
    NewFile = 'new_file_action'
    NewFolder = 'new_folder_action'
    OpenInterpreter = 'open_interpreter_action'
    OpenWithSpyder = 'open_with_spyder_action'
    OpenWithSystem = 'open_with_system_explorer_action'
    OpenWithSystem2 = 'open_with_system_explorer_2_action',
    Paste = 'paste_action'
    Rename = 'rename_action'
    Run = 'run_action'
    ShowInSystemExplorer = 'show_in_system_explorer_action'
    VersionControlCommit = 'version_control_commit_action'
    VersionControlBrowse = 'version_control_browse_action'

    # Toggles
    ToggleDateColumn = 'toggle_date_column_action'
    ToggleKindColumn = 'toggle_kind_column_action'
    ToggleShowAll = 'toggle_show_all_action'
    ToggleSingleClickToOpen = 'toggle_single_click_to_open_action'
    ToggleSizeColumn = 'toggle_size_column_action'


class PythonActions:
    # Triggers
    ConvertNotebook = 'convert_notebook_action'
    CreateModule = 'create_module_action'
    CreatePackage = 'create_package_action'


class ExplorerTreeWidgetActions:
    # Triggers
    Previous = 'previous_action'
    Next = 'next_action'
    Parent = 'parent_action'

    # Toggles
    ToggleShowCDOnly = 'toggle_show_cd_only_action'


class DirViewMenus:
    Header = 'header_menu'
    Context = 'context_menu'
    New = 'new_submenu'
    OpenWith = 'open_with_submenu'


class DirViewHeadeMenuSections:
    Main = 'main_section'


class DirViewContextMenuSections:
    # In order of appearance in the menu
    New = 'new_section'
    CopyPaste = 'copy_paste_section'
    System = 'system_section'
    VersionControl = 'version_control_section'
    Interpreter = 'interpreter_section'
    Extras = 'extras_section'


class DirViewNewSubMenuSections:
    # In order of appearance in the menu
    General = 'general_section'
    Language = 'language_section'


class DirViewOpenWithSubMenuSections:
    # In order of appearance in the menu
    Main = 'main_section'


class ExplorerWidgetHeaderMenuSections:
    Main = 'main_section'


class ExplorerWidgetOptionsMenuSections:
    Header = 'header_section'
    Common = 'common_section'


class ExplorerWidgetMainToolBarSections:
    Main = 'main_section'


# --- Utils
# ----------------------------------------------------------------------------
def open_file_in_external_explorer(filename):
    if sys.platform == "darwin":
        subprocess.call(["open", "-R", filename])
    elif os.name == 'nt':
        subprocess.call(["explorer", "/select,", filename])
    else:
        filename=os.path.dirname(filename)
        subprocess.call(["xdg-open", filename])


def show_in_external_file_explorer(fnames=None):
    """
    Show files in external file explorer.

    Args:
        fnames (list): Names of files to show.
    """
    if not isinstance(fnames, (tuple, list)):
        fnames = [fnames]

    for fname in fnames:
        open_file_in_external_explorer(fname)


def fixpath(path):
    """
    Normalize path fixing case, making absolute and removing symlinks.
    """
    norm = osp.normcase if os.name == 'nt' else osp.normpath
    return norm(osp.abspath(osp.realpath(path)))


def create_script(fname):
    """
    Create a new Python script.
    """
    text = os.linesep.join(["# -*- coding: utf-8 -*-", "", ""])
    try:
        encoding.write(to_text_string(text), fname, 'utf-8')
    except EnvironmentError as error:
        QMessageBox.critical(
            _("Save Error"),
            _("<b>Unable to save file '%s'</b>"
              "<br><br>Error message:<br>%s"
              ) % (osp.basename(fname), str(error)),
        )


def listdir(path, include=r'.', exclude=r'\.pyc$|^\.', show_all=False,
            folders_only=False):
    """
    List files and directories.
    """
    namelist = []
    dirlist = [to_text_string(osp.pardir)]
    for item in os.listdir(to_text_string(path)):
        if re.search(exclude, item) and not show_all:
            continue

        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif folders_only:
            continue
        elif re.search(include, item) or show_all:
            namelist.append(item)

    return (sorted(dirlist, key=str_lower)
            + sorted(namelist, key=str_lower))


def has_subdirectories(path, include, exclude, show_all):
    """
    Return True if path has subdirectories.
    """
    try:
        # > 1 because of '..'
        return len( listdir(path, include, exclude,
                            show_all, folders_only=True) ) > 1
    except (IOError, OSError):
        return False


# --- Widgets
# ----------------------------------------------------------------------------
class IconProvider(QFileIconProvider):
    """
    Project tree widget icon provider.
    """

    def __init__(self, treeview):
        super(IconProvider, self).__init__()
        self.treeview = treeview

    @Slot(int)
    @Slot(QFileInfo)
    def icon(self, icontype_or_qfileinfo):
        """
        Reimplement Qt method.
        """
        if isinstance(icontype_or_qfileinfo, QFileIconProvider.IconType):
            return super(IconProvider, self).icon(icontype_or_qfileinfo)
        else:
            qfileinfo = icontype_or_qfileinfo
            fname = osp.normpath(to_text_string(qfileinfo.absoluteFilePath()))
            if osp.isfile(fname) or osp.isdir(fname):
                icon = ima.get_icon_by_extension_or_type(fname,
                                                         scale_factor=1.0)
            else:
                icon = ima.get_icon('binary', adjust_for_interface=True)

            return icon


class DirView(QTreeView, SpyderWidgetMixin):
    """
    Base file/directory tree view.
    """
    DEFAULT_OPTIONS = {
        'date_column': False,
        'file_associations': {},
        'kind_column': True,
        'name_filters': ['*.py', '*.pyw'],
        'show_all': True,
        'single_click_to_open': False,
        'size_column': False,
    }

    # Signals
    sig_edited = Signal(str)
    sig_option_changed = Signal(str, object)
    sig_removed = Signal(str)
    sig_renamed = Signal(str, str)
    sig_run_requested = Signal(str)
    sig_tree_removed = Signal(str)
    sig_tree_renamed = Signal(str, str)
    sig_new_file_requested = Signal(str)
    sig_open_file_requested = Signal(str)
    sig_redirect_stdio_requested = Signal(bool)
    sig_open_interpreter_requested = Signal(str)

    # TODO: move python specific actions to extension
    sig_module_created = Signal(str)
    """
    This signal is emitted to inform that a new python module has been
    created.

    Parameters
    ----------
    module: str
        Path to created module.
    """

    sig_package_created = Signal(str)
    """
    This signal is emitted to inform that a new python packge has been
    created.

    Parameters
    ----------
    dirname: str
        Path to created package.
    """

    def __init__(self, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(parent=parent)

        # Attributes
        self._last_column = 0
        self._last_order = True
        self._parent = parent
        self._scrollbar_positions = None
        self._to_be_loaded = None
        self.__expanded_state = None
        self.parent_widget = parent

        # Widgets
        self.context_menu = None
        self.fsmodel = None
        self.header_menu = None
        header = self.header()

        # Setup
        self.setSelectionMode(self.ExtendedSelection)
        self.setup_fs_model()
        header.setContextMenuPolicy(Qt.CustomContextMenu)

        # Signals
        header.customContextMenuRequested.connect(self.show_header_menu)

        # Setup
        self.change_options(options)

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

    # --- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def setup(self, options=DEFAULT_OPTIONS):
        self.setup_view()

        # File actions
        new_file_action = self.create_action(
            DirViewActions.NewFile,
            text=_("File..."),
            icon=self.create_icon('filenew'),
            triggered=lambda: self.new_file(),
        )
        new_folder_action = self.create_action(
            DirViewActions.NewFolder,
            text=_("Folder..."),
            icon=self.create_icon('folder_new'),
            triggered=lambda: self.new_folder(),
        )
        run_action = self.create_action(
            DirViewActions.Run,
            text=_("Run"),
            icon=self.create_icon('run'),
            triggered=lambda: self.run(),
        )

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
            icon="move.png",  # TODO:Update image
            triggered=lambda: self.move(),
        )
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

        # Other actions
        if sys.platform == 'darwin':
            show_in_finder_text = _("Show in Finder")
        else:
            show_in_finder_text = _("Show in Folder")

        show_in_system_explorer_action = self.create_action(
            DirViewActions.ShowInSystemExplorer,
            text=show_in_finder_text,
            triggered=lambda: self.show_in_external_file_explorer(),
        )

        self.open_interpreter = self.create_action(
            DirViewActions.OpenInterpreter,
            text=_("Open IPython console here"),
            triggered=lambda: self.open_interpreter(),
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
        self.create_action(
            DirViewActions.NameFilters,
            text=_("Edit filename filters..."),
            icon=self.create_icon('filter'),
            triggered=lambda: self.edit_filters(),
        )
        self.create_action(
            DirViewActions.ToggleShowAll,
            text=_("Show all files"),
            toggled=lambda val: self.set_option('show_all', val),
            initial=self.get_option('show_all'),
        )
        self.create_action(
            DirViewActions.ToggleSingleClickToOpen,
            text=_("Single click to open"),
            toggled=lambda val: self.set_option('single_click_to_open', val),
            initial=self.get_option('single_click_to_open'),
        )

        # Header Actions
        size_column_action = self.create_action(
            DirViewActions.ToggleSizeColumn,
            text=_('Size'),
            toggled=lambda val: self.set_option('size_column', val),
            initial=self.get_option('size_column'),
            register_shortcut=False,
        )
        kind_column_action = self.create_action(
            DirViewActions.ToggleKindColumn,
            text=_('Kind') if sys.platform == 'darwin' else _('Type'),
            toggled=lambda val: self.set_option('kind_column', val),
            initial=self.get_option('kind_column'),
            register_shortcut=False,
        )
        date_column_action = self.create_action(
            DirViewActions.ToggleDateColumn,
            text=_("Date modified"),
            toggled=lambda val: self.set_option('date_column', val),
            initial=self.get_option('date_column'),
            register_shortcut=False,
        )

        # Header Context Menu
        self.header_menu = self.create_menu(DirViewMenus.Header)
        for item in [size_column_action, kind_column_action,
                     date_column_action]:
            self.add_item_to_menu(
                item,
                menu=self.header_menu,
                section=DirViewHeadeMenuSections.Main,
            )

        # New submenu
        self.new_submenu = self.create_menu(
            DirViewMenus.New,
            _('New'),
        )
        for item in [new_file_action, new_folder_action]:
            self.add_item_to_menu(
                item,
                menu=self.new_submenu,
                section=DirViewNewSubMenuSections.General,
            )

        # Open with submenu
        self.open_with_submenu = self.create_menu(
            DirViewMenus.OpenWith,
            _('Open with'),
        )

        # Context submenu
        self.context_menu = self.create_menu(DirViewMenus.Context)
        for item in [self.new_submenu, run_action, self.open_with_submenu,
                     self.open_with_spyder_action, self.open_external_action,
                     delete_action, rename_action, self.move_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.New,
            )

        for item in [copy_action, self.paste_action,
                     copy_absolute_path_action, copy_relative_path_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.CopyPaste,
            )

        for item in [self.vcs_commit_action, self.vcs_log_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DirViewContextMenuSections.VersionControl,
            )

        self.add_item_to_menu(
            show_in_system_explorer_action,
            menu=self.context_menu,
            section=DirViewContextMenuSections.System,
        )

        self.add_item_to_menu(
            self.open_interpreter,
            menu=self.context_menu,
            section=DirViewContextMenuSections.Extras,
        )

        # Signals
        self.context_menu.aboutToShow.connect(self.update_actions)

        # TODO: Move to extension API
        self.setup_python()

    def on_option_update(self, option, value):
        if option == 'size_column':
            self.setColumnHidden(DirViewColumns.Size, not value)
        elif option == 'kind_column':
            self.setColumnHidden(DirViewColumns.Kind, not value)
        elif option == 'date_column':
            self.setColumnHidden(DirViewColumns.Date, not value)
        elif option == 'name_filters':
            self.fsmodel.setNameFilters(value)
        elif option == 'show_all':
            if value:
                self.fsmodel.setNameFilters([])
            else:
                self.fsmodel.setNameFilters(self.get_option('name_filters'))

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
        self.open_interpreter.setVisible(only_dirs)
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

        # TODO: Move to extension API
        self.update_actions_python()

    # Qt overrides
    # ------------------------------------------------------------------------
    def sortByColumn(self, column, order=Qt.AscendingOrder):
        """
        Override Qt method.
        """
        header = self.header()
        header.setSortIndicatorShown(True)
        super().sortByColumn(column, order)
        header.setSortIndicator(0, order)
        self._last_column = column
        self._last_order = not self._last_order

    def viewportEvent(self, event):
        """
        Override Qt method.
        """
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
        return super().viewportEvent(event)

    def contextMenuEvent(self, event):
        """
        Override Qt method.
        """
        # Needed to handle not initialized menu.
        # See spyder-ide/spyder#6975
        try:
            fnames = self.get_selected_filenames()
            if len(fnames) != 0:
                self.context_menu.popup(event.globalPos())
        except AttributeError:
            pass

    def keyPressEvent(self, event):
        """
        Override Qt method.
        """
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked()
        elif event.key() == Qt.Key_F2:
            self.rename()
        elif event.key() == Qt.Key_Delete:
            self.delete()
        elif event.key() == Qt.Key_Backspace:
            self.go_to_parent_directory()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """
        Override Qt method.
        """
        super().mouseDoubleClickEvent(event)
        self.clicked()

    def mouseReleaseEvent(self, event):
        """
        Override Qt method.
        """
        super().mouseReleaseEvent(event)
        if self.get_option('single_click_to_open'):
            self.clicked()

    def dragEnterEvent(self, event):
        """
        Drag and Drop - Enter event.
        """
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """
        Drag and Drop - Move event.
        """
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def startDrag(self, dropActions):
        """
        Reimplement Qt Method - handle drag event.
        """
        data = QMimeData()
        data.setUrls([QUrl(fname) for fname in self.get_selected_filenames()])
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec_()

    # --- Model
    # ------------------------------------------------------------------------
    def setup_fs_model(self):
        """
        Setup filesystem model.
        """
        filters = (QDir.AllDirs | QDir.Files | QDir.Drives
                   | QDir.NoDotAndDotDot | QDir.Hidden)
        self.fsmodel = QFileSystemModel(self)
        self.fsmodel.setFilter(filters)
        self.fsmodel.setNameFilterDisables(False)

    def install_model(self):
        """
        Install filesystem model.
        """
        self.setModel(self.fsmodel)

    def setup_view(self):
        """
        Setup view.
        """
        self.install_model()
        self.fsmodel.directoryLoaded.connect(
            lambda: self.resizeColumnToContents(0))
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        self.fsmodel.modelReset.connect(self.reset_icon_provider)
        self.reset_icon_provider()

        # Disable the view of .spyproject.
        # TODO: Add methods to extend this functionality
        self.filter_directories()

    def reset_icon_provider(self):
        """
        Reset file system model icon provider.

        The purpose of this is to refresh files/directories icons.
        """
        self.fsmodel.setIconProvider(IconProvider(self))

    # --- File/Dir Helpers
    # ------------------------------------------------------------------------
    def get_filename(self, index):
        """
        Return filename associated with *index*.
        """
        if index:
            return osp.normpath(to_text_string(self.fsmodel.filePath(index)))

    def get_index(self, filename):
        """
        Return index associated with filename.
        """
        return self.fsmodel.index(filename)

    def get_selected_filenames(self):
        """
        Return selected filenames.
        """
        fnames = []
        if self.selectionMode() == self.ExtendedSelection:
            if self.selectionModel() is not None:
                fnames = [self.get_filename(idx) for idx in
                          self.selectionModel().selectedRows()]
        else:
            fnames = [self.get_filename(self.currentIndex())]

        return fnames

    def get_dirname(self, index):
        """
        Return dirname associated with `index`.
        """
        fname = self.get_filename(index)
        if fname:
            if osp.isdir(fname):
                return fname
            else:
                return osp.dirname(fname)

    # --- General actions API
    # ------------------------------------------------------------------------
    def show_header_menu(self, pos):
        """
        Display header menu.
        """
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
        """
        Directory was just clicked.
        """
        pass

    @Slot()
    def edit_filters(self, filters=None):
        """
        Edit name filters.
        """
        valid = True
        if filters is None:
            filters, valid = QInputDialog.getText(
                self,
                _('Edit filename filters'),
                _('Name filters:'),
                QLineEdit.Normal,
                ", ".join(self.get_option('name_filters')),
            )

        if valid:
            filters = [f.strip() for f in to_text_string(filters).split(',')]
            self.set_option('name_filters', filters)

    @Slot()
    def open(self, fnames=None):
        """
        Open files with the appropriate application.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        for fname in fnames:
            if osp.isfile(fname) and encoding.is_text_file(fname):
                self.sig_open_file_requested.emit(fname)
            else:
                self.open_outside_spyder([fname])

    @Slot()
    def open_association(self, app_path):
        """
        Open files with given application executable path.
        """
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
        """
        Open files with default application.
        """
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
            ok = programs.start_file(path)
            if not ok:
                self.sig_edited.emit(path)

    def remove_tree(self, dirname):
        """
        Remove whole directory tree.

        Reimplemented in project explorer widget.
        """
        while osp.exists(dirname):
            try:
                shutil.rmtree(dirname, onerror=misc.onerror)
            except Exception as e:
                # This handles a Windows problem with shutil.rmtree.
                # See spyder-ide/spyder#8567.
                if type(e).__name__ == "OSError":
                    error_path = to_text_string(e.filename)
                    shutil.rmtree(error_path, ignore_errors=True)

    def delete_file(self, fname, multiple, yes_to_all):
        """
        Delete file.
        """
        if multiple:
            buttons = (QMessageBox.Yes | QMessageBox.YesToAll
                       | QMessageBox.No | QMessageBox.Cancel)
        else:
            buttons = QMessageBox.Yes | QMessageBox.No

        if yes_to_all is None:
            answer = QMessageBox.warning(
                self,
                _("Delete"),
                _("Do you really want to delete <b>%s</b>?"
                  ) % osp.basename(fname),
                buttons,
            )

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
                self,
                _("Project Explorer"),
                _("<b>Unable to %s <i>%s</i></b><br><br>Error message:<br>%s"
                  ) % (action_str, fname, to_text_string(error)),
            )

        return False

    @Slot()
    def delete(self, fnames=None):
        """
        Delete files.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            spyproject_path = osp.join(fname, '.spyproject')
            if osp.isdir(fname) and osp.exists(spyproject_path):
                QMessageBox.information(
                    self,
                    _('File Explorer'),
                    _("The current directory contains a project.<br><br>"
                      "If you want to delete the project, please go to "
                      "<b>Projects</b> &raquo; <b>Delete Project</b>"),
                )
            else:
                yes_to_all = self.delete_file(fname, multiple, yes_to_all)
                if yes_to_all is not None and not yes_to_all:
                    # Canceled
                    break

    def rename_file(self, fname):
        """
        Rename file.
        """
        path, valid = QInputDialog.getText(
            self,
            _('Rename'),
            _('New name:'),
            QLineEdit.Normal,
            osp.basename(fname),
        )

        if valid:
            path = osp.join(osp.dirname(fname), to_text_string(path))
            if path == fname:
                return

            if osp.exists(path):
                answer = QMessageBox.warning(
                    self,
                    _("Rename"),
                    _("Do you really want to rename <b>%s</b> and "
                      "overwrite the existing file <b>%s</b>?"
                      ) % (osp.basename(fname), osp.basename(path)),
                    QMessageBox.Yes | QMessageBox.No,
                )
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
                    self,
                    _("Rename"),
                    _("<b>Unable to rename file <i>%s</i></b>"
                      "<br><br>Error message:<br>%s"
                      ) % (osp.basename(fname), to_text_string(error)),
                )

    @Slot()
    def show_in_external_file_explorer(self, fnames=None):
        """
        Show file in external file explorer.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        show_in_external_file_explorer(fnames)

    @Slot()
    def rename(self, fnames=None):
        """
        Rename files.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]

        for fname in fnames:
            self.rename_file(fname)

    @Slot()
    def move(self, fnames=None, directory=None):
        """
        Move files/directories.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        orig = fixpath(osp.dirname(fnames[0]))
        while True:
            self.sig_redirect_stdio_requested.emit(False)
            if directory is None:
                folder = getexistingdirectory(
                    self,
                    _("Select directory"),
                    orig,
                )
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
                    self,
                    _("Error"),
                    _("<b>Unable to move <i>%s</i></b>"
                      "<br><br>Error message:<br>%s"
                      ) % (basename, to_text_string(error)),
                )

    def create_new_folder(self, current_path, title, subtitle, is_package):
        """
        Create new folder.
        """
        if current_path is None:
            current_path = ''

        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        name, valid = QInputDialog.getText(
            self,
            title,
            subtitle,
            QLineEdit.Normal,
            "",
        )

        if valid:
            dirname = osp.join(current_path, to_text_string(name))
            try:
                os.mkdir(dirname)
            except EnvironmentError as error:
                QMessageBox.critical(
                    self,
                    title,
                    _("<b>Unable to create folder <i>%s</i></b>"
                      "<br><br>Error message:<br>%s"
                      ) % (dirname, to_text_string(error)),
                )
            finally:
                if is_package:
                    fname = osp.join(dirname, '__init__.py')
                    try:
                        with open(fname, 'wb') as f:
                            f.write(to_binary_string('#'))

                        self.sig_package_created.emit(dirname)

                        return dirname
                    except EnvironmentError as error:
                        QMessageBox.critical(
                            self,
                            title,
                            _("<b>Unable to create file <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (fname, to_text_string(error)),
                        )

    def new_folder(self, basedir=None):
        """
        New folder.
        """
        if basedir is None:
            fnames = self.get_selected_filenames()
            basedir = fixpath(osp.dirname(fnames[0]))

        title = _('New folder')
        subtitle = _('Folder name:')
        self.create_new_folder(basedir, title, subtitle, is_package=False)

    def create_new_file(self, current_path, title, filters, create_func):
        """
        Create new file.

        Returns True if successful.
        """
        if current_path is None:
            current_path = ''

        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)

        self.sig_redirect_stdio_requested.emit(False)
        fname, _selfilter = getsavefilename(self, title, current_path,
                                            filters)
        self.sig_redirect_stdio_requested.emit(True)

        if fname:
            try:
                create_func(fname)
                return fname
            except EnvironmentError as error:
                QMessageBox.critical(
                    self,
                    _("New file"),
                    _("<b>Unable to create file <i>%s</i>"
                      "</b><br><br>Error message:<br>%s"
                      ) % (fname, to_text_string(error)),
                )

    def new_file(self, basedir=None):
        """
        New file.
        """
        if basedir is None:
            fnames = self.get_selected_filenames()
            basedir = fixpath(osp.dirname(fnames[0]))

        title = _("New file")
        filters = _("All files") + " (*)"

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
        """
        Run files.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        for fname in fnames:
            self.sig_run_requested.emit(fname)

    def copy_path(self, fnames=None, method="absolute"):
        """
        Copy absolute or relative path to given file(s)/folders(s).
        """
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
        """
        Copy absolute paths of named files/directories to the clipboard.
        """
        self.copy_path(method="absolute")

    @Slot()
    def copy_relative_path(self):
        """
        Copy relative paths of named files/directories to the clipboard.
        """
        self.copy_path(method="relative")

    @Slot()
    def copy_file_clipboard(self, fnames=None):
        """
        Copy file(s)/folders(s) to clipboard.
        """
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
                self,
                _('File/Folder copy error'),
                _("Cannot copy this type of file(s) or "
                  "folder(s). The error was: \n\n") + to_text_string(e),
            )

    @Slot()
    def save_file_clipboard(self, fnames=None):
        """
        Paste file from clipboard into file/project explorer directory.
        """
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
                            QMessageBox.critical(
                                self,
                                _('Error pasting file'),
                                _("Unsupported copy operation. "
                                  "The error was:\n\n") + to_text_string(e),
                            )
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
                                QMessageBox.critical(
                                    self,
                                    _('Recursive copy'),
                                    _("Source is an ancestor of destination"
                                      " folder."),
                                )
                                continue
                            shutil.copytree(source_name, destination)
                        except Exception as e:
                            QMessageBox.critical(
                                self,
                                _('Error pasting folder'),
                                _("Unsupported copy operation. The error was:"
                                  "\n\n") + to_text_string(e),
                            )
            else:
                QMessageBox.critical(
                    self,
                    _("No file in clipboard"),
                    _("No file in the clipboard. Please copy"
                      " a file to the clipboard first."),
                )
        else:
            if QApplication.clipboard().mimeData().hasUrls():
                QMessageBox.critical(
                    self,
                    _('Blank area'),
                    _("Cannot paste in the blank area."),
                )
            else:
                pass

    def filter_directories(self):
        """
        Filter the directories to show.
        """
        index = self.get_index('.spyproject')
        if index is not None:
            self.setRowHidden(index.row(), index.parent(), True)

    def open_interpreter(self, fnames=None):
        """
        Open interpreter.
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        for path in sorted(fnames):
            self.sig_open_interpreter_requested.emit(path)

    # --- File Associations
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
        """
        Return the list of matching file associations for `fname`.
        """
        for exts, values in self.get_option('file_associations').items():
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

    def check_launch_error_codes(self, return_codes):
        """
        Check return codes and display message box if errors found.
        """
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
            QMessageBox.warning(
                self,
                'Application',
                msg,
                QMessageBox.Ok,
            )

        return not bool(errors)

    # --- VCS actions
    # ------------------------------------------------------------------------
    def vcs_command(self, action):
        """
        VCS action (commit, browse).
        """
        fnames = self.get_selected_filenames()
        try:
            for path in sorted(fnames):
                vcs.run_vcs_tool(path, action)
        except vcs.ActionToolNotFound as error:
            msg = (_("For %s support, please install one of the<br/> "
                     "following tools:<br/><br/>  %s")
                   % (error.vcsname, ', '.join(error.tools)))
            QMessageBox.critical(
                self,
                _("Error"),
                _("""<b>Unable to find external program.</b><br><br>%s"""
                  ) % to_text_string(msg),
            )

    # --- Settings
    # ------------------------------------------------------------------------
    def get_scrollbar_position(self):
        """
        Return scrollbar positions.
        """
        return (self.horizontalScrollBar().value(),
                self.verticalScrollBar().value())

    def set_scrollbar_position(self, position):
        """
        Set scrollbar positions.
        """
        # Scrollbars will be restored after the expanded state
        self._scrollbar_positions = position
        if self._to_be_loaded is not None and len(self._to_be_loaded) == 0:
            self.restore_scrollbar_positions()

    def restore_scrollbar_positions(self):
        """
        Restore scrollbar positions once tree is loaded.
        """
        hor, ver = self._scrollbar_positions
        self.horizontalScrollBar().setValue(hor)
        self.verticalScrollBar().setValue(ver)

    def get_expanded_state(self):
        """
        Return expanded state.
        """
        self.save_expanded_state()
        return self.__expanded_state

    def set_expanded_state(self, state):
        """
        Set expanded state.
        """
        self.__expanded_state = state
        self.restore_expanded_state()

    def save_expanded_state(self):
        """
        Save all items expanded state.
        """
        model = self.model()
        # If model is not installed, 'model' will be None: this happens when
        # using the Project Explorer without having selected a workspace yet
        if model is not None:
            self.__expanded_state = []
            for idx in model.persistentIndexList():
                if self.isExpanded(idx):
                    self.__expanded_state.append(self.get_filename(idx))

    def restore_directory_state(self, fname):
        """
        Restore directory expanded state.
        """
        root = osp.normpath(to_text_string(fname))
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
        """
        Follow directories loaded during startup.
        """
        if self._to_be_loaded is None:
            return

        path = osp.normpath(to_text_string(fname))
        if path in self._to_be_loaded:
            self._to_be_loaded.remove(path)

        if self._to_be_loaded is not None and len(self._to_be_loaded) == 0:
            self.fsmodel.directoryLoaded.disconnect(
                self.follow_directories_loaded)

            if self._scrollbar_positions is not None:
                # The tree view need some time to render branches:
                QTimer.singleShot(50, self.restore_scrollbar_positions)

    def restore_expanded_state(self):
        """
        Restore all items expanded state.
        """
        if self.__expanded_state is not None:
            # In the old project explorer, the expanded state was a
            # dictionnary.
            if isinstance(self.__expanded_state, list):
                self.fsmodel.directoryLoaded.connect(
                    self.restore_directory_state)
                self.fsmodel.directoryLoaded.connect(
                    self.follow_directories_loaded)

    # TODO: these could be removed?
    # --- Options
    # ------------------------------------------------------------------------
    def set_single_click_to_open(self, value):
        self.set_option('single_click_to_open', value)

    def set_show_all(self, value):
        self.set_option('show_all', value)

    def set_file_associations(self, value):
        self.set_option('file_associations', value)

    # TODO: provide methods for extension and use them
    # --- Python specific actions API
    # ------------------------------------------------------------------------
    def setup_python(self):
        """
        """
        create_module_action = self.create_action(
            PythonActions.CreateModule,
            text=_('Module'),
            triggered=lambda: self.new_module(),
        )
        create_package_action = self.create_action(
            PythonActions.CreatePackage,
            text=_('Package'),
            triggered=lambda: self.new_package(),
        )
        convert_notebook_action = self.create_action(
            PythonActions.ConvertNotebook,
            text=_('Convert to Python script'),
            triggered=lambda: self.convert_notebooks(),
        )

        # Context menus
        context_menu = self.get_menu(DirViewMenus.Context)
        self.add_item_to_menu(
            convert_notebook_action,
            menu=context_menu,
            section=DirViewContextMenuSections.Extras,
        )

        # New submenu
        new_menu = self.get_menu(DirViewMenus.New)
        for item in [create_module_action, create_package_action]:
            self.add_item_to_menu(
                item,
                menu=new_menu,
                section=DirViewNewSubMenuSections.Language,
            )

    def update_actions_python(self):
        """
        """
        fnames = self.get_selected_filenames()
        only_notebooks = all([osp.splitext(fname)[1] == '.ipynb'
                              for fname in fnames])
        only_modules = all([osp.splitext(fname)[1] in ('.py', '.pyw', '.ipy')
                            for fname in fnames])

        nb_visible = only_notebooks and nbexporter is not None
        self.get_action(PythonActions.ConvertNotebook).setVisible(nb_visible)
        self.get_action(DirViewActions.Run).setVisible(only_modules)

    def convert_notebook(self, fname):
        """
        Convert an IPython notebook to a Python script in editor.
        """
        try:
            script = nbexporter().from_filename(fname)[0]
        except Exception as e:
            QMessageBox.critical(
                self,
                _('Conversion error'),
                _("It was not possible to convert this "
                  "notebook. The error is:\n\n") + to_text_string(e))
            return

        self.sig_new_file_requested.emit(script)

    @Slot()
    def convert_notebooks(self):
        """
        Convert IPython notebooks to Python scripts in editor.
        """
        fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]

        for fname in fnames:
            self.convert_notebook(fname)

    def new_module(self, basedir=None):
        """
        New module.
        """
        if basedir is None:
            fnames = self.get_selected_filenames()
            basedir = fixpath(osp.dirname(fnames[0]))

        title = _("New module")
        filters = _("Python scripts") + " (*.py *.pyw *.ipy)"

        def create_func(fname):
            self.sig_module_created.emit(fname)

        self.create_new_file(basedir, title, filters, create_func)

    def new_package(self, basedir=None):
        """
        New package.
        """
        if basedir is None:
            fnames = self.get_selected_filenames()
            basedir = fixpath(osp.dirname(fnames[0]))

        title = _('New package')
        subtitle = _('Package name:')
        self.create_new_folder(basedir, title, subtitle, is_package=True)


class ProxyModel(QSortFilterProxyModel):
    """
    Proxy model: filters tree view.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.root_path = None
        self.path_list = []
        self.setDynamicSortFilter(True)

    def setup_filter(self, root_path, path_list):
        """
        Setup proxy model filter parameters.
        """
        self.root_path = osp.normpath(to_text_string(root_path))
        self.path_list = [osp.normpath(to_text_string(p)) for p in path_list]
        self.invalidateFilter()

    def sort(self, column, order=Qt.AscendingOrder):
        """
        Reimplement Qt method.
        """
        self.sourceModel().sort(column, order)

    def filterAcceptsRow(self, row, parent_index):
        """
        Reimplement Qt method.
        """
        if self.root_path is None:
            return True

        index = self.sourceModel().index(row, 0, parent_index)
        path = osp.normcase(osp.normpath(
            to_text_string(self.sourceModel().filePath(index))))

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
        """
        Show tooltip with full path only for the root directory.
        """
        if role == Qt.ToolTipRole:
            root_dir = self.path_list[0].split(osp.sep)[-1]
            if index.data() == root_dir:
                return osp.join(self.root_path, root_dir)

        return QSortFilterProxyModel.data(self, index, role)


class FilteredDirView(DirView):
    """
    Filtered file/directory tree view.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proxymodel = None
        self.setup_proxy_model()
        self.root_path = None

    #---- Model
    def setup_proxy_model(self):
        """
        Setup proxy model.
        """
        self.proxymodel = ProxyModel(self)
        self.proxymodel.setSourceModel(self.fsmodel)

    def install_model(self):
        """
        Install proxy model.
        """
        if self.root_path is not None:
            self.setModel(self.proxymodel)

    def set_root_path(self, root_path):
        """
        Set root path.
        """
        self.root_path = root_path
        self.install_model()
        index = self.fsmodel.setRootPath(root_path)
        self.proxymodel.setup_filter(self.root_path, [])
        self.setRootIndex(self.proxymodel.mapFromSource(index))

    def get_index(self, filename):
        """
        Return index associated with filename.
        """
        index = self.fsmodel.index(filename)
        if index.isValid() and index.model() is self.fsmodel:
            return self.proxymodel.mapFromSource(index)

    def set_folder_names(self, folder_names):
        """
        Set folder names.
        """
        # Fix assert as they can be removed when compiling with optiimize flag
        assert self.root_path is not None
        path_list = [osp.join(self.root_path, dirname)
                     for dirname in folder_names]
        self.proxymodel.setup_filter(self.root_path, path_list)

    def get_filename(self, index):
        """
        Return filename from index.
        """
        if index:
            path = self.fsmodel.filePath(self.proxymodel.mapToSource(index))
            return osp.normpath(to_text_string(path))

    def setup_project_view(self):
        """
        Setup view for projects.
        """
        for i in [1, 2, 3]:
            self.hideColumn(i)

        self.setHeaderHidden(True)

        # Disable the view of .spyproject.
        self.filter_directories()


class ExplorerTreeWidget(DirView):
    """
    File/directory explorer tree widget.

    show_cd_only: Show current directory only
        (True/False: enable/disable the option
        None: enable the option and do not allow the user to disable it)
    """

    DEFAULT_OPTIONS = {
        'date_column': False,
        'file_associations': {},
        'kind_column': True,
        'name_filters': ['*.py', '*.pyw'],
        'show_all': False,
        'show_cd_only': True,
        'single_click_to_open': False,
        'size_column': False,
    }

    # Signals
    sig_dir_opened = Signal(str)

    def __init__(self, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(parent=parent, options=options)

        self.__last_folder = None
        self.__original_root_index = None
        self.history = []
        self.histindex = None
        self.show_cd_only = self.get_option('show_cd_only')

        # Enable drag events
        self.setDragEnabled(True)

    # --- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def setup(self, options=DEFAULT_OPTIONS):
        super().setup(options=options)

        self.previous_action = self.create_action(
            ExplorerTreeWidgetActions.Previous,
            text=_("Previous"),
            icon=self.create_icon('ArrowBack'),
            triggered=self.go_to_previous_directory,
        )
        self.next_action = self.create_action(
            ExplorerTreeWidgetActions.Next,
            text=_("Next"),
            icon=self.create_icon('ArrowForward'),
            triggered=self.go_to_next_directory,
        )
        self.create_action(
            ExplorerTreeWidgetActions.Parent,
            text=_("Parent"),
            icon=self.create_icon('ArrowUp'),
            triggered=self.go_to_parent_directory
        )
        self.cd_only_action = self.create_action(
            ExplorerTreeWidgetActions.ToggleShowCDOnly,
            text=_("Show current directory only"),
            toggled=self.toggle_show_cd_only,
        )

    def update_actions(self):
        super().update_actions()

    def on_option_update(self, option, value):
        super().on_option_update(option, value)

    # # --- Context menu
    # def setup_common_actions(self):
    #     """Setup context menu common actions"""
    #     actions = super(ExplorerTreeWidget, self).setup_common_actions()
    #     if self.show_cd_only is None:
    #         # Enabling the 'show current directory only' option but do not
    #         # allow the user to disable it
    #         self.show_cd_only = True
    #     else:
    #         # Show current directory only
    #         cd_only_action = create_action(self,
    #                                        _("Show current directory only"),
    #                                        toggled=self.toggle_show_cd_only)
    #         cd_only_action.setChecked(self.show_cd_only)
    #         self.toggle_show_cd_only(self.show_cd_only)
    #         actions.append(cd_only_action)
    #     return actions

    # --- API
    # ------------------------------------------------------------------------
    @Slot(bool)
    def toggle_show_cd_only(self, checked):
        """
        Toggle show current directory only mode.
        """
        self.sig_option_changed.emit('show_cd_only', checked)
        self.show_cd_only = checked
        if checked:
            if self.__last_folder is not None:
                self.set_current_folder(self.__last_folder)
        elif self.__original_root_index is not None:
            self.setRootIndex(self.__original_root_index)

    # --- Refreshing widget
    def set_current_folder(self, folder):
        """
        Set current folder and return associated model index.
        """
        index = self.fsmodel.setRootPath(folder)
        self.__last_folder = folder
        if self.show_cd_only:
            if self.__original_root_index is None:
                self.__original_root_index = self.rootIndex()

            self.setRootIndex(index)

        return index

    def get_current_folder(self):
        return self.__last_folder

    def refresh(self, new_path=None, force_current=False):
        """
        Refresh widget.

        force=False: won't refresh widget if path has not changed.
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
            self.next_action.setEnabled(
                self.histindex < len(self.history) - 1)

        # Disable the view of .spyproject
        self.filter_directories()

    # --- Events
    def directory_clicked(self, dirname):
        """
        Directory was just clicked.
        """
        self.chdir(directory=dirname)

    # --- Files/Directories Actions
    @Slot()
    def go_to_parent_directory(self):
        """
        Go to parent directory.
        """
        self.chdir(osp.abspath(osp.join(getcwd_or_home(), os.pardir)))

    @Slot()
    def go_to_previous_directory(self):
        """
        Back to previous directory.
        """
        self.histindex -= 1
        self.chdir(browsing_history=True)

    @Slot()
    def go_to_next_directory(self):
        """
        Return to next directory.
        """
        self.histindex += 1
        self.chdir(browsing_history=True)

    def update_history(self, directory):
        """
        Update browse history.
        """
        try:
            directory = osp.abspath(to_text_string(directory))
            if directory in self.history:
                self.histindex = self.history.index(directory)
        except Exception:
            user_directory = get_home_dir()
            self.chdir(directory=user_directory, browsing_history=True)

    def chdir(self, directory=None, browsing_history=False, emit=True):
        """
        Set directory as working directory.
        """
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
                self.history = self.history[:self.histindex + 1]

            if (len(self.history) == 0
                    or (self.history and self.history[-1] != directory)):
                self.history.append(directory)

            self.histindex = len(self.history) - 1

        directory = to_text_string(directory)
        try:
            PermissionError
            FileNotFoundError
        except NameError:
            PermissionError = OSError
            if os.name == 'nt':
                FileNotFoundError = WindowsError
            else:
                FileNotFoundError = IOError

        try:
            os.chdir(directory)
            self.refresh(new_path=directory, force_current=True)

            if emit:
                self.sig_dir_opened.emit(directory)
        except PermissionError:
            QMessageBox.critical(
                self._parent,
                "Error",
                _("You don't have the right permissions to open this"
                  " directory"),
            )
        except FileNotFoundError:
            # Handle renaming directories on the fly.
            # See spyder-ide/spyder#5183
            self.history.pop(self.histindex)


class ExplorerWidget(PluginMainWidget):
    """
    Explorer widget.
    """

    DEFAULT_OPTIONS = {
        'date_column': False,
        'file_associations': {},
        'kind_column': True,
        'name_filters': ['*.py', '*.pyw'],
        'show_all': True,
        'show_cd_only': True,
        'single_click_to_open': True,
        'size_column': False,
    }

    # --- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The path to the directory opened.

    Notes
    -----
    This will update the current working directory.
    """

    sig_edited = Signal(str)
    """
    This signal is emitted when a file is open outside Spyder for edition.

    Parameters
    ----------
    path: str
        File path opened externally for edition.
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

    sig_tree_renamed = Signal(str)
    """
    This signal is emitted when a folder is renamed.

    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_new_file_requested = Signal()
    """
    This signal is emitted to request creating a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

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

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(name, plugin=plugin, parent=parent, options=options)

        # Widgets
        tree_options = self.options_from_keys(
            options,
            ExplorerTreeWidget.DEFAULT_OPTIONS,
        )
        self.treewidget = ExplorerTreeWidget(parent=self,
                                             options=tree_options)

        # Setup
        self.treewidget.setup(tree_options)
        self.chdir(getcwd_or_home())

        # Layouts
        layout = QHBoxLayout()
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

        # Signals
        self.treewidget.sig_option_changed.connect(self.sig_option_changed)
        self.treewidget.sig_edited.connect(self.sig_edited)
        self.treewidget.sig_removed.connect(self.sig_removed)
        self.treewidget.sig_tree_removed.connect(self.sig_tree_removed)
        self.treewidget.sig_renamed.connect(self.sig_renamed)
        self.treewidget.sig_tree_renamed.connect(self.sig_tree_renamed)
        self.treewidget.sig_new_file_requested.connect(
            self.sig_new_file_requested)
        self.treewidget.sig_run_requested.connect(
            self.sig_run_requested)
        self.treewidget.sig_open_file_requested.connect(
            self.sig_open_file_requested)
        self.treewidget.sig_open_interpreter_requested.connect(
            self.sig_open_interpreter_requested)
        self.treewidget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        self.treewidget.sig_dir_opened.connect(
            self.sig_dir_opened)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_focus_widget(self):
        return self.treewidget

    def get_title(self):
        return _('Explorer')

    def setup(self, options):
        # Add to menu
        menu = self.get_options_menu()
        for item in [self.get_action(DirViewActions.NameFilters),
                     self.get_action(DirViewActions.ToggleShowAll),
                     self.get_action(DirViewActions.ToggleSingleClickToOpen)]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Common,
            )

        for item in [self.get_action(DirViewActions.ToggleSizeColumn),
                     self.get_action(DirViewActions.ToggleKindColumn),
                     self.get_action(DirViewActions.ToggleDateColumn)]:
            self.add_item_to_menu(
                item,
                menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Header,
            )

        # Add to toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.get_action(ExplorerTreeWidgetActions.Previous),
                     self.get_action(ExplorerTreeWidgetActions.Next),
                     self.get_action(ExplorerTreeWidgetActions.Parent)]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=ExplorerWidgetMainToolBarSections.Main,
            )

    def update_actions(self):
        pass

    def on_option_update(self, option, value):
        self.treewidget.on_option_update(option, value)

    # --- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            Directory to set as working directory.
        """
        self.treewidget.chdir(directory, emit=emit)

    def go_to_parent_directory(self):
        """Move to parent directory."""
        self.treewidget.go_to_parent_directory()

    def go_to_previous_directory(self):
        """Move to previous directory in history."""
        self.treewidget.go_to_previous_directory()

    def go_to_next_directory(self):
        """Move to next directory in history."""
        self.treewidget.go_to_next_directory()

    def update_history(self, directory):
        """
        Update history with directory.

        Parameters
        ----------
        directory: str
            Path to add to history.
        """
        self.treewidget.update_history(directory)

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
        self.treewidget.refresh(new_path, force_current)

    def get_current_folder(self):
        """Get current folder in the tree widget."""
        return self.treewidget.get_current_folder()

    def set_current_folder(self, folder):
        """Set the current folder in the tree widget."""
        self.treewidget.set_current_folder(folder)


# =============================================================================
# Tests
# =============================================================================
class FileExplorerTest(QWidget):
    def __init__(self, directory=None, file_associations={}):
        super().__init__()

        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))

        options = ExplorerWidget.DEFAULT_OPTIONS
        options['file_associations'] = file_associations
        self.explorer = ExplorerWidget('explorer', parent=self, plugin=None,
                                       options=options)
        self.explorer._setup(options)
        self.explorer.setup(options)
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
        self.explorer.sig_option_changed.connect(
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))


class ProjectExplorerTest(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.treewidget = FilteredDirView(self)
        self.treewidget.setup_view()
        self.treewidget.set_root_path(osp.dirname(osp.abspath(__file__)))
        self.treewidget.set_folder_names(['variableexplorer'])
        self.treewidget.setup_project_view()
        vlayout.addWidget(self.treewidget)


def test(file_explorer):
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    if file_explorer:
        test = FileExplorerTest()
    else:
        test = ProjectExplorerTest()
    test.resize(640, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test(file_explorer=True)
    test(file_explorer=False)
