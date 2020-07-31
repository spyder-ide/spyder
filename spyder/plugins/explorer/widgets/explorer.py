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
from spyder.config.base import _, get_home_dir
from spyder.config.manager import CONF
from spyder.py3compat import str_lower, to_binary_string, to_text_string
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils import misc, programs, vcs
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_plugin_layout, file_uri,
                                    MENU_SEPARATOR, QInputDialogMultiline)

try:
    from nbconvert import PythonExporter as nbexporter
except:
    nbexporter = None    # analysis:ignore


def open_file_in_external_explorer(filename):
    if sys.platform == "darwin":
        subprocess.call(["open", "-R", filename])
    elif os.name == 'nt':
        subprocess.call(["explorer", "/select,", filename])
    else:
        filename=os.path.dirname(filename)
        subprocess.call(["xdg-open", filename])


def show_in_external_file_explorer(fnames=None):
    """Show files in external file explorer

    Args:
        fnames (list): Names of files to show.
    """
    if not isinstance(fnames, (tuple, list)):
        fnames = [fnames]
    for fname in fnames:
        open_file_in_external_explorer(fname)


def fixpath(path):
    """Normalize path fixing case, making absolute and removing symlinks"""
    norm = osp.normcase if os.name == 'nt' else osp.normpath
    return norm(osp.abspath(osp.realpath(path)))


def create_script(fname):
    """Create a new Python script"""
    text = os.linesep.join(["# -*- coding: utf-8 -*-", "", ""])
    try:
        encoding.write(to_text_string(text), fname, 'utf-8')
    except EnvironmentError as error:
        QMessageBox.critical(_("Save Error"),
                             _("<b>Unable to save file '%s'</b>"
                               "<br><br>Error message:<br>%s"
                               ) % (osp.basename(fname), str(error)))

def listdir(path, include=r'.', exclude=r'\.pyc$|^\.', show_all=False,
            folders_only=False):
    """List files and directories"""
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
    return sorted(dirlist, key=str_lower) + \
           sorted(namelist, key=str_lower)


def has_subdirectories(path, include, exclude, show_all):
    """Return True if path has subdirectories"""
    try:
        # > 1 because of '..'
        return len( listdir(path, include, exclude,
                            show_all, folders_only=True) ) > 1
    except (IOError, OSError):
        return False


class IconProvider(QFileIconProvider):
    """Project tree widget icon provider"""

    def __init__(self, treeview):
        super(IconProvider, self).__init__()
        self.treeview = treeview

    @Slot(int)
    @Slot(QFileInfo)
    def icon(self, icontype_or_qfileinfo):
        """Reimplement Qt method"""
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


