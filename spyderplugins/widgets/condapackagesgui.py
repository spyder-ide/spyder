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

from spyderlib.qt.QtGui import (QHBoxLayout, QWidget, QTreeWidgetItem,
                                QMessageBox, QVBoxLayout, QLabel, QTableView,
                                QAbstractItemView, QColor, QBrush,QTreeView,
                                QSortFilterProxyModel, QLineEdit, QComboBox)
from spyderlib.qt.QtCore import (Qt, SIGNAL, QProcess, QByteArray, QTextCodec,
                                 QAbstractTableModel, QModelIndex, QRegExp, QPoint)
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import getopenfilename, to_qvariant

import sys
import platform
import os
import os.path as osp
import time
import re
import subprocess
import json
from collections import OrderedDict


# Local imports
from spyderlib import dependencies
from spyderlib.utils import programs
from spyderlib.utils.encoding import to_unicode_from_fs
from spyderlib.utils.qthelpers import get_icon, create_toolbutton
from spyderlib.baseconfig import get_conf_path, get_translation
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
    python_ver = platform.python_version()
    python_ver = python_ver.replace('.', '')[:-1].lower()
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
    #print(fname, python_ver)
    usable_packages = {}
    grouped_usable_packages = {}

    for key, val in packages.iteritems():
        build = val['build'].lower()
        name = val['name'].lower()

        if (python_ver in build or build == '0') and name not in exclude:
            grouped_usable_packages[name] = list()
            usable_packages[key] = val
    """
        'build_number'
        'name'
        'license'
        'depends'
        'version' The version of the specific package
        'build'  The python version onto which it was built
        'size'
        'md5'
    """
    for key, val in usable_packages.iteritems():
        name = val['name'].lower()
        grouped_usable_packages[name].append([key, val])

    return grouped_usable_packages

# Constants
COLUMNS = (NAME, DESCRIPTION, VERSION, STATUS,
           UPDATE, INSTALL, REMOVE, ENDCOL) = list(range(8))
TYPES = INSTALLED, NOT_INSTALLED, UPGRADABLE, ALL = list(range(4))
COMBOBOX_VALUES_ORDERED = [u'Installed', u'Not installed', u'Upgradable',
                           u'All available']
COMBOBOX_VALUES = dict(zip(COMBOBOX_VALUES_ORDERED, TYPES))
HIDE_COLUMNS = [STATUS]
#HIDE_COLUMNS = []
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
        self.__rows = []

        # Run conda and initial setup
        self.__update_conda_packages()
        self.__get_env_and_prefixes()
        self.__set_env(self.__environment)
        self.__setup_data()

    def __update_conda_packages(self):
        self.__conda_packages = get_conda_packages()
        self.__packages_names = sorted([key for key in self.__conda_packages])
        self.__rows = range(len(self.__packages_names))

    def __get_env_and_prefixes(self):
        envs = conda_api.get_envs()
        prefixes = ([conda_api.get_prefix_envname(ROOT)] + [k for k in envs])
        environments = [ROOT] + [k.split(osp.sep)[-1] for k in envs]
        self.__environments = dict(zip(environments, prefixes))
        self.__envs = environments

    def __setup_data(self):
        self.__packages_linked = {}
        canonical_names = sorted(list(conda_api.linked(self.__prefix)))

        for canonical_name in canonical_names:
            n, v, b = conda_api.split_canonical_name(canonical_name)
            self.__packages_linked[n] = [n, v, b, canonical_name]

        for n in self.__packages_names:  # key here is the name of package
            self.__packages_versions[n] = sorted([s[0] for s in
                                                 self.__conda_packages[n]],
                                                 reverse=True)

        for n, vals in self.__packages_linked.iteritems():
            canonical_name = vals[-1]
            versions = self.__packages_versions[n]
            self.__packages_upgradable[n] = not(canonical_name in versions[0])

        for row, name in enumerate(self.__packages_names):
            if name in self.__packages_linked:
                version = self.__packages_linked[name][1]
                if self.__packages_upgradable[name]:
                    status = UPGRADABLE
                else:
                    status = INSTALLED
            else:
                version = '-'
                status = NOT_INSTALLED
            description = name
            self.__rows[row] = [name, description, version, status]

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
#        column = index.column()
#        if column in (NAME, VERSION, DESCRIPTION):
#            return Qt.ItemFlags(QAbstractTableModel.flags(self, index))
#        else:
        return Qt.ItemFlags(Qt.ItemIsEnabled)

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        column = index.column()
        name, description, version, status = self.__rows[row]

        if role == Qt.DisplayRole:
            if column == NAME:
                return to_qvariant(name)
            elif column == VERSION:
                return to_qvariant(version)
            elif column == STATUS:
                return to_qvariant(status)
