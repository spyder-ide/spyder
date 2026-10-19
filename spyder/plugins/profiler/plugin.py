# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler Plugin.
"""

# Standard library imports
from concurrent.futures import Future
import os.path as osp
from typing import List, Optional

# Third party imports
from packaging.version import parse
from qtpy.QtCore import Qt

# Local imports
from spyder.api.plugins import (
    ExposedCallError,
    Plugins,
    SpyderDockablePlugin,
    expose,
)
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.summary import (
    SortKey,
    describe_callers_and_callees,
    find_functions,
    make_is_library,
    summarize_profile,
)
from spyder.plugins.profiler.widgets.main_widget import ProfilerWidget
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.ipythonconsole.api import IPythonConsolePyConfiguration
from spyder.plugins.run.api import (
    ExtendedRunExecutionParameters,
    RunConfiguration,
    RunContext,
    RunExecutor,
    RunResult,
    run_execute,
)
from spyder.plugins.ipythonconsole.utils.execution import (
    DEFAULT_EXECUTE_TIMEOUT,
    build_run_line,
    check_ready,
    run_code,
)
from spyder.plugins.ipythonconsole.widgets.run_conf import IPythonConfigOptions
from spyder.plugins.editor.api.run import CellRun, SelectionRun


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin, ShellConnectPluginMixin, RunExecutor):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [
        Plugins.Preferences,
        Plugins.IPythonConsole,
        Plugins.Run,
        Plugins.Toolbar,
    ]
    OPTIONAL = [Plugins.Editor]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    def __init__(self, parent, configuration=None):
        SpyderDockablePlugin.__init__(self, parent, configuration)

        # Combined with ShellConnectPluginMixin and RunExecutor via multiple
        # inheritance; set up their state here since SpyderDockablePlugin's
        # __init__ doesn't reach them (and RunExecutor.__init__ would also
        # re-init the QObject part).
        ShellConnectPluginMixin.__init__(self)
        self.setup_run_executor()

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Profiler")

    @staticmethod
    def get_description():
        return _("Profile Python files to find execution bottlenecks.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('profiler')

    def on_initialize(self):

        self.python_editor_run_configuration = {
            'origin': self.NAME,
            'extension': ['py', 'ipy', 'pyw'],
            "contexts": [
                {"name": "File"},
                {"name": "Cell"},
                {"name": "Selection"},
            ],
        }

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 3
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'pyw',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': ['py', 'ipy', 'pyw'],
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': ['py', 'ipy', 'pyw'],
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
        ]

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)

        # Remove current parameters to recreate them due to the new
        # architecture for profiling introduced in PR spyder-ide/spyder#24794
        if (
            # This is needed when updgrading from Spyder 6.0 to 6.1
            (
                parse(self.old_spyder_conf_version) <= parse("87.3.0")
                and parse(self.spyder_conf_version) > parse("87.3.0")
            )
            # And this when downgrading from Spyder 6.1 to 6.0
            or (
                parse(self.old_spyder_conf_version) > parse("87.3.0")
                and parse(self.spyder_conf_version) <= parse("87.3.0")
            )
        ):
            all_execution_params = self.get_conf(
                "parameters", section="run", default={}
            )
            if self.NAME in all_execution_params:
                all_execution_params.pop(self.NAME)
                self.set_conf(
                    "parameters", all_execution_params, section="run"
                )

        run.register_executor_configuration(self, self.executor_configuration)

        run.create_run_in_executor_button(
            RunContext.File,
            self.NAME,
            text=_("Profile file"),
            tip=_("Profile file"),
            icon=self.create_icon('profiler'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.Profile,
            },
            add_to_toolbar=ApplicationToolbars.Profile,
            shortcut_widget_context=Qt.ShortcutContext.ApplicationShortcut,
        )

        run.create_run_in_executor_button(
            RunContext.Cell,
            self.NAME,
            text=_("Profile cell"),
            tip=_("Profile cell"),
            icon=self.create_icon('profile_cell'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.Profile,
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

        run.create_run_in_executor_button(
            RunContext.Selection,
            self.NAME,
            text=_("Profile current line or selection"),
            tip=_("Profile current line or selection"),
            icon=self.create_icon('profile_selection'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.Profile,
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration
        )

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.add_supported_run_configuration(
            self.python_editor_run_configuration
        )

        widget.sig_edit_goto_requested.connect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.remove_supported_run_configuration(
            self.python_editor_run_configuration
        )

        widget.sig_edit_goto_requested.disconnect(editor.load)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.create_application_toolbar(
            ApplicationToolbars.Profile, _("Profile toolbar")
        )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.remove_application_toolbar(ApplicationToolbars.Profile)

    def on_mainwindow_visible(self):
        # Make plugin visible in case it's not but only once. For most users
        # this will display it in the UI when moving from 6.0 to 6.1
        if not self.get_conf("make_visible", default=False):
            if not self.get_widget().is_visible:
                self.get_widget().toggle_view(True)
            self.set_conf("make_visible", True)

    # ---- For execution
    # -------------------------------------------------------------------------
    @run_execute(context=RunContext.File)
    def profile_file(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        params["run_method"] = "profilefile"

        return console.exec_files(input, conf)

    @run_execute(context=RunContext.Cell)
    def profile_cell(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:
        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        run_input: CellRun = input['run_input']
        if run_input['copy']:
            code = run_input['cell']
            if not code.strip():
                # Empty cell
                return

            console.run_selection("%%profile\n" + code)
            return

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        params["run_method"] = "profilecell"

        return console.exec_cell(input, conf)

    @run_execute(context=RunContext.Selection)
    def profile_selection(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        run_input: SelectionRun = input['run_input']
        code = run_input['selection']
        if not code.strip():
            # No selection
            return

        run_input['selection'] = "%%profile\n" + code

        return console.exec_selection(input, conf)

    # ---- For outside callers (e.g. AI agents)
    # -------------------------------------------------------------------------
    @expose(name="profile_code")
    def profile_code_with_output(
        self,
        code: str,
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
        limit: int = 20,
    ) -> Future:
        """
        Profile Python code in an IPython console and get its output and the
        functions where it spent the most time, measured with cProfile. The
        results are also shown in Spyder's Profiler pane. Use
        get_profile_results to see the callers and callees of a function.

        The code runs like with execute_code: in the user's live kernel,
        waiting for the console to be free, and slower than usual because of
        the profiling.

        Parameters
        ----------
        code : str
            Python code to profile.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the console to be free and the code to
            finish. If it doesn't finish in time, use get_profile_results
            once it does.
        limit : int, optional
            Maximum number of functions in the results.

        Returns
        -------
        Future
            Resolved with the ``output``, whether the code
            ``raised_exception``, the ``images`` it displayed, ``notes`` and
            the ``profile``: the ``total_time`` and the ``functions`` that
            took the most time (sorted by the time spent in the function
            itself), with their ``calls``, ``local_time``, ``total_time``
            (including the functions they called), location and whether
            they're ``library`` code.
        """
        return self._profile(f"%%profile\n{code}", console_id, timeout, limit)

    @expose(name="profile_file")
    def profile_file_with_output(
        self,
        filename: str,
        args: str = "",
        wdir: Optional[str] = None,
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
        limit: int = 20,
    ) -> Future:
        """
        Profile a Python file in an IPython console, like Run > Profile in
        Spyder, and get its output and the functions where it spent the most
        time. If the file is open in the Editor, its current contents run,
        including unsaved changes.

        Parameters
        ----------
        filename : str
            Absolute path of the file.
        args : str, optional
            Command line arguments for the file.
        wdir : str, optional
            Working directory to run the file in. By default, the file's
            directory.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the console to be free and the file to
            finish. If it doesn't finish in time, use get_profile_results
            once it does.
        limit : int, optional
            Maximum number of functions in the results.

        Returns
        -------
        Future
            Resolved like the one of ``profile_code_with_output``.
        """
        filename = osp.abspath(filename)
        if not osp.isfile(filename):
            raise ExposedCallError(f"{filename} doesn't exist.")

        shellwidget = self._get_console_shellwidget(console_id)
        line = build_run_line(
            shellwidget, filename, args, wdir, method="profilefile"
        )
        return self._profile(line, console_id, timeout, limit)

    @expose(read_only=True)
    def get_profile_results(
        self,
        console_id: Optional[str] = None,
        function: Optional[str] = None,
        sort: SortKey = "local",
        limit: int = 20,
        include_libraries: bool = True,
    ) -> dict:
        """
        Get the results of the last profiling in an IPython console (by the
        user or with profile_code or profile_file): the functions where it
        spent the most time or, for one function, the functions that called
        it and the ones it called, with the time spent through each.

        Parameters
        ----------
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        function : str, optional
            Function to get the callers and callees of, by name (e.g.
            ``solve``) or location (e.g. ``model.py:42``).
        sort : str, optional
            Sort functions by ``local`` time (spent in the function itself),
            ``total`` time (including the functions it called) or number of
            ``calls``.
        limit : int, optional
            Maximum number of functions.
        include_libraries : bool, optional
            Whether to include functions from libraries, the standard
            library and built-ins, or only the user's code.
        """
        shellwidget = self._get_console_shellwidget(console_id)
        data_tree = self._get_data_tree(shellwidget)
        stats = data_tree.profdata if data_tree is not None else None
        if stats is None:
            raise ExposedCallError(
                "There are no profiling results in this console. Use "
                "profile_code or profile_file first."
            )

        is_library = make_is_library(data_tree.is_builtin)
        if function is None:
            return summarize_profile(
                stats, is_library, sort, limit, include_libraries
            )

        keys = find_functions(stats, function)
        if not keys:
            raise ExposedCallError(
                f"No function {function!r} in the profiling results. Use "
                f"the names or locations listed without the function "
                f"argument."
            )
        return {
            "matches": [
                describe_callers_and_callees(key, stats, is_library, limit)
                for key in keys[:5]
            ]
        }

    def _get_console_shellwidget(self, console_id):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        shellwidget = ipyconsole.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        return shellwidget

    def _get_data_tree(self, shellwidget):
        """Profiling results tree of a console, if any."""
        widget = self.get_widget().get_widget_for_shellwidget(shellwidget)
        return getattr(widget, "data_tree", None)

    def _profile(self, line, console_id, timeout, limit) -> Future:
        """Run a profiling magic and add a summary of its results."""
        shellwidget = self._get_console_shellwidget(console_id)
        data_tree = self._get_data_tree(shellwidget)
        if data_tree is None:
            raise ExposedCallError("The console's profiler isn't ready.")
        previous = data_tree.profdata

        result = Future()

        def on_done(future):
            try:
                data = future.result()
            except Exception as error:
                result.set_exception(error)
                return

            stats = data_tree.profdata
            if stats is None or stats is previous:
                data["profile"] = None
                data.setdefault("notes", []).append(
                    "There are no profiling results yet. If the code is "
                    "still running, use get_profile_results when it "
                    "finishes."
                )
            else:
                data["profile"] = summarize_profile(
                    stats, make_is_library(data_tree.is_builtin), limit=limit
                )
            result.set_result(data)

        run_code(shellwidget, line, timeout).add_done_callback(on_done)
        return result
