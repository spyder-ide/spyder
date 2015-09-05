# -*- coding: utf-8 -*-
#
# Copyright © 2014 Gonzalo Peña (@goanpeca)
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Conda Packager Manager Widget

Maybe this package manager should be shipped as a different module
in pipy? spyder_package_manager? so that spyder updates could
be handled easily?
"""

# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement, print_function
import sys
import platform
import os
import os.path as osp
import json
import shutil

from spyderlib.qt.QtGui import (QGridLayout, QVBoxLayout, QHBoxLayout, QFont,
                                QDialogButtonBox, QToolButton, QLineEdit,
                                QComboBox, QProgressBar, QSpacerItem, QMenu,
                                QPushButton, QPixmap, QIcon, QCheckBox, QLabel,
                                QWidget, QSortFilterProxyModel, QTableView,
                                QAbstractItemView, QDialog, QPalette,
                                QDesktopServices)
from spyderlib.qt.QtCore import (QSize, Qt, QAbstractTableModel, QModelIndex,
                                 QPoint, QUrl, QObject, Signal, QThread,
                                 QByteArray)
from spyderlib.qt.QtNetwork import QNetworkRequest, QNetworkAccessManager
from spyderlib.qt.compat import to_qvariant

from spyderlib.utils import programs
from spyderlib.utils.qthelpers import get_icon, create_action, add_actions
from spyderlib.baseconfig import (get_conf_path, get_translation,
                                  get_image_path, get_module_data_path)
from spyderlib.py3compat import to_text_string, u, is_unicode
from spyderlib.py3compat import configparser as cp

import conda_api_q

_ = get_translation("p_condapackages", dirname="spyderplugins")

CONDA_PATH = programs.find_program('conda')


def sort_versions(versions=(), reverse=False, sep=u'.'):
    """Sort a list of version number strings

    This function ensures that the package sorting based on number name is
    performed correctly when including alpha, dev rc1 etc...
    """
    if versions == []:
        return []

    digits = u'0123456789'

    def toint(x):
        try:
            n = int(x)
        except:
            n = x
        return n
    versions = list(versions)
    new_versions, alpha, sizes = [], set(), set()

    for item in versions:
        it = item.split(sep)
        temp = []
        for i in it:
            x = toint(i)
            if not isinstance(x, int):
                x = u(x)
                middle = x.lstrip(digits).rstrip(digits)
                tail = toint(x.lstrip(digits).replace(middle, u''))
                head = toint(x.rstrip(digits).replace(middle, u''))
                middle = toint(middle)
                res = [head, middle, tail]
                while u'' in res:
                    res.remove(u'')
                for r in res:
                    if is_unicode(r):
                        alpha.add(r)
            else:
                res = [x]
            temp += res
        sizes.add(len(temp))
        new_versions.append(temp)

    # replace letters found by a negative number
    replace_dic = {}
    alpha = sorted(alpha, reverse=True)
    if len(alpha):
        replace_dic = dict(zip(alpha, list(range(-1, -(len(alpha)+1), -1))))

    # Complete with zeros based on longest item and replace alphas with number
    nmax = max(sizes)
    for i in range(len(new_versions)):
        item = []
        for z in new_versions[i]:
            if z in replace_dic:
                item.append(replace_dic[z])
            else:
                item.append(z)

        nzeros = nmax - len(item)
        item += [0]*nzeros
        item += [versions[i]]
        new_versions[i] = item

    new_versions = sorted(new_versions, reverse=reverse)
    return [n[-1] for n in new_versions]

# Constants
COLUMNS = (NAME, DESCRIPTION, VERSION, STATUS, URL, LICENSE, INSTALL,
           REMOVE, UPGRADE, DOWNGRADE, ENDCOL) = list(range(11))
ACTION_COLUMNS = [INSTALL, REMOVE, UPGRADE, DOWNGRADE]
TYPES = (INSTALLED, NOT_INSTALLED, UPGRADABLE, DOWNGRADABLE, ALL_INSTALLABLE,
         ALL, NOT_INSTALLABLE, MIXGRADABLE, CREATE, CLONE,
         REMOVE_ENV) = list(range(11))
COMBOBOX_VALUES_ORDERED = [_(u'Installed'), _(u'Not installed'),
                           _(u'Upgradable'), _(u'Downgradable'),
                           _(u'All instalable'), _(u'All')]
COMBOBOX_VALUES = dict(zip(COMBOBOX_VALUES_ORDERED, TYPES))
HIDE_COLUMNS = [STATUS, URL, LICENSE]
ROOT = 'root'


class CondaPackagesModel(QAbstractTableModel):
    """Abstract Model to handle the packages in a conda environment"""
    def __init__(self, parent, packages_names, packages_versions, row_data):
        super(CondaPackagesModel, self).__init__(parent)
        self._parent = parent
        self._packages_names = packages_names
        self._packages_versions = packages_versions
        self._rows = row_data

        self._icons = {
            'upgrade.active': get_icon('conda_upgrade_active.png'),
            'upgrade.inactive': get_icon('conda_upgrade_inactive.png'),
            'upgrade.pressed': get_icon('conda_upgrade_pressed.png'),
            'downgrade.active': get_icon('conda_downgrade_active.png'),
            'downgrade.inactive': get_icon('conda_downgrade_inactive.png'),
            'downgrade.pressed': get_icon('conda_downgrade_pressed.png'),
            'add.active': get_icon('conda_add_active.png'),
            'add.inactive': get_icon('conda_add_inactive.png'),
            'add.pressed': get_icon('conda_add_pressed.png'),
            'remove.active': get_icon('conda_remove_active.png'),
            'remove.inactive': get_icon('conda_remove_inactive.png'),
            'remove.pressed': get_icon('conda_remove_pressed.png')}

    def _update_cell(self, row, column):
        start = self.index(row, column)
        end = self.index(row, column)
        self.dataChanged.emit(start, end)

    def flags(self, index):
        """Override Qt method"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        column = index.column()
        if column in (NAME, DESCRIPTION, VERSION):
            return Qt.ItemFlags(Qt.ItemIsEnabled)
        elif column in ACTION_COLUMNS:
            return Qt.ItemFlags(Qt.ItemIsEnabled)
        elif column == ENDCOL:
            return Qt.ItemFlags(Qt.NoItemFlags)
        else:
            return Qt.ItemFlags(Qt.ItemIsEnabled)

    def data(self, index, role=Qt.DisplayRole):
        """Override Qt method"""
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return to_qvariant()

        row = index.row()
        column = index.column()

        # Carefull here with the order, this has to be adjusted manually
        if self._rows[row] == row:
            [name, description, version, status, url, license_, i, r, u, d] =\
                [u'', u'', '-', -1, u'', u'', False, False, False, False]
        else:
            [name, description, version, status, url, license_, i, r, u,
             d] = self._rows[row]

        if role == Qt.DisplayRole:
            if column == NAME:
                return to_qvariant(name)
            elif column == VERSION:
                return to_qvariant(version)
            elif column == STATUS:
                return to_qvariant(status)
            elif column == DESCRIPTION:
                return to_qvariant(description)
        elif role == Qt.TextAlignmentRole:
            if column in [NAME, DESCRIPTION]:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))
            else:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        elif role == Qt.DecorationRole:
            if column == INSTALL:
                if status == NOT_INSTALLED:
                    if i:
                        return to_qvariant(self._icons['add.pressed'])
                    else:
                        return to_qvariant(self._icons['add.active'])
                else:
                    return to_qvariant(self._icons['add.inactive'])
            elif column == REMOVE:
                if (status == INSTALLED or status == UPGRADABLE or
                        status == DOWNGRADABLE or status == MIXGRADABLE):
                    if r:
                        return to_qvariant(self._icons['remove.pressed'])
                    else:
                        return to_qvariant(self._icons['remove.active'])
                else:
                    return to_qvariant(self._icons['remove.inactive'])
            elif column == UPGRADE:
                if status == UPGRADABLE or status == MIXGRADABLE:
                    if u:
                        return to_qvariant(self._icons['upgrade.pressed'])
                    else:
                        return to_qvariant(self._icons['upgrade.active'])
                else:
                    return to_qvariant(self._icons['upgrade.inactive'])
            elif column == DOWNGRADE:
                if status == DOWNGRADABLE or status == MIXGRADABLE:
                    if d:
                        return to_qvariant(self._icons['downgrade.pressed'])
                    else:
                        return to_qvariant(self._icons['downgrade.active'])
                else:
                    return to_qvariant(self._icons['downgrade.inactive'])
        elif role == Qt.ToolTipRole:
            if column == INSTALL and status == NOT_INSTALLED:
                return to_qvariant(_('Install package'))
            elif column == REMOVE and (status == INSTALLED or
                                       status == UPGRADABLE or
                                       status == DOWNGRADABLE or
                                       status == MIXGRADABLE):
                return to_qvariant(_('Remove package'))
            elif column == UPGRADE and (status == INSTALLED or
                                        status == UPGRADABLE or
                                        status == MIXGRADABLE):
                return to_qvariant(_('Upgrade package'))
            elif column == DOWNGRADE and (status == INSTALLED or
                                          status == DOWNGRADABLE or
                                          status == MIXGRADABLE):
                return to_qvariant(_('Downgrade package'))
        elif role == Qt.ForegroundRole:
            palette = QPalette()
            if column in [NAME, DESCRIPTION, VERSION]:
                if status in [INSTALLED, UPGRADABLE, DOWNGRADABLE,
                              MIXGRADABLE]:
                    color = palette.color(QPalette.WindowText)
                    return to_qvariant(color)
                elif status in [NOT_INSTALLED, NOT_INSTALLABLE]:
                    color = palette.color(QPalette.Mid)
                    return to_qvariant(color)
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Override Qt method"""
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
        elif role == Qt.ToolTipRole:
            column = section
            if column == INSTALL:
                return to_qvariant(_('Install package'))
            elif column == REMOVE:
                return to_qvariant(_('Remove package'))
            elif column == UPGRADE:
                return to_qvariant(_('Upgrade package'))
            elif column == DOWNGRADE:
                return to_qvariant(_('Downgrade package'))

        if orientation == Qt.Horizontal:
            if section == NAME:
                return to_qvariant(_("Name"))
            elif section == VERSION:
                return to_qvariant(_("Version"))
            elif section == DESCRIPTION:
                return to_qvariant(_("Description"))
            elif section == STATUS:
                return to_qvariant(_("Status"))
            elif section == INSTALL:
                return to_qvariant(_("I"))
            elif section == REMOVE:
                return to_qvariant(_("R"))
            elif section == UPGRADE:
                return to_qvariant(_("U"))
            elif section == DOWNGRADE:
                return to_qvariant(_("D"))
            else:
                return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        """Override Qt method"""
        return len(self._packages_names)

    def columnCount(self, index=QModelIndex()):
        """Override Qt method"""
        return len(COLUMNS)

    def row(self, rownum):
        """ """
        return self._rows[rownum]

    def first_index(self):
        """ """
        return self.index(0, 0)

    def last_index(self):
        """ """
        return self.index(self.rowCount() - 1, self.columnCount() - 1)

    def update_row_icon(self, row, column):
        """ """
        if column in ACTION_COLUMNS:
            r = self._rows[row]
            actual_state = r[column]
            r[column] = not actual_state
            self._rows[row] = r
            self._update_cell(row, column)

    def is_installable(self, model_index):
        """ """
        row = model_index.row()
        status = self._rows[row][STATUS]
        return status == NOT_INSTALLED

    def is_removable(self, model_index):
        """ """
        row = model_index.row()
        status = self._rows[row][STATUS]
        return status in [UPGRADABLE, DOWNGRADABLE, INSTALLED, MIXGRADABLE]

    def is_upgradable(self, model_index):
        """ """
        row = model_index.row()
        status = self._rows[row][STATUS]
        return status == UPGRADABLE or status == MIXGRADABLE

    def is_downgradable(self, model_index):
        """ """
        row = model_index.row()
        status = self._rows[row][STATUS]
        return status == DOWNGRADABLE or status == MIXGRADABLE

    def get_package_versions(self, name, versiononly=True):
        """ Gives all the compatible package canonical name

            name : str
                name of the package
            versiononly : bool
                if True, returns version number only, otherwise canonical name
        """
        versions = self._packages_versions
        if name in versions:
            if versiononly:
                ver = versions[name]
                temp = []
                for ve in ver:
                    n, v, b = conda_api_q.split_canonical_name(ve)
                    temp.append(v)
                return temp
            else:
                return versions[name]
        else:
            return []

    def get_package_version(self, name):
        """  """
        packages = self._packages_names
        if name in packages:
            rownum = packages.index(name)
            return self.row(rownum)[VERSION]
        else:
            return u''


class MultiColumnSortFilterProxy(QSortFilterProxyModel):
    """Implements a QSortFilterProxyModel that allows for custom filtering.

    Add new filter functions using add_filter_function(). New functions should
    accept two arguments, the column to be filtered and the currently set
    filter string, and should return True to accept the row, False otherwise.

    Filter functions are stored in a dictionary for easy removal by key. Use
    the add_filter_function() and remove_filter_function() methods for access.

    The filterString is used as the main pattern matching string for filter
    functions. This could easily be expanded to handle regular expressions if
    needed.

    Copyright https://gist.github.com/dbridges/4732790
    """
    def __init__(self, parent=None):
        super(MultiColumnSortFilterProxy, self).__init__(parent)
        # if parent is stored as self.parent then PySide gives the following 
        # TypeError: 'CondaPackagesTable' object is not callable
        self._parent = parent
        self._filter_string = ''
        self._filter_status = ALL
        self._filter_functions = {}

    def set_filter(self, text, status):
        """
        text : string
            The string to be used for pattern matching.
        status : int
            TODO: add description
        """
        self._filter_string = text.lower()
        self._filter_status = status
        self.invalidateFilter()

    def add_filter_function(self, name, new_function):
        """
        name : hashable object
            The object to be used as the key for
            this filter function. Use this object
            to remove the filter function in the future.
            Typically this is a self descriptive string.

        new_function : function
            A new function which must take two arguments,
            the row to be tested and the ProxyModel's current
            filterString. The function should return True if
            the filter accepts the row, False otherwise.

            ex:
            model.add_filter_function(
                'test_columns_1_and_2',
                lambda r,s: (s in r[1] and s in r[2]))
        """
        self._filter_functions[name] = new_function
        self.invalidateFilter()

    def remove_filter_function(self, name):
        """Removes the filter function associated with name, if it exists

        name : hashable object
        """
        if name in self._filter_functions.keys():
            del self._filter_functions[name]
            self.invalidateFilter()

    def filterAcceptsRow(self, row_num, parent):
        """Qt override

        Reimplemented from base class to allow the use of custom filtering
        """
        model = self.sourceModel()

        # The source model should have a method called row()
        # which returns the table row as a python list.
        tests = [func(model.row(row_num), self._filter_string,
                 self._filter_status) for func in
                 self._filter_functions.values()]

        return False not in tests  # Changes this to any or all!


class CondaPackagesTable(QTableView):
    """ """
    WIDTH_NAME = 120
    WIDTH_ACTIONS = 24
    WIDTH_VERSION = 70

    def __init__(self, parent):
        super(CondaPackagesTable, self).__init__(parent)
        self._parent = parent
        self._searchbox = u''
        self._filterbox = ALL
        self.row_count = None

        # To manage icon states
        self._model_index_clicked = None
        self.valid = False
        self.column_ = None
        self.current_index = None

        # To prevent triggering the keyrelease after closing a dialog
        # but hititng enter on it
        self.pressed_here = False

        self.source_model = None
        self.proxy_model = None

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._palette = QPalette()

        # Header setup
        self._hheader = self.horizontalHeader()
        self._hheader.setResizeMode(self._hheader.Fixed)
        self._hheader.setStyleSheet("""QHeaderView {border: 0px;
                                              border-radius: 0px;};""")
        self.setPalette(self._palette)
        self.sortByColumn(NAME, Qt.AscendingOrder)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def setup_model(self, packages_names, packages_versions, row_data):
        """ """
        self.proxy_model = MultiColumnSortFilterProxy(self)
        self.setModel(self.proxy_model)
        self.source_model = CondaPackagesModel(self, packages_names,
                                               packages_versions, row_data)
        self.proxy_model.setSourceModel(self.source_model)
        self.hide_columns()
        
        # Custom Proxy Model setup
        self.proxy_model.setDynamicSortFilter(True)

        filter_text = \
            (lambda row, text, status: (
             all([t in row[NAME].lower() for t in
                 to_text_string(text).lower().split()]) or
             all([t in row[DESCRIPTION].lower() for t in
                 to_text_string(text).split()])))

        filter_status = (lambda row, text, status: to_text_string(row[STATUS])
                         in to_text_string(status))
        self.model().add_filter_function('status-search', filter_status)
        self.model().add_filter_function('text-search', filter_text)

        # signals and slots
        self.verticalScrollBar().valueChanged.connect(self.resize_rows)

    def resize_rows(self):
        """ """
        delta_y = 10
        height = self.height()
        y = 0
        while y < height:
            row = self.rowAt(y)
            self.resizeRowToContents(row)
            row_height = self.rowHeight(row)
            self.setRowHeight(row, row_height + delta_y)
            y += self.rowHeight(row) + delta_y

    def hide_columns(self):
        """ """
        for col in HIDE_COLUMNS:
            self.hideColumn(col)

    def filter_changed(self):
        """Trigger the filter"""
        group = self._filterbox
        text = self._searchbox

        if group in [ALL]:
            group = ''.join([to_text_string(INSTALLED),
                             to_text_string(UPGRADABLE),
                             to_text_string(NOT_INSTALLED),
                             to_text_string(DOWNGRADABLE),
                             to_text_string(MIXGRADABLE),
                             to_text_string(NOT_INSTALLABLE)])
        elif group in [INSTALLED]:
            group = ''.join([to_text_string(INSTALLED),
                             to_text_string(UPGRADABLE),
                             to_text_string(DOWNGRADABLE),
                             to_text_string(MIXGRADABLE)])
        elif group in [UPGRADABLE]:
            group = ''.join([to_text_string(UPGRADABLE),
                             to_text_string(MIXGRADABLE)])
        elif group in [DOWNGRADABLE]:
            group = ''.join([to_text_string(DOWNGRADABLE),
                             to_text_string(MIXGRADABLE)])
        elif group in [ALL_INSTALLABLE]:
            group = ''.join([to_text_string(INSTALLED),
                             to_text_string(UPGRADABLE),
                             to_text_string(NOT_INSTALLED),
                             to_text_string(DOWNGRADABLE),
                             to_text_string(MIXGRADABLE)])
        else:
            group = to_text_string(group)

        if self.proxy_model is not None:
            self.proxy_model.set_filter(text, group)
            self.resize_rows()

        # update label count
        count = self.verticalHeader().count()
        if count == 0:
            count_text = _("0 packages available ")
        elif count == 1:
            count_text = _("1 package available ")
        elif count > 1:
            count_text = str(count) + _(" packages available ")

        if text != '':
            count_text = count_text + _('matching "{0}"').format(text)

        self._parent._update_status(status=count_text, hide=False)

    def search_string_changed(self, text):
        """ """
        text = to_text_string(text)
        self._searchbox = text
        self.filter_changed()

    def filter_status_changed(self, text):
        """ """
        for key, val in COMBOBOX_VALUES.iteritems():
            if str(val) == to_text_string(text):
                group = val
                break
        self._filterbox = group
        self.filter_changed()

    def resizeEvent(self, event):
        """Override Qt method"""
        w = self.width()
        self.setColumnWidth(NAME, self.WIDTH_NAME)
        self.setColumnWidth(VERSION, self.WIDTH_VERSION)
        w_new = w - (self.WIDTH_NAME + self.WIDTH_VERSION +
                     (len(ACTION_COLUMNS) + 1)*self.WIDTH_ACTIONS)
        self.setColumnWidth(DESCRIPTION, w_new)

        for col in ACTION_COLUMNS:
            self.setColumnWidth(col, self.WIDTH_ACTIONS)
        QTableView.resizeEvent(self, event)
        self.resize_rows()

    def keyPressEvent(self, event):
        """Override Qt method"""
        QTableView.keyPressEvent(self, event)
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            index = self.currentIndex()
            self.action_pressed(index)
            self.pressed_here = True

    def keyReleaseEvent(self, event):
        """Override Qt method"""
        QTableView.keyReleaseEvent(self, event)
        if event.key() in [Qt.Key_Enter, Qt.Key_Return] and self.pressed_here:
            self.action_released()
        self.pressed_here = False

    def mousePressEvent(self, event):
        """Override Qt method"""
        QTableView.mousePressEvent(self, event)
        self.current_index = self.currentIndex()

        if event.button() == Qt.LeftButton:
            pos = QPoint(event.x(), event.y())
            index = self.indexAt(pos)
            self.action_pressed(index)
        elif event.button() == Qt.RightButton:
            self.context_menu_requested(event)

    def mouseReleaseEvent(self, event):
        """Override Qt method"""
        if event.button() == Qt.LeftButton:
            self.action_released()

    def action_pressed(self, index):
        """ """
        column = index.column()
        
        if self.proxy_model is not None:
            model_index = self.proxy_model.mapToSource(index)
            model = self.source_model
    
            self._model_index_clicked = model_index
            self.valid = False
    
            if ((column == INSTALL and model.is_installable(model_index)) or
               (column == REMOVE and model.is_removable(model_index)) or
               (column == UPGRADE and model.is_upgradable(model_index)) or
                    (column == DOWNGRADE and model.is_downgradable(model_index))):
    
                model.update_row_icon(model_index.row(), model_index.column())
                self.valid = True
                self.column_ = column
            else:
                self._model_index_clicked = None
                self.valid = False

    def action_released(self):
        """ """
        model_index = self._model_index_clicked
        if model_index:
            self.source_model.update_row_icon(model_index.row(),
                                              model_index.column())
            if self.valid:

                name = self.source_model.row(model_index.row())[NAME]
                versions = self.source_model.get_package_versions(name)
                version = self.source_model.get_package_version(name)
                action = self.column_

                self._parent._run_action(name, action, version, versions)

    def context_menu_requested(self, event):
        """ Custom context menu"""
        index = self.current_index
        model_index = self.proxy_model.mapToSource(index)
        row = self.source_model.row(model_index.row())

        name, license_ = row[NAME], row[LICENSE]
        pos = QPoint(event.x(), event.y())
        self._menu = QMenu(self)

        metadata = self._parent.get_package_metadata(name)
        pypi = metadata['pypi']
        home = metadata['home']
        dev = metadata['dev']
        docs = metadata['docs']

        q_pypi = QIcon(get_image_path('python.png'))
        q_home = QIcon(get_image_path('home.png'))
        q_docs = QIcon(get_image_path('conda_docs.png'))

        if 'git' in dev:
            q_dev = QIcon(get_image_path('conda_github.png'))
        elif 'bitbucket' in dev:
            q_dev = QIcon(get_image_path('conda_bitbucket.png'))
        else:
            q_dev = QIcon()

        if 'mit' in license_.lower():
            lic = 'http://opensource.org/licenses/MIT'
        elif 'bsd' == license_.lower():
            lic = 'http://opensource.org/licenses/BSD-3-Clause'
        else:
            lic = None

        actions = []

        if license_ != '':
            actions.append(create_action(self, _('License: ' + license_),
                                         icon=QIcon(), triggered=lambda:
                                         self.open_url(lic)))
            actions.append(None)

        if pypi != '':
            actions.append(create_action(self, _('Python Package Index'),
                                         icon=q_pypi, triggered=lambda:
                                         self.open_url(pypi)))
        if home != '':
            actions.append(create_action(self, _('Homepage'),
                                         icon=q_home, triggered=lambda:
                                         self.open_url(home)))
        if docs != '':
            actions.append(create_action(self, _('Documentation'),
                                         icon=q_docs, triggered=lambda:
                                         self.open_url(docs)))
        if dev != '':
            actions.append(create_action(self, _('Development'),
                                         icon=q_dev, triggered=lambda:
                                         self.open_url(dev)))
        if len(actions):
            add_actions(self._menu, actions)
            self._menu.popup(self.viewport().mapToGlobal(pos))

    def open_url(self, url):
        """Open link from action in default operating system  browser"""
        if url is None:
            return
        QDesktopServices.openUrl(QUrl(url))


class DownloadManager(QObject):
    """Synchronous download manager

    used http://qt-project.org/doc/qt-4.8/
    network-downloadmanager-downloadmanager-cpp.html

    as inspiration
    """
    def __init__(self, parent, on_finished_func, on_progress_func, save_path):
        super(DownloadManager, self).__init__(parent)
        self._parent = parent

        self._on_finished_func = on_finished_func
        self._on_progress_func = on_progress_func

        self._manager = QNetworkAccessManager(self)
        self._request = None
        self._reply = None
        self._queue = None         # [['filename', 'uri'], ...]
        self._url = None           # current url in process
        self._filename = None      # current filename in process
        self._save_path = None     # current defined save path
        self._error = None         # error number
        self._free = True          # lock process flag

        self.set_save_path(save_path)

    def _start_next_download(self):
        """ """
        if self._free:
            if len(self._queue) != 0:
                self._free = False
                self._filename, self._url = self._queue.pop(0)
                full_path = osp.join(self._save_path, self._filename)

                if osp.isfile(full_path):
                    # compare file versions by getting headers first
                    self._get(header_only=True)
                else:
                    # file does not exists, first download
                    self._get()
                # print(full_path)
            else:
                self._on_finished_func()

    def _get(self, header_only=False):
        """Download file specified by uri"""
        self._request = QNetworkRequest(QUrl(self._url))
        self._reply = None
        self._error = None

        if header_only:
            self._reply = self._manager.head(self._request)
            self._reply.finished.connect(self._on_downloaded_headers)
        else:
            self._reply = self._manager.get(self._request)
            self._reply.finished.connect(self._on_downloaded)

        self._reply.downloadProgress.connect(self._on_progress)

    def _on_downloaded_headers(self):
        """On header from uri downloaded"""
        # handle error for headers...
        error_code = self._reply.error()
        if error_code > 0:
            self._on_errors(error_code)
            return None

        fullpath = osp.join(self._save_path, self._filename)
        headers = {}
        data = self._reply.rawHeaderPairs()

        for d in data:
            if isinstance(d[0], QByteArray):
                d = [d[0].data(), d[1].data()]
            key = to_text_string(d[0], encoding='ascii')
            value = to_text_string(d[1], encoding='ascii')
            headers[key.lower()] = value

        if len(headers) != 0:
            header_filesize = int(headers['content-length'])
            local_filesize = int(osp.getsize(fullpath))

            if header_filesize == local_filesize:
                self._free = True
                self._start_next_download()
            else:
                self._get()

    def _on_downloaded(self):
        """On file downloaded"""
        # check if errors
        error_code = self._reply.error()
        if error_code > 0:
            self._on_errors(error_code)
            return None

        # process data if no errors
        data = self._reply.readAll()

        self._save_file(data)

    def _on_errors(self, e):
        """On download errors"""
        self._free = True  # otherwise update button cannot work!
        self._error = e
        self._on_finished_func()

    def _on_progress(self, downloaded_size, total_size):
        """On Partial progress"""
        self._on_progress_func([downloaded_size, total_size])

    def _save_file(self, data):
        """ """
        if not osp.isdir(self._save_path):
            os.mkdir(self._save_path)

        fullpath = osp.join(self._save_path, self._filename)

        if isinstance(data, QByteArray):
            data = data.data()

        with open(fullpath, 'wb') as f:
            f.write(data)

        self._free = True
        self._start_next_download()

    # public api
    # ----------
    def set_save_path(self, path):
        """ """
        self._save_path = path

    def set_queue(self, queue):
        """[['filename', 'uri'], ['filename', 'uri'], ...]"""
        self._queue = queue

    def get_errors(self):
        """ """
        return self._error

    def start_download(self):
        """ """
        self._start_next_download()

    def stop_download(self):
        """ """
        pass


class SearchLineEdit(QLineEdit):
    """Line edit search widget with icon and remove all button"""
    def __init__(self, parent, icon=True):
        super(SearchLineEdit, self).__init__(parent)
        self.setTextMargins(1, 0, 20, 0)

        if icon:
            self.setTextMargins(18, 0, 20, 0)
            self._label = QLabel(self)
            self._pixmap_icon = QPixmap(get_image_path('conda_search.png',
                                                       'png'))
            self._label.setPixmap(self._pixmap_icon)
            self._label.setStyleSheet('''border: 0px; padding-bottom: 2px;
                                      padding-left: 1px;''')

        self._pixmap = QPixmap(get_image_path(('conda_del.png')))
        self.button_clear = QToolButton(self)
        self.button_clear.setIcon(QIcon(self._pixmap))
        self.button_clear.setIconSize(QSize(18, 18))
        self.button_clear.setCursor(Qt.ArrowCursor)
        self.button_clear.setStyleSheet("""QToolButton
            {background: transparent;
            padding: 0px; border: none; margin:0px; }""")
        self.button_clear.setVisible(False)

        # signals and slots
        self.button_clear.clicked.connect(self.clear_text)
        self.textChanged.connect(self._toggle_visibility)
        self.textEdited.connect(self._toggle_visibility)

        # layout
        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self.button_clear, 0, Qt.AlignRight)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 2, 2, 0)

    def _toggle_visibility(self):
        """ """
        if len(self.text()) == 0:
            self.button_clear.setVisible(False)
        else:
            self.button_clear.setVisible(True)

    # public api
    # ----------
    def clear_text(self):
        """ """
        self.setText('')
        self.setFocus()


class CondaDependenciesModel(QAbstractTableModel):
    """ """
    def __init__(self, parent, dic):
        super(CondaDependenciesModel, self).__init__(parent)
        self._parent = parent
        self._packages = dic
        self._rows = []
        self._bold_rows = []

        if len(dic) == 0:
            self._rows = [[_(u'Updating dependency list...'), u'']]
            self._bold_rows.append(0)
        else:
            if 'actions' in dic:
                dic = dic['actions']
            titles = {'FETCH': _('Packages to download'),
                      'UNLINK': _('Packages to unlink'),
                      'LINK': _('Packages to link'),
                      'EXTRACT': _('Packages to extract')
                      }
            order = ['FETCH', 'EXTRACT', 'LINK', 'UNLINK']
            row = 0

            for key in order:
                if key in dic:
                    self._rows.append([u(titles[key]), ''])
                    self._bold_rows.append(row)
                    row += 1
                    for item in dic[key]:
                        name, version, build = \
                            conda_api_q.split_canonical_name(item)
                        self._rows.append([name, version])
                        row += 1

    def flags(self, index):
        """Override Qt method"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        column = index.column()
        if column in [0, 1]:
            return Qt.ItemFlags(Qt.ItemIsEnabled)
        else:
            return Qt.ItemFlags(Qt.NoItemFlags)

    def data(self, index, role=Qt.DisplayRole):
        """Override Qt method"""
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return to_qvariant()
        row = index.row()
        column = index.column()

        # Carefull here with the order, this has to be adjusted manually
        if self._rows[row] == row:
            name, size, = [u'', u'']
        else:
            name, size = self._rows[row]

        if role == Qt.DisplayRole:
            if column == 0:
                return to_qvariant(name)
            elif column == 1:
                return to_qvariant(size)
        elif role == Qt.TextAlignmentRole:
            if column in [0]:
                return to_qvariant(int(Qt.AlignLeft | Qt.AlignVCenter))
            elif column in [1]:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
        elif role == Qt.ForegroundRole:
            return to_qvariant()
        elif role == Qt.FontRole:
            font = QFont()
            if row in self._bold_rows:
                font.setBold(True)
                return to_qvariant(font)
            else:
                font.setBold(False)
                return to_qvariant(font)
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        """Override Qt method"""
        return len(self._rows)

    def columnCount(self, index=QModelIndex()):
        """Override Qt method"""
        return 2

    def row(self, rownum):
        """ """
        return self._rows[rownum]


