# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Copyright © 2010-2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

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
from spyderlib.qt.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from spyderlib.qt.QtGui import (QApplication, QComboBox, QCompleter, QFont,
                                QLineEdit, QPainter, QSizePolicy, QToolTip)

# Local imports
from spyderlib.config.base import _
from spyderlib.py3compat import to_text_string
from spyderlib.utils import icon_manager as ima


class BaseComboBox(QComboBox):
    """Editable combo box base class"""
    valid = Signal(bool, bool)
    sig_tab_pressed = Signal(bool)
    sig_double_tab_pressed = Signal(bool)

    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.setEditable(True)
        self.setCompleter(QCompleter(self))
        self.numpress = 0

    # --- overrides
    def event(self, event):
        """Qt Override.

        Filter tab keys and process double tab keys.
        """
        if (event.type() == QEvent.KeyPress) and (event.key() == Qt.Key_Tab):
            self.sig_tab_pressed.emit(True)
            self.numpress += 1
            if self.numpress == 1:
                self.presstimer = QTimer.singleShot(400, self.hanlde_keypress)
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
            self.lineEdit().setText(self.selected_text)
            self.hide_completer()
        else:
            QComboBox.keyPressEvent(self, event)

    def focusOutEvent(self, event):
        """Handle focus out event restoring the last valid selected path."""
        # Calling asynchronously the 'add_current_text' to avoid crash
        # https://groups.google.com/group/spyderlib/browse_thread/thread/2257abf530e210bd
        lineedit = self.lineEdit()
        QTimer.singleShot(50, lambda: lineedit.setText(self.selected_text))
        QComboBox.focusOutEvent(self, event)

    # --- own methods
    def hanlde_keypress(self):
        """ """
        if self.numpress == 2:
            self.sig_double_tab_pressed.emit(True)
        self.numpress = 0

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
        if osp.isdir(text):
            if text[-1] == os.sep:
                text = text[:-1]
        self.add_text(text)

    def add_current_text_if_valid(self):
        """Add current text to combo box history if valid"""
        valid = self.is_valid(self.currentText())
        if valid or valid is None:
            self.add_current_text()
            return True
        else:
            self.lineEdit().setText(self.selected_text)

    def hide_completer(self):
        """Hides the completion widget."""
        self.setCompleter(QCompleter([], self))


class PatternComboBox(BaseComboBox):
    """Search pattern combo box"""
    def __init__(self, parent, items=None, tip=None,
                 adjust_to_minimum=True):
        BaseComboBox.__init__(self, parent)
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
        if self.selected_text == qstr:
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
        self.sig_tab_pressed.connect(self.tab_complete)
        self.sig_double_tab_pressed.connect(self.double_tab_complete)
        self.valid.connect(lineedit.update_status)

    def _complete_options(self):
        """Find available completion options."""
        text = to_text_string(self.currentText())
        opts = glob.glob(text + "*")
        opts = sorted([opt for opt in opts if osp.isdir(opt)])
        self.setCompleter(QCompleter(opts, self))
        return opts

    def double_tab_complete(self):
        """If several options available a double tab displays options."""
        opts = self._complete_options()
        if len(opts) > 1:
            self.completer().complete()

    def tab_complete(self):
        """
        If there is a single option available one tab completes the option.
        """
        opts = self._complete_options()
        if len(opts) == 1:
            self.set_current_text(opts[0] + os.sep)
            self.hide_completer()

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


class UrlComboBox(PathComboBox):
    """
    QComboBox handling urls
    """
    def __init__(self, parent, adjust_to_contents=False):
        PathComboBox.__init__(self, parent, adjust_to_contents)
        self.editTextChanged.disconnect(self.validate)

    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return QUrl(qstr).isValid()


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


class IconLineEdit(QLineEdit):
    """Custom QLineEdit that includes an icon representing the validation."""
    def __init__(self, *args, **kwargs):
        super(IconLineEdit, self).__init__(*args, **kwargs)

        self._status = True
        self._status_set = True
        self._valid_icon = ima.icon('todo')
        self._invalid_icon = ima.icon('warning')
        self._set_icon = ima.icon('todo_list')

    def _refresh(self):
        """After an application style change, the paintEvent updates the
        custom defined stylesheet.
        """
        application_style = QApplication.style().objectName()
        padding = self.height()
        css_base = """QLineEdit {{border: none;
                                 padding-left: {padding}px;
                                 }}
                   """
        css_oxygen = """QLineEdit {{background: transparent;
                                   border: none;
                                   padding-left: {padding}px;
                                   }}
                     """
        if application_style == 'oxygen':
            css_template = css_oxygen
        else:
            css_template = css_base

        css = css_template.format(padding=padding)
        self.setStyleSheet(css)

    def update_status(self, value, value_set):
        """Update the status and set_status to update the icons to display."""
        self._status = value
        self._status_set = value_set
        self.repaint()
        self.update()

    def paintEvent(self, event):
        """Qt Override.

        Include a validation icon to the left of the line edit.
        """
        self._refresh()
        super(IconLineEdit, self).paintEvent(event)
        painter = QPainter(self)

        rect = self.geometry()
        space = int((rect.height())/6)
        h = rect.height() - space

        if self._status and self._status_set:
            pixmap = self._set_icon.pixmap(h, h)
        elif self._status:
            pixmap = self._valid_icon.pixmap(h, h)
        else:
            pixmap = self._invalid_icon.pixmap(h, h)

        painter.drawPixmap(space, space, pixmap)
