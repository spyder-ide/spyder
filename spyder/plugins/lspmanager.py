# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os
import os.path as osp

# Third party imports
from qtpy import API
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import (Qt, Signal, Slot, QAbstractTableModel, QModelIndex,)
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import (QApplication, QDialog,
                            QGridLayout, QGroupBox, QHBoxLayout,
                            QInputDialog, QLabel, QMenu, QSplitter, QTabWidget,
                            QToolBar, QVBoxLayout, QWidget, QTableView,
                            QAbstractItemView)

# Local imports
from spyder.config.main import CONF
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.plugins.runconfig import (ALWAYS_OPEN_FIRST_RUN_OPTION,
                                      get_run_configuration,
                                      RunConfigDialog, RunConfigOneDialog)
from spyder.utils.code_analysis import (LSPRequestTypes, LSPEventTypes,
                                        TextDocumentSyncKind)
from spyder.utils.code_analysis.lsp_client import LSPClient
from spyder.widgets.helperwidgets import HTMLDelegate


LSP_LANGUAGES = {
    'C#', 'CSS/LESS/SASS', 'Go', 'GraphQL', 'Groovy', 'Haxe', 'HTML',
    'Java', 'JavaScript', 'JSON', 'Julia', 'OCaml', 'PHP',
    'Python', 'Rust', 'Scala', 'Swift', 'TypeScript'
}


# def iter_servers():
#     for option in CONF.options('lsp-server'):


class LSPServer:
    """Convenience class to store LSP Server configuration values."""

    def __init__(self, language='', cmd='', host='127.0.0.1', port='', args='',
                 external=False):
        self.index = 0
        self.language = language
        self.cmd = cmd
        self.args = args
        self.port = port
        self.host = host
        self.external = external

    def __repr__(self):
        base_str = '[{0}] {1} {2} ({3}:{4})'
        fmt_args = [self.language, self.cmd, self.args,
                    self.host, self.port]
        if self.external:
            base_str = '[{0}] {1}:{2}'
            fmt_args = [self.language, self.host, self.port]
        return base_str.format(*fmt_args)

    def __str__(self):
        return self.__repr__()

    def __unicode__(self):
        return self.__repr__()

    def load(self):
        self.cmd = CONF.get('lsp-server', '{0}/cmd'.format(self.language))
        self.args = CONF.get('lsp-server', '{0}/args'.format(self.language))
        self.host = CONF.get('lsp-server', '{0}/host'.format(self.language))
        self.port = CONF.get('lsp-server', '{0}/port'.format(self.language))
        self.external = CONF.get(
            'lsp-server', '{0}/external'.format(self.language))

    def save(self):
        CONF.set('lsp-server', '{0}/cmd'.format(self.language), self.cmd)
        CONF.set('lsp-server', '{0}/args'.format(self.language), self.args)
        CONF.set('lsp-server', '{0}/host'.format(self.language), self.host)
        CONF.set('lsp-server', '{0}/port'.format(self.language), self.port)
        CONF.set('lsp-server', '{0}/external'.format(
            self.language), self.external)


LANGUAGE, ADDR, CMD = [0, 1, 2]


class LSPServersModel(QAbstractTableModel):
    def __init__(self, parent):
        QAbstractTableModel.__init__(self)
        self._parent = parent

        self.servers = []
        # self.scores = []
        self.rich_text = []
        self.normal_text = []
        self.letters = ''
        self.label = QLabel()
        self.widths = []

        # Needed to compensate for the HTMLDelegate color selection unawarness
        palette = parent.palette()
        self.text_color = palette.text().color().name()
        self.text_color_highlight = palette.highlightedText().color().name()

    def current_index(self):
        """Get the currently selected index in the parent table view."""
        i = self._parent.proxy_model.mapToSource(self._parent.currentIndex())
        return i

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
                text = '<tt>{0} {1}</tt>'
                if server.external:
                    text = 'External server'
                return to_qvariant(text.format(server.cmd, server.host))
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

    # def setData(self, index, value, role=Qt.EditRole):
    #     """Qt Override."""
    #     if index.isValid() and 0 <= index.row() < len(self.servers):
    #         server = self.servers[index.row()]
    #         column = index.column()
    #         text = from_qvariant(value, str)
    #         # if column == SEQUENCE:
    #         #     server.key = text
    #         self.dataChanged.emit(index, index)
    #         return True
    #     return False

    def update_active_row(self):
        """Update active row to update color in selected text."""
        self.data(self.current_index())

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
        self.setItemDelegateForColumn(CMD, HTMLDelegate(self, margin=9))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.selectionModel().selectionChanged.connect(self.selection)
        self.verticalHeader().hide()
        self.load_servers()

    def focusOutEvent(self, e):
        """Qt Override."""
        self.source_model.update_active_row()
        super(LSPServerTable, self).focusOutEvent(e)

    def focusInEvent(self, e):
        """Qt Override."""
        super(LSPServerTable, self).focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def selection(self, index):
        """Update selected row."""
        self.update()
        self.isActiveWindow()

    def adjust_cells(self):
        """Adjust column size based on contents."""
        self.resizeColumnsToContents()
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(s.cmd + ' ' * 9) for s in self.source_model.servers]
        self.setColumnWidth(CMD, max(names))
        self.horizontalHeader().setStretchLastSection(True)




class LSPManagerConfigPage(PluginConfigPage):
    """Language Server Protocol client manager preferences."""

    def get_name(self):
        return _('Language Server Protocol Manager')

    def get_icon(self):
        return ima.icon('lspserver')

    def setup_page(self):
        server_group = QGroupBox(_('Available LSP Servers'))
        description = _('To create a new configuration, '
                        'you need to select a programming '
                        'language, along with a executable '
                        'name for the server to execute '
                        '(If the instance is local), '
                        'and the host and port. Finally, '
                        'you\'ll to provide the '
                        'arguments that the server accepts. '
                        'The placeholders <tt>%(host)s</tt> and '
                        '<tt>%(port)s</tt> refer to the host '
                        'and the port, respectively.')
        server_settings_description = QLabel(description)
        server_settings_description.setWordWrap(True)


class LSPManager(SpyderPluginWidget):
    pass
