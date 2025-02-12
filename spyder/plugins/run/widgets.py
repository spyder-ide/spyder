# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Run dialogs and widgets and data models."""

# Standard library imports
import os.path as osp
import textwrap
from typing import Optional, Tuple, List, Dict
from uuid import uuid4

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QLayout,
    QMessageBox,
    QRadioButton,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)
import qstylizer.style

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.translations import _
from spyder.api.widgets.comboboxes import SpyderComboBox
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.config.base import running_in_ci, running_under_pytest
from spyder.plugins.run.api import (
    ExtendedRunExecutionParameters,
    RunExecutorConfigurationGroup,
    RunExecutionParameters,
    SupportedExecutionRunConfiguration,
    WorkingDirOpts,
    WorkingDirSource,
)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import qapplication
from spyder.utils.stylesheet import AppStyle, MAC
from spyder.widgets.collapsible import CollapsibleWidget
from spyder.widgets.helperwidgets import TipWidget


# ---- Main constants
# -----------------------------------------------------------------------------
FILE_DIR = _("The directory of the file being executed")
CW_DIR = _("The current working directory")
FIXED_DIR = _("The following directory:")
EMPTY_NAME = _("Provide a name for this configuration")
REPEATED_NAME = _("Select a different name for this configuration")
SAME_PARAMETERS = _(
    "You are trying to save a configuration that is exactly the same as the "
    "current one"
)


class RunDialogStatus:
    Close = 0
    Save = 1
    Run = 2


# ---- Base class
# -----------------------------------------------------------------------------
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

        # Style that will be set by children
        self._css = qstylizer.style.StyleSheet()

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

        # Align this button to the text above it
        reset_deafults_btn.setStyleSheet("margin-left: 5px")

        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        self.layout().addWidget(self.bbox)

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