#            elif column == DESCRIPTION:
#                return to_qvariant(row)
        elif role == Qt.TextAlignmentRole:
            if column in [NAME, DESCRIPTION, VERSION]:
                return to_qvariant(int(Qt.AlignCenter | Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole:
            if column == REMOVE:
                if status == INSTALLED or status == UPGRADABLE:
                    color = QColor(Qt.darkRed)
                    color.setAlphaF(.5)
                    return to_qvariant(color)
            elif column == UPDATE:
                if status == UPGRADABLE:
                    color = QColor(Qt.darkBlue)
                    color.setAlphaF(.5)
                    return to_qvariant(color)
            elif column == INSTALL:
                if status == NOT_INSTALLED:
                    color = QColor(Qt.darkGreen)
                    color.setAlphaF(.5)
                    return to_qvariant(color)
        elif role == Qt.ForegroundRole:
            if column == NAME and (status in [INSTALLED, UPGRADABLE]):
                color = QColor(Qt.darkBlue)
#                color.setAlphaF(.8)
                return to_qvariant(color)
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))

        if role != Qt.DisplayRole:
            return to_qvariant()
#        if role == Qt.BackgroundColorRole:
#            color = QColor(Qt.blue)
#            color.setAlphaF(.1)
#            return to_qvariant(color)

        if orientation == Qt.Horizontal:
            if section == NAME:
                return to_qvariant("Name")
            elif section == VERSION:
                return to_qvariant("Version")
            elif section == DESCRIPTION:
                return to_qvariant("Description")
            elif section == STATUS:
                return to_qvariant("Status")
            elif section == UPDATE:
                return to_qvariant("U")
            elif section == INSTALL:
                return to_qvariant("I")
            elif section == REMOVE:
                return to_qvariant("R")
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

    # 'public api'
    def env_changed(self, env):
        self.__set_env(env)
        self.__setup_data()
        self.__update_all()

    def first_index(self):
        return self.index(0, 0)

    def last_index(self):
        return self.index(self.rowCount() - 1, self.columnCount() - 1)

    @property
    def envs(self):
        return self.__envs


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
    WIDTH_ACTIONS = 15

    def __init__(self, parent, env):
        QTableView.__init__(self, parent)
        self.__searchbox = u''
        self.__filterbox = ALL
        self.__envbox = ROOT

        self.source_model = None
        self.proxy_model = MultiColumnSortFilterProxy(self)
        self.setModel(self.proxy_model)

        hheader = self.horizontalHeader()
        self.resizeColumnToContents(0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().hide()
        hheader.setStretchLastSection(True)
        hheader.setResizeMode(hheader.ResizeToContents)
#        hheader.setMinimumSectionSize(10)
        self.setAlternatingRowColors(True)
#        self.setSortingEnabled(True)
        self.setShowGrid(False)

        for col in [UPDATE, INSTALL, REMOVE]:
            self.setColumnWidth(col, self.WIDTH_ACTIONS)

        # Custom Proxy Model setup
        self.proxy_model.setDynamicSortFilter(True)
        filter_text = (lambda row, text, status: (text in row[NAME] or
                       text in row[DESCRIPTION]))
        filter_status = (lambda row, text, status: to_text_string(row[STATUS])
                         in to_text_string(status))
        self.model().addFilterFunction('status search', filter_status)
        self.model().addFilterFunction('text search', filter_text)

        self.horizontalHeader().setStyleSheet("""
        QHeaderView {
            border: 0px solid black;
            border-radius: 0px;
            background-color: rgb(200, 200, 255);
            font-weight: Bold;
            };
        """)
        self.sortByColumn(NAME, Qt.AscendingOrder)
        self.resizeColumnToContents(NAME)

    def set_model(self):
        self.source_model = CondaPackagesModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.hide_columns()

    def hide_columns(self):
        for col in HIDE_COLUMNS:
            self.hideColumn(col)


    def filter_changed(self):
        status = self.__filterbox
        text = self.__searchbox
        if status in [ALL]:
            status = ''.join([to_text_string(INSTALLED),
                             to_text_string(UPGRADABLE),
                             to_text_string(NOT_INSTALLED)])
        if status in [INSTALLED]:
            status = ''.join([to_text_string(INSTALLED),
                              to_text_string(UPGRADABLE)])
        else:
            status = to_text_string(status)
        self.model().setFilter(text, status)
        print(self.__envbox, self.__filterbox, self.__searchbox)

    def searchbox_changed(self, text):
        status = self.__filterbox
        text = to_text_string(text)
        self.__searchbox = text
        self.filter_changed()

    def filterbox_changed(self, text):
        status = COMBOBOX_VALUES[to_text_string(text)]
        text = self.__searchbox
        self.__filterbox = status
        self.filter_changed()

    def environmentbox_changed(self, env):
        envbox = to_text_string(env)
        self.__envbox = envbox
        self.source_model.env_changed(envbox)
        self.filter_changed()

    def mousePressEvent(self, event):
        row = self.rowAt(event.y())
        column = self.columnAt(event.x())
        pos = QPoint(event.x(), event.y())
        index = self.indexAt(pos)
        print(row, column, index.row())


class CondaPackagesWidget(QWidget):
    """
    Packages widget
    """
    VERSION = '1.0.0'

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.setWindowTitle("Conda Packages")

        self.updates_button = create_toolbutton(self, icon=get_icon('run.png'),
                                                text=_("Check for Updates"),
                                                tip=_("Check for Updates"),
                                                triggered=self.check_updates,
                                                text_beside_icon=True)

        self.environment_box_label = QLabel(_('Conda environment:'))
        self.environment_combobox = QComboBox()
        self.search_box = QLineEdit()
        self.filter_combobox = QComboBox()
        self.info_label = QLabel()
        self.table = CondaPackagesTable(self, ROOT)
        self.__envs = [u'']

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.environment_box_label)
        hlayout1.addWidget(self.environment_combobox)
        hlayout1.addStretch()
        hlayout1.addWidget(self.updates_button)
        
        hlayout2 = QHBoxLayout()

        hlayout2.addWidget(self.filter_combobox)
        hlayout1.addStretch()        
        hlayout2.addWidget(self.search_box)

        hlayout3 = QHBoxLayout()
        hlayout3.addWidget(self.info_label)

        hlayout4 = QHBoxLayout()
        hlayout4.addWidget(self.table)

        layout = QVBoxLayout()
        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)
        layout.addLayout(hlayout3)
        layout.addLayout(hlayout4)

        if CONDA_PATH is None:
