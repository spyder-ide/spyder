# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Customized combobox widgets."""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201


# Standard library imports
import glob
import os
import os.path as osp

# Third party imports
import qdarkstyle
from qtpy.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QComboBox, QCompleter, QLineEdit,
                            QSizePolicy, QToolTip)

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface
from spyder.py3compat import to_text_string
from spyder.widgets.helperwidgets import IconLineEdit


class BaseComboBox(QComboBox):
    """Editable combo box base class"""
    valid = Signal(bool, bool)
    sig_tab_pressed = Signal(bool)

    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.setEditable(True)
        self.setCompleter(QCompleter(self))
        self.selected_text = self.currentText()

    # --- Qt overrides
    def event(self, event):
        """Qt Override.

        Filter tab keys and process double tab keys.
        """
        if (event.type() == QEvent.KeyPress) and (event.key() == Qt.Key_Tab):
            self.sig_tab_pressed.emit(True)
            return True
        return QComboBox.event(self, event)

    def keyPressEvent(self, event):
        """Qt Override.

        Handle key press events.
        """
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.add_current_text_if_valid():
                self.selected()
                self.hide_completer()
        elif event.key() == Qt.Key_Escape:
            self.set_current_text(self.selected_text)
            self.hide_completer()
        else:
            QComboBox.keyPressEvent(self, event)

    # --- Own methods
    def is_valid(self, qstr):
        """
        Return True if string is valid
        Return None if validation can't be done
        """
        pass

    def selected(self):
        """Action to be executed when a valid item has been selected"""
        self.valid.emit(True, True)

    def add_text(self, text):
        """Add text to combo box: add a new item if text is not found in
        combo box items."""
        index = self.findText(text)
        while index != -1:
            self.removeItem(index)
            index = self.findText(text)
        self.insertItem(0, text)
        index = self.findText('')
        if index != -1:
            self.removeItem(index)
            self.insertItem(0, '')
            if text != '':
                self.setCurrentIndex(1)
            else:
                self.setCurrentIndex(0)
        else:
            self.setCurrentIndex(0)

    def set_current_text(self, text):
        """Sets the text of the QLineEdit of the QComboBox."""
        self.lineEdit().setText(to_text_string(text))

    def add_current_text(self):
        """Add current text to combo box history (convenient method)"""
        text = self.currentText()
        self.add_text(text)

    def add_current_text_if_valid(self):
        """Add current text to combo box history if valid"""
        valid = self.is_valid(self.currentText())
        if valid or valid is None:
            self.add_current_text()
            return True
        else:
            self.set_current_text(self.selected_text)

    def hide_completer(self):
        """Hides the completion widget."""
        self.setCompleter(QCompleter([], self))


class PatternComboBox(BaseComboBox):
    """Search pattern combo box"""
    def __init__(self, parent, items=None, tip=None,
                 adjust_to_minimum=True):
        BaseComboBox.__init__(self, parent)
        if hasattr(self.lineEdit(), 'setClearButtonEnabled'):  # only Qt >= 5.2
            self.lineEdit().setClearButtonEnabled(True)
        if adjust_to_minimum:
            self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if items is not None:
            self.addItems(items)
        if tip is not None:
            self.setToolTip(tip)


class EditableComboBox(BaseComboBox):
    """
    Editable combo box + Validate
    """

    def __init__(self, parent):
        BaseComboBox.__init__(self, parent)
        self.font = QFont()
        self.selected_text = self.currentText()

        # Widget setup
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)

        # Signals
        self.editTextChanged.connect(self.validate)
        self.tips = {True: _("Press enter to validate this entry"),
                     False: _('This entry is incorrect')}

    def show_tip(self, tip=""):
        """Show tip"""
        QToolTip.showText(self.mapToGlobal(self.pos()), tip, self)

    def selected(self):
        """Action to be executed when a valid item has been selected"""
        BaseComboBox.selected(self)
        self.selected_text = self.currentText()

    def validate(self, qstr, editing=True):
        """Validate entered path"""
        if self.selected_text == qstr and qstr != '':
            self.valid.emit(True, True)
            return

        valid = self.is_valid(qstr)
        if editing:
            if valid:
                self.valid.emit(True, False)
            else:
                self.valid.emit(False, False)


