# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

# Standard library imports
import os
import os.path as osp
import random
import sys
import threading
import traceback

# Third-party imports
from jupyter_client.manager import KernelManager
from qtpy.QtCore import Qt
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QFileDialog, QLineEdit, QTabBar
# This is required to run our tests in VSCode or Spyder-unittest
from qtpy import QtWebEngineWidgets  # noqa
import psutil
import pytest

# Spyder imports
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.plugins import Plugins
from spyder.app import start
from spyder.config.base import get_home_dir, running_in_ci
from spyder.config.manager import CONF
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.projects.api import EmptyProject
from spyder.plugins.run.api import RunActions, StoredRunConfigurationExecutor
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils import encoding
from spyder.utils.environ import (get_user_env, set_user_env,
                                  amend_user_shell_init)

# =============================================================================
# ---- Constants
# =============================================================================
# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))

# Time to wait until the IPython console is ready to receive input
# (in milliseconds)
SHELL_TIMEOUT = 40000 if os.name == 'nt' else 20000

# Need longer EVAL_TIMEOUT, because need to cythonize and C compile ".pyx" file
# before import and eval it
COMPILE_AND_EVAL_TIMEOUT = 30000

# Time to wait for the IPython console to evaluate something (in
# milliseconds)
EVAL_TIMEOUT = 3000

# Time to wait for the completion services to be up or give a response
COMPLETION_TIMEOUT = 30000


# =============================================================================
# ---- Auxiliary functions
# =============================================================================
def open_file_in_editor(main_window, fname, directory=None):
    """Open a file using the Editor and its open file dialog"""
    top_level_widgets = QApplication.topLevelWidgets()
    for w in top_level_widgets:
        if isinstance(w, QFileDialog):
            if directory is not None:
                w.setDirectory(directory)
            input_field = w.findChildren(QLineEdit)[0]
            input_field.setText(fname)
            QTest.keyClick(w, Qt.Key_Enter)


def reset_run_code(qtbot, shell, code_editor, nsb):
    """Reset state after a run code test"""
    qtbot.waitUntil(lambda: not shell._executing)
    with qtbot.waitSignal(shell.executed):
        shell.execute('%reset -f')
    qtbot.waitUntil(
        lambda: nsb.editor.source_model.rowCount() == 0, timeout=EVAL_TIMEOUT)
    code_editor.setFocus()
    qtbot.keyClick(code_editor, Qt.Key_Home, modifier=Qt.ControlModifier)


def start_new_kernel(startup_timeout=60, kernel_name='python', spykernel=False,
                     **kwargs):
    """Start a new kernel, and return its Manager and Client"""
    km = KernelManager(kernel_name=kernel_name)
    if spykernel:
        km._kernel_spec = SpyderKernelSpec()
    km.start_kernel(**kwargs)
    kc = km.client()
    kc.start_channels()
    try:
        kc.wait_for_ready(timeout=startup_timeout)
    except RuntimeError:
        kc.stop_channels()
        km.shutdown_kernel()
        raise

    return km, kc


def find_desired_tab_in_window(tab_name, window):
    all_tabbars = window.findChildren(QTabBar)
    for current_tabbar in all_tabbars:
        for tab_index in range(current_tabbar.count()):
            if current_tabbar.tabText(tab_index) == str(tab_name):
                return current_tabbar, tab_index
    return None, None


def read_asset_file(filename):
    """Read contents of an asset file."""
    return encoding.read(osp.join(LOCATION, filename))[0]


def create_project(tmpdir):
    """Create a simple project."""
    # Create project directory
    project = tmpdir.mkdir('test_project')
    project_path = str(project)

    # Create Spyder project
    spy_project = EmptyProject(project_path)
    CONF.set('project_explorer', 'current_project_path', project_path)

    # Add a file to the project
    p_file = project.join('file.py')
    p_file.write(read_asset_file('script_outline_1.py'))
    spy_project.set_recent_files([str(p_file)])