class CondaPackageActionDialog(QDialog):
    """ """
    def __init__(self, parent, env, name, action, version, versions):
        super(CondaPackageActionDialog, self).__init__(parent)
        self._parent = parent
        self._env = env
        self._version_text = None
        self._name = name
        self._dependencies_dic = {}
        self._conda_process = \
            conda_api_q.CondaProcess(self, self._on_process_finished)

        # widgets
        self.label = QLabel(self)
        self.combobox_version = QComboBox()
        self.label_version = QLabel(self)
        self.widget_version = None
        self.table_dependencies = None

        self.checkbox = QCheckBox(_('Install dependencies (recommended)'))
        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                Qt.Horizontal, self)

        self.button_ok = self.bbox.button(QDialogButtonBox.Ok)
        self.button_cancel = self.bbox.button(QDialogButtonBox.Cancel)

        self.button_cancel.setDefault(True)
        self.button_cancel.setAutoDefault(True)

        dialog_size = QSize(300, 90)

        # helper variable values
        action_title = {UPGRADE: _("Upgrade package"),
                        DOWNGRADE: _("Downgrade package"),
                        REMOVE: _("Remove package"),
                        INSTALL: _("Install package")}

        # Versions might have duplicates from different builds
        versions = sort_versions(list(set(versions)), reverse=True)

        # FIXME: There is a bug, a package installed by anaconda has version
        # astropy 0.4 and the linked list 0.4 but the available versions
        # in the json file do not include 0.4 but 0.4rc1... so...
        # temporal fix is to check if inside list otherwise show full list
        if action == UPGRADE:
            if version in versions:
                index = versions.index(version)
                versions = versions[:index]
            else:
                versions = versions
        elif action == DOWNGRADE:
            if version in versions:
                index = versions.index(version)
                versions = versions[index+1:]
            else:
                versions = versions
        elif action == REMOVE:
            versions = [version]
            self.combobox_version.setEnabled(False)

        if len(versions) == 1:
            if action == REMOVE:
                labeltext = _('Package version to remove:')
            else:
                labeltext = _('Package version available:')
            self.label_version.setText(versions[0])
            self.widget_version = self.label_version
        else:
            labeltext = _("Select package version:")
            self.combobox_version.addItems(versions)
            self.widget_version = self.combobox_version

        self.label.setText(labeltext)
        self.label_version.setAlignment(Qt.AlignLeft)
        self.table_dependencies = QWidget(self)

        self._layout = QGridLayout()
        self._layout.addWidget(self.label, 0, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self._layout.addWidget(self.widget_version, 0, 1, Qt.AlignVCenter |
                               Qt.AlignRight)

        self.widgets = [self.checkbox, self.button_ok, self.widget_version,
                        self.table_dependencies]
        row_index = 1

        # Create a Table
        if action in [INSTALL, UPGRADE, DOWNGRADE]:
            table = QTableView(self)
            dialog_size = QSize(dialog_size.width() + 40, 300)
            self.table_dependencies = table
            row_index = 1
            self._layout.addItem(QSpacerItem(10, 5), row_index, 0)
            self._layout.addWidget(self.checkbox, row_index + 1, 0, 1, 2)
            self.checkbox.setChecked(True)
            self._changed_version(versions[0])

            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.verticalHeader().hide()
            table.horizontalHeader().hide()
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.horizontalHeader().setStretchLastSection(True)

        self._layout.addWidget(self.table_dependencies, row_index + 2, 0, 1, 2,
                         Qt.AlignHCenter)
        self._layout.addItem(QSpacerItem(10, 5), row_index + 3, 0)
        self._layout.addWidget(self.bbox, row_index + 6, 0, 1, 2, Qt.AlignHCenter)

        title = "{0}: {1}".format(action_title[action], name)
        self.setLayout(self._layout)
        self.setMinimumSize(dialog_size)
        self.setFixedSize(dialog_size)
        self.setWindowTitle(title)
        self.setModal(True)

        # signals and slots
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.close)
        self.combobox_version.currentIndexChanged.connect(
            self._changed_version)
        self.checkbox.stateChanged.connect(self._changed_checkbox)

    def _changed_version(self, version, dependencies=True):
        """ """
        self._set_gui_disabled(True)
        install_dependencies = (self.checkbox.checkState() == 2)
        self._version_text = to_text_string(version)
        self._get_dependencies(install_dependencies)

    def _get_dependencies(self, dependencies=True):
        """ """
        name = [self._name + '=' + self._version_text]

        self._conda_process.dependencies(name=self._env, pkgs=name,
                                         dep=dependencies)

    def _changed_checkbox(self, state):
        """ """
        if state:
            self._changed_version(self._version_text)
        else:
            self._changed_version(self._version_text, dependencies=False)

    def _on_process_finished(self, boo):
        """ """
        if self.isVisible():
            dic = self._conda_process.output
            self.dependencies_dic = dic
            self._set_dependencies_table()
            self._set_gui_disabled(False)

    def _set_dependencies_table(self):
        """ """
        table = self.table_dependencies
        dic = self.dependencies_dic
        table.setModel(CondaDependenciesModel(self, dic))
        table.resizeColumnsToContents()
        table.resizeColumnToContents(1)

    def _set_gui_disabled(self, value):
        """ """
        if value:
            table = self.table_dependencies
            table.setModel(CondaDependenciesModel(self, {}))
            table.resizeColumnsToContents()
            table.setDisabled(True)
        else:
            table = self.table_dependencies
            table.setDisabled(False)

        for widget in self.widgets:
            widget.setDisabled(value)


