# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Run dialogs and widgets and data models."""

# Standard library imports
from datetime import datetime
import os.path as osp
from typing import Optional, Tuple, List, Dict
from uuid import uuid4

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                            QGroupBox, QHBoxLayout, QLabel, QLineEdit, QLayout,
                            QRadioButton, QStackedWidget, QVBoxLayout, QWidget)

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.comboboxes import SpyderComboBox
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.plugins.run.api import (
    RunParameterFlags, WorkingDirSource, WorkingDirOpts,
    RunExecutionParameters, ExtendedRunExecutionParameters,
    RunExecutorConfigurationGroup, SupportedExecutionRunConfiguration)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import create_toolbutton



# Main constants
RUN_DEFAULT_CONFIG = _("Run file with default configuration")
RUN_CUSTOM_CONFIG = _("Run file with custom configuration")
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

ALWAYS_OPEN_FIRST_RUN = _("Always show %s for this run configuration")
ALWAYS_OPEN_FIRST_RUN_OPTION = 'open_on_firstrun'

CLEAR_ALL_VARIABLES = _("Remove all variables before execution")
CONSOLE_NAMESPACE = _("Run in console's namespace instead of an empty one")
POST_MORTEM = _("Directly enter debugging when errors appear")
INTERACT = _("Interact with the Python console after execution")

FILE_DIR = _("The directory of the configuration being executed")
CW_DIR = _("The current working directory")
FIXED_DIR = _("The following directory:")

STORE_PARAMS = _('Store current configuration as:')


class RunDialogStatus:
    Close = 0
    Save = 1
    Run = 2


class BaseRunConfigDialog(QDialog):
    """Run configuration dialog box, base widget"""
    size_change = Signal(QSize)

    def __init__(self, parent=None, disable_run_btn=False):
        QDialog.__init__(self, parent)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setWindowIcon(ima.icon('run_settings'))
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.disable_run_btn = disable_run_btn

    def add_widgets(self, *widgets_or_spacings):
        """Add widgets/spacing to dialog vertical layout"""
        layout = self.layout()
        for widget_or_spacing in widgets_or_spacings:
            if isinstance(widget_or_spacing, int):
                layout.addSpacing(widget_or_spacing)
            elif isinstance(widget_or_spacing, QLayout):
                layout.addLayout(widget_or_spacing)
            else:
                layout.addWidget(widget_or_spacing)
        return layout

    def add_button_box(self, stdbtns):
        """Create dialog button box and add it to the dialog layout"""
        self.bbox = SpyderDialogButtonBox(stdbtns)

        if not self.disable_run_btn:
            run_btn = self.bbox.addButton(
                _("Run"), QDialogButtonBox.ActionRole)
            run_btn.clicked.connect(self.run_btn_clicked)

        reset_deafults_btn = self.bbox.addButton(
            _('Reset'), QDialogButtonBox.ResetRole)
        reset_deafults_btn.clicked.connect(self.reset_btn_clicked)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        btnlayout = QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bbox)
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

    def reset_btn_clicked(self):
        """Reset button was clicked."""
        pass

    def ok_btn_clicked(self):
        """Ok button was clicked."""
        pass

    def setup(self):
        """Setup Run Configuration dialog with filename *fname*"""
        raise NotImplementedError