def create_complex_project(tmpdir):
    """Create a complex project."""
    # Create project directories
    project = tmpdir.mkdir('test_project')
    project_subdir = project.mkdir('subdir')
    project_sub_subdir = project_subdir.mkdir('sub_subdir')

    # Create directories out of the project
    out_of_project_1 = tmpdir.mkdir('out_of_project_1')
    out_of_project_2 = tmpdir.mkdir('out_of_project_2')
    out_of_project_1_subdir = out_of_project_1.mkdir('subdir')
    out_of_project_2_subdir = out_of_project_2.mkdir('subdir')

    project_path = str(project)
    spy_project = EmptyProject(project_path)
    CONF.set('project_explorer', 'current_project_path', project_path)

    # Add some files to project. This is necessary to test that we get
    # symbols for all these files.
    abs_filenames = []
    filenames_to_create = {
        project: ['file1.py', 'file2.py', 'file3.txt', '__init__.py'],
        project_subdir: ['a.py', '__init__.py'],
        project_sub_subdir: ['b.py', '__init__.py'],
        out_of_project_1: ['c.py'],
        out_of_project_2: ['d.py', '__init__.py'],
        out_of_project_1_subdir: ['e.py', '__init__.py'],
        out_of_project_2_subdir: ['f.py']
    }

    for path in filenames_to_create.keys():
        filenames = filenames_to_create[path]
        for filename in filenames:
            p_file = path.join(filename)
            abs_filenames.append(str(p_file))
            if osp.splitext(filename)[1] == '.py':
                if path == project_subdir:
                    code = read_asset_file('script_outline_2.py')
                elif path == project_sub_subdir:
                    code = read_asset_file('script_outline_3.py')
                else:
                    code = read_asset_file('script_outline_1.py')
                p_file.write(code)
            else:
                p_file.write("Hello world!")

    spy_project.set_recent_files(abs_filenames)


def create_namespace_project(tmpdir):
    """Create a project that contains a namespace package."""
    # Create project as example posted in:
    # https://github.com/spyder-ide/spyder/issues/16406#issuecomment-917992317
    project = tmpdir.mkdir('namespace-project')
    ns_package = project.mkdir('namespace-package')
    sub_package = ns_package.mkdir('sub-package')

    project_path = str(project)
    spy_project = EmptyProject(project_path)
    CONF.set('project_explorer', 'current_project_path', project_path)

    # Add some files to sub-package.
    abs_filenames = []
    filenames_to_create = {sub_package: ['module_1.py', '__init__.py']}

    for path in filenames_to_create.keys():
        filenames = filenames_to_create[path]
        for filename in filenames:
            p_file = path.join(filename)
            abs_filenames.append(str(p_file))

            # Use different files to be extra sure we're loading symbols in
            # each case.
            if filename == 'module.py':
                code = read_asset_file('script_outline_4.py')
            else:
                code = read_asset_file('script_outline_1.py')

            p_file.write(code)

    spy_project.set_recent_files(abs_filenames)


def preferences_dialog_helper(qtbot, main_window, section):
    """
    Open preferences dialog and select page with `section` (CONF_SECTION).
    """
    # Wait until the window is fully up
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=SHELL_TIMEOUT
    )

    main_window.show_preferences()
    preferences = main_window.preferences
    container = preferences.get_container()

    qtbot.waitUntil(lambda: container.dialog is not None, timeout=5000)
    dlg = container.dialog
    index = dlg.get_index_by_name(section)
    page = dlg.get_page(index)
    dlg.set_current_index(index)
    return dlg, index, page


def generate_run_parameters(mainwindow, filename, selected=None,
                            executor=None):
    """Generate run configuration parameters for a given filename."""
    file_uuid = mainwindow.editor.get_widget().id_per_file[filename]
    if executor is None:
        executor = mainwindow.ipyconsole.NAME

    file_run_params = StoredRunConfigurationExecutor(
        executor=executor,
        selected=selected,
    )

    return {file_uuid: [file_run_params]}


