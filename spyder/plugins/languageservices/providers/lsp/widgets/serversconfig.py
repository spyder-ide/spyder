# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language servers configuration widgets.
"""

from __future__ import annotations

# Standard library imports
import json
import re

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import (Qt, Slot, QAbstractTableModel, QModelIndex,
                         QSize)
from qtpy.QtWidgets import (QAbstractItemView, QCheckBox,
                            QDialog, QDialogButtonBox, QGroupBox,
                            QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QSpinBox,
                            QTableView, QVBoxLayout)

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


def language_choices(selected=()) -> list[tuple[str, str, tuple[str, ...]]]:
    """``(language_id, display name, extensions)`` of every LSP language id
    known to Spyder and of each id in ``selected``, sorted by name."""
    extensions: dict[str, list[str]] = {}
    for language in Language:
        extensions.setdefault(language.language_id, []).extend(
            language.extensions)
    for language_id in selected:
        extensions.setdefault(language_id, [])
    choices = []
    for language_id, exts in extensions.items():
        language = Language.find(language_id=language_id)
        name = language.name if language else language_id
        choices.append((language_id, name, tuple(exts)))
    return sorted(choices, key=lambda choice: choice[1].lower())


class LSPServerEditor(SpyderFontsMixin, QDialog):
    HOST_REGEX = re.compile(r'^\w+([.]\w+)*$')
    NAME_REGEX = re.compile(r'^[\w.-]+$')
    NON_EMPTY_REGEX = re.compile(r'^\S+$')
    JSON_VALID = _('Valid JSON')
    JSON_INVALID = _('Invalid JSON')
    MIN_SIZE = QSize(850, 600)
    INVALID_CSS = "QLineEdit {border: 1px solid red;}"
    INVALID_LIST_CSS = "QListWidget {border: 1px solid red;}"
    VALID_CSS = "QLineEdit {border: 1px solid green;}"

    def __init__(self, parent, config: ServerConfig | None, get_option):
        super().__init__(parent)
        new_server = config is None
        if new_server:
            config = ServerConfig(name="untitled")
        self.existing_names = {
            name for name in parent.server_names()
            if new_server or name != config.name
        }

        description = _(
            "To create a new server configuration, you need to select a "
            "language or leave as 'auto', set the command to start its associated "
            "server and enter any arguments that should be passed to it on "
            "startup. Additionally, you can set the server's hostname and "
            "port if connecting to an external server, "
            "or to a local one using TCP instead of stdio pipes."
            "<br><br>"
            "<i>Note</i>: You can use the placeholders <tt>{host}</tt> and "
            "<tt>{port}</tt> in the server arguments field to automatically "
            "fill in the respective values.<br>"
        )
        self.parent = parent
        self.config = config
        self.external = config.external
        self.get_option = get_option

        # Widgets
        self.server_settings_description = QLabel(description)
        self.auto_languages_cb = QCheckBox(
            _('Auto (detect from the server)'), self)
        self.languages_filter = QLineEdit(self)
        self.languages_list = QListWidget(self)
        self.external_cb = QCheckBox(_('External server'), self)
        self.host_label = QLabel(_('Host:'))
        self.host_input = QLineEdit(self)
        self.port_label = QLabel(_('Port:'))
        self.port_spinner = QSpinBox(self)
        self.name_label = QLabel(_('Name:'))
        self.name_input = QLineEdit(self)
        self.cmd_label = QLabel(_('Command:'))
        self.cmd_input = QLineEdit(self)
        self.args_label = QLabel(_('Arguments:'))
        self.args_input = QLineEdit(self)
        self.json_label = QLabel(self.JSON_VALID, self)
        self.conf_label = QLabel(_('<b>Server Configuration:</b>'))
        self.conf_input = SimpleCodeEditor(None)

        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        # Widget setup
        self.setMinimumSize(self.MIN_SIZE)
        self.setWindowTitle(_('LSP server editor'))

        self.server_settings_description.setWordWrap(True)

        self.auto_languages_cb.setToolTip(
            _('Start the server with Spyder and use it for the languages '
              'it registers'))
        self.auto_languages_cb.setChecked(config.auto_languages)
        self.languages_filter.setPlaceholderText(_('Filter languages'))
        self.languages_filter.setClearButtonEnabled(True)
        self.languages_list.setToolTip(
            _('Programming languages provided by the LSP server'))
        self.languages_list.setMinimumHeight(
            6 * self.languages_list.fontMetrics().height())
        selected = () if config.auto_languages else config.languages
        choices = sorted(language_choices(selected),
                         key=lambda choice: choice[0] not in selected)
        for language_id, name, extensions in choices:
            item = QListWidgetItem(name, self.languages_list)
            item.setData(Qt.UserRole, language_id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if language_id in selected else Qt.Unchecked)
            if extensions:
                item.setToolTip(
                    ', '.join('.' + extension for extension in extensions))
        self.update_languages_state()
        self.auto_languages_cb.toggled.connect(
            lambda _: self.update_languages_state())
        self.auto_languages_cb.toggled.connect(lambda _: self.validate())
        self.languages_filter.textChanged.connect(self.filter_languages)
        self.languages_list.itemChanged.connect(lambda _: self.validate())

        self.name_input.setPlaceholderText(_('Unique server name'))
        if not new_server:
            self.name_input.setText(config.name)
        self.name_input.textChanged.connect(lambda _: self.validate())

        self.host_input.setPlaceholderText('127.0.0.1')
        self.host_input.setText(config.host)
        self.host_input.textChanged.connect(lambda _: self.validate())

        self.port_spinner.setToolTip(_('TCP port number of the server'))
        self.port_spinner.setMinimum(1)
        self.port_spinner.setMaximum(60000)
        self.port_spinner.setValue(config.port)
        self.port_spinner.valueChanged.connect(lambda _: self.validate())

        self.cmd_input.setText(config.cmd)
        self.cmd_input.setPlaceholderText('/absolute/path/to/command')

        self.args_input.setToolTip(
            _('Additional arguments required to start the server'))
        self.args_input.setText(config.args)
        self.args_input.setPlaceholderText(r'--host {host} --port {port}')

        self.conf_input.setup_editor(
            language='json',
            color_scheme=get_option('selected', section='appearance'),
            wrap=False,
            highlight_current_line=True,
            font=self.get_font(SpyderFontType.MonospaceInterface)
        )
        self.conf_input.set_language('json')
        self.conf_input.setToolTip(_('Additional LSP server configuration '
                                     'set at runtime. JSON required'))
        try:
            conf_text = json.dumps(
                config.configurations, indent=4, sort_keys=True)
        except Exception:
            conf_text = '{}'
        self.conf_input.set_text(conf_text)

        self.external_cb.setToolTip(
            _('Check if the server runs on a remote location'))
        self.external_cb.setChecked(config.external)

        self.stdio_cb = QCheckBox(_('Use stdio pipes for communication'), self)
        self.stdio_cb.setToolTip(_('Check if the server communicates '
                                   'using stdin/out pipes'))
        self.stdio_cb.setChecked(config.stdio)

        # Layout setup
        hlayout = QHBoxLayout()
        general_vlayout = QVBoxLayout()
        general_vlayout.addWidget(self.server_settings_description)

        vlayout = QVBoxLayout()

        lang_group = QGroupBox(_('Languages'))
        lang_layout = QVBoxLayout()
        lang_layout.addWidget(self.auto_languages_cb)
        lang_layout.addWidget(self.languages_filter)
        lang_layout.addWidget(self.languages_list)
        lang_group.setLayout(lang_layout)

        server_group = QGroupBox(_('Language server'))
        server_layout = QGridLayout()
        server_layout.addWidget(self.name_label, 0, 0)
        server_layout.addWidget(self.name_input, 0, 1)
        server_layout.addWidget(self.cmd_label, 1, 0)
        server_layout.addWidget(self.cmd_input, 1, 1)
        server_layout.addWidget(self.args_label, 2, 0)
        server_layout.addWidget(self.args_input, 2, 1)
        server_group.setLayout(server_layout)
        vlayout.addWidget(server_group)

        address_group = QGroupBox(_('Server address'))
        host_layout = QVBoxLayout()
        host_layout.addWidget(self.host_label)
        host_layout.addWidget(self.host_input)

        port_layout = QVBoxLayout()
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_spinner)

        conn_info_layout = QHBoxLayout()
        conn_info_layout.addLayout(host_layout)
        conn_info_layout.addLayout(port_layout)
        address_group.setLayout(conn_info_layout)
        vlayout.addWidget(address_group)

        advanced_group = QGroupBox(_('Advanced'))
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(self.external_cb)
        advanced_layout.addWidget(self.stdio_cb)
        advanced_group.setLayout(advanced_layout)
        vlayout.addWidget(advanced_group)

        conf_layout = QVBoxLayout()
        conf_layout.addWidget(lang_group, 2)
        conf_layout.addWidget(self.conf_label)
        conf_layout.addWidget(self.conf_input, 3)
        conf_layout.addWidget(self.json_label)

        vlayout.addStretch()
        hlayout.addLayout(vlayout, 2)
        hlayout.addLayout(conf_layout, 3)
        general_vlayout.addLayout(hlayout)

        general_vlayout.addWidget(self.bbox)
        self.setLayout(general_vlayout)

        # Signals
        if not config.external:
            self.cmd_input.textChanged.connect(lambda x: self.validate())
        self.external_cb.stateChanged.connect(self.set_local_options)
        self.stdio_cb.stateChanged.connect(self.set_stdio_options)
        self.conf_input.textChanged.connect(self.validate)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Final setup
        self.validate()
        if config.stdio:
            self.set_stdio_options(True)
        if config.external:
            self.set_local_options(True)

    @Slot()
    def validate(self):
        host_text = self.host_input.text()
        cmd_text = self.cmd_input.text()
        name_text = self.name_input.text().strip()

        names_valid = True
        if (not self.NAME_REGEX.match(name_text)
                or name_text in self.existing_names):
            names_valid = False
            self.name_input.setStyleSheet(self.INVALID_CSS)
            self.name_input.setToolTip(_('Name must be unique and non empty'))
        else:
            self.name_input.setStyleSheet(self.VALID_CSS)
            self.name_input.setToolTip('')

        if (not self.auto_languages_cb.isChecked()
                and not self.selected_languages()):
            names_valid = False
            self.languages_list.setStyleSheet(self.INVALID_LIST_CSS)
        else:
            self.languages_list.setStyleSheet('')

        if host_text not in ['127.0.0.1', 'localhost']:
            self.external = True
            self.external_cb.setChecked(True)

        if not self.HOST_REGEX.match(host_text):
            self.button_ok.setEnabled(False)
            self.host_input.setStyleSheet(self.INVALID_CSS)
            if bool(host_text):
                self.host_input.setToolTip(_('Hostname must be valid'))
            else:
                self.host_input.setToolTip(
                    _('Hostname or IP address of the host on which the server '
                      'is running. Must be non empty.'))
        else:
            self.host_input.setStyleSheet(self.VALID_CSS)
            self.host_input.setToolTip(_('Hostname is valid'))
            self.button_ok.setEnabled(True)

        if not self.external:
            if not self.NON_EMPTY_REGEX.match(cmd_text):
                self.button_ok.setEnabled(False)
                self.cmd_input.setStyleSheet(self.INVALID_CSS)
                self.cmd_input.setToolTip(
                    _('Command used to start the LSP server locally. Must be '
                      'non empty'))
                return

            if find_program(cmd_text) is None:
                self.button_ok.setEnabled(False)
                self.cmd_input.setStyleSheet(self.INVALID_CSS)
                self.cmd_input.setToolTip(_('Program was not found '
                                            'on your system'))
            else:
                self.cmd_input.setStyleSheet(self.VALID_CSS)
                self.cmd_input.setToolTip(_('Program was found on your '
                                            'system'))
                self.button_ok.setEnabled(True)
        else:
            port = int(self.port_spinner.text())
            response = check_connection_port(host_text, port)
            if not response:
                self.button_ok.setEnabled(False)

        try:
            json.loads(self.conf_input.toPlainText())
            try:
                self.json_label.setText(self.JSON_VALID)
            except Exception:
                pass
        except ValueError:
            try:
                self.json_label.setText(self.JSON_INVALID)
                self.button_ok.setEnabled(False)
            except Exception:
                pass

        if not names_valid:
            self.button_ok.setEnabled(False)

    @Slot(bool)
    @Slot(int)
    def set_local_options(self, enabled):
        self.external = enabled
        self.cmd_input.setEnabled(True)
        self.args_input.setEnabled(True)
        if enabled:
            self.cmd_input.setEnabled(False)
            self.cmd_input.setStyleSheet('')
            self.args_input.setEnabled(False)
            self.stdio_cb.stateChanged.disconnect()
            self.stdio_cb.setChecked(False)
            self.stdio_cb.setEnabled(False)
        else:
            self.cmd_input.setEnabled(True)
            self.args_input.setEnabled(True)
            self.stdio_cb.setEnabled(True)
            self.stdio_cb.setChecked(False)
            self.stdio_cb.stateChanged.connect(self.set_stdio_options)
        try:
            self.validate()
        except Exception:
            pass

    @Slot(bool)
    @Slot(int)
    def set_stdio_options(self, enabled):
        self.stdio = enabled
        if enabled:
            self.cmd_input.setEnabled(True)
            self.args_input.setEnabled(True)
            self.external_cb.stateChanged.disconnect()
            self.external_cb.setChecked(False)
            self.external_cb.setEnabled(False)
            self.host_input.setStyleSheet('')
            self.host_input.setEnabled(False)
            self.port_spinner.setEnabled(False)
        else:
            self.cmd_input.setEnabled(True)
            self.args_input.setEnabled(True)
            self.external_cb.setChecked(False)
            self.external_cb.setEnabled(True)
            self.external_cb.stateChanged.connect(self.set_local_options)
            self.host_input.setEnabled(True)
            self.port_spinner.setEnabled(True)
        try:
            self.validate()
        except Exception:
            pass

    def selected_languages(self) -> tuple[str, ...]:
        """Language ids checked in the list."""
        items = (self.languages_list.item(row)
                 for row in range(self.languages_list.count()))
        return tuple(item.data(Qt.UserRole) for item in items
                     if item.checkState() == Qt.Checked)

    @Slot()
    def update_languages_state(self):
        auto = self.auto_languages_cb.isChecked()
        self.languages_filter.setEnabled(not auto)
        self.languages_list.setEnabled(not auto)

    @Slot(str)
    def filter_languages(self, text):
        text = text.strip().lower()
        for row in range(self.languages_list.count()):
            item = self.languages_list.item(row)
            haystack = ' '.join((item.text(), item.data(Qt.UserRole),
                                 item.toolTip())).lower()
            item.setHidden(text not in haystack)

    def get_options(self):
        return self.config.with_changes(
            name=self.name_input.text().strip(),
            languages=(AUTO_LANGUAGES if self.auto_languages_cb.isChecked()
                       else self.selected_languages()),
            cmd=self.cmd_input.text(),
            args=self.args_input.text(),
            host=self.host_input.text(),
            port=int(self.port_spinner.value()),
            external=self.external_cb.isChecked(),
            stdio=self.stdio_cb.isChecked(),
            configurations=json.loads(self.conf_input.toPlainText()),
        )


NAME, LANGUAGES, ADDR, CMD = [0, 1, 2, 3]


class LSPServersModel(QAbstractTableModel):
    def __init__(self, parent):
        QAbstractTableModel.__init__(self)
        self._parent = parent

        self.servers = []
        self.server_map = {}
        # self.scores = []
        self.rich_text = []
        self.normal_text = []
        self.letters = ''
        self.label = QLabel()
        self.widths = []

        # Needed to compensate for the HTMLDelegate color selection unawareness
        self.text_color = SpyderPalette.COLOR_TEXT_1

    def sortByName(self):
        """Qt Override."""
        self.servers = sorted(self.servers, key=lambda x: x.name)
        self.reset()

    def flags(self, index):
        """Qt Override."""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        """Qt Override."""
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.servers)):
            return to_qvariant()

        server = self.servers[row]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == NAME:
                return to_qvariant(server.name)
            elif column == LANGUAGES:
                return to_qvariant(language_names(server))
            elif column == ADDR:
                text = '{0}:{1}'.format(server.host, server.port)
                return to_qvariant(text)
            elif column == CMD:
                text = '&nbsp;<tt style="color:{0}">{{0}} {{1}}</tt>'
                text = text.format(self.text_color)
                if server.external:
                    text = '&nbsp;<tt>External server</tt>'
                return to_qvariant(text.format(server.cmd, server.args))
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Qt Override."""
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return to_qvariant()
        if orientation == Qt.Horizontal:
            if section == NAME:
                return to_qvariant(_("Name"))
            elif section == LANGUAGES:
                return to_qvariant(_("Languages"))
            elif section == ADDR:
                return to_qvariant(_("Address"))
            elif section == CMD:
                return to_qvariant(_("Command to execute"))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        """Qt Override."""
        return len(self.servers)

    def columnCount(self, index=QModelIndex()):
        """Qt Override."""
        return 4

    def row(self, row_num):
        """Get row based on model index. Needed for the custom proxy model."""
        return self.servers[row_num]

    def reset(self):
        """"Reset model to take into account new search letters."""
        self.beginResetModel()
        self.endResetModel()


