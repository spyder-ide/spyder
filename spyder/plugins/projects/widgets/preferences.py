# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Project creation dialog."""

from __future__ import print_function

# Standard library imports
import errno
import io
import json
import os
import os.path as osp
import sys
import tempfile

# Third party imports
import requests
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QItemSelectionModel, Qt, Signal
from qtpy.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox,
                            QCompleter, QDialog, QDialogButtonBox, QGridLayout,
                            QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QPushButton, QRadioButton,
                            QStackedWidget, QStyledItemDelegate, QTableWidget,
                            QTableWidgetItem, QTabWidget, QToolButton,
                            QVBoxLayout, QWidget)

from spyder.config.base import _, get_home_dir
from spyder.plugins.projects.widgets import get_available_project_types
from spyder.preferences.configdialog import ConfigDialog, SpyderConfigPage
from spyder.py3compat import to_text_string

# Local imports
from spyder.utils import icon_manager as ima
from spyder.utils.programs import is_anaconda
from spyder.utils.qthelpers import get_std_icon


# --- Helpers
# ----------------------------------------------------------------------------
def get_conda_environments():
    """Get conda environment paths."""
    envs = []
    if is_anaconda():
        envs_folder = '{0}{1}{0}'.format(os.sep, 'envs')
        if envs_folder in sys.prefix:
            anaconda_root = sys.prefix.split(envs_folder)[0]
            envs_path = osp.join(anaconda_root, 'envs')
            for env in os.listdir(envs_path):
                path = os.path.join(envs_path, env)
                if osp.isdir(path):
                    envs.append(os.path.join(envs_path, env))
    # TODO: Use envrionments.txt file on ~/.condarc

    return list(sorted(envs))


def get_conda_packages(prefix):
    packages = []
    if is_anaconda:
        if osp.isdir(prefix):
            conda_meta = osp.join(prefix, 'conda-meta')
            for file_ in os.listdir(conda_meta):
                fpath = osp.join(conda_meta, file_)
                if osp.isfile(fpath) and fpath.endswith('.json'):
                    with io.open(fpath, 'r') as fh:
                        data = fh.read()
                        data = json.loads(data)
                    packages.append(data)
    packages = sorted(packages, key=lambda x: x['name'])
    return packages


def get_pypi_packages():
    url = 'https://pypi.org/simple/'
    packages = []
    try:
        r = requests.get(url)
    except Exception as e:
        print(e)
    else:
        data = r.content
        for line in data.split('\n'):
            if 'href' in line:
                name = line.split('>')
                if name:
                    name = name[1].split('<')
                    if name:
                        packages.append(name[0])

    return packages


def get_conda_forge_packages():
    url = 'https://api.github.com/repos/conda-forge/feedstocks/contents/feedstocks?per_page=10000'
    packages= []
    try:
        r = requests.get(url)
    except Exception as e:
        print(e)
        pass
    else:
        packages = r.json()
        packages = [p['name'] for p in packages]

    return packages


# --- Widgets
# ----------------------------------------------------------------------------
class ComboBoxDelegate(QStyledItemDelegate):
    """"""

    def __init__(self, parent, options=None):
        """"""
        super(ComboBoxDelegate, self).__init__(parent)
        self._options = options

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setEditable(False)
        if self._options:
            editor.addItems(self._options)
        editor.currentIndexChanged.connect(self.currentIndexChanged)
        return editor

    def set_options(self, options):
        """Set combobox delegate options."""
        self._options = options

    def setEditorData(self, editor, index):
        editor.blockSignals(True)
        editor.setCurrentText(index.data())
        editor.blockSignals(False)
        
    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())

    def currentIndexChanged(self):
        self.commitData.emit(self.sender())


class CompleterDelegate(QStyledItemDelegate):
    """"""

    def __init__(self, parent=None, options=None):
        """"""
        super(CompleterDelegate, self).__init__(parent=parent)
        self._options = options

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        if self._options and index.column() == 1:
            completer = QCompleter(self._options, self)
            completer.setCompletionRole(Qt.EditRole)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            editor.setCompleter(completer)

        return editor

    def set_options(self, options):
        """Set completer options."""
        self._options = options

    def setEditorData(self, editor, index):
    #     print("setEditorData")
        super(CompleterDelegate, self).setEditorData(editor, index)

    def closeEditor(self, editor, hint=None):
    #     print("closeEditor")
        super(CompleterDelegate, self).closeEditor(editor, hint)

    def commitData(self, editor):
    #     print "commitData"
        super(CompleterDelegate, self).commitData(editor)


