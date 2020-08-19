# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language server preferences
"""

# Standard library imports
import bisect
import os.path as osp
import json
import re
import sys

# Third party imports
from jsonschema.exceptions import ValidationError
from jsonschema import validate as json_validate
from qtpy.compat import to_qvariant, getsavefilename, getopenfilename
from qtpy.QtCore import (Qt, Slot, QAbstractTableModel, QModelIndex,
                         QSize, QObject)
from qtpy.QtWidgets import (QAbstractItemView, QCheckBox,
                            QComboBox, QDialog, QDialogButtonBox, QGroupBox,
                            QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                            QMessageBox, QPushButton, QSpinBox, QTableView,
                            QTabWidget, QVBoxLayout, QWidget, QSpacerItem,
                            QSizePolicy, QFileDialog)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.config.gui import get_font, is_dark_interface
from spyder.config.snippets import SNIPPETS
from spyder.plugins.completion.languageserver import LSP_LANGUAGES
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.misc import check_connection_port
from spyder.utils.snippets.ast import build_snippet_ast
from spyder.utils.programs import find_program
from spyder.widgets.helperwidgets import ItemDelegate

LSP_LANGUAGE_NAME = {x.lower(): x for x in LSP_LANGUAGES}
LSP_URL = "https://microsoft.github.io/language-server-protocol"
LANGUAGE_SET = {l.lower() for l in LSP_LANGUAGES}

PYTHON_POS = bisect.bisect_left(LSP_LANGUAGES, 'Python')
LSP_LANGUAGES_PY = list(LSP_LANGUAGES)
LSP_LANGUAGES_PY.insert(PYTHON_POS, 'Python')


SNIPPETS_SCHEMA = {
    'type': 'array',
    'title': 'Snippets',
    'items': {
        'type': 'object',
        'required': ['language', 'triggers'],
        'properties': {
            'language': {
                'type': 'string',
                'description': 'Programming language',
                'enum': [l.lower() for l in LSP_LANGUAGES_PY]
            },
            'triggers': {
                'type': 'array',
                'description': (
                    'List of snippet triggers defined for this language'),
                'items': {
                    'type': 'object',
                    'description': '',
                    'required': ['trigger', 'descriptions'],
                    'properties': {
                        'trigger': {
                            'type': 'string',
                            'description': (
                                'Text that triggers a snippet family'),
                        },
                        'descriptions': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'description': 'Snippet information',
                                'required': ['description', 'snippet'],
                                'properties': {
                                    'description': {
                                        'type': 'string',
                                        'description': (
                                            'Description of the snippet')
                                    },
                                    'snippet': {
                                        'type': 'object',
                                        'description': 'Snippet information',
                                        'required': ['text', 'remove_trigger'],
                                        'properties': {
                                            'text': {
                                                'type': 'string',
                                                'description': (
                                                    'Snippet to insert')
                                            },
                                            'remove_trigger': {
                                                'type': 'boolean',
                                                'description': (
                                                    'If true, the snippet '
                                                    'should remove the text '
                                                    'that triggers it')
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


def iter_servers():
    for option in CONF.options('lsp-server'):
        if option in LANGUAGE_SET:
            server = LSPServer(language=option)
            server.load()
            yield server


def iter_snippets(language, snippets=None):
    language_snippets = []
    if snippets is None:
        snippets = CONF.get('snippet-completions', language.lower(), {})
    for trigger in snippets:
        trigger_descriptions = snippets[trigger]
        for description in trigger_descriptions:
            this_snippet = Snippet(language=language, trigger_text=trigger,
                                   description=description)
            this_snippet.load()
            language_snippets.append(this_snippet)
    return language_snippets


class LSPServer(object):
    """Convenience class to store LSP Server configuration values."""

    def __init__(self, language=None, cmd='', host='127.0.0.1',
                 port=2084, args='', external=False, stdio=False,
                 configurations={}):
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
            state = CONF.get('lsp-server', self.language.lower())
            self.__dict__.update(state)

    def save(self):
        if self.language is not None:
            language = self.language.lower()
            CONF.set('lsp-server', language, self.__dict__)

    def delete(self):
        if self.language is not None:
            language = self.language.lower()
            CONF.remove_option('lsp-server', language)


class Snippet:
    """Convenience class to store user snippets."""

    def __init__(self, language=None, trigger_text="", description="",
                 snippet_text="", remove_trigger=False):
        self.index = 0
        self.language = language
        if self.language in LSP_LANGUAGE_NAME:
            self.language = LSP_LANGUAGE_NAME[self.language]

        self.trigger_text = trigger_text
        self.snippet_text = snippet_text
        self.description = description
        self.remove_trigger = remove_trigger
        self.initial_trigger_text = trigger_text
        self.initial_description = description

    def __repr__(self):
        return '[{0}] {1} ({2}): {3}'.format(
            self.language, self.trigger_text, self.description,
            repr(self.snippet_text))

    def __str__(self):
        return self.__repr__()

    def update(self, trigger_text, description_text, snippet_text):
        self.trigger_text = trigger_text
        self.description_text = description_text
        self.snippet_text = snippet_text

    def load(self):
        if self.language is not None and self.trigger_text != '':
            state = CONF.get('snippet-completions', self.language.lower())
            trigger_info = state[self.trigger_text]
            snippet_info = trigger_info[self.description]
            self.snippet_text = snippet_info['text']
            self.remove_trigger = snippet_info['remove_trigger']

    def save(self):
        if self.language is not None:
            language = self.language.lower()
            current_state = CONF.get('snippet-completions', language, {})
            new_state = {
                'text': self.snippet_text,
                'remove_trigger': self.remove_trigger
            }
            if (self.initial_trigger_text != self.trigger_text or
                    self.initial_description != self.description):
                # Delete previous entry
                trigger = current_state[self.initial_trigger_text]
                trigger.pop(self.initial_description)
                if len(trigger) == 0:
                    current_state.pop(self.initial_trigger_text)
            trigger_info = current_state.get(self.trigger_text, {})
            trigger_info[self.description] = new_state
            current_state[self.trigger_text] = trigger_info
            CONF.set('snippet-completions', language, current_state)

    def delete(self):
        if self.language is not None:
            language = self.language.lower()
            current_state = CONF.get('snippet-completions', language, {})
            trigger = current_state[self.trigger_text]
            trigger.pop(self.description)
            if len(trigger) == 0:
                current_state.pop(self.trigger_text)
            CONF.set('snippet-completions', language, current_state)


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
                 configurations={}, **kwargs):
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
        self.conf_input = CodeEditor(None)

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
        self.lang_cb.addItems(LSP_LANGUAGES)

        self.button_ok.setEnabled(False)
        if language is not None:
            idx = LSP_LANGUAGES.index(language)
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
            color_scheme=CONF.get('appearance', 'selected'),
            wrap=False,
            edge_line=True,
            highlight_current_line=True,
            highlight_current_cell=True,
            occurrence_highlighting=True,
            auto_unindent=True,
            font=get_font(),
            filename='config.json',
            folding=False
        )
        self.conf_input.set_language('json', 'config.json')
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
            server = self.parent.get_server_by_lang(LSP_LANGUAGES[idx - 1])
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
        language = LSP_LANGUAGES[language_idx - 1]
        host = self.host_input.text()
        port = int(self.port_spinner.value())
        external = self.external_cb.isChecked()
        stdio = self.stdio_cb.isChecked()
        args = self.args_input.text()
        cmd = self.cmd_input.text()
        configurations = json.loads(self.conf_input.toPlainText())
        server = LSPServer(language=language.lower(), cmd=cmd, args=args,
                           host=host, port=port, external=external,
                           stdio=stdio, configurations=configurations)
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

        # Needed to compensate for the HTMLDelegate color selection unawarness
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
        servers = list(iter_servers())
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
        for server in self.source_model.servers:
            server.save()
        while len(self.delete_queue) > 0:
            server = self.delete_queue.pop(0)
            server.delete()

    def delete_server(self, idx):
        server = self.source_model.servers.pop(idx)
        self.delete_queue.append(server)
        self.source_model.server_map.pop(server.language)
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(LANGUAGE, Qt.AscendingOrder)

    def show_editor(self, new_server=False):
        server = LSPServer()
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


class SnippetEditor(QDialog):
    SNIPPET_VALID = _('Valid snippet')
    SNIPPET_INVALID = _('Invalid snippet')
    INVALID_CB_CSS = "QComboBox {border: 1px solid red;}"
    VALID_CB_CSS = "QComboBox {border: 1px solid green;}"
    INVALID_LINE_CSS = "QLineEdit {border: 1px solid red;}"
    VALID_LINE_CSS = "QLineEdit {border: 1px solid green;}"
    MIN_SIZE = QSize(850, 600)

    def __init__(self, parent, language=None, trigger_text='', description='',
                 snippet_text='', remove_trigger=False, trigger_texts=[],
                 descriptions=[]):
        super(SnippetEditor, self).__init__(parent)

        snippet_description = _(
            "To add a new text snippet, you need to define the text "
            "that triggers it, a short description (two words maximum) "
            "of the snippet and if it should delete the trigger text when "
            "inserted. Finally, you need to define the snippet body to insert."
        )

        self.parent = parent
        self.trigger_text = trigger_text
        self.description = description
        self.remove_trigger = remove_trigger
        self.snippet_text = snippet_text
        self.descriptions = descriptions
        self.base_snippet = Snippet(
            language=language, trigger_text=trigger_text,
            snippet_text=snippet_text, description=description,
            remove_trigger=remove_trigger)

        # Widgets
        self.snippet_settings_description = QLabel(snippet_description)

        # Trigger text
        self.trigger_text_label = QLabel(_('Trigger text:'))
        self.trigger_text_cb = QComboBox(self)
        self.trigger_text_cb.setEditable(True)

        # Description
        self.description_label = QLabel(_('Description:'))
        self.description_input = QLineEdit(self)

        # Remove trigger
        self.remove_trigger_cb = QCheckBox(
            _('Remove trigger text on insertion'), self)
        self.remove_trigger_cb.setToolTip(_('Check if the text that triggers '
                                            'this snippet should be removed '
                                            'when inserting it'))
        self.remove_trigger_cb.setChecked(self.remove_trigger)

        # Snippet body input
        self.snippet_label = QLabel(_('<b>Snippet text:</b>'))
        self.snippet_valid_label = QLabel(self.SNIPPET_INVALID, self)
        self.snippet_input = CodeEditor(None)

        # Dialog buttons
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        # Widget setup
        self.setWindowTitle(_('Snippet editor'))

        self.snippet_settings_description.setWordWrap(True)
        self.trigger_text_cb.setToolTip(
            _('Trigger text for the current snippet'))
        self.trigger_text_cb.addItems(trigger_texts)

        if self.trigger_text != '':
            idx = trigger_texts.index(self.trigger_text)
            self.trigger_text_cb.setCurrentIndex(idx)

        self.description_input.setText(self.description)
        self.description_input.textChanged.connect(lambda _: self.validate())

        text_inputs = (self.trigger_text, self.description, self.snippet_text)
        non_empty_text = all([x != '' for x in text_inputs])
        if non_empty_text:
            self.button_ok.setEnabled(True)

        self.snippet_input.setup_editor(
            language=language,
            color_scheme=CONF.get('appearance', 'selected'),
            wrap=False,
            edge_line=True,
            highlight_current_line=True,
            highlight_current_cell=True,
            occurrence_highlighting=True,
            auto_unindent=True,
            font=get_font(),
            filename='snippet',
            folding=False
        )
        self.snippet_input.set_language(language, 'snippet')
        self.snippet_input.setToolTip(_('Snippet text completion to insert'))
        self.snippet_input.set_text(snippet_text)

        # Layout setup
        general_layout = QVBoxLayout()
        general_layout.addWidget(self.snippet_settings_description)

        snippet_settings_group = QGroupBox(_('Trigger information'))
        settings_layout = QGridLayout()
        settings_layout.addWidget(self.trigger_text_label, 0, 0)
        settings_layout.addWidget(self.trigger_text_cb, 0, 1)
        settings_layout.addWidget(self.description_label, 1, 0)
        settings_layout.addWidget(self.description_input, 1, 1)

        all_settings_layout = QVBoxLayout()
        all_settings_layout.addLayout(settings_layout)
        all_settings_layout.addWidget(self.remove_trigger_cb)
        snippet_settings_group.setLayout(all_settings_layout)
        general_layout.addWidget(snippet_settings_group)

        text_layout = QVBoxLayout()
        text_layout.addWidget(self.snippet_label)
        text_layout.addWidget(self.snippet_input)
        text_layout.addWidget(self.snippet_valid_label)
        general_layout.addLayout(text_layout)

        general_layout.addWidget(self.bbox)
        self.setLayout(general_layout)

        # Signals
        self.trigger_text_cb.editTextChanged.connect(self.validate)
        self.description_input.textChanged.connect(self.validate)
        self.snippet_input.textChanged.connect(self.validate)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        # Final setup
        if trigger_text != '' or snippet_text != '':
            self.validate()

    @Slot()
    def validate(self):
        trigger_text = self.trigger_text_cb.currentText()
        description_text = self.description_input.text()
        snippet_text = self.snippet_input.toPlainText()

        invalid = False
        try:
            build_snippet_ast(snippet_text)
            self.snippet_valid_label.setText(self.SNIPPET_VALID)
        except SyntaxError:
            invalid = True
            self.snippet_valid_label.setText(self.SNIPPET_INVALID)

        if trigger_text == '':
            invalid = True
            self.trigger_text_cb.setStyleSheet(self.INVALID_CB_CSS)
        else:
            self.trigger_text_cb.setStyleSheet(self.VALID_CB_CSS)

        if self.trigger_text != trigger_text:
            if description_text in self.descriptions[trigger_text]:
                invalid = True
                self.description_input.setStyleSheet(self.INVALID_LINE_CSS)
            else:
                self.description_input.setStyleSheet(self.VALID_LINE_CSS)
        else:
            if description_text != self.description:
                if description_text in self.descriptions[trigger_text]:
                    invalid = True
                    self.description_input.setStyleSheet(self.INVALID_LINE_CSS)
                else:
                    self.description_input.setStyleSheet(self.VALID_LINE_CSS)
            else:
                self.description_input.setStyleSheet(self.VALID_LINE_CSS)

        self.button_ok.setEnabled(not invalid)

    def get_options(self):
        trigger_text = self.trigger_text_cb.currentText()
        description_text = self.description_input.text()
        snippet_text = self.snippet_input.toPlainText()
        self.base_snippet.update(trigger_text, description_text, snippet_text)
        return self.base_snippet


class SnippetsModel(QAbstractTableModel):
    TRIGGER = 0
    DESCRIPTION = 1

    def __init__(self, parent, text_color=None, text_color_highlight=None):
        super(QAbstractTableModel, self).__init__()
        self.parent = parent

        self.snippets = []
        self.delete_queue = []
        self.snippet_map = {}
        self.rich_text = []
        self.normal_text = []
        self.letters = ''
        self.label = QLabel()
        self.widths = []

        # Needed to compensate for the HTMLDelegate color selection unawarness
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
        self.snippets = sorted(self.snippets, key=lambda x: x.trigger_text)
        self.reset()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.snippets)):
            return to_qvariant()

        snippet = self.snippets[row]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == self.TRIGGER:
                return to_qvariant(snippet.trigger_text)
            elif column == self.DESCRIPTION:
                return to_qvariant(snippet.description)
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
            if section == self.TRIGGER:
                return to_qvariant(_('Trigger text'))
            elif section == self.DESCRIPTION:
                return to_qvariant(_('Description'))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.snippets)

    def columnCount(self, index=QModelIndex()):
        return 2

    def row(self, row_num):
        return self.snippets[row_num]

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class SnippetModelsProxy:
    def __init__(self):
        self.models = {}
        self.awaiting_queue = {}

    def get_model(self, table, language, text_color=None):
        if language not in self.models:
            language_model = SnippetsModel(table, text_color=text_color)
            to_add = self.awaiting_queue.pop(language, [])
            self.load_snippets(language, language_model, to_add=to_add)
            self.models[language] = language_model
        language_model = self.models[language]
        return language_model

    def reload_model(self, language, defaults):
        if language in self.models:
            model = self.models[language]
            self.load_snippets(language, model, defaults)

    def load_snippets(self, language, model, snippets=None, to_add=[]):
        snippets = iter_snippets(language, snippets=snippets)
        for i, snippet in enumerate(snippets):
            snippet.index = i

        snippet_map = {(x.trigger_text, x.description): x
                       for x in snippets}

        # Merge loaded snippets
        for snippet in to_add:
            key = (snippet.trigger_text, snippet.description)
            if key in snippet_map:
                to_replace = snippet_map[key]
                snippet.index = to_replace.index
                snippet_map[key] = snippet
            else:
                snippet.index = len(snippet_map)
                snippet_map[key] = snippet

        model.snippets = list(snippet_map.values())
        model.snippet_map = snippet_map

    def save_snippets(self):
        for language in self.models:
            language_model = self.models[language]
            for snippet in language_model.snippets:
                snippet.save()
            while len(language_model.delete_queue) > 0:
                snippet = language_model.delete_queue.pop(0)
                snippet.delete()

        for language in list(self.awaiting_queue.keys()):
            language_queue = self.awaiting_queue.pop(language)
            for snippet in language_queue:
                snippet.save()

    def update_or_enqueue(self, language, trigger, description, snippet):
        new_snippet = Snippet(
            language=language, trigger_text=trigger, description=description,
            snippet_text=snippet['text'],
            remove_trigger=snippet['remove_trigger'])

        if language in self.models:
            language_model = self.models[language]
            snippet_map = language_model.snippet_map
            key = (trigger, description)
            if key in snippet_map:
                old_snippet = snippet_map[key]
                new_snippet.index = old_snippet.index
                snippet_map[key] = new_snippet
            else:
                new_snippet.index = len(snippet_map)
                snippet_map[key] = new_snippet

            language_model.snippets = list(snippet_map.values())
            language_model.snippet_map = snippet_map
            language_model.reset()
        else:
            language_queue = self.awaiting_queue.get(language, [])
            language_queue.append(new_snippet)

    def export_snippets(self, filename):
        snippets = []
        for language in self.models:
            language_model = self.models[language]
            language_snippets = {
                'language': language,
                'triggers': []
            }
            triggers = {}
            for snippet in language_model.snippets:
                default_trigger = {
                    'trigger': snippet.trigger_text,
                    'descriptions': []
                }
                snippet_info = triggers.get(
                    snippet.trigger_text, default_trigger)
                snippet_info['descriptions'].append({
                    'description': snippet.description,
                    'snippet': {
                        'text': snippet.snippet_text,
                        'remove_trigger': snippet.remove_trigger
                    }
                })
                triggers[snippet.trigger_text] = snippet_info
            language_snippets['triggers'] = list(triggers.values())
            snippets.append(language_snippets)

        with open(filename, 'w') as f:
            json.dump(snippets, f)

    def import_snippets(self, filename):
        errors = {}
        total_snippets = 0
        valid_snippets = 0
        with open(filename, 'r') as f:
            try:
                snippets = json.load(f)
            except ValueError as e:
                errors['loading'] = e.msg

        if len(errors) == 0:
            try:
                json_validate(instance=snippets, schema=SNIPPETS_SCHEMA)
            except ValidationError as e:
                index_path = ['snippets']
                for part in e.absolute_path:
                    index_path.append('[{0}]'.format(part))
                full_message = '{0} on instance {1}:<br>{2}'.format(
                    e.message, ''.join(index_path), e.instance
                )
                errors['validation'] = full_message

        if len(errors) == 0:
            for language_info in snippets:
                language = language_info['language']
                triggers = language_info['triggers']
                for trigger_info in triggers:
                    trigger = trigger_info['trigger']
                    descriptions = trigger_info['descriptions']
                    for description_info in descriptions:
                        description = description_info['description']
                        snippet = description_info['snippet']
                        snippet_text = snippet['text']
                        total_snippets += 1
                        try:
                            build_snippet_ast(snippet_text)
                            self.update_or_enqueue(
                                language, trigger, description, snippet)
                            valid_snippets += 1
                        except SyntaxError as e:
                            syntax_errors = errors.get('syntax', {})
                            key = '{0}/{1}/{2}'.format(
                                language, trigger, description)
                            syntax_errors[key] = e.msg
                            errors['syntax'] = syntax_errors

        return valid_snippets, total_snippets, errors


class SnippetTable(QTableView):
    def __init__(self, parent, proxy, language=None, text_color=None):
        super(SnippetTable, self).__init__()
        self._parent = parent
        self.language = language
        self.source_model = proxy.get_model(
            self, language.lower(), text_color=text_color)
        self.setModel(self.source_model)
        self.setItemDelegateForColumn(CMD, ItemDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)
        self.verticalHeader().hide()

        self.reset_plain()

    def focusOutEvent(self, e):
        """Qt Override."""
        # self.source_model.update_active_row()
        # self._parent.delete_btn.setEnabled(False)
        super(SnippetTable, self).focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super(SnippetTable, self).focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def selection(self, index):
        self.update()
        self.isActiveWindow()
        self._parent.delete_snippet_btn.setEnabled(True)

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(s.description) for s in self.source_model.snippets]
        if names:
            self.setColumnWidth(CMD, max(names))
        self.horizontalHeader().setStretchLastSection(True)

    def reset_plain(self):
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(self.source_model.TRIGGER, Qt.AscendingOrder)

    def delete_snippet(self, idx):
        snippet = self.source_model.snippets.pop(idx)
        self.source_model.delete_queue.append(snippet)
        self.source_model.snippet_map.pop(
            (snippet.trigger_text, snippet.description))
        self.source_model.reset()
        self.adjust_cells()
        self.sortByColumn(self.source_model.TRIGGER, Qt.AscendingOrder)

    def show_editor(self, new_snippet=False):
        snippet = Snippet()
        if not new_snippet:
            idx = self.currentIndex().row()
            snippet = self.source_model.row(idx)

        snippets_keys = list(self.source_model.snippet_map.keys())
        trigger_texts = [x[0] for x in snippets_keys]
        descriptions = {}
        for trigger, description in snippets_keys:
            trigger_descriptions = descriptions.get(trigger, set({}))
            trigger_descriptions |= {description}
            descriptions[trigger] = trigger_descriptions

        dialog = SnippetEditor(self, language=self.language.lower(),
                               trigger_text=snippet.trigger_text,
                               description=snippet.description,
                               remove_trigger=snippet.remove_trigger,
                               snippet_text=snippet.snippet_text,
                               trigger_texts=trigger_texts,
                               descriptions=descriptions)
        if dialog.exec_():
            snippet = dialog.get_options()
            key = (snippet.trigger_text, snippet.description)
            self.source_model.snippet_map[key] = snippet
            snippet_list = list(
                self.source_model.snippet_map.values())
            self.source_model.snippets = list(
                self.source_model.snippet_map.values())
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
            super(SnippetTable, self).keyPressEvent(event)
        else:
            super(SnippetTable, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Qt Override."""
        self.show_editor()


