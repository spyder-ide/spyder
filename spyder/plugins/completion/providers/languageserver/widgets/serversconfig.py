# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language servers configuration widgets.
"""

# Standard library imports
import json
import re

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import (Qt, Slot, QAbstractTableModel, QModelIndex,
                         QSize)
from qtpy.QtWidgets import (QAbstractItemView, QCheckBox,
                            QComboBox, QDialog, QDialogButtonBox, QGroupBox,
                            QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                            QSpinBox, QTableView, QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.plugins.completion.api import SUPPORTED_LANGUAGES
from spyder.utils.misc import check_connection_port
from spyder.utils.programs import find_program
from spyder.widgets.helperwidgets import ItemDelegate
from spyder.widgets.simplecodeeditor import SimpleCodeEditor

LSP_LANGUAGE_NAME = {x.lower(): x for x in SUPPORTED_LANGUAGES}
LANGUAGE_SET = {lang.lower() for lang in SUPPORTED_LANGUAGES}


def iter_servers(get_option, set_option, remove_option):
    for language in LANGUAGE_SET:
        conf = get_option(language, default=None)
        if conf is not None:
            server = LSPServer(language=language,
                               set_option=set_option,
                               get_option=get_option,
                               remove_option=remove_option)
            server.load()
            yield server


class LSPServer(object):
    """Convenience class to store LSP Server configuration values."""

    def __init__(self, language=None, cmd='', host='127.0.0.1',
                 port=2084, args='', external=False, stdio=False,
                 configurations={}, set_option=None, get_option=None,
                 remove_option=None):
        self.index = 0
        self.language = language
        if self.language in LSP_LANGUAGE_NAME:
            self.language = LSP_LANGUAGE_NAME[self.language]
        self.cmd = cmd
        self.args = args
        self.configurations = configurations
        self.port = port
        self.host = host
        self.external = external
        self.stdio = stdio
        self.set_option = set_option
        self.get_option = get_option
        self.remove_option = remove_option

    def __repr__(self):
        base_str = '[{0}] {1} {2} ({3}:{4})'
        fmt_args = [self.language, self.cmd, self.args,
                    self.host, self.port]
        if self.stdio:
            base_str = '[{0}] {1} {2}'
            fmt_args = [self.language, self.cmd, self.args]
        if self.external:
            base_str = '[{0}] {1}:{2}'
            fmt_args = [self.language, self.host, self.port]
        return base_str.format(*fmt_args)

    def __str__(self):
        return self.__repr__()

    def __unicode__(self):
        return self.__repr__()

    def load(self):
        if self.language is not None:
            state = self.get_option(self.language.lower())
            self.__dict__.update(state)

    def save(self):
        if self.language is not None:
            language = self.language.lower()
            dict_repr = dict(self.__dict__)
            dict_repr.pop('set_option')
            dict_repr.pop('get_option')
            dict_repr.pop('remove_option')
            self.set_option(language, dict_repr,
                            recursive_notification=False)

    def delete(self):
        if self.language is not None:
            language = self.language.lower()
            self.remove_option(language)


class LSPServerEditor(QDialog):
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 2084
    DEFAULT_CMD = ''
    DEFAULT_ARGS = ''
    DEFAULT_CONFIGURATION = '{}'
    DEFAULT_EXTERNAL = False
    DEFAULT_STDIO = False
    HOST_REGEX = re.compile(r'^\w+([.]\w+)*$')
    NON_EMPTY_REGEX = re.compile(r'^\S+$')
    JSON_VALID = _('Valid JSON')
    JSON_INVALID = _('Invalid JSON')
    MIN_SIZE = QSize(850, 600)
    INVALID_CSS = "QLineEdit {border: 1px solid red;}"
    VALID_CSS = "QLineEdit {border: 1px solid green;}"

    def __init__(self, parent, language=None, cmd='', host='127.0.0.1',
                 port=2084, args='', external=False, stdio=False,
                 configurations={}, get_option=None, set_option=None,
                 remove_option=None, **kwargs):
        super(LSPServerEditor, self).__init__(parent)

        description = _(
            "To create a new server configuration, you need to select a "
            "programming language, set the command to start its associated "
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
        self.external = external
        self.set_option = set_option
        self.get_option = get_option
        self.remove_option = remove_option

        # Widgets
        self.server_settings_description = QLabel(description)
        self.lang_cb = QComboBox(self)
        self.external_cb = QCheckBox(_('External server'), self)
        self.host_label = QLabel(_('Host:'))
        self.host_input = QLineEdit(self)
        self.port_label = QLabel(_('Port:'))
        self.port_spinner = QSpinBox(self)
        self.cmd_label = QLabel(_('Command:'))
        self.cmd_input = QLineEdit(self)
        self.args_label = QLabel(_('Arguments:'))
        self.args_input = QLineEdit(self)
        self.json_label = QLabel(self.JSON_VALID, self)
        self.conf_label = QLabel(_('<b>Server Configuration:</b>'))
        self.conf_input = SimpleCodeEditor(None)

        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        # Widget setup
        self.setMinimumSize(self.MIN_SIZE)
        self.setWindowTitle(_('LSP server editor'))

        self.server_settings_description.setWordWrap(True)

        self.lang_cb.setToolTip(
            _('Programming language provided by the LSP server'))
        self.lang_cb.addItem(_('Select a language'))
        self.lang_cb.addItems(SUPPORTED_LANGUAGES)

        self.button_ok.setEnabled(False)
        if language is not None:
            idx = SUPPORTED_LANGUAGES.index(language)
            self.lang_cb.setCurrentIndex(idx + 1)
            self.button_ok.setEnabled(True)

        self.host_input.setPlaceholderText('127.0.0.1')
        self.host_input.setText(host)
        self.host_input.textChanged.connect(lambda _: self.validate())

        self.port_spinner.setToolTip(_('TCP port number of the server'))
        self.port_spinner.setMinimum(1)
        self.port_spinner.setMaximum(60000)
        self.port_spinner.setValue(port)
        self.port_spinner.valueChanged.connect(lambda _: self.validate())

        self.cmd_input.setText(cmd)
        self.cmd_input.setPlaceholderText('/absolute/path/to/command')

        self.args_input.setToolTip(
            _('Additional arguments required to start the server'))
        self.args_input.setText(args)
        self.args_input.setPlaceholderText(r'--host {host} --port {port}')

        self.conf_input.setup_editor(
            language='json',
            color_scheme=get_option('selected', section='appearance'),
            wrap=False,
            highlight_current_line=True,
            font=get_font()
        )
        self.conf_input.set_language('json')
        self.conf_input.setToolTip(_('Additional LSP server configuration '
                                     'set at runtime. JSON required'))
        try:
            conf_text = json.dumps(configurations, indent=4, sort_keys=True)
        except Exception:
            conf_text = '{}'
        self.conf_input.set_text(conf_text)

        self.external_cb.setToolTip(
            _('Check if the server runs on a remote location'))
        self.external_cb.setChecked(external)

        self.stdio_cb = QCheckBox(_('Use stdio pipes for communication'), self)
        self.stdio_cb.setToolTip(_('Check if the server communicates '
                                   'using stdin/out pipes'))
        self.stdio_cb.setChecked(stdio)

        # Layout setup
        hlayout = QHBoxLayout()
        general_vlayout = QVBoxLayout()
        general_vlayout.addWidget(self.server_settings_description)

        vlayout = QVBoxLayout()

        lang_group = QGroupBox(_('Language'))
        lang_layout = QVBoxLayout()
        lang_layout.addWidget(self.lang_cb)
        lang_group.setLayout(lang_layout)
        vlayout.addWidget(lang_group)

        server_group = QGroupBox(_('Language server'))
        server_layout = QGridLayout()
        server_layout.addWidget(self.cmd_label, 0, 0)
        server_layout.addWidget(self.cmd_input, 0, 1)
        server_layout.addWidget(self.args_label, 1, 0)
        server_layout.addWidget(self.args_input, 1, 1)
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
        conf_layout.addWidget(self.conf_label)
        conf_layout.addWidget(self.conf_input)
        conf_layout.addWidget(self.json_label)

        vlayout.addStretch()
        hlayout.addLayout(vlayout, 2)
        hlayout.addLayout(conf_layout, 3)
        general_vlayout.addLayout(hlayout)

        general_vlayout.addWidget(self.bbox)
        self.setLayout(general_vlayout)
        self.form_status(False)

        # Signals
        if not external:
            self.cmd_input.textChanged.connect(lambda x: self.validate())
        self.external_cb.stateChanged.connect(self.set_local_options)
        self.stdio_cb.stateChanged.connect(self.set_stdio_options)
        self.lang_cb.currentIndexChanged.connect(self.lang_selection_changed)
        self.conf_input.textChanged.connect(self.validate)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Final setup
        if language is not None:
            self.form_status(True)
            self.validate()
            if stdio:
                self.set_stdio_options(True)
            if external:
                self.set_local_options(True)

    @Slot()
    def validate(self):
        host_text = self.host_input.text()
        cmd_text = self.cmd_input.text()

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

    def form_status(self, status):
        self.host_input.setEnabled(status)
        self.port_spinner.setEnabled(status)
        self.external_cb.setEnabled(status)
        self.stdio_cb.setEnabled(status)
        self.cmd_input.setEnabled(status)
        self.args_input.setEnabled(status)
        self.conf_input.setEnabled(status)
        self.json_label.setVisible(status)

    @Slot()
    def lang_selection_changed(self):
        idx = self.lang_cb.currentIndex()
        if idx == 0:
            self.set_defaults()
            self.form_status(False)
            self.button_ok.setEnabled(False)
        else:
            server = self.parent.get_server_by_lang(SUPPORTED_LANGUAGES[idx - 1])
            self.form_status(True)
            if server is not None:
                self.host_input.setText(server.host)
                self.port_spinner.setValue(server.port)
                self.external_cb.setChecked(server.external)
                self.stdio_cb.setChecked(server.stdio)
                self.cmd_input.setText(server.cmd)
                self.args_input.setText(server.args)
                self.conf_input.set_text(json.dumps(server.configurations))
                self.json_label.setText(self.JSON_VALID)
                self.button_ok.setEnabled(True)
            else:
                self.set_defaults()

    def set_defaults(self):
        self.cmd_input.setStyleSheet('')
        self.host_input.setStyleSheet('')
        self.host_input.setText(self.DEFAULT_HOST)
        self.port_spinner.setValue(self.DEFAULT_PORT)
        self.external_cb.setChecked(self.DEFAULT_EXTERNAL)
        self.stdio_cb.setChecked(self.DEFAULT_STDIO)
        self.cmd_input.setText(self.DEFAULT_CMD)
        self.args_input.setText(self.DEFAULT_ARGS)
        self.conf_input.set_text(self.DEFAULT_CONFIGURATION)
        self.json_label.setText(self.JSON_VALID)

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

    def get_options(self):
        language_idx = self.lang_cb.currentIndex()
        language = SUPPORTED_LANGUAGES[language_idx - 1]
        host = self.host_input.text()
        port = int(self.port_spinner.value())
        external = self.external_cb.isChecked()
        stdio = self.stdio_cb.isChecked()
        args = self.args_input.text()
        cmd = self.cmd_input.text()
        configurations = json.loads(self.conf_input.toPlainText())
        server = LSPServer(language=language.lower(), cmd=cmd, args=args,
                           host=host, port=port, external=external,
                           stdio=stdio, configurations=configurations,
                           get_option=self.get_option,
                           set_option=self.set_option,
                           remove_option=self.remove_option)
        return server


LANGUAGE, ADDR, CMD = [0, 1, 2]


class LSPServersModel(QAbstractTableModel):
    def __init__(self, parent, text_color=None, text_color_highlight=None):
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
        palette = parent.palette()
        if text_color is None:
            self.text_color = palette.text().color().name()
        else:
            self.text_color = text_color

        if text_color_highlight is None:
            self.text_color_highlight = \
                palette.highlightedText().color().name()
        else:
            self.text_color_highlight = text_color_highlight

    def sortByName(self):
        """Qt Override."""
        self.servers = sorted(self.servers, key=lambda x: x.language)
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
            if column == LANGUAGE:
                return to_qvariant(server.language)
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
            if section == LANGUAGE:
                return to_qvariant(_("Language"))
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
        return 3

    def row(self, row_num):
        """Get row based on model index. Needed for the custom proxy model."""
        return self.servers[row_num]

    def reset(self):
        """"Reset model to take into account new search letters."""
        self.beginResetModel()
        self.endResetModel()


