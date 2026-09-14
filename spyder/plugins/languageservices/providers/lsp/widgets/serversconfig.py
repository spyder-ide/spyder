# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Table and editor of the language servers run by the LSP provider."""

from __future__ import annotations

# Standard library imports
import json
import re

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt, Slot
from qtpy.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableView,
    QVBoxLayout,
)

# Local imports
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.providers.lsp.config import (
    AUTO_LANGUAGES,
    ServerConfig,
)
from spyder.utils.misc import check_connection_port
from spyder.utils.palette import SpyderPalette
from spyder.utils.programs import find_program
from spyder.widgets.helperwidgets import ItemDelegate
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


def language_names(config: ServerConfig) -> str:
    """Display text of the languages a server is configured for."""
    if config.auto_languages:
        return _("auto")
    names = []
    for language_id in config.languages:
        language = Language.find(language_id=language_id)
        names.append(language.name if language else language_id)
    return ", ".join(names)


def parse_languages(text: str) -> tuple[str, ...] | str:
    """``languages`` field from the editor text (names or ids, comma
    separated). Empty or "auto" means auto-detection."""
    text = text.strip()
    if not text or text.lower() == AUTO_LANGUAGES:
        return AUTO_LANGUAGES
    ids = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        language = Language.find(name=part)
        if language is None:
            try:
                Language.from_language_id(part)
            except LookupError:
                raise ValueError(_("Unknown language: {0}").format(part))
            ids.append(part)
        else:
            ids.append(language.language_id)
    return tuple(ids)


