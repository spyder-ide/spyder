# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Run dialogs and widgets and data models."""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                            QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                            QLabel, QLineEdit, QMessageBox, QPushButton,
                            QRadioButton, QSizePolicy, QStackedWidget,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.translations import get_translation
from spyder.config.manager import CONF
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.misc import getcwd_or_home

# Localization
_ = get_translation("spyder")

CURRENT_INTERPRETER = _("Execute in current console")
DEDICATED_INTERPRETER = _("Execute in a dedicated console")
SYSTERM_INTERPRETER = _("Execute in an external system terminal")

CURRENT_INTERPRETER_OPTION = 'default/interpreter/current'
DEDICATED_INTERPRETER_OPTION = 'default/interpreter/dedicated'
SYSTERM_INTERPRETER_OPTION = 'default/interpreter/systerm'

WDIR_USE_SCRIPT_DIR_OPTION = 'default/wdir/use_script_directory'
WDIR_USE_CWD_DIR_OPTION = 'default/wdir/use_cwd_directory'
WDIR_USE_FIXED_DIR_OPTION = 'default/wdir/use_fixed_directory'
WDIR_FIXED_DIR_OPTION = 'default/wdir/fixed_directory'

ALWAYS_OPEN_FIRST_RUN = _("Always show %s on a first file run")
ALWAYS_OPEN_FIRST_RUN_OPTION = 'open_on_firstrun'

CLEAR_ALL_VARIABLES = _("Remove all variables before execution")
CONSOLE_NAMESPACE = _("Run in console's namespace instead of an empty one")
POST_MORTEM = _("Directly enter debugging when errors appear")
INTERACT = _("Interact with the Python console after execution")

FILE_DIR = _("The directory of the file being executed")
CW_DIR = _("The current working directory")
FIXED_DIR = _("The following directory:")


class RunConfiguration(object):
    """Run configuration"""

    def __init__(self, fname=None):
        self.args = None
        self.args_enabled = None
        self.wdir = None
        self.wdir_enabled = None
        self.current = None
        self.systerm = None
        self.interact = None
        self.post_mortem = None
        self.python_args = None
        self.python_args_enabled = None
        self.clear_namespace = None
        self.console_namespace = None
        self.file_dir = None
        self.cw_dir = None
        self.fixed_dir = None
        self.dir = None

        self.set(CONF.get('run', 'defaultconfiguration', default={}))

    def set(self, options):
        self.args = options.get('args', '')
        self.args_enabled = options.get('args/enabled', False)
        self.current = options.get('current',
                           CONF.get('run', CURRENT_INTERPRETER_OPTION, True))
        self.systerm = options.get('systerm',
                           CONF.get('run', SYSTERM_INTERPRETER_OPTION, False))
        self.interact = options.get('interact',
                           CONF.get('run', 'interact', False))
        self.post_mortem = options.get('post_mortem',
                           CONF.get('run', 'post_mortem', False))
        self.python_args = options.get('python_args', '')
        self.python_args_enabled = options.get('python_args/enabled', False)
        self.clear_namespace = options.get('clear_namespace',
                                    CONF.get('run', 'clear_namespace', False))
        self.console_namespace = options.get('console_namespace',
                                   CONF.get('run', 'console_namespace', False))
        self.file_dir = options.get('file_dir',
                           CONF.get('run', WDIR_USE_SCRIPT_DIR_OPTION, True))
        self.cw_dir = options.get('cw_dir',
                           CONF.get('run', WDIR_USE_CWD_DIR_OPTION, False))
        self.fixed_dir = options.get('fixed_dir',
                           CONF.get('run', WDIR_USE_FIXED_DIR_OPTION, False))
        self.dir = options.get('dir', '')

    def get(self):
        return {
                'args/enabled': self.args_enabled,
                'args': self.args,
                'workdir/enabled': self.wdir_enabled,
                'workdir': self.wdir,
                'current': self.current,
                'systerm': self.systerm,
                'interact': self.interact,
                'post_mortem': self.post_mortem,
                'python_args/enabled': self.python_args_enabled,
                'python_args': self.python_args,
                'clear_namespace': self.clear_namespace,
                'console_namespace': self.console_namespace,
                'file_dir': self.file_dir,
                'cw_dir': self.cw_dir,
                'fixed_dir': self.fixed_dir,
                'dir': self.dir
                }

    def get_working_directory(self):
       return self.dir

    def get_arguments(self):
        if self.args_enabled:
            return self.args
        else:
            return ''

    def get_python_arguments(self):
        if self.python_args_enabled:
            return self.python_args
        else:
            return ''


