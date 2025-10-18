# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Text editor dialog
"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
)

# Local import
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog


# =============================================================================
# ---- Constants
# =============================================================================
class TextEditorActions:
    Close = 'close'
    Copy = 'copy_action'


class TextEditorMenus:
    Options = 'options_menu'


class TextEditorWidgets:
    OptionsToolButton = 'options_button_widget'
    Toolbar = 'toolbar'
    ToolbarStretcher = 'toolbar_stretcher'


class TextEditorToolbarSections:
    Copy = 'copy_section'


class TextEditor(BaseDialog, SpyderWidgetMixin, SpyderFontsMixin):
    """Array Editor Dialog"""
    CONF_SECTION = 'variable_explorer'

    def __init__(self, text, title='', parent=None, readonly=False):
        super().__init__(parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.text = None
        self.btn_save_and_close = None

        self.close_action = self.create_action(
            name=TextEditorActions.Close,
            icon=self.create_icon('close_pane'),
            text=_('Close'),
            triggered=self.reject,
            shortcut=self.get_shortcut(TextEditorActions.Close),
            register_action=False,
            register_shortcut=True
        )
        self.register_shortcut_for_widget(name='close', triggered=self.reject)

        # Display text as unicode if it comes as bytes, so users see
        # its right representation
        if isinstance(text, bytes):
            self.is_binary = True
            text = str(text, 'utf8')
        else:
            self.is_binary = False

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.toolbar = self.create_toolbar(
            TextEditorWidgets.Toolbar,
            register=False
        )
        self.layout.addWidget(self.toolbar)

        # Text edit
        self.edit = QTextEdit(parent)
        self.edit.setReadOnly(readonly)
        self.edit.textChanged.connect(self.text_changed)
        self.edit.setPlainText(text)
        font = self.get_font(SpyderFontType.MonospaceInterface)
        self.edit.setFont(font)
        self.layout.addWidget(self.edit)

        # Buttons configuration
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        if not readonly:
            self.btn_save_and_close = QPushButton(_('Save and Close'))
            self.btn_save_and_close.setDisabled(True)
            self.btn_save_and_close.clicked.connect(self.accept)
            btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        self.layout.addLayout(btn_layout)

        # Make the dialog act as a window
        if sys.platform == 'darwin':
            # See spyder-ide/spyder#12825
            self.setWindowFlags(Qt.Tool)
        else:
            # Make the dialog act as a window
            self.setWindowFlags(Qt.Window)

        self.setWindowIcon(ima.icon('edit'))
        if title:
            try:
                unicode_title = str(title)
            except UnicodeEncodeError:
                unicode_title = u''
        else:
            unicode_title = u''

        self.setWindowTitle(_("Text editor") + \
                            u"%s" % (u" - " + unicode_title
                                     if unicode_title else u""))
        
        stretcher = self.create_stretcher(
            TextEditorWidgets.ToolbarStretcher
        )
        options_menu = self.create_menu(
            TextEditorMenus.Options,
            register=False
        )
        for item in [self.close_action]:
            self.add_item_to_menu(item, options_menu)
        options_button = self.create_toolbutton(
            name=TextEditorWidgets.OptionsToolButton,
            text=_('Options'),
            icon=ima.icon('tooloptions'),
            register=False
        )
        options_button.setPopupMode(QToolButton.InstantPopup)
        options_button.setMenu(options_menu)

        self.toolbar.clear()
        self.toolbar._section_items.clear()
        self.toolbar._item_map.clear()
        
        for item in [stretcher, options_button]:
            self.add_item_to_toolbar(
                item,
                self.toolbar,
                section=TextEditorToolbarSections.Copy
            )
        self.toolbar.render()

    @Slot()
    def text_changed(self):
        """Text has changed"""
        # Save text as bytes, if it was initially bytes
        if self.is_binary:
            self.text = bytes(self.edit.toPlainText(), 'utf8')
        else:
            self.text = str(self.edit.toPlainText())
        if self.btn_save_and_close:
            self.btn_save_and_close.setEnabled(True)
            self.btn_save_and_close.setAutoDefault(True)
            self.btn_save_and_close.setDefault(True)

    def get_value(self):
        """Return modified text"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.text

    def setup_and_check(self, value):
        """Verify if TextEditor is able to display strings passed to it."""
        try:
            if not isinstance(value, str):
                str(value, 'utf8')
            return True
        except Exception:
            return False

#==============================================================================
# Tests
#==============================================================================
def test():
    """Text editor demo"""
    from spyder.utils.qthelpers import qapplication
    _app = qapplication()  # analysis:ignore

    text = """01234567890123456789012345678901234567890123456789012345678901234567890123456789
dedekdh elkd ezd ekjd lekdj elkdfjelfjk e"""
    dialog = TextEditor(text)
    dialog.exec_()

    dlg_text = dialog.get_value()
    assert text == dlg_text


if __name__ == "__main__":
    test()
