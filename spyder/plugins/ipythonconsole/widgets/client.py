# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Client widget for the IPython Console.

This is the widget used on all its tabs.
"""

# Standard library imports.
import logging
import os
import os.path as osp
from string import Template
import time
import traceback

# Third party imports (qtpy)
from qtpy.QtCore import QUrl, QTimer, Signal, Slot, QThread
from qtpy.QtWidgets import QVBoxLayout, QWidget

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import (
    get_home_dir, get_module_source_path, get_conf_path)
from spyder.utils.icon_manager import ima
from spyder.utils import sourcecode
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.installers import InstallerIPythonKernelError
from spyder.utils.environ import RemoteEnvDialog
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import add_actions, DialogManager
from spyder.plugins.ipythonconsole import SpyderKernelError
from spyder.plugins.ipythonconsole.widgets import ShellWidget
from spyder.widgets.collectionseditor import CollectionsEditor
from spyder.widgets.mixins import SaveHistoryMixin


# Localization and logging
_ = get_translation('spyder')
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------
# Using the same css file from the Help plugin for now. Maybe
# later it'll be a good idea to create a new one.
PLUGINS_PATH = get_module_source_path('spyder', 'plugins')

CSS_PATH = osp.join(PLUGINS_PATH, 'help', 'utils', 'static', 'css')
TEMPLATES_PATH = osp.join(
    PLUGINS_PATH, 'ipythonconsole', 'assets', 'templates')

BLANK = open(osp.join(TEMPLATES_PATH, 'blank.html')).read()
LOADING = open(osp.join(TEMPLATES_PATH, 'loading.html')).read()
KERNEL_ERROR = open(osp.join(TEMPLATES_PATH, 'kernel_error.html')).read()

try:
    time.monotonic  # time.monotonic new in 3.3
except AttributeError:
    time.monotonic = time.time

# ----------------------------------------------------------------------------
# Client widget
# ----------------------------------------------------------------------------
class ClientWidget(QWidget, SaveHistoryMixin, SpyderWidgetMixin):
    """
    Client widget for the IPython Console

    This widget is necessary to handle the interaction between the
    plugin and each shell widget.
    """

    sig_append_to_history_requested = Signal(str, str)
    sig_execution_state_changed = Signal()
    sig_time_label = Signal(str)

    CONF_SECTION = 'ipython_console'
    SEPARATOR = '{0}## ---({1})---'.format(os.linesep*2, time.ctime())
    INITHISTORY = ['# -*- coding: utf-8 -*-',
                   '# *** Spyder Python Console History Log ***', ]

    def __init__(self, parent, id_,
                 config_options,
                 additional_options,
                 interpreter_versions,
                 context_menu_actions=(),
                 menu_actions=None,
                 given_name=None,
                 give_focus=True,
                 options_button=None,
                 handlers={},
                 initial_cwd=None):
        super(ClientWidget, self).__init__(parent)
        SaveHistoryMixin.__init__(self, get_conf_path('history.py'))

        # --- Init attrs
        self.container = parent
        self.id_ = id_
        self.menu_actions = menu_actions
        self.given_name = given_name
        self.initial_cwd = initial_cwd

        # --- Other attrs
        self.kernel_handler = None
        self.hostname = None
        self.show_elapsed_time = self.get_conf('show_elapsed_time')
        self.reset_warning = self.get_conf('show_reset_namespace_warning')
        self.context_menu_actions = context_menu_actions
        self.options_button = options_button
        self.history = []
        self.allow_rename = True
        self.error_text = None
        self.restart_thread = None
        self.give_focus = give_focus

        css_path = self.get_conf('css_path', section='appearance')
        if css_path is None:
            self.css_path = CSS_PATH
        else:
            self.css_path = css_path

        # --- Widgets
        self.shellwidget = ShellWidget(
            config=config_options,
            ipyclient=self,
            additional_options=additional_options,
            interpreter_versions=interpreter_versions,
            handlers=handlers,
            local_kernel=True
        )
        self.infowidget = self.container.infowidget
        self.blank_page = self._create_blank_page()
        self.loading_page = self._create_loading_page()
        # To keep a reference to the page to be displayed
        # in infowidget
        self.info_page = None

        # Elapsed time
        self.t0 = time.monotonic()
        self.timer = QTimer(self)

        # --- Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.shellwidget)
        if self.infowidget is not None:
            self.layout.addWidget(self.infowidget)
        self.setLayout(self.layout)

        # --- Exit function
        self.exit_callback = lambda: self.container.close_client(client=self)

        # --- Dialog manager
        self.dialog_manager = DialogManager()

        # --- Standard files handling
        self.start_successful = False

    def __del__(self):
        """Close threads to avoid segfault."""
        if (self.restart_thread is not None
                and self.restart_thread.isRunning()):
            self.restart_thread.quit()
            self.restart_thread.wait()

    # ----- Private methods ---------------------------------------------------
    def _before_prompt_is_ready(self):
        """Configuration before kernel is connected."""
        self._show_loading_page()
        self.shellwidget.sig_prompt_ready.connect(
            self._when_prompt_is_ready)
        # If remote execution, the loading page should be hidden as well
        self.shellwidget.sig_remote_execute.connect(
            self._when_prompt_is_ready)

    def _when_prompt_is_ready(self):
        """Configuration after the prompt is shown."""
        if self.error_text:
            # an error occured during startup, but after the prompt was sent
            return
        self.start_successful = True

        # To hide the loading page
        self._hide_loading_page()

        # Show possible errors when setting Matplotlib backend
        self._show_mpl_backend_errors()

        # To show if special console is valid
        self._check_special_console_error()

        # Set the initial current working directory in the kernel
        self._set_initial_cwd_in_kernel()

        self.shellwidget.sig_prompt_ready.disconnect(
            self._when_prompt_is_ready)
        self.shellwidget.sig_remote_execute.disconnect(
            self._when_prompt_is_ready)

        # It's necessary to do this at this point to avoid giving
        # focus to _control at startup.
        self._connect_control_signals()

        if self.give_focus:
            self.shellwidget._control.setFocus()

    def _create_loading_page(self):
        """Create html page to show while the kernel is starting"""
        loading_template = Template(LOADING)
        loading_img = get_image_path('loading_sprites')
        if os.name == 'nt':
            loading_img = loading_img.replace('\\', '/')
        message = _("Connecting to kernel...")
        page = loading_template.substitute(css_path=self.css_path,
                                           loading_img=loading_img,
                                           message=message)
        return page

    def _create_blank_page(self):
        """Create html page to show while the kernel is starting"""
        loading_template = Template(BLANK)
        page = loading_template.substitute(css_path=self.css_path)
        return page

    def _show_loading_page(self):
        """Show animation while the kernel is loading."""
        if self.infowidget is not None:
            self.shellwidget.hide()
            self.infowidget.show()
            self.info_page = self.loading_page
            self.set_info_page()

    def _hide_loading_page(self):
        """Hide animation shown while the kernel is loading."""
        if self.infowidget is not None:
            self.infowidget.hide()
            self.info_page = self.blank_page
            self.set_info_page()
        self.shellwidget.show()

    def _show_mpl_backend_errors(self):
        """
        Show possible errors when setting the selected Matplotlib backend.
        """
        if self.shellwidget.is_spyder_kernel:
            self.shellwidget.call_kernel().show_mpl_backend_errors()

    def _check_special_console_error(self):
        """Check if the dependecies for special consoles are available."""
        self.shellwidget.call_kernel(
            callback=self._show_special_console_error
            ).is_special_kernel_valid()

    def _show_special_console_error(self, missing_dependency):
        if missing_dependency is not None:
            error_message = _(
                "Your Python environment or installation doesn't have the "
                "<tt>{missing_dependency}</tt> module installed or it "
                "occurred a problem importing it. Due to that, it is not "
                "possible for Spyder to create this special console for "
                "you."
            ).format(missing_dependency=missing_dependency)

            self.show_kernel_error(error_message)

    def _abort_kernel_restart(self):
        """
        Abort kernel restart if there are errors while starting it.

        We also ignore errors about comms, which are irrelevant.
        """
        if self.start_successful:
            return False
        return bool(self.error_text)

    def _connect_control_signals(self):
        """Connect signals of control widgets."""
        control = self.shellwidget._control
        page_control = self.shellwidget._page_control

        control.sig_focus_changed.connect(
            self.container.sig_focus_changed)
        page_control.sig_focus_changed.connect(
            self.container.sig_focus_changed)
        control.sig_visibility_changed.connect(
            self.container.refresh_container)
        page_control.sig_visibility_changed.connect(
            self.container.refresh_container)
        page_control.sig_show_find_widget_requested.connect(
            self.container.find_widget.show)

    def _set_initial_cwd_in_kernel(self):
        """Set the initial cwd in the kernel."""
        logger.debug("Setting initial working directory in the kernel")
        cwd_path = get_home_dir()
        project_path = self.container.get_active_project_path()
        emit_cwd_change = True

        # This is for the first client
        if self.id_['int_id'] == '1':
            if self.get_conf(
                'startup/use_project_or_home_directory',
                section='workingdir'
            ):
                cwd_path = get_home_dir()
                if project_path is not None:
                    cwd_path = project_path
            elif self.get_conf(
                'startup/use_fixed_directory',
                section='workingdir'
            ):
                cwd_path = self.get_conf(
                    'startup/fixed_directory',
                    default=get_home_dir(),
                    section='workingdir'
                )
        else:
            # For new clients
            if self.initial_cwd is not None:
                cwd_path = self.initial_cwd
            elif self.get_conf(
                'console/use_project_or_home_directory',
                section='workingdir'
            ):
                cwd_path = get_home_dir()
                if project_path is not None:
                    cwd_path = project_path
            elif self.get_conf('console/use_cwd', section='workingdir'):
                cwd_path = self.container.get_working_directory()
                emit_cwd_change = False
            elif self.get_conf(
                'console/use_fixed_directory',
                section='workingdir'
            ):
                cwd_path = self.get_conf(
                    'console/fixed_directory',
                    default=get_home_dir(),
                    section='workingdir'
                )

        if osp.isdir(cwd_path):
            self.shellwidget.set_cwd(cwd_path, emit_cwd_change=emit_cwd_change)

    # ----- Public API --------------------------------------------------------
    @property
    def connection_file(self):
        if self.kernel_handler is None:
            return None
        return self.kernel_handler.connection_file

    def connect_kernel(self, kernel_handler):
        """Connect kernel to client using our handler."""
        self._before_prompt_is_ready()
        self.kernel_handler = kernel_handler

        # Connect standard streams.
        kernel_handler.sig_stderr.connect(self.print_stderr)
        kernel_handler.sig_stdout.connect(self.print_stdout)
        kernel_handler.sig_fault.connect(self.print_fault)

        # Actually do the connection
        self.shellwidget.connect_kernel(kernel_handler)

    @Slot(str)
    def print_stderr(self, stderr):
        """Print stderr written in PIPE."""
        if not stderr:
            return

        if self.is_benign_error(stderr):
            return

        if self.shellwidget.isHidden():
            error_text = '<tt>%s</tt>' % stderr
            # Avoid printing the same thing again
            if self.error_text != error_text:
                if self.error_text:
                    # Append to error text
                    error_text = self.error_text + error_text
                self.show_kernel_error(error_text)

        if self.shellwidget._starting:
            self.shellwidget.banner = (
                stderr + '\n' + self.shellwidget.banner)
        else:
            self.shellwidget._append_plain_text(
                stderr, before_prompt=True)

    @Slot(str)
    def print_stdout(self, stdout):
        """Print stdout written in PIPE."""
        if not stdout:
            return

        if self.shellwidget._starting:
            self.shellwidget.banner = (
                stdout + '\n' + self.shellwidget.banner)
        else:
            self.shellwidget._append_plain_text(
                stdout, before_prompt=True)

    def connect_shellwidget_signals(self):
        """Configure shellwidget after kernel is connected."""
        # Set exit callback
        self.shellwidget.exit_requested.connect(self.exit_callback)

        # To save history
        self.shellwidget.executing.connect(self.add_to_history)

        # For Mayavi to run correctly
        self.shellwidget.executing.connect(
            self.shellwidget.set_backend_for_mayavi)

        # To update history after execution
        self.shellwidget.executed.connect(self.update_history)

        # To enable the stop button when executing a process
        self.shellwidget.executing.connect(
            self.sig_execution_state_changed)

        # To disable the stop button after execution stopped
        self.shellwidget.executed.connect(
            self.sig_execution_state_changed)

        # To show kernel restarted/died messages
        self.shellwidget.sig_kernel_restarted_message.connect(
            self.kernel_restarted_message)
        self.shellwidget.sig_kernel_died_restarted.connect(
            self._finalise_restart)

        # To correctly change Matplotlib backend interactively
        self.shellwidget.executing.connect(
            self.shellwidget.change_mpl_backend)

        # To show env and sys.path contents
        self.shellwidget.sig_show_syspath.connect(self.show_syspath)
        self.shellwidget.sig_show_env.connect(self.show_env)

        # To sync with working directory toolbar
        self.shellwidget.executed.connect(self.shellwidget.update_cwd)

    def add_to_history(self, command):
        """Add command to history"""
        if self.shellwidget.is_debugging():
            return
        return super(ClientWidget, self).add_to_history(command)

    def is_client_executing(self):
        return (self.shellwidget._executing or
                self.shellwidget.is_waiting_pdb_input())

    @Slot()
    def stop_button_click_handler(self):
        """Method to handle what to do when the stop button is pressed"""
        # Interrupt computations or stop debugging
        if not self.shellwidget.is_waiting_pdb_input():
            self.interrupt_kernel()
        else:
            self.shellwidget.pdb_execute_command('exit')

    def show_kernel_error(self, error):
        """Show kernel initialization errors in infowidget."""
        if isinstance(error, Exception):
            if isinstance(error, SpyderKernelError):
                error = error.args[0]
            else:
                error = _("The error is:<br><br>"
                          "<tt>{}</tt>").format(traceback.format_exc())
        self.error_text = error

        if self.is_benign_error(error):
            return

        InstallerIPythonKernelError(error)

        # Replace end of line chars with <br>
        eol = sourcecode.get_eol_chars(error)
        if eol:
            error = error.replace(eol, '<br>')

        # Don't break lines in hyphens
        # From https://stackoverflow.com/q/7691569/438386
        error = error.replace('-', '&#8209')

        # Create error page
        message = _("An error ocurred while starting the kernel")
        kernel_error_template = Template(KERNEL_ERROR)
        self.info_page = kernel_error_template.substitute(
            css_path=self.css_path,
            message=message,
            error=error)

        # Show error
        if self.infowidget is not None:
            self.set_info_page()
            self.shellwidget.hide()
            self.infowidget.show()

        # Stop shellwidget
        self.shellwidget.shutdown()

    def is_benign_error(self, error):
        """Decide if an error is benign in order to filter it."""
        benign_errors = [
            # Error when switching from the Qt5 backend to the Tk one.
            # See spyder-ide/spyder#17488
            "KeyboardInterrupt caught in kernel",
            "QSocketNotifier: Multiple socket notifiers for same socket",
            # Error when switching from the Tk backend to the Qt5 one.
            # See spyder-ide/spyder#17488
            "Tcl_AsyncDelete async handler deleted by the wrong thread",
            "error in background error handler:",
            "    while executing",
            '"::tcl::Bgerror',
            # Avoid showing this warning because it was up to the user to
            # disable secure writes.
            "WARNING: Insecure writes have been enabled via environment",
            # Old error
            "No such comm",
            # PYDEVD debug warning message. See spyder-ide/spyder#18908
            "Note: Debugging will proceed. "
            "Set PYDEVD_DISABLE_FILE_VALIDATION=1 to disable this validation."
        ]

        return any([err in error for err in benign_errors])

    def get_name(self):
        """Return client name"""
        if self.given_name is None:
            # Name according to host
            if self.hostname is None:
                name = _("Console")
            else:
                name = self.hostname
            # Adding id to name
            client_id = self.id_['int_id'] + u'/' + self.id_['str_id']
            name = name + u' ' + client_id
        elif self.given_name in ["Pylab", "SymPy", "Cython"]:
            client_id = self.id_['int_id'] + u'/' + self.id_['str_id']
            name = self.given_name + u' ' + client_id
        else:
            name = self.given_name + u'/' + self.id_['str_id']
        return name

    def get_control(self):
        """Return the text widget (or similar) to give focus to"""
        # page_control is the widget used for paging
        page_control = self.shellwidget._page_control
        if page_control and page_control.isVisible():
            return page_control
        else:
            return self.shellwidget._control

    def add_actions_to_context_menu(self, menu):
        """Add actions to IPython widget context menu"""
        add_actions(menu, self.context_menu_actions)

        return menu

    def set_font(self, font):
        """Set IPython widget's font"""
        self.shellwidget._control.setFont(font)
        self.shellwidget.font = font

    def set_color_scheme(self, color_scheme, reset=True):
        """Set IPython color scheme."""
        # Needed to handle not initialized kernel_client
        # See spyder-ide/spyder#6996.
        try:
            self.shellwidget.set_color_scheme(color_scheme, reset)
        except AttributeError:
            pass

    def close_client(self, is_last_client):
        """Close the client."""
        # Needed to handle a RuntimeError. See spyder-ide/spyder#5568.
        try:
            # Close client
            self.stop_button_click_handler()
        except RuntimeError:
            pass

        # Disconnect timer needed to update elapsed time
        try:
            self.timer.timeout.disconnect(self.show_time)
        except (RuntimeError, TypeError):
            pass

        self.shutdown(is_last_client)
        self.close()
        self.setParent(None)

    def shutdown(self, is_last_client):
        """Shutdown connection and kernel if needed."""
        self.dialog_manager.close_all()
        if (self.restart_thread is not None
                and self.restart_thread.isRunning()):
            self.restart_thread.finished.disconnect()
            self.restart_thread.quit()
            self.restart_thread.wait()
        shutdown_kernel = (
            is_last_client and not self.shellwidget.is_external_kernel
            and not self.error_text
        )
        self.shellwidget.shutdown(shutdown_kernel)

    def interrupt_kernel(self):
        """Interrupt the associanted Spyder kernel if it's running"""
        # Needed to prevent a crash when a kernel is not running.
        # See spyder-ide/spyder#6299.
        try:
            self.shellwidget.request_interrupt_kernel()
        except RuntimeError:
            pass

    @Slot()
    def restart_kernel(self):
        """
        Restart the associated kernel.

        Took this code from the qtconsole project
        Licensed under the BSD license
        """
        sw = self.shellwidget
        if sw.is_external_kernel:
            sw._append_plain_text(
                _('Cannot restart a kernel not started by Spyder\n'),
                before_prompt=True
            )
            return

        if self.infowidget is not None:
            if self.infowidget.isVisible():
                self.infowidget.hide()

        # Close comm
        sw.spyder_kernel_comm.close()

        if self._abort_kernel_restart():
            return

        # Stop autorestart mechanism
        sw.kernel_manager.stop_restarter()
        sw.kernel_manager.autorestart = False

        # Disconnect the std pipes so errors will not mess with the restart
        self.kernel_handler.disconnect_std_pipes()

        # Reconfigure client before the new kernel is connected again.
        self._before_prompt_is_ready()

        # Create and run restarting thread
        if (
            self.restart_thread is not None
            and self.restart_thread.isRunning()
        ):
            self.restart_thread.finished.disconnect()
            self.restart_thread.quit()
            self.restart_thread.wait()
        self.restart_thread = QThread(None)
        self.restart_thread.run = self._restart_thread_main
        self.restart_thread.error = None
        self.restart_thread.finished.connect(
            lambda: self._finalise_restart(True))
        self.restart_thread.start()

    def _restart_thread_main(self):
        """Restart the kernel in a thread."""
        try:
            self.kernel_handler.restart_kernel()
        except RuntimeError as e:
            self.restart_thread.error = e

    def _finalise_restart(self, reset=False):
        """Finishes the restarting of the kernel."""
        sw = self.shellwidget

        if self._abort_kernel_restart():
            sw.spyder_kernel_comm.remove()
            return

        if self.restart_thread and self.restart_thread.error is not None:
            sw._append_plain_text(
                _('Error restarting kernel: %s\n') % self.restart_thread.error,
                before_prompt=True
            )
        else:
            self.kernel_handler.connect_std_pipes()

            # Reset Pdb state and reopen comm
            sw.reset_kernel_state()

            # Reopen comm
            sw.spyder_kernel_comm.remove()
            try:
                sw.spyder_kernel_comm.open_comm(sw.kernel_client)
            except AttributeError:
                # An error occurred while opening our comm channel.
                # Aborting!
                return

            # Start autorestart mechanism
            sw.kernel_manager.autorestart = True
            sw.kernel_manager.start_restarter()

            if reset:
                sw.reset(clear=True)
            
            self.kernel_handler.poll_fault_text()

            sw._append_html(_("<br>Restarting kernel...<br>"),
                            before_prompt=True)
            sw.insert_horizontal_ruler()

            sw.send_spyder_kernel_configuration()

        self.restart_thread = None
        self.sig_execution_state_changed.emit()
    
    def print_fault(self, fault):
        """Print fault text."""
        self.shellwidget._append_plain_text(
            '\n' + fault, before_prompt=True)

    @Slot(str)
    def kernel_restarted_message(self, msg):
        """Show kernel restarted/died messages."""
        self.shellwidget._append_html("<br>%s<hr><br>" % msg,
                                      before_prompt=False)

    @Slot()
    def enter_array_inline(self):
        """Enter and show the array builder on inline mode."""
        self.shellwidget._control.enter_array_inline()

    @Slot()
    def enter_array_table(self):
        """Enter and show the array builder on table."""
        self.shellwidget._control.enter_array_table()

    @Slot()
    def inspect_object(self):
        """Show how to inspect an object with our Help plugin"""
        self.shellwidget._control.inspect_current_object()

    @Slot()
    def clear_line(self):
        """Clear a console line"""
        self.shellwidget._keyboard_quit()

    @Slot()
    def clear_console(self):
        """Clear the whole console"""
        self.shellwidget.clear_console()

    @Slot()
    def reset_namespace(self):
        """Resets the namespace by removing all names defined by the user"""
        self.shellwidget.reset_namespace(warning=self.reset_warning,
                                         message=True)

    def update_history(self):
        self.history = self.shellwidget._history

    @Slot(object)
    def show_syspath(self, syspath):
        """Show sys.path contents."""
        if syspath is not None:
            editor = CollectionsEditor(self)
            editor.setup(syspath, title="sys.path contents", readonly=True,
                         icon=ima.icon('syspath'))
            self.dialog_manager.show(editor)
        else:
            return

    @Slot(object)
    def show_env(self, env):
        """Show environment variables."""
        self.dialog_manager.show(RemoteEnvDialog(env, parent=self))

    def show_time(self, end=False):
        """Text to show in time_label."""

        elapsed_time = time.monotonic() - self.t0
        # System time changed to past date, so reset start.
        if elapsed_time < 0:
            self.t0 = time.monotonic()
            elapsed_time = 0
        if elapsed_time > 24 * 3600:  # More than a day...!
            fmt = "%d %H:%M:%S"
        else:
            fmt = "%H:%M:%S"
        if end:
            color = QStylePalette.COLOR_TEXT_3
        else:
            color = QStylePalette.COLOR_ACCENT_4
        text = "<span style=\'color: %s\'><b>%s" \
               "</b></span>" % (color,
                                time.strftime(fmt, time.gmtime(elapsed_time)))
        if self.show_elapsed_time:
            self.sig_time_label.emit(text)
        else:
            self.sig_time_label.emit("")

    @Slot(bool)
    def set_show_elapsed_time(self, state):
        """Slot to show/hide elapsed time label."""
        self.show_elapsed_time = state

    def set_info_page(self):
        """Set current info_page."""
        if self.infowidget is not None and self.info_page is not None:
            self.infowidget.setHtml(
                self.info_page,
                QUrl.fromLocalFile(self.css_path)
            )
