# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Run API tests."""

# Standard library imports
import copy
from datetime import datetime
from itertools import chain, repeat
import logging
from types import MethodType
from typing import Dict, Tuple, Optional, List
from uuid import uuid4
from unittest.mock import MagicMock

# Third-part imports
import pytest
from qtpy.QtCore import Signal, Qt
from qtpy.QtWidgets import (
    QAction, QWidget, QCheckBox, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel)

# Local imports
from spyder.plugins.run.api import (
    RunExecutor, RunConfigurationProvider, RunConfigurationMetadata, Context,
    RunConfiguration, SupportedExtensionContexts,
    RunExecutorConfigurationGroup, ExtendedRunExecutionParameters,
    PossibleRunResult, RunContext, ExtendedContext, RunActions, run_execute,
    WorkingDirSource)
from spyder.plugins.run.plugin import Run


logger = logging.getLogger(__name__)


class MockedMainWindow(QWidget, MagicMock):
    def get_plugin(self, name, error=True):
        return MagicMock()


class ExampleConfigurationProvider(RunConfigurationProvider):
    sig_uuid_focus_requested = Signal(str)

    def __init__(self, parent, info, provider_name) -> None:
        super().__init__(parent)

        # self.executor_configuration = []
        self.current_uuid = None
        self.provider_name = provider_name
        self.run_configurations: Dict[str, RunConfigurationMetadata] = {}
        self.configuration_uuids: Dict[Tuple[str, str], str] = {}
        self.supported_extensions: List[SupportedExtensionContexts] = []
        self.actions: Dict[str, QAction] = {}

        for ext, context, reg, create_btn in info:
            ctx = Context(name=context)
            ext_ctx = ExtendedContext(context=ctx, is_super=reg)

            self.supported_extensions.append(
                SupportedExtensionContexts(
                    input_extension=ext, contexts=[ext_ctx]))

            if reg:
                uuid = str(uuid4())
                metadata = RunConfigurationMetadata(
                    name=f'{ext}_{context.lower()}_{provider_name}_example',
                    source=provider_name,
                    path=f'test-example-{context}.{ext}',
                    timestamp=datetime.now(), uuid=uuid,
                    context=ctx,
                    input_extension=ext)

                self.run_configurations[uuid] = metadata
                self.configuration_uuids[(ext, context)] = uuid

            if create_btn:
                self.actions[context] = None

    def on_run_available(self, run: Run):
        self.sig_uuid_focus_requested.connect(
            run.switch_focused_run_configuration)

        run.register_run_configuration_provider(
            self.provider_name, self.supported_extensions)

        for uuid in self.run_configurations:
            metadata = self.run_configurations[uuid]
            run.register_run_configuration_metadata(self, metadata)

        for context_name in list(self.actions):
            act = run.create_run_button(
                getattr(RunContext, context_name),
                f'Run {context_name}',
                icon=None,
                tip=None,
                shortcut_context=None,
                register_shortcut=False,
                add_to_toolbar=False,
                add_to_menu=False
            )

            self.actions[context_name] = act

    def on_run_teardown(self, run):
        run.deregister_run_configuration_provider(
            self.provider_name, self.supported_extensions)

        for uuid in self.run_configurations:
            # metadata = self.run_configurations[uuid]
            run.deregister_run_configuration_metadata(uuid)

        for context_name in list(self.actions):
            run.destroy_run_button(getattr(RunContext, context_name))
            self.actions.pop(context_name)

    def get_run_configuration(self, uuid: str) -> RunConfiguration:
        metadata = self.run_configurations[uuid]
        name = metadata['name']
        source = metadata['source']
        path = metadata['path']
        context = metadata['context']['name']
        extension = metadata['input_extension']
        run_input = {
            'contents': (f'File: {name} | Location: {path} | Source: {source} '
                         f'| Context: {context} | Ext: {extension}')
        }

        return RunConfiguration(run_input=run_input, metadata=metadata)

    def get_run_configuration_per_context(
        self,
        context: str,
        action_name: Optional[str] = None,
        context_modificator: Optional[str] = None,
        re_run: bool = False
    ) -> Optional[RunConfiguration]:

        metadata = copy.deepcopy(self.run_configurations[self.current_uuid])
        inverse_run_ctx = {RunContext[k]: k for k in RunContext}
        metadata['context'] = Context(name=inverse_run_ctx[context],
                                      identifier=context)

        name = metadata['name']
        source = metadata['source']
        path = metadata['path']
        context = metadata['context']['name']
        extension = metadata['input_extension']
        run_input = {
            'contents': (f'File: {name} | Location: {path} | Source: {source} '
                         f'| Context: {context} | Ext: {extension} '
                         f'| Action: {action_name} | Re-run: {re_run}'),
            'action': action_name,
            're_run': re_run
        }

        return RunConfiguration(run_input=run_input, metadata=metadata)

    def switch_focus(self, ext: str, context: str):
        uuid = None
        if (ext, context) in self.configuration_uuids:
            uuid = self.configuration_uuids[(ext, context)]
        self.current_uuid = uuid
        self.sig_uuid_focus_requested.emit(uuid)

    def focus_run_configuration(self, uuid: str):
        metadata = self.run_configurations[uuid]
        context = metadata['context']['name']
        extension = metadata['input_extension']
        self.switch_focus(extension, context)