class LSPServerEditor(SpyderFontsMixin, QDialog):
    """Dialog editing one :class:`ServerConfig`."""

    HOST_REGEX = re.compile(r"^\w+([.]\w+)*$")
    NAME_REGEX = re.compile(r"^[\w.-]+$")
    NON_EMPTY_REGEX = re.compile(r"^\S+$")
    JSON_VALID = _("Valid JSON")
    JSON_INVALID = _("Invalid JSON")
    MIN_SIZE = QSize(850, 600)
    INVALID_CSS = "QLineEdit {border: 1px solid red;}"
    VALID_CSS = "QLineEdit {border: 1px solid green;}"

    def __init__(self, parent, config: ServerConfig | None, get_option):
        super().__init__(parent)
        self.parent = parent
        self.existing_names = {
            name for name in parent.server_names() if config is None or name != config.name
        }
        config = config or ServerConfig(name="")
        self.config = config

        description = _(
            "A server is started with a command and arguments, or reached "
            "at a host and port when it is external. List the languages it "
            "serves (names or LSP ids, comma separated) or leave the field "
            "empty to detect them from the server registrations."
            "<br><br>"
            "<i>Note</i>: <tt>{host}</tt> and <tt>{port}</tt> in the "
            "arguments are replaced by the address the server must bind."
        )

        self.description = QLabel(description)
        self.description.setWordWrap(True)
        self.name_input = QLineEdit(config.name, self)
        self.languages_input = QLineEdit(
            "" if config.auto_languages else language_names(config), self
        )
        self.external_cb = QCheckBox(_("External server"), self)
        self.stdio_cb = QCheckBox(_("Use stdio pipes for communication"), self)
        self.host_input = QLineEdit(config.host, self)
        self.port_spinner = QSpinBox(self)
        self.cmd_input = QLineEdit(config.cmd, self)
        self.args_input = QLineEdit(config.args, self)
        self.json_label = QLabel(self.JSON_VALID, self)
        self.conf_input = SimpleCodeEditor(None)

        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)

        self.setMinimumSize(self.MIN_SIZE)
        self.setWindowTitle(_("LSP server editor"))
        self.name_input.setPlaceholderText(_("Unique server name"))
        self.languages_input.setPlaceholderText(_("e.g. Rust, Go (empty: auto)"))
        self.host_input.setPlaceholderText("127.0.0.1")
        self.port_spinner.setRange(1, 65535)
        self.port_spinner.setValue(config.port)
        self.cmd_input.setPlaceholderText("/absolute/path/to/command")
        self.args_input.setPlaceholderText(r"--host {host} --port {port}")
        self.external_cb.setChecked(config.external)
        self.stdio_cb.setChecked(config.stdio)
        self.conf_input.setup_editor(
            language="json",
            color_scheme=get_option("selected", section="appearance"),
            wrap=False,
            highlight_current_line=True,
            font=self.get_font(SpyderFontType.MonospaceInterface),
        )
        self.conf_input.set_language("json")
        self.conf_input.set_text(
            json.dumps(config.configurations, indent=4, sort_keys=True)
        )

        form = QGridLayout()
        form.addWidget(QLabel(_("Name:")), 0, 0)
        form.addWidget(self.name_input, 0, 1)
        form.addWidget(QLabel(_("Languages:")), 1, 0)
        form.addWidget(self.languages_input, 1, 1)
        form.addWidget(QLabel(_("Command:")), 2, 0)
        form.addWidget(self.cmd_input, 2, 1)
        form.addWidget(QLabel(_("Arguments:")), 3, 0)
        form.addWidget(self.args_input, 3, 1)
        form.addWidget(QLabel(_("Host:")), 4, 0)
        form.addWidget(self.host_input, 4, 1)
        form.addWidget(QLabel(_("Port:")), 5, 0)
        form.addWidget(self.port_spinner, 5, 1)
        server_group = QGroupBox(_("Language server"))
        server_group.setLayout(form)

        advanced_group = QGroupBox(_("Advanced"))
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(self.external_cb)
        advanced_layout.addWidget(self.stdio_cb)
        advanced_group.setLayout(advanced_layout)

        left = QVBoxLayout()
        left.addWidget(server_group)
        left.addWidget(advanced_group)
        left.addStretch()

        right = QVBoxLayout()
        right.addWidget(QLabel(_("<b>Server configuration:</b>")))
        right.addWidget(self.conf_input)
        right.addWidget(self.json_label)

        columns = QHBoxLayout()
        columns.addLayout(left, 2)
        columns.addLayout(right, 3)

        layout = QVBoxLayout()
        layout.addWidget(self.description)
        layout.addLayout(columns)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        for widget in (self.name_input, self.languages_input, self.host_input,
                       self.cmd_input):
            widget.textChanged.connect(lambda _text: self.validate())
        self.port_spinner.valueChanged.connect(lambda _value: self.validate())
        self.conf_input.textChanged.connect(self.validate)
        self.external_cb.toggled.connect(self._update_mode)
        self.stdio_cb.toggled.connect(self._update_mode)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        self._update_mode()

    @Slot()
    def _update_mode(self):
        external = self.external_cb.isChecked()
        stdio = self.stdio_cb.isChecked()
        self.stdio_cb.setEnabled(not external)
        self.external_cb.setEnabled(not stdio)
        self.cmd_input.setEnabled(not external)
        self.args_input.setEnabled(not external)
        self.host_input.setEnabled(not stdio)
        self.port_spinner.setEnabled(not stdio)
        self.validate()

    @Slot()
    def validate(self):
        valid = True

        name = self.name_input.text().strip()
        if not self.NAME_REGEX.match(name) or name in self.existing_names:
            self.name_input.setStyleSheet(self.INVALID_CSS)
            self.name_input.setToolTip(_("Name must be unique and non empty"))
            valid = False
        else:
            self.name_input.setStyleSheet(self.VALID_CSS)
            self.name_input.setToolTip("")

        try:
            parse_languages(self.languages_input.text())
            self.languages_input.setStyleSheet(self.VALID_CSS)
            self.languages_input.setToolTip("")
        except ValueError as exc:
            self.languages_input.setStyleSheet(self.INVALID_CSS)
            self.languages_input.setToolTip(str(exc))
            valid = False

        host = self.host_input.text()
        if not self.stdio_cb.isChecked():
            if host not in ("127.0.0.1", "localhost"):
                self.external_cb.setChecked(True)
            if not self.HOST_REGEX.match(host):
                self.host_input.setStyleSheet(self.INVALID_CSS)
                self.host_input.setToolTip(_("Hostname must be valid"))
                valid = False
            else:
                self.host_input.setStyleSheet(self.VALID_CSS)
                self.host_input.setToolTip("")

        if self.external_cb.isChecked():
            if not check_connection_port(host, self.port_spinner.value()):
                self.host_input.setToolTip(
                    _("No server is listening at this address")
                )
                valid = False
        else:
            cmd = self.cmd_input.text()
            if not self.NON_EMPTY_REGEX.match(cmd) or find_program(cmd) is None:
                self.cmd_input.setStyleSheet(self.INVALID_CSS)
                self.cmd_input.setToolTip(_("Program was not found on your system"))
                valid = False
            else:
                self.cmd_input.setStyleSheet(self.VALID_CSS)
                self.cmd_input.setToolTip(_("Program was found on your system"))

        try:
            json.loads(self.conf_input.toPlainText())
            self.json_label.setText(self.JSON_VALID)
        except ValueError:
            self.json_label.setText(self.JSON_INVALID)
            valid = False

        self.button_ok.setEnabled(valid)

    def get_config(self) -> ServerConfig:
        return ServerConfig(
            name=self.name_input.text().strip(),
            cmd=self.cmd_input.text(),
            args=self.args_input.text(),
            host=self.host_input.text(),
            port=self.port_spinner.value(),
            external=self.external_cb.isChecked(),
            stdio=self.stdio_cb.isChecked(),
            languages=parse_languages(self.languages_input.text()),
            configurations=json.loads(self.conf_input.toPlainText()),
        )


