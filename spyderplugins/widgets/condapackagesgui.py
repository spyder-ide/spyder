# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Packager manager widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement, print_function

from spyderlib.qt.QtGui import (QGroupBox, QDialogButtonBox, QToolButton,
                                QPixmap, QIcon, QHBoxLayout, QGridLayout,
                                QWidget, QMessageBox, QVBoxLayout, QLabel,
                                QTableView, QPushButton, QAbstractItemView,
                                QColor, QBrush, QPainter, QLayout,
                                QSortFilterProxyModel, QLineEdit, QComboBox,
                                QStyle, QFont, QDialog, QSizePolicy, QRegExpValidator)
from spyderlib.qt.QtCore import (QSize, Qt, SIGNAL, QProcess, QByteArray,
                                 QTextCodec, Signal,
                                 QAbstractTableModel, QModelIndex, QRegExp,
                                 QPoint, SLOT)
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import to_qvariant
from spyderlib.utils.qthelpers import get_icon

import sys
import platform
import os
import os.path as osp
import json


# Local imports
from spyderlib import dependencies
from spyderlib.utils import programs
from spyderlib.utils.encoding import to_unicode_from_fs
from spyderlib.utils.qthelpers import get_icon, create_toolbutton
from spyderlib.baseconfig import get_conf_path, get_translation, get_image_path
from spyderlib.widgets.onecolumntree import OneColumnTree
from spyderlib.widgets.texteditor import TextEditor
from spyderlib.widgets.comboboxes import (PythonModulesComboBox,
                                          is_module_or_package)
from spyderlib.py3compat import to_text_string, getcwd, pickle
_ = get_translation("p_condapackages", dirname="spyderplugins")

import conda_api # FIXME:This will reside where???
CONDA_PATH = programs.find_program('conda')  # FIXME: Conda api has similar check

# FIXME: Conda API requires defining this first. Where should I put this?
conda_api.set_root_prefix()


def fetch_repodata(index):
    """
    JSON Repos
    http://repo.continuum.io/pkgs/index.html
    http://repo.continuum.io/pkgs/free/linux-32/repodata.json
    http://repo.continuum.io/pkgs/free/linux-64/repodata.json
    http://repo.continuum.io/pkgs/free/linux-armv6l/repodata.json
    http://repo.continuum.io/pkgs/free/osx-64/repodata.json
    http://repo.continuum.io/pkgs/free/osx-32/repodata.json
    http://repo.continuum.io/pkgs/free/win-32/repodata.json
    http://repo.continuum.io/pkgs/free/win-64/repodata.json
    """
    python_ver = platform.python_version()  # "2.7.3"
    base_uri = 'http://repo.continuum.io/pkgs/free/'
    full_uri = base_uri + index + '/repodata.json'

#    if python_ver.m
    import urllib2
    response = urllib2.urlopen('http://www.example.com/')
    html = response.read()


def get_conda_packages():
    """
    """
    exclude = [u'anaconda', u'_license', u'_windows']
    exclude = []
    system = sys.platform.lower()
    bitness = 64 if sys.maxsize > 2**32 else 32
    fname = [None, None]

    if 'win' in system:
        fname[0] = 'win'
    elif 'lin' in system:
        fname[0] = 'linux'
    elif 'osx' in system:
        fname[0] = 'osx'
    else:
        pass

    if bitness == 32:
        fname[1] = '32'
    elif bitness == 64:
        fname[1] = '64'
    else:
        pass

    fname = '-'.join(fname) + '.json'

    # Try to get file from continuum, if error then get local file
    curdir = os.path.dirname(os.path.realpath(__file__))
    fname = osp.join(curdir, fname)
    with open(fname, 'r') as f:
        data = json.load(f)

    info = data['info']
    packages = data['packages']

    # Now preprocess the data to remove packages not usable given actual
    # python used
    usable_packages = {}
    grouped_usable_packages = {}
#
#    # This has to be outside of here!!!!! FUCK
    for key, val in packages.iteritems():
#        build = val['build'].lower()
        name = val['name'].lower()
#
##        if (python_ver in build or build == '0') and name not in exclude:
        grouped_usable_packages[name] = list()