class GenExampleRunExecutorConf(RunExecutorConfigurationGroup):

    def __init__(self, parent: QWidget, context: Context, input_extension: str,
                 input_metadata: RunConfigurationMetadata):
        super().__init__(parent, context, input_extension, input_metadata)
        default_conf = self.get_default_configuration()
        self.widgets = {}

        layout = QVBoxLayout()
        for key_name in default_conf:
            default_value = default_conf[key_name]
            if isinstance(default_value, bool):
                widget = QCheckBox(key_name)
                layout.addWidget(widget)
            elif isinstance(default_value, str):
                temp_layout = QHBoxLayout()
                label = QLabel(key_name)
                temp_layout.addWidget(label)
                widget = QLineEdit()
                temp_layout.addWidget(widget)
                layout.addLayout(temp_layout)
            self.widgets[key_name] = widget

        self.setLayout(layout)

    def get_configuration(self) -> dict:
        conf = {}
        for key_name in self.widgets:
            widget = self.widgets[key_name]
            if isinstance(widget, QCheckBox):
                conf[key_name] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                conf[key_name] = widget.text()
        return conf

    def set_configuration(self, config: dict):
        for key_name in config:
            value = config[key_name]
            widget = self.widgets[key_name]
            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(value)


class MetaExampleRunExecutorConf(type(GenExampleRunExecutorConf)):

    def __new__(cls, clsname, bases, attrs):
        default_args = attrs.pop('default_args_meta')

        def get_default_configuration() -> dict:
            return default_args

        return super(MetaExampleRunExecutorConf, cls).__new__(
            cls, clsname, bases, {
                **attrs,
                'get_default_configuration': staticmethod(
                    get_default_configuration)
            }
        )


def ExampleRunExecutorConfFactory(default_args_dict: dict):

    class WrappedExampleRunExecutorConf(
            GenExampleRunExecutorConf, metaclass=MetaExampleRunExecutorConf):
        default_args_meta = default_args_dict

    return WrappedExampleRunExecutorConf


def gen_executor_handler(executor_name, handler_name, ext=None, context=None):

    @run_execute(extension=ext, context=context)
    def executor_handler(
            self, input: RunConfiguration,
            conf: ExtendedRunExecutionParameters) -> List[PossibleRunResult]:
        self.sig_run_invocation.emit(
            (executor_name, handler_name, input, conf))

    return executor_handler


