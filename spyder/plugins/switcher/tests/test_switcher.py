# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Switcher Widget.
"""
# Third party imports
import pytest
from qtpy.QtCore import Qt

from spyder.config.base import _


@pytest.fixture
def dlg_switcher(qtbot):
    """Set up switcher widget."""
    # Local import need to run tests locally
    from spyder.plugins.switcher.widgets.switcher import Switcher

    dlg_switcher = Switcher(None, item_styles=None,
                            item_separator_styles=None)
    dlg_switcher.add_mode('>', _('Commands'))
    dlg_switcher.add_mode('?', _('Help'))
    dlg_switcher.add_mode(':', _('Go to Line'))
    dlg_switcher.add_mode('@', _('Go to Symbol in File'))

    def handle_modes(mode):
        if mode == '>':
            create_options_example_switcher(dlg_switcher)
        elif mode == '?':
            create_help_example_switcher(dlg_switcher)
        elif mode == ':':
            create_line_example_switcher(dlg_switcher)
        elif mode == '@':
            create_symbol_example_switcher(dlg_switcher)
        elif mode == '':
            create_vcs_example_switcher(dlg_switcher)

    def item_selected(item, mode, search_text):
        print([item, mode, search_text])  # spyder: test-skip
        print([item.get_title(), mode, search_text])  # spyder: test-skip

    dlg_switcher.sig_mode_selected.connect(handle_modes)
    dlg_switcher.sig_item_selected.connect(item_selected)

    qtbot.addWidget(dlg_switcher)
    create_vcs_example_switcher(dlg_switcher)
    return dlg_switcher


def test_switcher(dlg_switcher, qtbot):
    """Test that shortcut summary is visible and is not empty"""
    # Test that the dialog exists and is shown
    dlg_switcher.show()
    assert dlg_switcher.isVisible()

    # Test that the dialog is closed properly on Esc keypress
    qtbot.keyClick(dlg_switcher.edit, Qt.Key_Escape)
    assert not dlg_switcher.isVisible()


def test_switcher_filter_and_mode(dlg_switcher, qtbot):
    """Test filter and mode change."""
    edit = dlg_switcher.edit

    # Initially cvs mode with five rows
    assert dlg_switcher.count() == 6

    # Match one row by name
    edit.setText("master")
    qtbot.wait(1000)
    assert dlg_switcher.count() == 2

    # Help mode
    edit.setText("")
    edit.setText("?")
    qtbot.wait(1000)
    assert dlg_switcher.count() == 5

    # Symbol mode
    edit.setText("")
    edit.setText("@")
    qtbot.wait(1000)
    assert dlg_switcher.count() == 2

    # Commands mode
    edit.setText("")
    edit.setText(">")
    qtbot.wait(1000)
    assert dlg_switcher.count() == 7

    # Text mode
    edit.setText("")
    edit.setText(":")
    qtbot.wait(1000)
    assert dlg_switcher.count() == 1


def test_switcher_filter_unicode(dlg_switcher, qtbot):
    """Test filter with unicode."""
    edit = dlg_switcher.edit

    # Initially cvs mode with five rows
    assert dlg_switcher.count() == 6
    dlg_switcher.show()
    # Match one row by name
    edit.setText('试')
    qtbot.wait(1000)
    assert dlg_switcher.count() == 2

# Helper functions for tests


def create_vcs_example_switcher(sw):
    """Add example data for vcs."""
    from spyder.utils.icon_manager import ima
    sw.clear()
    sw.set_placeholder_text('Select a ref to Checkout')
    sw.add_item(title='Create New Branch', action_item=True,
                icon=ima.icon('MessageBoxInformation'))
    sw.add_item(title='master', description='123123')
    sw.add_item(title='develop', description='1231232a')
    sw.add_item(title=u'test-试', description='1231232ab')
    sw.add_separator()
    sw.add_item(title='other', description='q2211231232a')


def create_options_example_switcher(sw):
    """Add example actions."""
    sw.clear()
    sw.set_placeholder_text('Select Action')
    section = _('change view')
    sw.add_item(title=_('Indent Using Spaces'), description='Test',
                section=section, shortcut='Ctrl+I')
    sw.add_item(title=_('Indent Using Tabs'), description='Test',
                section=section)
    sw.add_item(title=_('Detect Indentation from Content'), section=section)
    sw.add_separator()
    section = _('convert file')
    sw.add_item(title=_('Convert Indentation to Spaces'), description='Test',
                section=section)
    sw.add_item(title=_('Convert Indentation to Tabs'), section=section)
    sw.add_item(title=_('Trim Trailing Whitespace'), section=section)


def create_help_example_switcher(sw):
    """Add help data."""
    sw.clear()
    sw.add_item(title=_('Help me!'), section='1')
    sw.add_separator()
    sw.add_item(title=_('Help me 2!'), section='2')
    sw.add_separator()
    sw.add_item(title=_('Help me 3!'), section='3')


def create_line_example_switcher(sw):
    """Add current line example."""
    sw.clear()
    sw.add_item(title=_('Current line, type something'), action_item=True)


def create_symbol_example_switcher(sw):
    """Add symbol data example."""
    sw.clear()
    sw.add_item(title=_('Some symbol'))
    sw.add_item(title=_('another symbol'))


def create_example_switcher(main=None):
    """Create example switcher."""
    from spyder.plugins.switcher.widgets.switcher import Switcher
    from qtpy.QtWidgets import QLineEdit
    # Create Switcher
    if main is None:
        main = QLineEdit()
    sw = Switcher(main)
    sw.add_mode('>', _('Commands'))
    sw.add_mode('?', _('Help'))
    sw.add_mode(':', _('Go to Line'))
    sw.add_mode('@', _('Go to Symbol in File'))

    def handle_modes(mode):
        if mode == '>':
            create_options_example_switcher(sw)
        elif mode == '?':
            create_help_example_switcher(sw)
        elif mode == ':':
            create_line_example_switcher(sw)
        elif mode == '@':
            create_symbol_example_switcher(sw)
        elif mode == '':
            create_vcs_example_switcher(sw)

    def item_selected(item, mode, search_text):
        print([item, mode, search_text])  # spyder: test-skip
        print([item.get_title(), mode, search_text])  # spyder: test-skip

    sw.sig_mode_selected.connect(handle_modes)
    sw.sig_item_selected.connect(item_selected)

    create_vcs_example_switcher(sw)
    sw.show()