#        usable_packages[key] = val
#    """
#        'build_number'
#        'name'
#        'license'
#        'depends'
#        'version' The version of the specific package
#        'build'  The python version onto which it was built
#        'size'
#        'md5'
#    """
#    for key, val in usable_packages.iteritems():
    for key, val in packages.iteritems():
        name = val['name'].lower()
        grouped_usable_packages[name].append([key, val])

    return grouped_usable_packages

# Constants
COLUMNS = (NAME, DESCRIPTION, VERSION, STATUS,
           INSTALL, REMOVE, UPGRADE, DOWNGRADE, ENDCOL) = list(range(9))
ACTION_COLUMNS = [INSTALL, REMOVE, UPGRADE, DOWNGRADE]
TYPES = (INSTALLED, NOT_INSTALLED, UPGRADABLE, DOWNGRADABLE,
         ALL, CREATE, CLONE) = list(range(7))
COMBOBOX_VALUES_ORDERED = [u'Installed', u'Not installed', u'Upgradable',
                           u'Downgradable', u'All available']
COMBOBOX_VALUES = dict(zip(COMBOBOX_VALUES_ORDERED, TYPES))
HIDE_COLUMNS = [STATUS]
ROOT = 'root'


class CondaPackagesModel(QAbstractTableModel):
    """ """
    def __init__(self):
        QAbstractTableModel.__init__(self)
        self.__envs = []   # ordered... for combo box
        self.__environments = {}
        self.__environment = ROOT   # Default value
        self.__conda_packages = {}  # Everything from the json file
        self.__packages_names = []
        self.__packages_linked = {}  # Has to be remeptied on __setup_data
        self.__packages_versions = {}
        self.__packages_upgradable = {}
        self.__packages_downgradable = {}
        self.__rows = []

        self.__python_ver = u''

        self.icons = \
            {'upgrade.active': get_icon('conda_upgrade_active.png'),
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

        # Run conda and initial setup
        self.__update_conda_packages()
        self.__get_env_and_prefixes()
        self.__set_env(self.__environment)
        self.__setup_data()

    def __update_conda_packages(self):
        """ """
        self.__conda_packages = get_conda_packages()

    def __get_env_and_prefixes(self):
        """ """
        python_ver = platform.python_version()
        envs = conda_api.get_envs()
        prefixes = ([conda_api.get_prefix_envname(ROOT)] + [k for k in envs])
        environments = [ROOT] + [k.split(osp.sep)[-1] for k in envs]
        self.__environments = dict(zip(environments, prefixes))
        self.__envs = environments
        # FIXME: In case this needs to be changed!
        self.__python_ver = python_ver.replace('.', '')[:-1].lower()

#    def get_package_data(self, package):
#        """ """
#        self.__conda_packages[package]

    def get_package_versions(self, package):
        """ """
        cp = self.__conda_packages[package]
        versions = set()
        for p in cp:
            versions.add(p[-1]['version'])
        return sorted(versions, reverse=True)

    def __setup_data(self):
        """ """
        # Check the python versions and remove the ones that dont comply?
        self.__packages_names = sorted([key for key in self.__conda_packages])
        self.__rows = range(len(self.__packages_names))
        self.__packages_linked = {}

        canonical_names = sorted(list(conda_api.linked(self.__prefix)))

        for canonical_name in canonical_names:
            n, v, b = conda_api.split_canonical_name(canonical_name)
            self.__packages_linked[n] = [n, v, b, canonical_name]

        for n in self.__packages_names:  # key here is the name of package
            self.__packages_versions[n] = sorted([s[0] for s in
                                                 self.__conda_packages[n]],
                                                 reverse=True)
        # FIXME: Check for ale
        for n, vals in self.__packages_linked.iteritems():
            canonical_name = vals[-1]
            vers = self.__packages_versions[n]
            self.__packages_upgradable[n] = not(canonical_name in vers[0])
            self.__packages_downgradable[n] = not(canonical_name in vers[-1])

        for row, name in enumerate(self.__packages_names):
            if name in self.__packages_linked:
                version = self.__packages_linked[name][1]
                if self.__packages_upgradable[name]:
                    status = UPGRADABLE
                elif self.__packages_downgradable[name]:
                    status = DOWNGRADABLE
                else:
                    status = INSTALLED
            else:
                version = '-'
                status = NOT_INSTALLED
            description = name
            self.__rows[row] = [name, description, version, status, False,
                                False, False, False]

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(Qt.ItemIsEnabled)

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        column = index.column()

        # Carefull here with the order, this has to be adjusted manually
        name, description, version, status, i, r, u, d = self.__rows[row]

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
            if column in [NAME, DESCRIPTION, VERSION]:
                return to_qvariant(int(Qt.AlignCenter | Qt.AlignVCenter))
        elif role == Qt.DecorationRole:
            if column == UPGRADE:
                if status == UPGRADABLE:
                    if u:
                        return to_qvariant(self.icons['upgrade.pressed'])
                    else:
                        return to_qvariant(self.icons['upgrade.active'])
                else:
                    return to_qvariant(self.icons['upgrade.inactive'])
            elif column == INSTALL:
                if status == NOT_INSTALLED:
                    if i:
                        return to_qvariant(self.icons['add.pressed'])
                    else:
                        return to_qvariant(self.icons['add.active'])
                else:
                    return to_qvariant(self.icons['add.inactive'])
            elif column == REMOVE:
                if (status == INSTALLED or status == UPGRADABLE or
                   status == DOWNGRADABLE):
                    if r:
                        return to_qvariant(self.icons['remove.pressed'])
                    else:
                        return to_qvariant(self.icons['remove.active'])
                else:
                    return to_qvariant(self.icons['remove.inactive'])
            elif column == DOWNGRADE:
                if status == DOWNGRADABLE:
                    if d:
                        return to_qvariant(self.icons['downgrade.pressed'])
                    else:
                        return to_qvariant(self.icons['downgrade.active'])
                else:
                    return to_qvariant(self.icons['downgrade.inactive'])
        elif role == Qt.ToolTipRole:
            if column == INSTALL and status == NOT_INSTALLED:
                return to_qvariant('Install package')
            elif column == REMOVE and (status == INSTALLED or
                                       status == UPGRADABLE):
                return to_qvariant('Remove package')
            elif column == UPGRADE and (status == INSTALLED or
                                        status == UPGRADABLE):
                return to_qvariant('Upgrade package')
            elif column == DOWNGRADE and (status == INSTALLED or
                                          status == DOWNGRADABLE):
                return to_qvariant('Downgrade package')
        elif role == Qt.ForegroundRole:
            if column == NAME:
                if status in [INSTALLED, UPGRADABLE]:
                    color = QColor(Qt.black)
                    return to_qvariant(color)
                elif status == NOT_INSTALLED:
                    color = QColor(Qt.darkGray)
                    return to_qvariant(color)
        elif role == Qt.FontRole:
            if column == NAME and (status in [INSTALLED, UPGRADABLE]):
                font = QFont()
                font.setBold(False)
                return to_qvariant(font)
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))

        if orientation == Qt.Horizontal:
            if section == NAME:
                return to_qvariant("Name")
            elif section == VERSION:
                return to_qvariant("Version")
            elif section == DESCRIPTION:
                return to_qvariant("Description")
            elif section == STATUS:
                return to_qvariant("Status")
            elif section == UPGRADE:
                return to_qvariant("")
            elif section == INSTALL:
                return to_qvariant("")
            elif section == REMOVE:
                return to_qvariant("")
            elif section == DOWNGRADE:
                return to_qvariant("")
            return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.__packages_names)

    def columnCount(self, index=QModelIndex()):
        return len(COLUMNS)

    def row(self, rownum):
        """ """
        return self.__rows[rownum]

    def __set_env(self, env=ROOT):
        self.__prefix = self.__environments[env]

    def __update_all(self):
        first = self.first_index()
        last = self.last_index()
        self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), first, last)

    def __update_cell(self, row, column):
        start = self.index(row, column)
        end = self.index(row, column)
        self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), start, end)

    # 'public api'
    def refresh_(self):
        self.__update_conda_packages()
        self.__get_env_and_prefixes()
        self.__setup_data()
        self.__update_all()

    def refresh_envs(self):
        """ """
        self.__get_env_and_prefixes()

    def env_changed(self, env):
        self.__set_env(env)
        self.__setup_data()
        self.__update_all()

    def first_index(self):
        return self.index(0, 0)

    def last_index(self):
        return self.index(self.rowCount() - 1, self.columnCount() - 1)

    def update_row_icon(self, row, column):
        """ """
        if column in ACTION_COLUMNS:
            r = self.__rows[row]
            actual_state = r[column]
            r[column] = not actual_state
            self.__rows[row] = r
            self.__update_cell(row, column)

    def is_installable(self, model_index):
        """ """
        row = model_index.row()
        status = self.__rows[row][STATUS]
        return status == NOT_INSTALLED

    def is_removable(self, model_index):
        """ """
        row = model_index.row()
        status = self.__rows[row][STATUS]
        return status in [UPGRADABLE, DOWNGRADABLE, INSTALLED]

    def is_upgradable(self, model_index):
        """ """
        row = model_index.row()
        status = self.__rows[row][STATUS]
        return status == UPGRADABLE

    def is_downgradable(self, model_index):
        """ """
        row = model_index.row()
        status = self.__rows[row][STATUS]
        return status == DOWNGRADABLE

    @property
    def envs(self):
        """ """
        self.__get_env_and_prefixes()
        return self.__envs

    @property
    def environments(self):
        """ """
        self.__get_env_and_prefixes()
        return self.__environments