class ExampleRunExecutorWrapper(RunExecutor):

    sig_run_invocation = Signal(tuple)

    def __init__(self, parent, info, executor_name):
        self.executor_configuration = []
        self.handlers = {}
        self.actions = {}
        self.executor_name = executor_name
        self.handlers['all'] = self.bind_execution_method('all')

        for ext, context, prio, default_conf, req_cwd, handler, btn in info:
            ConfWidget = ExampleRunExecutorConfFactory(default_conf)
            context_id = RunContext[context]
            self.executor_configuration.append({
                'input_extension': ext,
                'context': {
                    'name': context
                },
                'output_formats': [],
                'configuration_widget': ConfWidget,
                'requires_cwd': req_cwd,
                'priority': prio
            })

            if handler == 'context':
                self.handlers[context] = self.bind_execution_method(
                    f'context_{context_id}', context=context_id)
            elif handler == 'ext':
                self.handlers[ext] = self.bind_execution_method(
                    f'ext_{ext}', ext=ext)
            elif handler == 'both':
                self.handlers[(ext, context_id)] = self.bind_execution_method(
                    f'{ext}_{context_id}', ext=ext, context=context_id)

            if btn:
                self.actions[context_id] = None

        super().__init__(parent)

    def bind_execution_method(self, handler_name, ext=None, context=None):
        func = gen_executor_handler(
            self.executor_name, handler_name, ext, context)
        meth = MethodType(func, self)
        setattr(self, f'exec_{handler_name}', meth)
        return meth

    def on_run_available(self, run):
        run.register_executor_configuration(self, self.executor_configuration)
        for context_id in list(self.actions):
            act = run.create_run_in_executor_button(
                context_id,
                self.NAME,
                text=f'Run {context_id} in {self.NAME}',
                tip=None,
                icon=None,
                shortcut_context=None,
                register_shortcut=False,
                add_to_menu=False
            )
            self.actions[context_id] = act

    def on_run_teardown(self, run):
        run.deregister_executor_configuration(self, self.executor_configuration)
        for context_id in list(self.actions):
            run.destroy_run_in_executor_button(context_id, self.NAME)
            self.actions.pop(context_id)


class MetaExampleRunExecutor(type(ExampleRunExecutorWrapper)):

    def __new__(cls, clsname, bases, attrs):
        executor_name = attrs.pop('executor_name_meta')

        def get_name():
            return executor_name

        return super(MetaExampleRunExecutor, cls).__new__(
            cls, clsname, bases, {
                **attrs,
                'get_name': staticmethod(get_name),
                'NAME': executor_name
            }
        )


def ExampleRunExecutorFactory(parent, info, executor_name):

    class ExampleRunExecutor(
            ExampleRunExecutorWrapper, metaclass=MetaExampleRunExecutor):
        executor_name_meta = executor_name

    return ExampleRunExecutor(parent, info, executor_name)


@pytest.fixture
def run_mock(qtbot, tmpdir):
    temp_dir = str(tmpdir.mkdir('run'))
    mock_main_window = MockedMainWindow()
    run = Run(mock_main_window, None)
    run.on_initialize()
    run.switch_working_dir(temp_dir)
    return run, mock_main_window, temp_dir


