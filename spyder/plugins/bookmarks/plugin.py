# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""Bookmarks/errors Plugin."""


# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.api.plugins import SpyderPluginWidget

from .widgets.bookmarksgui import BookmarkWidget


class Bookmarks(SpyderPluginWidget):
    """Bookmarkslist"""
    CONF_SECTION = 'bookmarks'

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.bookmarks = BookmarkWidget(self,
                                        options_button=self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.bookmarks)
        self.setLayout(layout)

    # ----- SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Bookmarks")

    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('bookmarks', icon_path=path)

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.bookmarks.bookmarktable

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.help)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.bookmarks.load_bookmark.connect(self.main.editor.load_bookmark)

        # Follow bookmark changes
        self.main.editor.bookmarks_changed.connect(self.set_data)
        self.bookmarks.delete_all_bookmarks.connect(self.main.editor.delete_all_bookmarks)
        self.bookmarks.delete_bookmark.connect(self.main.editor.delete_bookmark)
        self.add_dockwidget()

        list_action = create_action(self, _("List bookmarks/errors"),
                                    triggered=self.show)
        list_action.setEnabled(True)
        self.main.editor.pythonfile_dependent_actions += [list_action]

    def show(self):
        """Show the bookmarks dockwidget"""
        self.switch_to_plugin()

    @Slot()
    def set_data(self):
        self.bookmarks.set_data()