class MultiColumnSortFilterProxy(QSortFilterProxyModel):
    """
    Copyright https://gist.github.com/dbridges/4732790

    Implements a QSortFilterProxyModel that allows for custom
    filtering. Add new filter functions using addFilterFunction().
    New functions should accept two arguments, the column to be
    filtered and the currently set filter string, and should
    return True to accept the row, False otherwise.

    Filter functions are stored in a dictionary for easy
    removal by key. Use the addFilterFunction() and
    removeFilterFunction() methods for access.

    The filterString is used as the main pattern matching
    string for filter functions. This could easily be expanded
    to handle regular expressions if needed.
    """
    def __init__(self, parent=None):
        super(MultiColumnSortFilterProxy, self).__init__(parent)
        self.filterString = ''
        self.filterStatus = ALL
        self.filterFunctions = {}
        self.table = parent

    def setFilter(self, text, status):
        """
        text : string
            The string to be used for pattern matching.
        status : int
            TODO:
        """
        self.filterString = text
        self.filterStatus = status
        self.invalidateFilter()

    def addFilterFunction(self, name, new_func):
        """
        name : hashable object
            The object to be used as the key for
            this filter function. Use this object
            to remove the filter function in the future.
            Typically this is a self descriptive string.

        new_func : function
            A new function which must take two arguments,
            the row to be tested and the ProxyModel's current
            filterString. The function should return True if
            the filter accepts the row, False otherwise.

            ex:
            model.addFilterFunction(
                'test_columns_1_and_2',
                lambda r,s: (s in r[1] and s in r[2]))
        """
        self.filterFunctions[name] = new_func
        self.invalidateFilter()

    def removeFilterFunction(self, name):
        """
        name : hashable object

        Removes the filter function associated with name,
        if it exists.
        """
        if name in self.filterFunctions.keys():
            del self.filterFunctions[name]
            self.invalidateFilter()

    def filterAcceptsRow(self, row_num, parent):
        """
        Reimplemented from base class to allow the use
        of custom filtering.
        """
        model = self.sourceModel()

        # The source model should have a method called row()
        # which returns the table row as a python list.
        tests = [func(model.row(row_num), self.filterString, self.filterStatus)
                 for func in self.filterFunctions.values()]
        return not (False in tests)