class VariablesTable(QTableWidget):
    """"""

    def __init__(self, parent=None):
        """"""
        super(VariablesTable, self).__init__(parent=parent)
        self.setHorizontalHeaderLabels([_('Name'), _('Value'), _('Description')])
        self.horizontalHeader().setStretchLastSection(True)

    def get_environment_variables(self):
        """"""
        variables = []
        for idx in self.rowCount():
            name = self.item(idx, 0)
            value = self.item(idx, 1)
            desc = self.item(idx, 2)

            if name and value:
                dic = {}
                dic['name'] = name
                dic['value'] = value
                dic['description'] = desc
                variables.append(dic)

        return list(sorted(variables, key=lambda x: x['name']))


class PackagesTable(QTableWidget):
    """"""

    def __init__(self, parent=None):
        """"""
        super(PackagesTable, self).__init__(parent=parent)
        # Widgets
        self._pypi = get_pypi_packages()
        self._conda_forge = get_conda_forge_packages()
        self._completer_delegate_pypi = CompleterDelegate(self, self._pypi)
        self._completer_delegate_conda = CompleterDelegate(self, self._conda_forge)
        self._combobox_delegate = ComboBoxDelegate(self, ['conda', 'pip'])

        # Widget setup
        headers = [_('Type'), _('Name'), _('Version')]
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(1, 200)
        self.setSortingEnabled(True)
        self.setItemDelegateForColumn(0, self._combobox_delegate)

        # Signals
        self.cellChanged.connect(self._update_completer)

    def _update_completer(self, row, col):
        """"""
        item = self.item(row, 0)
        if item and col == 0:
            value = self.item(row, 0).text()
            if value == 'pip':
                self.setItemDelegateForRow(row, self._completer_delegate_pypi)
            elif value == 'conda':
                self.setItemDelegateForRow(row, self._completer_delegate_conda)
        self.setItemDelegateForColumn(0, self._combobox_delegate)

    def add_packages(self, packages):
        """"""
        self.clearContents()
        self.setRowCount(len(packages))
        for row, values in enumerate(packages):
            type_ = values.get('type', 'conda')
            name = values.get('name', '')
            version = values.get('version', '')

            item_type = QTableWidgetItem(type_)
            item_name = QTableWidgetItem(name)
            item_version = QTableWidgetItem(version)

            for col, item in enumerate((item_type, item_name, item_version)):
                item.setFlags(Qt.ItemIsSelectable| Qt.ItemIsEnabled)
                self.setItem(row, col, item)

    def get_package_specs(self):
        """Return a dictionary of the current packages and versions."""


class VariablesWidget(QWidget):
    """"""

    def __init__(self, parent=None):
        """"""
        super(VariablesWidget, self).__init__(parent=parent)
        # Widgets
        self.table = VariablesTable(parent=self)
        self.button_add = QPushButton(_('Add'))
        self.button_remove = QPushButton(_('Remove'))

        # Widget setup
        self.table.setColumnCount(3)
        headers = [_('Name'), _('Value'), _('Description')]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Layouts
        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(self.button_add)
        buttons_layout.addWidget(self.button_remove)
        buttons_layout.addStretch(1)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.table)
        hlayout.addLayout(buttons_layout)

        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)

        # Signals
        self.button_add.clicked.connect(lambda x=None: self.add_row())
        self.button_remove.clicked.connect(lambda x=None: self.remove_row())

    def add_row(self):
        """Add a new row to the bottom."""
        count = self.table.rowCount()
        self.table.setRowCount(count + 1)
        self.table.setCurrentCell(count, 0)
        self.table.setFocus()

    def remove_row(self, row=None):
        """Remove currently selected row."""
        row = row or self.table.currentRow()
        self.table.removeRow(row)
        if row == 0:
            row = self.table.rowCount()
        self.table.setCurrentCell(row - 1, 0)
        self.table.setFocus()

    def get_environment_variables(self):
        """"""
        return self.table.get_environment_variables()

    def validate(self):
        """"""

    def clear(self):
        """Clear all content rows from table."""
        self.table.clearContents()
        self.table.setRowCount(0)