class LSPServerTable(QTableView):
    def __init__(self, parent, text_color=None):
        QTableView.__init__(self, parent)
        self._parent = parent
        self.delete_queue = []
        self.source_model = LSPServersModel(self, text_color=text_color)
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
        super(LSPServerTable, self).focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super(LSPServerTable, self).focusInEvent(e)
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

    def get_server_by_lang(self, lang):
        return self.source_model.server_map.get(lang)

    def load_servers(self):
        servers = list(iter_servers(self._parent.get_option,
                                    self._parent.set_option,
                                    self._parent.remove_option))
        for i, server in enumerate(servers):
            server.index = i
            server.language = LSP_LANGUAGE_NAME[server.language.lower()]
        server_map = {x.language: x for x in servers}
        self.source_model.servers = servers
        self.source_model.server_map = server_map
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(LANGUAGE, Qt.AscendingOrder)

    def save_servers(self):
        language_set = set({})
        for server in self.source_model.servers:
            language_set |= {server.language.lower()}
            server.save()
        while len(self.delete_queue) > 0:
            server = self.delete_queue.pop(0)
            language_set |= {server.language.lower()}
            server.delete()
        return language_set

    def delete_server(self, idx):
        server = self.source_model.servers.pop(idx)
        self.delete_queue.append(server)
        self.source_model.server_map.pop(server.language)
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(LANGUAGE, Qt.AscendingOrder)

    def delete_server_by_lang(self, language):
        idx = next((i for i, x in enumerate(self.source_model.servers)
                    if x.language == language), None)
        if idx is not None:
            self.delete_server(idx)

    def show_editor(self, new_server=False):
        server = LSPServer(get_option=self._parent.get_option,
                           set_option=self._parent.set_option,
                           remove_option=self._parent.remove_option)
        if not new_server:
            idx = self.currentIndex().row()
            server = self.source_model.row(idx)
        dialog = LSPServerEditor(self, **server.__dict__)
        if dialog.exec_():
            server = dialog.get_options()
            self.source_model.server_map[server.language] = server
            self.source_model.servers = list(
                self.source_model.server_map.values())
            self.source_model.reset()
            self.adjust_cells()
            self.sortByColumn(LANGUAGE, Qt.AscendingOrder)
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
            super(LSPServerTable, self).keyPressEvent(event)
        else:
            super(LSPServerTable, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Qt Override."""
        self.show_editor()