class CondaPackagesTable(QTableView):
    """ """
    WIDTH_NAME = 120
    WIDTH_ACTIONS = 24
    WIDTH_VERSION = 70

    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self.parent = parent
        self.__searchbox = u''
        self.__filterbox = ALL
        self.__envbox = ROOT

        # To manage icon states
        self.__model_index_clicked = None
        self.valid = False
        self.column = None

        self.source_model = None
        self.proxy_model = None

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Header setup
        hheader = self.horizontalHeader()
        hheader.setResizeMode(hheader.Fixed)
        hheader.setStyleSheet("""
        QHeaderView {
            border: 0px solid black;
            border-radius: 0px;
            background-color: rgb(200, 200, 255);
            font-weight: Normal;
            };
        """)
        self.sortByColumn(NAME, Qt.AscendingOrder)
        self.setMouseTracking(True)

    def setup_model(self):
        """ """
        self.proxy_model = MultiColumnSortFilterProxy(self)
        self.setModel(self.proxy_model)
        self.source_model = CondaPackagesModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.hide_columns()

        # Custom Proxy Model setup
        self.proxy_model.setDynamicSortFilter(True)
        filter_text = (lambda row, text, status: (text in row[NAME] or
                       text in row[DESCRIPTION]))
        filter_status = (lambda row, text, status: to_text_string(row[STATUS])
                         in to_text_string(status))
        self.model().addFilterFunction('status search', filter_status)
        self.model().addFilterFunction('text search', filter_text)

    def hide_columns(self):
        """ """
        for col in HIDE_COLUMNS:
            self.hideColumn(col)

    def filter_changed(self):
        """ """
        status = self.__filterbox
        text = self.__searchbox
        if status in [ALL]:
            status = ''.join([to_text_string(INSTALLED),
                             to_text_string(UPGRADABLE),
                             to_text_string(NOT_INSTALLED),
                             to_text_string(DOWNGRADABLE)])
        if status in [INSTALLED]:
            status = ''.join([to_text_string(INSTALLED),
                              to_text_string(UPGRADABLE),
                              to_text_string(DOWNGRADABLE)])
        else:
            status = to_text_string(status)
        self.model().setFilter(text, status)