class PackagesWidget(QWidget):
    """"""

    def __init__(self, parent=None):
        """"""
        super(PackagesWidget, self).__init__(parent=parent)

        # Widgets
        self.table = PackagesTable(parent=self)
        self.label_information = QLabel()
        self.button_add = QPushButton(_('Add'))
        self.button_remove = QPushButton(_('Remove'))

        # Widget setup
        self.button_remove.setEnabled(False)

        # Layouts
        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(self.button_add)
        buttons_layout.addWidget(self.button_remove)
        buttons_layout.addStretch(1)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.table)
        hlayout.addLayout(buttons_layout)

        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.label_information)
        self.setLayout(vlayout)

        # Signals
        self.button_add.clicked.connect(lambda x=None: self.add_row())
        self.button_remove.clicked.connect(lambda x=None: self.remove_row())

    def add_row(self):
        """Add a new row to the bottom."""
        count = self.table.rowCount()
        self.table.setRowCount(count + 1)
        self.table.setCurrentCell(count, 0)
        self.table.setFocus()

    def remove_row(self, row=None):
        """Remove currently selected row."""
        row = row or self.table.currentRow()
        self.table.removeRow(row)
        if row == 0:
            row = self.table.rowCount()
        self.table.setCurrentCell(row - 1, 0)
        self.table.setFocus()

    def add_packages(self, packages):
        """"""
        self.table.add_packages(packages)

    def get_package_specs(self):
        """Return a dictionary of the current packages and versions."""
        return {'name': 'version'}

    def set_environment_path(self, path):
        """"""

    def setEnabled(self, value):
        """"""
        for widget in [self.button_add, self.button_remove]:
            widget.setEnabled(value)

    def setDisabled(self, value):
        """"""
        self.setEnabled(not value)

    def validate(self):
        """"""

    def clear(self):
        """Clear all content rows from table."""
        self.table.clearContents()
        self.table.setRowCount(0)

    def update_status(self):
        """Update status information on packages."""
        count = self.table.rowCount()
        if count == 0:
            self.label_information.setText('')
        else:
            self.label_information.setText('{} packages in environment'.format(count))


# --- Project preferences dialog
# ----------------------------------------------------------------------------
class ProjectPreferences(ConfigDialog):
    """Project preferences dialog."""

    def __init__(self, parent=None):
        """Project config dialog based on the preferences config dialog."""
        super(ProjectPreferences, self).__init__(parent=parent)
        self.setWindowTitle(_('Project preferences'))
        self.setWindowIcon(ima.icon('configure'))

    def set_title(self, title):
        """"""
        self.setWindowTitle(title)


# --- Configuration Pages
# ----------------------------------------------------------------------------
class GeneralProjectConfigPage(SpyderConfigPage):
    CONF_SECTION = "general"

    def __init__(self, parent, project_root=None):
        """"""
        super(GeneralProjectConfigPage, self).__init__(parent)
        self._project_root = project_root or '<No project root provided>'

    def setup_page(self):
        project_info_widget = QWidget(self)
        self.line_name = self.create_lineedit(
            _('Name:'),
            'project_name',
        )
        self.text_description = self.create_textedit(
            _('Description:'),
            'project_description',
        )
        label_location = QLabel(_('Location:'))
        self.label_location_value = QLabel('')
        master_widget = QWidget(self)
        self.master_file = self.create_browsefile(
            _('Project master file:'),
            'master_file',
        )

        # Widget setup
        self.line_name.textbox.setText('Awesome project # 5')
        self.text_description.textbox.setPlainText('Some larger explanation of the project')
        self.text_description.setMaximumHeight(300)
        self.label_location_value.setText(self._project_root)

        project_info_layout = QGridLayout()
        project_info_layout.addWidget(self.line_name.label, 0, 0)
        project_info_layout.addWidget(self.line_name.textbox, 0, 1)
        project_info_layout.addWidget(self.text_description.label, 1, 0, Qt.AlignTop)
        project_info_layout.addWidget(self.text_description.textbox, 1, 1)
        project_info_layout.addWidget(label_location, 2, 0)
        project_info_layout.addWidget(self.label_location_value, 2, 1)
        project_info_widget.setLayout(project_info_layout)


        master_layout = QVBoxLayout()
        master_layout.addWidget(self.master_file)
        master_widget.setLayout(master_layout)

        # Add tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(project_info_widget),
                    _("Information"))
        tabs.addTab(self.create_tab(master_widget),
                    _("Master file"))
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)

    def refresh_items(self):
        """"""

    def get_icon(self):
        return ima.icon('genprefs')

    def get_name(self):
        return _("General")

    def apply_settings(self, options):
        pass


class EnvironmentVariablesConfigPage(SpyderConfigPage):
    CONF_SECTION = "environment_variables"

    def setup_page(self):
        # Widgets
        self.label = QLabel(_('Manage your project enviroment variables.'))
        self.variables_widget = VariablesWidget(self)

        # Layouts
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.label)
        vlayout.addWidget(self.variables_widget)
        self.setLayout(vlayout)

        # Signals

    def refresh_items(self):
        """"""

    def get_icon(self):
        return ima.icon('genprefs')

    def get_name(self):
        return _("Environment variables")

    def apply_settings(self, options):
        pass


