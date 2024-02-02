# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for SidebarDialog."""

# Third party imports
from qtpy.QtWidgets import QLabel, QVBoxLayout
import pytest

# Local imports
from spyder.utils.stylesheet import APP_STYLESHEET
from spyder.widgets.sidebardialog import SidebarDialog, SidebarPage


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def sidebar_dialog(qapp, qtbot):

    # Pages
    class Page1(SidebarPage):

        def get_name(self):
            return "Page 1"

        def get_icon(self):
            return self.create_icon("variable_explorer")

        def setup_page(self):
            self.label = QLabel("This is page one!")
            layout = QVBoxLayout()
            layout.addWidget(self.label)
            layout.addStretch(1)
            self.setLayout(layout)

    class Page2(SidebarPage):

        def get_name(self):
            return "Page 2"

        def get_icon(self):
            return self.create_icon("files")

        def setup_page(self):
            self.label = QLabel("This is page two!")
            layout = QVBoxLayout()
            layout.addWidget(self.label)
            layout.addStretch(1)
            self.setLayout(layout)

    # Dialog
    class TestDialog(SidebarDialog):
        PAGE_CLASSES = [Page1, Page2]

    qapp.setStyleSheet(str(APP_STYLESHEET))
    dialog = TestDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    return dialog


# --- Tests
# -----------------------------------------------------------------------------
def test_sidebardialog(sidebar_dialog, qtbot):
    dialog = sidebar_dialog
    assert dialog is not None

    # To check the dialog visually
    qtbot.wait(1000)

    # Check label displayed in the initial page
    assert "one" in dialog.get_page().label.text()

    # Check label in the second page
    dialog.set_current_index(1)
    assert "two" in dialog.get_page().label.text()