class CondaPackagesWidget(QWidget):
    """Conda Packages Widget"""
    VERSION = '1.0.0'

    # Location of updated repo.json files from continuum/binstar
    CONDA_CONF_PATH = get_conf_path('conda')

    # Location of continuum/anaconda default repos shipped with spyder
    DATA_PATH = get_module_data_path('spyderplugins', 'data')

    # file inside DATA_PATH with metadata for conda packages
    DATABASE_FILE = 'packages.ini'

    def __init__(self, parent):
        super(CondaPackagesWidget, self).__init__(parent)
        self._parent = parent
        self._status = ''  # Statusbar message
        self._conda_process = \
            conda_api_q.CondaProcess(self, self._on_conda_process_ready,
                                     self._on_conda_process_partial)
        self._prefix = conda_api_q.ROOT_PREFIX

        self._download_manager = DownloadManager(self,
                                                 self._on_download_finished,
                                                 self._on_download_progress,
                                                 self.CONDA_CONF_PATH)
        self._thread = QThread(self)
        self._worker = None
        self._db_metadata = cp.ConfigParser()
        self._db_file = CondaPackagesWidget.DATABASE_FILE
        self._db_metadata.readfp(open(osp.join(self.DATA_PATH, self._db_file)))
        self._packages_names = None
        self._row_data = None
        # Hardcoded channels for the moment
        self._default_channels = [
            ['_free_', 'http://repo.continuum.io/pkgs/free'],
            ['_pro_', 'http://repo.continuum.io/pkgs/pro']
            ]

        self._extra_channels = []
        # pyqt not working with ssl some bug here on the anaconda compilation
        # [['binstar_goanpeca_', 'https://conda.binstar.org/goanpeca']]

        self._repo_name = None   # linux-64, win-32, etc...
        self._channels = None    # [['filename', 'channel url'], ...]
        self._repo_files = None  # [filepath, filepath, ...]
        self._packages = {}
        self._download_error = None
        self._error = None

        # defined in self._setup() if None or in self.set_env method
        self._selected_env = None

        # widgets
        self.combobox_filter = QComboBox(self)
        self.button_update = QPushButton(_('Update package index'))
        self.textbox_search = SearchLineEdit(self)

        self.table = CondaPackagesTable(self)
        self.status_bar = QLabel(self)
        self.progress_bar = QProgressBar(self)

        self.widgets = [self.button_update, self.combobox_filter,
                        self.textbox_search, self.table]

        # setup widgets
        self.combobox_filter.addItems([k for k in COMBOBOX_VALUES_ORDERED])
        self.combobox_filter.setCurrentIndex(ALL)
        self.combobox_filter.setMinimumWidth(120)

        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setMaximumWidth(130)

        self.setWindowTitle(_("Conda Packages"))
        self.setMinimumSize(QSize(480, 300))

        # signals and slots
        self.combobox_filter.currentIndexChanged.connect(self.filter_package)
        self.button_update.clicked.connect(self.update_package_index)
        self.textbox_search.textChanged.connect(self.search_package)

        # NOTE: do not try to save the QSpacerItems in a variable for reuse
        # it will crash python on exit if you do!

        # layout setup
        self._spacer_w = 250
        self._spacer_h = 5

        self._top_layout = QHBoxLayout()
        self._top_layout.addWidget(self.combobox_filter)
        self._top_layout.addWidget(self.button_update)
        self._top_layout.addWidget(self.textbox_search)

        self._middle_layout = QVBoxLayout()
        self._middle_layout.addWidget(self.table)

        self._bottom_layout = QHBoxLayout()
        self._bottom_layout.addWidget(self.status_bar, Qt.AlignLeft)
        self._bottom_layout.addWidget(self.progress_bar, Qt.AlignRight)

        self._layout = QVBoxLayout(self)
        self._layout.addItem(QSpacerItem(self._spacer_w, self._spacer_h))
        self._layout.addLayout(self._top_layout)
        self._layout.addLayout(self._middle_layout)
        self._layout.addItem(QSpacerItem(self._spacer_w, self._spacer_h))
        self._layout.addLayout(self._bottom_layout)
        self._layout.addItem(QSpacerItem(self._spacer_w, self._spacer_h))

        self.setLayout(self._layout)
        # setup
        if self._supports_architecture():
            self.update_package_index()
            pass
        else:
            status = _('no packages supported for this architecture!')
            self._update_status(progress=[0, 0], hide=True, status=status)
            
    def _supports_architecture(self):
        """ """
        self._set_repo_name()

        if self._repo_name is None:
            return False
        else:
            return True

    def _set_repo_name(self):
        """Get python system and bitness, and return default repo name"""
        system = sys.platform.lower()
        bitness = 64 if sys.maxsize > 2**32 else 32
        machine = platform.machine()
        fname = [None, None]

        if 'win' in system:
            fname[0] = 'win'
        elif 'lin' in system:
            fname[0] = 'linux'
        elif 'osx' in system or 'darwin' in system:  # TODO: is this correct?
            fname[0] = 'osx'
        else:
            return None

        if bitness == 32:
            fname[1] = '32'
        elif bitness == 64:
            fname[1] = '64'
        else:
            return None

        # armv6l
        if machine.startswith('armv6'):
            fname[1] = 'armv6l'

        self._repo_name = '-'.join(fname)

    def _set_channels(self):
        """ """
        default = self._default_channels
        extra = self._extra_channels
        body = self._repo_name
        tail = '/repodata.json'
        channels = []
        files = []

        for channel in default + extra:
            prefix = channel[0]
            url = '{0}/{1}{2}'.format(channel[1], body, tail)
            name = '{0}{1}.json'.format(prefix, body)
            channels.append([name, url])
            files.append(osp.join(self.CONDA_CONF_PATH, name))

        self._repo_files = files
        self._channels = channels

    def _download_repodata(self):
        """download the latest version available of the repo(s)"""
        status = _('Updating package index...')
        self._update_status(hide=True, progress=[0, 0], status=status)

        self._download_manager.set_queue(self._channels)
        self._download_manager.start_download()

    # --- callback download manager
    # ------------------------------------------------------------------------
    def _on_download_progress(self, progress):
        """function called by download manager when receiving data

        progress : [int, int]
            A two item list of integers with relating [downloaded, total]
        """
        self._update_status(hide=True, progress=progress, status=None)

    def _on_download_finished(self):
        """function called by download manager when finished all downloads

        this will be called even if errors were encountered, so error handling
        is done here as well
        """
        error = self._download_manager.get_errors()

        if error is not None:
            self._update_status(hide=False)

            if not osp.isdir(self.CONDA_CONF_PATH):
                os.mkdir(self.CONDA_CONF_PATH)

            for repo_file in self._repo_files:
                # if a file does not exists, look for one in DATA_PATH
                if not osp.isfile(repo_file):
                    filename = osp.basename(repo_file)
                    bck_repo_file = osp.join(self.DATA_PATH, filename)

                    # if available copy to CONDA_CONF_PATH
                    if osp.isfile(bck_repo_file):
                        shutil.copy(bck_repo_file, repo_file)
                    # otherwise remove from the repo_files list
                    else:
                        self._repo_files.remove(repo_file)
            self._error = None

        self._setup_widget()
    # ------------------------------------------------------------------------

    def _setup_widget(self):
        """ """
        if self._selected_env is None:
            self._selected_env = ROOT
            
        self._thread.terminate()
        self._thread = QThread(self)
        self._worker = Worker(self, self._repo_files, self._selected_env,
                              self._prefix)
        self._worker.sig_status_updated.connect(self._update_status)
        self._worker.sig_ready.connect(self._worker_ready)
        self._worker.sig_ready.connect(self._thread.quit)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker._prepare_model)        
        self._thread.start()

    def _worker_ready(self):
        """ """
        self._packages_names = self._worker.packages_names
        self._packages_versions = self._worker.packages_versions
        self._row_data = self._worker.row_data

        # depending on the size of table this might lock the gui for a moment
        self.table.setup_model(self._packages_names, self._packages_versions,
                               self._row_data)
        self.table.filter_changed()

        self._update_status(hide=False)

    def _update_status(self, status=None, hide=True, progress=None):
        """Update status bar, progress bar display and widget visibility

        status : str
            TODO:
        hide : bool
            TODO:
        progress : [int, int]
            TODO:
        """
        for widget in self.widgets:
            widget.setDisabled(hide)

        self.progress_bar.setVisible(hide)

        if status is not None:
            self._status = status

        self.status_bar.setText(self._status)

        if progress is not None:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(progress[1])
            self.progress_bar.setValue(progress[0])

    def _run_action(self, name, action, version, versions):
        """ """
        env = self._selected_env
        dlg = CondaPackageActionDialog(self, env, name, action, version,
                                       versions)

        if dlg.exec_():
            dic = {}

            self.status = 'Processing'
            self._update_status(hide=True)
            self.repaint()

            env = self._selected_env
            ver1 = dlg.label_version.text()
            ver2 = dlg.combobox_version.currentText()
            pkg = u'{0}={1}{2}'.format(name, ver1, ver2)
            dep = dlg.checkbox.checkState()
            state = dlg.checkbox.isEnabled()
            dlg.close()

            dic['name'] = env
            dic['pkg'] = pkg
            dic['dep'] = not (dep == 0 and state)

            self._run_conda_process(action, dic)

    def _run_conda_process(self, action, dic):
        """ """
        cp = self._conda_process
        name = dic['name']

        if 'pkg' in dic and 'dep' in dic:
            pkgs = dic['pkg']
            dep = dic['dep']

        if action == INSTALL or action == UPGRADE or action == DOWNGRADE:
            status = _('Installing <b>') + dic['pkg'] + '</b>'
            status = status + _(' into <i>') + dic['name'] + '</i>'
            cp.install(name=name, pkgs=[pkgs], dep=dep)
        elif action == REMOVE:
            status = (_('Removing <b>') + dic['pkg'] + '</b>' + _(' from <i>')
                      + dic['name'] + '</i>')
            cp.remove(pkgs, name=name)

    # --- actions to be implemented in case of environment needs
        elif action == CREATE:
            status = _('Creating environment <b>') + dic['name'] + '</b>'
        elif action == CLONE:
            status = (_('Cloning ') + '<i>' + dic['cloned from']
                      + _('</i> into <b>') + dic['name'] + '</b>')
        elif action == REMOVE_ENV:
            status = _('Removing environment <b>') + dic['name'] + '</b>'

        self._update_status(hide=True, status=status, progress=[0, 0])

    def _on_conda_process_ready(self):
        """ """
        error = self._conda_process.error

        if error is None:
            status = _('there was an error')
            self._update_status(hide=False, status=status)
        else:
            self._update_status(hide=True)

        self._setup_widget()

    def _on_conda_process_partial(self):
        """ """
        try:
            partial = self._conda_process.partial.split('\n')[0]
            partial = json.loads(partial)
        except:
            partial = {'progress': 0, 'maxval': 0}

        progress = partial['progress']
        maxval = partial['maxval']

        if 'fetch' in partial:
            status = _('Downloading <b>') + partial['fetch'] + '</b>'
        elif 'name' in partial:
            status = _('Installing and linking <b>') + partial['name'] + '</b>'
        else:
            progress = 0
            maxval = 0
            status = None

        self._update_status(status=status, progress=[progress, maxval])

    # public api
    # ----------
    def update_package_index(self):
        """ """
        self._set_channels()
        self._download_repodata()

    def search_package(self, text):
        """ """
        self.table.search_string_changed(text)

    def filter_package(self, value):
        """ """
        self.table.filter_status_changed(value)

    def get_package_metadata(self, name):
        """ """
        db = self._db_metadata
        metadata = dict(description='', url='', pypi='', home='', docs='',
                        dev='')
        for key in metadata:
            name_lower = name.lower()
            for name_key in (name_lower, name_lower.split('-')[0]):
                try:
                    metadata[key] = db.get(name_key, key)
                    break
                except (cp.NoSectionError, cp.NoOptionError):
                    pass
        return metadata

    def set_environment(self, env):
        """Reset environent to reflect this environment in the pacakge model"""
        # TODO: check if env exists!
        self._selected_env = env
        self._setup_widget()
    

