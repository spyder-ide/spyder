# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer Tree."""

# Standard library imports
import os.path as osp
import shutil

# Third party imports
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QAbstractItemView, QHeaderView, QMessageBox

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.plugins.explorer.widgets.explorer import FilteredDirView
from spyder.utils import misc


# Localization
_ = get_translation("spyder")


# TODO: Inheritance may change if explorer is merged
class ExplorerTreeWidget(FilteredDirView, SpyderWidgetMixin):
    """Explorer tree widget."""

    DEFAULT_OPTIONS = {
        'horizontal_scrollbar': True,  # show_hscrollbar
    }

    # --- Signals
    sig_delete_project_requested = Signal()
    """
    FIXME
    """

    sig_externally_opened = Signal(str)

    sig_create_module_requested = Signal(str)

    def __init__(self, parent, options=DEFAULT_OPTIONS):
        super().__init__(parent)

        self.change_options(options)

        # Widget setup
        self.setDragEnabled(True)
        self.setDragDropMode(FilteredDirView.DragDrop)
        self.setSelectionMode(FilteredDirView.ExtendedSelection)

    # --- SpyderWidgetMixin API
    # ---------------------------------------------------------
    def setup(self, options=DEFAULT_OPTIONS):
        actions = FilteredDirView.setup_common_actions(self)

        # Toggle horizontal scrollbar
        hscrollbar_action = self.create_action(
            'toggle_horizontal_scrollbar_action',
            text=_("Show horizontal scrollbar"),
            toggled=lambda value:
                self.set_option('horizontal_scrollbar', value),
            initial=self.get_option('horizontal_scrollbar'),
        )

        # FIXME: Add to a menu?

        return actions + [hscrollbar_action]

    def on_option_update(self, option, value):
        if option == 'horizontal_scrollbar':
            header = self.header()
            header.setStretchLastSection(not value)
            header.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

            try:
                header.setSectionResizeMode(QHeaderView.ResizeToContents)
            except Exception:
                # Support for qtpy<1.2.0
                header.setResizeMode(QHeaderView.ResizeToContents)

    def update_actions(self):
        pass

    # --- Qt Overrides
    # ------------------------------------------------------------------------
    def dragMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index:
            dst = self.get_filename(index)
            if osp.isdir(dst):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.ignore()
        action = event.dropAction()
        if action not in (Qt.MoveAction, Qt.CopyAction):
            return

        # QTreeView must not remove the source items even in MoveAction mode:
        # event.setDropAction(Qt.CopyAction)
        dst = self.get_filename(self.indexAt(event.pos()))
        yes_to_all, no_to_all = None, None
        src_list = [str(url.toString())
                    for url in event.mimeData().urls()]
        if len(src_list) > 1:
            buttons = (QMessageBox.Yes | QMessageBox.YesToAll
                       | QMessageBox.No | QMessageBox.NoToAll
                       | QMessageBox.Cancel)
        else:
            buttons = QMessageBox.Yes | QMessageBox.No

        for src in src_list:
            if src == dst:
                continue

            dst_fname = osp.join(dst, osp.basename(src))
            if osp.exists(dst_fname):
                if yes_to_all is not None or no_to_all is not None:
                    if no_to_all:
                        continue
                elif osp.isfile(dst_fname):
                    answer = QMessageBox.warning(
                        self,
                        _('Project explorer'),
                        _('File <b>%s</b> already exists.<br>'
                          'Do you want to overwrite it?') % dst_fname,
                        buttons,
                    )

                    if answer == QMessageBox.No:
                        continue
                    elif answer == QMessageBox.Cancel:
                        break
                    elif answer == QMessageBox.YesToAll:
                        yes_to_all = True
                    elif answer == QMessageBox.NoToAll:
                        no_to_all = True
                        continue
                else:
                    QMessageBox.critical(
                        self,
                        _('Project explorer'),
                        _('Folder <b>%s</b> already exists.'
                          ) % dst_fname,
                        QMessageBox.Ok,
                    )
                    event.setDropAction(Qt.CopyAction)
                    return
            try:
                if action == Qt.CopyAction:
                    if osp.isfile(src):
                        shutil.copy(src, dst)
                    else:
                        shutil.copytree(src, dst)
                else:
                    if osp.isfile(src):
                        misc.move_file(src, dst)
                    else:
                        shutil.move(src, dst)

                    self.parent_widget.removed.emit(src)

            except EnvironmentError as error:
                if action == Qt.CopyAction:
                    action_str = _('copy')
                else:
                    action_str = _('move')

                QMessageBox.critical(
                    self,
                    _("Project Explorer"),
                    _("<b>Unable to %s <i>%s</i></b>"
                      "<br><br>Error message:<br>%s")
                      % (action_str, src, str(error)),
                )

    # --- Public API
    # ---------------------------------------------------------
    @Slot()
    def delete(self, fnames=None):
        """
        Delete files.

        Parameters
        ----------
        fnames: FIXME
            FIXME
        """
        if fnames is None:
            fnames = self.get_selected_filenames()

        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            if fname == self.proxymodel.path_list[0]:
                self.sig_delete_project.emit()
            else:
                yes_to_all = self.delete_file(fname, multiple, yes_to_all)
                if yes_to_all is not None and not yes_to_all:
                    # Canceled
                    break