def _get_run_configurations():
    history_count = CONF.get('run', 'history', 20)
    try:
        return [(filename, options)
                for filename, options in CONF.get('run', 'configurations', [])
                if osp.isfile(filename)][:history_count]
    except ValueError:
        CONF.set('run', 'configurations', [])
        return []


def _set_run_configurations(configurations):
    history_count = CONF.get('run', 'history', 20)
    CONF.set('run', 'configurations', configurations[:history_count])


def get_run_configuration(fname):
    """Return script *fname* run configuration"""
    configurations = _get_run_configurations()
    for filename, options in configurations:
        if fname == filename:
            runconf = RunConfiguration()
            runconf.set(options)
            return runconf


class RunConfigOptions(QWidget):
    """Run configuration options"""
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.dir = None
        self.runconf = RunConfiguration()
        firstrun_o = CONF.get('run', ALWAYS_OPEN_FIRST_RUN_OPTION, False)

        # --- Interpreter ---
        interpreter_group = QGroupBox(_("Console"))
        interpreter_layout = QVBoxLayout()
        interpreter_group.setLayout(interpreter_layout)

        self.current_radio = QRadioButton(CURRENT_INTERPRETER)
        interpreter_layout.addWidget(self.current_radio)

        self.dedicated_radio = QRadioButton(DEDICATED_INTERPRETER)
        interpreter_layout.addWidget(self.dedicated_radio)

        self.systerm_radio = QRadioButton(SYSTERM_INTERPRETER)
        interpreter_layout.addWidget(self.systerm_radio)

        # --- General settings ----
        common_group = QGroupBox(_("General settings"))
        common_layout = QGridLayout()
        common_group.setLayout(common_layout)

        self.clear_var_cb = QCheckBox(CLEAR_ALL_VARIABLES)
        common_layout.addWidget(self.clear_var_cb, 0, 0)

        self.console_ns_cb = QCheckBox(CONSOLE_NAMESPACE)
        common_layout.addWidget(self.console_ns_cb, 1, 0)

        self.post_mortem_cb = QCheckBox(POST_MORTEM)
        common_layout.addWidget(self.post_mortem_cb, 2, 0)

        self.clo_cb = QCheckBox(_("Command line options:"))
        common_layout.addWidget(self.clo_cb, 3, 0)
        self.clo_edit = QLineEdit()
        self.clo_cb.toggled.connect(self.clo_edit.setEnabled)
        self.clo_edit.setEnabled(False)
        common_layout.addWidget(self.clo_edit, 3, 1)

        # --- Working directory ---
        wdir_group = QGroupBox(_("Working directory settings"))
        wdir_layout = QVBoxLayout()
        wdir_group.setLayout(wdir_layout)

        self.file_dir_radio = QRadioButton(FILE_DIR)
        wdir_layout.addWidget(self.file_dir_radio)

        self.cwd_radio = QRadioButton(CW_DIR)
        wdir_layout.addWidget(self.cwd_radio)

        fixed_dir_layout = QHBoxLayout()
        self.fixed_dir_radio = QRadioButton(FIXED_DIR)
        fixed_dir_layout.addWidget(self.fixed_dir_radio)
        self.wd_edit = QLineEdit()
        self.fixed_dir_radio.toggled.connect(self.wd_edit.setEnabled)
        self.wd_edit.setEnabled(False)
        fixed_dir_layout.addWidget(self.wd_edit)
        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select directory"))
        browse_btn.clicked.connect(self.select_directory)
        fixed_dir_layout.addWidget(browse_btn)
        wdir_layout.addLayout(fixed_dir_layout)

        # --- System terminal ---
        external_group = QGroupBox(_("External system terminal"))
        external_group.setDisabled(True)

        self.systerm_radio.toggled.connect(external_group.setEnabled)

        external_layout = QGridLayout()
        external_group.setLayout(external_layout)
        self.interact_cb = QCheckBox(INTERACT)
        external_layout.addWidget(self.interact_cb, 1, 0, 1, -1)

        self.pclo_cb = QCheckBox(_("Command line options:"))
        external_layout.addWidget(self.pclo_cb, 3, 0)
        self.pclo_edit = QLineEdit()
        self.pclo_cb.toggled.connect(self.pclo_edit.setEnabled)
        self.pclo_edit.setEnabled(False)
        self.pclo_edit.setToolTip(_("<b>-u</b> is added to the "
                                    "other options you set here"))
        external_layout.addWidget(self.pclo_edit, 3, 1)

        # Checkbox to preserve the old behavior, i.e. always open the dialog
        # on first run
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        self.firstrun_cb = QCheckBox(ALWAYS_OPEN_FIRST_RUN % _("this dialog"))
        self.firstrun_cb.clicked.connect(self.set_firstrun_o)
        self.firstrun_cb.setChecked(firstrun_o)

        layout = QVBoxLayout()
        layout.addWidget(interpreter_group)
        layout.addWidget(common_group)
        layout.addWidget(wdir_group)
        layout.addWidget(external_group)
        layout.addWidget(hline)
        layout.addWidget(self.firstrun_cb)
        self.setLayout(layout)

    def select_directory(self):
        """Select directory"""
        basedir = str(self.wd_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd_or_home()
        directory = getexistingdirectory(self, _("Select directory"), basedir)
        if directory:
            self.wd_edit.setText(directory)
            self.dir = directory

    def set(self, options):
        self.runconf.set(options)
        self.clo_cb.setChecked(self.runconf.args_enabled)
        self.clo_edit.setText(self.runconf.args)
        if self.runconf.current:
            self.current_radio.setChecked(True)
        elif self.runconf.systerm:
            self.systerm_radio.setChecked(True)
        else:
            self.dedicated_radio.setChecked(True)
        self.interact_cb.setChecked(self.runconf.interact)
        self.post_mortem_cb.setChecked(self.runconf.post_mortem)
        self.pclo_cb.setChecked(self.runconf.python_args_enabled)
        self.pclo_edit.setText(self.runconf.python_args)
        self.clear_var_cb.setChecked(self.runconf.clear_namespace)
        self.console_ns_cb.setChecked(self.runconf.console_namespace)
        self.file_dir_radio.setChecked(self.runconf.file_dir)
        self.cwd_radio.setChecked(self.runconf.cw_dir)
        self.fixed_dir_radio.setChecked(self.runconf.fixed_dir)
        self.dir = self.runconf.dir
        self.wd_edit.setText(self.dir)

    def get(self):
        self.runconf.args_enabled = self.clo_cb.isChecked()
        self.runconf.args = str(self.clo_edit.text())
        self.runconf.current = self.current_radio.isChecked()
        self.runconf.systerm = self.systerm_radio.isChecked()
        self.runconf.interact = self.interact_cb.isChecked()
        self.runconf.post_mortem = self.post_mortem_cb.isChecked()
        self.runconf.python_args_enabled = self.pclo_cb.isChecked()
        self.runconf.python_args = str(self.pclo_edit.text())
        self.runconf.clear_namespace = self.clear_var_cb.isChecked()
        self.runconf.console_namespace = self.console_ns_cb.isChecked()
        self.runconf.file_dir = self.file_dir_radio.isChecked()
        self.runconf.cw_dir = self.cwd_radio.isChecked()
        self.runconf.fixed_dir = self.fixed_dir_radio.isChecked()
        self.runconf.dir = self.wd_edit.text()
        return self.runconf.get()

    def is_valid(self):
        wdir = str(self.wd_edit.text())
        if not self.fixed_dir_radio.isChecked() or osp.isdir(wdir):
            return True
        else:
            QMessageBox.critical(self, _("Run configuration"),
                                 _("The following working directory is "
                                   "not valid:<br><b>%s</b>") % wdir)
            return False

    def set_firstrun_o(self):
        CONF.set('run', ALWAYS_OPEN_FIRST_RUN_OPTION,
                 self.firstrun_cb.isChecked())


class BaseRunConfigDialog(QDialog):
    """Run configuration dialog box, base widget"""
    size_change = Signal(QSize)

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setWindowIcon(ima.icon('run_settings'))
        layout = QVBoxLayout()
        self.setLayout(layout)

    def add_widgets(self, *widgets_or_spacings):
        """Add widgets/spacing to dialog vertical layout"""
        layout = self.layout()
        for widget_or_spacing in widgets_or_spacings:
            if isinstance(widget_or_spacing, int):
                layout.addSpacing(widget_or_spacing)
            else:
                layout.addWidget(widget_or_spacing)

    def add_button_box(self, stdbtns):
        """Create dialog button box and add it to the dialog layout"""
        bbox = QDialogButtonBox(stdbtns)
        run_btn = bbox.addButton(_("Run"), QDialogButtonBox.AcceptRole)
        run_btn.clicked.connect(self.run_btn_clicked)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)
        self.layout().addLayout(btnlayout)

    def resizeEvent(self, event):
        """
        Reimplement Qt method to be able to save the widget's size from the
        main application
        """
        QDialog.resizeEvent(self, event)
        self.size_change.emit(self.size())

    def run_btn_clicked(self):
        """Run button was just clicked"""
        pass

    def setup(self, fname):
        """Setup Run Configuration dialog with filename *fname*"""
        raise NotImplementedError


