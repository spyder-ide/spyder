# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Run configurations related dialogs and widgets and data models"""

from spyderlib.qt.QtGui import (QVBoxLayout, QDialog, QWidget, QGroupBox,
                                QLabel, QPushButton, QCheckBox, QLineEdit,
                                QComboBox, QHBoxLayout, QDialogButtonBox,
                                QStackedWidget, QGridLayout, QSizePolicy,
                                QRadioButton, QMessageBox, QFrame,
                                QButtonGroup)
from spyderlib.qt.QtCore import SIGNAL, SLOT, Qt
from spyderlib.qt.compat import getexistingdirectory

import os.path as osp

# Local imports
from spyderlib.baseconfig import _
from spyderlib.config import CONF
from spyderlib.utils.qthelpers import get_icon, get_std_icon
from spyderlib.plugins.configdialog import GeneralConfigPage
from spyderlib.py3compat import to_text_string, getcwd


CURRENT_INTERPRETER = _("Execute in current Python or IPython console")
DEDICATED_INTERPRETER = _("Execute in a new dedicated Python console")
SYSTERM_INTERPRETER = _("Execute in an external System terminal")

CURRENT_INTERPRETER_OPTION = 'default/interpreter/current'
DEDICATED_INTERPRETER_OPTION = 'default/interpreter/dedicated'
SYSTERM_INTERPRETER_OPTION = 'default/interpreter/systerm'

WDIR_USE_SCRIPT_DIR_OPTION = 'default/wdir/use_script_directory'
WDIR_USE_FIXED_DIR_OPTION = 'default/wdir/use_fixed_directory'
WDIR_FIXED_DIR_OPTION = 'default/wdir/fixed_directory'

