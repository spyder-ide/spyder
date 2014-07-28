# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Packager manager widget"""

# pylint: disable=C01031
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement, print_function

from spyderlib.qt.QtGui import (QGridLayout, QVBoxLayout, QHBoxLayout,
                                QStatusBar, QDialogButtonBox, QToolButton,
                                QLineEdit, QComboBox, QProgressBar,
                                QSpacerItem, QPushButton, QMenu,
                                QPixmap, QIcon, QFileDialog,
                                QWidget, QMessageBox, QLabel, QAction,
                                QTableView, QAbstractItemView, QSortFilterProxyModel,
                                QColor, QBrush, QPainter,
                                QStyle, QFont, QDialog, QPalette,
                                QSizePolicy, QRegExpValidator)
from spyderlib.qt.QtCore import (QSize, Qt, SIGNAL, QProcess, QByteArray, QRect,
                                 QTextCodec, Signal, QThread,
                                 QAbstractTableModel, QModelIndex, QRegExp,
                                 QPoint, SLOT, Slot, QObject, QMetaObject, Q_ARG)
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import to_qvariant, getexistingdirectory

import sys
import platform
import os
import os.path as osp
import json
#import locale

# Local imports
from spyderlib import dependencies
from spyderlib.utils import programs
from spyderlib.utils.encoding import to_unicode_from_fs
from spyderlib.utils.qthelpers import (get_icon, create_toolbutton, create_action,
                                       add_actions)
from spyderlib.baseconfig import get_conf_path, get_translation, get_image_path

from spyderlib.py3compat import to_text_string, getcwd, pickle
_ = get_translation("p_condapackages", dirname="spyderplugins")

import conda_api # TODO: This will reside where???
CONDA_PATH = programs.find_program('conda')  # FIXME: Conda api has similar check

# FIXME: Conda API requires defining this first. Where should I put this?
conda_api.set_root_prefix()  # TODO:


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
        fname[0] = 'dummy'
        pass  # FIXME: Return fucntion or have an dummy json dic with no info

    if bitness == 32:
        fname[1] = '32'
    elif bitness == 64:
        fname[1] = '64'
    else:
        fname[0] = 'package'
        pass  # FIXME: Return fucntion

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


def sort_versions(versions=[], reverse=False, sep =u'.'):  # FIXME: Python 3 unicode?
    """ Sort a list of version number strings """
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
    new_versions = []
    alpha, sizes = set(), set()

    for item in versions:
        it = item.split(sep)
        temp = []
        for i in it:
            x = toint(i)
            if not isinstance(x, int):
                x = unicode(x)
                middle = x.lstrip(digits).rstrip(digits)
                tail = toint(x.lstrip(digits).replace(middle, u''))
                head = toint(x.rstrip(digits).replace(middle, u''))
                middle = toint(middle)
                res = [head, middle, tail]
                while u'' in res:
                    res.remove(u'')
                for r in res:
                    if isinstance(r, unicode):
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
    # return sorted(versions, reverse=reverse)

# Constants
COLUMNS = (NAME, DESCRIPTION, VERSION, STATUS,
           INSTALL, REMOVE, UPGRADE, DOWNGRADE, ENDCOL) = list(range(9))
ACTION_COLUMNS = [INSTALL, REMOVE, UPGRADE, DOWNGRADE]
TYPES = (INSTALLED, NOT_INSTALLED, UPGRADABLE, DOWNGRADABLE, INSTALLABLE, ALL,
         MIXGRADABLE, CREATE, CLONE, REMOVE_ENV) = list(range(10))
