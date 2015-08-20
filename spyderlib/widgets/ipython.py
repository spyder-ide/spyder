# -*- coding:utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.13+ client's widget
"""
# Fix for Issue 1356
from __future__ import absolute_import

# Stdlib imports
import os
import os.path as osp
import re
from string import Template
import sys
import time

# Qt imports
from spyderlib.qt.QtGui import (QTextEdit, QKeySequence, QWidget, QMenu,
                                QHBoxLayout, QToolButton, QVBoxLayout,
                                QMessageBox)
from spyderlib.qt.QtCore import SIGNAL, Qt

from spyderlib import pygments_patch
pygments_patch.apply()

# IPython imports
try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget as RichIPythonWidget
except ImportError:
    from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
from IPython.qt.console.ansi_code_processor import ANSI_OR_SPECIAL_PATTERN
from IPython.core.application import get_ipython_dir
from IPython.core.oinspect import call_tip
from IPython.config.loader import Config, load_pyconfig_files

# Local imports
from spyderlib.baseconfig import (get_conf_path, get_image_path,
                                  get_module_source_path, _)
from spyderlib.config import CONF
from spyderlib.guiconfig import (create_shortcut, get_font, get_shortcut,
                                 new_shortcut)
from spyderlib.utils.dochelpers import getargspecfromtext, getsignaturefromtext
from spyderlib.utils.qthelpers import (get_std_icon, create_toolbutton,
                                       add_actions, create_action, get_icon,
                                       restore_keyevent)
from spyderlib.utils import programs, sourcecode
from spyderlib.widgets.browser import WebView
from spyderlib.widgets.calltip import CallTipWidget
from spyderlib.widgets.mixins import (BaseEditMixin, InspectObjectMixin,
                                      SaveHistoryMixin, TracebackLinksMixin)
from spyderlib.py3compat import PY3


#-----------------------------------------------------------------------------
# Templates
#-----------------------------------------------------------------------------
# Using the same css file from the Object Inspector for now. Maybe
# later it'll be a good idea to create a new one.
UTILS_PATH = get_module_source_path('spyderlib', 'utils')
CSS_PATH = osp.join(UTILS_PATH, 'inspector', 'static', 'css')
TEMPLATES_PATH = osp.join(UTILS_PATH, 'ipython', 'templates')

BLANK = open(osp.join(TEMPLATES_PATH, 'blank.html')).read()
LOADING = open(osp.join(TEMPLATES_PATH, 'loading.html')).read()
KERNEL_ERROR = open(osp.join(TEMPLATES_PATH, 'kernel_error.html')).read()

#-----------------------------------------------------------------------------
# Control widgets
#-----------------------------------------------------------------------------
class IPythonControlWidget(TracebackLinksMixin, InspectObjectMixin, QTextEdit,
                           BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins to use as the
    control widget for IPython widgets
    """
    QT_CLASS = QTextEdit
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)
        TracebackLinksMixin.__init__(self)
        InspectObjectMixin.__init__(self)

        self.calltip_widget = CallTipWidget(self, hide_timer_on=True)
        self.found_results = []

        # To not use Spyder calltips obtained through the monitor
        self.calltips = False

    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.emit(SIGNAL("visibility_changed(bool)"), True)

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
        self.emit(SIGNAL('focus_changed()'))
        return super(IPythonControlWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(IPythonControlWidget, self).focusOutEvent(event)


class IPythonPageControlWidget(QTextEdit, BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins.BaseEditMixin to
    use as the paging widget for IPython widgets
    """
    QT_CLASS = QTextEdit
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        BaseEditMixin.__init__(self)
        self.found_results = []
    
    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.emit(SIGNAL("visibility_changed(bool)"), True)
    
    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        
        if key == Qt.Key_Slash and self.isVisible():
            self.emit(SIGNAL("show_find_widget()"))

    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(IPythonPageControlWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(IPythonPageControlWidget, self).focusOutEvent(event)


#-----------------------------------------------------------------------------
# Shell widget
#-----------------------------------------------------------------------------
class IPythonShellWidget(RichIPythonWidget):
    """
    Spyder's IPython shell widget

    This class has custom control and page_control widgets, additional methods
    to provide missing functionality and a couple more keyboard shortcuts.
    """
    def __init__(self, *args, **kw):
        # To override the Qt widget used by RichIPythonWidget
        self.custom_control = IPythonControlWidget
        self.custom_page_control = IPythonPageControlWidget
        super(IPythonShellWidget, self).__init__(*args, **kw)
        self.set_background_color()
        
        # --- Spyder variables ---
        self.ipyclient = None
        
        # --- Keyboard shortcuts ---
        self.shortcuts = self.create_shortcuts()
        
        # --- IPython variables ---
        # To send an interrupt signal to the Spyder kernel
        self.custom_interrupt = True
        
        # To restart the Spyder kernel in case it dies
        self.custom_restart = True
    
    #---- Public API ----------------------------------------------------------
    def set_ipyclient(self, ipyclient):
        """Bind this shell widget to an IPython client one"""
        self.ipyclient = ipyclient
        self.exit_requested.connect(ipyclient.exit_callback)
    
    def long_banner(self):
        """Banner for IPython widgets with pylab message"""
        from IPython.core.usage import default_gui_banner
        banner = default_gui_banner
        
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
        """Short banner with Python and IPython versions"""
        from IPython.core.release import version
        py_ver = '%d.%d.%d' % (sys.version_info[0], sys.version_info[1],
                               sys.version_info[2])
        banner = 'Python %s on %s -- IPython %s' % (py_ver, sys.platform,
                                                    version)
        return banner
    
    def clear_console(self):
        self.execute("%clear")
        
    def write_to_stdin(self, line):
        """Send raw characters to the IPython kernel through stdin"""
        try:
            self.kernel_client.stdin_channel.input(line)
        except AttributeError:
            self.kernel_client.input(line)
    
    def set_background_color(self):
        lightbg_o = CONF.get('ipython_console', 'light_color')
        if not lightbg_o:
            self.set_default_style(colors='linux')
    
    def create_shortcuts(self):
        inspect = create_shortcut(self._control.inspect_current_object,
                                  context='Console', name='Inspect current object',
                                  parent=self)
        clear_console = create_shortcut(self.clear_console, context='Console',
                                        name='Clear shell', parent=self)

        # Fixed shortcuts
        new_shortcut("Ctrl+T", self,
                     lambda: self.emit(SIGNAL("new_ipyclient()")))

        return [inspect, clear_console]

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

    #---- IPython private methods ---------------------------------------------
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
    
    def _handle_object_info_reply(self, rep):
        """
        Reimplement call tips to only show signatures, using the same style
        from our Editor and External Console too
        Note: For IPython 2-
        """
        self.log.debug("oinfo: %s", rep.get('content', ''))
        cursor = self._get_cursor()
        info = self._request_info.get('call_tip')
        if info and info.id == rep['parent_header']['msg_id'] and \
          info.pos == cursor.position():
            content = rep['content']
            if content.get('ismagic', False):
                call_info, doc = None, None
            else:
                call_info, doc = call_tip(content, format_call=True)
                if call_info is None and doc is not None:
                    name = content['name'].split('.')[-1]
                    argspec = getargspecfromtext(doc)
                    if argspec:
                        # This covers cases like np.abs, whose docstring is
                        # the same as np.absolute and because of that a proper
                        # signature can't be obtained correctly
                        call_info = name + argspec
                    else:
                        call_info = getsignaturefromtext(doc, name)
            if call_info:
                self._control.show_calltip(_("Arguments"), call_info,
                                           signature=True, color='#2D62FF')

    def _handle_inspect_reply(self, rep):
        """
        Reimplement call tips to only show signatures, using the same style
        from our Editor and External Console too
        Note: For IPython 3+
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
    
    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(IPythonShellWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(IPythonShellWidget, self).focusOutEvent(event)


#-----------------------------------------------------------------------------
# Client widget
#-----------------------------------------------------------------------------
class IPythonClient(QWidget, SaveHistoryMixin):
    """
    IPython client or frontend for Spyder

    This is a widget composed of a shell widget (i.e. RichIPythonWidget
    + our additions = IPythonShellWidget) and an WebView info widget to 
    print kernel error and other messages.
    """
    
    SEPARATOR = '%s##---(%s)---' % (os.linesep*2, time.ctime())
    
    def __init__(self, plugin, name, history_filename, connection_file=None, 
                 hostname=None, sshkey=None, password=None, 
                 kernel_widget_id=None, menu_actions=None):
        super(IPythonClient, self).__init__(plugin)
        SaveHistoryMixin.__init__(self)
        self.options_button = None
        
        # stop button and icon
        self.stop_button = None
        self.stop_icon = get_icon("stop.png")
        
        self.connection_file = connection_file
        self.kernel_widget_id = kernel_widget_id
        self.hostname = hostname
        self.sshkey = sshkey
        self.password = password
        self.name = name
        self.get_option = plugin.get_option
        self.shellwidget = IPythonShellWidget(config=self.shellwidget_config(),
                                              local_kernel=False)
        self.shellwidget.hide()
        self.infowidget = WebView(self)
        self.menu_actions = menu_actions
        self.history_filename = get_conf_path(history_filename)
        self.history = []
        self.namespacebrowser = None
        
        self.set_infowidget_font()
        self.loading_page = self._create_loading_page()
        self.infowidget.setHtml(self.loading_page)
        
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
        
        self.exit_callback = lambda: plugin.close_client(client=self)
        
    #------ Public API --------------------------------------------------------
    def show_shellwidget(self, give_focus=True):
        """Show shellwidget and configure it"""
        self.infowidget.hide()
        self.shellwidget.show()
        self.infowidget.setHtml(BLANK)
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
        self.shellwidget.executed.connect(self.auto_refresh_namespacebrowser)
        
        # To show a stop button, when executing a process
        self.shellwidget.executing.connect(self.enable_stop_button)
        
        # To hide a stop button after execution stopped
        self.shellwidget.executed.connect(self.disable_stop_button)
    
    def enable_stop_button(self):
        self.stop_button.setEnabled(True)
   
    def disable_stop_button(self):
        self.stop_button.setDisabled(True)
        
    def stop_button_click_handler(self):
        self.stop_button.setDisabled(True)
        # Interrupt computations or stop debugging
        if not self.shellwidget._reading:
            self.interrupt_kernel()
        else:
            self.shellwidget.write_to_stdin('exit')

    def show_kernel_error(self, error):
        """Show kernel initialization errors in infowidget"""
        # Remove explanation about how to kill the kernel (doesn't apply to us)
        error = error.split('issues/2049')[-1]
        # Remove unneeded blank lines at the beginning
        eol = sourcecode.get_eol_chars(error)
        if eol:
            error = error.replace(eol, '<br>')
        while error.startswith('<br>'):
            error = error[4:]
        # Remove connection message
        if error.startswith('To connect another client') or \
          error.startswith('[IPKernelApp] To connect another client'):
            error = error.split('<br>')
            error = '<br>'.join(error[2:])
        # Don't break lines in hyphens
        # From http://stackoverflow.com/q/7691569/438386
        error = error.replace('-', '&#8209')
            
        message = _("An error ocurred while starting the kernel")
        kernel_error_template = Template(KERNEL_ERROR)
        page = kernel_error_template.substitute(css_path=CSS_PATH,
                                                message=message,
                                                error=error)
        self.infowidget.setHtml(page)
    
    def show_restart_animation(self):
        self.shellwidget.hide()
        self.infowidget.setHtml(self.loading_page)
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

    def get_options_menu(self):
        """Return options menu"""
        restart_action = create_action(self, _("Restart kernel"),
                                       shortcut=QKeySequence("Ctrl+."),
                                       icon=get_icon('restart.png'),
                                       triggered=self.restart_kernel)
        restart_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        
        # Main menu
        if self.menu_actions is not None:
            actions = [restart_action, None] + self.menu_actions
        else:
            actions = [restart_action]
        return actions
    
    def get_toolbar_buttons(self):
        """Return toolbar buttons list"""
        #TODO: Eventually add some buttons (Empty for now)
        # (see for example: spyderlib/widgets/externalshell/baseshell.py)
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
                        text=_("Options"), icon=get_icon('tooloptions.png'))
                self.options_button.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(self)
                add_actions(menu, options)
                self.options_button.setMenu(menu)
        if self.options_button is not None:
            buttons.append(self.options_button)

        return buttons

    def add_actions_to_context_menu(self, menu):
        """Add actions to IPython widget context menu"""
        # See spyderlib/widgets/ipython.py for more details on this method
        inspect_action = create_action(self, _("Inspect current object"),
                                    QKeySequence(get_shortcut('console',
                                                    'inspect current object')),
                                    icon=get_std_icon('MessageBoxInformation'),
                                    triggered=self.inspect_object)
        clear_line_action = create_action(self, _("Clear line or block"),
                                          QKeySequence("Shift+Escape"),
                                          icon=get_icon('eraser.png'),
                                          triggered=self.clear_line)
        clear_console_action = create_action(self, _("Clear console"),
                                             QKeySequence(get_shortcut('console',
                                                               'clear shell')),
                                             icon=get_icon('clear.png'),
                                             triggered=self.clear_console)
        quit_action = create_action(self, _("&Quit"), icon='exit.png',
                                    triggered=self.exit_callback)
        add_actions(menu, (None, inspect_action, clear_line_action,
                           clear_console_action, None, quit_action))
        return menu
    
    def set_font(self, font):
        """Set IPython widget's font"""
        self.shellwidget._control.setFont(font)
        self.shellwidget.font = font
    
    def set_infowidget_font(self):
        font = get_font('inspector', 'rich_text')
        self.infowidget.set_font(font)
    
    def interrupt_kernel(self):
        """Interrupt the associanted Spyder kernel if it's running"""
        self.shellwidget.request_interrupt_kernel()
    
    def restart_kernel(self):
        """Restart the associanted Spyder kernel"""
        self.shellwidget.request_restart_kernel()
    
    def inspect_object(self):
        """Show how to inspect an object with our object inspector"""
        self.shellwidget._control.inspect_current_object()
    
    def clear_line(self):
        """Clear a console line"""
        self.shellwidget._keyboard_quit()
    
    def clear_console(self):
        """Clear the whole console"""
        self.shellwidget.execute("%clear")
    
    def if_kernel_dies(self, t):
        """
        Show a message in the console if the kernel dies.
        t is the time in seconds between the death and showing the message.
        """
        message = _("It seems the kernel died unexpectedly. Use "
                    "'Restart kernel' to continue using this console.")
        self.shellwidget._append_plain_text(message + '\n')
    
    def update_history(self):
        self.history = self.shellwidget._history
    
    def set_backend_for_mayavi(self, command):
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
    
    def interrupt_message(self):
        """
        Print an interrupt message when the client is connected to an external
        kernel
        """
        message = _("Kernel process is either remote or unspecified. "
                    "Cannot interrupt")
        QMessageBox.information(self, "IPython", message)
    
    def restart_message(self):
        """
        Print a restart message when the client is connected to an external
        kernel
        """
        message = _("Kernel process is either remote or unspecified. "
                    "Cannot restart.")
        QMessageBox.information(self, "IPython", message)

    def set_namespacebrowser(self, namespacebrowser):
        """Set namespace browser widget"""
        self.namespacebrowser = namespacebrowser

    def auto_refresh_namespacebrowser(self):
        """Refresh namespace browser"""
        if self.namespacebrowser:
            self.namespacebrowser.refresh_table()
    
    def shellwidget_config(self):
        """Generate a Config instance for shell widgets using our config
        system
        
        This lets us create each widget with its own config (as opposed to
        IPythonQtConsoleApp, where all widgets have the same config)
        """
        # ---- IPython config ----
        try:
            profile_path = osp.join(get_ipython_dir(), 'profile_default')
            full_ip_cfg = load_pyconfig_files(['ipython_qtconsole_config.py'],
                                              profile_path)
            
            # From the full config we only select the IPythonWidget section
            # because the others have no effect here.
            ip_cfg = Config({'IPythonWidget': full_ip_cfg.IPythonWidget})
        except:
            ip_cfg = Config()
       
        # ---- Spyder config ----
        spy_cfg = Config()
        
        # Make the pager widget a rich one (i.e a QTextEdit)
        spy_cfg.IPythonWidget.kind = 'rich'
        
        # Gui completion widget
        gui_comp_o = self.get_option('use_gui_completion')
        completions = {True: 'droplist', False: 'ncurses'}
        spy_cfg.IPythonWidget.gui_completion = completions[gui_comp_o]

        # Pager
        pager_o = self.get_option('use_pager')
        if pager_o:
            spy_cfg.IPythonWidget.paging = 'inside'
        else:
            spy_cfg.IPythonWidget.paging = 'none'
        
        # Calltips
        calltips_o = self.get_option('show_calltips')
        spy_cfg.IPythonWidget.enable_calltips = calltips_o

        # Buffer size
        buffer_size_o = self.get_option('buffer_size')
        spy_cfg.IPythonWidget.buffer_size = buffer_size_o
        
        # Prompts
        in_prompt_o = self.get_option('in_prompt')
        out_prompt_o = self.get_option('out_prompt')
        if in_prompt_o:
            spy_cfg.IPythonWidget.in_prompt = in_prompt_o
        if out_prompt_o:
            spy_cfg.IPythonWidget.out_prompt = out_prompt_o
        
        # Merge IPython and Spyder configs. Spyder prefs will have prevalence
        # over IPython ones
        ip_cfg._merge(spy_cfg)
        return ip_cfg
    
    #------ Private API -------------------------------------------------------
    def _create_loading_page(self):
        loading_template = Template(LOADING)
        loading_img = get_image_path('loading_sprites.png')
        if os.name == 'nt':
            loading_img = loading_img.replace('\\', '/')
        message = _("Connecting to kernel...")
        page = loading_template.substitute(css_path=CSS_PATH,
                                           loading_img=loading_img,
                                           message=message)
        return page
    
    #---- Qt methods ----------------------------------------------------------
    def closeEvent(self, event):
        """
        Reimplement Qt method to stop sending the custom_restart_kernel_died
        signal
        """
        kc = self.shellwidget.kernel_client
        if kc is not None:
            kc.hb_channel.pause()