def get_random_dockable_plugin(main_window, exclude=None):
    """Get a random dockable plugin and give it focus."""
    plugins = main_window.get_dockable_plugins()
    for plugin_name, plugin in plugins:
        if exclude and plugin_name in exclude:
            plugins.remove((plugin_name, plugin))

    plugin = random.choice(plugins)[1]

    if not plugin.get_widget().toggle_view_action.isChecked():
        plugin.toggle_view(True)
        plugin._hide_after_test = True

    plugin.switch_to_plugin()
    plugin.get_widget().get_focus_widget().setFocus()
    return plugin


# =============================================================================
# ---- Pytest hooks
# =============================================================================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture(scope="session", autouse=True)
def cleanup(request, qapp):
    """Cleanup the testing setup once we are finished."""

    def close_window():
        # Close last used mainwindow and QApplication if needed
        if hasattr(main_window, 'window') and main_window.window is not None:
            window = main_window.window
            main_window.window = None
            window.closing(close_immediately=True)
            window.close()
            window = None
            CONF.reset_to_defaults(notification=False)
            CONF.reset_manager()
            PLUGIN_REGISTRY.reset()

        if qapp.instance():
            for widget in qapp.allWidgets():
                try:
                    widget.close()
                except RuntimeError:
                    pass
            qapp.quit()

    request.addfinalizer(close_window)