class RunConfigOneDialog(BaseRunConfigDialog):
    """Run configuration dialog box: single file version"""
    def __init__(self, parent=None):
        BaseRunConfigDialog.__init__(self, parent)
        self.filename = None
        self.runconfigoptions = None

    def setup(self, fname):
        """Setup Run Configuration dialog with filename *fname*"""
        self.filename = fname
        self.runconfigoptions = RunConfigOptions(self)
        self.runconfigoptions.set(RunConfiguration(fname).get())
        self.add_widgets(self.runconfigoptions)
        self.add_button_box(QDialogButtonBox.Cancel)
        self.setWindowTitle(_("Run settings for %s") % osp.basename(fname))

    @Slot()
    def accept(self):
        """Reimplement Qt method"""
        if not self.runconfigoptions.is_valid():
            return
        configurations = _get_run_configurations()
        configurations.insert(0, (self.filename, self.runconfigoptions.get()))
        _set_run_configurations(configurations)
        QDialog.accept(self)

    def get_configuration(self):
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.runconfigoptions.runconf


class RunConfigDialog(BaseRunConfigDialog):
    """Run configuration dialog box: multiple file version"""
    def __init__(self, parent=None):
        BaseRunConfigDialog.__init__(self, parent)
        self.file_to_run = None
        self.combo = None
        self.stack = None

    def run_btn_clicked(self):
        """Run button was just clicked"""
        self.file_to_run = str(self.combo.currentText())

    def setup(self, fname):
        """Setup Run Configuration dialog with filename *fname*"""
        combo_label = QLabel(_("Select a run configuration:"))
        self.combo = QComboBox()
        self.combo.setMaxVisibleItems(20)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.stack = QStackedWidget()

        configurations = _get_run_configurations()
        for index, (filename, options) in enumerate(configurations):
            if fname == filename:
                break
        else:
            # There is no run configuration for script *fname*:
            # creating a temporary configuration that will be kept only if
            # dialog changes are accepted by the user
            configurations.insert(0, (fname, RunConfiguration(fname).get()))
            index = 0
        for filename, options in configurations:
            widget = RunConfigOptions(self)
            widget.set(options)
            self.combo.addItem(filename)
            self.stack.addWidget(widget)
        self.combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.combo.setCurrentIndex(index)

        self.add_widgets(combo_label, self.combo, 10, self.stack)
        self.add_button_box(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)

        self.setWindowTitle(_("Run configuration per file"))

    def accept(self):
        """Reimplement Qt method"""
        configurations = []
        for index in range(self.stack.count()):
            filename = str(self.combo.itemText(index))
            runconfigoptions = self.stack.widget(index)
            if index == self.stack.currentIndex() and\
               not runconfigoptions.is_valid():
                return
            options = runconfigoptions.get()
            configurations.append( (filename, options) )
        _set_run_configurations(configurations)
        QDialog.accept(self)