class CondaEnvironmentConfigPage(SpyderConfigPage):
    CONF_SECTION = "conda_environment"

    def setup_page(self):
        # 'Conda group' on tab 'Environments'
        conda_button_group = QButtonGroup(self)
        conda_label = QLabel(_("Select which type of conda environment "
                               "you want to use:"))
        self.conda_use_existing = self.create_radiobutton(
            _("Use existing conda environment"),
            'conda_env_existing',
            button_group=conda_button_group,
        )
        self.conda_use_project = self.create_radiobutton(
            _("Use project environment"),
            'conda_env_project',
            button_group=conda_button_group,
        )
        envs = get_conda_environments()
        choices = [(osp.basename(env), env) for env in envs]
        self.line_conda = self.create_combobox(
            '',
            choices,
            _(""),
            'conda_env_path',
        )
        self.label_message = QLabel()
        self.packages_widget = PackagesWidget(self)

        # Widget setup
        conda_layout = QGridLayout()
        conda_layout.addWidget(conda_label, 0, 0, 1, 2)
        conda_layout.addWidget(self.conda_use_project, 1, 0)
        conda_layout.addWidget(self.conda_use_existing,  2, 0)
        conda_layout.addWidget(self.line_conda, 2, 1)
        conda_layout.addWidget(self.label_message, 3, 0, 1, 2)
        conda_widget = QWidget()
        conda_widget.setLayout(conda_layout)

        packages_group = QGroupBox(_("Environment packages"))
        packages_layout = QVBoxLayout()
        packages_layout.addWidget(self.packages_widget)
        packages_group.setLayout(packages_layout)

        # Add tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(conda_widget),
                    _("Environment"))
        tabs.addTab(self.create_tab(self.packages_widget),
                    _("Packages"))
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)

        # Signals
        conda_button_group.buttonClicked.connect(self.refresh_items)
        self.line_conda.combobox.currentIndexChanged.connect(
            self.refresh_items)
        self.refresh_items()

    def refresh_items(self):
        """"""
        use_existing = self.conda_use_existing.isChecked()
        if use_existing:
            combobox = self.line_conda.combobox
            prefix = combobox.itemData(combobox.currentIndex()) 
            packages = get_conda_packages(prefix)
            self.line_conda.setEnabled(use_existing)
            self.label_message.setText(_('This project is not reproducible!'))
            self.packages_widget.add_packages(packages)
            self.packages_widget.setEnabled(not use_existing)
        else:
            self.line_conda.setEnabled(use_existing)
            self.label_message.setText('')
            self.packages_widget.setEnabled(not use_existing)
            self.packages_widget.clear()
        self.packages_widget.update_status()

    def get_icon(self):
        return ima.icon('genprefs')

    def get_name(self):
        return _("Conda environment")

    def apply_settings(self, options):
        pass


class VersionControlConfigPage(SpyderConfigPage):
    CONF_SECTION = "vcs"

    def setup_page(self):
        vcs_group = QGroupBox(_("Version Control"))
        vcs_button_group = QButtonGroup(vcs_group)
        vcs_label = QLabel(_("Select if you want to use git version control "
                             "for the project:"))
        self.radio_vcs_disabled = self.create_radiobutton(
            _("Do not use"),
            'vcs_disabled',
            button_group=vcs_button_group,
        )
        self.radio_vcs_existing = self.create_radiobutton(
            _("Use existing repository in project folder"),
            'vcs_init',
            button_group=vcs_button_group,
        )
        self.radio_vcs_init = self.create_radiobutton(
            _("Initialize a local repository for the project"),
            'vcs_init',
            button_group=vcs_button_group,
        )
        self.radio_vcs_clone = self.create_radiobutton(
            _("Clone from existing project"),
            'vcs_clone',
            button_group=vcs_button_group,
        )
        self.line_repository = self.create_lineedit(
            _(""),
            'vcs_repository',
        )

        vcs_layout = QVBoxLayout()
        vcs_layout.addWidget(vcs_label)
        vcs_layout.addWidget(self.radio_vcs_disabled)
        vcs_layout.addWidget(self.radio_vcs_init)
        vcs_layout.addWidget(self.radio_vcs_existing)
        vcs_layout.addWidget(self.radio_vcs_clone)
        vcs_layout.addWidget(self.line_repository)
        vcs_group.setLayout(vcs_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(vcs_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def get_icon(self):
        return ima.icon('genprefs')

    def get_name(self):
        return _("Version Control")

    def apply_settings(self, options):
        pass



def show_project_prefences():
    """"""
    import qdarkstyle
    css = qdarkstyle.load_stylesheet_pyqt5()
    dlg = ProjectPreferences()
    dlg.setStyleSheet(css)
    pages = [GeneralProjectConfigPage, EnvironmentVariablesConfigPage]
    if is_anaconda:
        pages.append(CondaEnvironmentConfigPage)
    pages.append(VersionControlConfigPage)

    for CLASS in pages:
        widget = CLASS(dlg)
        widget.initialize(load=False)
        dlg.add_page(widget)

    dlg.show()


def test():
    """Local test."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    show_project_prefences()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