def test_run_plugin(qtbot, run_mock):
    run, main_window, temp_cwd = run_mock

    # Create mock run configuration providers
    provider_1_conf = [
        ('ext1', 'RegisteredContext', True, False),
        ('ext1', 'SubordinateContext1', False, True),
        ('ext1', 'UnusedContext', False, True),
        ('ext2', 'AnotherSuperContext', True, False),
        ('ext3', 'RegisteredContext', True, False)
    ]

    provider_2_conf = [
        ('ext1', 'RegisteredContext', True, False),
        ('ext1', 'SubordinateContext1', False, True),
        ('ext1', 'SubordinateContext2', False, True),
        ('ext3', 'AnotherSuperContext', True, False)
    ]

    exec_provider_1 = ExampleConfigurationProvider(
        main_window, provider_1_conf, 'conf_prov_1')

    exec_provider_2 = ExampleConfigurationProvider(
        main_window, provider_2_conf, 'conf_prov_2')

    # Register providers with the Run plugin
    exec_provider_1.on_run_available(run)
    exec_provider_2.on_run_available(run)

    # Assert that the actions for 'SubordinateContext1' are the same for both
    # providers.
    act1 = exec_provider_1.actions['SubordinateContext1']
    act2 = exec_provider_2.actions['SubordinateContext1']
    assert act1 == act2

    # Create mock run executors
    executor_1_conf = [
        (
            'ext1', 'RegisteredContext', 0, {
                'opt1': True,
                'opt2': '',
                'opt3': False
            }, True, 'both', True
        ),
        (
            'ext1', 'SubordinateContext1', 1, {
                'arg1': '',
                'arg2': False,
                'arg3': False
            }, False, 'ext', True
        ),
        (
            'ext2', 'AnotherSuperContext', 0, {
                'only_opt': '',
            }, True, 'context', False
        ),
        (
            'ext3', 'AnotherSuperContext', 0, {
                'name_1': False,
                'name_2': True
            }, False, 'context', False
        ),
    ]

    executor_2_conf = [
        (
            'ext1', 'RegisteredContext', 1, {
                'ex2_opt1': True,
                'ex2_opt2': False,
                'ex2_opt3': False,

            }, True, 'ext', True
        ),
        (
            'ext1', 'SubordinateContext1', 0, {
                'arg1': '',
                'arg2': False,
                'arg3': False
            }, True, 'ext', True
        ),
        (
            'ext1', 'SubordinateContext2', 0, {
                'opt1': True,
                'opt2': False,
                'opt3': False
            }, True, 'context', True
        ),
        (
            'ext3', 'RegisteredContext', 0, {
                'name_1': False,
                'name_2': True
            }, False, 'all', False
        ),
    ]

    executor_1 = ExampleRunExecutorFactory(
        main_window, executor_1_conf, 'executor_1')
    executor_2 = ExampleRunExecutorFactory(
        main_window, executor_2_conf, 'executor_2')

    # Register run executors on the Run plugin
    executor_1.on_run_available(run)
    executor_2.on_run_available(run)

    # Focus on the first run configuration for the first configuration provider
    exec_provider_1.switch_focus('ext1', 'RegisteredContext')

    # Assert that both provider and run are in sync
    container = run.get_container()
    run_uuid = container.currently_selected_configuration
    assert run_uuid == exec_provider_1.current_uuid

    # Assert that run-specific context actions are available or disabled
    act = exec_provider_1.actions['SubordinateContext1']
    assert act.isEnabled()

    act = exec_provider_1.actions['UnusedContext']
    assert not act.isEnabled()

    act = exec_provider_2.actions['SubordinateContext2']
    assert not act.isEnabled()

    # Spawn the configuration dialog
    run_act = run.get_action(RunActions.Run)
    run_act.trigger()

    expected_configurations = []
    total_prov_1_conf = zip(
        repeat(exec_provider_1.provider_name, len(provider_1_conf)),
        provider_1_conf)
    total_prov_2_conf = zip(
        repeat(exec_provider_2.provider_name, len(provider_2_conf)),
        provider_2_conf)
    for provider_name, (ext, context, reg, _) in chain(
            total_prov_1_conf, total_prov_2_conf):
        if reg:
            expected_configurations.append(
                (ext, context,
                 f'{ext}_{context.lower()}_{provider_name}_example'))

    executors_per_conf = {}
    executor_1_conf_id = zip(repeat(executor_1.NAME, len(executor_1_conf)),
                             executor_1_conf)
    executor_2_conf_id = zip(repeat(executor_2.NAME, len(executor_2_conf)),
                             executor_2_conf)
    executor_conf_iter = chain(executor_1_conf_id, executor_2_conf_id)
    for (exec_name, (ext, context, prio,
                     default_conf, req_cwd, handler, _)) in executor_conf_iter:
        conf_executors = executors_per_conf.get((ext, context), [])
        conf_executors.insert(
            prio, (exec_name, default_conf, req_cwd, handler))
        executors_per_conf[(ext, context)] = conf_executors

    dialog = container.dialog
    with qtbot.waitSignal(dialog.finished, timeout=200000):
        conf_combo = dialog.configuration_combo
        exec_combo = dialog.executor_combo
        wdir_group = dialog.wdir_group

        # Ensure that there are 5 registered run configurations
        assert conf_combo.count() == 5

        # Ensure that the combobox contain all available configurations
        for i, (_, _, label) in enumerate(expected_configurations):
            combo_label = conf_combo.itemText(i)
            assert label == combo_label

        # Ensure that the currently selected configuration corresponds to the
        # currently selected one.
        assert conf_combo.currentText() == expected_configurations[0][-1]

        # Ensure that the executor settings are being loaded correctly per
        # run configuration
        for i, (ext, context, _) in enumerate(expected_configurations):
            conf_combo.setCurrentIndex(i)
            available_executors = executors_per_conf[(ext, context)]
            # Assert that the order and the executor configurations are loaded
            # according to the priority order.
            for (j, (executor_name,
                     default_conf,
                     req_cwd, _)) in enumerate(available_executors):
                exec_combo.setCurrentIndex(j)
                current_exec_name = exec_combo.currentText()
                conf_widget = dialog.current_widget
                current_conf = conf_widget.get_configuration()

                # Ensure that the selected executor corresponds to the one
                # defined by the priority order
                assert current_exec_name == executor_name

                # Ensure that the working directory options are enabled or
                # disabled according to the executor settings.
                assert not (wdir_group.isEnabled() ^ req_cwd)

                # Ensure that the executor configuration group widget contains
                # the default options declared.
                assert current_conf == default_conf

        # Select the first configuration again
        conf_combo.setCurrentIndex(0)

        # Change some default options
        conf_widget = dialog.current_widget
        cwd_radio = dialog.cwd_radio
        conf_widget.widgets['opt2'].setText('Test')
        cwd_radio.setChecked(True)

        # Execute the configuration
        buttons = dialog.bbox.buttons()
        run_btn = buttons[2]
        with qtbot.waitSignal(executor_1.sig_run_invocation) as sig:
            qtbot.mouseClick(run_btn, Qt.LeftButton)

    # Verify the selected executor output
    test_executor_name, handler_name, run_input, exec_conf = sig.args[0]
    ext, context, name = expected_configurations[0]
    available_executors = executors_per_conf[(ext, context)]
    executor_name, default_conf, _, handler = available_executors[0]
    conf_copy = copy.deepcopy(default_conf)

    conf_copy['opt2'] = 'Test'
    actual_run_input = run_input['run_input']
    metadata = run_input['metadata']

    name = metadata['name']
    source = metadata['source']
    path = metadata['path']
    context = metadata['context']
    run_conf_uuid = metadata['uuid']
    ext = metadata['input_extension']

    contents = actual_run_input['contents']
    assert contents == (f'File: {name} | Location: {path} | Source: {source} '
                        f'| Context: {context["name"]} | Ext: {ext}')

    assert test_executor_name == executor_name
    assert handler == 'both'

    # Ensure that the executor run configuration is transient
    assert exec_conf['uuid'] is None
    assert exec_conf['name'] is None

    # Check that the configuration parameters are the ones defined by the
    # dialog
    params = exec_conf['params']
    working_dir = params['working_dir']
    assert params['executor_params'] == conf_copy
    assert working_dir['source'] == WorkingDirSource.CurrentDirectory
    assert working_dir['path'] == temp_cwd

    # Assert that the run_exec dispatcher works for the specific combination
    assert handler_name == f'{ext}_{context["identifier"]}'

    # Assert that the run configuration gets registered without executor params
    stored_run_params = run.get_last_used_executor_parameters(run_conf_uuid)
    assert stored_run_params['executor'] == test_executor_name
    assert stored_run_params['selected'] is None
    assert not stored_run_params['display_dialog']
    assert not stored_run_params['first_execution']

    # The configuration gets run again
    with qtbot.waitSignal(executor_1.sig_run_invocation) as sig:
        run_act.trigger()

    # Assert that the transient run executor parameters reverted to the
    # default ones
    _, _, _, exec_conf = sig.args[0]
    params = exec_conf['params']
    working_dir = params['working_dir']
    assert working_dir['source'] == WorkingDirSource.ConfigurationDirectory
    assert working_dir['path'] == ''
    assert params['executor_params'] == default_conf

    # Focus into another configuration
    exec_provider_2.switch_focus('ext3', 'AnotherSuperContext')

    # Re-run last configuration
    re_run_act = run.get_action(RunActions.ReRun)

    with qtbot.waitSignal(executor_1.sig_run_invocation) as sig:
        re_run_act.trigger()

    # Assert that the previously ran configuration is the same as the current
    # one
    _, _, run_input, _ = sig.args[0]
    re_run_metadata = run_input['metadata']
    assert re_run_metadata == metadata

    # Run a subordinate context on the same executor
    subordinate_act = exec_provider_1.actions['SubordinateContext1']
    with qtbot.waitSignal(executor_1.sig_run_invocation) as sig:
        subordinate_act.trigger()

    subord_executor_name, handler_name, run_input, exec_conf = sig.args[0]
    available_executors = executors_per_conf[('ext1', 'SubordinateContext1')]
    executor_name, default_conf, _, handler = available_executors[1]

    assert subord_executor_name == executor_name
    assert handler_name == 'ext_ext1'

    actual_run_input = run_input['run_input']
    metadata = run_input['metadata']

    name = metadata['name']
    source = metadata['source']
    path = metadata['path']
    context = metadata['context']
    run_conf_uuid = metadata['uuid']
    ext = metadata['input_extension']

    contents = actual_run_input['contents']
    action = actual_run_input['action']
    re_run = actual_run_input['re_run']
    assert contents == (f'File: {name} | Location: {path} | Source: {source} '
                        f'| Context: {context["name"]} | Ext: {ext} '
                        f'| Action: {action} | Re-run: {re_run}')

    params = exec_conf['params']
    working_dir = params['working_dir']
    assert params['executor_params'] == default_conf
    assert working_dir['source'] == WorkingDirSource.ConfigurationDirectory
    assert working_dir['path'] == ''

    # Run a subordinate context on a different executor
    subordinate_act = exec_provider_2.actions['SubordinateContext2']
    with qtbot.waitSignal(executor_2.sig_run_invocation) as sig:
        subordinate_act.trigger()

    subord_executor_name, handler_name, run_input, exec_conf = sig.args[0]
    available_executors = executors_per_conf[('ext1', 'SubordinateContext2')]
    executor_name, default_conf, _, handler = available_executors[0]

    assert subord_executor_name == executor_name
    assert handler_name == 'context_subordinate_context2'

    actual_run_input = run_input['run_input']
    metadata = run_input['metadata']

    name = metadata['name']
    source = metadata['source']
    path = metadata['path']
    context = metadata['context']
    run_conf_uuid = metadata['uuid']
    ext = metadata['input_extension']

    contents = actual_run_input['contents']
    action = actual_run_input['action']
    re_run = actual_run_input['re_run']
    assert contents == (f'File: {name} | Location: {path} | Source: {source} '
                        f'| Context: {context["name"]} | Ext: {ext} '
                        f'| Action: {action} | Re-run: {re_run}')

    params = exec_conf['params']
    working_dir = params['working_dir']
    assert params['executor_params'] == default_conf
    assert working_dir['source'] == WorkingDirSource.ConfigurationDirectory
    assert working_dir['path'] == ''

    # Invoke another executor using one of the dedicated actions
    with qtbot.waitSignal(executor_2.sig_run_invocation) as sig:
        subordinate_act.trigger()

    used_executor_name, handler_name, run_input, exec_conf = sig.args[0]
    available_executors = executors_per_conf[('ext1', 'SubordinateContext1')]
    executor_name, default_conf, _, handler = available_executors[0]

    assert used_executor_name == executor_name

    # Switch to other run configuration and register a set of custom run
    # executor parameters
    exec_provider_2.switch_focus('ext3', 'AnotherSuperContext')

    # Spawn the configuration dialog
    run_act = run.get_action(RunActions.Run)
    run_act.trigger()

    dialog = container.dialog
    with qtbot.waitSignal(dialog.finished, timeout=200000):
        conf_combo = dialog.configuration_combo
        exec_combo = dialog.executor_combo
        store_params_cb = dialog.store_params_cb
        store_params_text = dialog.store_params_text

        # Modify some options
        conf_widget = dialog.current_widget
        conf_widget.widgets['name_1'].setChecked(True)
        conf_widget.widgets['name_2'].setChecked(False)

        # Make sure that the custom configuration is stored
        store_params_cb.setChecked(True)
        store_params_text.setText('CustomParams')

        # Execute the configuration
        buttons = dialog.bbox.buttons()
        run_btn = buttons[2]
        with qtbot.waitSignal(executor_1.sig_run_invocation) as sig:
            qtbot.mouseClick(run_btn, Qt.LeftButton)

    executor_name, _, run_input, exec_conf = sig.args[0]

    # Ensure that the configuration got saved
    saved_params = run.get_executor_configuration_parameters(
        executor_name, 'ext3', RunContext.AnotherSuperContext)
    executor_params = saved_params['params']
    assert len(executor_params) == 1

    # Check that the configuration passed to the executor is the same that was
    # saved.
    exec_conf_uuid = exec_conf['uuid']
    current_saved_params = executor_params[exec_conf_uuid]
    current_saved_params['params']['working_dir']['path'] = ''
    assert current_saved_params == exec_conf
    assert current_saved_params['name'] == 'CustomParams'

    # Check that the run configuration points to the latest saved parameters
    metadata = run_input['metadata']
    run_conf_uuid = metadata['uuid']
    stored_run_params = run.get_last_used_executor_parameters(run_conf_uuid)
    assert stored_run_params['executor'] == executor_name
    assert stored_run_params['selected'] == exec_conf_uuid
    assert not stored_run_params['display_dialog']
    assert not stored_run_params['first_execution']

    # Test teardown functions
    executor_1.on_run_teardown(run)
    executor_2.on_run_teardown(run)

    exec_provider_1.on_run_teardown(run)
    exec_provider_2.on_run_teardown(run)