class LSPServerTable(QTableView):
    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self._parent = parent
        self.source_model = LSPServersModel(self)
        self.setModel(self.source_model)
        self.setItemDelegateForColumn(CMD, ItemDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)
        self.verticalHeader().hide()

        self.load_servers()

    def focusOutEvent(self, e):
        """Qt Override."""
        # self.source_model.update_active_row()
        # self._parent.delete_btn.setEnabled(False)
        super().focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super().focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def selection(self, index):
        """Update selected row."""
        self.update()
        self.isActiveWindow()
        self._parent.delete_btn.setEnabled(True)

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(s.cmd) for s in self.source_model.servers]
        if names:
            self.setColumnWidth(CMD, max(names))
        self.horizontalHeader().setStretchLastSection(True)

    def server_names(self):
        return list(self.source_model.server_map)

    def load_servers(self):
        stored = self._parent.get_option('servers', default={}) or {}
        servers = [
            ServerConfig.from_conf(name, dict(data))
            for name, data in sorted(stored.items())
        ]
        server_map = {x.name: x for x in servers}
        self.source_model.servers = servers
        self.source_model.server_map = server_map
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(NAME, Qt.AscendingOrder)

    def save_servers(self):
        self._parent.set_option(
            'servers',
            {server.name: server.to_conf()
             for server in self.source_model.servers})
        return {'servers'}

    def delete_server(self, idx):
        server = self.source_model.servers.pop(idx)
        self.source_model.server_map.pop(server.name)
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(NAME, Qt.AscendingOrder)

    def clear_servers(self):
        self.source_model.servers = []
        self.source_model.server_map = {}
        self.source_model.reset()

    def show_editor(self, new_server=False):
        config = None
        if not new_server:
            idx = self.currentIndex().row()
            if not (0 <= idx < len(self.source_model.servers)):
                return
            config = self.source_model.row(idx)
        dialog = LSPServerEditor(self, config, self._parent.get_option)
        if dialog.exec_():
            server = dialog.get_options()
            if config is not None:
                self.source_model.server_map.pop(config.name)
            self.source_model.server_map[server.name] = server
            self.source_model.servers = list(
                self.source_model.server_map.values())
            self.source_model.reset()
            self.adjust_cells()
            self.sortByColumn(NAME, Qt.AscendingOrder)
            self._parent.set_modified(True)

    def next_row(self):
        """Move to next row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.source_model.rowCount()
        if row + 1 == rows:
            row = -1
        self.selectRow(row + 1)

    def previous_row(self):
        """Move to previous row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.source_model.rowCount()
        if row == 0:
            row = rows
        self.selectRow(row - 1)

    def keyPressEvent(self, event):
        """Qt Override."""
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            self.show_editor()
        elif key in [Qt.Key_Backtab]:
            self.parent().reset_btn.setFocus()
        elif key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Qt Override."""
        self.show_editor()