class LanguageServerConfigPage(GeneralConfigPage):
    """Language Server Protocol manager preferences."""
    CONF_SECTION = 'lsp-server'
    NAME = _('Completion and linting')
    ICON = ima.icon('lspserver')
    CTRL = "Cmd" if sys.platform == 'darwin' else "Ctrl"

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Completion ---
        # Completion group
        self.completion_box = newcb(_("Enable code completion"),
                                    'code_completion')
        self.completion_hint_box = newcb(
            _("Show completion details"),
            'completions_hint',
            section='editor')
        self.completions_hint_after_ms = self.create_spinbox(
            _("Show completion detail after keyboard idle (ms):"), None,
            'completions_hint_after_ms', min_=0, max_=5000, step=10,
            tip=_("Default is 500"), section='editor')
        self.automatic_completion_box = newcb(
            _("Show completions on the fly"),
            'automatic_completions',
            section='editor')
        self.completions_after_characters = self.create_spinbox(
            _("Show automatic completions after characters entered:"), None,
            'automatic_completions_after_chars', min_=1, step=1,
            tip=_("Default is 3"), section='editor')
        self.completions_after_ms = self.create_spinbox(
            _("Show automatic completions after keyboard idle (ms):"), None,
            'automatic_completions_after_ms', min_=0, max_=5000, step=10,
            tip=_("Default is 300"), section='editor')
        code_snippets_box = newcb(_("Enable code snippets"), 'code_snippets')

        completion_layout = QGridLayout()
        completion_layout.addWidget(self.completion_box, 0, 0)
        completion_layout.addWidget(self.completion_hint_box, 1, 0)
        completion_layout.addWidget(self.completions_hint_after_ms.plabel,
                                    2, 0)
        completion_layout.addWidget(self.completions_hint_after_ms.spinbox,
                                    2, 1)
        completion_layout.addWidget(self.automatic_completion_box, 3, 0)
        completion_layout.addWidget(self.completions_after_characters.plabel,
                                    4, 0)
        completion_layout.addWidget(self.completions_after_characters.spinbox,
                                    4, 1)
        completion_layout.addWidget(self.completions_after_ms.plabel, 5, 0)
        completion_layout.addWidget(self.completions_after_ms.spinbox, 5, 1)
        completion_layout.addWidget(code_snippets_box, 6, 0)
        completion_layout.setColumnStretch(2, 6)
        completion_widget = QWidget()
        completion_widget.setLayout(completion_layout)

        self.completion_box.toggled.connect(self.check_completion_options)
        self.automatic_completion_box.toggled.connect(
            self.check_completion_options)

        # --- Introspection ---
        # Introspection group
        introspection_group = QGroupBox(_("Basic features"))
        goto_definition_box = newcb(
            _("Enable Go to definition"),
            'jedi_definition',
            tip=_("If enabled, left-clicking on an object name while \n"
                  "pressing the {} key will go to that object's definition\n"
                  "(if resolved).").format(self.CTRL))
        follow_imports_box = newcb(_("Follow imports when going to a "
                                     "definition"),
                                   'jedi_definition/follow_imports')
        show_signature_box = newcb(_("Show calltips"), 'jedi_signature_help')
        enable_hover_hints_box = newcb(
            _("Enable hover hints"),
            'enable_hover_hints',
            tip=_("If enabled, hovering the mouse pointer over an object\n"
                  "name will display that object's signature and/or\n"
                  "docstring (if present)."))
        introspection_layout = QVBoxLayout()
        introspection_layout.addWidget(goto_definition_box)
        introspection_layout.addWidget(follow_imports_box)
        introspection_layout.addWidget(show_signature_box)
        introspection_layout.addWidget(enable_hover_hints_box)
        introspection_group.setLayout(introspection_layout)

        goto_definition_box.toggled.connect(follow_imports_box.setEnabled)

        # Advanced group
        advanced_group = QGroupBox(_("Advanced"))
        modules_textedit = self.create_textedit(
            _("Preload the following modules to make completion faster "
              "and more accurate:"),
            'preload_modules'
        )
        if is_dark_interface():
            modules_textedit.textbox.setStyleSheet(
                "border: 1px solid #32414B;"
            )

        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(modules_textedit)
        advanced_group.setLayout(advanced_layout)

        # --- Linting ---
        # Linting options
        linting_label = QLabel(_("Spyder can optionally highlight syntax "
                                 "errors and possible problems with your "
                                 "code in the editor."))
        linting_label.setOpenExternalLinks(True)
        linting_label.setWordWrap(True)
        linting_check = self.create_checkbox(
            _("Enable basic linting"),
            'pyflakes')
        underline_errors_box = newcb(
            _("Underline errors and warnings"),
            'underline_errors',
            section='editor')
        linting_complexity_box = self.create_checkbox(
            _("Enable complexity linting with the Mccabe package"),
            'mccabe')

        # Linting layout
        linting_layout = QVBoxLayout()
        linting_layout.addWidget(linting_label)
        linting_layout.addWidget(linting_check)
        linting_layout.addWidget(underline_errors_box)
        linting_layout.addWidget(linting_complexity_box)
        linting_widget = QWidget()
        linting_widget.setLayout(linting_layout)

        linting_check.toggled.connect(underline_errors_box.setEnabled)

        # --- Code style tab ---
        # Code style label
        pep_url = (
            '<a href="https://www.python.org/dev/peps/pep-0008">PEP 8</a>')
        code_style_codes_url = _(
            "<a href='http://pycodestyle.pycqa.org/en/stable"
            "/intro.html#error-codes'>pycodestyle error codes</a>")
        code_style_label = QLabel(
            _("Spyder can use pycodestyle to analyze your code for "
              "conformance to the {} convention. You can also "
              "manually show or hide specific warnings by their "
              "{}.").format(pep_url, code_style_codes_url))
        code_style_label.setOpenExternalLinks(True)
        code_style_label.setWordWrap(True)

        # Code style checkbox
        self.code_style_check = self.create_checkbox(
            _("Enable code style linting"),
            'pycodestyle')

        # Code style options
        self.code_style_filenames_match = self.create_lineedit(
            _("Only check filenames matching these patterns:"),
            'pycodestyle/filename', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Check Python files: *.py"))
        self.code_style_exclude = self.create_lineedit(
            _("Exclude files or directories matching these patterns:"),
            'pycodestyle/exclude', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Exclude all test files: (?!test_).*\\.py"))
        code_style_select = self.create_lineedit(
            _("Show the following errors or warnings:").format(
                code_style_codes_url),
            'pycodestyle/select', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: E113, W391"))
        code_style_ignore = self.create_lineedit(
            _("Ignore the following errors or warnings:"),
            'pycodestyle/ignore', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: E201, E303"))
        code_style_max_line_length = self.create_spinbox(
            _("Maximum allowed line length:"), None,
            'pycodestyle/max_line_length', min_=10, max_=500, step=1,
            tip=_("Default is 79"))

        # Code style layout
        code_style_g_layout = QGridLayout()
        code_style_g_layout.addWidget(
            self.code_style_filenames_match.label, 1, 0)
        code_style_g_layout.addWidget(
            self.code_style_filenames_match.textbox, 1, 1)
        code_style_g_layout.addWidget(self.code_style_exclude.label, 2, 0)
        code_style_g_layout.addWidget(self.code_style_exclude.textbox, 2, 1)
        code_style_g_layout.addWidget(code_style_select.label, 3, 0)
        code_style_g_layout.addWidget(code_style_select.textbox, 3, 1)
        code_style_g_layout.addWidget(code_style_ignore.label, 4, 0)
        code_style_g_layout.addWidget(code_style_ignore.textbox, 4, 1)
        code_style_g_layout.addWidget(code_style_max_line_length.plabel, 5, 0)
        code_style_g_layout.addWidget(
            code_style_max_line_length.spinbox, 5, 1)

        # Set Code style options enabled/disabled
        code_style_g_widget = QWidget()
        code_style_g_widget.setLayout(code_style_g_layout)
        code_style_g_widget.setEnabled(self.get_option('pycodestyle'))
        self.code_style_check.toggled.connect(code_style_g_widget.setEnabled)

        # Code style layout
        code_style_layout = QVBoxLayout()
        code_style_layout.addWidget(code_style_label)
        code_style_layout.addWidget(self.code_style_check)
        code_style_layout.addWidget(code_style_g_widget)

        code_style_widget = QWidget()
        code_style_widget.setLayout(code_style_layout)

        # --- Docstring tab ---
        # Docstring style label
        numpy_url = (
            "<a href='https://numpydoc.readthedocs.io/en/"
            "latest/format.html'>Numpy</a>")
        pep257_url = (
            "<a href='https://www.python.org/dev/peps/pep-0257/'>PEP 257</a>")
        docstring_style_codes = _(
            "<a href='http://www.pydocstyle.org/en/stable"
            "/error_codes.html'>page</a>")
        docstring_style_label = QLabel(
            _("Here you can decide if you want to perform style analysis on "
              "your docstrings according to the {} or {} conventions. You can "
              "also decide if you want to show or ignore specific errors, "
              "according to the codes found on this {}.").format(
                  numpy_url, pep257_url, docstring_style_codes))
        docstring_style_label.setOpenExternalLinks(True)
        docstring_style_label.setWordWrap(True)

        # Docstring style checkbox
        self.docstring_style_check = self.create_checkbox(
            _("Enable docstring style linting"),
            'pydocstyle')

        # Docstring style options
        docstring_style_convention = self.create_combobox(
            _("Choose the convention used to lint docstrings: "),
            (("Numpy", 'numpy'),
             ("PEP 257", 'pep257'),
             ("Custom", 'custom')),
            'pydocstyle/convention')
        self.docstring_style_select = self.create_lineedit(
            _("Show the following errors:"),
            'pydocstyle/select', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: D413, D414"))
        self.docstring_style_ignore = self.create_lineedit(
            _("Ignore the following errors:"),
            'pydocstyle/ignore', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: D107, D402"))
        self.docstring_style_match = self.create_lineedit(
            _("Only check filenames matching these patterns:"),
            'pydocstyle/match', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Skip test files: (?!test_).*\\.py"))
        self.docstring_style_match_dir = self.create_lineedit(
            _("Only check in directories matching these patterns:"),
            'pydocstyle/match_dir', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Skip dot directories: [^\\.].*"))

        # Custom option handling
        docstring_style_convention.combobox.currentTextChanged.connect(
                self.setup_docstring_style_convention)
        current_convention = docstring_style_convention.combobox.currentText()
        self.setup_docstring_style_convention(current_convention)

        # Docstring style layout
        docstring_style_g_layout = QGridLayout()
        docstring_style_g_layout.addWidget(
            docstring_style_convention.label, 1, 0)
        docstring_style_g_layout.addWidget(
            docstring_style_convention.combobox, 1, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_select.label, 2, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_select.textbox, 2, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_ignore.label, 3, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_ignore.textbox, 3, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match.label, 4, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match.textbox, 4, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match_dir.label, 5, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match_dir.textbox, 5, 1)

        # Set Docstring style options enabled/disabled
        docstring_style_g_widget = QWidget()
        docstring_style_g_widget.setLayout(docstring_style_g_layout)
        docstring_style_g_widget.setEnabled(self.get_option('pydocstyle'))
        self.docstring_style_check.toggled.connect(
            docstring_style_g_widget.setEnabled)

        # Docstring style layout
        docstring_style_layout = QVBoxLayout()
        docstring_style_layout.addWidget(docstring_style_label)
        docstring_style_layout.addWidget(self.docstring_style_check)
        docstring_style_layout.addWidget(docstring_style_g_widget)

        docstring_style_widget = QWidget()
        docstring_style_widget.setLayout(docstring_style_layout)

        # --- Snippets tab ---
        self.snippets_language = 'python'
        grammar_url = (
            "<a href=\"{0}/specifications/specification-current#snippet_syntax\">"
            "{1}</a>".format(LSP_URL, _('the LSP grammar')))
        snippets_info_label = QLabel(
            _("Spyder allows to define custom completion snippets to use "
              "in addition to the ones offered by the LSP. Each snippet "
              "should follow {}. <b>Note:</b> All changes will be effective "
              "only when applying the settings").format(grammar_url))
        snippets_info_label.setOpenExternalLinks(True)
        snippets_info_label.setWordWrap(True)
        snippets_info_label.setAlignment(Qt.AlignJustify)

        self.snippets_language_cb = QComboBox(self)
        self.snippets_language_cb.setToolTip(
            _('Programming language provided by the LSP server'))
        self.snippets_language_cb.addItems(LSP_LANGUAGES_PY)
        self.snippets_language_cb.setCurrentIndex(PYTHON_POS)

        snippet_lang_group = QGroupBox(_('Language'))
        snippet_lang_layout = QVBoxLayout()
        snippet_lang_layout.addWidget(self.snippets_language_cb)
        snippet_lang_group.setLayout(snippet_lang_layout)

        self.snippets_proxy = SnippetModelsProxy()
        self.snippets_table = SnippetTable(
            self, self.snippets_proxy, language=self.snippets_language)
        self.snippets_table.setMaximumHeight(120)

        snippet_table_group = QGroupBox(_('Available snippets'))
        snippet_table_layout = QVBoxLayout()
        snippet_table_layout.addWidget(self.snippets_table)
        snippet_table_group.setLayout(snippet_table_layout)

        # Buttons
        self.reset_snippets_btn = QPushButton(_("Reset to default values"))
        self.new_snippet_btn = QPushButton(_("Create a new snippet"))
        self.delete_snippet_btn = QPushButton(
            _("Delete currently selected snippet"))
        self.delete_snippet_btn.setEnabled(False)
        self.export_snippets_btn = QPushButton(_("Export snippets to JSON"))
        self.import_snippets_btn = QPushButton(_("Import snippets from JSON"))

        # Slots connected to buttons
        self.new_snippet_btn.clicked.connect(self.create_new_snippet)
        self.reset_snippets_btn.clicked.connect(self.reset_default_snippets)
        self.delete_snippet_btn.clicked.connect(self.delete_snippet)
        self.export_snippets_btn.clicked.connect(self.export_snippets)
        self.import_snippets_btn.clicked.connect(self.import_snippets)

        # Buttons layout
        btns = [self.new_snippet_btn,
                self.delete_snippet_btn,
                self.reset_snippets_btn,
                self.export_snippets_btn,
                self.import_snippets_btn]
        sn_buttons_layout = QGridLayout()
        for i, btn in enumerate(btns):
            sn_buttons_layout.addWidget(btn, i, 1)
        sn_buttons_layout.setColumnStretch(0, 1)
        sn_buttons_layout.setColumnStretch(1, 2)
        sn_buttons_layout.setColumnStretch(2, 1)

        # Snippets layout
        snippets_layout = QVBoxLayout()
        snippets_layout.addWidget(snippets_info_label)
        snippets_layout.addWidget(snippet_lang_group)
        snippets_layout.addWidget(snippet_table_group)
        snippets_layout.addLayout(sn_buttons_layout)

        snippets_widget = QWidget()
        snippets_widget.setLayout(snippets_layout)

        # --- Advanced tab ---
        # Clients group
        clients_group = QGroupBox(_("Providers"))
        self.kite_enabled = newcb(_("Enable Kite "
                                    "(if the Kite engine is running)"),
                                  'enable',
                                  section='kite')
        self.fallback_enabled = newcb(_("Enable fallback completions"),
                                      'enable',
                                      section='fallback-completions')
        self.completions_wait_for_ms = self.create_spinbox(
            _("Time to wait for all providers to return (ms):"), None,
            'completions_wait_for_ms', min_=0, max_=5000, step=10,
            tip=_("Beyond this timeout, "
                  "the first available provider will be returned"),
            section='editor')

        clients_layout = QVBoxLayout()
        clients_layout.addWidget(self.kite_enabled)
        clients_layout.addWidget(self.fallback_enabled)
        clients_layout.addWidget(self.completions_wait_for_ms)
        clients_group.setLayout(clients_layout)

        kite_layout = QVBoxLayout()
        self.kite_cta = self.create_checkbox(
            _("Notify me when Kite can provide missing completions"
              " (but is unavailable)"),
            'call_to_action',
            section='kite')
        kite_layout.addWidget(self.kite_cta)
        kite_group = QGroupBox(_(
            'Kite configuration'))
        kite_group.setLayout(kite_layout)

        # Advanced label
        lsp_advanced_group = QGroupBox(_(
            'Python Language Server configuration'))
        advanced_label = QLabel(
            _("<b>Warning</b>: Only modify these values if "
              "you know what you're doing!"))
        advanced_label.setWordWrap(True)
        advanced_label.setAlignment(Qt.AlignJustify)

        # Advanced settings checkbox
        self.advanced_options_check = self.create_checkbox(
            _("Enable advanced settings"), 'advanced/enabled')

        # Advanced options
        self.advanced_module = self.create_lineedit(
            _("Module for the Python language server: "),
            'advanced/module', alignment=Qt.Horizontal,
            word_wrap=False)
        self.advanced_host = self.create_lineedit(
            _("IP Address and port to bind the server to: "),
            'advanced/host', alignment=Qt.Horizontal,
            word_wrap=False)
        self.advanced_port = self.create_spinbox(
            ":", "", 'advanced/port', min_=1, max_=65535, step=1)
        self.external_server = self.create_checkbox(
            _("This is an external server"),
            'advanced/external')
        self.use_stdio = self.create_checkbox(
            _("Use stdio pipes to communicate with server"),
            'advanced/stdio')
        self.use_stdio.stateChanged.connect(self.disable_tcp)
        self.external_server.stateChanged.connect(self.disable_stdio)

        # Advanced layout
        advanced_g_layout = QGridLayout()
        advanced_g_layout.addWidget(self.advanced_module.label, 1, 0)
        advanced_g_layout.addWidget(self.advanced_module.textbox, 1, 1)
        advanced_g_layout.addWidget(self.advanced_host.label, 2, 0)

        advanced_host_port_g_layout = QGridLayout()
        advanced_host_port_g_layout.addWidget(self.advanced_host.textbox, 1, 0)
        advanced_host_port_g_layout.addWidget(self.advanced_port.plabel, 1, 1)
        advanced_host_port_g_layout.addWidget(self.advanced_port.spinbox, 1, 2)
        advanced_g_layout.addLayout(advanced_host_port_g_layout, 2, 1)

        # External server and stdio options layout
        advanced_server_layout = QVBoxLayout()
        advanced_server_layout.addWidget(self.external_server)
        advanced_server_layout.addWidget(self.use_stdio)

        advanced_options_layout = QVBoxLayout()
        advanced_options_layout.addLayout(advanced_g_layout)
        advanced_options_layout.addLayout(advanced_server_layout)

        # Set advanced options enabled/disabled
        advanced_options_widget = QWidget()
        advanced_options_widget.setLayout(advanced_options_layout)
        advanced_options_widget.setEnabled(self.get_option('advanced/enabled'))
        self.advanced_options_check.toggled.connect(
            advanced_options_widget.setEnabled)
        self.advanced_options_check.toggled.connect(
            self.show_advanced_warning)

        # Advanced options layout
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(advanced_label)
        advanced_layout.addWidget(self.advanced_options_check)
        advanced_layout.addWidget(advanced_options_widget)

        lsp_advanced_group.setLayout(advanced_layout)

        # --- Other servers tab ---
        # Section label
        servers_label = QLabel(
            _("Spyder uses the <a href=\"{lsp_url}\">Language Server "
              "Protocol</a> to provide code completion and linting "
              "for its Editor. Here, you can setup and configure LSP servers "
              "for languages other than Python, so Spyder can provide such "
              "features for those languages as well."
              ).format(lsp_url=LSP_URL))
        servers_label.setOpenExternalLinks(True)
        servers_label.setWordWrap(True)
        servers_label.setAlignment(Qt.AlignJustify)

        # Servers table
        table_group = QGroupBox(_('Available servers:'))
        self.table = LSPServerTable(self, text_color=ima.MAIN_FG_COLOR)
        self.table.setMaximumHeight(150)
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)

        # Buttons
        self.reset_btn = QPushButton(_("Reset to default values"))
        self.new_btn = QPushButton(_("Set up a new server"))
        self.delete_btn = QPushButton(_("Delete currently selected server"))
        self.delete_btn.setEnabled(False)

        # Slots connected to buttons
        self.new_btn.clicked.connect(self.create_new_server)
        self.reset_btn.clicked.connect(self.reset_to_default)
        self.delete_btn.clicked.connect(self.delete_server)

        # Buttons layout
        btns = [self.new_btn, self.delete_btn, self.reset_btn]
        buttons_layout = QGridLayout()
        for i, btn in enumerate(btns):
            buttons_layout.addWidget(btn, i, 1)
        buttons_layout.setColumnStretch(0, 1)
        buttons_layout.setColumnStretch(1, 2)
        buttons_layout.setColumnStretch(2, 1)

        # Combined layout
        servers_widget = QWidget()
        servers_layout = QVBoxLayout()
        servers_layout.addSpacing(-10)
        servers_layout.addWidget(servers_label)
        servers_layout.addWidget(table_group)
        servers_layout.addSpacing(10)
        servers_layout.addLayout(buttons_layout)
        servers_widget.setLayout(servers_layout)

        # --- Tabs organization ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_tab(completion_widget),
                         _('Completion'))
        self.tabs.addTab(self.create_tab(snippets_widget), _('Snippets'))
        self.tabs.addTab(self.create_tab(linting_widget), _('Linting'))
        self.tabs.addTab(self.create_tab(introspection_group, advanced_group),
                         _('Introspection'))
        self.tabs.addTab(self.create_tab(code_style_widget), _('Code style'))
        self.tabs.addTab(self.create_tab(docstring_style_widget),
                         _('Docstring style'))
        self.tabs.addTab(self.create_tab(clients_group,
                                         lsp_advanced_group,
                                         kite_group),
                         _('Advanced'))
        self.tabs.addTab(self.create_tab(servers_widget), _('Other languages'))

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.tabs)
        self.setLayout(vlayout)

    def check_completion_options(self, state):
        """Update enabled status of completion checboxes and spinboxes."""
        state = self.completion_box.isChecked()
        self.completion_hint_box.setEnabled(state)
        self.automatic_completion_box.setEnabled(state)

        state = state and self.automatic_completion_box.isChecked()
        self.completions_after_characters.spinbox.setEnabled(state)
        self.completions_after_characters.plabel.setEnabled(state)
        self.completions_after_ms.spinbox.setEnabled(state)
        self.completions_after_ms.plabel.setEnabled(state)

    def disable_tcp(self, state):
        if state == Qt.Checked:
            self.advanced_host.textbox.setEnabled(False)
            self.advanced_port.spinbox.setEnabled(False)
            self.external_server.stateChanged.disconnect()
            self.external_server.setChecked(False)
            self.external_server.setEnabled(False)
        else:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.external_server.setChecked(False)
            self.external_server.setEnabled(True)
            self.external_server.stateChanged.connect(self.disable_stdio)

    def disable_stdio(self, state):
        if state == Qt.Checked:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.advanced_module.textbox.setEnabled(False)
            self.use_stdio.stateChanged.disconnect()
            self.use_stdio.setChecked(False)
            self.use_stdio.setEnabled(False)
        else:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.advanced_module.textbox.setEnabled(True)
            self.use_stdio.setChecked(False)
            self.use_stdio.setEnabled(True)
            self.use_stdio.stateChanged.connect(self.disable_tcp)

    @Slot(str)
    def setup_docstring_style_convention(self, text):
        """Handle convention changes."""
        if text == 'Custom':
            self.docstring_style_select.label.setText(
                _("Show the following errors:"))
            self.docstring_style_ignore.label.setText(
                _("Ignore the following errors:"))
        else:
            self.docstring_style_select.label.setText(
                _("Show the following errors in addition "
                  "to the specified convention:"))
            self.docstring_style_ignore.label.setText(
                _("Ignore the following errors in addition "
                  "to the specified convention:"))

    @Slot(bool)
    def show_advanced_warning(self, state):
        """
        Show a warning when trying to modify the PyLS advanced
        settings.
        """
        # Don't show warning if the option is already enabled.
        # This avoids showing it when the Preferences dialog
        # is created.
        if self.get_option('advanced/enabled'):
            return

        # Show warning when toggling the button state
        if state:
            QMessageBox.warning(
                self,
                _("Warning"),
                _("<b>Modifying these options can break code completion!!</b>"
                  "<br><br>"
                  "If that's the case, please reset your Spyder preferences "
                  "by going to the menu"
                  "<br><br>"
                  "<tt>Tools > Reset Spyder to factory defaults</tt>"
                  "<br><br>"
                  "instead of reporting a bug."))

    def reset_to_default(self):
        CONF.reset_to_defaults(section='lsp-server')
        self.table.load_servers()
        self.load_from_conf()
        self.set_modified(True)

    def create_new_server(self):
        self.table.show_editor(new_server=True)

    def delete_server(self):
        idx = self.table.currentIndex().row()
        self.table.delete_server(idx)
        self.set_modified(True)
        self.delete_btn.setEnabled(False)

    def create_new_snippet(self):
        self.snippets_table.show_editor(new_snippet=True)

    def delete_snippet(self):
        idx = self.snippets_table.currentIndex().row()
        self.snippets_table.delete_snippet(idx)
        self.set_modified(True)
        self.delete_snippet_btn.setEnabled(False)

    def reset_default_snippets(self):
        language = self.snippets_language_cb.currentText()
        default_snippets_lang = SNIPPETS[language.lower()]
        self.snippets_proxy.reload_model(language, default_snippets_lang)
        self.snippets_table.reset_plain()
        self.set_modified(True)

    def export_snippets(self):
        filename, _selfilter = getsavefilename(
            self, _("Save snippets"),
            'spyder_snippets.json',
            filters='JSON (*.json)',
            selectedfilter='',
            options=QFileDialog.HideNameFilterDetails)

        if filename:
            filename = osp.normpath(filename)
            self.snippets_proxy.export_snippets(filename)

    def import_snippets(self):
        filename, _sf = getopenfilename(
            self,
            _("Load snippets"),
            filters='JSON (*.json)',
            selectedfilter='',
            options=QFileDialog.HideNameFilterDetails,
        )

        if filename:
            filename = osp.normpath(filename)
            valid, total, errors = self.snippets_proxy.import_snippets(
                filename)
            modified = True
            if len(errors) == 0:
                QMessageBox.information(self, _('All snippets imported'),
                    _('{0} snippets were loaded successfully').format(valid),
                    QMessageBox.Ok)
            else:
                if 'loading' in errors:
                    modified = False
                    QMessageBox.critical(self, _('JSON malformed'),
                        _('There was an error when trying to load the '
                          'provided JSON file: <tt>{0}</tt>').format(
                              errors['loading']),
                        QMessageBox.Ok
                    )
                elif 'validation' in errors:
                    modified = False
                    QMessageBox.critical(self, _('Invalid snippet file'),
                        _('The provided snippet file does not comply with '
                          'the Spyder JSON snippets spec and therefore it '
                          'cannot be loaded.<br><br><tt>{}</tt>').format(
                              errors['validation']),
                        QMessageBox.Ok
                    )
                elif 'syntax' in errors:
                    syntax_errors = errors['syntax']
                    msg = []
                    for syntax_key in syntax_errors:
                        syntax_err = syntax_errors[syntax_key]
                        msg.append('<b>{0}</b>: {1}'.format(
                            syntax_key, syntax_err))
                    err_msg = '<br>'.join(msg)

                    QMessageBox.warning(self, _('Incorrect snippet format'),
                        _('Spyder was able to load {0}/{1} snippets '
                          'correctly, please check the following snippets '
                          'for any syntax errors: '
                          '<br><br>{2}').format(valid, total, err_msg),
                        QMessageBox.Ok
                    )
            self.set_modified(modified)

    def report_no_external_server(self, host, port, language):
        """
        Report that connection couldn't be established with
        an external server.
        """
        QMessageBox.critical(
            self,
            _("Error"),
            _("It appears there is no {language} language server listening "
              "at address:"
              "<br><br>"
              "<tt>{host}:{port}</tt>"
              "<br><br>"
              "Please verify that the provided information is correct "
              "and try again.").format(host=host, port=port,
                                       language=language.capitalize())
        )

    def report_no_address_change(self):
        """
        Report that server address has no changed after checking the
        external server option.
        """
        QMessageBox.critical(
            self,
            _("Error"),
            _("The address of the external server you are trying to connect "
              "to is the same as the one of the current internal server "
              "started by Spyder."
              "<br><br>"
              "Please provide a different address!")
        )

    def is_valid(self):
        """Check if config options are valid."""
        host = self.advanced_host.textbox.text()

        # If host is not local, the server must be external
        # and we need to automatically check the corresponding
        # option
        if host not in ['127.0.0.1', 'localhost']:
            self.external_server.setChecked(True)

        # Checks for extenal PyLS
        if self.external_server.isChecked():
            port = int(self.advanced_port.spinbox.text())

            # Check that host and port of the current server are
            # different from the new ones provided to connect to
            # an external server.
            lsp = self.main.completions.get_client('lsp')
            pyclient = lsp.clients.get('python')
            if pyclient is not None:
                instance = pyclient['instance']
                if (instance is not None and
                        not pyclient['config']['external']):
                    if (instance.server_host == host and
                            instance.server_port == port):
                        self.report_no_address_change()
                        return False

            # Check connection to LSP server using a TCP socket
            response = check_connection_port(host, port)
            if not response:
                self.report_no_external_server(host, port, 'python')
                return False

        return super(GeneralConfigPage, self).is_valid()

    def apply_settings(self, options):
        # Check regex of code style options
        try:
            code_style_filenames_matches = (
                self.code_style_filenames_match.textbox.text().split(","))
            for match in code_style_filenames_matches:
                re.compile(match.strip())
        except re.error:
            self.set_option('pycodestyle/filename', '')

        try:
            code_style_excludes = (
                self.code_style_exclude.textbox.text().split(","))
            for match in code_style_excludes:
                re.compile(match.strip())
        except re.error:
            self.set_option('pycodestyle/exclude', '')

        # Check regex of docstring style options
        try:
            docstring_style_match = (
                self.docstring_style_match.textbox.text())
            re.compile(docstring_style_match)
        except re.error:
            self.set_option('pydocstyle/match', '')

        try:
            docstring_style_match_dir = (
                self.docstring_style_match.textbox.text())
            re.compile(docstring_style_match_dir)
        except re.error:
            self.set_option('pydocstyle/match_dir', '')

        self.table.save_servers()

        # Update entries in the source menu
        for name, action in self.main.editor.checkable_actions.items():
            if name in options:
                section = self.CONF_SECTION
                if name == 'underline_errors':
                    section = 'editor'

                state = self.get_option(name, section=section)

                # Avoid triggering the action when this action changes state
                # See: spyder-ide/spyder#9915
                action.blockSignals(True)
                action.setChecked(state)
                action.blockSignals(False)

        # TODO: Reset Manager
        self.main.completions.update_configuration()

        # Update editor plugin options
        editor = self.main.editor
        editor_method_sec_opts = {
            'set_code_snippets_enabled': (self.CONF_SECTION, 'code_snippets'),
            'set_hover_hints_enabled':  (self.CONF_SECTION,
                                         'enable_hover_hints'),
            'set_automatic_completions_enabled': ('editor',
                                                  'automatic_completions'),
            'set_completions_hint_enabled': ('editor', 'completions_hint'),
            'set_completions_hint_after_ms': ('editor',
                                              'completions_hint_after_ms'),
            'set_underline_errors_enabled': ('editor', 'underline_errors'),
            'set_automatic_completions_after_chars': (
                'editor', 'automatic_completions_after_chars'),
            'set_automatic_completions_after_ms': (
                'editor', 'automatic_completions_after_ms'),
        }
        for editorstack in editor.editorstacks:
            for method_name, (sec, opt) in editor_method_sec_opts.items():
                if opt in options:
                    method = getattr(editorstack, method_name)
                    method(self.get_option(opt, section=sec))