#        print(self.__envbox, self.__filterbox, self.__searchbox)

    def search_string_changed(self, text):
        """ """
        text = to_text_string(text).lower()
        self.__searchbox = text
        self.filter_changed()

    def filter_status_changed(self, text):
        """ """
        status = COMBOBOX_VALUES[to_text_string(text)]
        self.__filterbox = status
        self.filter_changed()

    def environment_changed(self, env):
        """ """
        self.__envbox = env
        self.source_model.env_changed(env)
        self.filter_changed()

    # Events
    def resizeEvent(self, event):
        """ """
        w = self.width()
        self.setColumnWidth(NAME, self.WIDTH_NAME)
        self.setColumnWidth(VERSION, self.WIDTH_VERSION)
        w_new = w - (self.WIDTH_NAME + self.WIDTH_VERSION +
                     (len(ACTION_COLUMNS)+1)*self.WIDTH_ACTIONS)
        self.setColumnWidth(DESCRIPTION, w_new)

        for col in ACTION_COLUMNS:
            self.setColumnWidth(col, self.WIDTH_ACTIONS)
        QTableView.resizeEvent(self, event)

    def keyPressEvent(self, event):
        """ """
#        print('key')
        QTableView.keyPressEvent(self, event)


    def mousePressEvent(self, event):
        """ """
#        row = self.rowAt(event.y())
        column = self.columnAt(event.x())
        pos = QPoint(event.x(), event.y())
        index = self.indexAt(pos)
        model_index = self.proxy_model.mapToSource(index)
        self.__model_index_clicked = model_index
        model = self.source_model
        self.valid = False

        if ( (column == INSTALL and model.is_installable(model_index)) or
             (column == REMOVE and model.is_removable(model_index)) or
             (column == UPGRADE and model.is_upgradable(model_index)) or
             (column == DOWNGRADE and model.is_downgradable(model_index)) ):
            model.update_row_icon(model_index.row(), model_index.column())
            self.valid = True
            self.column = column
        else:
            self.__model_index_clicked = None
            self.valid = False

    def mouseReleaseEvent(self, event):
        """ """
        model_index = self.__model_index_clicked
        if model_index:
            self.source_model.update_row_icon(model_index.row(),
                                              model_index.column())
#            print(model_index.row(), model_index.column())

        if self.valid:
            dlg = CondaActionDialog(self, self.column)
            if dlg.exec_():
                pass
                # Do something            

    def mouseMoveEvent(self, event):
        """ """