class ExecutionParametersDialog(BaseRunConfigDialog):
    """Run execution parameters edition dialog."""

    def __init__(
        self,
        parent,
        executor_params: Dict[Tuple[str, str], SupportedExecutionRunConfiguration],
        extensions: Optional[List[str]] = None,
        contexts: Optional[Dict[str, List[str]]] = None,
        default_params: Optional[ExtendedRunExecutionParameters] = None,
        extension: Optional[str] = None,
        context: Optional[str] = None
    ):
        super().__init__(parent, True)

        self.executor_params = executor_params
        self.default_params = default_params
        self.extensions = extensions or []
        self.contexts = contexts or {}
        self.extension = extension
        self.context = context

        self.parameters_name = None
        if default_params is not None:
            self.parameters_name = default_params['name']

        self.current_widget = None
        self.status = RunDialogStatus.Close

    def setup(self):
        ext_combo_label = QLabel(_("Select a file extension:"))
        context_combo_label = QLabel(_("Select a run context:"))

        self.extension_combo = SpyderComboBox(self)
        self.extension_combo.currentIndexChanged.connect(
            self.extension_changed)

        self.context_combo = SpyderComboBox(self)
        self.context_combo.currentIndexChanged.connect(self.context_changed)

        self.stack = QStackedWidget()
        self.executor_group = QGroupBox(_("Executor parameters"))
        executor_layout = QVBoxLayout(self.executor_group)
        executor_layout.addWidget(self.stack)

        self.wdir_group = QGroupBox(_("Working directory settings"))

        wdir_layout = QVBoxLayout(self.wdir_group)

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
        browse_btn = create_toolbutton(
            self,
            triggered=self.select_directory,
            icon=ima.icon('DirOpenIcon'),
            tip=_("Select directory")
            )
        fixed_dir_layout.addWidget(browse_btn)
        wdir_layout.addLayout(fixed_dir_layout)

        params_name_label = QLabel(_('Configuration name:'))
        self.store_params_text = QLineEdit()
        store_params_layout = QHBoxLayout()
        store_params_layout.addWidget(params_name_label)
        store_params_layout.addWidget(self.store_params_text)

        self.store_params_text.setPlaceholderText(_('My configuration name'))

        all_group = QVBoxLayout()
        all_group.addWidget(self.executor_group)
        all_group.addWidget(self.wdir_group)
        all_group.addLayout(store_params_layout)

        layout = self.add_widgets(ext_combo_label, self.extension_combo,
                                  context_combo_label, self.context_combo,
                                  10, all_group)

        widget_dialog = QWidget()
        widget_dialog.setMinimumWidth(600)
        widget_dialog.setLayout(layout)
        scroll_layout = QVBoxLayout(self)
        scroll_layout.addWidget(widget_dialog)
        self.add_button_box(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.setWindowTitle(_("Run parameters"))

        self.extension_combo.addItems(self.extensions)

        extension_index = 0
        if self.extension is not None:
            extension_index = self.extensions.index(self.extension)
            self.extension_combo.setEnabled(False)

        if self.context is not None:
            self.context_combo.setEnabled(False)

        self.extension_combo.setCurrentIndex(extension_index)

        if self.parameters_name:
            self.store_params_text.setText(self.parameters_name)

    def extension_changed(self, index: int):
        if index < 0:
            return

        self.selected_extension = self.extension_combo.itemText(index)
        contexts = self.contexts[self.selected_extension]

        self.context_combo.clear()
        self.context_combo.addItems(contexts)
        self.context_combo.setCurrentIndex(-1)

        context_index = 0
        if self.context is not None:
            context_index = contexts.index(self.context)
        self.context_combo.setCurrentIndex(context_index)

    def context_changed(self, index: int):
        if index < 0:
            return

        # Clear the QStackWidget contents
        self.current_widget = None
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)

        self.selected_context = self.context_combo.itemText(index)

        executor_conf_metadata = self.executor_params[
            (self.selected_extension, self.selected_context)]

        requires_cwd = executor_conf_metadata['requires_cwd']
        ConfigWidget = (executor_conf_metadata['configuration_widget'] or
                        RunExecutorConfigurationGroup)

        if executor_conf_metadata['configuration_widget'] is None:
            self.executor_group.setEnabled(False)
        else:
            self.executor_group.setEnabled(True)

        self.wdir_group.setEnabled(requires_cwd)

        self.current_widget = ConfigWidget(
            self, self.selected_context, self.selected_extension, {})
        self.stack.addWidget(self.current_widget)

        working_dir_params = WorkingDirOpts(
            source=WorkingDirSource.ConfigurationDirectory,
            path=None)
        exec_params = RunExecutionParameters(
            working_dir=working_dir_params,
            executor_params=None)

        default_params = self.current_widget.get_default_configuration()

        if self.default_params:
            params = self.default_params['params']
            working_dir_params = params['working_dir']
            exec_params = params

        params_set = exec_params['executor_params'] or default_params

        if params_set.keys() == default_params.keys():
            self.current_widget.set_configuration(params_set)

        source = working_dir_params['source']
        path = working_dir_params['path']

        if source == WorkingDirSource.ConfigurationDirectory:
            self.file_dir_radio.setChecked(True)
            self.cwd_radio.setChecked(False)
            self.fixed_dir_radio.setChecked(False)
            self.wd_edit.setText('')
        elif source == WorkingDirSource.CurrentDirectory:
            self.file_dir_radio.setChecked(False)
            self.cwd_radio.setChecked(True)
            self.fixed_dir_radio.setChecked(False)
            self.wd_edit.setText('')
        elif source == WorkingDirSource.CustomDirectory:
            self.file_dir_radio.setChecked(False)
            self.cwd_radio.setChecked(False)
            self.fixed_dir_radio.setChecked(True)
            self.wd_edit.setText(path)

        if (not self.executor_group.isEnabled() and not
                self.wdir_group.isEnabled()):
            ok_btn = self.bbox.button(QDialogButtonBox.Ok)
            ok_btn.setEnabled(False)

        self.adjustSize()

    def select_directory(self):
        """Select directory"""
        basedir = str(self.wd_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd_or_home()
        directory = getexistingdirectory(self, _("Select directory"), basedir)
        if directory:
            self.wd_edit.setText(directory)
            self.dir = directory

    def reset_btn_clicked(self):
        index = self.context_combo.currentIndex()
        self.context_changed(index)

    def run_btn_clicked(self):
        self.status |= RunDialogStatus.Run

    def ok_btn_clicked(self):
        self.status |= RunDialogStatus.Save

    def accept(self) -> None:
        self.status |= RunDialogStatus.Save
        widget_conf = self.current_widget.get_configuration()

        path = None
        source = None
        if self.file_dir_radio.isChecked():
            source = WorkingDirSource.ConfigurationDirectory
        elif self.cwd_radio.isChecked():
            source = WorkingDirSource.CurrentDirectory
        else:
            source = WorkingDirSource.CustomDirectory
            path = self.wd_edit.text()

        cwd_opts = WorkingDirOpts(source=source, path=path)

        exec_params = RunExecutionParameters(
            working_dir=cwd_opts, executor_params=widget_conf)

        if self.default_params:
            uuid = self.default_params['uuid']
        else:
            uuid = str(uuid4())
        name = self.store_params_text.text()
        if name == '':
            date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            name = f'Configuration-{date_str}'

        ext_exec_params = ExtendedRunExecutionParameters(
            uuid=uuid, name=name, params=exec_params
        )

        self.saved_conf = (self.selected_extension, self.selected_context,
                           ext_exec_params)
        super().accept()

    def get_configuration(
            self
    ) -> Tuple[str, str, ExtendedRunExecutionParameters]:

        return self.saved_conf


class RunDialog(BaseRunConfigDialog):
    """Run dialog used to configure run executors."""

    def __init__(
        self,
        parent=None,
        run_conf_model=None,
        executors_model=None,
        parameter_model=None,
        disable_run_btn=False
    ):
        super().__init__(parent, disable_run_btn=disable_run_btn)
        self.run_conf_model = run_conf_model
        self.executors_model = executors_model
        self.parameter_model = parameter_model
        self.current_widget = None
        self.status = RunDialogStatus.Close

    def setup(self):
        combo_label = QLabel(_("Select a run configuration:"))
        executor_label = QLabel(_("Select a run executor:"))

        self.configuration_combo = SpyderComboBox(self)
        self.executor_combo = SpyderComboBox(self)

        parameters_label = QLabel(_("Select the run parameters:"))
        self.parameters_combo = SpyderComboBox(self)
        self.stack = QStackedWidget()
        executor_layout = QVBoxLayout()
        executor_layout.addWidget(parameters_label)
        executor_layout.addWidget(self.parameters_combo)
        executor_layout.addWidget(self.stack)

        self.executor_group = QGroupBox(_("Executor parameters"))
        self.executor_group.setLayout(executor_layout)

        # --- Working directory ---
        self.wdir_group = QGroupBox(_("Working directory settings"))
        executor_layout.addWidget(self.wdir_group)

        wdir_layout = QVBoxLayout(self.wdir_group)

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
        browse_btn = create_toolbutton(
            self,
            triggered=self.select_directory,
            icon=ima.icon('DirOpenIcon'),
            tip=_("Select directory")
        )
        fixed_dir_layout.addWidget(browse_btn)
        wdir_layout.addLayout(fixed_dir_layout)

        # --- Store new custom configuration
        self.store_params_cb = QCheckBox(STORE_PARAMS)
        self.store_params_text = QLineEdit()
        store_params_layout = QHBoxLayout()
        store_params_layout.addWidget(self.store_params_cb)
        store_params_layout.addWidget(self.store_params_text)
        executor_layout.addLayout(store_params_layout)

        self.store_params_cb.toggled.connect(self.store_params_text.setEnabled)
        self.store_params_text.setPlaceholderText(_('My configuration name'))
        self.store_params_text.setEnabled(False)

        self.firstrun_cb = QCheckBox(ALWAYS_OPEN_FIRST_RUN % _("this dialog"))

        layout = self.add_widgets(combo_label, self.configuration_combo,
                                  executor_label, self.executor_combo,
                                  10, self.executor_group, self.firstrun_cb)

        self.executor_combo.currentIndexChanged.connect(
            self.display_executor_configuration)
        self.executor_combo.setModel(self.executors_model)

        self.configuration_combo.currentIndexChanged.connect(
            self.update_configuration_run_index)
        self.configuration_combo.setModel(self.run_conf_model)
        self.configuration_combo.setCurrentIndex(
            self.run_conf_model.get_initial_index())

        self.configuration_combo.setMaxVisibleItems(20)
        self.configuration_combo.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded)

        self.executor_combo.setMaxVisibleItems(20)
        self.executor_combo.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded)

        self.parameters_combo.currentIndexChanged.connect(
            self.update_parameter_set)
        self.parameters_combo.setModel(self.parameter_model)

        widget_dialog = QWidget()
        widget_dialog.setMinimumWidth(600)
        widget_dialog.setLayout(layout)
        scroll_layout = QVBoxLayout(self)
        scroll_layout.addWidget(widget_dialog)
        self.add_button_box(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.setWindowTitle(_("Run configuration per file"))
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    def select_directory(self):
        """Select directory"""
        basedir = str(self.wd_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd_or_home()
        directory = getexistingdirectory(self, _("Select directory"), basedir)
        if directory:
            self.wd_edit.setText(directory)
            self.dir = directory

    def update_configuration_run_index(self, index: int):
        self.executor_combo.setCurrentIndex(-1)
        self.run_conf_model.update_index(index)
        self.executor_combo.setCurrentIndex(
            self.executors_model.get_initial_index())

    def update_parameter_set(self, index: int):
        if index < 0:
            return

        if self.index_to_select is not None:
            index = self.index_to_select
            self.index_to_select = None
            self.parameters_combo.setCurrentIndex(index)

        action, params = self.parameter_model.get_executor_parameters(index)
        working_dir_params = params['working_dir']
        stored_parameters = params['executor_params']

        if action == RunParameterFlags.SetDefaults:
            stored_parameters = self.current_widget.get_default_configuration()
        self.current_widget.set_configuration(stored_parameters)

        source = working_dir_params['source']
        path = working_dir_params['path']

        if source == WorkingDirSource.ConfigurationDirectory:
            self.file_dir_radio.setChecked(True)
            self.cwd_radio.setChecked(False)
            self.fixed_dir_radio.setChecked(False)
            self.wd_edit.setText('')
        elif source == WorkingDirSource.CurrentDirectory:
            self.file_dir_radio.setChecked(False)
            self.cwd_radio.setChecked(True)
            self.fixed_dir_radio.setChecked(False)
            self.wd_edit.setText('')
        elif source == WorkingDirSource.CustomDirectory:
            self.file_dir_radio.setChecked(False)
            self.cwd_radio.setChecked(False)
            self.fixed_dir_radio.setChecked(True)
            self.wd_edit.setText(path)

    def display_executor_configuration(self, index: int):
        if index == -1:
            return

        # Clear the QStackWidget contents
        self.current_widget = None
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)

        exec_tuple = self.executors_model.get_selected_run_executor(index)
        executor_name, executor_info = exec_tuple
        enable_cwd = executor_info['requires_cwd']
        self.wdir_group.setEnabled(enable_cwd)

        ConfigWidget = (executor_info['configuration_widget'] or
                        RunExecutorConfigurationGroup)

        if executor_info['configuration_widget'] is None:
            self.executor_group.setVisible(False)
        else:
            self.executor_group.setVisible(True)

        metadata = self.run_conf_model.get_selected_metadata()
        context = metadata['context']
        input_extension = metadata['input_extension']
        uuid = metadata['uuid']

        self.current_widget = ConfigWidget(
            self, context, input_extension, metadata)
        self.stack.addWidget(self.current_widget)

        if uuid not in self.run_conf_model:
            return

        stored_param = self.run_conf_model.get_run_configuration_parameters(
            uuid, executor_name)

        self.parameter_model.set_parameters(stored_param['params'])

        selected_params = self.run_conf_model.get_last_used_execution_params(
            uuid, executor_name)
        all_selected_params = (
            self.run_conf_model.get_last_used_executor_parameters(uuid))
        re_open_dialog = all_selected_params['display_dialog']
        index = self.parameter_model.get_parameters_index(selected_params)

        if self.parameters_combo.count() == 0:
            self.index_to_select = index

        self.parameters_combo.setCurrentIndex(index)
        self.firstrun_cb.setChecked(re_open_dialog)
        self.adjustSize()

    def select_executor(self, executor_name: str):
        self.executor_combo.setCurrentIndex(
            self.executors_model.get_run_executor_index(executor_name))

    def reset_btn_clicked(self):
        self.parameters_combo.setCurrentIndex(-1)
        index = self.executor_combo.currentIndex()
        self.display_executor_configuration(index)
        self.store_params_text.setText('')
        self.store_params_cb.setChecked(False)

    def run_btn_clicked(self):
        self.status |= RunDialogStatus.Run
        self.accept()

    def accept(self) -> None:
        self.status |= RunDialogStatus.Save

        widget_conf = self.current_widget.get_configuration()

        path = None
        source = None
        if self.file_dir_radio.isChecked():
            source = WorkingDirSource.ConfigurationDirectory
        elif self.cwd_radio.isChecked():
            source = WorkingDirSource.CurrentDirectory
        else:
            source = WorkingDirSource.CustomDirectory
            path = self.wd_edit.text()

        cwd_opts = WorkingDirOpts(source=source, path=path)

        exec_params = RunExecutionParameters(
            working_dir=cwd_opts, executor_params=widget_conf)

        uuid, name = self.parameter_model.get_parameters_uuid_name(
            self.parameters_combo.currentIndex()
        )

        if self.store_params_cb.isChecked():
            uuid = str(uuid4())
            name = self.store_params_text.text()
            if name == '':
                date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                name = f'Configuration-{date_str}'

        ext_exec_params = ExtendedRunExecutionParameters(
            uuid=uuid, name=name, params=exec_params
        )
        executor_name, _ = self.executors_model.get_selected_run_executor(
            self.executor_combo.currentIndex()
        )
        metadata_info = self.run_conf_model.get_metadata(
            self.configuration_combo.currentIndex()
        )

        open_dialog = self.firstrun_cb.isChecked()

        self.saved_conf = (metadata_info['uuid'], executor_name,
                           ext_exec_params, open_dialog)
        return super().accept()

    def get_configuration(
        self
    ) -> Tuple[str, str, ExtendedRunExecutionParameters, bool]:

        return self.saved_conf