NAME, LANGUAGES, ADDR, CMD = range(4)


class LSPServersModel(QAbstractTableModel):
    def __init__(self, parent):
        super().__init__(parent)
        self.servers: list[ServerConfig] = []
        self.text_color = SpyderPalette.COLOR_TEXT_1

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.servers)):
            return to_qvariant()
        server = self.servers[row]
        column = index.column()
        if role == Qt.DisplayRole:
            if column == NAME:
                return to_qvariant(server.name)
            if column == LANGUAGES:
                return to_qvariant(language_names(server))
            if column == ADDR:
                if server.stdio:
                    return to_qvariant(_("stdio"))
                return to_qvariant(f"{server.host}:{server.port}")
            if column == CMD:
                if server.external:
                    return to_qvariant("&nbsp;<tt>" + _("External server") + "</tt>")
                text = '&nbsp;<tt style="color:{0}">{1} {2}</tt>'
                return to_qvariant(
                    text.format(self.text_color, server.cmd, server.args)
                )
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return to_qvariant()
        if orientation == Qt.Horizontal:
            return to_qvariant(
                {
                    NAME: _("Name"),
                    LANGUAGES: _("Languages"),
                    ADDR: _("Address"),
                    CMD: _("Command to execute"),
                }[section]
            )
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.servers)

    def columnCount(self, index=QModelIndex()):
        return 4

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class LSPServerTable(QTableView):
    """Servers stored in the provider's ``servers`` option."""

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.source_model = LSPServersModel(self)
        self.setModel(self.source_model)
        self.setItemDelegateForColumn(CMD, ItemDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)
        self.verticalHeader().hide()
        self.load_servers()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def selection(self, index):
        self.update()
        self._parent.delete_btn.setEnabled(True)

    def adjust_cells(self):
        self.resizeColumnsToContents()
        self.horizontalHeader().setStretchLastSection(True)

    def server_names(self) -> list[str]:
        return [server.name for server in self.source_model.servers]

    def load_servers(self):
        stored = self._parent.get_option("servers", default={}) or {}
        self.source_model.servers = [
            ServerConfig.from_conf(name, dict(data))
            for name, data in sorted(stored.items())
        ]
        self.source_model.reset()
        self.adjust_cells()

    def save_servers(self) -> set:
        """Write the servers to the configuration and return the options set."""
        self._parent.set_option(
            "servers",
            {server.name: server.to_conf() for server in self.source_model.servers},
        )
        return {"servers"}

    def delete_server(self, idx):
        if 0 <= idx < len(self.source_model.servers):
            self.source_model.servers.pop(idx)
            self.source_model.reset()
            self.adjust_cells()

    def clear_servers(self):
        self.source_model.servers = []
        self.source_model.reset()

    def show_editor(self, new_server=False):
        config = None
        if not new_server:
            idx = self.currentIndex().row()
            if not (0 <= idx < len(self.source_model.servers)):
                return
            config = self.source_model.servers[idx]
        dialog = LSPServerEditor(self, config, self._parent.get_option)
        if dialog.exec_():
            new_config = dialog.get_config()
            servers = [s for s in self.source_model.servers if s is not config]
            servers.append(new_config)
            self.source_model.servers = sorted(servers, key=lambda s: s.name)
            self.source_model.reset()
            self.adjust_cells()
            self._parent.set_modified(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.show_editor()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.show_editor()