#        if True:
            for widget in (self.table, self.search_box,
                           self.updates_button, self.filter_combobox,
                           self.environment_combobox):
                widget.setDisabled(True)

            info_text = _('To use the Conda Package Manager you need to install the ')
            url = 'https://store.continuum.io/cshop/anaconda/'
            info_text += ' <a href={0}>{1}</a>'.format(url, '<b>anaconda</b>')
            info_text += ' distribution.'
            self.info_label.setText(info_text)
            self.info_label.setTextFormat(Qt.RichText)
            self.info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.info_label.setOpenExternalLinks(True)
        else:
            self.table.set_model()
            self.__envs = self.table.source_model.envs
            self.setup_widget()

        self.setLayout(layout)

    def setup_widget(self):        
        
        self.environment_combobox.addItems(self.__envs)
        self.environment_combobox.setCurrentIndex(0)

        self.filter_combobox.addItems([k for k in COMBOBOX_VALUES_ORDERED])
        self.filter_combobox.setCurrentIndex(ALL)
        # Connect search box
        self.connect(self.search_box, SIGNAL('textChanged(QString)'),
                     self.table.searchbox_changed)

        # Connect filter combobox
        self.connect(self.filter_combobox,
                     SIGNAL('currentIndexChanged(QString)'),
                     self.table.filterbox_changed)

        # Connect environments combobox
        self.connect(self.environment_combobox,
                     SIGNAL('currentIndexChanged(QString)'),
                     self.table.environmentbox_changed)

        self.table.filter_changed()

    def create_conda_environment(self):
        pass

    def install_conda_package(self):
        pass

    def remove_conda_package(self):
        pass

    def update_conda_package(self):
        pass

    def check_updates(self):
        pass


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
