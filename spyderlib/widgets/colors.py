# -*- coding: utf-8 -*-

from spyderlib.qt.QtGui import (QLineEdit, QIcon, QHBoxLayout, QColor,
                                QPushButton, QColorDialog, QPixmap)
from spyderlib.qt.QtCore import SIGNAL, QSize, Slot, Property

# Local imports
from spyderlib.py3compat import is_text_string


class ColorButton(QPushButton):
    """
    Color choosing push button
    """
    __pyqtSignals__ = ("colorChanged(QColor)",)
    
    def __init__(self, parent=None):
        QPushButton.__init__(self, parent)
        self.setFixedSize(20, 20)
        self.setIconSize(QSize(12, 12))
        self.connect(self, SIGNAL("clicked()"), self.choose_color)
        self._color = QColor()
    
    def choose_color(self):
        color = QColorDialog.getColor(self._color, self.parentWidget(),
                                      'Select Color',
                                      QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.set_color(color)
    
    def get_color(self):
        return self._color
    
    @Slot(QColor)
    def set_color(self, color):
        if color != self._color:
            self._color = color
            self.emit(SIGNAL("colorChanged(QColor)"), self._color)
            pixmap = QPixmap(self.iconSize())
            pixmap.fill(color)
            self.setIcon(QIcon(pixmap))
    
    color = Property("QColor", get_color, set_color)


def text_to_qcolor(text):
    """
    Create a QColor from specified string
    Avoid warning from Qt when an invalid QColor is instantiated
    """
    color = QColor()
    text = str(text)
    if not is_text_string(text):
        return color
    if text.startswith('#') and len(text)==7:
        correct = '#0123456789abcdef'
        for char in text:
            if char.lower() not in correct:
                return color
    elif text not in list(QColor.colorNames()):
        return color
    color.setNamedColor(text)
    return color


class ColorLayout(QHBoxLayout):
    """Color-specialized QLineEdit layout"""
    def __init__(self, color, parent=None):
        QHBoxLayout.__init__(self)
        assert isinstance(color, QColor)
        self.lineedit = QLineEdit(color.name(), parent)
        self.connect(self.lineedit, SIGNAL("textChanged(QString)"),
                     self.update_color)
        self.addWidget(self.lineedit)
        self.colorbtn = ColorButton(parent)
        self.colorbtn.color = color
        self.connect(self.colorbtn, SIGNAL("colorChanged(QColor)"),
                     self.update_text)
        self.addWidget(self.colorbtn)

    def update_color(self, text):
        color = text_to_qcolor(text)
        if color.isValid():
            self.colorbtn.color = color

    def update_text(self, color):
        self.lineedit.setText(color.name())
        
    def text(self):
        return self.lineedit.text()
