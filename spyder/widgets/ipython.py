# -*- coding:utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython client's widget
"""

# Standard library imports
from __future__ import absolute_import  # Fix for Issue 1356

import ast
import os
import os.path as osp
import re
import uuid
from string import Template
import sys
from threading import Thread
import time

# Third party imports (qtpy)
from qtpy.QtCore import Qt, QEventLoop, QUrl, Signal, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import (QHBoxLayout, QMenu, QMessageBox, QTextEdit,
                            QToolButton, QVBoxLayout, QWidget)

# Third party imports (Jupyter)
from ipykernel.pickleutil import CannedObject
from ipykernel.serialize import deserialize_object
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.ansi_code_processor import ANSI_OR_SPECIAL_PATTERN

# Local imports
from spyder.config.base import (_, get_conf_path, get_image_path,
                                get_module_source_path)
from spyder.config.gui import (config_shortcut, get_font, get_shortcut,
                               fixed_shortcut)
from spyder.config.main import CONF
from spyder.py3compat import PY3, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import programs
from spyder.utils.dochelpers import getargspecfromtext, getsignaturefromtext
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, restore_keyevent)
from spyder.widgets.arraybuilder import SHORTCUT_INLINE, SHORTCUT_TABLE
from spyder.widgets.browser import WebView
from spyder.widgets.calltip import CallTipWidget
from spyder.widgets.mixins import (BaseEditMixin, GetHelpMixin,
                                   SaveHistoryMixin, TracebackLinksMixin)


#-----------------------------------------------------------------------------
# Templates
#-----------------------------------------------------------------------------
# Using the same css file from the Help plugin for now. Maybe
# later it'll be a good idea to create a new one.
UTILS_PATH = get_module_source_path('spyder', 'utils')
CSS_PATH = osp.join(UTILS_PATH, 'help', 'static', 'css')
TEMPLATES_PATH = osp.join(UTILS_PATH, 'ipython', 'templates')

BLANK = open(osp.join(TEMPLATES_PATH, 'blank.html')).read()
LOADING = open(osp.join(TEMPLATES_PATH, 'loading.html')).read()
KERNEL_ERROR = open(osp.join(TEMPLATES_PATH, 'kernel_error.html')).read()


#-----------------------------------------------------------------------------
# Auxiliary functions
#-----------------------------------------------------------------------------
def background(f):
    """
    Call a function in a simple thread, to prevent blocking

    Taken from the Jupyter Qtconsole project
    """
    t = Thread(target=f)
    t.start()
    return t


#-----------------------------------------------------------------------------
# Control widgets
#-----------------------------------------------------------------------------
class IPythonControlWidget(TracebackLinksMixin, GetHelpMixin, QTextEdit,
                           BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins to use as the
    control widget for IPython widgets
    """
    QT_CLASS = QTextEdit
    visibility_changed = Signal(bool)
    go_to_error = Signal(str)
    focus_changed = Signal()
    
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)
        TracebackLinksMixin.__init__(self)
        GetHelpMixin.__init__(self)

        self.calltip_widget = CallTipWidget(self, hide_timer_on=True)
        self.found_results = []

        # To not use Spyder calltips obtained through the monitor
        self.calltips = False

    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.visibility_changed.emit(True)

    def _key_question(self, text):
        """ Action for '?' and '(' """
        self.current_prompt_pos = self.parentWidget()._prompt_pos
        if self.get_current_line_to_cursor():
            last_obj = self.get_last_obj()
            if last_obj and not last_obj.isdigit():
                self.show_object_info(last_obj)
        self.insert_text(text)
    
    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        if key == Qt.Key_Question and not self.has_selected_text():
            self._key_question(text)
        elif key == Qt.Key_ParenLeft and not self.has_selected_text():
            self._key_question(text)
        else:
            # Let the parent widget handle the key press event
            QTextEdit.keyPressEvent(self, event)

    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(IPythonControlWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(IPythonControlWidget, self).focusOutEvent(event)


class IPythonPageControlWidget(QTextEdit, BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins.BaseEditMixin to
    use as the paging widget for IPython widgets
    """
    QT_CLASS = QTextEdit
    visibility_changed = Signal(bool)
    show_find_widget = Signal()
    focus_changed = Signal()
    
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)
        self.found_results = []
    
    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.visibility_changed.emit(True)
    
    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        
        if key == Qt.Key_Slash and self.isVisible():
            self.show_find_widget.emit()

    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(IPythonPageControlWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(IPythonPageControlWidget, self).focusOutEvent(event)


#-----------------------------------------------------------------------------
# Shell widget
#-----------------------------------------------------------------------------
class IPythonShellWidget(RichJupyterWidget):
    """
    Spyder's Jupyter shell widget

    This class has custom control and page_control widgets, additional methods
    to provide missing functionality and a couple more keyboard shortcuts.
    """
    focus_changed = Signal()
    new_client = Signal()
    sig_namespace_view = Signal(object)
    sig_var_properties = Signal(object)
    sig_get_value = Signal()
    sig_error_message = Signal()
    
    def __init__(self, *args, **kw):
        # To override the Qt widget used by RichJupyterWidget
        self.custom_control = IPythonControlWidget
        self.custom_page_control = IPythonPageControlWidget
        super(IPythonShellWidget, self).__init__(*args, **kw)
        self.set_background_color()

        # --- Spyder variables ---
        self.ipyclient = None
        self.namespacebrowser = None

        # --- Keyboard shortcuts ---
        self.shortcuts = self.create_shortcuts()

        # --- To save the replies of kernel method executions
        #     (except getting values of variables)
        self._kernel_methods = {}

        # --- To save values and messages returned by the kernel ---
        self.kernel_value = None
        self.kernel_message = None
        self.__kernel_is_starting = True

    #---- Public API ----------------------------------------------------------
    def set_ipyclient(self, ipyclient):
        """Bind this shell widget to an IPython client one"""
        self.ipyclient = ipyclient
        self.exit_requested.connect(ipyclient.exit_callback)

    def long_banner(self):
        """Banner for IPython widgets with pylab message"""
        from IPython.core.usage import default_banner
        banner = default_banner

        pylab_o = CONF.get('ipython_console', 'pylab', True)
        autoload_pylab_o = CONF.get('ipython_console', 'pylab/autoload', True)
        mpl_installed = programs.is_module_installed('matplotlib')
        if mpl_installed and (pylab_o and autoload_pylab_o):
            pylab_message = ("\nPopulating the interactive namespace from "
                             "numpy and matplotlib")
            banner = banner + pylab_message
        
        sympy_o = CONF.get('ipython_console', 'symbolic_math', True)
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
        return banner

    def short_banner(self):
        """Short banner with Python and QtConsole versions"""
        from qtconsole._version import __version__
        py_ver = '%d.%d.%d' % (sys.version_info[0], sys.version_info[1],
                               sys.version_info[2])
        banner = 'Python %s on %s -- QtConsole %s' % (py_ver, sys.platform,
                                                      __version__)
        return banner

    def clear_console(self):
        self.execute("%clear")
        
    def reset_namespace(self):
        """Resets the namespace by removing all names defined by the user"""
        
        reply = QMessageBox.question(
            self,
            _("Reset IPython namespace"),
            _("All user-defined variables will be removed."
            "<br>Are you sure you want to reset the namespace?"),
            QMessageBox.Yes | QMessageBox.No,
            )

        if reply == QMessageBox.Yes:
            self.execute("%reset -f")

    def write_to_stdin(self, line):
        """Send raw characters to the IPython kernel through stdin"""
        self.kernel_client.input(line)

    def set_background_color(self):
        lightbg_o = CONF.get('ipython_console', 'light_color')
        if not lightbg_o:
            self.set_default_style(colors='linux')

    def create_shortcuts(self):
        inspect = config_shortcut(self._control.inspect_current_object,
                                  context='Console', name='Inspect current object',
                                  parent=self)
        clear_console = config_shortcut(self.clear_console, context='Console',
                                        name='Clear shell', parent=self)

        # Fixed shortcuts
        fixed_shortcut("Ctrl+T", self, lambda: self.new_client.emit())
        fixed_shortcut("Ctrl+R", self, lambda: self.reset_namespace())
        fixed_shortcut(SHORTCUT_INLINE, self,
                       lambda: self._control.enter_array_inline())
        fixed_shortcut(SHORTCUT_TABLE, self,
                       lambda: self._control.enter_array_table())

        return [inspect, clear_console]

    # ---- For the Help plugin ----------------------------------------
    def clean_invalid_var_chars(self, var):
        """
        Replace invalid variable chars in a string by underscores

        Taken from http://stackoverflow.com/a/3305731/438386
        """
        if PY3:
            return re.sub('\W|^(?=\d)', '_', var, re.UNICODE)
        else:
            return re.sub('\W|^(?=\d)', '_', var)

    def get_signature(self, content):
        """Get signature from inspect reply content"""
        data = content.get('data', {})
        text = data.get('text/plain', '')
        if text:
            text = ANSI_OR_SPECIAL_PATTERN.sub('', text)
            self._control.current_prompt_pos = self._prompt_pos
            line = self._control.get_current_line_to_cursor()
            name = line[:-1].split('(')[-1]   # Take last token after a (
            name = name.split('.')[-1]        # Then take last token after a .
            # Clean name from invalid chars
            try:
                name = self.clean_invalid_var_chars(name).split('_')[-1]
            except:
                pass
            argspec = getargspecfromtext(text)
            if argspec:
                # This covers cases like np.abs, whose docstring is
                # the same as np.absolute and because of that a proper
                # signature can't be obtained correctly
                signature = name + argspec
            else:
                signature = getsignaturefromtext(text, name)
            return signature
        else:
            return ''

    #---- For the Variable Explorer -------------------
    def set_namespacebrowser(self, namespacebrowser):
        """Set namespace browser widget"""
        self.namespacebrowser = namespacebrowser
        self.configure_namespacebrowser()

    def configure_namespacebrowser(self):
        """Configure associated namespace browser widget"""
        # Tell it that we are connected to client
        self.namespacebrowser.is_ipyclient = True

        # Update namespace view
        self.sig_namespace_view.connect(lambda data:
            self.namespacebrowser.process_remote_view(data))

        # Update properties of variables
        self.sig_var_properties.connect(lambda data:
            self.namespacebrowser.set_var_properties(data))

    def refresh_namespacebrowser(self):
        """Refresh namespace browser"""
        if self.namespacebrowser:
            self.silent_exec_method(
                'get_ipython().kernel.get_namespace_view()')
            self.silent_exec_method(
                'get_ipython().kernel.get_var_properties()')

    def set_namespace_view_settings(self):
        """Set the namespace view settings"""
        settings = to_text_string(self.namespacebrowser.get_view_settings())
        code = u"get_ipython().kernel.namespace_view_settings = %s" % settings
        self.silent_execute(code)

    def silent_execute(self, code):
        """Execute code in the kernel without increasing the prompt"""
        self.kernel_client.execute(to_text_string(code), silent=True)

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
                    view = ast.literal_eval(data['text/plain'])
                    self.sig_namespace_view.emit(view)
                elif 'get_var_properties' in method:
                    properties = ast.literal_eval(data['text/plain'])
                    self.sig_var_properties.emit(properties)
                elif 'load_data' in method or 'save_namespace' in method:
                    self.kernel_message = ast.literal_eval(data['text/plain'])
                    self.sig_error_message.emit()

                # Remove method after being processed
                self._kernel_methods.pop(expression)

    def get_value(self, name):
        """Ask kernel for a value"""
        # Wait until the kernel returns the value
        wait_loop = QEventLoop()
        self.sig_get_value.connect(wait_loop.quit)
        self.silent_execute("get_ipython().kernel.get_value('%s')" % name)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_get_value.disconnect(wait_loop.quit)
        wait_loop = None

        return self.kernel_value

    def _handle_data_message(self, msg):
        """
        Handle raw (serialized) data sent by the kernel

        We only handle data asked by Spyder, in case people use
        publish_data for other purposes.
        """
        # Deserialize data
        data = deserialize_object(msg['buffers'])[0]

        # We only handle data asked by Spyder
        value = data.get('__spy_data__', None)
        if value is not None:
            if isinstance(value, CannedObject):
                value = value.get_object()
            self.kernel_value = value
            self.sig_get_value.emit()

    def set_value(self, name, value):
        """Set value for a variable"""
        value = to_text_string(value)
        self.silent_execute("get_ipython().kernel.set_value('%s', %s)" %
                            (name, value))

    def remove_value(self, name):
        """Remove a variable"""
        self.silent_execute("get_ipython().kernel.remove_value('%s')" % name)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        self.silent_execute("get_ipython().kernel.copy_value('%s', '%s')" %
                            (orig_name, new_name))

    def load_data(self, filename, ext):
        # Wait until the kernel tries to load the file
        wait_loop = QEventLoop()
        self.sig_error_message.connect(wait_loop.quit)
        self.silent_exec_method(
                "get_ipython().kernel.load_data('%s', '%s')" % (filename, ext))
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_error_message.disconnect(wait_loop.quit)
        wait_loop = None

        return self.kernel_message

    def save_namespace(self, filename):
        # Wait until the kernel tries to save the file
        wait_loop = QEventLoop()
        self.sig_error_message.connect(wait_loop.quit)
        self.silent_exec_method("get_ipython().kernel.save_namespace('%s')" %
                                filename)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_error_message.disconnect(wait_loop.quit)
        wait_loop = None

        return self.kernel_message

    #---- Private methods ---------------------------------------------
    def _context_menu_make(self, pos):
        """Reimplement the IPython context menu"""
        menu = super(IPythonShellWidget, self)._context_menu_make(pos)
        return self.ipyclient.add_actions_to_context_menu(menu)
    
    def _banner_default(self):
        """
        Reimplement banner creation to let the user decide if he wants a
        banner or not
        """
        banner_o = CONF.get('ipython_console', 'show_banner', True)
        if banner_o:
            return self.long_banner()
        else:
            return self.short_banner()

    def _handle_inspect_reply(self, rep):
        """
        Reimplement call tips to only show signatures, using the same
        style from our Editor and External Console too
        """
        cursor = self._get_cursor()
        info = self._request_info.get('call_tip')
        if info and info.id == rep['parent_header']['msg_id'] and \
          info.pos == cursor.position():
            content = rep['content']
            if content.get('status') == 'ok' and content.get('found', False):
                signature = self.get_signature(content)
                if signature:
                    self._control.show_calltip(_("Arguments"), signature,
                                               signature=True, color='#2D62FF')

    def _handle_execute_reply(self, msg):
        """
        Reimplemented to handle communications between Spyder
        and the kernel
        """
        msg_id = msg['parent_header']['msg_id']
        info = self._request_info['execute'].get(msg_id)
        # unset reading flag, because if execute finished, raw_input can't
        # still be pending.
        self._reading = False

        # Refresh namespacebrowser after the kernel starts running
        exec_count = msg['content']['execution_count']
        if exec_count == 0 and self.__kernel_is_starting:
            self.set_namespace_view_settings()
            self.refresh_namespacebrowser()
            self.__kernel_is_starting = False

        # Handle silent execution of kernel methods
        if info and info.kind == 'silent_exec_method' and not self._hidden:
            self.handle_exec_method(msg)
            self._request_info['execute'].pop(msg_id)
        else:
            super(IPythonShellWidget, self)._handle_execute_reply(msg)

    def _handle_status(self, msg):
        """
        Reimplemented to refresh the namespacebrowser after kernel
        restarts
        """
        state = msg['content'].get('execution_state', '')
        msg_type = msg['parent_header'].get('msg_type', '')
        if state == 'starting' and not self.__kernel_is_starting:
            # This handles restarts when the kernel dies
            # unexpectedly
            self.__kernel_is_starting = True
        elif state == 'idle' and msg_type == 'shutdown_request':
            # This handles restarts asked by the user
            self.set_namespace_view_settings()
            self.refresh_namespacebrowser()
        else:
            super(IPythonShellWidget, self)._handle_status(msg)

    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(IPythonShellWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.focus_changed.emit()
        return super(IPythonShellWidget, self).focusOutEvent(event)


#-----------------------------------------------------------------------------
# Client widget
#-----------------------------------------------------------------------------
class IPythonClient(QWidget, SaveHistoryMixin):
    """
    IPython client or frontend for Spyder

    This is a widget composed of a shell widget (i.e. RichJupyterWidget
    + our additions = IPythonShellWidget) and a WebView info widget to
    print kernel error and other messages.
    """

    SEPARATOR = '%s##---(%s)---' % (os.linesep*2, time.ctime())
    append_to_history = Signal(str, str)

    def __init__(self, plugin, name, history_filename, config_options,
                 connection_file=None, hostname=None, menu_actions=None,
                 slave=False):
        super(IPythonClient, self).__init__(plugin)
        SaveHistoryMixin.__init__(self)

        # --- Init attrs
        self.name = name
        self.history_filename = get_conf_path(history_filename)
        self.connection_file = connection_file
        self.hostname = hostname
        self.menu_actions = menu_actions
        self.slave = slave

        # --- Other attrs
        self.options_button = None
        self.stop_button = None
        self.stop_icon = ima.icon('stop')
        self.history = []

        # --- Widgets
        self.shellwidget = IPythonShellWidget(config=config_options,
                                              local_kernel=True)
        self.shellwidget.hide()
        self.infowidget = WebView(self)
        self.set_infowidget_font()
        self.loading_page = self._create_loading_page()
        self.infowidget.setHtml(self.loading_page,
                                QUrl.fromLocalFile(CSS_PATH))

        # --- Layout
        vlayout = QVBoxLayout()
        toolbar_buttons = self.get_toolbar_buttons()
        hlayout = QHBoxLayout()
        for button in toolbar_buttons:
            hlayout.addWidget(button)
        vlayout.addLayout(hlayout)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.shellwidget)
        vlayout.addWidget(self.infowidget)
        self.setLayout(vlayout)

        # --- Exit function
        self.exit_callback = lambda: plugin.close_client(client=self)

        # --- Signals
        # As soon as some content is printed in the console, stop
        # our loading animation
        document = self.get_control().document()
        document.contentsChange.connect(self._stop_loading_animation)

    #------ Public API --------------------------------------------------------
    def configure_shellwidget(self, give_focus=True):
        """Configure shellwidget after kernel is started"""
        if give_focus:
            self.get_control().setFocus()

        # Connect shellwidget to the client
        self.shellwidget.set_ipyclient(self)

        # To save history
        self.shellwidget.executing.connect(self.add_to_history)

        # For Mayavi to run correctly
        self.shellwidget.executing.connect(self.set_backend_for_mayavi)

        # To update history after execution
        self.shellwidget.executed.connect(self.update_history)

        # To update the Variable Explorer after execution
        self.shellwidget.executed.connect(
            self.shellwidget.refresh_namespacebrowser)

        # To enable the stop button when executing a process
        self.shellwidget.executing.connect(self.enable_stop_button)

        # To disable the stop button after execution stopped
        self.shellwidget.executed.connect(self.disable_stop_button)

    def enable_stop_button(self):
        self.stop_button.setEnabled(True)

    def disable_stop_button(self):
        self.stop_button.setDisabled(True)

    @Slot()
    def stop_button_click_handler(self):
        """Method to handle what to do when the stop button is pressed"""
        self.stop_button.setDisabled(True)
        # Interrupt computations or stop debugging
        if not self.shellwidget._reading:
            self.interrupt_kernel()
        else:
            self.shellwidget.write_to_stdin('exit')

    def show_kernel_error(self, error):
        """Show kernel initialization errors in infowidget"""
        # Don't break lines in hyphens
        # From http://stackoverflow.com/q/7691569/438386
        error = error.replace('-', '&#8209')

        # Create error page
        message = _("An error ocurred while starting the kernel")
        kernel_error_template = Template(KERNEL_ERROR)
        page = kernel_error_template.substitute(css_path=CSS_PATH,
                                                message=message,
                                                error=error)

        # Show error
        self.infowidget.setHtml(page)
        self.shellwidget.hide()
        self.infowidget.show()

    def get_name(self):
        """Return client name"""
        return ((_("Console") if self.hostname is None else self.hostname)
                + " " + self.name)
    
    def get_control(self):
        """Return the text widget (or similar) to give focus to"""
        # page_control is the widget used for paging
        page_control = self.shellwidget._page_control
        if page_control and page_control.isVisible():
            return page_control
        else:
            return self.shellwidget._control

    def get_kernel(self):
        """Get kernel associated with this client"""
        return self.shellwidget.kernel_manager

    def get_options_menu(self):
        """Return options menu"""
        restart_action = create_action(self, _("Restart kernel"),
                                       shortcut=QKeySequence("Ctrl+."),
                                       icon=ima.icon('restart'),
                                       triggered=self.restart_kernel,
                                       context=Qt.WidgetWithChildrenShortcut)

        # Main menu
        if self.menu_actions is not None:
            actions = [restart_action, None] + self.menu_actions
        else:
            actions = [restart_action]
        return actions

    def get_toolbar_buttons(self):
        """Return toolbar buttons list"""
        buttons = []
        # Code to add the stop button
        if self.stop_button is None:
            self.stop_button = create_toolbutton(self, text=_("Stop"),
                                             icon=self.stop_icon,
                                             tip=_("Stop the current command"))
            self.disable_stop_button()
            # set click event handler
            self.stop_button.clicked.connect(self.stop_button_click_handler)
        if self.stop_button is not None:
            buttons.append(self.stop_button)
            
        if self.options_button is None:
            options = self.get_options_menu()
            if options:
                self.options_button = create_toolbutton(self,
                        text=_('Options'), icon=ima.icon('tooloptions'))
                self.options_button.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(self)
                add_actions(menu, options)
                self.options_button.setMenu(menu)
        if self.options_button is not None:
            buttons.append(self.options_button)

        return buttons

    def add_actions_to_context_menu(self, menu):
        """Add actions to IPython widget context menu"""
        inspect_action = create_action(self, _("Inspect current object"),
                                    QKeySequence(get_shortcut('console',
                                                    'inspect current object')),
                                    icon=ima.icon('MessageBoxInformation'),
                                    triggered=self.inspect_object)
        clear_line_action = create_action(self, _("Clear line or block"),
                                          QKeySequence("Shift+Escape"),
                                          icon=ima.icon('editdelete'),
                                          triggered=self.clear_line)
        reset_namespace_action = create_action(self, _("Reset namespace"),
                                          QKeySequence("Ctrl+R"),
                                          triggered=self.reset_namespace)
        clear_console_action = create_action(self, _("Clear console"),
                                             QKeySequence(get_shortcut('console',
                                                               'clear shell')),
                                             icon=ima.icon('editclear'),
                                             triggered=self.clear_console)
        quit_action = create_action(self, _("&Quit"), icon=ima.icon('exit'),
                                    triggered=self.exit_callback)
        add_actions(menu, (None, inspect_action, clear_line_action,
                           clear_console_action, reset_namespace_action,
                           None, quit_action))
        return menu
    
    def set_font(self, font):
        """Set IPython widget's font"""
        self.shellwidget._control.setFont(font)
        self.shellwidget.font = font

    def set_infowidget_font(self):
        """Set font for infowidget"""
        font = get_font(option='rich_font')
        self.infowidget.set_font(font)

    def shutdown(self):
        """Shutdown kernel"""
        if self.get_kernel() is not None and not self.slave:
            self.shellwidget.kernel_manager.shutdown_kernel()
        if self.shellwidget.kernel_client is not None:
            background(self.shellwidget.kernel_client.stop_channels)

    def interrupt_kernel(self):
        """Interrupt the associanted Spyder kernel if it's running"""
        self.shellwidget.request_interrupt_kernel()

    @Slot()
    def restart_kernel(self):
        """
        Restart the associanted kernel

        Took this code from the qtconsole project
        Licensed under the BSD license
        """
        message = _('Are you sure you want to restart the kernel?')
        buttons = QMessageBox.Yes | QMessageBox.No
        result = QMessageBox.question(self, _('Restart kernel?'),
                                      message, buttons)
        if result == QMessageBox.Yes:
            sw = self.shellwidget
            if sw.kernel_manager:
                try:
                    sw.kernel_manager.restart_kernel()
                except RuntimeError as e:
                    sw._append_plain_text(
                        _('Error restarting kernel: %s\n') % e,
                        before_prompt=True
                    )
                else:
                    sw._append_html(_("<br>Restarting kernel...\n<hr><br>"),
                        before_prompt=True,
                    )
            else:
                sw._append_plain_text(
                    _('Cannot restart a kernel not started by Spyder\n'),
                    before_prompt=True
                )

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
        self.shellwidget.reset_namespace()

    def update_history(self):
        self.history = self.shellwidget._history

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
            self.shellwidget._append_plain_text(message + '\n')
            self.shellwidget.execute("%gui inline\n%gui qt")

    #------ Private API -------------------------------------------------------
    def _create_loading_page(self):
        """Create html page to show while the kernel is starting"""
        loading_template = Template(LOADING)
        loading_img = get_image_path('loading_sprites.png')
        if os.name == 'nt':
            loading_img = loading_img.replace('\\', '/')
        message = _("Connecting to kernel...")
        page = loading_template.substitute(css_path=CSS_PATH,
                                           loading_img=loading_img,
                                           message=message)
        return page

    def _stop_loading_animation(self):
        """Stop animation shown while the kernel is starting"""
        self.infowidget.hide()
        self.shellwidget.show()
        self.infowidget.setHtml(BLANK)

        document = self.get_control().document()
        document.contentsChange.disconnect(self._stop_loading_animation)