class DirView(QTreeView):
    """Base file/directory tree view"""
    sig_edit = Signal(str)
    sig_removed = Signal(str)
    sig_removed_tree = Signal(str)
    sig_renamed = Signal(str, str)
    sig_renamed_tree = Signal(str, str)
    sig_create_module = Signal(str)
    sig_run = Signal(str)
    sig_new_file = Signal(str)
    sig_open_interpreter = Signal(str)
    redirect_stdio = Signal(bool)

    def __init__(self, parent=None):
        super(DirView, self).__init__(parent)
        self.parent_widget = parent

        # Options
        self.name_filters = ['*.py']
        self.show_all = None
        self.show_hidden = None
        self.single_click_to_open = False
        self.file_associations = {}
        self._last_column = 0
        self._last_order = True

        header = self.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)

        self.menu = None
        self.menu_header = QMenu(self)
        self.common_actions = None
        self.__expanded_state = None
        self._to_be_loaded = None
        self.fsmodel = None
        self.setup_fs_model()
        self._scrollbar_positions = None
        self.setSelectionMode(self.ExtendedSelection)
        self.shortcuts = self.create_shortcuts()

        # Signals
        header.customContextMenuRequested.connect(self.show_header_menu)

    #---- Model
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

    def sortByColumn(self, column, order=Qt.AscendingOrder):
        """Override Qt method."""
        header = self.header()
        header.setSortIndicatorShown(True)
        QTreeView.sortByColumn(self, column, order)
        header.setSortIndicator(0, order)
        self._last_column = column
        self._last_order = not self._last_order

    def show_header_menu(self, pos):
        """Display header menu."""
        self.menu_header.clear()
        kind = _('Kind') if sys.platform == 'darwin' else _('Type')
        items = [_('Size'), kind, _("Date modified")]
        header_actions = []
        for idx, item in enumerate(items):
            column = idx + 1
            action = create_action(
                self,
                item,
                None,
                None,
                toggled=lambda x, c=column: self.toggle_column(c),
            )
            action.blockSignals(True)
            action.setChecked(not self.isColumnHidden(column))
            action.blockSignals(False)
            header_actions.append(action)

        add_actions(self.menu_header, header_actions)
        self.menu_header.popup(self.mapToGlobal(pos))

    def toggle_column(self, column):
        """Toggle visibility of column."""
        is_hidden = self.isColumnHidden(column)
        self.setColumnHidden(column, not is_hidden)
        visible_columns = [0]
        for col in range(1, 4):
            if not self.isColumnHidden(col):
                visible_columns.append(col)

        self.parent_widget.sig_option_changed.emit('visible_columns',
                                                   visible_columns)

    def set_single_click_to_open(self, value):
        """Set single click to open items."""
        self.single_click_to_open = value
        self.parent_widget.sig_option_changed.emit('single_click_to_open',
                                                   value)

    def set_file_associations(self, value):
        """Set file associations open items."""
        self.file_associations = value

    def set_name_filters(self, name_filters):
        """Set name filters"""
        self.name_filters = name_filters
        self.fsmodel.setNameFilters(name_filters)

    def set_show_all(self, state):
        """Toggle 'show all files' state"""
        self.filters_action.setDisabled(state)
        if state:
            self.fsmodel.setNameFilters([])
        else:
            self.fsmodel.setNameFilters(self.name_filters)

    def set_show_hidden(self, state):
        """Toggle 'show hidden files' state"""
        filters = (QDir.AllDirs | QDir.Files | QDir.Drives |
                   QDir.NoDotAndDotDot)
        if state:
            filters = (QDir.AllDirs | QDir.Files | QDir.Drives |
                       QDir.NoDotAndDotDot | QDir.Hidden)
        self.fsmodel.setFilter(filters)

    def get_filename(self, index):
        """Return filename associated with *index*"""
        if index:
            return osp.normpath(to_text_string(self.fsmodel.filePath(index)))

    def get_index(self, filename):
        """Return index associated with filename"""
        return self.fsmodel.index(filename)

    def get_selected_filenames(self):
        """Return selected filenames"""
        if self.selectionMode() == self.ExtendedSelection:
            if self.selectionModel() is None:
                return []
            rows = self.selectionModel().selectedRows()
            return [self.get_filename(idx) for idx in rows]
        else:
            return [self.get_filename(self.currentIndex())]

    def get_dirname(self, index):
        """Return dirname associated with *index*"""
        fname = self.get_filename(index)
        if fname:
            if osp.isdir(fname):
                return fname
            else:
                return osp.dirname(fname)

    #---- Tree view widget
    def setup(self, name_filters=['*.py', '*.pyw'], show_all=False,
              show_hidden=False, single_click_to_open=False,
              file_associations={}):
        """Setup tree widget"""
        self.setup_view()

        self.set_name_filters(name_filters)
        self.show_all = show_all
        self.show_hidden = show_hidden
        self.single_click_to_open = single_click_to_open
        self.set_file_associations(file_associations)

        # Setup context menu
        self.menu = QMenu(self)
        self.common_actions = self.setup_common_actions()

    def reset_icon_provider(self):
        """Reset file system model icon provider
        The purpose of this is to refresh files/directories icons"""
        self.fsmodel.setIconProvider(IconProvider(self))

    #---- Context menu
    def setup_common_actions(self):
        """Set-up context menu common actions."""
        # Show all files
        self.all_action = create_action(
            self,
            _("Show all files"),
            toggled=self.toggle_all)
        # Show hidden files
        self.hidden_action = create_action(
            self,
            _("Show hidden files"),
            toggled=self.toggle_hidden,
        )
        # Filters
        self.filters_action = create_action(
            self, _("Show files with these extensions..."), None,
            ima.icon('filter'),
            triggered=self.edit_filter,
        )
        # Single click
        self.single_click_to_open_action = create_action(
            self,
            _("Single click to open"),
            toggled=self.set_single_click_to_open,
        )

        actions = [self.all_action, self.hidden_action, self.filters_action,
                   MENU_SEPARATOR, self.single_click_to_open_action]
        self.update_common_actions()
        return actions

    def update_common_actions(self):
        """Update the status of widget actions based on stored state."""
        self.set_show_all(self.show_all)
        self.set_show_hidden(self.show_hidden)
        self.all_action.setChecked(self.show_all)
        self.hidden_action.setChecked(self.show_hidden)
        self.single_click_to_open_action.setChecked(self.single_click_to_open)

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
        for exts, values in self.file_associations.items():
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

    @Slot()
    def edit_filter(self):
        """Edit name filters."""
        dialog = QInputDialogMultiline(
            self, _('Edit filename filters'),
            _('Name filters:'),
            ", ".join(self.name_filters))
        dialog.resize(500, 300)
        result = dialog.exec_()
        if result:
            filters = dialog.text_edit.toPlainText()
            filters = [f.strip() for f in to_text_string(filters).split(',')]
            self.parent_widget.sig_option_changed.emit('name_filters', filters)
            self.set_name_filters(filters)

    @Slot(bool)
    def toggle_all(self, checked):
        """Toggle all files mode"""
        self.parent_widget.sig_option_changed.emit('show_all', checked)
        self.show_all = checked
        self.set_show_all(checked)

    @Slot(bool)
    def toggle_hidden(self, checked):
        """Toggle hidden files."""
        self.parent_widget.sig_option_changed.emit('show_hidden', checked)
        self.show_hidden = checked
        self.set_show_hidden(checked)

    def create_file_new_actions(self, fnames):
        """Return actions for submenu 'New...'"""
        root_path = self.fsmodel.rootPath()
        new_file_act = create_action(self, _("File..."),
                                     icon=ima.icon('TextFileIcon'),
                                     triggered=lambda:
                                     self.new_file(root_path))
        new_module_act = create_action(self, _("Python script..."),
                                       icon=ima.icon('python'),
                                       triggered=lambda:
                                       self.new_module(root_path))
        new_folder_act = create_action(self, _("Folder..."),
                                       icon=ima.icon('DirOpenIcon'),
                                       triggered=lambda:
                                       self.new_folder(root_path))
        new_package_act = create_action(self, _("Python Package..."),
                                        triggered=lambda:
                                        self.new_package(root_path))
        return [new_file_act, new_folder_act, None,
                new_module_act, new_package_act]

    def create_file_import_actions(self, fnames):
        """Return actions for submenu 'Import...'"""
        return []

    def create_file_manage_actions(self, fnames):
        """Return file management actions"""
        only_files = all([osp.isfile(_fn) for _fn in fnames])
        only_modules = all([osp.splitext(_fn)[1] in ('.py', '.pyw', '.ipy')
                            for _fn in fnames])
        only_notebooks = all([osp.splitext(_fn)[1] == '.ipynb'
                              for _fn in fnames])
        only_valid = all([encoding.is_text_file(_fn) for _fn in fnames])
        run_action = create_action(self, _("Run"), icon=ima.icon('run'),
                                   triggered=self.run)
        open_with_spyder_action = create_action(
            self, _("Open in Spyder"), icon=ima.icon('edit'),
            triggered=self.open)
        open_with_menu = QMenu(_('Open with'), self)

        open_external_action = create_action(
            self,
            _("Open externally"),
            triggered=self.open_external)

        move_action = create_action(
            self,
            _("Move..."),
            icon="move.png",
            triggered=self.move)

        delete_action = create_action(
            self,
            _("Delete..."),
            icon=ima.icon('editdelete'),
            triggered=self.delete)

        rename_action = create_action(
            self,
            _("Rename..."),
            icon=ima.icon('rename'),
            triggered=self.rename)

        ipynb_convert_action = create_action(
            self,
            _("Convert to Python script"),
            icon=ima.icon('python'),
            triggered=self.convert_notebooks)

        copy_file_clipboard_action = create_action(
            self,
            _("Copy"),
            QKeySequence(CONF.get_shortcut('explorer', 'copy file')),
            icon=ima.icon('editcopy'),
            triggered=self.copy_file_clipboard)

        save_file_clipboard_action = create_action(
            self,
            _("Paste"),
            QKeySequence(CONF.get_shortcut('explorer', 'paste file')),
            icon=ima.icon('editpaste'),
            triggered=self.save_file_clipboard)

        copy_absolute_path_action = create_action(
            self,
            _("Copy Absolute Path"),
            QKeySequence(CONF.get_shortcut('explorer', 'copy absolute path')),
            triggered=self.copy_absolute_path)

        copy_relative_path_action = create_action(
            self,
            _("Copy Relative Path"),
            QKeySequence(CONF.get_shortcut('explorer', 'copy relative path')),
            triggered=self.copy_relative_path)

        actions = []
        if only_modules:
            actions.append(run_action)

        if only_files:
            if only_valid:
                actions.append(open_with_spyder_action)

            if len(fnames) == 1:
                assoc = self.get_file_associations(fnames[0])
            elif len(fnames) > 1:
                assoc = self.get_common_file_associations(fnames)
            else:
                assoc = []

            if len(assoc) >= 1:
                actions.append(open_with_menu)
                open_with_actions = []
                for app_name, fpath in assoc:
                    if not (os.path.isfile(fpath) or os.path.isdir(fpath)):
                        app_name += _(' (Application not found!)')

                    open_with_action = create_action(
                        self, app_name,
                        triggered=lambda x, y=fpath: self.open_association(y))

                    if not (os.path.isfile(fpath) or os.path.isdir(fpath)):
                        open_with_action.setDisabled(True)

                    open_with_actions.append(open_with_action)
                open_external_action_2 = create_action(
                    self, _("Default external application"),
                    triggered=self.open_external)
                open_with_actions.append(open_external_action_2)
                add_actions(open_with_menu, open_with_actions)
            else:
                actions.append(open_external_action)

        if sys.platform == 'darwin':
            text = _("Show in Finder")
        else:
            text = _("Show in Folder")

        external_fileexp_action = create_action(
            self, text, triggered=self.show_in_external_file_explorer)
        actions += [delete_action, rename_action]
        if fnames:
            basedir = fixpath(osp.dirname(fnames[0]))
            if all([fixpath(osp.dirname(_fn)) == basedir for _fn in fnames]):
                actions.append(move_action)
        actions += [None]
        actions += [copy_file_clipboard_action, save_file_clipboard_action,
                    copy_absolute_path_action, copy_relative_path_action]
        if not QApplication.clipboard().mimeData().hasUrls():
            save_file_clipboard_action.setDisabled(True)
        actions += [None]
        actions.append(external_fileexp_action)
        actions.append(None)
        if only_notebooks and nbexporter is not None:
            actions.append(ipynb_convert_action)

        if fnames:
            dirname = (
                fnames[0] if osp.isdir(fnames[0]) else osp.dirname(fnames[0]))
        if len(fnames) == 1:
            # VCS support is quite limited for now, so we are enabling the VCS
            # related actions only when a single file/folder is selected:
            if vcs.is_vcs_repository(dirname):
                commit_slot = lambda: self.vcs_command([dirname], 'commit')
                browse_slot = lambda: self.vcs_command([dirname], 'browse')
                vcs_ci = create_action(self, _("Commit"),
                                       icon=ima.icon('vcs_commit'),
                                       triggered=commit_slot)
                vcs_log = create_action(self, _("Browse repository"),
                                        icon=ima.icon('vcs_browse'),
                                        triggered=browse_slot)
                actions += [None, vcs_ci, vcs_log]

        # Needed to disable actions in the context menu if there's an
        # empty folder. See spyder-ide/spyder#13004
        if len(fnames) == 1 and self.selectionModel():
            current_index = self.selectionModel().currentIndex()
            if (self.model().type(current_index) == 'Folder' and
                    self.model().rowCount(current_index) == 0):
                fnames = []
        if not fnames:
            for action in actions:
                if action:
                    action.setDisabled(True)
        return actions

    def create_folder_manage_actions(self, fnames):
        """Return folder management actions"""
        actions = []
        if os.name == 'nt':
            _title = _("Open command prompt here")
        else:
            _title = _("Open terminal here")
        _title = _("Open IPython console here")
        action = create_action(self, _title,
                               triggered=lambda:
                               self.open_interpreter(fnames))
        actions.append(action)
        return actions

    def create_context_menu_actions(self):
        """Create context menu actions"""
        actions = []
        fnames = self.get_selected_filenames()
        new_actions = self.create_file_new_actions(fnames)
        if len(new_actions) > 1:
            # Creating a submenu only if there is more than one entry
            new_act_menu = QMenu(_('New'), self)
            add_actions(new_act_menu, new_actions)
            actions.append(new_act_menu)
        else:
            actions += new_actions
        import_actions = self.create_file_import_actions(fnames)
        if len(import_actions) > 1:
            # Creating a submenu only if there is more than one entry
            import_act_menu = QMenu(_('Import'), self)
            add_actions(import_act_menu, import_actions)
            actions.append(import_act_menu)
        else:
            actions += import_actions
        if actions:
            actions.append(None)
        actions += self.create_file_manage_actions(fnames)
        if actions:
            actions.append(None)
        if fnames and all([osp.isdir(_fn) for _fn in fnames]):
            actions += self.create_folder_manage_actions(fnames)
        return actions

    def update_menu(self):
        """Update context menu"""
        self.menu.clear()
        add_actions(self.menu, self.create_context_menu_actions())

    #---- Events
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
            self.update_menu()
            self.menu.popup(event.globalPos())
            event.accept()
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
        QTreeView.mouseDoubleClickEvent(self, event)
        self.clicked()

    def mouseReleaseEvent(self, event):
        """Reimplement Qt method."""
        QTreeView.mouseReleaseEvent(self, event)
        if self.single_click_to_open:
            self.clicked()

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

    #---- Drag
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

    #---- File/Directory actions
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

    @Slot()
    def open(self, fnames=None):
        """Open files with the appropriate application"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            if osp.isfile(fname) and encoding.is_text_file(fname):
                self.parent_widget.sig_open_file.emit(fname)
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
        """Open file outside Spyder with the appropriate application
        If this does not work, opening unknown file in Spyder, as text file"""
        for path in sorted(fnames):
            path = file_uri(path)
            ok = programs.start_file(path)
            if not ok:
                self.sig_edit.emit(path)

    def open_interpreter(self, fnames):
        """Open interpreter"""
        for path in sorted(fnames):
            self.sig_open_interpreter.emit(path)

    @Slot()
    def run(self, fnames=None):
        """Run Python scripts"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            self.sig_run.emit(fname)

    def remove_tree(self, dirname):
        """Remove whole directory tree
        Reimplemented in project explorer widget"""
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
        """Delete file"""
        if multiple:
            buttons = QMessageBox.Yes|QMessageBox.YesToAll| \
                      QMessageBox.No|QMessageBox.Cancel
        else:
            buttons = QMessageBox.Yes|QMessageBox.No
        if yes_to_all is None:
            answer = QMessageBox.warning(self, _("Delete"),
                                 _("Do you really want "
                                   "to delete <b>%s</b>?"
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
                self.sig_removed_tree.emit(fname)
            return yes_to_all
        except EnvironmentError as error:
            action_str = _('delete')
            QMessageBox.critical(self, _("Project Explorer"),
                            _("<b>Unable to %s <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (action_str, fname, to_text_string(error)))
        return False

    @Slot()
    def delete(self, fnames=None):
        """Delete files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            spyproject_path = osp.join(fname,'.spyproject')
            if osp.isdir(fname) and osp.exists(spyproject_path):
                QMessageBox.information(self, _('File Explorer'),
                                        _("The current directory contains a "
                                        "project.<br><br>"
                                        "If you want to delete"
                                        " the project, please go to "
                                        "<b>Projects</b> &raquo; <b>Delete "
                                        "Project</b>"))
            else:
                yes_to_all = self.delete_file(fname, multiple, yes_to_all)
                if yes_to_all is not None and not yes_to_all:
                    # Canceled
                    break

    def convert_notebook(self, fname):
        """Convert an IPython notebook to a Python script in editor"""
        try:
            script = nbexporter().from_filename(fname)[0]
        except Exception as e:
            QMessageBox.critical(self, _('Conversion error'),
                                 _("It was not possible to convert this "
                                 "notebook. The error is:\n\n") + \
                                 to_text_string(e))
            return
        self.sig_new_file.emit(script)

    @Slot()
    def convert_notebooks(self):
        """Convert IPython notebooks to Python scripts in editor"""
        fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        for fname in fnames:
            self.convert_notebook(fname)

    def rename_file(self, fname):
        """Rename file"""
        path, valid = QInputDialog.getText(self, _('Rename'),
                              _('New name:'), QLineEdit.Normal,
                              osp.basename(fname))
        if valid:
            path = osp.join(osp.dirname(fname), to_text_string(path))
            if path == fname:
                return
            if osp.exists(path):
                if QMessageBox.warning(self, _("Rename"),
                         _("Do you really want to rename <b>%s</b> and "
                           "overwrite the existing file <b>%s</b>?"
                           ) % (osp.basename(fname), osp.basename(path)),
                         QMessageBox.Yes|QMessageBox.No) == QMessageBox.No:
                    return
            try:
                misc.rename_file(fname, path)
                if osp.isfile(path):
                    self.sig_renamed.emit(fname, path)
                else:
                    self.sig_renamed_tree.emit(fname, path)
                return path
            except EnvironmentError as error:
                QMessageBox.critical(self, _("Rename"),
                            _("<b>Unable to rename file <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (osp.basename(fname), to_text_string(error)))

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
            self.redirect_stdio.emit(False)
            if directory is None:
                folder = getexistingdirectory(self, _("Select directory"),
                                              orig)
            else:
                folder = directory
            self.redirect_stdio.emit(True)
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
                QMessageBox.critical(self, _("Error"),
                                     _("<b>Unable to move <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (basename, to_text_string(error)))

    def create_new_folder(self, current_path, title, subtitle, is_package):
        """Create new folder"""
        if current_path is None:
            current_path = ''
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        name, valid = QInputDialog.getText(self, title, subtitle,
                                           QLineEdit.Normal, "")
        if valid:
            dirname = osp.join(current_path, to_text_string(name))
            try:
                os.mkdir(dirname)
            except EnvironmentError as error:
                QMessageBox.critical(self, title,
                                     _("<b>Unable "
                                       "to create folder <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (dirname, to_text_string(error)))
            finally:
                if is_package:
                    fname = osp.join(dirname, '__init__.py')
                    try:
                        with open(fname, 'wb') as f:
                            f.write(to_binary_string('#'))
                        return dirname
                    except EnvironmentError as error:
                        QMessageBox.critical(self, title,
                                             _("<b>Unable "
                                               "to create file <i>%s</i></b>"
                                               "<br><br>Error message:<br>%s"
                                               ) % (fname,
                                                    to_text_string(error)))

    def new_folder(self, basedir):
        """New folder"""
        title = _('New folder')
        subtitle = _('Folder name:')
        self.create_new_folder(basedir, title, subtitle, is_package=False)

    def new_package(self, basedir):
        """New package"""
        title = _('New package')
        subtitle = _('Package name:')
        self.create_new_folder(basedir, title, subtitle, is_package=True)

    def create_new_file(self, current_path, title, filters, create_func):
        """Create new file
        Returns True if successful"""
        if current_path is None:
            current_path = ''
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        self.redirect_stdio.emit(False)
        fname, _selfilter = getsavefilename(self, title, current_path, filters)
        self.redirect_stdio.emit(True)
        if fname:
            try:
                create_func(fname)
                return fname
            except EnvironmentError as error:
                QMessageBox.critical(self, _("New file"),
                                     _("<b>Unable to create file <i>%s</i>"
                                       "</b><br><br>Error message:<br>%s"
                                       ) % (fname, to_text_string(error)))

    def new_file(self, basedir):
        """New file"""
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

    def new_module(self, basedir):
        """New module"""
        title = _("New module")
        filters = _("Python scripts")+" (*.py *.pyw *.ipy)"

        def create_func(fname):
            self.sig_create_module.emit(fname)

        self.create_new_file(basedir, title, filters, create_func)

    def go_to_parent_directory(self):
        pass

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
        copied_from = self.parent_widget.__class__.__name__
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
            QMessageBox.critical(self,
                                 _('File/Folder copy error'),
                                 _("Cannot copy this type of file(s) or "
                                     "folder(s). The error was:\n\n")
                                 + to_text_string(e))

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
                                                 + to_text_string(e))
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
                                                   "\n\n") + to_text_string(e))
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

    def create_shortcuts(self):
        """Create shortcuts for this file explorer."""
        # Configurable
        copy_clipboard_file = CONF.config_shortcut(
            self.copy_file_clipboard,
            context='explorer',
            name='copy file',
            parent=self)

        paste_clipboard_file = CONF.config_shortcut(
            self.save_file_clipboard,
            context='explorer',
            name='paste file',
            parent=self)

        copy_absolute_path = CONF.config_shortcut(
            self.copy_absolute_path,
            context='explorer',
            name='copy absolute path',
            parent=self)

        copy_relative_path = CONF.config_shortcut(
            self.copy_relative_path,
            context='explorer',
            name='copy relative path',
            parent=self)

        return [copy_clipboard_file, paste_clipboard_file, copy_absolute_path,
                copy_relative_path]

    def get_shortcut_data(self):
        """
        Return shortcut data, a list of tuples (shortcut, text, default).
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    #----- VCS actions
    def vcs_command(self, fnames, action):
        """VCS action (commit, browse)"""
        try:
            for path in sorted(fnames):
                vcs.run_vcs_tool(path, action)
        except vcs.ActionToolNotFound as error:
            msg = _("For %s support, please install one of the<br/> "
                    "following tools:<br/><br/>  %s")\
                        % (error.vcsname, ', '.join(error.tools))
            QMessageBox.critical(self, _("Error"),
                _("""<b>Unable to find external program.</b><br><br>%s""")
                    % to_text_string(msg))

    #----- Settings
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
            self.fsmodel.directoryLoaded.disconnect(self.restore_directory_state)

    def follow_directories_loaded(self, fname):
        """Follow directories loaded during startup"""
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
        """Restore all items expanded state"""
        if self.__expanded_state is not None:
            # In the old project explorer, the expanded state was a dictionnary:
            if isinstance(self.__expanded_state, list):
                self.fsmodel.directoryLoaded.connect(
                                                  self.restore_directory_state)
                self.fsmodel.directoryLoaded.connect(
                                                self.follow_directories_loaded)

    def filter_directories(self):
        """Filter the directories to show"""
        index = self.get_index('.spyproject')
        if index is not None:
            self.setRowHidden(index.row(), index.parent(), True)


class ProxyModel(QSortFilterProxyModel):
    """Proxy model: filters tree view"""
    def __init__(self, parent):
        super(ProxyModel, self).__init__(parent)
        self.root_path = None
        self.path_list = []
        self.setDynamicSortFilter(True)

    def setup_filter(self, root_path, path_list):
        """Setup proxy model filter parameters"""
        self.root_path = osp.normpath(to_text_string(root_path))
        self.path_list = [osp.normpath(to_text_string(p)) for p in path_list]
        self.invalidateFilter()

    def sort(self, column, order=Qt.AscendingOrder):
        """Reimplement Qt method"""
        self.sourceModel().sort(column, order)

    def filterAcceptsRow(self, row, parent_index):
        """Reimplement Qt method"""
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
        """Show tooltip with full path only for the root directory"""
        if role == Qt.ToolTipRole:
            root_dir = self.path_list[0].split(osp.sep)[-1]
            if index.data() == root_dir:
                return osp.join(self.root_path, root_dir)
        return QSortFilterProxyModel.data(self, index, role)

    def type(self, index):
        """Returns the type of file for the given index."""
        return self.sourceModel().type(self.mapToSource(index))


class FilteredDirView(DirView):
    """Filtered file/directory tree view"""
    def __init__(self, parent=None):
        super(FilteredDirView, self).__init__(parent)
        self.proxymodel = None
        self.setup_proxy_model()
        self.root_path = None

    #---- Model
    def setup_proxy_model(self):
        """Setup proxy model"""
        self.proxymodel = ProxyModel(self)
        self.proxymodel.setSourceModel(self.fsmodel)

    def install_model(self):
        """Install proxy model"""
        if self.root_path is not None:
            self.setModel(self.proxymodel)

    def set_root_path(self, root_path):
        """Set root path"""
        self.root_path = root_path
        self.install_model()
        index = self.fsmodel.setRootPath(root_path)
        self.proxymodel.setup_filter(self.root_path, [])
        self.setRootIndex(self.proxymodel.mapFromSource(index))

    def get_index(self, filename):
        """Return index associated with filename"""
        index = self.fsmodel.index(filename)
        if index.isValid() and index.model() is self.fsmodel:
            return self.proxymodel.mapFromSource(index)

    def set_folder_names(self, folder_names):
        """Set folder names"""
        assert self.root_path is not None
        path_list = [osp.join(self.root_path, dirname)
                     for dirname in folder_names]
        self.proxymodel.setup_filter(self.root_path, path_list)

    def get_filename(self, index):
        """Return filename from index"""
        if index:
            path = self.fsmodel.filePath(self.proxymodel.mapToSource(index))
            return osp.normpath(to_text_string(path))

    def setup_project_view(self):
        """Setup view for projects"""
        for i in [1, 2, 3]:
            self.hideColumn(i)
        self.setHeaderHidden(True)
        # Disable the view of .spyproject.
        self.filter_directories()


class ExplorerTreeWidget(DirView):
    """File/directory explorer tree widget
    show_cd_only: Show current directory only
    (True/False: enable/disable the option
     None: enable the option and do not allow the user to disable it)"""
    set_previous_enabled = Signal(bool)
    set_next_enabled = Signal(bool)

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

    def __init__(self, parent=None, show_cd_only=None):
        DirView.__init__(self, parent)

        self.history = []
        self.histindex = None

        self.show_cd_only = show_cd_only
        self.__original_root_index = None
        self.__last_folder = None

        self.menu = None
        self.common_actions = None

        # Enable drag events
        self.setDragEnabled(True)

    #---- Context menu
    def setup_common_actions(self):
        """Setup context menu common actions"""
        actions = super(ExplorerTreeWidget, self).setup_common_actions()
        if self.show_cd_only is None:
            # Enabling the 'show current directory only' option but do not
            # allow the user to disable it
            self.show_cd_only = True
        else:
            # Show current directory only
            cd_only_action = create_action(self,
                                           _("Show current directory only"),
                                           toggled=self.toggle_show_cd_only)
            cd_only_action.setChecked(self.show_cd_only)
            self.toggle_show_cd_only(self.show_cd_only)
            actions.append(cd_only_action)
        return actions

    @Slot(bool)
    def toggle_show_cd_only(self, checked):
        """Toggle show current directory only mode"""
        self.parent_widget.sig_option_changed.emit('show_cd_only', checked)
        self.show_cd_only = checked
        if checked:
            if self.__last_folder is not None:
                self.set_current_folder(self.__last_folder)
        elif self.__original_root_index is not None:
            self.setRootIndex(self.__original_root_index)

    #---- Refreshing widget
    def set_current_folder(self, folder):
        """Set current folder and return associated model index"""
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
        """Refresh widget
        force=False: won't refresh widget if path has not changed"""
        if new_path is None:
            new_path = getcwd_or_home()
        if force_current:
            index = self.set_current_folder(new_path)
            self.expand(index)
            self.setCurrentIndex(index)
        self.set_previous_enabled.emit(
                             self.histindex is not None and self.histindex > 0)
        self.set_next_enabled.emit(self.histindex is not None and \
                                   self.histindex < len(self.history)-1)
        # Disable the view of .spyproject.
        self.filter_directories()

    #---- Events
    def directory_clicked(self, dirname):
        """Directory was just clicked"""
        self.chdir(directory=dirname)

    #---- Files/Directories Actions
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
        """Update browse history"""
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
            if len(self.history) == 0 or \
               (self.history and self.history[-1] != directory):
                self.history.append(directory)
            self.histindex = len(self.history)-1
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
            QMessageBox.critical(self.parent_widget, "Error",
                                 _("You don't have the right permissions to "
                                   "open this directory"))
        except FileNotFoundError:
            # Handle renaming directories on the fly.
            # See spyder-ide/spyder#5183
            self.history.pop(self.histindex)


class ExplorerWidget(QWidget):
    """Explorer widget"""
    sig_option_changed = Signal(str, object)
    sig_open_file = Signal(str)
    open_dir = Signal(str)

    def __init__(self, parent=None, name_filters=['*.py', '*.pyw'],
                 show_all=False, show_hidden=False, show_cd_only=None,
                 single_click_to_open=False, file_associations={},
                 options_button=None, visible_columns=[0, 3]):
        QWidget.__init__(self, parent)

        # Widgets
        self.treewidget = ExplorerTreeWidget(self, show_cd_only=show_cd_only)
        button_previous = QToolButton(self)
        button_next = QToolButton(self)
        button_parent = QToolButton(self)
        self.button_menu = options_button or QToolButton(self)
        self.action_widgets = [button_previous, button_next, button_parent,
                               self.button_menu]

        # Actions
        previous_action = create_action(
            self, text=_("Previous"),
            icon=ima.icon('ArrowBack'),
            triggered=self.treewidget.go_to_previous_directory)
        next_action = create_action(
            self, text=_("Next"),
            icon=ima.icon('ArrowForward'),
            triggered=self.treewidget.go_to_next_directory)
        parent_action = create_action(
            self, text=_("Parent"),
            icon=ima.icon('ArrowUp'),
            triggered=self.treewidget.go_to_parent_directory)

        # Setup widgets
        self.treewidget.setup(
            name_filters=name_filters,
            show_all=show_all,
            show_hidden=show_hidden,
            single_click_to_open=single_click_to_open,
            file_associations=file_associations,
        )

        # Setup of actions
        ismac = sys.platform == 'darwin'
        kind = _('Display kind') if ismac else _('Display type')
        self.display_column_actions = []
        for idx, text in enumerate([_('Display size'), kind,
                                   _('Display date modified')]):
            col = idx + 1
            action = create_action(
                self, text=text,
                toggled=lambda x, c=col: self.treewidget.toggle_column(c))

            if col in visible_columns:
                self.treewidget.showColumn(col)
            else:
                self.treewidget.hideColumn(col)

            action.blockSignals(True)
            action.setChecked(not self.treewidget.isColumnHidden(col))
            action.blockSignals(False)

            self.display_column_actions.append(action)

        self.treewidget.chdir(getcwd_or_home())
        self.treewidget.common_actions = (
            self.treewidget.common_actions[:-1] + self.display_column_actions
            + [MENU_SEPARATOR] + self.treewidget.common_actions[-1:])

        button_previous.setDefaultAction(previous_action)
        previous_action.setEnabled(False)

        button_next.setDefaultAction(next_action)
        next_action.setEnabled(False)

        button_parent.setDefaultAction(parent_action)

        for widget in self.action_widgets:
            widget.setAutoRaise(True)
            widget.setIconSize(QSize(16, 16))

        # Layouts
        blayout = QHBoxLayout()
        blayout.addWidget(button_previous)
        blayout.addWidget(button_next)
        blayout.addWidget(button_parent)
        blayout.addStretch()
        blayout.addWidget(self.button_menu)

        layout = create_plugin_layout(blayout, self.treewidget)
        self.setLayout(layout)

        # Signals and slots
        self.treewidget.set_previous_enabled.connect(
                                               previous_action.setEnabled)
        self.treewidget.set_next_enabled.connect(next_action.setEnabled)
        self.sig_option_changed.connect(self.refresh_actions)

    def refresh_actions(self, option, value):
        """Refresh column visibility actions."""
        if option == 'visible_columns':
            for col in range(1, 4):
                is_hidden = self.treewidget.isColumnHidden(col)
                action = self.display_column_actions[col - 1]
                action.blockSignals(True)
                action.setChecked(not is_hidden)
                action.blockSignals(False)


#==============================================================================
# Tests
#==============================================================================
class FileExplorerTest(QWidget):
    def __init__(self, directory=None, file_associations={}):
        super(FileExplorerTest, self).__init__()

        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))

        self.explorer = ExplorerWidget(self, show_cd_only=None,
                                       file_associations=file_associations)
        self.label_dir = QLabel("<b>Open dir:</b>")
        self.label_file = QLabel("<b>Open file:</b>")
        self.label1 = QLabel()
        self.label_dir.setAlignment(Qt.AlignRight)
        self.label2 = QLabel()
        self.label_option = QLabel("<b>Option changed:</b>")
        self.label3 = QLabel()

        # Setup
        self.explorer.treewidget.set_current_folder(self.directory)
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
        self.explorer.open_dir.connect(self.label2.setText)
        self.explorer.open_dir.connect(
                                lambda: self.explorer.treewidget.refresh('..'))
        self.explorer.sig_open_file.connect(self.label1.setText)
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