class SearchLineEdit(QLineEdit):
    """ """
    buttonClicked = Signal(bool)

    def __init__(self):
        QLineEdit.__init__(self)
        self.setTextMargins(18, 0, 24, 0)

        self.label = QLabel(self)
        pixmap = QPixmap(get_image_path('conda_search.png', 'png'))
        self.label.setPixmap(pixmap.scaled(self.sizeHint(),
                             aspectRatioMode=Qt.KeepAspectRatio))
        self.label.setStyleSheet('border: 0px; padding: 2px;')

        self.button = QToolButton(self)
        self.button.setIcon(QIcon(get_icon('conda_del.png')))
        self.button.setCursor(Qt.ArrowCursor)
        self.button.setStyleSheet("background: transparent; border: none;")
        self.button.setVisible(False)

        # Signals and slots
        self.button.clicked.connect(self.buttonClicked.emit)
        self.connect(self, SIGNAL("buttonClicked(bool)"),
                     self.delete_text)
        self.connect(self, SIGNAL("textChanged(QString)"),
                     self.toggle_visibility)
        self.connect(self, SIGNAL("textEdited(QString)"),
                     self.toggle_visibility)

        layout = QHBoxLayout(self)
        layout.addWidget(self.button, 0, Qt.AlignRight)
        layout.setSpacing(0)
        layout.setMargin(3)

    def delete_text(self):
        """ """
        self.setText('')

    def toggle_visibility(self):
        """ """
        if len(self.text()) == 0:
            self.button.setVisible(False)
        else:
            self.button.setVisible(True)


class CondaActionDialog(QDialog):
    """ """
    def __init__(self, parent, action):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.parent = parent

        if action == UPGRADE:
            self.setWindowTitle(_("Upgrade package"))
        elif action == DOWNGRADE:
            self.setWindowTitle(_("Downgrade package"))
        elif action == REMOVE:
            self.setWindowTitle(_("Remove package"))
        elif action == INSTALL:
            self.setWindowTitle(_("Install package"))

        self.setModal(True)



        label = QLabel(_("Go to line:"))

        glayout = QGridLayout()
        glayout.addWidget(label, 0, 0, Qt.AlignVCenter | Qt.AlignRight)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                Qt.Vertical, self)
#        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
#        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        btnlayout = QVBoxLayout()
        btnlayout.addWidget(bbox)
        btnlayout.addStretch(1)

        ok_button = bbox.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(False)
#        self.connect(self.lineedit, SIGNAL("textChanged(QString)"),
#                     lambda text: ok_button.setEnabled(len(text) > 0))
#
        layout = QHBoxLayout()
        layout.addLayout(glayout)
        layout.addLayout(btnlayout)
        self.setLayout(layout)

#        self.lineedit.setFocus()


class CondaCreateDialog(QDialog):
    """ """
    def __init__(self, parent, action):
        QDialog.__init__(self, parent)
        self.parent = parent

        # Widgets
        if action == CREATE:
            self.setWindowTitle(_("Create new environment"))
            self.env_name_text = QLineEdit()
            self.yes_button = QPushButton('C&reate')
        elif action == CLONE:
            self.setWindowTitle(_("Clone existing environment"))
            self.env_name_text = QComboBox()
            self.yes_button = QPushButton('C&lone')

        self.env_name_label = QLabel(_('Environment name:'))
        self.python_ver_label = QLabel(_('Python version:'))
        self.python_ver_combobox = QComboBox()
        self.no_button = QPushButton('&Cancel')

        # Layout
        hlayout1 = QGridLayout()
        hlayout1.addWidget(self.env_name_label, 0, 0)
        hlayout1.addWidget(self.env_name_text, 0, 1)
        hlayout1.addWidget(self.python_ver_label, 1, 0)
        hlayout1.addWidget(self.python_ver_combobox, 1, 1)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.yes_button)
        hlayout2.addWidget(self.no_button)

        layout = QVBoxLayout()
        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)

        self.setLayout(layout)
        self.setup_widget()

    def setup_widget(self):
        """ """
        self.setMinimumSize(QSize(280, 100))
        self.setFixedSize(280,100)
        self.yes_button.setDisabled(True)
        self.env_name_text.setMaxLength(12)

        default_pyver = 2  # FIXME: add this to the control panel
        pyver = self.parent.table.source_model.get_package_versions('python')
        py3 = [v for v in pyver if v[0] == '3']
        py2 = [v for v in pyver if v[0] == '2']

        self.python_ver_combobox.addItems(pyver)
        self.python_ver_combobox.insertSeparator(len(py3))
        self.python_ver_combobox.insertSeparator(len(py3) + len(py2) + 1)

        if default_pyver == 2:
            self.python_ver_combobox.setCurrentIndex(len(py3) + 1)
        elif default_pyver == 3:
            self.python_ver_combobox.setCurrentIndex(0)
        self.setModal(True)

        # Validator
        regexp = QRegExp('^[a-zA-Z\d]+$')
        regexp = QRegExp('^[a-z\d]+$')
        self.env_name_text.setValidator(QRegExpValidator(regexp))

        # Signals and slots
        self.connect(self.no_button, SIGNAL('clicked(bool)'),
                     self.close)

        self.connect(self.yes_button, SIGNAL('clicked(bool)'),
                     self.accept)

        self.connect(self.env_name_text, SIGNAL('textChanged(QString)'),
                     self.check_text)

    def check_text(self, text):
        """ """
        # Necessary? this makes the entering a bit slow...
        text = to_text_string(text)
        envs = self.parent.table.source_model.envs

        if text and text not in envs:
            self.yes_button.setDisabled(False)
        else:
            self.yes_button.setDisabled(True)