@pytest.fixture
def main_window(request, tmpdir, qtbot):
    """Main Window fixture"""

    # Get original processEvents function in case the test that overrides it
    # fails
    super_processEvents = QApplication.processEvents

    # Don't show tours message
    CONF.set('tours', 'show_tour_message', False)

    # Tests assume inline backend
    CONF.set('ipython_console', 'pylab/backend', 'inline')

    # Test assume the plots are rendered in the console as png
    CONF.set('plots', 'mute_inline_plotting', False)
    CONF.set('ipython_console', 'pylab/inline/figure_format', "png")

    # Set exclamation mark to True
    CONF.set('debugger', 'pdb_use_exclamation_mark', True)

    # Check if we need to use introspection in a given test
    # (it's faster and less memory consuming not to use it!)
    use_introspection = request.node.get_closest_marker('use_introspection')

    if use_introspection:
        CONF.set('completions', ('enabled_providers', 'lsp'), True)
        CONF.set('completions', ('enabled_providers', 'fallback'), True)
        CONF.set('completions', ('enabled_providers', 'snippets'), True)
    else:
        CONF.set('completions', ('enabled_providers', 'lsp'), False)
        CONF.set('completions', ('enabled_providers', 'fallback'), False)
        CONF.set('completions', ('enabled_providers', 'snippets'), False)

    # Only use single_instance mode for tests that require it
    single_instance = request.node.get_closest_marker('single_instance')

    if single_instance:
        CONF.set('main', 'single_instance', True)
    else:
        CONF.set('main', 'single_instance', False)

    # Check if we need to load a simple project to the interface
    preload_project = request.node.get_closest_marker('preload_project')
    if preload_project:
        create_project(tmpdir)
    else:
        CONF.set('project_explorer', 'current_project_path', None)

    # Check if we need to preload a complex project in a give test
    preload_complex_project = request.node.get_closest_marker(
        'preload_complex_project')
    if preload_complex_project:
        CONF.set('editor', 'show_class_func_dropdown', True)
        create_complex_project(tmpdir)
    else:
        CONF.set('editor', 'show_class_func_dropdown', False)
        if not preload_project:
            CONF.set('project_explorer', 'current_project_path', None)

    # Check if we need to preload a project with a namespace package
    preload_namespace_project = request.node.get_closest_marker(
        'preload_namespace_project')
    if preload_namespace_project:
        create_namespace_project(tmpdir)
    else:
        if not (preload_project or preload_complex_project):
            CONF.set('project_explorer', 'current_project_path', None)

    # Get config values passed in parametrize and apply them
    try:
        param = request.param
        if isinstance(param, dict) and 'spy_config' in param:
            CONF.set(*param['spy_config'])
    except AttributeError:
        # Not all tests that use this fixture define request.param
        pass

    QApplication.processEvents()

    if not hasattr(main_window, 'window') or main_window.window is None:
        # Start the window
        window = start.main()
        main_window.window = window

    else:
        window = main_window.window

        if not request.node.get_closest_marker('no_new_console'):
            # Create a new console to ensure new config is loaded
            # even if the same mainwindow instance is reused
            window.ipyconsole.create_new_client(give_focus=True)

    # Add a handle to the "Debug file" button to access it quickly because
    # it's used a lot.
    toolbar = window.get_plugin(Plugins.Toolbar)
    debug_toolbar = toolbar.get_application_toolbar(ApplicationToolbars.Debug)
    debug_action = window.run.get_action(
        "run file in debugger")
    debug_button = debug_toolbar.widgetForAction(debug_action)
    window.debug_button = debug_button

    # Add a handle to the run buttons to access it quickly because they are
    # used a lot.
    run_toolbar = toolbar.get_application_toolbar(ApplicationToolbars.Run)
    run_action = window.run.get_action(RunActions.Run)
    run_button = run_toolbar.widgetForAction(run_action)
    window.run_button = run_button

    run_cell_action = window.run.get_action('run cell')
    run_cell_button = run_toolbar.widgetForAction(run_cell_action)
    window.run_cell_button = run_cell_button

    run_cell_and_advance_action = window.run.get_action('run cell and advance')
    run_cell_and_advance_button = run_toolbar.widgetForAction(
        run_cell_and_advance_action)
    window.run_cell_and_advance_button = run_cell_and_advance_button

    run_selection_action = window.run.get_action('run selection and advance')
    run_selection_button = run_toolbar.widgetForAction(run_selection_action)
    window.run_selection_button = run_selection_button

    QApplication.processEvents()

    if os.name != 'nt':
        # _DummyThread are created if current_thread() is called from them.
        # They will always leak (From python doc) so we ignore them.
        init_threads = [
            repr(thread) for thread in threading.enumerate()
            if not isinstance(thread, threading._DummyThread)]
        proc = psutil.Process()
        init_files = [repr(f) for f in proc.open_files()]
        init_subprocesses = [repr(f) for f in proc.children()]

    yield window

    # Remap original QApplication.processEvents function
    QApplication.processEvents = super_processEvents

    # Print shell content if failed
    if request.node.rep_setup.passed:
        if request.node.rep_call.failed:
            # Print content of shellwidget and close window
            print(window.ipyconsole.get_current_shellwidget(
                )._control.toPlainText())
            # Print info page content is not blank
            console = window.ipyconsole
            client = console.get_current_client()
            if client.info_page != client.blank_page:
                print('info_page')
                print(client.info_page)
            main_window.window = None
            window.closing(close_immediately=True)
            window.close()
            window = None
            CONF.reset_to_defaults(notification=False)
            CONF.reset_manager()
            PLUGIN_REGISTRY.reset()

        else:
            # Try to close used mainwindow directly on fixture
            # after running test that uses the fixture
            # Currently 'test_out_runfile_runcell' is the last tests so
            # in order to prevent errors finalizing the test suit such test has
            # this marker.
            # Also, try to decrease chances of freezes/timeouts from tests that
            # are known to have leaks by also closing the main window for them.
            known_leak = request.node.get_closest_marker(
                'known_leak')
            close_main_window = request.node.get_closest_marker(
                'close_main_window')
            if close_main_window or known_leak:
                main_window.window = None
                window.closing(close_immediately=True)
                window.close()
                window = None
                CONF.reset_to_defaults(notification=False)
                CONF.reset_manager()
                PLUGIN_REGISTRY.reset()
            else:
                try:
                    # Close or hide everything we can think of
                    window.switcher.hide()
                    window.switcher.on_close()

                    # Close editor related elements
                    window.editor.close_all_files()

                    # Force close all files
                    editor_widget = window.editor.get_widget()
                    while editor_widget.editorstacks[0].close_file(force=True):
                        pass
                    for editorwindow in editor_widget.editorwindows:
                        editorwindow.close()

                    window.projects.close_project()

                    if window.console.error_dialog:
                        window.console.close_error_dialog()

                    # Reset cwd
                    window.explorer.chdir(get_home_dir())

                    # Restore default Spyder Python Path
                    CONF.set(
                        'pythonpath_manager', 'spyder_pythonpath',
                        CONF.get_default('pythonpath_manager',
                                         'spyder_pythonpath')
                    )

                    # Restore run configurations
                    CONF.set('run', 'configurations', [])

                    # Close consoles
                    (window.ipyconsole.get_widget()
                        .create_new_client_if_empty) = False
                    window.ipyconsole.restart()
                except Exception:
                    main_window.window = None
                    window.closing(close_immediately=True)
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    CONF.reset_manager()
                    PLUGIN_REGISTRY.reset()
                    return

                if os.name == 'nt':
                    # Do not test leaks on windows
                    return

                def show_diff(init_list, now_list, name):
                    sys.stderr.write(f"Extra {name} before test:\n")
                    for item in init_list:
                        if item in now_list:
                            now_list.remove(item)
                        else:
                            sys.stderr.write(item + "\n")
                    sys.stderr.write(f"Extra {name} after test:\n")
                    for item in now_list:
                        sys.stderr.write(item + "\n")

                # The test is not allowed to open new files or threads.
                try:
                    def threads_condition():
                        threads = [
                            thread for thread in threading.enumerate()
                            if not isinstance(thread, threading._DummyThread)]
                        return (len(init_threads) >= len(threads))

                    qtbot.waitUntil(threads_condition, timeout=SHELL_TIMEOUT)
                except Exception:
                    now_threads = [
                        thread for thread in threading.enumerate()
                        if not isinstance(thread, threading._DummyThread)]
                    threads = [repr(t) for t in now_threads]
                    show_diff(init_threads, threads, "thread")
                    sys.stderr.write("Running Threads stacks:\n")
                    now_thread_ids = [t.ident for t in now_threads]
                    for thread_id, frame in sys._current_frames().items():
                        if thread_id in now_thread_ids:
                            sys.stderr.write(
                                "\nThread " + str(threads) + ":\n")
                            traceback.print_stack(frame)
                    main_window.window = None
                    window.closing(close_immediately=True)
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    CONF.reset_manager()
                    PLUGIN_REGISTRY.reset()
                    raise

                try:
                    qtbot.waitUntil(lambda: (
                        len(init_subprocesses) >= len(proc.children())),
                        timeout=SHELL_TIMEOUT)
                except Exception:
                    subprocesses = [repr(f) for f in proc.children()]
                    show_diff(init_subprocesses, subprocesses, "processes")
                    main_window.window = None
                    window.closing(close_immediately=True)
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    CONF.reset_manager()
                    PLUGIN_REGISTRY.reset()
                    raise

                try:
                    files = [
                        repr(f) for f in proc.open_files()
                        if 'QtWebEngine' not in repr(f)
                    ]
                    qtbot.waitUntil(
                        lambda: (len(init_files) >= len(files)),
                        timeout=SHELL_TIMEOUT)
                except Exception:
                    show_diff(init_files, files, "files")
                    main_window.window = None
                    window.closing(close_immediately=True)
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    CONF.reset_manager()
                    PLUGIN_REGISTRY.reset()
                    raise


@pytest.fixture
def restore_user_env():
    """Set user environment variables and restore upon test exit"""
    if not running_in_ci():
        pytest.skip("Skipped because not in CI.")

    if os.name == "nt":
        orig_env = get_user_env()

    yield

    if os.name == "nt":
        set_user_env(orig_env)
    else:
        amend_user_shell_init(restore=True)