class PathComboBox(EditableComboBox):
    """
    QComboBox handling path locations
    """
    open_dir = Signal(str)

    def __init__(self, parent, adjust_to_contents=False):
        EditableComboBox.__init__(self, parent)

        # Replace the default lineedit by a custom one with icon display
        lineedit = IconLineEdit(self)

        # Widget setup
        if adjust_to_contents:
            self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        else:
            self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: _("Press enter to validate this path"),
                     False: ''}
        self.setLineEdit(lineedit)

        # Signals
        self.highlighted.connect(self.add_tooltip_to_highlighted_item)
        self.sig_tab_pressed.connect(self.tab_complete)
        self.valid.connect(lineedit.update_status)

    # --- Qt overrides
    def focusInEvent(self, event):
        """Handle focus in event restoring to display the status icon."""
        show_status = getattr(self.lineEdit(), 'show_status_icon', None)
        if show_status:
            show_status()
        QComboBox.focusInEvent(self, event)

    def focusOutEvent(self, event):
        """Handle focus out event restoring the last valid selected path."""
        # Calling asynchronously the 'add_current_text' to avoid crash
        # https://groups.google.com/group/spyderlib/browse_thread/thread/2257abf530e210bd
        if not self.is_valid():
            lineedit = self.lineEdit()
            QTimer.singleShot(50, lambda: lineedit.setText(self.selected_text))

        hide_status = getattr(self.lineEdit(), 'hide_status_icon', None)
        if hide_status:
            hide_status()
        QComboBox.focusOutEvent(self, event)

    # --- Own methods
    def _complete_options(self):
        """Find available completion options."""
        text = to_text_string(self.currentText())
        opts = glob.glob(text + "*")
        opts = sorted([opt for opt in opts if osp.isdir(opt)])

        completer = QCompleter(opts, self)
        if is_dark_interface():
            dark_qss = qdarkstyle.load_stylesheet_from_environment()
            completer.popup().setStyleSheet(dark_qss)
        self.setCompleter(completer)

        return opts

    def tab_complete(self):
        """
        If there is a single option available one tab completes the option.
        """
        opts = self._complete_options()
        if len(opts) == 1:
            self.set_current_text(opts[0] + os.sep)
            self.hide_completer()
        else:
            self.completer().complete()

    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return osp.isdir(to_text_string(qstr))

    def selected(self):
        """Action to be executed when a valid item has been selected"""
        self.selected_text = self.currentText()
        self.valid.emit(True, True)
        self.open_dir.emit(self.selected_text)

    def add_current_text(self):
        """
        Add current text to combo box history (convenient method).
        If path ends in os separator ("\" windows, "/" unix) remove it.
        """
        text = self.currentText()
        if osp.isdir(text) and text:
            if text[-1] == os.sep:
                text = text[:-1]
        self.add_text(text)

    def add_tooltip_to_highlighted_item(self, index):
        """
        Add a tooltip showing the full path of the currently highlighted item
        of the PathComboBox.
        """
        self.setItemData(index, self.itemText(index), Qt.ToolTipRole)


class UrlComboBox(PathComboBox):
    """
    QComboBox handling urls
    """
    def __init__(self, parent, adjust_to_contents=False):
        PathComboBox.__init__(self, parent, adjust_to_contents)
        line_edit = QLineEdit(self)
        self.setLineEdit(line_edit)
        self.editTextChanged.disconnect(self.validate)

    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return QUrl(qstr).isValid()


class FileComboBox(PathComboBox):
    """
    QComboBox handling File paths
    """
    def __init__(self, parent=None, adjust_to_contents=False,
                 default_line_edit=False):
        PathComboBox.__init__(self, parent, adjust_to_contents)

        if default_line_edit:
            line_edit = QLineEdit(self)
            self.setLineEdit(line_edit)

        # Widget setup
        if adjust_to_contents:
            self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        else:
            self.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def is_valid(self, qstr=None):
        """Return True if string is valid."""
        if qstr is None:
            qstr = self.currentText()
        valid = (osp.isfile(to_text_string(qstr)) or
                 osp.isdir(to_text_string(qstr)))
        return valid

    def tab_complete(self):
        """
        If there is a single option available one tab completes the option.
        """
        opts = self._complete_options()
        if len(opts) == 1:
            text = opts[0]
            if osp.isdir(text):
                text = text + os.sep
            self.set_current_text(text)
            self.hide_completer()
        else:
            self.completer().complete()

    def _complete_options(self):
        """Find available completion options."""
        text = to_text_string(self.currentText())
        opts = glob.glob(text + "*")
        opts = sorted([opt for opt in opts
                       if osp.isdir(opt) or osp.isfile(opt)])

        completer = QCompleter(opts, self)
        if is_dark_interface():
            dark_qss = qdarkstyle.load_stylesheet_from_environment()
            completer.popup().setStyleSheet(dark_qss)
        self.setCompleter(completer)

        return opts


def is_module_or_package(path):
    """Return True if path is a Python module/package"""
    is_module = osp.isfile(path) and osp.splitext(path)[1] in ('.py', '.pyw')
    is_package = osp.isdir(path) and osp.isfile(osp.join(path, '__init__.py'))
    return is_module or is_package


class PythonModulesComboBox(PathComboBox):
    """
    QComboBox handling Python modules or packages path
    (i.e. .py, .pyw files *and* directories containing __init__.py)
    """
    def __init__(self, parent, adjust_to_contents=False):
        PathComboBox.__init__(self, parent, adjust_to_contents)

    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return is_module_or_package(to_text_string(qstr))

    def selected(self):
        """Action to be executed when a valid item has been selected"""
        EditableComboBox.selected(self)
        self.open_dir.emit(self.currentText())
