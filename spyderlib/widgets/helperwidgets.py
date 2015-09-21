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
                                QVBoxLayout, QSpacerItem, QHBoxLayout,
                                QMessageBox, QCheckBox, QWidget, QMenu)


# Local imports
from spyderlib.config.base import _
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.qthelpers import get_std_icon
import spyderlib.utils.icon_manager as ima

class WidgetInnerToolbar(QWidget):
    """A light-weight toolbar-like widget which can be toggled on/off like
    a proper toolbar. Usage: Layout.addWidget(WidgetInnerToolbar)"""
    
    def __init__(self, buttons, non_icon_buttons=None):
        """Expects a sequence of buttons, each of which is made using
        the helper function called create_toolbutton."""
        # TODO: fix import issues, so this isn't local
        from spyderlib.utils.qthelpers import create_action, add_actions
                                               
        QWidget.__init__(self)
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)
        self._layout.setAlignment(Qt.AlignLeft)
        self._layout.setContentsMargins(0, 0, 0, 0)

        for btn in buttons:
            self._layout.addWidget(btn)
        
        if non_icon_buttons:
            self._button_menu = QToolButton(self)
            self._menu = QMenu(self)
            add_actions(self._menu, non_icon_buttons)
            self._button_menu.setIcon(ima.icon('tooloptions'))
            self._button_menu.setPopupMode(QToolButton.InstantPopup)
            self._button_menu.setMenu(self._menu)
            self._layout.addStretch()
            self._layout.addWidget(self._button_menu)

        self._dummy_parent = QObject()
        self._toggle_view_action = create_action(self._dummy_parent,
                                                 "toggle WidgetInnerToolbar",
                                                 toggled=self.toggleEvent)
        self._toggle_view_action.setChecked(True)
    
    @Slot(bool)
    def toggleEvent(self, v):
        """handler for toggle_view_action"""
        self.setVisible(v)
    
    def toggleViewAction(self):
        return self._toggle_view_action
        
    def objectName(self):
        return None

    @Slot(bool)
    def toggle_icontext(self, value):
        print("TODO")
        # TODO: actually make this work
        # for widget in something:
        #     if widget is not self.button_menu:
        #         if state:
        #             widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        #         else:
        #             widget.setToolButtonStyle(Qt.ToolButtonIconOnly)

        
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
