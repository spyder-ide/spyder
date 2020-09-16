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

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import QDateTime, Qt, Signal, Slot
from qtpy.QtWidgets import (QAbstractItemDelegate, QDateEdit, QDateTimeEdit,
                            QItemDelegate, QLineEdit, QMessageBox, QTableView)

# Local imports
from spyder.config.base import _
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.config.gui import get_font
from spyder_kernels.utils.nsview import (
    array, DataFrame, Index, display_to_value, FakeObject,
    Image, is_editable_type, is_known_type, MaskedArray, ndarray, Series)
from spyder.py3compat import is_binary_string, is_text_string, to_text_string
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor
from spyder.plugins.variableexplorer.widgets.objectexplorer.attribute_model \
    import safe_tio_call

if ndarray is not FakeObject:
    from spyder.plugins.variableexplorer.widgets.arrayeditor import (
            ArrayEditor)

if DataFrame is not FakeObject:
    from spyder.plugins.variableexplorer.widgets.dataframeeditor import (
            DataFrameEditor)


LARGE_COLLECTION = 1e5
LARGE_ARRAY = 5e6


class CollectionsDelegate(QItemDelegate):
    """CollectionsEditor Item Delegate"""
    sig_free_memory = Signal()
    sig_open_editor = Signal()
    sig_editor_shown = Signal()

    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)
        self._editors = {}  # keep references on opened editors

    def get_value(self, index):
        if index.isValid():
            return index.model().get_value(index)

    def set_value(self, index, value):
        if index.isValid():
            index.model().set_value(index, value)

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
        self.sig_open_editor.emit()
        if index.column() < 3:
            return None
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
            if value is None:
                return None
        except ImportError as msg:
            self.sig_editor_shown.emit()
            module = str(msg).split("'")[1]
            if module in ['pandas', 'numpy']:
                if module == 'numpy':
                    val_type = 'array'
                else:
                    val_type = 'dataframe, series'
                QMessageBox.critical(
                    self.parent(), _("Error"),
                    _("Spyder is unable to show the {val_type} or object "
                      "you're trying to view because <tt>{module}</tt> was "
                      "not installed alongside Spyder. Please install "
                      "this package in your Spyder environment."
                      "<br>").format(val_type=val_type, module=module))
                return
            else:
                QMessageBox.critical(
                    self.parent(), _("Error"),
                    _("Spyder is unable to show the variable you're "
                      "trying to view because the module "
                      "<tt>{module}</tt> was not found in your  "
                      "Spyder environment. Please install "
                      "this package in your Spyder environment."
                      "<br>").format(module=module))
                return
        except Exception as msg:
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
        # CollectionsEditor for a list, tuple, dict, etc.
        if isinstance(value, (list, set, tuple, dict)) and not object_explorer:
            from spyder.widgets.collectionseditor import CollectionsEditor
            editor = CollectionsEditor(parent=parent)
            editor.setup(value, key, icon=self.parent().windowIcon(),
                         readonly=readonly)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for a Numpy array
        elif (isinstance(value, (ndarray, MaskedArray)) and
                ndarray is not FakeObject and not object_explorer):
            editor = ArrayEditor(parent=parent)
            if not editor.setup_and_check(value, title=key, readonly=readonly):
                return
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for an images
        elif (isinstance(value, Image) and ndarray is not FakeObject and
                Image is not FakeObject and not object_explorer):
            arr = array(value)
            editor = ArrayEditor(parent=parent)
            if not editor.setup_and_check(arr, title=key, readonly=readonly):
                return
            conv_func = lambda arr: Image.fromarray(arr, mode=value.mode)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly,
                                            conv=conv_func))
            return None
        # DataFrameEditor for a pandas dataframe, series or index
        elif (isinstance(value, (DataFrame, Index, Series))
                and DataFrame is not FakeObject and not object_explorer):
            editor = DataFrameEditor(parent=parent)
            if not editor.setup_and_check(value, title=key):
                return
            editor.dataModel.set_format(index.model().dataframe_format)
            editor.sig_option_changed.connect(self.change_option)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # QDateEdit and QDateTimeEdit for a dates or datetime respectively
        elif isinstance(value, datetime.date) and not object_explorer:
            # Needed to handle NaT values
            # See spyder-ide/spyder#8329
            try:
                value.time()
            except ValueError:
                self.sig_editor_shown.emit()
                return None
            if readonly:
                self.sig_editor_shown.emit()
                return None
            else:
                if isinstance(value, datetime.datetime):
                    editor = QDateTimeEdit(value, parent=parent)
                else:
                    editor = QDateEdit(value, parent=parent)
                editor.setCalendarPopup(True)
                editor.setFont(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
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
                editor.setFont(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
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
            show_callable_attributes = index.model().show_callable_attributes
            show_special_attributes = index.model().show_special_attributes
            dataframe_format = index.model().dataframe_format

            if show_callable_attributes is None:
                show_callable_attributes = False
            if show_special_attributes is None:
                show_special_attributes = False

            from spyder.plugins.variableexplorer.widgets.objectexplorer \
                import ObjectExplorer
            editor = ObjectExplorer(
                value,
                name=key,
                parent=parent,
                show_callable_attributes=show_callable_attributes,
                show_special_attributes=show_special_attributes,
                dataframe_format=dataframe_format,
                readonly=readonly)
            editor.sig_option_changed.connect(self.change_option)
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

    @Slot(str, object)
    def change_option(self, option_name, new_value):
        """
        Change configuration option.

        This function is called when a `sig_option_changed` signal is received.
        At the moment, this signal can only come from a DataFrameEditor
        or an ObjectExplorer.
        """
        if option_name == 'dataframe_format':
            self.parent().set_dataframe_format(new_value)
        elif option_name == 'show_callable_attributes':
            self.parent().toggle_show_callable_attributes(new_value)
        elif option_name == 'show_special_attributes':
            self.parent().toggle_show_special_attributes(new_value)

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
            self.sig_free_memory.emit()
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
                raise
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
    def __init__(self, parent=None):
        CollectionsDelegate.__init__(self, parent)
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
            editor = CollectionsEditor(parent=parent)
            editor.setup(value, key, icon=self.parent().windowIcon(),
                         readonly=readonly)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for a Numpy array
        elif (isinstance(value, (ndarray, MaskedArray)) and
                ndarray is not FakeObject):
            editor = ArrayEditor(parent=parent)
            if not editor.setup_and_check(value, title=key, readonly=readonly):
                return
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly))
            return None
        # ArrayEditor for an images
        elif (isinstance(value, Image) and ndarray is not FakeObject and
                Image is not FakeObject):
            arr = array(value)
            editor = ArrayEditor(parent=parent)
            if not editor.setup_and_check(arr, title=key, readonly=readonly):
                return
            conv_func = lambda arr: Image.fromarray(arr, mode=value.mode)
            self.create_dialog(editor, dict(model=index.model(), editor=editor,
                                            key=key, readonly=readonly,
                                            conv=conv_func))
            return None
        # DataFrameEditor for a pandas dataframe, series or index
        elif (isinstance(value, (DataFrame, Index, Series))
                and DataFrame is not FakeObject):
            editor = DataFrameEditor(parent=parent)
            if not editor.setup_and_check(value, title=key):
                return
            editor.dataModel.set_format(index.model().dataframe_format)
            editor.sig_option_changed.connect(self.change_option)
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
                editor.setFont(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
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
                editor.setFont(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
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
