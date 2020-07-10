# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main interpreter entry in Preferences."""

# Standard library imports
from __future__ import print_function

import os
import os.path as osp
import sys

# Third party imports
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QInputDialog, QLabel,
                            QLineEdit, QMessageBox, QPushButton, QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.preferences.configdialog import GeneralConfigPage
from spyder.py3compat import PY2, is_text_string, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.misc import get_python_executable
from spyder.utils import programs


class MainInterpreterConfigPage(GeneralConfigPage):
    CONF_SECTION = "main_interpreter"
    NAME = _("Python interpreter")
    ICON = ima.icon('python')

    def __init__(self, parent, main):
        GeneralConfigPage.__init__(self, parent, main)
        self.cus_exec_radio = None
        self.pyexec_edit = None
        self.cus_exec_combo = None

        # Python executable selection (initializing default values as well)
        executable = self.get_option('executable', get_python_executable())
        if self.get_option('default'):
            executable = get_python_executable()

        if not osp.isfile(executable):
            # This is absolutely necessary, in case the Python interpreter
            # executable has been moved since last Spyder execution (following
            # a Python distribution upgrade for example)
            self.set_option('executable', get_python_executable())
        elif executable.endswith('pythonw.exe'):
            # That should not be necessary because this case is already taken
            # care of by the `get_python_executable` function but, this was
            # implemented too late, so we have to fix it here too, in case
            # the Python executable has already been set with pythonw.exe:
            self.set_option('executable',
                            executable.replace("pythonw.exe", "python.exe"))

        if not self.get_option('default'):
            if not self.get_option('custom_interpreter'):
                self.set_option('custom_interpreter', ' ')
            self.set_custom_interpreters_list(executable)
            self.validate_custom_interpreters_list()

    def initialize(self):
        GeneralConfigPage.initialize(self)

    def setup_page(self):
        newcb = self.create_checkbox

        # Python executable Group
        pyexec_group = QGroupBox(_("Python interpreter"))
        pyexec_bg = QButtonGroup(pyexec_group)
        pyexec_label = QLabel(_("Select the Python interpreter for all Spyder "
                                "consoles"))
        self.def_exec_radio = self.create_radiobutton(
                                _("Default (i.e. the same as Spyder's)"),
                                'default', button_group=pyexec_bg)
        self.cus_exec_radio = self.create_radiobutton(
                                _("Use the following Python interpreter:"),
                                'custom', button_group=pyexec_bg)
        if os.name == 'nt':
            filters = _("Executables")+" (*.exe)"
        else:
            filters = None

        pyexec_layout = QVBoxLayout()
        pyexec_layout.addWidget(pyexec_label)
        pyexec_layout.addWidget(self.def_exec_radio)
        pyexec_layout.addWidget(self.cus_exec_radio)
        self.validate_custom_interpreters_list()
        self.cus_exec_combo = self.create_file_combobox(
            _('Recent custom interpreters'),
            self.get_option('custom_interpreters_list'),
            'custom_interpreter',
            filters=filters,
            default_line_edit=True,
            adjust_to_contents=True,
            validate_callback=programs.is_python_interpreter,
        )
        self.def_exec_radio.toggled.connect(self.cus_exec_combo.setDisabled)
        self.cus_exec_radio.toggled.connect(self.cus_exec_combo.setEnabled)
        pyexec_layout.addWidget(self.cus_exec_combo)
        pyexec_group.setLayout(pyexec_layout)

        self.pyexec_edit = self.cus_exec_combo.combobox.lineEdit()

        # UMR Group
        umr_group = QGroupBox(_("User Module Reloader (UMR)"))
        umr_label = QLabel(_("UMR forces Python to reload modules which were "
                             "imported when executing a file in a Python or "
                             "IPython console with the <i>runfile</i> "
                             "function."))
        umr_label.setWordWrap(True)
        umr_enabled_box = newcb(_("Enable UMR"), 'umr/enabled',
                                msg_if_enabled=True, msg_warning=_(
                        "This option will enable the User Module Reloader (UMR) "
                        "in Python/IPython consoles. UMR forces Python to "
                        "reload deeply modules during import when running a "
                        "Python script using the Spyder's builtin function "
                        "<b>runfile</b>."
                        "<br><br><b>1.</b> UMR may require to restart the "
                        "console in which it will be called "
                        "(otherwise only newly imported modules will be "
                        "reloaded when executing files)."
                        "<br><br><b>2.</b> If errors occur when re-running a "
                        "PyQt-based program, please check that the Qt objects "
                        "are properly destroyed (e.g. you may have to use the "
                        "attribute <b>Qt.WA_DeleteOnClose</b> on your main "
                        "window, using the <b>setAttribute</b> method)"),
                                )
        umr_verbose_box = newcb(_("Show reloaded modules list"),
                                'umr/verbose', msg_info=_(
                                "Please note that these changes will "
                                "be applied only to new consoles"))
        umr_namelist_btn = QPushButton(
                            _("Set UMR excluded (not reloaded) modules"))
        umr_namelist_btn.clicked.connect(self.set_umr_namelist)

        umr_layout = QVBoxLayout()
        umr_layout.addWidget(umr_label)
        umr_layout.addWidget(umr_enabled_box)
        umr_layout.addWidget(umr_verbose_box)
        umr_layout.addWidget(umr_namelist_btn)
        umr_group.setLayout(umr_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(pyexec_group)
        vlayout.addWidget(umr_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

    def warn_python_compatibility(self, pyexec):
        if not osp.isfile(pyexec):
            return
        spyder_version = sys.version_info[0]
        try:
            args = ["-c", "import sys; print(sys.version_info[0])"]
            proc = programs.run_program(pyexec, args)
            console_version = int(proc.communicate()[0])
        except IOError:
            console_version = spyder_version
        except ValueError:
            return False
        if spyder_version != console_version:
            QMessageBox.warning(self, _('Warning'),
                _("You selected a <b>Python %d</b> interpreter for the console "
                  "but Spyder is running on <b>Python %d</b>!.<br><br>"
                  "Although this is possible, we recommend you to install and "
                  "run Spyder directly with your selected interpreter, to avoid "
                  "seeing false warnings and errors due to the incompatible "
                  "syntax between these two Python versions."
                  ) % (console_version, spyder_version), QMessageBox.Ok)
        return True

    def set_umr_namelist(self):
        """Set UMR excluded modules name list"""
        arguments, valid = QInputDialog.getText(self, _('UMR'),
                                  _("Set the list of excluded modules as "
                                    "this: <i>numpy, scipy</i>"),
                                  QLineEdit.Normal,
                                  ", ".join(self.get_option('umr/namelist')))
        if valid:
            arguments = to_text_string(arguments)
            if arguments:
                namelist = arguments.replace(' ', '').split(',')
                fixed_namelist = []
                non_ascii_namelist = []
                for module_name in namelist:
                    if PY2:
                        if all(ord(c) < 128 for c in module_name):
                            if programs.is_module_installed(module_name):
                                fixed_namelist.append(module_name)
                        else:
                            QMessageBox.warning(self, _('Warning'),
                            _("You are working with Python 2, this means that "
                              "you can not import a module that contains non-"
                              "ascii characters."), QMessageBox.Ok)
                            non_ascii_namelist.append(module_name)
                    elif programs.is_module_installed(module_name):
                        fixed_namelist.append(module_name)
                invalid = ", ".join(set(namelist)-set(fixed_namelist)-
                                    set(non_ascii_namelist))
                if invalid:
                    QMessageBox.warning(self, _('UMR'),
                                        _("The following modules are not "
                                          "installed on your machine:\n%s"
                                          ) % invalid, QMessageBox.Ok)
                QMessageBox.information(self, _('UMR'),
                                    _("Please note that these changes will "
                                      "be applied only to new Python/IPython "
                                      "consoles"), QMessageBox.Ok)
            else:
                fixed_namelist = []
            self.set_option('umr/namelist', fixed_namelist)

    def set_custom_interpreters_list(self, value):
        """Update the list of interpreters used and the current one."""
        custom_list = self.get_option('custom_interpreters_list')
        if value not in custom_list:
            custom_list.append(value)
            self.set_option('custom_interpreters_list', custom_list)

    def validate_custom_interpreters_list(self):
        """Check that the used custom interpreters are still valid."""
        custom_list = self.get_option('custom_interpreters_list')
        valid_custom_list = []
        for value in custom_list:
            if osp.isfile(value) and programs.is_python_interpreter(value):
                valid_custom_list.append(value)
        self.set_option('custom_interpreters_list', valid_custom_list)

    def apply_settings(self, options):
        if not self.def_exec_radio.isChecked():
            executable = self.pyexec_edit.text()
            executable = osp.normpath(executable)
            if executable.endswith('pythonw.exe'):
                executable = executable.replace("pythonw.exe", "python.exe")

            # Set new interpreter
            self.set_custom_interpreters_list(executable)
            self.set_option('executable', executable)
            self.set_option('custom_interpreter', executable)

            # Update combobox items.
            custom_list = self.get_option('custom_interpreters_list')
            self.cus_exec_combo.combobox.clear()
            self.cus_exec_combo.combobox.addItems(custom_list)
            self.pyexec_edit.setText(executable)

            # Show warning compatibility message.
            self.warn_python_compatibility(executable)
        if not self.pyexec_edit.text():
            self.set_option('custom_interpreter', '')
        else:
            # This prevents showing an incorrect file name in the custom
            # line edit.
            if not programs.is_python_interpreter(self.pyexec_edit.text()):
                self.pyexec_edit.clear()
                self.set_option('custom_interpreter', '')
        if ('default' in options or 'custom' in options
                or 'custom_interpreter' in options):
            self.main.sig_main_interpreter_changed.emit()
        self.main.apply_statusbar_settings()
