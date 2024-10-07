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
import functools
import logging
import os
import os.path as osp
from string import Template
import time
import traceback

# Third party imports (qtpy)
from qtpy.QtCore import QUrl, QTimer, Signal, Slot
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import (
    get_home_dir, get_module_source_path, get_conf_path)
from spyder.utils.icon_manager import ima
from spyder.utils import sourcecode
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.installers import InstallerIPythonKernelError
from spyder.utils.environ import RemoteEnvDialog
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import DialogManager
from spyder.plugins.ipythonconsole import SpyderKernelError
from spyder.plugins.ipythonconsole.utils.kernel_handler import (
    KernelConnectionState)
from spyder.plugins.ipythonconsole.widgets import ShellWidget
from spyder.widgets.collectionseditor import CollectionsEditor
from spyder.widgets.mixins import SaveHistoryMixin


# Logging
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

    # Signals for remote kernels
    sig_shutdown_kernel_requested = Signal(str, str)
    sig_interrupt_kernel_requested = Signal(str, str)
    sig_restart_kernel_requested = Signal()
    sig_kernel_died = Signal()

    CONF_SECTION = 'ipython_console'
    SEPARATOR = '{0}## ---({1})---'.format(os.linesep*2, time.ctime())
    INITHISTORY = ['# -*- coding: utf-8 -*-',
                   '# *** Spyder Python Console History Log ***', ]

    def __init__(
        self,
        parent,
        id_,
        config_options,
        additional_options,
        menu_actions=None,
        given_name=None,
        give_focus=True,
        options_button=None,
        handlers=None,
        initial_cwd=None,
        forcing_custom_interpreter=False,
        special_kernel=None,
        server_id=None,
        can_close=True,
    ):
        super(ClientWidget, self).__init__(parent)
        SaveHistoryMixin.__init__(self, get_conf_path('history.py'))

        # --- Init attrs
        self.container = parent
        self.id_ = id_
        self.menu_actions = menu_actions
        self.given_name = given_name
        self.initial_cwd = initial_cwd
        self.forcing_custom_interpreter = forcing_custom_interpreter
        self.server_id = server_id
        self.can_close = can_close

        # --- Other attrs
        self.kernel_handler = None
        self.hostname = None
        self.show_elapsed_time = self.get_conf('show_elapsed_time')
        self.reset_warning = self.get_conf('show_reset_namespace_warning')
        self.options_button = options_button
        self.history = []
        self.allow_rename = True
        self.error_text = None
        self.give_focus = give_focus
        self.kernel_id = None
        self.__on_close = lambda: None

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
            handlers=handlers,
            local_kernel=True,
            special_kernel=special_kernel,
            server_id=server_id,
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

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _when_kernel_is_ready(self):
        """
        Configuration after the prompt is shown.

        Notes
        -----
        This is not called on restart. For kernel setup you need to use
        ShellWidget.handle_kernel_is_ready.
        """
        if self.kernel_handler.connection_state not in [
                KernelConnectionState.SpyderKernelReady,
                KernelConnectionState.IpykernelReady]:
            # The kernel is not ready
            return

        self.kernel_handler.sig_kernel_is_ready.disconnect(
            self._when_kernel_is_ready)

        # To hide the loading page
        self._hide_loading_page()

        # Set the initial current working directory in the kernel
        self._set_initial_cwd_in_kernel()

        # Notes:
        # 1. It's necessary to do this at this point to avoid giving focus to
        #    _control at startup.
        # 2. The try except is needed to avoid some errors in our tests.
        try:
            self._connect_control_signals()
        except RuntimeError:
            pass

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

    # ---- Public API
    # -------------------------------------------------------------------------
    @property
    def connection_file(self):
        if self.kernel_handler is None:
            return None
        return self.kernel_handler.connection_file

    def connect_kernel(self, kernel_handler, first_connect=True):
        """Connect kernel to client using our handler."""
        self.kernel_handler = kernel_handler

        # Connect standard streams.
        kernel_handler.sig_stderr.connect(self.print_stderr)
        kernel_handler.sig_stdout.connect(self.print_stdout)
        kernel_handler.sig_fault.connect(self.print_fault)
        kernel_handler.sig_kernel_is_ready.connect(
            self._when_kernel_is_ready)

        if self.is_remote():
            self._hide_loading_page()
        else:
            self._show_loading_page()

        # Actually do the connection
        self.shellwidget.connect_kernel(kernel_handler, first_connect)

    def disconnect_kernel(self, shutdown_kernel):
        """Disconnect from current kernel."""
        kernel_handler = getattr(self, "kernel_handler", None)
        if not kernel_handler:
            return

        kernel_handler.sig_stderr.disconnect(self.print_stderr)
        kernel_handler.sig_stdout.disconnect(self.print_stdout)
        kernel_handler.sig_fault.disconnect(self.print_fault)

        self.shellwidget.disconnect_kernel(shutdown_kernel)
        self.kernel_handler = None

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

        # To correctly change Matplotlib backend interactively
        self.shellwidget.executing.connect(
            self.shellwidget.change_mpl_backend)

        # To show env and sys.path contents
        self.shellwidget.sig_show_syspath.connect(self.show_syspath)
        self.shellwidget.sig_show_env.connect(self.show_env)

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
        message = _("An error occurred while starting the kernel")
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

        # Inform other plugins that the shell failed to start
        self.shellwidget.sig_shellwidget_errored.emit(self.shellwidget)

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
            "Set PYDEVD_DISABLE_FILE_VALIDATION=1 to disable this validation.",
            # Argument not expected error. See spyder-ide/spyder#19298
            "The following argument was not expected",
            # Avoid showing error for kernel restarts after kernel dies when
            # using an external interpreter
            "conda.cli.main_run",
            # Warning when debugpy is not available because it's an optional
            # dependency of IPykernel.
            # See spyder-ide/spyder#21900
            "debugpy_stream undefined, debugging will not be enabled",
            # Harmless warning from OpenCL on Windows.
            # See spyder-ide/spyder#22551
            "The system cannot find the path specified",
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
        elif (self.given_name in ["Pylab", "SymPy", "Cython"] or
              self.forcing_custom_interpreter):
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

    def close_client(self, is_last_client, close_console=False):
        """Close the client."""
        self.__on_close = lambda: None
        debugging = False

        # Needed to handle a RuntimeError. See spyder-ide/spyder#5568.
        try:
            # This is required after spyder-ide/spyder#21788 to prevent freezes
            # when closing Spyder. That happens not only when a console is in
            # debugging mode before closing, but also when a kernel restart is
            # requested while debugging.
            if self.shellwidget.is_debugging():
                debugging = True
                self.__on_close = functools.partial(
                    self.finish_close,
                    is_last_client,
                    close_console,
                    debugging
                )
                self.shellwidget.sig_prompt_ready.connect(self.__on_close)
                self.shellwidget.stop_debugging()
            else:
                self.interrupt_kernel()
        except RuntimeError:
            pass

        if not debugging:
            self.finish_close(is_last_client, close_console, debugging)

    def finish_close(self, is_last_client, close_console, debugging):
        """Actions to take to finish closing the client."""
        # Disconnect timer needed to update elapsed time and this slot in case
        # it was connected.
        try:
            self.shellwidget.sig_prompt_ready.disconnect(self.__on_close)
            self.timer.timeout.disconnect(self.show_time)
        except (RuntimeError, TypeError):
            pass

        # This is a hack to prevent segfaults when closing Spyder and the
        # client was debugging before doing it.
        # It's a side effect of spyder-ide/spyder#21788
        if debugging and close_console:
            for __ in range(3):
                time.sleep(0.08)
                QApplication.processEvents()

        self.shutdown(is_last_client, close_console=close_console)

        # Prevent errors in our tests
        try:
            self.close()
            self.setParent(None)
        except RuntimeError:
            pass

    def shutdown(self, is_last_client, close_console=False):
        """Shutdown connection and kernel if needed."""
        self.dialog_manager.close_all()
        shutdown_kernel = (
            is_last_client
            and (not self.shellwidget.is_external_kernel or self.is_remote())
            and not self.error_text
        )

        if self.is_remote() and shutdown_kernel and not close_console:
            # This signal allows to shutdown a remote kernel when a client is
            # closed. And we don't emit it when the console is being closed
            # because it's not necessary in that case.
            self.sig_shutdown_kernel_requested.emit(
                self.server_id, self.kernel_id
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

    def replace_kernel(self, kernel_handler, shutdown_kernel, clear=True):
        """
        Replace kernel by disconnecting from the current one and connecting to
        another kernel, which is equivalent to a restart.
        """
        # Connect kernel to client
        self.disconnect_kernel(shutdown_kernel)
        self.connect_kernel(kernel_handler, first_connect=False)

        # Reset shellwidget and print restart message
        self.shellwidget.reset(clear=clear)
        self.shellwidget._kernel_restarted_message(died=False)

    def is_kernel_active(self):
        """Check if the kernel is active."""
        return (
            self.kernel_handler is not None
            and self.kernel_handler.connection_state
            in [
                KernelConnectionState.SpyderKernelReady,
                KernelConnectionState.IpykernelReady,
            ]
        )

    def print_fault(self, fault):
        """Print fault text."""
        self.shellwidget._append_plain_text('\n' + fault, before_prompt=True)

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
            color = SpyderPalette.COLOR_TEXT_3
        else:
            color = SpyderPalette.COLOR_ACCENT_4
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
            self.sig_execution_state_changed.emit()

    # ---- For remote clients
    # -------------------------------------------------------------------------
    def is_remote(self):
        """Check if this client is connected to a remote server."""
        return self.server_id is not None

    def handle_remote_kernel_restarted(self, clear=True):
        """Handle restarts for remote kernels."""
        # Reset shellwidget and print restart message
        self.shellwidget.reset(clear=clear)

    def show_restarting_message(self, died=False):
        self.shellwidget._kernel_restarted_message(died=died)

    def remote_kernel_restarted_failure_message(
        self, error=None, shutdown=False
    ):
        """Show message when the kernel failed to be restarted."""

        msg = _("It was not possible to restart the kernel")

        if error is None:
            error_html = f"<br>{msg}<br>"
        else:
            if isinstance(error, SpyderKernelError):
                error = error.args[0]
            elif isinstance(error, Exception):
                error = _("The error is:<br><br>" "<tt>{}</tt>").format(
                    traceback.format_exc()
                )

            # Replace end of line chars with <br>
            eol = sourcecode.get_eol_chars(error)
            if eol:
                error = error.replace(eol, '<br>')

            # Don't break lines in hyphens
            # From https://stackoverflow.com/q/7691569/438386
            error = error.replace('-', '&#8209')

            # Create error page
            kernel_error_template = Template(KERNEL_ERROR)
            error_html = kernel_error_template.substitute(
                css_path=self.css_path,
                message=msg,
                error=error)

        self.shellwidget._append_html(error_html, before_prompt=False)
        self.shellwidget.insert_horizontal_ruler()

        if shutdown:
            self.shutdown(is_last_client=False, close_console=False)
