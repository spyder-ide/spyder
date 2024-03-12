# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2019- Spyder Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. Licensed under the terms of the MIT License;
# see NOTICE.txt in the Spyder root directory for details
# -----------------------------------------------------------------------------

# Standard library imports
import copy
import datetime
import functools
import operator
from typing import Any, Callable, Optional

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import QDateTime, QModelIndex, Qt, Signal
from qtpy.QtWidgets import (
    QAbstractItemDelegate, QDateEdit, QDateTimeEdit, QItemDelegate, QLineEdit,
    QMessageBox, QTableView)
from spyder_kernels.utils.lazymodules import (
    FakeObject, numpy as np, pandas as pd, PIL)
from spyder_kernels.utils.nsview import (display_to_value, is_editable_type,
                                         is_known_type)

# Local imports
from spyder.api.config.fonts import SpyderFontsMixin, SpyderFontType
from spyder.config.base import _, is_conda_based_app
from spyder.py3compat import is_binary_string, is_text_string, to_text_string
from spyder.plugins.variableexplorer.widgets.arrayeditor import ArrayEditor
from spyder.plugins.variableexplorer.widgets.dataframeeditor import (
    DataFrameEditor)
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor


LARGE_COLLECTION = 1e5
LARGE_ARRAY = 5e6


class CollectionsDelegate(QItemDelegate, SpyderFontsMixin):
    """CollectionsEditor Item Delegate"""
    sig_free_memory_requested = Signal()
    sig_editor_creation_started = Signal()
    sig_editor_shown = Signal()

    def __init__(
        self,
        parent=None,
        namespacebrowser=None,
        data_function: Optional[Callable[[], Any]] = None
    ):
        QItemDelegate.__init__(self, parent)
        self.namespacebrowser = namespacebrowser
        self.data_function = data_function
        self._editors = {}  # keep references on opened editors

    def get_value(self, index):
        if index.isValid():
            return index.model().get_value(index)

    def set_value(self, index, value):
        if index.isValid():
            index.model().set_value(index, value)

    def make_data_function(
        self,
        index: QModelIndex
    ) -> Optional[Callable[[], Any]]:
        """
        Construct function which returns current value of data.

        This is used to refresh editors created from this piece of data.
        For instance, if `self` is the delegate for an editor that displays
        the dict `xxx` and the user opens another editor for `xxx["aaa"]`,
        then to refresh the data of the second editor, the nested function
        `datafun` first gets the refreshed data for `xxx` and then gets the
        item with key "aaa".

        Parameters
        ----------
        index : QModelIndex
            Index of item whose current value is to be returned by the
            function constructed here.

        Returns
        -------
        Optional[Callable[[], Any]]
            Function which returns the current value of the data, or None if
            such a function cannot be constructed.
        """
        if self.data_function is None:
            return None
        key = index.model().keys[index.row()]

        def datafun():
            data = self.data_function()
            if isinstance(data, (tuple, list, dict, set)):
                return data[key]

            try:
                return getattr(data, key)
            except (NotImplementedError, AttributeError,
                    TypeError, ValueError):
                return None

        return datafun

    def show_warning(self, index):
        """
        Decide if showing a warning when the user is trying to view
        a big variable associated to a Tablemodel index.

        This avoids getting the variables' value to know its
        size and type, using instead those already computed by
        the TableModel.

        The problem is when a variable is too big, it can take a
        lot of time just to get its value.
        """
        val_type = index.sibling(index.row(), 1).data()
        val_size = index.sibling(index.row(), 2).data()

        if val_type in ['list', 'set', 'tuple', 'dict']:
            if int(val_size) > LARGE_COLLECTION:
                return True
        elif (val_type in ['DataFrame', 'Series'] or 'Array' in val_type or
                'Index' in val_type):
            # Avoid errors for user declared types that contain words like
            # the ones we're looking for above
            try:
                # From https://blender.stackexchange.com/a/131849
                shape = [int(s) for s in val_size.strip("()").split(",") if s]
                size = functools.reduce(operator.mul, shape)
                if size > LARGE_ARRAY:
                    return True
            except Exception:
                pass

        return False

    def createEditor(self, parent, option, index, object_explorer=False):
        """Overriding method createEditor"""
        val_type = index.sibling(index.row(), 1).data()
        self.sig_editor_creation_started.emit()
        if index.column() < 3:
            return None
        if self.show_warning(index):
            answer = QMessageBox.warning(
                self.parent(), _("Warning"),
                _("Opening this variable can be slow\n\n"
                  "Do you want to continue anyway?"),
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                self.sig_editor_shown.emit()
                return None
        try:
            value = self.get_value(index)
            if value is None:
                return None
        except ImportError as msg:
            self.sig_editor_shown.emit()
            module = str(msg).split("'")[1]
            if module in ['pandas', 'numpy']:
                if module == 'numpy':
                    val_type = 'array'
                else:
                    val_type = 'dataframe or series'
                message = _("Spyder is unable to show the {val_type} object "
                            "you're trying to view because <tt>{module}</tt> "
                            "is missing. Please install that package in your "
                            "Spyder environment to fix this problem.")
                QMessageBox.critical(
                    self.parent(), _("Error"),
                    message.format(val_type=val_type, module=module))
                return
            else:
                if is_conda_based_app():
                    message = _("Spyder is unable to show the variable you're"
                                " trying to view because the module "
                                "<tt>{module}</tt> is not supported "
                                "by Spyder's standalone application.<br>")
                else:
                    message = _("Spyder is unable to show the variable you're"
                                " trying to view because the module "
                                "<tt>{module}</tt> is not found in your "
                                "Spyder environment. Please install this "
                                "package in this environment.<br>")
                QMessageBox.critical(self.parent(), _("Error"),
                                     message.format(module=module))
                return
        except Exception as msg:
            self.sig_editor_shown.emit()
            QMessageBox.critical(
                self.parent(), _("Error"),
                _("Spyder was unable to retrieve the value of "
                  "this variable from the console.<br><br>"
                  "The error message was:<br>"
                  "%s") % to_text_string(msg))
            return

        key = index.model().get_key(index)
        readonly = (isinstance(value, (tuple, set)) or self.parent().readonly
                    or not is_known_type(value))

        # We can't edit Numpy void objects because they could be anything, so
        # this might cause a crash.
        # Fixes spyder-ide/spyder#10603
        if isinstance(value, np.void):
            self.sig_editor_shown.emit()
            return None
        # CollectionsEditor for a list, tuple, dict, etc.
        elif isinstance(value, (list, set, tuple, dict)) and not object_explorer:
            from spyder.widgets.collectionseditor import CollectionsEditor
            editor = CollectionsEditor(
                parent=parent,
                namespacebrowser=self.namespacebrowser,
                data_function=self.make_data_function(index)
            )
            editor.setup(value, key, icon=self.parent().windowIcon(),
                         readonly=readonly)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for a Numpy array
        elif (isinstance(value, (np.ndarray, np.ma.MaskedArray)) and
                np.ndarray is not FakeObject and not object_explorer):
            # We need to leave this import here for tests to pass.
            from .arrayeditor import ArrayEditor
            editor = ArrayEditor(
                parent=parent,
                data_function=self.make_data_function(index)
            )
            if not editor.setup_and_check(value, title=key, readonly=readonly):
                self.sig_editor_shown.emit()
                return
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for an images
        elif (isinstance(value, PIL.Image.Image) and
                np.ndarray is not FakeObject and
                PIL.Image is not FakeObject and
                not object_explorer):
            # Sometimes the ArrayEditor import above is not seen (don't know
            # why), so we need to reimport it here.
            # Fixes spyder-ide/spyder#16731
            from .arrayeditor import ArrayEditor
            arr = np.array(value)
            editor = ArrayEditor(parent=parent)
            if not editor.setup_and_check(arr, title=key, readonly=readonly):
                self.sig_editor_shown.emit()
                return
            conv_func = lambda arr: PIL.Image.fromarray(arr, mode=value.mode)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly,
                                            conv=conv_func))
            return None
        # DataFrameEditor for a pandas dataframe, series or index
        elif (isinstance(value, (pd.DataFrame, pd.Index, pd.Series))
                and pd.DataFrame is not FakeObject and not object_explorer):
            # We need to leave this import here for tests to pass.
            from .dataframeeditor import DataFrameEditor
            editor = DataFrameEditor(
                parent=parent,
                data_function=self.make_data_function(index)
            )
            if not editor.setup_and_check(value, title=key):
                self.sig_editor_shown.emit()
                return
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # QDateEdit and QDateTimeEdit for a dates or datetime respectively
        elif isinstance(value, datetime.date) and not object_explorer:
            if readonly:
                self.sig_editor_shown.emit()
                return None
            else:
                if isinstance(value, datetime.datetime):
                    editor = QDateTimeEdit(value, parent=parent)
                    # Needed to handle NaT values
                    # See spyder-ide/spyder#8329
                    try:
                        value.time()
                    except ValueError:
                        self.sig_editor_shown.emit()
                        return None
                else:
                    editor = QDateEdit(value, parent=parent)
                editor.setCalendarPopup(True)
                editor.setFont(
                    self.get_font(SpyderFontType.MonospaceInterface)
                )
                self.sig_editor_shown.emit()
                return editor
        # TextEditor for a long string
        elif is_text_string(value) and len(value) > 40 and not object_explorer:
            te = TextEditor(None, parent=parent)
            if te.setup_and_check(value):
                editor = TextEditor(value, key,
                                    readonly=readonly, parent=parent)
                self.create_dialog(editor, dict(model=index.model(),
                                                editor=editor, key=key,
                                                readonly=readonly))
            return None
        # QLineEdit for an individual value (int, float, short string, etc)
        elif is_editable_type(value) and not object_explorer:
            if readonly:
                self.sig_editor_shown.emit()
                return None
            else:
                editor = QLineEdit(parent=parent)
                editor.setFont(
                    self.get_font(SpyderFontType.MonospaceInterface)
                )
                editor.setAlignment(Qt.AlignLeft)
                # This is making Spyder crash because the QLineEdit that it's
                # been modified is removed and a new one is created after
                # evaluation. So the object on which this method is trying to
                # act doesn't exist anymore.
                # editor.returnPressed.connect(self.commitAndCloseEditor)
                self.sig_editor_shown.emit()
                return editor
        # ObjectExplorer for an arbitrary Python object
        else:
            from spyder.plugins.variableexplorer.widgets.objectexplorer \
                import ObjectExplorer
            editor = ObjectExplorer(
                value,
                name=key,
                parent=parent,
                namespacebrowser=self.namespacebrowser,
                data_function=self.make_data_function(index),
                readonly=readonly)
            self.create_dialog(editor, dict(model=index.model(),
                                            editor=editor,
                                            key=key, readonly=readonly))
            return None

    def create_dialog(self, editor, data):
        self._editors[id(editor)] = data
        editor.accepted.connect(
                     lambda eid=id(editor): self.editor_accepted(eid))
        editor.rejected.connect(
                     lambda eid=id(editor): self.editor_rejected(eid))
        self.sig_editor_shown.emit()
        editor.show()

    def editor_accepted(self, editor_id):
        data = self._editors[editor_id]
        if not data['readonly']:
            index = data['model'].get_index_from_key(data['key'])
            value = data['editor'].get_value()
            conv_func = data.get('conv', lambda v: v)
            self.set_value(index, conv_func(value))
        # This is needed to avoid the problem reported on
        # spyder-ide/spyder#8557.
        try:
            self._editors.pop(editor_id)
        except KeyError:
            pass
        self.free_memory()

    def editor_rejected(self, editor_id):
        # This is needed to avoid the problem reported on
        # spyder-ide/spyder#8557.
        try:
            self._editors.pop(editor_id)
        except KeyError:
            pass
        self.free_memory()

    def free_memory(self):
        """Free memory after closing an editor."""
        try:
            self.sig_free_memory_requested.emit()
        except RuntimeError:
            pass

    def commitAndCloseEditor(self):
        """Overriding method commitAndCloseEditor"""
        editor = self.sender()
        # Avoid a segfault with PyQt5. Variable value won't be changed
        # but at least Spyder won't crash. It seems generated by a bug in sip.
        try:
            self.commitData.emit(editor)
        except AttributeError:
            pass
        self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)

    def setEditorData(self, editor, index):
        """
        Overriding method setEditorData
        Model --> Editor
        """
        value = self.get_value(index)
        if isinstance(editor, QLineEdit):
            if is_binary_string(value):
                try:
                    value = to_text_string(value, 'utf8')
                except Exception:
                    pass
            if not is_text_string(value):
                value = repr(value)
            editor.setText(value)
        elif isinstance(editor, QDateEdit):
            editor.setDate(value)
        elif isinstance(editor, QDateTimeEdit):
            editor.setDateTime(QDateTime(value.date(), value.time()))

    def setModelData(self, editor, model, index):
        """
        Overriding method setModelData
        Editor --> Model
        """
        if ((hasattr(model, "sourceModel")
                and not hasattr(model.sourceModel(), "set_value"))
                or not hasattr(model, "set_value")):
            # Read-only mode
            return

        if isinstance(editor, QLineEdit):
            value = editor.text()
            try:
                value = display_to_value(to_qvariant(value),
                                         self.get_value(index),
                                         ignore_errors=False)
            except Exception as msg:
                QMessageBox.critical(editor, _("Edit item"),
                                     _("<b>Unable to assign data to item.</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % str(msg))
                return
        elif isinstance(editor, QDateEdit):
            qdate = editor.date()
            value = datetime.date(qdate.year(), qdate.month(), qdate.day())
        elif isinstance(editor, QDateTimeEdit):
            qdatetime = editor.dateTime()
            qdate = qdatetime.date()
            qtime = qdatetime.time()
            # datetime uses microseconds, QDateTime returns milliseconds
            value = datetime.datetime(qdate.year(), qdate.month(), qdate.day(),
                                      qtime.hour(), qtime.minute(),
                                      qtime.second(), qtime.msec()*1000)
        else:
            # Should not happen...
            raise RuntimeError("Unsupported editor widget")
        self.set_value(index, value)

    def updateEditorGeometry(self, editor, option, index):
        """
        Overriding method updateEditorGeometry.

        This is necessary to set the correct position of the QLineEdit
        editor since option.rect doesn't have values -> QRect() and
        makes the editor to be invisible (i.e. it has 0 as x, y, width
        and height) when doing double click over a cell.
        See spyder-ide/spyder#9945
        """
        table_view = editor.parent().parent()
        if isinstance(table_view, QTableView):
            row = index.row()
            column = index.column()
            y0 = table_view.rowViewportPosition(row)
            x0 = table_view.columnViewportPosition(column)
            width = table_view.columnWidth(column)
            height = table_view.rowHeight(row)
            editor.setGeometry(x0, y0, width, height)
        else:
            super(CollectionsDelegate, self).updateEditorGeometry(
                editor, option, index)


class ToggleColumnDelegate(CollectionsDelegate):
    """ToggleColumn Item Delegate"""

    def __init__(self, parent=None, namespacebrowser=None,
                 data_function: Optional[Callable[[], Any]] = None):
        CollectionsDelegate.__init__(
            self, parent, namespacebrowser, data_function
        )
        self.current_index = None
        self.old_obj = None

    def restore_object(self):
        """Discart changes made to the current object in edition."""
        if self.current_index and self.old_obj is not None:
            index = self.current_index
            index.model().treeItem(index).obj = self.old_obj

    def get_value(self, index):
        """Get object value in index."""
        if index.isValid():
            value = index.model().treeItem(index).obj
            return value

    def set_value(self, index, value):
        if index.isValid():
            index.model().set_value(index, value)

    def make_data_function(
        self,
        index: QModelIndex
    ) -> Optional[Callable[[], Any]]:
        """
        Construct function which returns current value of data.

        This is used to refresh editors created from this piece of data.
        For instance, if `self` is the delegate for an editor displays the
        object `obj` and the user opens another editor for `obj.xxx.yyy`,
        then to refresh the data of the second editor, the nested function
        `datafun` first gets the refreshed data for `obj` and then gets the
        `xxx` attribute and then the `yyy` attribute.

        Parameters
        ----------
        index : QModelIndex
            Index of item whose current value is to be returned by the
            function constructed here.

        Returns
        -------
        Optional[Callable[[], Any]]
            Function which returns the current value of the data, or None if
            such a function cannot be constructed.
        """
        if self.data_function is None:
            return None

        obj_path = index.model().get_key(index).obj_path
        path_elements = obj_path.split('.')
        del path_elements[0]  # first entry is variable name

        def datafun():
            data = self.data_function()
            try:
                for attribute_name in path_elements:
                    data = getattr(data, attribute_name)
                return data
            except (NotImplementedError, AttributeError,
                    TypeError, ValueError):
                return None

        return datafun

    def createEditor(self, parent, option, index):
        """Overriding method createEditor"""
        if self.show_warning(index):
            answer = QMessageBox.warning(
                self.parent(), _("Warning"),
                _("Opening this variable can be slow\n\n"
                  "Do you want to continue anyway?"),
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return None
        try:
            value = self.get_value(index)
            try:
                self.old_obj = value.copy()
            except AttributeError:
                self.old_obj = copy.deepcopy(value)
            if value is None:
                return None
        except Exception as msg:
            QMessageBox.critical(
                self.parent(), _("Error"),
                _("Spyder was unable to retrieve the value of "
                  "this variable from the console.<br><br>"
                  "The error message was:<br>"
                  "<i>%s</i>") % to_text_string(msg))
            return
        self.current_index = index

        key = index.model().get_key(index).obj_name
        readonly = (isinstance(value, (tuple, set)) or self.parent().readonly
                    or not is_known_type(value))

        # CollectionsEditor for a list, tuple, dict, etc.
        if isinstance(value, (list, set, tuple, dict)):
            from spyder.widgets.collectionseditor import CollectionsEditor
            editor = CollectionsEditor(
                parent=parent,
                namespacebrowser=self.namespacebrowser,
                data_function=self.make_data_function(index)
            )
            editor.setup(value, key, icon=self.parent().windowIcon(),
                         readonly=readonly)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for a Numpy array
        elif (isinstance(value, (np.ndarray, np.ma.MaskedArray)) and
                np.ndarray is not FakeObject):
            editor = ArrayEditor(
                parent=parent,
                data_function=self.make_data_function(index)
            )
            if not editor.setup_and_check(value, title=key, readonly=readonly):
                return
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for an images
        elif (isinstance(value, PIL.Image.Image) and
                np.ndarray is not FakeObject and PIL.Image is not FakeObject):
            arr = np.array(value)
            editor = ArrayEditor(parent=parent)
            if not editor.setup_and_check(arr, title=key, readonly=readonly):
                return
            conv_func = lambda arr: PIL.Image.fromarray(arr, mode=value.mode)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly,
                                            conv=conv_func))
            return None
        # DataFrameEditor for a pandas dataframe, series or index
        elif (isinstance(value, (pd.DataFrame, pd.Index, pd.Series))
                and pd.DataFrame is not FakeObject):
            editor = DataFrameEditor(
                parent=parent,
                data_function=self.make_data_function(index)
            )
            if not editor.setup_and_check(value, title=key):
                return
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # QDateEdit and QDateTimeEdit for a dates or datetime respectively
        elif isinstance(value, datetime.date):
            if readonly:
                return None
            else:
                if isinstance(value, datetime.datetime):
                    editor = QDateTimeEdit(value, parent=parent)
                else:
                    editor = QDateEdit(value, parent=parent)
                editor.setCalendarPopup(True)
                editor.setFont(
                    self.get_font(SpyderFontType.MonospaceInterface)
                )
                return editor
        # TextEditor for a long string
        elif is_text_string(value) and len(value) > 40:
            te = TextEditor(None, parent=parent)
            if te.setup_and_check(value):
                editor = TextEditor(value, key,
                                    readonly=readonly, parent=parent)
                self.create_dialog(editor, dict(model=index.model(),
                                                editor=editor, key=key,
                                                readonly=readonly))
            return None
        # QLineEdit for an individual value (int, float, short string, etc)
        elif is_editable_type(value):
            if readonly:
                return None
            else:
                editor = QLineEdit(parent=parent)
                editor.setFont(
                    self.get_font(SpyderFontType.MonospaceInterface)
                )
                editor.setAlignment(Qt.AlignLeft)
                # This is making Spyder crash because the QLineEdit that it's
                # been modified is removed and a new one is created after
                # evaluation. So the object on which this method is trying to
                # act doesn't exist anymore.
                # editor.returnPressed.connect(self.commitAndCloseEditor)
                return editor
        # An arbitrary Python object.
        # Since we are already in the Object Explorer no editor is needed
        else:
            return None

    def editor_accepted(self, editor_id):
        """Actions to execute when the editor has been closed."""
        data = self._editors[editor_id]
        if not data['readonly'] and self.current_index:
            index = self.current_index
            value = data['editor'].get_value()
            conv_func = data.get('conv', lambda v: v)
            self.set_value(index, conv_func(value))
        # This is needed to avoid the problem reported on
        # spyder-ide/spyder#8557.
        try:
            self._editors.pop(editor_id)
        except KeyError:
            pass
        self.free_memory()

    def editor_rejected(self, editor_id):
        """Actions to do when the editor was rejected."""
        self.restore_object()
        super(ToggleColumnDelegate, self).editor_rejected(editor_id)
