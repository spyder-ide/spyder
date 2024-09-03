# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run container."""

# Standard library imports
import functools
import os.path as osp
from typing import Callable, List, Dict, Tuple, Set, Optional
from uuid import uuid4
from weakref import WeakSet, WeakValueDictionary

# Third-party imports
from qtpy.QtGui import QIcon
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QAction

# Local imports
from spyder.utils.sourcecode import camel_case_to_snake_case
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.translations import _
from spyder.plugins.run.api import (
    RunActions, StoredRunExecutorParameters, RunContext, RunExecutor,
    RunResultFormat, RunConfigurationProvider, RunResultViewer, OutputFormat,
    SupportedExecutionRunConfiguration, RunConfigurationMetadata,
    StoredRunConfigurationExecutor, ExtendedRunExecutionParameters,
    RunExecutionParameters, WorkingDirOpts, WorkingDirSource,
    SupportedExtensionContexts)
from spyder.plugins.run.models import (
    RunExecutorParameters, RunExecutorListModel, RunConfigurationListModel)
from spyder.plugins.run.widgets import RunDialog, RunDialogStatus


class RunContainer(PluginMainContainer):
    """Non-graphical container used to spawn dialogs and creating actions."""

    sig_run_action_created = Signal(str, bool, str)
    sig_open_preferences_requested = Signal()

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        self.current_working_dir: Optional[str] = None

        self.parameter_model = RunExecutorParameters(self)
        self.executor_model = RunExecutorListModel(self)
        self.metadata_model = RunConfigurationListModel(
            self, self.executor_model)

        self.run_metadata_provider: WeakValueDictionary[
            str, RunConfigurationProvider] = WeakValueDictionary()
        self.run_executors: WeakValueDictionary[
            str, RunExecutor] = WeakValueDictionary()
        self.viewers: WeakValueDictionary[
            str, RunResultViewer] = WeakValueDictionary()

        self.executor_use_count: Dict[str, int] = {}
        self.viewers_per_output: Dict[str, Set[str]] = {}

        self.run_action = self.create_action(
            RunActions.Run,
            _('&Run'),
            self.create_icon('run'),
            tip=_("Run file"),
            triggered=functools.partial(
                self.run_file, selected_uuid=None,
                selected_executor=None
            ),
            register_shortcut=True,
            shortcut_context='_',
            context=Qt.ApplicationShortcut
        )

        self.configure_action = self.create_action(
            RunActions.Configure,
            _('&Configuration per file'),
            self.create_icon('run_settings'),
            tip=_('Run settings'),
            triggered=functools.partial(
                self.edit_run_configurations,
                display_dialog=True,
                disable_run_btn=True,
                selected_executor=None
            ),
            register_shortcut=True,
            shortcut_context='_',
            context=Qt.ApplicationShortcut
        )

        self.create_action(
            RunActions.GlobalConfigurations,
            _("&Global configurations"),
            triggered=self.sig_open_preferences_requested
        )

        self.re_run_action = self.create_action(
            RunActions.ReRun,
            _('Re-run &last file'),
            self.create_icon('run_again'),
            tip=_('Run again last file'),
            triggered=self.re_run_file,
            register_shortcut=True,
            shortcut_context='_',
            context=Qt.ApplicationShortcut
        )

        self.re_run_action.setEnabled(False)

        self.current_input_provider: Optional[str] = None
        self.current_input_extension: Optional[str] = None

        self.context_actions: Dict[
            Tuple[str, str, str], Tuple[QAction, Callable]] = {}
        self.re_run_actions: Dict[
            Tuple[str, str, str], Tuple[QAction, Callable]] = {}
        self.run_executor_actions: Dict[
            Tuple[str, str], Tuple[QAction, Callable]] = {}

        self.supported_extension_contexts: Dict[str, Set[Tuple[str, str]]] = {}
        self.super_contexts: Set[str] = set({})

        self.last_executed_file: Optional[str] = None
        self.last_executed_per_context: Set[Tuple[str, str]] = set()

    def update_actions(self):
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    def gen_anonymous_execution_run(
        self,
        context: str,
        extra_action_name: Optional[str] = None,
        context_modificator: Optional[str] = None,
        re_run: bool = False,
        last_executor_name: Optional[str] = None
    ) -> Callable:

        def anonymous_execution_run():
            if self.currently_selected_configuration is None:
                return

            input_provider = self.run_metadata_provider[
                self.currently_selected_configuration]

            if context in self.super_contexts:
                run_conf = input_provider.get_run_configuration(
                    self.currently_selected_configuration)
            else:
                run_conf = input_provider.get_run_configuration_per_context(
                    context, extra_action_name, context_modificator,
                    re_run=re_run)

            if run_conf is None:
                return

            uuid = self.currently_selected_configuration
            super_metadata = self.metadata_model[uuid]
            extension = super_metadata['input_extension']

            path = super_metadata['path']
            dirname = osp.dirname(path)

            last_executor = last_executor_name
            if last_executor is None:
                last_executor = self.get_last_used_executor_parameters(uuid)
                last_executor = last_executor['executor']

            run_comb = (extension, context)
            if (last_executor is None or
                    not self.executor_model.executor_supports_configuration(
                        last_executor, run_comb)):
                last_executor = self.executor_model.get_default_executor(
                    run_comb)
            executor_metadata = self.executor_model[
                ((extension, context), last_executor)]
            ConfWidget = executor_metadata['configuration_widget']

            conf = {}
            if ConfWidget is not None:
                conf = ConfWidget.get_default_configuration()

            working_dir = WorkingDirOpts(
                source=WorkingDirSource.ConfigurationDirectory,
                path=dirname)

            exec_params = RunExecutionParameters(
                working_dir=working_dir, executor_params=conf)

            ext_exec_params = ExtendedRunExecutionParameters(
                uuid=None, name=None, params=exec_params)
            executor = self.run_executors[last_executor]
            executor.exec_run_configuration(run_conf, ext_exec_params)

            self.last_executed_per_context |= {(uuid, context)}

            if (
                (context, extra_action_name, context_modificator)
                in self.re_run_actions
            ):
                act, _ = self.re_run_actions[
                    (context, extra_action_name, context_modificator)]
                act.setEnabled(True)

        return anonymous_execution_run

    def run_file(self, selected_uuid=None, selected_executor=None):
        if not isinstance(selected_uuid, bool) and selected_uuid is not None:
            self.switch_focused_run_configuration(selected_uuid)

        self.edit_run_configurations(
            display_dialog=False,
            selected_executor=selected_executor)

    def edit_run_configurations(
        self,
        display_dialog=True,
        disable_run_btn=False,
        selected_executor=None
    ):
        self.dialog = RunDialog(
            self,
            self.metadata_model,
            self.executor_model,
            self.parameter_model,
            disable_run_btn=disable_run_btn
        )

        self.dialog.setup()
        self.dialog.finished.connect(self.process_run_dialog_result)
        self.dialog.sig_delete_config_requested.connect(
            self.delete_executor_configuration_parameters
        )

        if selected_executor is not None:
            self.dialog.select_executor(selected_executor)

        if display_dialog:
            self.dialog.open()
        else:
            self.dialog.run_btn_clicked()

    def process_run_dialog_result(self, result):
        status = self.dialog.status

        if status == RunDialogStatus.Close:
            return

        uuid, executor_name, ext_params = self.dialog.get_configuration()

        if (status & RunDialogStatus.Save) == RunDialogStatus.Save:
            exec_uuid = ext_params['uuid']

            # Default parameters should already be saved in our config system.
            # So, there is no need to save them again here.
            if exec_uuid is not None and not ext_params["default"]:

                info = self.metadata_model.get_metadata_context_extension(uuid)
                context, ext =  info
                context_name = context['name']
                context_id = getattr(RunContext, context_name)
                all_exec_params = self.get_executor_configuration_parameters(
                    executor_name,
                    ext,
                    context_id
                )
                exec_params = all_exec_params['params']
                exec_params[exec_uuid] = ext_params

                self.set_executor_configuration_parameters(
                    executor_name,
                    ext,
                    context_id,
                    all_exec_params,
                )

            last_used_conf = StoredRunConfigurationExecutor(
                executor=executor_name, selected=ext_params['uuid']
            )

            self.set_last_used_execution_params(uuid, last_used_conf)

        if (status & RunDialogStatus.Run) == RunDialogStatus.Run:
            provider = self.run_metadata_provider[uuid]
            executor = self.run_executors[executor_name]
            run_conf = provider.get_run_configuration(uuid)
            working_dir_opts = ext_params['params']['working_dir']
            working_dir_source = working_dir_opts['source']
            if working_dir_source == WorkingDirSource.ConfigurationDirectory:
                fname = run_conf['metadata']['path']
                dirname = osp.dirname(fname)
            elif working_dir_source == WorkingDirSource.CurrentDirectory:
                dirname = self.current_working_dir
            else:
                dirname = working_dir_opts['path']

            working_dir_opts['path'] = dirname

            self.last_executed_file = uuid
            self.re_run_action.setEnabled(True)

            executor.exec_run_configuration(run_conf, ext_params)

    def re_run_file(self):
        self.run_file(self.last_executed_file, selected_executor=None)
    
    @property
    def currently_selected_configuration(self):
        return self.metadata_model.get_current_run_configuration()

    def switch_focused_run_configuration(self, uuid: Optional[str]):
        uuid = uuid or None
        if uuid == self.currently_selected_configuration:
            return

        self.metadata_model.set_current_run_configuration(uuid)

        if uuid is not None:
            self.run_action.setEnabled(True)

            metadata = self.metadata_model[uuid]
            self.current_input_provider = metadata['source']
            self.current_input_extension = metadata['input_extension']

            input_provider = self.run_metadata_provider[uuid]
            input_provider.focus_run_configuration(uuid)
            self.set_actions_status()

            return

        self.run_action.setEnabled(False)
        
        for context, act, mod in self.context_actions:
            action, __ = self.context_actions[(context, act, mod)]
            action.setEnabled(False)

        for context, act, mod in self.re_run_actions:
            action, __ = self.re_run_actions[(context, act, mod)]
            action.setEnabled(False)

        for context_name, executor_name in self.run_executor_actions:
            action, __ = self.run_executor_actions[
                (context_name, executor_name)]
            action.setEnabled(False)

    def set_actions_status(self):
        if self.current_input_provider is None:
            return

        if self.currently_selected_configuration is None:
            return

        if (
            self.current_input_provider
            not in self.supported_extension_contexts
        ):
            return

        input_provider_ext_ctxs = self.supported_extension_contexts[
            self.current_input_provider]

        for context, act, mod in self.context_actions:
            key = (self.current_input_extension, context)
            status = key in self.executor_model
            status = status and key in input_provider_ext_ctxs
            action, __ = self.context_actions[(context, act, mod)]
            action.setEnabled(status)

        for context, act, mod in self.re_run_actions:
            key = (self.current_input_extension, context)
            status = key in self.executor_model
            status = status and key in input_provider_ext_ctxs

            last_run_exists = (
                (self.currently_selected_configuration,
                 context) in self.last_executed_per_context)

            action, __ = self.re_run_actions[(context, act, mod)]
            action.setEnabled(status and last_run_exists)

        for context_name, executor_name in self.run_executor_actions:
            status = self.executor_model.executor_supports_configuration(
                executor_name,
                (self.current_input_extension, context_name))
            key = (self.current_input_extension, context_name)
            status = status and key in input_provider_ext_ctxs

            action, __ = self.run_executor_actions[
                (context_name, executor_name)]
            action.setEnabled(status)

    def set_current_working_dir(self, path: str):
        self.current_working_dir = path

    def create_run_button(
        self,
        context_name: str,
        text: str,
        icon: Optional[QIcon] = None,
        tip: Optional[str] = None,
        shortcut_context: Optional[str] = None,
        register_shortcut: bool = False,
        extra_action_name: Optional[str] = None,
        context_modificator: Optional[str] = None,
        re_run: bool = False
    ) -> QAction:
        """
        Create a run or a "run and do something" button for a specific run
        context.

        Parameters
        ----------
        context_name: str
            The identifier of the run context.
        text: str
           Localized text for the action
        icon: Optional[QIcon]
            Icon for the action when used in menu or toolbar.
        tip: Optional[str]
            Tooltip to define for action on menu or toolbar.
        shortcut_context: Optional[str]
            Set the `str` context of the shortcut.
        register_shortcut: bool
            If True, main window will expose the shortcut in Preferences.
            The default value is `False`.
        extra_action_name: Optional[str]
            The name of the action to execute on the run input provider
            after requesting the run input.
        context_modificator: Optional[str]
            The name of the modification to apply to the action, e.g. run
            selection <up to line>.
        re_run: bool
            If True, then the button will act as a re-run button instead of
            a run one.

        Returns
        -------
        action: SpyderAction
            The corresponding action that was created.

        Notes
        -----
        1. The context passed as a parameter must be a subordinate of the
        context of the current focused run configuration that was
        registered via `register_run_configuration_metadata`. For instance,
        Cell can be used if and only if the file was registered.

        2. The button will be registered as `run <context>` or
        `run <context> <context_modificator> and <extra_action_name>` 
        on the action registry.

        3. The created button will operate over the last focused run input
        provider.

        4. If the requested button already exists, this method will not do
        anything, which implies that the first registered shortcut will be the
        one to be used. For the built-in run contexts (file, cell and
        selection), the editor will register their corresponding icons and
        shortcuts.
        """
        dict_actions = self.re_run_actions if re_run else self.context_actions

        if (
            (context_name, extra_action_name, context_modificator)
            in dict_actions
        ):
            action, __ = self.context_actions[
                (context_name, extra_action_name, context_modificator)]
            return action

        prefix = 're-' if re_run else ''
        action_name = f'{prefix}run {context_name}'
        if context_modificator is not None:
            action_name = f'{action_name} {context_modificator}'
        if extra_action_name is not None:
            action_name = f'{action_name} and {extra_action_name}'

        func = self.gen_anonymous_execution_run(
            context_name, extra_action_name, context_modificator,
            re_run=re_run, last_executor_name=None)

        action = self.create_action(
            action_name,
            text,
            icon,
            tip=tip,
            triggered=func,
            register_shortcut=register_shortcut,
            shortcut_context=shortcut_context,
            context=Qt.WidgetShortcut,
        )

        if re_run:
            self.re_run_actions[
                (context_name, extra_action_name, context_modificator)] = (
                action, func)
            action.setEnabled(False)
        else:
            self.context_actions[
                (context_name, extra_action_name, context_modificator)] = (
                action, func)

        self.sig_run_action_created.emit(action_name, register_shortcut,
                                         shortcut_context)
        return action

    def create_run_in_executor_button(
        self,
        context_name: str,
        executor_name: str,
        text: str,
        icon: Optional[QIcon] = None,
        tip: Optional[str] = None,
        shortcut_context: Optional[str] = None,
        register_shortcut: bool = False,
        shortcut_widget_context: int = Qt.WidgetShortcut
    ) -> QAction:
        """
        Create a "run <context> in <provider>" button for a given run context
        and executor.

        Parameters
        ----------
        context_name: str
            The identifier of the run context.
        executor_name: str
            The identifier of the run executor.
        text: str
           Localized text for the action
        icon: Optional[QIcon]
            Icon for the action when used in a menu or toolbar.
        tip: Optional[str]
            Tooltip to define for action on menu or toolbar.
        shortcut_context: Optional[str]
            Set the `str` context of the shortcut.
        register_shortcut: bool
            If True, main window will expose the shortcut in Preferences.
            The default value is `False`.

        Returns
        -------
        action: SpyderAction
            The corresponding action that was created.

        Notes
        -----
        1. The context passed as a parameter must be a subordinate of the
        context of the current focused run configuration that was
        registered via `register_run_configuration_metadata`. For instance,
        Cell can be used if and only if the file was registered.

        2. The button will be registered as `run <context> in <provider>` on
        the action registry.

        3. The created button will operate over the last focused run input
        provider.

        4. If the requested button already exists, this method will not do
        anything, which implies that the first registered shortcut will be the
        one to be used.
        """
        if (context_name, executor_name) in self.run_executor_actions:
            action, __ = self.run_executor_actions[
                (context_name, executor_name)]
            return action

        action_name = f'run {context_name} in {executor_name}'

        func = lambda: None
        if context_name in self.super_contexts:
            func = functools.partial(self.run_file,
                                     selected_executor=executor_name)
        else:
            func = self.gen_anonymous_execution_run(
                context_name, re_run=False,
                last_executor_name=executor_name)

        action = self.create_action(
            action_name,
            text,
            icon,
            tip=tip,
            triggered=func,
            register_shortcut=register_shortcut,
            shortcut_context=shortcut_context,
            context=shortcut_widget_context
        )

        self.run_executor_actions[(context_name, executor_name)] = (
            action, func)

        self.sig_run_action_created.emit(action_name, register_shortcut,
                                         shortcut_context)
        return action

    def register_run_configuration_provider(
        self,
        provider_name: str,
        supported_extensions_contexts: List[SupportedExtensionContexts]
    ):
        """
        Register the supported extensions and contexts that a
        `RunConfigurationProvider` supports.

        Parameters
        ----------
        provider_name: str
            The identifier of the :class:`RunConfigurationProvider` instance
            that is registering the set of supported contexts per extension.
        supported_extensions_contexts: List[SupportedExtensionContexts]
            A list containing the supported contexts per file extension
            supported.
        """
        provider_extensions_contexts = self.supported_extension_contexts.get(
            provider_name, set({}))

        for supported_extension_contexts in supported_extensions_contexts:
            for ext_context in supported_extension_contexts['contexts']:
                context = ext_context['context']
                is_super = ext_context['is_super']
                context_name = context['name']
                context_identifier = context.get('identifier', None)
                if context_identifier is None:
                    context_identifier = camel_case_to_snake_case(context_name)
                    context['identifier'] = context_identifier
                setattr(RunContext, context_name, context_identifier)
                ext_list = supported_extension_contexts['input_extension']
                if not isinstance(ext_list, list):
                    ext_list = [ext_list]
                for ext in ext_list:
                    provider_extensions_contexts |= {(ext, context_identifier)}
                if is_super:
                    self.super_contexts |= {context_identifier}

        self.supported_extension_contexts[
            provider_name] = provider_extensions_contexts

        self.set_actions_status()

    def deregister_run_configuration_provider(
        self,
        provider_name: str,
        unsupported_extensions_contexts: List[SupportedExtensionContexts]
    ):
        """
        Deregister the extensions and contexts that a
        `RunConfigurationProvider` no longer supports.

        Parameters
        ----------
        provider_name: str
            The identifier of the :class:`RunConfigurationProvider` instance
            that is deregistering the set of formerly supported contexts
            per extension.
        unsupported_extensions_contexts: List[SupportedExtensionContexts]
            A list containing the formerly supported contexts per
            file extension.
        """
        provider_extensions_contexts = self.supported_extension_contexts.get(
            provider_name, set({}))

        for unsupported_extension_contexts in unsupported_extensions_contexts:
            ext = unsupported_extension_contexts['input_extension']
            for ext_context in unsupported_extension_contexts['contexts']:
                context = ext_context['context']
                context_name = context['name']
                context_id = getattr(RunContext, context_name)
                provider_extensions_contexts -= {(ext, context_id)}

        if provider_extensions_contexts:
            self.supported_extension_contexts[
                provider_name] = provider_extensions_contexts
        else:
            self.supported_extension_contexts.pop(provider_name, set({}))

    def register_run_configuration_metadata(
        self,
        provider: RunConfigurationProvider,
        metadata: RunConfigurationMetadata
    ):
        """
        Register the metadata for a run configuration.

        Parameters
        ----------
        provider: RunConfigurationProvider
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunConfigurationProvider` interface and will register
            and own a run configuration.
        metadata: RunConfigurationMetadata
            The metadata for a run configuration that the provider is able to
            produce.
        """
        context = metadata['context']
        context_name = context['name']
        context_identifier = context.get('identifier', None)

        if context_identifier is None:
            context_identifier = camel_case_to_snake_case(context_name)
            context['identifier'] = context_identifier
        setattr(RunContext, context_name, context_identifier)

        run_id = metadata['uuid']
        self.run_metadata_provider[run_id] = provider
        self.metadata_model[run_id] = metadata

    def deregister_run_configuration_metadata(self, uuid: str):
        """
        Deregister a given run configuration by its unique identifier.

        Parameters
        ----------
        uuid: str
            Unique identifier for a run configuration metadata that will not
            longer exist. This id should have been registered using
            `register_run_configuration_metadata`.
        """
        self.metadata_model.pop(uuid)
        self.run_metadata_provider.pop(uuid)

        if uuid == self.last_executed_file:
            self.last_executed_file = None
            self.re_run_action.setEnabled(False)

        to_remove = set({})
        for (opened_uuid, context) in self.last_executed_per_context:
            if opened_uuid == uuid:
                to_remove |= {(opened_uuid, context)}

        self.last_executed_per_context -= to_remove

    def register_executor_configuration(
        self,
        executor: RunExecutor,
        configuration: List[SupportedExecutionRunConfiguration]
    ):
        """
        Register a :class:`RunExecutorProvider` instance to indicate its
        support for a given set of run configurations.

        Parameters
        ----------
        provider: RunExecutor
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunExecutor` interface and will register execution
            input type information.
        configuration: List[SupportedExecutionRunConfiguration]
            A list of input configurations that the provider is able to
            produce. Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        executor_id = executor.NAME
        executor_name = executor.get_name()
        self.run_executors[executor_id] = executor
        executor_count = self.executor_use_count.get(executor_id, 0)

        for config in configuration:
            context = config['context']
            context_name = context['name']
            context_id = context.get('identifier', None)
            if context_id is None:
                context_id = camel_case_to_snake_case(context_name)
            setattr(RunContext, context_name, context_id)

            output_formats = []
            for out in config['output_formats']:
                output_name = out['name']
                output_id = out.get('identifier', None)
                if not output_id:
                    output_id = camel_case_to_snake_case(output_name)
                setattr(RunResultFormat, output_name, output_id)
                updated_out = {'name': output_name, 'identifier': output_id}
                output_formats.append(updated_out)

            config['output_formats'] = output_formats
            ext_list = config['input_extension']
            if not isinstance(ext_list, list):
                ext_list = [ext_list]
            for ext in ext_list:
                self.executor_model.add_input_executor_configuration(
                    ext, context_id, executor_id, config)
                executor_count += 1

                # Save default configs to our config system so that they are
                # displayed in the Run confpage
                config_widget = config["configuration_widget"]
                default_conf = (
                    config_widget.get_default_configuration()
                    if config_widget
                    else {}
                )
                self._save_default_graphical_executor_configuration(
                    executor_id,
                    ext,
                    context_id,
                    default_conf
                )

        self.executor_use_count[executor_id] = executor_count
        self.executor_model.set_executor_name(executor_id, executor_name)
        self.set_actions_status()

    def deregister_executor_configuration(
        self,
        executor: RunExecutor,
        configuration: List[SupportedExecutionRunConfiguration]
    ):
        """
        Deregister a :class:`RunExecutor` instance from providing a set
        of run configurations that are no longer supported by it.

        Parameters
        ----------
        executor: RunExecutor
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunExecutor` interface and will deregister execution
            input type information.
        configuration: List[SupportedExecutionRunConfiguration]
            A list of input configurations that the executor wants to
            deregister. Each configuration specifies the input extension
            identifier as well as the available execution context for that
            type.
        """
        executor_id = executor.NAME

        for config in configuration:
            ext = config['input_extension']
            context = config['context']
            context_name = context['name']
            context_id = getattr(RunContext, context_name)
            self.executor_model.remove_input_executor_configuration(
                ext, context_id, executor_id)
            self.executor_use_count[executor_id] -= 1

        if self.executor_use_count[executor_id] <= 0:
            self.run_executors.pop(executor_id)

        self.set_actions_status()

    def register_viewer_configuration(
        self,
        viewer: RunResultViewer,
        formats: List[OutputFormat]
    ):
        """
        Register a :class:`RunResultViewer` instance to indicate its support
        for a given set of output run result formats.

        Parameters
        ----------
        provider: RunResultViewer
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunResultViewer` interface and will register
            supported output formats.
        formats: List[OutputFormat]
            A list of output formats that the viewer is able to display.
        """
        for out_format in formats:
            format_name = out_format['name']
            format_id = out_format.get('identifier', None)
            if format_id is None:
                format_id = camel_case_to_snake_case(format_name)
            setattr(RunResultFormat, format_name, format_id)

            viewers_set = self.viewers.get(format_id, WeakSet())
            viewers_set.add(viewer)
            self.viewers[format_id] = viewers_set

    def deregister_viewer_configuration(
        self,
        viewer: RunResultViewer,
        formats: List[OutputFormat]
    ):
        """
        Deregister a :class:`RunResultViewer` instance from supporting a set of
        output formats that are no longer supported by it.

        Parameters
        ----------
        provider: RunResultViewer
            A :class:`SpyderPluginV2` instance that implements the
            :class:`RunResultViewer` interface and will deregister
            output format support.
        formats: List[OutputFormat]
            A list of output formats that the viewer wants to deregister.
        """
        for out_format in formats:
            format_name = out_format['name']
            format_id = getattr(RunResultFormat, format_name)
            if format_id in self.viewers:
                viewer_set = self.viewers[format_id]
                viewer_set.discard(viewer)

    def get_executor_configuration_parameters(
        self,
        executor_name: str,
        extension: str,
        context_id: str
    ) -> StoredRunExecutorParameters:
        """
        Retrieve the stored parameters for a given executor `executor_name`
        using context `context_id` with file extension `extension`.

        Parameters
        ----------
        executor_name: str
            The identifier of the run executor.
        extension: str
            The file extension to register the configuration parameters for.
        context_id: str
            The context to register the configuration parameters for.

        Returns
        -------
        config: StoredRunExecutorParameters
            A dictionary containing the run executor parameters for the given
            run configuration.
        """

        all_execution_params: Dict[
            str,
            Dict[Tuple[str, str], StoredRunExecutorParameters]
        ] = self.get_conf('parameters', default={})

        executor_params = all_execution_params.get(executor_name, {})
        params = executor_params.get(
            (extension, context_id),
            StoredRunExecutorParameters(params={})
        )

        return params

    def set_executor_configuration_parameters(
        self,
        executor_name: str,
        extension: str,
        context_id: str,
        params: StoredRunExecutorParameters
    ):
        """
        Update and save the list of configuration parameters for a given
        executor on a given pair of context and file extension.

        Parameters
        ----------
        executor_name: str
            The identifier of the run executor.
        extension: str
            The file extension to register the configuration parameters for.
        context_id: str
            The context to register the configuration parameters for.
        params: StoredRunExecutorParameters
            A dictionary containing the run configuration parameters for the
            given executor.
        """
        all_execution_params: Dict[
            str,
            Dict[Tuple[str, str], StoredRunExecutorParameters]
        ] = self.get_conf('parameters', default={})

        executor_params = all_execution_params.get(executor_name, {})
        ext_ctx_params = executor_params.get((extension, context_id), {})

        if ext_ctx_params:
            # Update current parameters in case the user has already saved some
            # before.
            ext_ctx_params['params'].update(params['params'])
        else:
            # Create a new entry of executor parameters in case there isn't any
            executor_params[(extension, context_id)] = params

        all_execution_params[executor_name] = executor_params

        self.set_conf('parameters', all_execution_params)

    def delete_executor_configuration_parameters(
        self,
        executor_name: str,
        extension: str,
        context_id: str,
        uuid: str
    ):
        """
        Delete an executor parameter set from our config system.

        Parameters
        ----------
        executor_name: str
            The identifier of the run executor.
        extension: str
            The file extension of the configuration parameters to delete.
        context_id: str
            The context of the configuration parameters to delete.
        uuid: str
            The run configuration identifier.
        """
        all_execution_params: Dict[
            str,
            Dict[Tuple[str, str], StoredRunExecutorParameters]
        ] = self.get_conf('parameters', default={})

        executor_params = all_execution_params[executor_name]
        ext_ctx_params = executor_params[(extension, context_id)]['params']

        for params_id in ext_ctx_params:
            if params_id == uuid:
                # Prevent to remove default parameters
                if ext_ctx_params[params_id]["default"]:
                    return

                ext_ctx_params.pop(params_id, None)
                break

        executor_params[(extension, context_id)]['params'] = ext_ctx_params
        all_execution_params[executor_name] = executor_params

        self.set_conf('parameters', all_execution_params)

    def get_last_used_executor_parameters(
        self,
        uuid: str
    ) -> StoredRunConfigurationExecutor:
        """
        Retrieve the last used execution parameters for a given
        run configuration.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.

        Returns
        -------
        last_used_params: StoredRunConfigurationExecutor
            A dictionary containing the last used executor and parameters
            for the given run configuration.
        """
        mru_executors_uuids: Dict[
            str,
            StoredRunConfigurationExecutor
        ] = self.get_conf('last_used_parameters', default={})

        last_used_params = mru_executors_uuids.get(
            uuid,
            StoredRunConfigurationExecutor(
                executor=None,
                selected=None
            )
        )

        return last_used_params

    def get_last_used_execution_params(
        self,
        uuid: str,
        executor_name: str
    ) -> Optional[str]:
        """
        Retrieve the last used execution parameters for a given pair of run
        configuration and execution identifiers.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.
        executor_name: str
            The identifier of the run executor.

        Returns
        -------
        last_used_params: Optional[str]
            The identifier of the last used parameters for the given
            run configuration on the given executor. None if the executor has
            not executed the run configuration.
        """

        mru_executors_uuids: Dict[
            str,
            StoredRunConfigurationExecutor
        ] = self.get_conf('last_used_parameters', default={})

        default = StoredRunConfigurationExecutor(
            executor=executor_name,
            selected=None
        )
        params = mru_executors_uuids.get(uuid, default)

        last_used_params = None
        if params['executor'] == executor_name:
            last_used_params = params['selected']

        return last_used_params

    def set_last_used_execution_params(
        self,
        uuid: str,
        params: StoredRunConfigurationExecutor
    ):
        """
        Store the last used executor and parameters for a given run
        configuration.

        Parameters
        ----------
        uuid: str
            The run configuration identifier.
        params: StoredRunConfigurationExecutor
            Dictionary containing the last used executor and run parameters
            used.
        """
        mru_executors_uuids: Dict[
            str,
            StoredRunConfigurationExecutor
        ] = self.get_conf('last_used_parameters', default={})

        mru_executors_uuids[uuid] = params
        self.set_conf('last_used_parameters', mru_executors_uuids)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _save_default_graphical_executor_configuration(
        self,
        executor_name: str,
        extension: str,
        context_id: str,
        default_conf: dict,
    ):
        """
        Save a default executor configuration to our config system.

        Parameters
        ----------
        executor_name: str
            The identifier of the run executor.
        extension: str
            The file extension to register the configuration parameters for.
        context_id: str
            The context to register the configuration parameters for.
        default_conf: dict
            A dictionary containing the run configuration parameters for the
            given executor.
        """
        # Check if there's already a default parameter config to not do this
        # because it's not necessary.
        current_params = self.get_executor_configuration_parameters(
            executor_name,
            extension,
            context_id
        )

        for param in current_params["params"].values():
            if param["default"]:
                return

        # Id for this config
        uuid = str(uuid4())

        # Build config
        cwd_opts = WorkingDirOpts(
            source=WorkingDirSource.ConfigurationDirectory,
            path=None
        )

        exec_params = RunExecutionParameters(
            working_dir=cwd_opts, executor_params=default_conf
        )

        ext_exec_params = ExtendedRunExecutionParameters(
            uuid=uuid,
            name=_("Default"),
            params=exec_params,
            file_uuid=None,
            default=True,
        )

        store_params = StoredRunExecutorParameters(
            params={uuid: ext_exec_params}
        )

        # Save config
        self.set_executor_configuration_parameters(
            executor_name,
            extension,
            context_id,
            store_params,
        )
