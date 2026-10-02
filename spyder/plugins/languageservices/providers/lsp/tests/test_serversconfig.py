# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the LSP servers table and editor dialog."""

from qtpy.QtWidgets import QWidget

from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.plugins.languageservices.providers.lsp.widgets.serversconfig import (
    LSPServerEditor,
)


class EditorHost(QWidget):
    """Stand-in for the servers table the editor takes as parent."""

    def server_names(self):
        return ["existing"]


def get_option(option, default=None, section=None):
    assert (section, option) == ("appearance", "selected")
    return "spyder/dark"


def test_editor_opens_blank_for_new_server(qtbot):
    host = EditorHost()
    qtbot.addWidget(host)
    editor = LSPServerEditor(host, None, get_option)
    qtbot.addWidget(editor)

    assert editor.name_input.text() == ""
    assert editor.host_input.text() == "127.0.0.1"
    assert editor.port_spinner.value() == 2084
    # An empty name is invalid, so the dialog cannot be accepted yet.
    assert not editor.button_ok.isEnabled()


def test_editor_shows_existing_server(qtbot):
    host = EditorHost()
    qtbot.addWidget(host)
    config = ServerConfig(
        name="rust", cmd="rust-analyzer", languages=("rust",), stdio=True
    )
    editor = LSPServerEditor(host, config, get_option)
    qtbot.addWidget(editor)

    assert editor.name_input.text() == "rust"
    assert editor.cmd_input.text() == "rust-analyzer"
    assert editor.stdio_cb.isChecked()
