# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Shell Widget for the IPython Console
"""

# Standard library imports
import os
import uuid
from textwrap import dedent

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.manager import CONF
from spyder.config.base import _
from spyder.config.gui import config_shortcut
from spyder.py3compat import to_text_string
from spyder.utils import programs, encoding
from spyder.utils import syntaxhighlighters as sh
from spyder.plugins.ipythonconsole.utils.style import create_qss_style, create_style_class
from spyder.widgets.helperwidgets import MessageCheckBox
from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm
from spyder.plugins.ipythonconsole.widgets import (
        ControlWidget, DebuggingWidget, FigureBrowserWidget,
        HelpWidget, NamepaceBrowserWidget, PageControlWidget)


class ShellWidget(NamepaceBrowserWidget, HelpWidget, DebuggingWidget,
                  FigureBrowserWidget):
    """
    Shell widget for the IPython Console

    This is the widget in charge of executing code
    """
    # NOTE: Signals can't be assigned separately to each widget
    #       That's why we define all needed signals here.

    # For NamepaceBrowserWidget
    sig_show_syspath = Signal(object)
    sig_show_env = Signal(object)

    # For FigureBrowserWidget
    sig_new_inline_figure = Signal(object, str)

    # For DebuggingWidget
    sig_pdb_step = Signal(str, int)

    # For ShellWidget
    focus_changed = Signal()
    new_client = Signal()
    sig_is_spykernel = Signal(object)
    sig_kernel_restarted = Signal(str)
    sig_prompt_ready = Signal()

    # For global working directory
    sig_change_cwd = Signal(str)

    # For printing internal errors
    sig_exception_occurred = Signal(str, bool)

    def __init__(self, ipyclient, additional_options, interpreter_versions,
                 external_kernel, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = ControlWidget
        self.custom_page_control = PageControlWidget
        self.custom_edit = True
        self.spyder_kernel_comm = KernelComm()
        self.spyder_kernel_comm.sig_exception_occurred.connect(
            self.sig_exception_occurred)
        super(ShellWidget, self).__init__(*args, **kw)

        self.ipyclient = ipyclient
        self.additional_options = additional_options
        self.interpreter_versions = interpreter_versions
        self.external_kernel = external_kernel
        self._cwd = ''

        # Keyboard shortcuts
        self.shortcuts = self.create_shortcuts()

        # Set the color of the matched parentheses here since the qtconsole
        # uses a hard-coded value that is not modified when the color scheme is
        # set in the qtconsole constructor. See spyder-ide/spyder#4806.
        self.set_bracket_matcher_color_scheme(self.syntax_style)

        self.kernel_manager = None
        self.kernel_client = None
        handlers = {
            'pdb_state': self.set_pdb_state,
            'pdb_continue': self.pdb_continue,
            'get_pdb_settings': self.handle_get_pdb_settings,
            'run_cell': self.handle_run_cell,
            'cell_count': self.handle_cell_count,
            'current_filename': self.handle_current_filename,
            'get_file_code': self.handle_get_file_code,
            'set_debug_state': self.handle_debug_state,
            'update_syspath': self.update_syspath,
        }
        for request_id in handlers:
            self.spyder_kernel_comm.register_call_handler(
                request_id, handlers[request_id])

    def call_kernel(self, interrupt=False, blocking=False, callback=None,
                    timeout=None):
        """Send message to spyder."""
        return self.spyder_kernel_comm.remote_call(
            interrupt=interrupt,
            blocking=blocking,
            callback=callback,
            timeout=timeout
        )

    def set_kernel_client_and_manager(self, kernel_client, kernel_manager):
        """Set the kernel client and manager"""
        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client
        self.spyder_kernel_comm.open_comm(kernel_client)

        # Redefine the complete method to work while debugging.
        self.redefine_complete_for_dbg(self.kernel_client)

    #---- Public API ----------------------------------------------------------
    def set_exit_callback(self):
        """Set exit callback for this shell."""
        self.exit_requested.connect(self.ipyclient.exit_callback)

    def is_running(self):
        if self.kernel_client is not None and \
          self.kernel_client.channels_running:
            return True
        else:
            return False

    def is_spyder_kernel(self):
        """Determine if the kernel is from Spyder."""
        code = u"getattr(get_ipython().kernel, 'set_value', False)"
        if self._reading:
            return
        else:
            self.silent_exec_method(code)

    def set_cwd(self, dirname):
        """Set shell current working directory."""
        # Replace single for double backslashes on Windows
        if os.name == 'nt':
            dirname = dirname.replace(u"\\", u"\\\\")

        if self.ipyclient.hostname is None:
            self.call_kernel(interrupt=True).set_cwd(dirname)
            self._cwd = dirname

    def update_cwd(self):
        """Update current working directory.

        Retrieve the cwd and emit a signal connected to the working directory
        widget. (see: handle_exec_method())
        """
        if self.kernel_client is None:
            return
        self.call_kernel(callback=self.remote_set_cwd).get_cwd()

    def remote_set_cwd(self, cwd):
        """Get current working directory from kernel."""
        self._cwd = cwd
        self.sig_change_cwd.emit(self._cwd)

    def set_bracket_matcher_color_scheme(self, color_scheme):
        """Set color scheme for matched parentheses."""
        bsh = sh.BaseSH(parent=self, color_scheme=color_scheme)
        mpcolor = bsh.get_matched_p_color()
        self._bracket_matcher.format.setBackground(mpcolor)

    def set_color_scheme(self, color_scheme, reset=True):
        """Set color scheme of the shell."""
        self.set_bracket_matcher_color_scheme(color_scheme)
        self.style_sheet, dark_color = create_qss_style(color_scheme)
        self.syntax_style = color_scheme
        self._style_sheet_changed()
        self._syntax_style_changed()
        if reset:
            self.reset(clear=True)
        if not dark_color:
            # Needed to change the colors of tracebacks
            self.silent_execute("%colors linux")
            self.call_kernel(
                interrupt=True,
                blocking=False).set_sympy_forecolor(background_color='dark')
        else:
            self.silent_execute("%colors lightbg")
            self.call_kernel(
                interrupt=True,
                blocking=False).set_sympy_forecolor(background_color='light')

    def update_syspath(self, path_dict, new_path_dict):
        """Update sys.path contents on kernel."""
        self.call_kernel(
            interrupt=True,
            blocking=False).update_syspath(path_dict, new_path_dict)

    def request_syspath(self):
        """Ask the kernel for sys.path contents."""
        self.call_kernel(
            interrupt=True, callback=self.sig_show_syspath.emit).get_syspath()

    def request_env(self):
        """Ask the kernel for environment variables."""
        self.call_kernel(
            interrupt=True, callback=self.sig_show_env.emit).get_env()

    # --- To handle the banner
    def long_banner(self):
        """Banner for clients with additional content."""
        # Default banner
        py_ver = self.interpreter_versions['python_version'].split('\n')[0]
        ipy_ver = self.interpreter_versions['ipython_version']

        banner_parts = [
            'Python %s\n' % py_ver,
            'Type "copyright", "credits" or "license" for more information.\n\n',
            'IPython %s -- An enhanced Interactive Python.\n' % ipy_ver
        ]
        banner = ''.join(banner_parts)

        # Pylab additions
        pylab_o = self.additional_options['pylab']
        autoload_pylab_o = self.additional_options['autoload_pylab']
        mpl_installed = programs.is_module_installed('matplotlib')
        if mpl_installed and (pylab_o and autoload_pylab_o):
            pylab_message = ("\nPopulating the interactive namespace from "
                             "numpy and matplotlib\n")
            banner = banner + pylab_message

        # Sympy additions
        sympy_o = self.additional_options['sympy']
        if sympy_o:
            lines = """