class Worker(QObject):
    """ helper class to preprocess the repodata.json file(s) information into
    an usefull format for the CondaPackagesModel class without blocking the GUI
    in case the number of packages or channels grows too large
    """
    sig_ready = Signal()
    sig_status_updated = Signal(str, bool, list)

    def __init__(self, parent, repo_files, env, prefix):
        QObject.__init__(self)
        self._parent = parent
        self._repo_files = repo_files
        self._env = env
        self._prefix = prefix

        self.packages_names = None
        self.row_data = None
        self.packages_versions = None

        # define helper function locally
        self._get_package_metadata = parent.get_package_metadata

    def _prepare_model(self):
        """ """
        self._load_packages()
        self._setup_data()

    def _load_packages(self):
        """ """
        self.sig_status_updated.emit(_('Loading conda packages...'), True,
                                     [0, 0])
        grouped_usable_packages = {}
        packages_all = []

        for repo_file in self._repo_files:
            with open(repo_file, 'r') as f:
                data = json.load(f)

            # info = data['info']
            packages = data['packages']

            if packages is not None:
                packages_all.append(packages)
                for key in packages:
                    val = packages[key]
                    name = val['name'].lower()
                    grouped_usable_packages[name] = list()

        for packages in packages_all:
            for key in packages:
                val = packages[key]
                name = val['name'].lower()
                grouped_usable_packages[name].append([key, val])

        self._packages = grouped_usable_packages

    def _setup_data(self):
        """ """
        self._packages_names = []
        self._rows = []
        self._packages_versions = {}  # the canonical name of versions compat

        self._packages_linked = {}
        self._packages_versions_number = {}
        self._packages_versions_all = {}  # the canonical name of all versions
        self._packages_upgradable = {}
        self._packages_downgradable = {}
        self._packages_installable = {}
        self._packages_licenses_all = {}
        self._conda_api = conda_api_q

        cp = self._conda_api
        # TODO: Do we want to exclude some packages? If we plan to continue
        # with the projects in spyder idea, we might as well hide spyder
        # from the possible instalable apps...
        # exclude_names = ['emptydummypackage']  # FIXME: packages to exclude?

        # First do the list of linked packages so in case there is no json
        # We can show at least that
        self._packages_linked = {}
        canonical_names = sorted(list(cp.linked(self._prefix)))

        # This has to do with the versions of the selected environment, NOT
        # with the python version running!
        pyver, numpyver, pybuild, numpybuild = None, None, None, None
        for canonical_name in canonical_names:
            n, v, b = cp.split_canonical_name(canonical_name)
            self._packages_linked[n] = [n, v, b, canonical_name]
            if n == 'python':
                pyver = v
                pybuild = b
            elif n == 'numpy':
                numpyver = v
                numpybuild = b

        if self._packages == {}:
            self._packages_names = sorted([l for l in self._packages_linked])
            self._rows = list(range(len(self._packages_names)))
            for n in self._packages_linked:
                val = self._packages_linked[n]
                v = val[-1]
                self._packages[n] = [[v, v]]
        else:
            self._packages_names = sorted([key for key in
                                           self._packages])
            self._rows = list(range(len(self._packages_names)))
            for n in self._packages:
                self._packages_licenses_all[n] = {}

        pybuild = 'py' + ''.join(pyver.split('.'))[:-1] + '_'  # + pybuild
        if numpyver is None and numpybuild is None:
            numpybuild = ''
        else:
            numpybuild = 'np' + ''.join(numpyver.split('.'))[:-1]

        for n in self._packages_names:
            self._packages_versions_all[n] = \
                sort_versions([s[0] for s in self._packages[n]],
                              reverse=True)
            for s in self._packages[n]:
                val = s[1]
                if 'version' in val:
                    ver = val['version']
                    if 'license' in val:
                        lic = val['license']
                        self._packages_licenses_all[n][ver] = lic

        # Now clean versions depending on the build version of python and numpy
        # FIXME: there is an issue here... at this moment a package with same
        # version but only differing in the build number will get added
        # Now it assumes that there is a python installed in the root
        for name in self._packages_versions_all:
            tempver_cano = []
            tempver_num = []
            for ver in self._packages_versions_all[name]:
                n, v, b = cp.split_canonical_name(ver)

                if 'np' in b and 'py' in b:
                    if numpybuild + pybuild in b:
                        tempver_cano.append(ver)
                        tempver_num.append(v)
                elif 'py' in b:
                    if pybuild in b:
                        tempver_cano.append(ver)
                        tempver_num.append(v)
                elif 'np' in b:
                    if numpybuild in b:
                        tempver_cano.append(ver)
                        tempver_num.append(v)
                else:
                    tempver_cano.append(ver)
                    tempver_num.append(v)
            self._packages_versions[name] = sort_versions(tempver_cano,
                                                          reverse=True)
            self._packages_versions_number[name] = sort_versions(tempver_num,
                                                                 reverse=True)

        # FIXME: Check what to do with different builds??
        # For the moment here a set is used to remove duplicate versions
        for n in self._packages_linked:
            vals = self._packages_linked[n]
            canonical_name = vals[-1]
            current_ver = vals[1]
            
            # fix error when package installed from other channels besides
            # the standard ones
            if n in self._packages_versions_number:
                vers = self._packages_versions_number[n]
                vers = sort_versions(list(set(vers)), reverse=True)
    
                self._packages_upgradable[n] = not current_ver == vers[0]
                self._packages_downgradable[n] = not current_ver == vers[-1]

        for row, name in enumerate(self._packages_names):
            if name in self._packages_linked:
                version = self._packages_linked[name][1]
                if (self._packages_upgradable[name] and
                        self._packages_downgradable[name]):
                    status = MIXGRADABLE
                elif self._packages_upgradable[name]:
                    status = UPGRADABLE
                elif self._packages_downgradable[name]:
                    status = DOWNGRADABLE
                else:
                    status = INSTALLED
            else:
                vers = self._packages_versions_number[name]
                vers = sort_versions(list(set(vers)), reverse=True)
                version = '-'

                if len(vers) == 0:
                    status = NOT_INSTALLABLE
                else:
                    status = NOT_INSTALLED

            metadata = self._get_package_metadata(name)
            description = metadata['description']
            url = metadata['url']

            if version in self._packages_licenses_all[name]:
                if self._packages_licenses_all[name][version]:
                    license_ = self._packages_licenses_all[name][version]
                else:
                    license_ = u''
            else:
                license_ = u''

            self._rows[row] = [name, description, version, status, url,
                               license_, False, False, False, False]

        self.row_data = self._rows
        self.packages_names = self._packages_names
        self.packages_versions = self._packages_versions

        self.sig_ready.emit()

# TODO:  update packages.ini file
# TODO: Define some automatic tests that can include the following:

# Test 1
# Find out if all the urls in the packages.ini file lead to a webpage
# or if they produce a 404 error

# Test 2
# Test installation of custom packages

# Test 3
# nothing is loaded on the package listing but clicking on it will produce an
# nonetype error


def test():
    """Run conda packages widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = CondaPackagesWidget(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
