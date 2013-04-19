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
                                QRadioButton, QMessageBox)
from spyderlib.qt.QtCore import SIGNAL, SLOT, Qt
from spyderlib.qt.compat import getexistingdirectory

import os
import os.path as osp

# Local imports
from spyderlib.baseconfig import _
from spyderlib.config import CONF
from spyderlib.utils.qthelpers import get_icon, get_std_icon
from spyderlib.plugins.configdialog import SizeMixin


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
        self.python_args = None
        self.python_args_enabled = None
        self.set(CONF.get('run', 'defaultconfiguration', default={}))
        if fname is not None:
            self.wdir = osp.dirname(fname)
            self.wdir_enabled = True
        
    def set(self, options):
        self.args = options.get('args', '')
        self.args_enabled = options.get('args/enabled', False)
        self.wdir = options.get('workdir', os.getcwdu())
        self.wdir_enabled = options.get('workdir/enabled', False)
        self.current = options.get('current', True)
        self.systerm = options.get('systerm', False)
        self.interact = options.get('interact', False)
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
        self.runconf = RunConfiguration()
        
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
        
        radio_group = QGroupBox(_("Interpreter"))
        radio_layout = QVBoxLayout()
        radio_group.setLayout(radio_layout)
        self.current_radio = QRadioButton(_("Execute in current Python "
                                            "or IPython interpreter"))
        radio_layout.addWidget(self.current_radio)
        self.new_radio = QRadioButton(_("Execute in a new dedicated "
                                        "Python interpreter"))
        radio_layout.addWidget(self.new_radio)
        self.systerm_radio = QRadioButton(_("Execute in an external "
                                            "System terminal"))
        radio_layout.addWidget(self.systerm_radio)
        
        new_group = QGroupBox(_("Dedicated Python interpreter"))
        self.connect(self.current_radio, SIGNAL("toggled(bool)"),
                     new_group.setDisabled)
        new_layout = QGridLayout()
        new_group.setLayout(new_layout)
        self.interact_cb = QCheckBox(_("Interact with the Python "
                                       "interpreter after execution"))
        new_layout.addWidget(self.interact_cb, 1, 0, 1, -1)
        self.pclo_cb = QCheckBox(_("Command line options:"))
        new_layout.addWidget(self.pclo_cb, 2, 0)
        self.pclo_edit = QLineEdit()
        self.connect(self.pclo_cb, SIGNAL("toggled(bool)"),
                     self.pclo_edit.setEnabled)
        self.pclo_edit.setEnabled(False)
        new_layout.addWidget(self.pclo_edit, 2, 1)
        pclo_label = QLabel(_("The <b>-u</b> option is "
                              "added to these commands"))
        pclo_label.setWordWrap(True)
        new_layout.addWidget(pclo_label, 3, 1)
        
        #TODO: Add option for "Post-mortem debugging"
        
        layout = QVBoxLayout()
        layout.addWidget(radio_group)
        layout.addWidget(common_group)
        layout.addWidget(new_group)
        self.setLayout(layout)

    def select_directory(self):
        """Select directory"""
        basedir = unicode(self.wd_edit.text())
        if not osp.isdir(basedir):
            basedir = os.getcwdu()
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
            self.new_radio.setChecked(True)
        self.interact_cb.setChecked(self.runconf.interact)
        self.pclo_cb.setChecked(self.runconf.python_args_enabled)
        self.pclo_edit.setText(self.runconf.python_args)
    
    def get(self):
        self.runconf.args_enabled = self.clo_cb.isChecked()
        self.runconf.args = unicode(self.clo_edit.text())
        self.runconf.wdir_enabled = self.wd_cb.isChecked()
        self.runconf.wdir = unicode(self.wd_edit.text())
        self.runconf.current = self.current_radio.isChecked()
        self.runconf.systerm = self.systerm_radio.isChecked()
        self.runconf.interact = self.interact_cb.isChecked()
        self.runconf.python_args_enabled = self.pclo_cb.isChecked()
        self.runconf.python_args = unicode(self.pclo_edit.text())
        return self.runconf.get()
    
    def is_valid(self):
        wdir = unicode(self.wd_edit.text())
        if not self.wd_cb.isChecked() or osp.isdir(wdir):
            return True
        else:
            QMessageBox.critical(self, _("Run configuration"),
                                 _("The following working directory is "
                                   "not valid:<br><b>%s</b>") % wdir)
            return False


class BaseRunConfigDialog(QDialog, SizeMixin):
    """Run configuration dialog box, base widget"""
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        SizeMixin.__init__(self)
        
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setWindowIcon(get_icon("run.png"))
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
        self.setWindowTitle(_("Run %s") % osp.basename(fname))
            
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
        self.file_to_run = unicode(self.combo.currentText())
        
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
            filename = unicode(self.combo.itemText(index))
            runconfigoptions = self.stack.widget(index)
            if not runconfigoptions.is_valid():
                return
            options = runconfigoptions.get()
            configurations.append( (filename, options) )
        _set_run_configurations(configurations)
        QDialog.accept(self)
