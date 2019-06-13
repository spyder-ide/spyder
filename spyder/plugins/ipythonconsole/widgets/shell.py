# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Shell Widget for the IPython Console
"""

import ast
import os
import uuid
from textwrap import dedent

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox
from spyder.config.main import CONF
from spyder.config.base import _
from spyder.config.gui import config_shortcut
from spyder.py3compat import PY2, to_text_string
from spyder.utils import encoding
from spyder.utils import programs
from spyder.utils import syntaxhighlighters as sh
from spyder.plugins.ipythonconsole.utils.style import create_qss_style, create_style_class
from spyder.widgets.helperwidgets import MessageCheckBox
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
    sig_namespace_view = Signal(object)
    sig_var_properties = Signal(object)
    sig_show_syspath = Signal(object)
    sig_show_env = Signal(object)

    # For FigureBrowserWidget
    sig_new_inline_figure = Signal(object, str)

    # For DebuggingWidget
    sig_pdb_step = Signal(str, int)

    # For ShellWidget
    focus_changed = Signal()
    new_client = Signal()
    sig_got_reply = Signal()
    sig_is_spykernel = Signal(object)
    sig_kernel_restarted = Signal(str)
    sig_prompt_ready = Signal()

    # For global working directory
    sig_change_cwd = Signal(str)

    def __init__(self, ipyclient, additional_options, interpreter_versions,
                 external_kernel, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = ControlWidget
        self.custom_page_control = PageControlWidget
        self.custom_edit = True
        super(ShellWidget, self).__init__(*args, **kw)

        self.ipyclient = ipyclient
        self.additional_options = additional_options
        self.interpreter_versions = interpreter_versions
        self.external_kernel = external_kernel
        self._cwd = ''

        # Keyboard shortcuts
        self.shortcuts = self.create_shortcuts()

        # To save kernel replies in silent execution
        self._kernel_reply = None

        # Set the color of the matched parentheses here since the qtconsole
        # uses a hard-coded value that is not modified when the color scheme is
        # set in the qtconsole constructor. See issue #4806.   
        self.set_bracket_matcher_color_scheme(self.syntax_style)
                
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

        if not self.external_kernel:
            code = u"get_ipython().kernel.set_cwd(u'''{}''')".format(dirname)
            if self._reading:
                self.kernel_client.input(u'!' + code)
            else:
                self.silent_execute(code)
            self._cwd = dirname

    def get_cwd(self):
        """Update current working directory.

        Retrieve the cwd and emit a signal connected to the working directory
        widget. (see: handle_exec_method())
        """
        code = u"get_ipython().kernel.get_cwd()"
        if self._reading:
            return
        else:
            self.silent_exec_method(code)
            
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
            self.silent_execute("%colors linux")
        else:
            self.silent_execute("%colors lightbg")

    def get_syspath(self):
        """Ask the kernel for sys.path contents."""
        code = u"get_ipython().kernel.get_syspath()"
        if self._reading:
            return
        else:
            self.silent_exec_method(code)

    def get_env(self):
        """Ask the kernel for environment variables."""
        code = u"get_ipython().kernel.get_env()"
        if self._reading:
            return
        else:
            self.silent_exec_method(code)

    # --- To handle the banner
    def long_banner(self):
        """Banner for IPython widgets with pylab message"""
        # Default banner
        try:
            from IPython.core.usage import quick_guide
        except Exception:
            quick_guide = ''
        banner_parts = [
            'Python %s\n' % self.interpreter_versions['python_version'],
            'Type "copyright", "credits" or "license" for more information.\n\n',
            'IPython %s -- An enhanced Interactive Python.\n' % \
            self.interpreter_versions['ipython_version'],
            quick_guide
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
        """Short banner with Python and QtConsole versions"""
        banner = 'Python %s -- IPython %s' % (
                                  self.interpreter_versions['python_version'],
                                  self.interpreter_versions['ipython_version'])
        return banner

    # --- To define additional shortcuts
    def clear_console(self):
        if self._reading:
            self.dbg_exec_magic('clear')
        else:
            self.execute("%clear")

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
        # See spyder-ide/spyder#9505
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
            if self._reading:
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
                    self.silent_execute(
                        'get_ipython().kernel.close_all_mpl_figures()')
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
                if 'get_namespace_view' in method:
                    if data is not None and 'text/plain' in data:
                        literal = ast.literal_eval(data['text/plain'])
                        view = ast.literal_eval(literal)
                    else:
                        view = None
                    self.sig_namespace_view.emit(view)
                elif 'get_var_properties' in method:
                    if data is not None and 'text/plain' in data:
                        literal = ast.literal_eval(data['text/plain'])
                        properties = ast.literal_eval(literal)
                    else:
                        properties = None
                    self.sig_var_properties.emit(properties)
                elif 'get_cwd' in method:
                    if data is not None and 'text/plain' in data:
                        self._cwd = ast.literal_eval(data['text/plain'])
                        if PY2:
                            self._cwd = encoding.to_unicode_from_fs(self._cwd)
                    else:
                        self._cwd = ''
                    self.sig_change_cwd.emit(self._cwd)
                elif 'get_syspath' in method:
                    if data is not None and 'text/plain' in data:
                        syspath = ast.literal_eval(data['text/plain'])
                    else:
                        syspath = None
                    self.sig_show_syspath.emit(syspath)
                elif 'get_env' in method:
                    if data is not None and 'text/plain' in data:
                        env = ast.literal_eval(data['text/plain'])
                    else:
                        env = None
                    self.sig_show_env.emit(env)
                elif 'getattr' in method:
                    if data is not None and 'text/plain' in data:
                        is_spyder_kernel = data['text/plain']
                        if 'SpyderKernel' in is_spyder_kernel:
                            self.sig_is_spykernel.emit(self)
                else:
                    if data is not None and 'text/plain' in data:
                        self._kernel_reply = ast.literal_eval(data['text/plain'])
                    else:
                        self._kernel_reply = None
                    self.sig_got_reply.emit()

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

        Fixes issue 4002
        """
        if command.startswith('%matplotlib') and \
          len(command.splitlines()) == 1:
            if not 'inline' in command:
                self.silent_execute(command)

    #---- Private methods (overrode by us) ---------------------------------
    def _handle_error(self, msg):
        """
        Reimplemented to reset the prompt if the error comes after the reply
        """
        self._process_execute_error(msg)
        self._show_interpreter_prompt()

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