ALWAYS_OPEN_FIRST_RUN = _("Always show %s on a first file run")
ALWAYS_OPEN_FIRST_RUN_OPTION = 'open_on_firstrun'


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
        self.show_kill_warning = None
        self.python_args = None
        self.python_args_enabled = None
        self.set(CONF.get('run', 'defaultconfiguration', default={}))
        if fname is not None and\
           CONF.get('run', WDIR_USE_SCRIPT_DIR_OPTION, True):
            self.wdir = osp.dirname(fname)
            self.wdir_enabled = True
        
    def set(self, options):
        self.args = options.get('args', '')
        self.args_enabled = options.get('args/enabled', False)
        if CONF.get('run', WDIR_USE_FIXED_DIR_OPTION, False):
            default_wdir = CONF.get('run', WDIR_FIXED_DIR_OPTION, getcwd())
            self.wdir = options.get('workdir', default_wdir)
            self.wdir_enabled = True
        else:
            self.wdir = options.get('workdir', getcwd())
            self.wdir_enabled = options.get('workdir/enabled', False)
        self.current = options.get('current',
                           CONF.get('run', CURRENT_INTERPRETER_OPTION, True))
        self.systerm = options.get('systerm',
                           CONF.get('run', SYSTERM_INTERPRETER_OPTION, False))
        self.interact = options.get('interact', False)
        self.show_kill_warning = options.get('show_kill_warning', True)
        self.python_args = options.get('python_args', '')
        self.python_args_enabled = options.get('python_args/enabled', False)
        
    def get(self):
        return {
                'args/enabled': self.args_enabled,
                'args': self.args,
                'workdir/enabled': self.wdir_enabled,
                'workdir': self.wdir,
                'current': self.current,
                'systerm': self.systerm,
                'interact': self.interact,
                'show_kill_warning': self.show_kill_warning,
                'python_args/enabled': self.python_args_enabled,
                'python_args': self.python_args,
                }
        
    def get_working_directory(self):
        if self.wdir_enabled:
            return self.wdir
        else:
            return ''
        
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

        self.current_radio = None
        self.dedicated_radio = None
        self.systerm_radio = None

        self.runconf = RunConfiguration()
        
        firstrun_o = CONF.get('run', ALWAYS_OPEN_FIRST_RUN_OPTION, False)

        # --- General settings ----
        common_group = QGroupBox(_("General settings"))
        common_layout = QGridLayout()
        common_group.setLayout(common_layout)
        self.clo_cb = QCheckBox(_("Command line options:"))
        common_layout.addWidget(self.clo_cb, 0, 0)
        self.clo_edit = QLineEdit()
        self.connect(self.clo_cb, SIGNAL("toggled(bool)"),
                     self.clo_edit.setEnabled)
        self.clo_edit.setEnabled(False)
        common_layout.addWidget(self.clo_edit, 0, 1)
        self.wd_cb = QCheckBox(_("Working directory:"))
        common_layout.addWidget(self.wd_cb, 1, 0)
        wd_layout = QHBoxLayout()
        self.wd_edit = QLineEdit()
        self.connect(self.wd_cb, SIGNAL("toggled(bool)"),
                     self.wd_edit.setEnabled)
        self.wd_edit.setEnabled(False)
        wd_layout.addWidget(self.wd_edit)
        browse_btn = QPushButton(get_std_icon('DirOpenIcon'), "", self)
        browse_btn.setToolTip(_("Select directory"))
        self.connect(browse_btn, SIGNAL("clicked()"), self.select_directory)
        wd_layout.addWidget(browse_btn)
        common_layout.addLayout(wd_layout, 1, 1)
        
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
        
        # --- Dedicated interpreter ---
        new_group = QGroupBox(_("Dedicated Python console"))
        self.connect(self.current_radio, SIGNAL("toggled(bool)"),
                     new_group.setDisabled)
        new_layout = QGridLayout()
        new_group.setLayout(new_layout)
        self.interact_cb = QCheckBox(_("Interact with the Python "
                                       "console after execution"))
        new_layout.addWidget(self.interact_cb, 1, 0, 1, -1)
        
        self.show_kill_warning_cb = QCheckBox(_("Show warning when killing"
                                                " running process"))
        new_layout.addWidget(self.show_kill_warning_cb, 2, 0, 1, -1)
        self.pclo_cb = QCheckBox(_("Command line options:"))
        new_layout.addWidget(self.pclo_cb, 3, 0)
        self.pclo_edit = QLineEdit()
        self.connect(self.pclo_cb, SIGNAL("toggled(bool)"),
                     self.pclo_edit.setEnabled)
        self.pclo_edit.setEnabled(False)
        self.pclo_edit.setToolTip(_("<b>-u</b> is added to the "
                                    "other options you set here"))
        new_layout.addWidget(self.pclo_edit, 3, 1)
        
        #TODO: Add option for "Post-mortem debugging"

        # Checkbox to preserve the old behavior, i.e. always open the dialog
        # on first run
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        self.firstrun_cb = QCheckBox(ALWAYS_OPEN_FIRST_RUN % _("this dialog"))
        self.connect(self.firstrun_cb, SIGNAL("clicked(bool)"),
                     self.set_firstrun_o)
        self.firstrun_cb.setChecked(firstrun_o)
        
        layout = QVBoxLayout()
        layout.addWidget(interpreter_group)
        layout.addWidget(common_group)
        layout.addWidget(new_group)
        layout.addWidget(hline)
        layout.addWidget(self.firstrun_cb)
        self.setLayout(layout)

    def select_directory(self):
        """Select directory"""
        basedir = to_text_string(self.wd_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd()
        directory = getexistingdirectory(self, _("Select directory"), basedir)
        if directory:
            self.wd_edit.setText(directory)
            self.wd_cb.setChecked(True)
        
    def set(self, options):
        self.runconf.set(options)
        self.clo_cb.setChecked(self.runconf.args_enabled)
        self.clo_edit.setText(self.runconf.args)
        self.wd_cb.setChecked(self.runconf.wdir_enabled)
        self.wd_edit.setText(self.runconf.wdir)
        if self.runconf.current:
            self.current_radio.setChecked(True)
        elif self.runconf.systerm:
            self.systerm_radio.setChecked(True)
        else:
            self.dedicated_radio.setChecked(True)
        self.interact_cb.setChecked(self.runconf.interact)
        self.show_kill_warning_cb.setChecked(self.runconf.show_kill_warning)
        self.pclo_cb.setChecked(self.runconf.python_args_enabled)
        self.pclo_edit.setText(self.runconf.python_args)
    
    def get(self):
        self.runconf.args_enabled = self.clo_cb.isChecked()
        self.runconf.args = to_text_string(self.clo_edit.text())
        self.runconf.wdir_enabled = self.wd_cb.isChecked()
        self.runconf.wdir = to_text_string(self.wd_edit.text())
        self.runconf.current = self.current_radio.isChecked()
        self.runconf.systerm = self.systerm_radio.isChecked()
        self.runconf.interact = self.interact_cb.isChecked()
        self.runconf.show_kill_warning = self.show_kill_warning_cb.isChecked()
        self.runconf.python_args_enabled = self.pclo_cb.isChecked()
        self.runconf.python_args = to_text_string(self.pclo_edit.text())
        return self.runconf.get()
    
    def is_valid(self):
        wdir = to_text_string(self.wd_edit.text())
        if not self.wd_cb.isChecked() or osp.isdir(wdir):
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
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setWindowIcon(get_icon("run_settings.png"))
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
        self.connect(run_btn, SIGNAL('clicked()'), self.run_btn_clicked)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
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
        self.emit(SIGNAL("size_change(QSize)"), self.size())
    
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
        self.file_to_run = to_text_string(self.combo.currentText())
        
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
        self.connect(self.combo, SIGNAL("currentIndexChanged(int)"),
                     self.stack.setCurrentIndex)
        self.combo.setCurrentIndex(index)

        self.add_widgets(combo_label, self.combo, 10, self.stack)
        self.add_button_box(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)

        self.setWindowTitle(_("Run Settings"))
        
    def accept(self):
        """Reimplement Qt method"""
        configurations = []
        for index in range(self.stack.count()):
            filename = to_text_string(self.combo.itemText(index))
            runconfigoptions = self.stack.widget(index)
            if index == self.stack.currentIndex() and\
               not runconfigoptions.is_valid():
                return
            options = runconfigoptions.get()
            configurations.append( (filename, options) )
        _set_run_configurations(configurations)
        QDialog.accept(self)


class RunConfigPage(GeneralConfigPage):
    """Default Run Settings configuration page"""
    CONF_SECTION = "run"

    NAME = _("Run")
    ICON = "run.png"
    
    def setup_page(self):
        run_dlg = _("Run Settings")
        run_menu = _("Run")
        about_label = QLabel(_("The following are the default <i>%s</i>. "\
                               "These options may be overriden using the "\
                               "<b>%s</b> dialog box (see the <b>%s</b> menu)"\
                               ) % (run_dlg, run_dlg, run_menu))
        about_label.setWordWrap(True)

        interpreter_group = QGroupBox(_("Console"))
        interpreter_bg = QButtonGroup(interpreter_group)
        self.current_radio = self.create_radiobutton(CURRENT_INTERPRETER,
                                CURRENT_INTERPRETER_OPTION, True,
                                button_group=interpreter_bg)
        self.dedicated_radio = self.create_radiobutton(DEDICATED_INTERPRETER,
                                DEDICATED_INTERPRETER_OPTION, False,
                                button_group=interpreter_bg)
        self.systerm_radio = self.create_radiobutton(SYSTERM_INTERPRETER,
                                SYSTERM_INTERPRETER_OPTION, False,
                                button_group=interpreter_bg)

        interpreter_layout = QVBoxLayout()
        interpreter_group.setLayout(interpreter_layout)
        interpreter_layout.addWidget(self.current_radio)
        interpreter_layout.addWidget(self.dedicated_radio)
        interpreter_layout.addWidget(self.systerm_radio)
        
        wdir_group = QGroupBox(_("Working directory"))
        wdir_bg = QButtonGroup(wdir_group)
        wdir_label = QLabel(_("Default working directory is:"))
        wdir_label.setWordWrap(True)
        dirname_radio = self.create_radiobutton(_("the script directory"),
                                WDIR_USE_SCRIPT_DIR_OPTION, True,
                                button_group=wdir_bg)
        thisdir_radio = self.create_radiobutton(_("the following directory:"),
                                WDIR_USE_FIXED_DIR_OPTION, False,
                                button_group=wdir_bg)
        thisdir_bd = self.create_browsedir("", WDIR_FIXED_DIR_OPTION, getcwd())
        self.connect(thisdir_radio, SIGNAL("toggled(bool)"),
                     thisdir_bd.setEnabled)
        self.connect(dirname_radio, SIGNAL("toggled(bool)"),
                     thisdir_bd.setDisabled)
        thisdir_layout = QHBoxLayout()
        thisdir_layout.addWidget(thisdir_radio)
        thisdir_layout.addWidget(thisdir_bd)

        wdir_layout = QVBoxLayout()
        wdir_layout.addWidget(wdir_label)
        wdir_layout.addWidget(dirname_radio)
        wdir_layout.addLayout(thisdir_layout)
        wdir_group.setLayout(wdir_layout)

        firstrun_cb = self.create_checkbox(
                            ALWAYS_OPEN_FIRST_RUN % _("Run Settings dialog"),
                            ALWAYS_OPEN_FIRST_RUN_OPTION, False)
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(about_label)
        vlayout.addSpacing(10)
        vlayout.addWidget(interpreter_group)
        vlayout.addWidget(wdir_group)
        vlayout.addWidget(firstrun_cb)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def apply_settings(self, options):
        pass
