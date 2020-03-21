# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console plugin based on QtConsole.
"""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget)
from spyder.utils.programs import get_temp_dir


# Localization
_ = get_translation('spyder')


class IPythonConsole(SpyderDockablePlugin):
    """
    IPython Console plugin
    """

    NAME = 'ipython_console'
    REQUIRES = [Plugins.Console]
    OPTIONAL = [Plugins.Editor]
    TABIFY = [Plugins.History]
    WIDGET_CLASS = IPythonConsoleWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = IPythonConsoleConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    CONF_FROM_OPTIONS = {
        # Appearance
        'color_scheme': ('appearance', 'selected'),
        'css_path': ('appearance', 'css_path'),
        # Editor
        'save_all_before_run': ('editor', 'save_all_before_run'),
        # Existing kernel?
        'connection_settings': ('existing-kernel', 'settings'),
        # Help
        'connect_to_help': ('help', 'connect/ipython_console'),
        # Main interpreter
        'use_default_main_interpreter': ('main_interpreter', 'default'),
        'main_interpreter_executable': ('main_interpreter', 'executable'),
        # Run
        'breakpoints': ('run', 'breakpoints'),
        'pdb_execute_events': ('run', 'pdb_execute_events'),
        'pdb_ignore_lib': ('run', 'pdb_ignore_lib'),
        # Workingdir
        # FIXME: All this could be simplified
        'console/use_project_or_home_directory': (
            'workingdir', 'console/use_project_or_home_directory'),
        'console/use_fixed_directory': (
            'workingdir', 'console/use_fixed_directory'),
        'console/fixed_directory': ('workingdir', 'console/fixed_directory'),
        'startup/use_fixed_directory': (
            'workingdir', 'startup/use_fixed_directory'),
        'startup/fixed_directory': ('workingdir', 'startup/fixed_directory'),
    }

    # Signals
    sig_history_requested = Signal(str)
    """
    """

    sig_append_to_history_requested = Signal(str, str)
    """
    FIXME:
    """

    sig_edit_goto_requested = Signal((str, int, str), (str, int, str, bool))
    """
    FIXME:
    """

    sig_focus_changed = Signal()
    """
    FIXME:
    """

    sig_pdb_state_changed = Signal(bool, dict)  # old: sig_pdb_state
    """
    FIXME:
    """

    sig_exception_occurred = Signal(dict)
    """
    FIXME:
    """

    sig_render_plain_text_requested = Signal(str)
    """
    This signal is emitted to request a plain text help render.

    Parameters
    ----------
    plain_text: str
        The plain text to render.
    """

    sig_render_rich_text_requested = Signal(str, bool)
    """
    This signal is emitted to request a rich text help render.

    Parameters
    ----------
    rich_text: str
        The rich text.
    collapse: bool
        If the text contains collapsed sections, show them closed (True) or
        open (False).
    """

    sig_shellwidget_process_started = Signal(object)
    """
    This signal is emitted when a shellwidget process starts.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_shellwidget_process_finished = Signal(object)
    """
    This signal is emitted when a shellwidget process finishes.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_shellwidget_changed = Signal(object)
    """
    This signal is emitted when the current shellwidget changes.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_help_requested = Signal(dict)
    """
    This signal is emitted to request help on a given object `name`.
    Parameters
    ----------
    help_data: dict
        Example `{'name': str, 'ignore_unknown': bool}`.
    """

    sig_current_directory_changed = Signal(str)
    """
    This signal is emitted when the current directory of the active shell
    widget has changed.
    Parameters
    ----------
    working_directory: str
        The new working directory path.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('IPython console')

    def get_description(self):
        return _('IPython console')

    def get_icon(self):
        return self.create_icon('ipython_console')

    def register(self):
        widget = self.get_widget()
        console = self.get_plugin(Plugins.Console)
        editor = self.get_plugin(Plugins.Editor)

        # TODO: Temporary workaround while the editor is decoupled from the
        # ipyconsole
        widget.main = self._main

        # Expose main widget signals on the plugin
        widget.sig_help_requested.connect(self.sig_help_requested)
        widget.sig_history_requested.connect(self.sig_history_requested)
        widget.sig_append_to_history_requested.connect(
            self.sig_append_to_history_requested)
        widget.sig_shellwidget_process_started.connect(
            self.sig_shellwidget_process_started)
        widget.sig_shellwidget_process_finished.connect(
            self.sig_shellwidget_process_finished)
        widget.sig_shellwidget_changed.connect(
            self.sig_shellwidget_changed)
        widget.sig_current_tab_changed.connect(self.update_working_directory)
        widget.sig_current_tab_changed.connect(self.check_pdb_state)
        widget.sig_focus_changed.connect(self.sig_focus_changed)
        widget.sig_working_directory_changed.connect(
            self.sig_current_directory_changed)
        widget.sig_spyder_python_path_update_requested.connect(
            self.update_spyder_python_path)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_edit_goto_requested[str, int, str, bool].connect(
            self.sig_edit_goto_requested[str, int, str, bool])
        widget.sig_exception_occurred.connect(self.sig_exception_occurred)

        # Connect to editor slots
        if editor:
            self.sig_edit_goto_requested.connect(editor.load)
            self.sig_edit_goto_requested[str, int, str, bool].connect(
                lambda fname, lineno, word, processevents:
                    editor.load(fname, lineno, word,
                                processevents=processevents))

            # FIXME: These editor signal names
            editor.breakpoints_saved.connect(self.set_spyder_breakpoints)
            editor.run_in_current_ipyclient.connect(self.run_script)
            editor.run_cell_in_ipyclient.connect(self.run_cell)
            editor.debug_cell_in_ipyclient.connect(self.debug_cell)

        # FIXME:
        # self.focus_changed.connect(self.main.plugin_focus_changed)
        # self.tabwidget.currentChanged.connect(self.update_working_directory)
        # self.tabwidget.currentChanged.connect(self.check_pdb_state)

        # TODO: We need a spyder/plugins/python that works with this
        # Update kernels if python path is changed
        # python = self.get_plugin(Plugins.Python)
        # python.sig_python_path_changed.connect(self.update_path)
        self.main.sig_pythonpath_changed.connect(self.update_path)

        self._remove_old_stderr_files()

        # For reference
        # if self.main.historylog is not None:
        #     self.main.historylog.add_history(client.history_filename)
        #     client.append_to_history.connect(
        #         self.main.historylog.append_to_history)

    def update_font(self):
        font = self.get_font()
        rich_font = self.get_font(rich_text=True)
        self.get_widget().update_font(font, rich_font)

    def on_close(self, cancelable=False):
        self.get_widget().mainwindow_close = True
        self.get_widget().close_clients()
        return True

    # def apply_plugin_settings(self, options):
    #     """Apply configuration file's plugin settings"""
    #     font_n = 'plugin_font'
    #     font_o = self.get_font()
    #     help_n = 'connect_to_oi'
    #     help_o = CONF.get('help', 'connect/ipython_console')
    #     color_scheme_n = 'color_scheme_name'
    #     color_scheme_o = CONF.get('appearance', 'selected')
    #     show_time_n = 'show_elapsed_time'
    #     show_time_o = self.get_option(show_time_n)
    #     reset_namespace_n = 'show_reset_namespace_warning'
    #     reset_namespace_o = self.get_option(reset_namespace_n)
    #     ask_before_restart_n = 'ask_before_restart'
    #     ask_before_restart_o = self.get_option(ask_before_restart_n)
    #     for client in self.clients:
    #         control = client.get_control()
    #         if font_n in options:
    #             client.set_font(font_o)
    #         if help_n in options and control is not None:
    #             control.set_help_enabled(help_o)
    #         if color_scheme_n in options:
    #             client.set_color_scheme(color_scheme_o)
    #         if show_time_n in options:
    #             client.show_time_action.setChecked(show_time_o)
    #             client.set_elapsed_time_visible(show_time_o)
    #         if reset_namespace_n in options:
    #             client.reset_warning = reset_namespace_o
    #         if ask_before_restart_n in options:
    #             client.ask_before_restart = ask_before_restart_o

    def on_mainwindow_visible(self):
        self.get_widget().create_new_client(give_focus=False)

    # --- Private methods
    # ------------------------------------------------------------------------
    def _remove_old_stderr_files(self):
        """
        Remove stderr files left by previous Spyder instances.

        This is only required on Windows because we can't
        clean up stderr files while Spyder is running on it.
        """
        if os.name == 'nt':
            tmpdir = get_temp_dir()
            for fname in os.listdir(tmpdir):
                if os.path.splitext(fname)[1] == '.stderr':
                    try:
                        os.remove(os.path.join(tmpdir, fname))
                    except Exception:
                        pass

    # --- API
    # ------------------------------------------------------------------------
    def update_path(self, a, b):
        self.get_widget().update_path(a, b)

    def update_working_directory(self):
        self.get_widget().update_working_directory()

    # Debugging
    def debug_cell(self, code, cell_name, filename, run_cell_copy):
        self.get_widget().debug_cell(code, cell_name, filename, run_cell_copy)

    def check_pdb_state(self):
        self.get_widget().check_pdb_state()

    def get_pdb_state(self):
        self.get_widget().get_pdb_state()

    def get_pdb_last_step(self):
        self.get_widget().get_pdb_last_step()

    def set_spyder_breakpoints(self):
        # TODO: This is needed since the config is not read directly anymore
        # these changes need to be applied and propagated.
        self.apply_conf(["breakpoints"])
        self.get_widget().set_spyder_breakpoints()

    # --- Shellwidget
    def get_current_shellwidget(self):
        return self.get_widget().get_current_shellwidget()

    # --- Kernels
    def reset_kernel(self):
        """FIXME:"""
        self.get_widget().reset_kernel()

    def restart_kernel(self):
        self.get_widget().restart_kernel()

    # --- Clients
    def get_clients(self):
        return self.get_widget().get_clients()

    def get_current_client(self):
        return self.get_widget().get_current_client()

    def get_related_clients(self, client):
        return self.get_widget().get_related_clients(client)

    def create_new_client(self, give_focus=True, filename='', is_cython=False,
                          is_pylab=False, is_sympy=False, given_name=None):
        self.get_widget().create_new_client(
            give_focus=give_focus,
            filename=filename,
            is_cython=is_cython,
            is_pylab=is_pylab,
            is_sympy=is_sympy,
            given_name=given_name,
        )

    def create_client_for_file(self, filename, is_cython=False):
        self.get_widget().create_client_for_file(
            filename, is_cython=is_cython)

    def create_client_from_path(self, path):
        """
        Create a new console with `path` set as the current working directory.

        Parameters
        ----------
        path: str
            Path to use as working directory in new console.
        """
        self.get_widget().create_client_from_path(path)

    def close_client(self, index=None, client=None, force=False):
        self.get_widget().close_client(index=index, client=client,
                                       force=force)

    def set_current_client_working_directory(self, directory):
        self.get_widget().set_current_client_working_directory(directory)

    # --- Help
    # FIXME: These methods probably belong directly in the Help plugin.
    def show_intro(self):
        self.get_widget().show_intro()

    def show_quickref(self):
        self.get_widget().show_quickref()

    def show_guiref(self):
        self.get_widget().show_guiref()

    # --- Run
    def run_script(self, filename, wdir, args, debug, post_mortem,
                   current_client, clear_variables, console_namespace):
        self.get_widget().run_script(filename, wdir, args, debug, post_mortem,
                                     current_client, clear_variables,
                                     console_namespace)

    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 function='runcell'):
        self.get_widget().run_cell(
            code, cell_name, filename, run_cell_copy, function=function)

    def restart(self):
        self.get_widget().restart()

    def execute_code(self, lines, current_client=True, clear_variables=False):
        self.get_widget().execute_code(lines, current_client=current_client,
                                       clear_variables=clear_variables)

    # --- Python specific
    def update_spyder_python_path(self):
        # FIXME:
        self.set_conf_option('spyder_pythonpath',
                             self.main.get_spyder_pythonpath(), section='main')