These commands were executed:
>>> from __future__ import division
>>> from sympy import *
>>> x, y, z, t = symbols('x y z t')
>>> k, m, n = symbols('k m n', integer=True)
>>> f, g, h = symbols('f g h', cls=Function)
"""
            banner = banner + lines
        if (pylab_o and sympy_o):
            lines = """
Warning: pylab (numpy and matplotlib) and symbolic math (sympy) are both
enabled at the same time. Some pylab functions are going to be overrided by
the sympy module (e.g. plot)
"""
            banner = banner + lines

        return banner

    def short_banner(self):
        """Short banner with Python and IPython versions only."""
        py_ver = self.interpreter_versions['python_version'].split(' ')[0]
        ipy_ver = self.interpreter_versions['ipython_version']
        banner = 'Python %s -- IPython %s' % (py_ver, ipy_ver)
        return banner

    # --- To define additional shortcuts
    def clear_console(self):
        if self.is_waiting_pdb_input():
            self.dbg_exec_magic('clear')
        else:
            self.execute("%clear")
        # Stop reading as any input has been removed.
        self._reading = False

    def _reset_namespace(self):
        warning = CONF.get('ipython_console', 'show_reset_namespace_warning')
        self.reset_namespace(warning=warning)

    def reset_namespace(self, warning=False, message=False):
        """Reset the namespace by removing all names defined by the user."""
        reset_str = _("Remove all variables")
        warn_str = _("All user-defined variables will be removed. "
                     "Are you sure you want to proceed?")
        # This is necessary to make resetting variables work in external
        # kernels.
        # See spyder-ide/spyder#9505.
        try:
            kernel_env = self.kernel_manager._kernel_spec.env
        except AttributeError:
            kernel_env = {}

        if warning:
            box = MessageCheckBox(icon=QMessageBox.Warning, parent=self)
            box.setWindowTitle(reset_str)
            box.set_checkbox_text(_("Don't show again."))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.Yes)

            box.set_checked(False)
            box.set_check_visible(True)
            box.setText(warn_str)

            answer = box.exec_()

            # Update checkbox based on user interaction
            CONF.set('ipython_console', 'show_reset_namespace_warning',
                     not box.is_checked())
            self.ipyclient.reset_warning = not box.is_checked()

            if answer != QMessageBox.Yes:
                return

        try:
            if self.is_waiting_pdb_input():
                self.dbg_exec_magic('reset', '-f')
            else:
                if message:
                    self.reset()
                    self._append_html(_("<br><br>Removing all variables..."
                                        "\n<hr>"),
                                      before_prompt=False)
                self.silent_execute("%reset -f")
                if kernel_env.get('SPY_AUTOLOAD_PYLAB_O') == 'True':
                    self.silent_execute("from pylab import *")
                if kernel_env.get('SPY_SYMPY_O') == 'True':
                    sympy_init = """
                        from __future__ import division
                        from sympy import *
                        x, y, z, t = symbols('x y z t')
                        k, m, n = symbols('k m n', integer=True)
                        f, g, h = symbols('f g h', cls=Function)
                        init_printing()"""
                    self.silent_execute(dedent(sympy_init))
                if kernel_env.get('SPY_RUN_CYTHON') == 'True':
                    self.silent_execute("%reload_ext Cython")
                self.refresh_namespacebrowser()

                if not self.external_kernel:
                    self.call_kernel().close_all_mpl_figures()
        except AttributeError:
            pass

    def create_shortcuts(self):
        """Create shortcuts for ipyconsole."""
        inspect = config_shortcut(self._control.inspect_current_object,
                                  context='Console',
                                  name='Inspect current object', parent=self)
        clear_console = config_shortcut(self.clear_console, context='Console',
                                        name='Clear shell', parent=self)
        restart_kernel = config_shortcut(self.ipyclient.restart_kernel,
                                         context='ipython_console',
                                         name='Restart kernel', parent=self)
        new_tab = config_shortcut(lambda: self.new_client.emit(),
                                  context='ipython_console', name='new tab',
                                  parent=self)
        reset_namespace = config_shortcut(lambda: self._reset_namespace(),
                                          context='ipython_console',
                                          name='reset namespace', parent=self)
        array_inline = config_shortcut(self._control.enter_array_inline,
                                       context='array_builder',
                                       name='enter array inline', parent=self)
        array_table = config_shortcut(self._control.enter_array_table,
                                      context='array_builder',
                                      name='enter array table', parent=self)
        clear_line = config_shortcut(self.ipyclient.clear_line,
                                     context='console', name='clear line',
                                     parent=self)

        return [inspect, clear_console, restart_kernel, new_tab,
                reset_namespace, array_inline, array_table, clear_line]

    # --- To communicate with the kernel
    def silent_execute(self, code):
        """Execute code in the kernel without increasing the prompt"""
        try:
            self.kernel_client.execute(to_text_string(code), silent=True)
        except AttributeError:
            pass

    def silent_exec_method(self, code):
        """Silently execute a kernel method and save its reply

        The methods passed here **don't** involve getting the value
        of a variable but instead replies that can be handled by
        ast.literal_eval.

        To get a value see `get_value`

        Parameters
        ----------
        code : string
            Code that contains the kernel method as part of its
            string

        See Also
        --------
        handle_exec_method : Method that deals with the reply

        Note
        ----
        This is based on the _silent_exec_callback method of
        RichJupyterWidget. Therefore this is licensed BSD
        """
        # Generate uuid, which would be used as an indication of whether or
        # not the unique request originated from here
        local_uuid = to_text_string(uuid.uuid1())
        code = to_text_string(code)
        if self.kernel_client is None:
            return

        msg_id = self.kernel_client.execute('', silent=True,
                                            user_expressions={ local_uuid:code })
        self._kernel_methods[local_uuid] = code
        self._request_info['execute'][msg_id] = self._ExecutionRequest(msg_id,
                                                          'silent_exec_method')

    def handle_exec_method(self, msg):
        """
        Handle data returned by silent executions of kernel methods

        This is based on the _handle_exec_callback of RichJupyterWidget.
        Therefore this is licensed BSD.
        """
        user_exp = msg['content'].get('user_expressions')
        if not user_exp:
            return
        for expression in user_exp:
            if expression in self._kernel_methods:
                # Process kernel reply
                method = self._kernel_methods[expression]
                reply = user_exp[expression]
                data = reply.get('data')
                if 'getattr' in method:
                    if data is not None and 'text/plain' in data:
                        is_spyder_kernel = data['text/plain']
                        if 'SpyderKernel' in is_spyder_kernel:
                            self.sig_is_spykernel.emit(self)

                # Remove method after being processed
                self._kernel_methods.pop(expression)

    def set_backend_for_mayavi(self, command):
        """
        Mayavi plots require the Qt backend, so we try to detect if one is
        generated to change backends
        """
        calling_mayavi = False
        lines = command.splitlines()
        for l in lines:
            if not l.startswith('#'):
                if 'import mayavi' in l or 'from mayavi' in l:
                    calling_mayavi = True
                    break
        if calling_mayavi:
            message = _("Changing backend to Qt for Mayavi")
            self._append_plain_text(message + '\n')
            self.silent_execute("%gui inline\n%gui qt")

    def change_mpl_backend(self, command):
        """
        If the user is trying to change Matplotlib backends with
        %matplotlib, send the same command again to the kernel to
        correctly change it.

        Fixes spyder-ide/spyder#4002.
        """
        if command.startswith('%matplotlib') and \
          len(command.splitlines()) == 1:
            if not 'inline' in command:
                self.silent_execute(command)

    # ---- Spyder-kernels methods -------------------------------------------
    def get_editor(self, filename):
        """Get editor for filename and set it as the current editor."""
        editorstack = self.get_editorstack()
        if editorstack is None:
            return None

        if not filename:
            return None

        index = editorstack.has_filename(filename)
        if index is None:
            return None

        editor = editorstack.data[index].editor
        editorstack.set_stack_index(index)
        return editor

    def get_editorstack(self):
        """Get the current editorstack."""
        plugin = self.ipyclient.plugin
        if plugin.main.editor is not None:
            editor = plugin.main.editor
            return editor.get_current_editorstack()
        raise RuntimeError('No editorstack found.')

    def handle_get_file_code(self, filename):
        """
        Return the bytes that compose the file.

        Bytes are returned instead of str to support non utf-8 files.
        """
        editorstack = self.get_editorstack()
        if CONF.get('editor', 'save_all_before_run', True):
            editorstack.save_all(save_new_files=False)
        editor = self.get_editor(filename)

        if editor is None:
            # Load it from file instead
            text, _enc = encoding.read(filename)
            return text

        return editor.toPlainText()

    def handle_run_cell(self, cell_name, filename):
        """
        Get cell code from cell name and file name.
        """
        editorstack = self.get_editorstack()
        if CONF.get('editor', 'save_all_before_run', True):
            editorstack.save_all(save_new_files=False)
        editor = self.get_editor(filename)

        if editor is None:
            raise RuntimeError(
                "File {} not open in the editor".format(filename))

        editorstack.last_cell_call = (filename, cell_name)

        # The file is open, load code from editor
        return editor.get_cell_code(cell_name)

    def handle_cell_count(self, filename):
        """Get number of cells in file to loop."""
        editorstack = self.get_editorstack()
        editor = self.get_editor(filename)

        if editor is None:
            raise RuntimeError(
                "File {} not open in the editor".format(filename))

        # The file is open, get cell count from editor
        return editor.get_cell_count()

    def handle_current_filename(self):
        """Get the current filename."""
        return self.get_editorstack().get_current_finfo().filename

    # ---- Private methods (overrode by us) ---------------------------------

    def _handle_error(self, msg):
        """
        Reimplemented to reset the prompt if the error comes after the reply
        """
        self._process_execute_error(msg)

    def _context_menu_make(self, pos):
        """Reimplement the IPython context menu"""
        menu = super(ShellWidget, self)._context_menu_make(pos)
        return self.ipyclient.add_actions_to_context_menu(menu)

    def _banner_default(self):
        """
        Reimplement banner creation to let the user decide if he wants a
        banner or not
        """
        # Don't change banner for external kernels
        if self.external_kernel:
            return ''
        show_banner_o = self.additional_options['show_banner']
        if show_banner_o:
            return self.long_banner()
        else:
            return self.short_banner()

    def _kernel_restarted_message(self, died=True):
        msg = _("Kernel died, restarting") if died else _("Kernel restarting")
        self.sig_kernel_restarted.emit(msg)

    def _syntax_style_changed(self):
        """Refresh the highlighting with the current syntax style by class."""
        if self._highlighter is None:
            # ignore premature calls
            return
        if self.syntax_style:
            self._highlighter._style = create_style_class(self.syntax_style)
            self._highlighter._clear_caches()
        else:
            self._highlighter.set_style_sheet(self.style_sheet)

    def _prompt_started_hook(self):
        """Emit a signal when the prompt is ready."""
        if not self._reading:
            self._highlighter.highlighting_on = True
            self.sig_prompt_ready.emit()

    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ShellWidget, self).focusInEvent(event)

    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(ShellWidget, self).focusOutEvent(event)
