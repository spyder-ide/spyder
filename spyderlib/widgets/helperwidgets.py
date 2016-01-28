# -*- coding: utf-8 -*-
#
# Copyright © 2013-2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Helper widgets.
"""

# Third party imports
from spyderlib.qt.QtCore import QPoint, QSize, Qt
from spyderlib.qt.QtGui import (QToolButton, QToolTip,
                                QStyledItemDelegate, QApplication,
                                QTextDocument, QStyleOptionViewItem,
                                QAbstractTextDocumentLayout, QStyle,
                                QVBoxLayout, QSpacerItem, QPainter,
                                QMessageBox, QCheckBox, QLineEdit)

# Local imports
from spyderlib.config.base import _
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.qthelpers import get_std_icon


class HelperToolButton(QToolButton):
    """Subclasses QToolButton, to provide a simple tooltip on mousedown.
    """
    def __init__(self):
        QToolButton.__init__(self)
        self.setIcon(get_std_icon('MessageBoxInformation'))
        style = """
            QToolButton {
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
              background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                  stop: 0 #f6f7fa, stop: 1 #dadbde);
            }
            """
        self.setStyleSheet(style)

    def setToolTip(self, text):
        self._tip_text = text

    def toolTip(self):
        return self._tip_text

    def mousePressEvent(self, event):
        QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())),
                          self._tip_text)


class MessageCheckBox(QMessageBox):
    """
    A QMessageBox derived widget that includes a QCheckBox aligned to the right
    under the message and on top of the buttons.
    """
    def __init__(self, *args, **kwargs):
        super(MessageCheckBox, self).__init__(*args, **kwargs)

        self._checkbox = QCheckBox()

        # Set layout to include checkbox
        size = 9
        check_layout = QVBoxLayout()
        check_layout.addItem(QSpacerItem(size, size))
        check_layout.addWidget(self._checkbox, 0, Qt.AlignRight)
        check_layout.addItem(QSpacerItem(size, size))

        # Access the Layout of the MessageBox to add the Checkbox
        layout = self.layout()
        layout.addLayout(check_layout, 1, 1)

    # --- Public API
    # Methods to access the checkbox
    def is_checked(self):
        return self._checkbox.isChecked()

    def set_checked(self, value):
        return self._checkbox.setChecked(value)

    def set_check_visible(self, value):
        self._checkbox.setVisible(value)

    def is_check_visible(self):
        self._checkbox.isVisible()

    def checkbox_text(self):
        self._checkbox.text()

    def set_checkbox_text(self, text):
        self._checkbox.setText(text)


class HTMLDelegate(QStyledItemDelegate):
    """With this delegate, a QListWidgetItem or a QTableItem can render HTML.

    Taken from http://stackoverflow.com/a/5443112/2399799
    """
    def __init__(self, parent, margin=0):
        super(HTMLDelegate, self).__init__(parent)
        self._margin = margin

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        doc.setDocumentMargin(self._margin)
        doc.setHtml(options.text)

        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
        painter.save()
        if style.objectName() == 'oxygen':
            painter.translate(textRect.topLeft() + QPoint(5, -9))
        else:
            painter.translate(textRect.topLeft())
            painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())

        return QSize(doc.idealWidth(), doc.size().height())


class IconLineEdit(QLineEdit):
    """Custom QLineEdit that includes an icon representing the validation."""

    def __init__(self, *args, **kwargs):
        super(IconLineEdit, self).__init__(*args, **kwargs)

        self._status = True
        self._status_set = True
        self._valid_icon = ima.icon('todo')
        self._invalid_icon = ima.icon('warning')
        self._set_icon = ima.icon('todo_list')
        self._application_style = QApplication.style().objectName()
        self._refresh()
        self._paint_count = 0
        self._icon_visible = False

    def _refresh(self):
        """After an application style change, the paintEvent updates the
        custom defined stylesheet.
        """
        padding = self.height()
        css_base = """QLineEdit {{
                                 border: none;
                                 padding-right: {padding}px;
                                 }}
                   """
        css_oxygen = """QLineEdit {{background: transparent;
                                   border: none;
                                   padding-right: {padding}px;
                                   }}
                     """
        if self._application_style == 'oxygen':
            css_template = css_oxygen
        else:
            css_template = css_base

        css = css_template.format(padding=padding)
        self.setStyleSheet(css)
        self.update()

    def hide_status_icon(self):
        """Show the status icon."""
        self._icon_visible = False
        self.repaint()
        self.update()

    def show_status_icon(self):
        """Hide the status icon."""
        self._icon_visible = True
        self.repaint()
        self.update()

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
        super(IconLineEdit, self).paintEvent(event)
        painter = QPainter(self)

        rect = self.geometry()
        space = int((rect.height())/6)
        h = rect.height() - space
        w = rect.width() - h

        if self._icon_visible:
            if self._status and self._status_set:
                pixmap = self._set_icon.pixmap(h, h)
            elif self._status:
                pixmap = self._valid_icon.pixmap(h, h)
            else:
                pixmap = self._invalid_icon.pixmap(h, h)

            painter.drawPixmap(w, space, pixmap)

        application_style = QApplication.style().objectName()
        if self._application_style != application_style:
            self._application_style = application_style
            self._refresh()

        # Small hack to gurantee correct padding on Spyder start
        if self._paint_count < 5:
            self._paint_count += 1
            self._refresh()


def test_msgcheckbox():
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    box = MessageCheckBox()
    box.setWindowTitle(_("Spyder updates"))
    box.setText("Testing checkbox")
    box.set_checkbox_text("Check for updates on startup?")
    box.setStandardButtons(QMessageBox.Ok)
    box.setDefaultButton(QMessageBox.Ok)
    box.setIcon(QMessageBox.Information)
    box.exec_()


if __name__ == '__main__':
    test_msgcheckbox()
