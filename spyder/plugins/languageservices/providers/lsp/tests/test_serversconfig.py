# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the LSP servers table and editor dialog."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QPushButton, QWidget

from spyder.plugins.languageservices.providers.lsp.config import (
    AUTO_LANGUAGES,
    ServerConfig,
)
from spyder.plugins.languageservices.providers.lsp.widgets.serversconfig import (
    LSPServerEditor,
    LSPServerTable,
)


class EditorHost(QWidget):
    """Stand-in for the servers table the editor takes as parent."""

    def server_names(self):
        return ["existing"]


def get_option(option, default=None, section=None):
    assert (section, option) == ("appearance", "selected")
    return "spyder/dark"


class TableHost(QWidget):
    """Stand-in for the config page the servers table takes as parent."""

    def __init__(self, servers):
        super().__init__()
        self.servers = servers
        self.delete_btn = QPushButton(self)
        self.delete_btn.setEnabled(False)

    def get_option(self, option, default=None, section=None):
        if option == "servers":
            return self.servers
        return get_option(option, default, section)


def language_items(editor):
    widget = editor.languages_list
    return {
        widget.item(row).data(Qt.UserRole): widget.item(row)
        for row in range(widget.count())
    }


def check_language(editor, language_id):
    language_items(editor)[language_id].setCheckState(Qt.Checked)


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


def test_editor_options_keep_hidden_fields(qtbot):
    host = EditorHost()
    qtbot.addWidget(host)
    config = ServerConfig(
        name="rust",
        cmd="rust-analyzer",
        stdio=True,
        python_module=True,
        initialization_options={"check": True},
    )
    editor = LSPServerEditor(host, config, get_option)
    qtbot.addWidget(editor)

    editor.name_input.setText("existing")
    assert not editor.button_ok.isEnabled()

    editor.name_input.setText("renamed")
    editor.auto_languages_cb.setChecked(False)
    check_language(editor, "rust")
    options = editor.get_options()
    assert options.name == "renamed"
    assert options.languages == ("rust",)
    assert options.python_module
    assert options.initialization_options == {"check": True}


def test_editor_language_selector(qtbot):
    host = EditorHost()
    qtbot.addWidget(host)
    editor = LSPServerEditor(host, None, get_option)
    qtbot.addWidget(editor)
    editor.name_input.setText("server")
    editor.cmd_input.setText("python")

    # Python and IPython share the "python" id and are listed once.
    texts = [
        editor.languages_list.item(row).text()
        for row in range(editor.languages_list.count())
    ]
    assert texts.count("Python") == 1
    assert "IPython" not in texts
    assert language_items(editor)["python"].text() == "Python"

    # New servers default to auto-detection, which disables the list.
    assert editor.auto_languages_cb.isChecked()
    assert not editor.languages_list.isEnabled()
    assert editor.button_ok.isEnabled()
    assert editor.get_options().languages == AUTO_LANGUAGES

    # Without auto-detection at least one language must be checked.
    editor.auto_languages_cb.setChecked(False)
    assert editor.languages_list.isEnabled()
    assert not editor.button_ok.isEnabled()
    check_language(editor, "go")
    check_language(editor, "rust")
    assert editor.button_ok.isEnabled()
    assert editor.get_options().languages == ("go", "rust")

    editor.languages_filter.setText(".rs")
    visible = [
        language_id for language_id, item in language_items(editor).items()
        if not item.isHidden()
    ]
    assert visible == ["rust"]


def test_editor_keeps_unknown_configured_language(qtbot):
    host = EditorHost()
    qtbot.addWidget(host)
    config = ServerConfig(
        name="zls", cmd="zls", languages=("rust", "zig"), stdio=True
    )
    editor = LSPServerEditor(host, config, get_option)
    qtbot.addWidget(editor)

    assert not editor.auto_languages_cb.isChecked()
    # Configured languages are listed first so they are visible.
    first = [editor.languages_list.item(row).text() for row in range(2)]
    assert first == ["Rust", "zig"]
    items = language_items(editor)
    assert items["zig"].text() == "zig"
    assert set(editor.selected_languages()) == {"rust", "zig"}


def test_table_selection_enables_delete(qtbot):
    servers = {
        "rust": ServerConfig(
            name="rust", cmd="rust-analyzer", languages=("rust",), stdio=True
        ).to_conf()
    }
    host = TableHost(servers)
    qtbot.addWidget(host)
    table = LSPServerTable(host)

    table.selectRow(0)
    assert host.delete_btn.isEnabled()