class CondaPackagesWidget(QWidget):
    """
    Packages widget
    """
    VERSION = '1.0.0'

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.setWindowTitle(_("Conda Packages"))

        self.updates_button = QPushButton(_('Update'))

        self.env_box_label = QLabel(_('Environment '))
        self.env_combobox = QComboBox()
        self.env_create_button = QPushButton(_('Create'))
        self.env_clone_button = QPushButton(_('Clone'))
        self.env_remove_button = QPushButton(_('Remove'))

        self.search_box = SearchLineEdit()
        self.filter_combobox = QComboBox()
        self.info_label = QLabel()
        self.table = CondaPackagesTable(self)
        self.status_bar = QLabel(u'Status bar')

        self.envs = [u'']
        self.environments = {}
        self.last_env_removed = None


#        self.environment_combobox.setSizePolicy(QSizePolicy.Expanding,
#                                                QSizePolicy.Expanding)

        self.empty_space = QLabel()
#        self.empty_space.sizeHint(QSize(10, 1))

        env_group = QGroupBox(_("Environment"))
        env_layout = QVBoxLayout()
        env_combo_layout = QVBoxLayout()
        env_button_layout = QHBoxLayout()
        env_combo_layout.addWidget(self.env_combobox)
        env_button_layout.addWidget(self.env_create_button)
        env_button_layout.addWidget(self.env_clone_button)
        env_button_layout.addWidget(self.env_remove_button)
        env_button_layout.addStretch()

        env_layout.addLayout(env_button_layout)
        env_layout.addLayout(env_combo_layout)
        env_group.setLayout(env_layout)

        if CONDA_PATH is None:
        #if True:
            hlayout3 = QHBoxLayout()
            hlayout3.addWidget(self.info_label)

            for widget in (self.table, self.search_box, self.updates_button,
                           self.filter_combobox, self.env_combobox,
                           self.env_create_button, self.env_clone_button,
                           self.env_remove_button):
                widget.setDisabled(True)

            info_text = _('To use the Conda Package Manager you need to ')
            url = 'http://docs.continuum.io/anaconda/index.html'
            info_text += 'install the <a href={0}>{1}</a>'. \
                format(url, '<b>anaconda</b>')
            info_text += ' distribution.'
            self.info_label.setText(info_text)
            self.info_label.setTextFormat(Qt.RichText)
            self.info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.info_label.setOpenExternalLinks(True)
        else:
            self.env_clone_button.setDisabled(True)
            hlayout3 = QHBoxLayout()
            hlayout3.addWidget(self.filter_combobox)
            hlayout3.addWidget(self.updates_button)
            hlayout3.addWidget(self.search_box)

            self.table.setup_model()
            self.envs = self.table.source_model.envs
            self.environments = self.table.source_model.environments
            self.setup_widget()

        hlayout4 = QHBoxLayout()
        hlayout4.addWidget(self.table)

        hlayout5 = QHBoxLayout()
        hlayout5.addWidget(self.status_bar)

        layout = QVBoxLayout()
        layout.addWidget(self.empty_space)
        layout.addWidget(env_group)
        layout.addLayout(hlayout3)
        layout.addLayout(hlayout4)
        layout.addLayout(hlayout5)

        self.setLayout(layout)


    def refresh_env_combobox(self):
        """ """
        self.table.source_model.refresh_envs()
        self.envs = self.table.source_model.envs
        self.environments = self.table.source_model.environments

        envs_items = ["{0} ({1})".format(k, self.environments[k]) for k in
                      self.envs]
        n = len(envs_items)
        actual_n = self.env_combobox.count()
        actual_envs_items = [to_text_string(self.env_combobox.itemText(i)) for
                             i in range(actual_n)]
        print(envs_items, n)
        print(actual_envs_items, actual_n)
        if actual_n == 0:  # Initial population of combobox
            self.env_combobox.addItems(envs_items)
            self.env_combobox.setCurrentIndex(0)
        elif n > actual_n:  # Added environment        
            actual_envs_items.extend([None]*(n - actual_n))
            for i, item in enumerate(envs_items):
                if item != actual_envs_items[i]:
                    self.env_combobox.insertItem(i, envs_items[i])
                    self.env_combobox.setCurrentIndex(i)
                    break
        elif n < actual_n:  # Removed environment
            env_remove = to_text_string(self.env_combobox.currentText())
            self.env_combobox.removeItem(actual_envs_items.index(env_remove))
            self.env_combobox.setCurrentIndex(0)

    def setup_widget(self):
        """ """
        self.refresh_env_combobox()

        self.filter_combobox.addItems([k for k in COMBOBOX_VALUES_ORDERED])
        self.filter_combobox.setCurrentIndex(ALL)

        # Connect environments combobox
        self.connect(self.env_create_button, SIGNAL('clicked(bool)'),
                     self.create_environment)
        self.connect(self.env_clone_button, SIGNAL('clicked(bool)'),
                     self.clone_environment)
        self.connect(self.env_remove_button, SIGNAL('clicked(bool)'),
                     self.remove_environment)

        # Connect environments combobox
        self.connect(self.updates_button,
                     SIGNAL('clicked(bool)'),
                     self.check_updates)

        # Connect search box
        self.connect(self.search_box, SIGNAL('textChanged(QString)'),
                     self.table.search_string_changed)

        # Connect filter combobox
        self.connect(self.filter_combobox,
                     SIGNAL('currentIndexChanged(QString)'),
                     self.table.filter_status_changed)

        # Connect environments combobox
        self.connect(self.env_combobox,
                     SIGNAL('currentIndexChanged(QString)'),
                     self.environment_changed)

        self.env_remove_button.setDisabled(True)
        self.table.filter_changed()

    def environment_changed(self, text):
        """ """
        text = to_text_string(text)
        if text:
            env = text.split()[0]
            if env != ROOT and env != self.last_env_removed:
                self.env_remove_button.setDisabled(False)
            else:
                self.env_remove_button.setDisabled(True)

            self.table.environment_changed(env)

    def remove_environment(self):
        """ """
        env = self.envs[self.env_combobox.currentIndex()]
        msg_box = QMessageBox()
        msg_box.setWindowTitle(_("Remove conda environment"))
        msg_box.setText(_("Do you wish to remove ") + '<b>{}</b>?'.format(env))
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setIcon(QMessageBox.Warning)

        ret = msg_box.exec_()
        if ret == QMessageBox.Yes:
            #conda_api.remove_environment(env)
            # Temporal fix...
            res = conda_api._call_conda(['remove', '--yes', '--quiet', '--all',
                                        '--no-pin', '--features', '-n', env, ])

            self.last_env_removed = env
            self.refresh_env_combobox()
        elif ret == QMessageBox.No:
            pass

    def create_environment(self):
        """ """
        """ """
        dlg = CondaCreateDialog(self, CREATE)
        ret = dlg.exec_()
        if ret:
            envname = to_text_string(dlg.env_name_text.text())
            pyver = to_text_string(dlg.python_ver_combobox.currentText())
            conda_api.create(name=envname, pkgs=['python={}'.format(pyver)])
            self.refresh_env_combobox()
        else:
            pass

    def clone_environment(self):
        """ """
        dlg = CondaCreateDialog(self, CLONE)
        if dlg.exec_():
            print('clone')

    def check_updates(self):
        """ """
        model = self.table.source_model
        model.refresh_()        
        self.refresh_env_combobox()


def test():
    """Run packages widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = CondaPackagesWidget(None)
    widget.show()
#    widget.analyze(__file__)
    sys.exit(app.exec_())

if __name__ == '__main__':
    test()