# ---- Dialogs
# -----------------------------------------------------------------------------
class ExecutionParametersDialog(BaseRunConfigDialog):
    """Run execution parameters edition dialog."""

    def __init__(
        self,
        parent,
        executor_name,
        executor_params: Dict[
            Tuple[str, str], SupportedExecutionRunConfiguration
        ],
        param_names: Dict[Tuple[str, str], List[str]],
        extensions: Optional[List[str]] = None,
        contexts: Optional[Dict[str, List[str]]] = None,
        current_params: Optional[ExtendedRunExecutionParameters] = None,
        extension: Optional[str] = None,
        context: Optional[str] = None,
        new_config: bool = False
    ):
        super().__init__(parent, True)

        self.executor_name = executor_name
        self.executor_params = executor_params
        self.param_names = param_names
        self.current_params = current_params
        self.extensions = extensions or []
        self.contexts = contexts or {}
        self.extension = extension
        self.context = context
        self.new_config = new_config

        self.parameters_name = None
        if current_params is not None:
            self.parameters_name = (
                _("Default")
                if current_params["default"]
                else current_params["name"]
            )

        self.current_widget = None
        self.status = RunDialogStatus.Close
        self.saved_conf = None

    # ---- Public methods
    # -------------------------------------------------------------------------
    def setup(self):
        # --- Configuration name
        if self.new_config:
            params_name_text = _("Save configuration as:")
        else:
            params_name_text = _("Configuration name:")

        params_name_label = QLabel(params_name_text)
        self.store_params_text = QLineEdit(self)
        self.store_params_text.setMinimumWidth(250)
        store_params_layout = QHBoxLayout()
        store_params_layout.addWidget(params_name_label)
        store_params_layout.addWidget(self.store_params_text)
        store_params_layout.addStretch(1)

        # This action needs to be added before setting an icon for it so that
        # it doesn't show up in the line edit (despite being set as not visible
        # below). That's probably a Qt bug.
        status_action = QAction(self)
        self.store_params_text.addAction(
            status_action, QLineEdit.TrailingPosition
        )
        self.store_params_text.status_action = status_action

        status_action.setIcon(ima.icon("error"))
        status_action.setVisible(False)

        # This is necessary to fix the style of the tooltip shown inside the
        # lineedit
        store_params_css = qstylizer.style.StyleSheet()
        store_params_css["QLineEdit QToolTip"].setValues(
            padding="1px 2px",
        )
        self.store_params_text.setStyleSheet(store_params_css.toString())

        # --- Extension and context widgets
        ext_combo_label = QLabel(_("File extension:"))
        context_combo_label = QLabel(_("Run context:"))

        self.extension_combo = SpyderComboBox(self)
        self.extension_combo.addItems(self.extensions)
        self.extension_combo.currentIndexChanged.connect(
            self.extension_changed)

        self.context_combo = SpyderComboBox(self)
        self.context_combo.currentIndexChanged.connect(self.context_changed)

        self.extension_combo.setMinimumWidth(150)
        self.context_combo.setMinimumWidth(150)

        ext_context_g_layout = QGridLayout()
        ext_context_g_layout.addWidget(ext_combo_label, 0, 0)
        ext_context_g_layout.addWidget(self.extension_combo, 0, 1)
        ext_context_g_layout.addWidget(context_combo_label, 1, 0)
        ext_context_g_layout.addWidget(self.context_combo, 1, 1)

        ext_context_layout = QHBoxLayout()
        ext_context_layout.addLayout(ext_context_g_layout)
        ext_context_layout.addStretch(1)

        # --- Runner settings
        self.stack = QStackedWidget(self)

        # --- Working directory settings
        self.wdir_group = QGroupBox(_("Working directory settings"))
        wdir_layout = QVBoxLayout(self.wdir_group)
        wdir_layout.setContentsMargins(
            3 * AppStyle.MarginSize,
            3 * AppStyle.MarginSize,
            3 * AppStyle.MarginSize,
            AppStyle.MarginSize if MAC else 0,
        )

        self.file_dir_radio = QRadioButton(FILE_DIR)
        wdir_layout.addWidget(self.file_dir_radio)

        self.cwd_radio = QRadioButton(CW_DIR)
        wdir_layout.addWidget(self.cwd_radio)

        self.fixed_dir_radio = QRadioButton(FIXED_DIR)
        self.wd_edit = QLineEdit(self)
        self.fixed_dir_radio.toggled.connect(self.wd_edit.setEnabled)
        self.wd_edit.setEnabled(False)
        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select directory"))
        browse_btn.clicked.connect(self.select_directory)
        browse_btn.setIconSize(
            QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
        )

        fixed_dir_layout = QHBoxLayout()
        fixed_dir_layout.addWidget(self.fixed_dir_radio)
        fixed_dir_layout.addWidget(self.wd_edit)
        fixed_dir_layout.addWidget(browse_btn)
        wdir_layout.addLayout(fixed_dir_layout)

        # --- Final layout
        layout = self.add_widgets(
            store_params_layout,
            4 * AppStyle.MarginSize,
            ext_context_layout,
            (3 if MAC else 4) * AppStyle.MarginSize,
            self.stack,
            self.wdir_group,
            (-2 if MAC else 1) * AppStyle.MarginSize,
        )
        layout.addStretch()
        layout.setContentsMargins(*((AppStyle.InnerContentPadding,) * 4))

        self.add_button_box(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # --- Settings
        self.setWindowTitle(
            _("New run configuration for: {}").format(self.executor_name)
        )
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

        extension_index = 0
        if self.extension is not None:
            extension_index = self.extensions.index(self.extension)
            self.extension_combo.setEnabled(False)

        self.extension_combo.setCurrentIndex(extension_index)

        # This is necessary because extension_changed is not triggered
        # automatically for this extension_index.
        if extension_index == 0:
            self.extension_changed(extension_index)

        if self.context is not None:
            self.context_combo.setEnabled(False)

        if self.parameters_name:
            self.store_params_text.setText(self.parameters_name)

            # Don't allow to change name for default or already saved params.
            if self.current_params["default"] or not self.new_config:
                self.store_params_text.setEnabled(False)

        # --- Stylesheet
        self.setStyleSheet(self._stylesheet)

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

    def context_changed(self, index: int, reset: bool = False):
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
            self.stack.setEnabled(False)
        else:
            self.stack.setEnabled(True)

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

        if self.current_params:
            params = self.current_params['params']
            working_dir_params = params['working_dir']
            exec_params = params

        params_set = (
            default_params
            if reset
            else (exec_params["executor_params"] or default_params)
        )

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

        if not self.stack.isEnabled() and not self.wdir_group.isEnabled():
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
        self.context_changed(index, reset=True)

    def run_btn_clicked(self):
        self.status |= RunDialogStatus.Run

    def ok_btn_clicked(self):
        self.status |= RunDialogStatus.Save

    def get_configuration(
            self
    ) -> Tuple[str, str, ExtendedRunExecutionParameters]:

        return self.saved_conf

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accept(self) -> None:
        self.status |= RunDialogStatus.Save
        widget_conf = self.current_widget.get_configuration()
        self.store_params_text.status_action.setVisible(False)

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

        if self.current_params:
            uuid = self.current_params['uuid']
        else:
            uuid = str(uuid4())

        # Validate name only for new configurations
        name = self.store_params_text.text()
        if self.new_config:
            if name == '':
                self.store_params_text.status_action.setVisible(True)
                self.store_params_text.status_action.setToolTip(
                    '\n'.join(textwrap.wrap(EMPTY_NAME, 50))
                )
                return
            else:
                extension = self.extension_combo.lineEdit().text()
                context = self.context_combo.lineEdit().text()
                current_names = self.param_names[(extension, context)]
                if name in current_names:
                    self.store_params_text.status_action.setVisible(True)
                    self.store_params_text.status_action.setToolTip(
                        '\n'.join(textwrap.wrap(REPEATED_NAME, 50))
                    )
                    return

        # Check if params are app default ones.
        # Fixes spyder-ide/spyder#22649
        if self.current_params is None:
            # The user is trying to create new params, so this is not a
            # default.
            is_default = False
        else:
            if self.current_params["default"]:
                # Default params
                is_default = True
            else:
                # User created params
                is_default = False

        ext_exec_params = ExtendedRunExecutionParameters(
            uuid=uuid,
            name=name,
            params=exec_params,
            file_uuid=None,
            default=is_default,
        )

        self.saved_conf = (self.selected_extension, self.selected_context,
                           ext_exec_params)

        super().accept()

    # ---- Private methods
    # -------------------------------------------------------------------------
    @property
    def _stylesheet(self):
        # This avoids the extra bottom margin added by the config dialog since
        # this widget is one of its children
        self._css.QGroupBox.setValues(
            marginBottom='0px',
        )

        return self._css.toString()


class RunDialog(BaseRunConfigDialog, SpyderFontsMixin):
    """Run dialog used to configure run executors."""

    sig_delete_config_requested = Signal(str, str, str, str)

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
        self._is_shown = False

    # ---- Public methods
    # -------------------------------------------------------------------------
    def setup(self):
        # --- Header
        self.header_label = QLabel(self)
        self.header_label.setObjectName("run-header-label")

        # --- File combobox
        # It's hidden by default to decrease the complexity of this dialog
        self.configuration_combo = SpyderComboBox(self)
        self.configuration_combo.hide()

        # --- Executor and parameters widgets
        executor_label = QLabel(_("Runner:"))
        self.executor_combo = SpyderComboBox(self)
        self.executor_combo.setMinimumWidth(250)
        executor_tip = TipWidget(
            _("Configure the selected runner for this file"),
            icon=ima.icon('question_tip'),
            hover_icon=ima.icon('question_tip_hover'),
            size=23,
            wrap_text=True
        )

        parameters_label = QLabel(_("Preset configuration:"))
        self.parameters_combo = SpyderComboBox(self)
        self.parameters_combo.setMinimumWidth(250)
        parameters_tip = TipWidget(
            _(
                "Select between global or local (i.e. for this file) "
                "configuration presets. You can set the latter below"
            ),
            icon=ima.icon('question_tip'),
            hover_icon=ima.icon('question_tip_hover'),
            size=23,
            wrap_text=True
        )

        executor_g_layout = QGridLayout()
        executor_g_layout.addWidget(executor_label, 0, 0)
        executor_g_layout.addWidget(self.executor_combo, 0, 1)
        executor_g_layout.addWidget(executor_tip, 0, 2)
        executor_g_layout.addWidget(parameters_label, 1, 0)
        executor_g_layout.addWidget(self.parameters_combo, 1, 1)
        executor_g_layout.addWidget(parameters_tip, 1, 2)

        executor_layout = QHBoxLayout()
        executor_layout.addLayout(executor_g_layout)
        executor_layout.addStretch()

        # --- Configuration properties
        config_props_group = QGroupBox(_("Configuration properties"))
        config_props_layout = QGridLayout(config_props_group)

        # Increase margin between title and line edit below so this looks good
        config_props_margins = config_props_layout.contentsMargins()
        config_props_margins.setTop(12)
        config_props_layout.setContentsMargins(config_props_margins)

        # Name to save custom configuration
        name_params_label = QLabel(_("Name:"))
        self.name_params_text = QLineEdit(self)
        self.name_params_text.setPlaceholderText(
            _("Set a name for this configuration")
        )
        name_params_tip = TipWidget(
            _(
                "You can set as many configuration presets as you want by "
                "providing different names. Each one will be saved after "
                "clicking the Ok button below"
            ),
            icon=ima.icon('question_tip'),
            hover_icon=ima.icon('question_tip_hover'),
            size=23,
            wrap_text=True
        )

        # This action needs to be added before setting an icon for it so that
        # it doesn't show up in the line edit (despite being set as not visible
        # below). That's probably a Qt bug.
        status_action = QAction(self)
        self.name_params_text.addAction(
            status_action, QLineEdit.TrailingPosition
        )
        self.name_params_text.status_action = status_action

        status_action.setIcon(ima.icon("error"))
        status_action.setVisible(False)

        config_props_layout.addWidget(name_params_label, 0, 0)
        config_props_layout.addWidget(self.name_params_text, 0, 1)
        config_props_layout.addWidget(name_params_tip, 0, 2)

        # --- Runner settings
        self.stack = QStackedWidget(self)

        # --- Working directory settings
        self.wdir_group = QGroupBox(_("Working directory settings"))
        wdir_layout = QVBoxLayout(self.wdir_group)

        self.file_dir_radio = QRadioButton(FILE_DIR)
        wdir_layout.addWidget(self.file_dir_radio)

        self.cwd_radio = QRadioButton(CW_DIR)
        wdir_layout.addWidget(self.cwd_radio)

        self.fixed_dir_radio = QRadioButton(FIXED_DIR)
        self.wd_edit = QLineEdit(self)
        self.fixed_dir_radio.toggled.connect(self.wd_edit.setEnabled)
        self.wd_edit.setEnabled(False)
        browse_btn = QPushButton(ima.icon('DirOpenIcon'), '', self)
        browse_btn.setToolTip(_("Select directory"))
        browse_btn.clicked.connect(self.select_directory)
        browse_btn.setIconSize(
            QSize(AppStyle.ConfigPageIconSize, AppStyle.ConfigPageIconSize)
        )

        fixed_dir_layout = QHBoxLayout()
        fixed_dir_layout.addWidget(self.fixed_dir_radio)
        fixed_dir_layout.addWidget(self.wd_edit)
        fixed_dir_layout.addWidget(browse_btn)
        wdir_layout.addLayout(fixed_dir_layout)

        # --- Group all customization widgets into a collapsible one
        custom_config = CollapsibleWidget(self, _("Custom configuration"))
        custom_config.addWidget(config_props_group)
        custom_config.addWidget(self.stack)
        custom_config.addWidget(self.wdir_group)

        # Fix bottom and left margins.
        custom_config.set_content_bottom_margin(0)
        custom_config.set_content_right_margin(AppStyle.MarginSize)

        # Center dialog after custom_config is expanded/collapsed
        custom_config._animation.finished.connect(self._center_dialog)

        # --- Final layout
        layout = self.add_widgets(
            self.header_label,
            self.configuration_combo,  # Hidden for simplicity
            executor_layout,
            custom_config,
            (-2 if MAC else 1) * AppStyle.MarginSize,
        )
        layout.setContentsMargins(
            AppStyle.InnerContentPadding,
            # This needs to be bigger to make the layout look better
            AppStyle.InnerContentPadding + AppStyle.MarginSize,
            # This makes the left and right padding be the same
            AppStyle.InnerContentPadding + 4,
            AppStyle.InnerContentPadding,
        )

        self.add_button_box(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.delete_button = QPushButton(_("Delete"))
        self.delete_button.clicked.connect(self.delete_btn_clicked)
        self.bbox.addButton(self.delete_button, QDialogButtonBox.ActionRole)

        # --- Settings
        self.executor_combo.currentIndexChanged.connect(
            self.display_executor_configuration)
        self.executor_combo.setModel(self.executors_model)

        # This signal needs to be connected after
        # executor_combo.currentIndexChanged and before
        # configuration_combo.currentIndexChanged for parameters_combo to be
        # updated as expected when opening the dialog.
        self.parameters_combo.currentIndexChanged.connect(
            self.update_parameter_set
        )
        self.parameters_combo.setModel(self.parameter_model)

        self.configuration_combo.currentIndexChanged.connect(
            self.update_configuration_run_index)
        self.configuration_combo.setModel(self.run_conf_model)
        self.configuration_combo.setCurrentIndex(
            self.run_conf_model.get_initial_index())
        self.configuration_combo.setMaxVisibleItems(1)

        self.executor_combo.setMaxVisibleItems(20)
        self.executor_combo.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded)

        self.setWindowTitle(_("Run configuration per file"))
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

        self.setStyleSheet(self._stylesheet)

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
            self.executors_model.get_initial_index()
        )

    def update_parameter_set(self, index: int):
        if index < 0:
            return

        # Get parameters
        stored_params = self.parameter_model.get_parameters(index)
        global_params = stored_params["file_uuid"] is None

        # Set parameters name
        if global_params:
            # We set this name for global params so users don't have to think
            # about selecting one when customizing them
            custom_name = self._get_auto_custom_name(stored_params["name"])
            self.name_params_text.setText(custom_name)
        else:
            # We show the actual name for file params
            self.name_params_text.setText(stored_params["name"])

        # Disable delete button for global configs
        if global_params:
            self.delete_button.setEnabled(False)
        else:
            self.delete_button.setEnabled(True)

        # Set parameters in their corresponding graphical elements
        params = stored_params["params"]
        working_dir_params = params['working_dir']
        exec_params = params['executor_params']
        self.current_widget.set_configuration(exec_params)

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
            self.stack.setVisible(False)
        else:
            self.stack.setVisible(True)

        metadata = self.run_conf_model.get_selected_metadata()
        context = metadata['context']
        input_extension = metadata['input_extension']
        uuid = metadata['uuid']

        self.current_widget = ConfigWidget(
            self, context, input_extension, metadata)
        self.stack.addWidget(self.current_widget)

        if uuid not in self.run_conf_model:
            return

        stored_params = self.run_conf_model.get_run_configuration_parameters(
            uuid, executor_name)['params']

        # Only show global parameters (i.e. those with file_uuid = None) or
        # those that correspond to the current file.
        stored_params = {
            k: v for (k, v) in stored_params.items()
            if v.get("file_uuid") in [None, uuid]
        }

        self.parameter_model.set_parameters(stored_params)
        selected_params = self.run_conf_model.get_last_used_execution_params(
            uuid, executor_name)
        params_index = self.parameter_model.get_parameters_index_by_uuid(
            selected_params
        )

        self.parameters_combo.setCurrentIndex(params_index)
        self.adjustSize()

    def select_executor(self, executor_name: str):
        self.executor_combo.setCurrentIndex(
            self.executors_model.get_run_executor_index(executor_name))

    def reset_btn_clicked(self):
        self.parameters_combo.setCurrentIndex(0)

    def run_btn_clicked(self):
        self.status |= RunDialogStatus.Run
        self.accept()

    def delete_btn_clicked(self):
        answer = QMessageBox.question(
            self,
            _("Delete"),
            _("Do you want to delete the current configuration?"),
        )

        if answer == QMessageBox.Yes:
            # Get executor name
            executor_name, __ = self.executors_model.get_selected_run_executor(
                self.executor_combo.currentIndex()
            )

            # Get extension and context_id
            metadata = self.run_conf_model.get_selected_metadata()
            extension = metadata["input_extension"]
            context_id = metadata["context"]["identifier"]

            # Get index associated with config
            idx = self.parameters_combo.currentIndex()

            # Get config uuid
            uuid, __ = self.parameter_model.get_parameters_uuid_name(idx)

            self.sig_delete_config_requested.emit(
                executor_name, extension, context_id, uuid
            )

            # Close dialog to not have to deal with the difficult case of
            # updating its contents after this config is deleted
            self.reject()

    def get_configuration(
        self
    ) -> Tuple[str, str, ExtendedRunExecutionParameters, bool]:

        return self.saved_conf

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accept(self) -> None:
        self.status |= RunDialogStatus.Save

        # Configuration to save/execute
        widget_conf = self.current_widget.get_configuration()

        # Hide status action in case users fix the problem reported through it
        # on a successive try
        self.name_params_text.status_action.setVisible(False)

        # Get index of current params
        current_index = self.parameters_combo.currentIndex()
        if running_in_ci() and current_index == -1:
            # This error seems to happen only on CIs
            self.status = RunDialogStatus.Close
            return

        # Detect if the current params are global
        params = self.parameter_model.get_parameters(current_index)
        global_params = params["file_uuid"] is None

        if global_params:
            custom_name = self._get_auto_custom_name(params["name"])
        else:
            custom_name = ""

        # Working directory params
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

        # Execution params
        exec_params = RunExecutionParameters(
            working_dir=cwd_opts, executor_params=widget_conf
        )

        # Different validations for the params name
        params_name = self.name_params_text.text()
        if self.isVisible():
            allow_to_close = True

            if not params_name:
                # Don't allow to save params without a name
                self.name_params_text.status_action.setVisible(True)
                self.name_params_text.status_action.setToolTip(
                    '\n'.join(textwrap.wrap(EMPTY_NAME, 50))
                )
                allow_to_close = False
            elif global_params and params_name == custom_name:
                # We don't need to perform a validation in this case because we
                # set the params name on behalf of users
                pass
            elif params_name != self.parameters_combo.lineEdit().text():
                if params_name in self.parameter_model.get_parameter_names():
                    # Don't allow to save params with the same name of an
                    # existing one because it doesn't make sense.
                    allow_to_close = False
                    self.name_params_text.status_action.setVisible(True)
                    self.name_params_text.status_action.setToolTip(
                        '\n'.join(textwrap.wrap(REPEATED_NAME, 50))
                    )
                elif params["params"] == exec_params:
                    # Don't allow to save params that are exactly the same as
                    # the current ones.
                    allow_to_close = False
                    self.name_params_text.status_action.setVisible(True)
                    self.name_params_text.status_action.setToolTip(
                       '\n'.join(textwrap.wrap(SAME_PARAMETERS, 50))
                    )

            if not allow_to_close:
                # With this the dialog can be closed when clicking the Cancel
                # button
                self.status = RunDialogStatus.Close
                return

        # Get index associated with config
        if params["params"] == exec_params:
            # This avoids saving an unnecessary custom config when the current
            # parameters haven't been modified with respect to the selected
            # config
            idx = current_index
        else:
            idx = self.parameter_model.get_parameters_index_by_name(
                params_name
            )

        # Get uuid and name from index
        if idx == -1:
            # This means that there are no saved parameters for params_name, so
            # we need to generate a new uuid for them.
            uuid = str(uuid4())
            name = params_name
        else:
            # Retrieve uuid and name from our config system
            uuid, name = self.parameter_model.get_parameters_uuid_name(idx)

        # Build configuration to be saved or executed
        metadata_info = self.run_conf_model.get_metadata(
            self.configuration_combo.currentIndex()
        )

        ext_exec_params = ExtendedRunExecutionParameters(
            uuid=uuid,
            name=name,
            params=exec_params,
            file_uuid=None
            if (global_params and idx >= 0)
            else metadata_info["uuid"],
            default=True
            if (global_params and params["default"] and idx >= 0)
            else False,
        )

        executor_name, __ = self.executors_model.get_selected_run_executor(
            self.executor_combo.currentIndex()
        )

        self.saved_conf = (
            metadata_info["uuid"],
            executor_name,
            ext_exec_params,
        )

        return super().accept()

    def showEvent(self, event):
        """Adjustments when the widget is shown."""
        if not self._is_shown:
            # Set file name as the header
            fname = self.configuration_combo.currentText()
            header_font = (
                self.get_font(SpyderFontType.Interface, font_size_delta=1)
            )

            # Elide fname in case fname is too long
            fm = QFontMetrics(header_font)
            text = fm.elidedText(
                fname, Qt.ElideLeft, self.header_label.width()
            )

            self.header_label.setFont(header_font)
            self.header_label.setAlignment(Qt.AlignCenter)
            self.header_label.setText(text)
            if text != fname:
                self.header_label.setToolTip(fname)

            self._is_shown = True

        super().showEvent(event)

    # ---- Private methods
    # -------------------------------------------------------------------------
    @property
    def _stylesheet(self):
        # --- Style for the header
        self._css["QLabel#run-header-label"].setValues(
            # Add good enough margin with the widgets below it.
            marginBottom=f"{3 * AppStyle.MarginSize}px",
            # This is necessary to align the label to the widgets below it.
            marginLeft="4px",
        )

        # --- Style for the collapsible
        self._css["CollapsibleWidget"].setValues(
            # Separate it from the widgets above it
            marginTop=f"{3 * AppStyle.MarginSize}px"
        )

        return self._css.toString()

    def _center_dialog(self):
        """
        Center dialog relative to the main window after collapsing/expanding
        the custom configuration widget.
        """
        # This doesn't work in our tests because the main window is usually
        # not available in them.
        if running_under_pytest():
            return

        qapp = qapplication()
        main_window_pos = qapp.get_mainwindow_position()
        main_window_height = qapp.get_mainwindow_height()

        # We only center the dialog vertically because there's no need to
        # do it horizontally.
        x = self.x()
        y = main_window_pos.y() + ((main_window_height - self.height()) // 2)

        self.move(x, y)

    def _get_auto_custom_name(self, global_params_name: str) -> str:
        """
        Get an auto-generated custom name given the a global parameters one.
        """
        n_custom = self.parameter_model.get_number_of_custom_params(
            global_params_name
        )

        return (
            global_params_name
            + " ("
            + _("custom")
            + (")" if n_custom == 0 else f" {n_custom})")
        )