COMBOBOX_VALUES_ORDERED = [_(u'Installed'), _(u'Not installed'),
                           _(u'Upgradable'), _(u'Downgradable'),
                           _(u'All instalable'), _(u'All')]
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
        self.__packages_versions = {}         # the canonical name of versions compatible
        self.__packages_versions_number = {}
        self.__packages_versions_all = {}     # the canonical name of all versions
        self.__packages_upgradable = {}
        self.__packages_downgradable = {}
        self.__rows = []

        self.__python_ver = u''

        self.icons = {
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
        pyver_running = platform.python_version()
        envs = conda_api.get_envs()  # TODO:
        prefixes = ([conda_api.get_prefix_envname(ROOT)] + [k for k in envs])  # TODO:
        environments = [ROOT] + [k.split(osp.sep)[-1] for k in envs]
        self.__environments = dict(zip(environments, prefixes))
        self.__envs = environments

        # This has to do with the active python
        self.__pyver_running = pyver_running.replace('.', '')[:-1].lower()

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

    def __setup_data(self):
        """ """
        exlude_names = ['emptydummypackage']  # FIXME: Any packages to exclude?
        self.__packages_names = sorted([key for key in self.__conda_packages])
        self.__rows = range(len(self.__packages_names))
        self.__packages_linked = {}

        canonical_names = sorted(list(conda_api.linked(self.__prefix))) # TODO:

        # This has to do with the versions of the selected environment, NOT
        # with the python version running!
        pyver, numpyver, pybuild, numpybuild = None, None, None, None
        for canonical_name in canonical_names:
            n, v, b = conda_api.split_canonical_name(canonical_name)  # TODO:
            self.__packages_linked[n] = [n, v, b, canonical_name]
            if n == 'python':
                pyver = v
                pybuild = b
            elif n == 'numpy':
                numpyver = v
                numpybuild = b

        pybuild = 'py' + ''.join(pyver.split('.'))[:-1] + '_'  # + pybuild
        if numpyver is None and numpybuild is None:
            numpybuild = ''
        else:
            numpybuild = 'np' + ''.join(numpyver.split('.'))[:-1]

        for n in self.__packages_names:
            self.__packages_versions_all[n] = sort_versions([s[0] for s in
                                                     self.__conda_packages[n]],
                                                     reverse=True)
        # Now clean versions depending on the build version of python and numpy
        # FIXME: there is an issue here... at this moment on package with same
        # version but only differing in the build number will get added
        for name in self.__packages_versions_all:
            tempver_cano = []
            tempver_num = []
            for ver in self.__packages_versions_all[name]:
                n, v, b = conda_api.split_canonical_name(ver)

                if 'np' in b and 'py' in b:
                    if (numpybuild + pybuild) in b:
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
            self.__packages_versions[name] = sort_versions(tempver_cano,
                                                           reverse=True)
            self.__packages_versions_number[name] = sort_versions(tempver_num,
                                                           reverse=True)

        # FIXME: Check what to do with different builds??
        # For the moment here a set is used to remove duplicate versions
        for n, vals in self.__packages_linked.iteritems():
            canonical_name = vals[-1]
            current_ver = vals[1]
            vers = self.__packages_versions_number[n]
            vers = sort_versions(list(set(vers)), reverse=True)

            self.__packages_upgradable[n] = not(current_ver == vers[0])
            self.__packages_downgradable[n] = not(current_ver == vers[-1])

        for row, name in enumerate(self.__packages_names):
            if name in self.__packages_linked:
                version = self.__packages_linked[name][1]
                if (self.__packages_upgradable[name] and
                    self.__packages_downgradable[name]):
                    status = MIXGRADABLE
                elif self.__packages_upgradable[name]:
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
        """ """
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
        if not index.isValid() or not (0 <= index.row() < len(self.__rows)):
            return to_qvariant()

        row = index.row()
        column = index.column()

        # Carefull here with the order, this has to be adjusted manually
        if self.__rows[row] == row:
            name, description, version, status, i, r, u, d = [u'', u'', '-',
                                                              -1, False, False,
                                                              False, False]
        else:
            name, description, version, status, i, r, u, d = self.__rows[row]
#            print(self.__rows, row)

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
            if column == INSTALL:
                if status == NOT_INSTALLED:
                    if i:
                        return to_qvariant(self.icons['add.pressed'])
                    else:
                        return to_qvariant(self.icons['add.active'])
                else:
                    return to_qvariant(self.icons['add.inactive'])
            elif column == REMOVE:
                if (status == INSTALLED or status == UPGRADABLE or
                   status == DOWNGRADABLE or status == MIXGRADABLE):
                    if r:
                        return to_qvariant(self.icons['remove.pressed'])
                    else:
                        return to_qvariant(self.icons['remove.active'])
                else:
                    return to_qvariant(self.icons['remove.inactive'])
            elif column == UPGRADE:
                if status == UPGRADABLE or status == MIXGRADABLE:
                    if u:
                        return to_qvariant(self.icons['upgrade.pressed'])
                    else:
                        return to_qvariant(self.icons['upgrade.active'])
                else:
                    return to_qvariant(self.icons['upgrade.inactive'])
            elif column == DOWNGRADE:
                if status == DOWNGRADABLE or status == MIXGRADABLE:
                    if d:
                        return to_qvariant(self.icons['downgrade.pressed'])
                    else:
                        return to_qvariant(self.icons['downgrade.active'])
                else:
                    return to_qvariant(self.icons['downgrade.inactive'])
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
            if column == NAME:
                if status in [INSTALLED, UPGRADABLE, DOWNGRADABLE,
                              MIXGRADABLE]:
                    color = QColor(Qt.black)  # FIXME: Use system colors
                    return to_qvariant(color)
                elif status == NOT_INSTALLED:
                    color = QColor(Qt.darkGray)  # FIXME: Use system colors
                    return to_qvariant(color)
        elif role == Qt.FontRole:
            if column == NAME and (status in [INSTALLED, UPGRADABLE,
                                              DOWNGRADABLE, MIXGRADABLE]):
                font = QFont()
                font.setBold(False)
                return to_qvariant(font)
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
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
        return len(self.__packages_names)

    def columnCount(self, index=QModelIndex()):
        return len(COLUMNS)

    def row(self, rownum):
        """ """
        return self.__rows[rownum]

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
        return status in [UPGRADABLE, DOWNGRADABLE, INSTALLED, MIXGRADABLE]

    def is_upgradable(self, model_index):
        """ """
        row = model_index.row()
        status = self.__rows[row][STATUS]
        return status == UPGRADABLE or status == MIXGRADABLE

    def is_downgradable(self, model_index):
        """ """
        row = model_index.row()
        status = self.__rows[row][STATUS]
        return status == DOWNGRADABLE or status == MIXGRADABLE

    def get_package_versions(self, name, versiononly=True):
        """ Gives all the compatible package canonical name

            name : str
                name of the package
            versiononly : bool
                if True, returns version number only, otherwise canonical name
        """
        versions = self.__packages_versions
        if name in versions:
            if versiononly:
                ver = versions[name]
                temp = []
                for ve in ver:
                    n, v, b = conda_api.split_canonical_name(ve)
                    temp.append(v)
                return temp
            else:
                return versions[name]
        else:
            return []

        # FIXME: now the env create is broken
        cp = self.__conda_packages[name]
        versions = set()
        for p in cp:
            versions.add(p[-1]['version'])
        return sorted(versions, reverse=True)

    def get_package_version(self, name):
        """  """
        packages = self.__packages_names
        if name in packages:
            rownum = packages.index(name)
            return self.row(rownum)[VERSION]
        else:
            return u''

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
            TODO: add description
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
        hheader.setStyleSheet("""
         QHeaderView {
            border: 0px solid black;
            background-color: rgb(200, 200, 255);
            border-radius: 0px;
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
        self.model().addFilterFunction('status-search', filter_status)
        self.model().addFilterFunction('text-search', filter_text)

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
                             to_text_string(DOWNGRADABLE),
                             to_text_string(MIXGRADABLE)])
        elif status in [INSTALLED]:
            status = ''.join([to_text_string(INSTALLED),
                              to_text_string(UPGRADABLE),
                              to_text_string(DOWNGRADABLE),
                              to_text_string(MIXGRADABLE)])
        elif status in [UPGRADABLE]:
            status = ''.join([to_text_string(UPGRADABLE),
                              to_text_string(MIXGRADABLE)])
        elif status in [DOWNGRADABLE]:
            status = ''.join([to_text_string(DOWNGRADABLE),
                              to_text_string(MIXGRADABLE)])
        else:
            status = to_text_string(status)
        self.model().setFilter(text, status)

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
                     (len(ACTION_COLUMNS) + 1)*self.WIDTH_ACTIONS)
        self.setColumnWidth(DESCRIPTION, w_new)

        for col in ACTION_COLUMNS:
            self.setColumnWidth(col, self.WIDTH_ACTIONS)
        QTableView.resizeEvent(self, event)

    def keyPressEvent(self, event):
        """ """
        QTableView.keyPressEvent(self, event)
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            index = self.currentIndex()
            self.action_pressed(index)

    def keyReleaseEvent(self, event):
        """ """
        QTableView.keyReleaseEvent(self, event)
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.action_released()

    def mousePressEvent(self, event):
        """ """
        pos = QPoint(event.x(), event.y())
        index = self.indexAt(pos)
        self.action_pressed(index)

    def mouseReleaseEvent(self, event):
        """ """
        self.action_released()

    def mouseMoveEvent(self, event):
        """ """

    def action_pressed(self, index):
        """ """
        column = index.column()
        model_index = self.proxy_model.mapToSource(index)
        self.__model_index_clicked = model_index
        model = self.source_model
        self.valid = False

        if ((column == INSTALL and model.is_installable(model_index)) or
            (column == REMOVE and model.is_removable(model_index)) or
            (column == UPGRADE and model.is_upgradable(model_index)) or
            (column == DOWNGRADE and model.is_downgradable(model_index))):

            model.update_row_icon(model_index.row(), model_index.column())
            self.valid = True
            self.column = column
        else:
            self.__model_index_clicked = None
            self.valid = False

    #FIXME: Maybe this should be moved to the Main widget to centralize the
    # Conda actions either in the widget or in the Abstract Model...
    def action_released(self):
        """ """
        model_index = self.__model_index_clicked
        if model_index:
            self.source_model.update_row_icon(model_index.row(),
                                              model_index.column())
        if self.valid:
            name = self.source_model.row(model_index.row())[NAME]
            versions = self.source_model.get_package_versions(name)
            version = self.source_model.get_package_version(name)
            dlg = CondaActionDialog(self, self.column, version, versions)

            if dlg.exec_():
                env = self.__envbox
                ver = dlg.version_combobox.currentText()
                pkgs = [u'{0}={1}'.format(name, ver)]
                if self.column == REMOVE:
                    conda_api.remove(name, name=env)
                elif self.column == INSTALL:
                    conda_api.install(env, pkgs=pkgs)
                elif self.column == UPGRADE:
                    conda_api.install(env, pkgs=pkgs)
                elif self.column == DOWNGRADE:
                    conda_api.install(env, pkgs=pkgs)
                self.source_model.refresh_()
#                print(env, pkgs)


class SearchLineEdit(QLineEdit):
    """ """
    def __init__(self, icon=True):
        QLineEdit.__init__(self)

        self.setTextMargins(1, 0, 20, 0)
        if icon:
            self.setTextMargins(18, 0, 20, 0)
            self.label = QLabel(self)
            pixmap = QPixmap(get_image_path('conda_search.png', 'png'))
            self.label.setPixmap(pixmap)
            self.label.setStyleSheet('''border: 0px; padding-bottom: 2px;
                                     padding-left: 1px;''')

        pixmap = QPixmap(get_image_path(('conda_del.png')))
        self.button = QToolButton(self)
        self.button.setIcon(QIcon(pixmap))
        self.button.setIconSize(QSize(18, 18))
        self.button.setCursor(Qt.ArrowCursor)
        self.button.setStyleSheet("""QToolButton {background: transparent;
                                  padding: 0px; border: none; margin:0px; }""")
        self.button.setVisible(False)

        # Signals and slots
        self.connect(self.button, SIGNAL("clicked(bool)"),
                     self.delete_text)
        self.connect(self, SIGNAL("textChanged(QString)"),
                     self.toggle_visibility)
        self.connect(self, SIGNAL("textEdited(QString)"),
                     self.toggle_visibility)

#        self.button.setMinimumSize(QSize(18, 18))
        layout = QHBoxLayout(self)
        layout.addWidget(self.button, 0, Qt.AlignRight)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 2, 2, 0)

    def delete_text(self, val):
        """ """
        self.setText('')
        self.setFocus()

    def toggle_visibility(self):
        """ """
        if len(self.text()) == 0:
            self.button.setVisible(False)
        else:
            self.button.setVisible(True)


class CondaActionDialog(QDialog):
    """ """
    def __init__(self, parent, action, version, versions):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
#        self.setAttribute(Qt.WA_DeleteOnClose)

        self.parent = parent

        self.setModal(True)

        self.label = QLabel()
        self.version_combobox = QComboBox()

        labeltext = _("Select package version:")

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                Qt.Horizontal, self)
        btnlayout = QVBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        ok_button = bbox.button(QDialogButtonBox.Ok)

        # Versions mih have duplicates from different builds
        versions = sort_versions(list(set(versions)), reverse=True)

        # FIXME: There is a bug, a package installed by anaconda has version
        # astropy 0.4 and the linked list 0.4 but the available versions
        # in the json file do not include 0.4 but 0.4rc1... so...
        # temporal fix is to check if inside list otherwise show full list
        if action == UPGRADE:
            self.setWindowTitle(_("Upgrade package"))
#            print(version, versions)
            if version in versions:
                index = versions.index(version)
                versions = versions[:index]
            else:
                versions = versions
                ok_button.setEnabled(True)
        elif action == DOWNGRADE:
            self.setWindowTitle(_("Downgrade package"))
            if version in versions:
                index = versions.index(version)
                versions = versions[index+1:]
            else:
                versions = versions
            ok_button.setEnabled(True)
        elif action == REMOVE:
            self.setWindowTitle(_("Remove package"))
            labeltext = _("Package version:")
            versions = [version]
            self.version_combobox.setEnabled(False)
#            ok_button.setEnabled(False)
            ok_button.setEnabled(True)
        elif action == INSTALL:
            self.setWindowTitle(_("Install package"))
            ok_button.setEnabled(True)

        if len(versions) == 1:
            labeltext = _('Package available:')

        self.label.setText(labeltext)
        self.version_combobox.addItems(versions)

        glayout = QGridLayout()
        glayout.addWidget(self.label, 0, 0, Qt.AlignVCenter | Qt.AlignRight)
        glayout.addWidget(self.version_combobox, 0, 1, Qt.AlignVCenter |
                          Qt.AlignRight)

        layout = QVBoxLayout()
        layout.addLayout(glayout)
        layout.addLayout(btnlayout)
        self.setLayout(layout)

        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
#        self.lineedit.setFocus()


class CondaEnvironmentActionDialog(QDialog):
    """ """
    def __init__(self, parent, action, pyvers, envs, env_dir, active_env):
        """ """
        QDialog.__init__(self, parent)

        # Attributes
        self.parent = parent
        self.action = action
        self.pyvers = pyvers
        self.envs = envs
        self.env_dir = env_dir
        self.active_env = active_env

        self.dialog_size = QSize(460, 160)

        # Widgets
        self.env_name_label = QLabel(_('Environment name'))
        self.python_ver_label = QLabel(_('Python version'))
        self.env_path_label = QLabel(_('Path (optional)'))
        self.env_path_text = SearchLineEdit(False)
        self.python_ver_combobox = QComboBox()
        self.env_combobox = QComboBox()
        self.env_name_text = QLineEdit()

        if action == CREATE:
            self.setWindowTitle(_("Create new environment"))
            self.combobox = self.python_ver_combobox
            self.combobox_label = self.python_ver_label
        elif action == CLONE:
            self.setWindowTitle(_("Clone existing environment"))
            self.combobox = self.env_combobox
            self.combobox_label = QLabel(_('Clone from'))
        elif action == REMOVE_ENV:
            self.setWindowTitle(_("Remove existing environment"))
            self.combobox = self.env_combobox
            self.combobox_label = QLabel(_('Select environment '))
            self.dialog_size = QSize(260, 100)

        self.bbox = QDialogButtonBox(QDialogButtonBox.Cancel |
                                     QDialogButtonBox.Ok,
                                     Qt.Horizontal, self)
        self.ok_button = self.bbox.button(QDialogButtonBox.Ok)

        # Layout
        hlayout1 = QGridLayout()

        if action == REMOVE_ENV:
            hlayout1.addWidget(self.combobox_label, 0, 0)
            hlayout1.addWidget(self.combobox, 0, 1)
        else:
            self.browse = create_toolbutton(self,
                                            icon=get_icon('fileopen.png'),
                                            tip=_('Select directory'),
                                            triggered=self.select_file)
            hlayout1.addWidget(self.env_name_label, 0, 0)
            hlayout1.addWidget(self.env_name_text, 0, 2, 1, 2)
            hlayout1.addWidget(self.combobox_label, 1, 0)
            hlayout1.addWidget(self.combobox, 1, 2, 1, 2)
            hlayout1.addWidget(self.env_path_label, 2, 0)
            hlayout1.addWidget(self.env_path_text, 2, 2)
            hlayout1.addWidget(self.browse, 2, 3)

        hlayout2 = QHBoxLayout()
        hlayout2.addStretch(0)
        hlayout2.addWidget(self.bbox)
        hlayout2.addStretch(0)

        layout = QVBoxLayout()
        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)

        self.setLayout(layout)
        self.setup_widget()

    def setup_widget(self):
        """ """
        self.setMinimumSize(self.dialog_size)
        self.setFixedSize(self.dialog_size)
        self.env_name_text.setMaxLength(12)
        self.env_path_text.setReadOnly(True)
        self.env_path_text.setPlaceholderText(self.env_dir)

        default_pyver = 2  # FIXME: add this to the control panel
        py3 = [v for v in self.pyvers if v[0] == '3']
        py2 = [v for v in self.pyvers if v[0] == '2']
        py1 = [v for v in self.pyvers if v[0] == '1']

        if self.action == REMOVE_ENV:
            envs = self.envs
            if ROOT in envs:
                envs.remove(ROOT)
            if self.active_env in envs:
                envs.remove(self.active_env)
            self.env_combobox.addItems(self.envs)
            self.ok_button.setDisabled(False)
        else:
            self.env_combobox.addItems(self.envs)
            self.python_ver_combobox.addItems(self.pyvers)
            self.python_ver_combobox.insertSeparator(len(py3))
            self.ok_button.setDisabled(True)

            if py1:
                self.python_ver_combobox.insertSeparator(len(py3) +
                                                         len(py2) + 1)
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
        self.connect(self.bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(self.bbox, SIGNAL("rejected()"), SLOT("reject()"))
        self.connect(self.env_name_text, SIGNAL('textChanged(QString)'),
                     self.check_text)

        # Existing environments
        self.envs = self.parent.table.source_model.envs
        self.env_name_text.setFocus()

    def check_text(self, text):
        """ """
        text = to_text_string(text)
        envs = self.envs

        if text and text not in envs:
            self.ok_button.setDisabled(False)
        else:
            self.ok_button.setDisabled(True)

        env_dir = osp.join(self.env_dir, text)
        self.env_path_text.setPlaceholderText(env_dir)

    def select_file(self):
        """ """
        folder = getexistingdirectory(self, _("Select directory"),
                                      getcwd(), QFileDialog.ShowDirsOnly)
        if folder:
            self.env_path_text.setText(folder)


class CondaPackagesWidget(QWidget):
    """
    Packages widget
    """
    VERSION = '1.0.0'

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        # Variables
        self.envs = [u'']
        self.environments = {}
        self.active_env = self.get_active_env()
        self.selected_env = self.get_active_env()

        self.last_env_created = None
        self.last_env_deleted = None

        # Widget Options
        self.setWindowTitle(_("Conda Packages"))

        # Widgets
        self.filter_combobox = QComboBox()
        self.updates_button = QPushButton(_('Update list'))
        self.search_box = SearchLineEdit()
        self.info_label = QLabel()

        self.env_options_menu = QMenu()
        self.env_options_submenu = QMenu(_('Environments'))
        self.env_create_button = create_action(self, _('Create'),
                                               icon=get_icon('filenew.png'),
                                               triggered=self.create_env)
        self.env_clone_button = create_action(self, _('Clone'),
                                              icon=get_icon('editcopy.png'),
                                              triggered=self.clone_env)
        self.env_remove_button = create_action(self, _('Remove'),
                                               icon=get_icon('editdelete.png'),
                                               triggered=self.remove_env)
        actions = [self.env_create_button, self.env_clone_button,
                   self.env_remove_button, self.env_options_submenu]
        add_actions(self.env_options_menu, actions)

        self.env_options_button = QToolButton()
        self.env_options_button.setAutoRaise(True)
        self.env_options_button.setMenu(self.env_options_menu)
        self.env_options_button.setPopupMode(QToolButton.InstantPopup)
        self.env_options_button.setIcon(get_icon('tooloptions.png'))

        self.table = CondaPackagesTable(self)

        self.status_bar = QStatusBar()
        self.progress_bar = QProgressBar()

        if CONDA_PATH is None:
#        if True:
            top_layout = QHBoxLayout()
            top_layout.addWidget(self.info_label)

            for widget in (self.table, self.search_box, self.updates_button,
                           self.filter_combobox, self.env_create_button,
                           self.env_clone_button, self.env_remove_button):
                widget.setDisabled(True)
            url = 'http://docs.continuum.io/anaconda/index.html'
            info_text = _('''To use the Conda Package Manager you need to
                          install the ''')
            info_text += ' <a href={0}>{1}</a> '.format(url, '<b>anaconda</b>')
            info_text += _('distribution.')
            self.info_label.setText(info_text)
            self.info_label.setTextFormat(Qt.RichText)
            self.info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.info_label.setOpenExternalLinks(True)
            self.status_bar.setSizeGripEnabled(False)
            self.progress_bar.setVisible(False)
        else:
            top_layout = QHBoxLayout()
            top_layout.addWidget(self.filter_combobox)
            top_layout.addWidget(self.updates_button)
            top_layout.addWidget(self.search_box)
            top_layout.addWidget(self.env_options_button)

            self.table.setup_model()
            self.envs = self.table.source_model.envs
            self.environments = self.table.source_model.environments
            self._setup_widget()

        middle_layout = QHBoxLayout()
        middle_layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.status_bar)
        self.status_bar.addPermanentWidget(self.progress_bar)

        layout = QVBoxLayout()
        layout.addItem(QSpacerItem(250, 5))

        layout.addLayout(top_layout)
        layout.addLayout(middle_layout)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def _refresh_env_submenu(self):
        """ """
        self.table.source_model.refresh_envs()
        self.envs = self.table.source_model.envs
        self.environments = self.table.source_model.environments

        active = _(' [active]')
        actions = []
        active_env = self.get_active_env()
        selected_env = self.selected_env

        for i, env in enumerate(self.envs):
            e = env
            if e == active_env:
                e = env + active
                icon = QIcon()
#                active_index = i
            if selected_env == env:
                selected_index = i

            actions.append(create_action(self, _(e), icon=icon,
                           triggered=lambda
                           env=env: self.select_env(env)))

        self.env_options_submenu.clear()
        actions[selected_index].setCheckable(True)
        actions[selected_index].setChecked(True)
        add_actions(self.env_options_submenu, actions)

        envs = self.envs
        active_env = self.get_active_env()

        if active_env == ROOT and len(envs) == 1:
            self.env_remove_button.setDisabled(True)
        elif active_env != ROOT and len(envs) == 2:
            self.env_remove_button.setDisabled(True)
        else:
            self.env_remove_button.setDisabled(False)

    def _setup_widget(self):
        """ """
        self._refresh_env_submenu()
        self.progress_bar.setMaximum(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setMaximumWidth(140)

        self.status_bar.setSizeGripEnabled(False)
        self.progress_bar.setVisible(False)
        self.env_options_button.setToolTip(_('Options'))

        self.filter_combobox.addItems([k for k in COMBOBOX_VALUES_ORDERED])
        self.filter_combobox.setCurrentIndex(ALL)

        # Connect environments buttons
        self.connect(self.env_create_button, SIGNAL('clicked()'),
                     self.create_env)
        self.connect(self.env_clone_button, SIGNAL('clicked()'),
                     self.clone_env)
        self.connect(self.env_remove_button, SIGNAL('clicked()'),
                     self.remove_env)

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

        self.table.filter_changed()

    def _run_env_action(self, action, envs=[]):
        """ """
        env_dir = osp.join(conda_api.get_prefix_envname(ROOT), 'envs')
        pyvers = self.table.source_model.get_package_versions('python', True)
        pyvers = sort_versions(list(set(pyvers)), reverse=True)
        active_env = self.get_active_env()

        dlg = CondaEnvironmentActionDialog(self, action, pyvers, envs, env_dir,
                                           active_env)

        ret = dlg.exec_()

        if ret:
            envname = to_text_string(dlg.env_name_text.text())
            pyver = to_text_string(dlg.python_ver_combobox.currentText())
            path = to_text_string(dlg.env_path_text.text())
            envclone = to_text_string(dlg.env_combobox.currentText())
            pkgs = 'python={}'.format(pyver)
            dic = {}

            dic['pkgs'] = pkgs

            # Use QProcess and only use
            self.process = QProcess(self)
            self.process.readyRead.connect(self._on_data_available)

            if action == CREATE:
                self.last_env_created = envname
                if path != u'':
                    dic['path'] = osp.join(path, envname)
#                    self._run_conda(action, dic)
                else:
                    dic['name'] = envname
                    self._run_conda(action, dic)
            elif action == CLONE:
                if path != u'':
                    pass
                else:
                    dic['cloned from'] = envclone
                    dic['name'] = envname
                    self.last_env_created = envname
                    self._run_conda(action, dic)
            elif action == REMOVE_ENV:
                dic['name'] = envclone
                self.last_env_created = self.get_active_env()

                self._run_conda(action, dic)

            self.process.started.connect(lambda: self._set_gui_disabled(True))
            self.process.finished.connect(lambda: self._on_process_ready(True))

    def _set_gui_disabled(self, boo):
        """ """
        widgets = [self.updates_button, self.filter_combobox,
                   self.filter_combobox, self.search_box,
                   self.table, self.env_options_button]

        for widget in widgets:
            widget.setDisabled(boo)

        self.progress_bar.setVisible(boo)

        if boo:
            self.status_bar.showMessage(self.status)
        else:
            self.status_bar.showMessage('')

    def _run_conda(self, action, dic):
        """ """
        if action == CREATE and 'path' in dic:
            pass
        elif action == CREATE and 'path' not in dic:
            extra_args = ['create', '--yes', '--quiet',
                          '--name', dic['name'], dic['pkgs']]
            cmd_list = conda_api._call_conda_2(extra_args)
            print(cmd_list[0], cmd_list[1:])
            status = _('Creating environment "') + dic['name'] + '"'
        elif action == CLONE:
            (extra_args) = ['create', '--yes', '--quiet', '-n', dic['name'],
                            '--clone',  dic['cloned from']]
            cmd_list = conda_api._call_conda_2(extra_args)
            status = (_('Cloning from environment ') + '"' + dic['cloned from']
                      + _('" into "') + dic['name'] + '"')
        elif action == REMOVE_ENV:
            cmd_list = conda_api._call_conda_2(['remove', '--yes', '--quiet',
                                                '--all', '--no-pin',
                                                '--features', '-n',
                                                dic['name']])
            status = _('Removing environment "') + dic['name'] + '"'

        self.process.start(cmd_list[0], cmd_list[1:])
        self.status = status

    def _on_data_available(self):
        """ """
        response = to_text_string(self.process.readAll())
        response

    def _on_process_ready(self, True):
        """ """
        env = self.last_env_created
        self.select_env(env)
        self._set_gui_disabled(False)

    def select_env(self, env):
        """ """
        self.selected_env = to_text_string(env)
        self._refresh_env_submenu()
        self.table.environment_changed(env)

    def remove_env(self):
        """ """
        self._run_env_action(REMOVE_ENV, self.envs)

    def create_env(self):
        """ """
        self._run_env_action(CREATE)

    def clone_env(self):
        """ """
        self._run_env_action(CLONE, self.envs)

    def check_updates(self):
        """ """
        model = self.table.source_model
        model.refresh_()
        self._refresh_env_submenu()
#        print([self.get_active_env()])

    def get_active_env(self):
        """ """
        tup = conda_api._call_conda(['info', '-e'])  # TODO:
        out = tup[0].replace('\r', '').split('\n')

        while '' in out:
            out.remove('')

        envs = out[2:]

        for env in envs:
            if ' * ' in env:
                return env.split()[0]


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
