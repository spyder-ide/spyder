# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

# Standard library imports
import os
import os.path as osp
import sys
import threading
import traceback

# Third-party imports
from qtpy.QtWidgets import QApplication
import psutil
import pytest

# Spyder imports
from spyder.app import start
from spyder.config.base import get_home_dir
from spyder.config.manager import CONF
from spyder.plugins.projects.api import EmptyProject
from spyder.utils import encoding


# =============================================================================
# ---- Constants
# =============================================================================
# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))

# Time to wait until the IPython console is ready to receive input
# (in milliseconds)
SHELL_TIMEOUT = 40000 if os.name == 'nt' else 20000


# =============================================================================
# ---- Auxiliary functions
# =============================================================================
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
            window.close()
            window = None
            CONF.reset_to_defaults(notification=False)
        if qapp.instance():
            qapp.quit()

    request.addfinalizer(close_window)


@pytest.fixture
def main_window(request, tmpdir, qtbot):
    """Main Window fixture"""

    # Get original processEvents function in case the test that overrides it
    # fails
    super_processEvents = QApplication.processEvents

    # Disable Kite provider
    CONF.set('completions', 'enabled_providers', {'kite': False})

    # Don't show tours message
    CONF.set('tours', 'show_tour_message', False)

    # Tests assume inline backend
    CONF.set('ipython_console', 'pylab/backend', 0)

    # Test assume the plots are rendered in the console as png
    CONF.set('plots', 'mute_inline_plotting', False)
    CONF.set('ipython_console', 'pylab/inline/figure_format', 0)

    # Set exclamation mark to True
    CONF.set('ipython_console', 'pdb_use_exclamation_mark', True)

    # Check if we need to use introspection in a given test
    # (it's faster and less memory consuming not to use it!)
    use_introspection = request.node.get_closest_marker('use_introspection')

    if use_introspection:
        os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    else:
        try:
            os.environ.pop('SPY_TEST_USE_INTROSPECTION')
        except KeyError:
            pass

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
        create_complex_project(tmpdir)
    else:
        if not preload_project:
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
        from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
        PLUGIN_REGISTRY.reset()

        # Start the window
        window = start.main()
        main_window.window = window

    else:
        window = main_window.window

        if not request.node.get_closest_marker('no_new_console'):
            # Create a new console to ensure new config is loaded
            # even if the same mainwindow instance is reused
            window.ipyconsole.create_new_client(give_focus=True)

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
            window.close()
            window = None
            CONF.reset_to_defaults(notification=False)
        else:
            # Try to close used mainwindow directly on fixture
            # after running test that uses the fixture
            # Currently 'test_out_runfile_runcell' is the last tests so
            # in order to prevent errors finalizing the test suit such test has
            # this marker
            close_main_window = request.node.get_closest_marker(
                'close_main_window')
            if close_main_window:
                main_window.window = None
                window.close()
                window = None
                CONF.reset_to_defaults(notification=False)
            else:
                try:
                    # Close everything we can think of
                    window.switcher.close()

                    # Close editor related elements
                    window.editor.close_all_files()
                    # force close all files
                    while window.editor.editorstacks[0].close_file(force=True):
                        pass
                    for editorwindow in window.editor.editorwindows:
                        editorwindow.close()
                    editorstack = window.editor.get_current_editorstack()
                    if editorstack.switcher_dlg:
                        editorstack.switcher_dlg.close()

                    window.projects.close_project()

                    if window.console.error_dialog:
                        window.console.close_error_dialog()

                    # Reset cwd
                    window.explorer.chdir(get_home_dir())

                    # Restore default Spyder Python Path
                    CONF.set(
                        'main', 'spyder_pythonpath',
                        CONF.get_default('main', 'spyder_pythonpath'))

                    # Restore run configurations
                    CONF.set('run', 'configurations', [])

                    # Close consoles
                    (window.ipyconsole.get_widget()
                        .create_new_client_if_empty) = False
                    window.ipyconsole.restart()

                except Exception:
                    main_window.window = None
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    return

                if os.name == 'nt':
                    # Do not test leaks on windows
                    return

                known_leak = request.node.get_closest_marker(
                    'known_leak')
                if known_leak:
                    # This test has a known leak
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
                    for threadId, frame in sys._current_frames().items():
                        if threadId in now_thread_ids:
                            sys.stderr.write(
                                "\nThread " + str(threads) + ":\n")
                            traceback.print_stack(frame)
                    main_window.window = None
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    raise

                try:
                    qtbot.waitUntil(lambda: (
                        len(init_subprocesses) >= len(proc.children())),
                        timeout=SHELL_TIMEOUT)
                except Exception:
                    subprocesses = [repr(f) for f in proc.children()]
                    show_diff(init_subprocesses, subprocesses, "processes")
                    main_window.window = None
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
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
                    window.close()
                    window = None
                    CONF.reset_to_defaults(notification=False)
                    raise
