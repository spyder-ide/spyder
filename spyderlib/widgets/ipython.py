# -*- coding:utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.13+ client's widget
"""

# Stdlib imports
import os
import os.path as osp
from string import Template
import time

# Qt imports
from spyderlib.qt.QtGui import (QTextEdit, QKeySequence, QShortcut, QWidget,
                                QMenu, QHBoxLayout, QToolButton, QVBoxLayout,
                                QMessageBox)
from spyderlib.qt.QtCore import SIGNAL, Qt
from spyderlib.utils.qthelpers import restore_keyevent

# IPython imports
try:  # 1.0
    from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
except ImportError: # 0.13
    from IPython.frontend.qt.console.rich_ipython_widget import RichIPythonWidget

# Local imports
from spyderlib.baseconfig import (get_conf_path, get_image_path,
                                  get_module_source_path, _)
from spyderlib.config import CONF
from spyderlib.guiconfig import get_font
from spyderlib.utils.qthelpers import (get_std_icon, create_toolbutton,
                                       add_actions, create_action, get_icon)
from spyderlib.utils import programs
from spyderlib.widgets.mixins import (BaseEditMixin, InspectObjectMixin,
                                      SaveHistoryMixin, TracebackLinksMixin)
from spyderlib.widgets.browser import WebView

#-----------------------------------------------------------------------------
# Templates
#-----------------------------------------------------------------------------
# Using the same css file from the Object Inspector for now. Maybe
# later it'll be a good idea to create a new one.
OI_UTILS_PATH = get_module_source_path('spyderlib', osp.join('utils',
                                                             'inspector'))
CSS_PATH = osp.join(OI_UTILS_PATH, 'static', 'css')

BLANK = \
r"""<html>
<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
</head>
</html>
"""

LOADING = \
r"""<html>
<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
  <link rel="stylesheet" href="file:///${css_path}/default.css" type="text/css"/>
</head>
<body>
  <div class="loading">
    <img src="file:///${loading_img}"/>&nbsp;&nbsp;${message}
  </div>
</body>
</html>
"""

KERNEL_ERROR = \
r"""<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <link rel="stylesheet" href="file:///${css_path}/default.css" type="text/css"/>
</head>
<body>
  <div id="kernel-warning">${message}</div>
  <div id="kernel-error">${error}</div>
</body>
</html>
"""

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
        self.calltips = False        # To not use Spyder calltips
        self.found_results = []
    
    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.emit(SIGNAL("visibility_changed(bool)"), True)
    
    def _key_question(self, text):
        """ Action for '?' and '(' """
        parent = self.parentWidget()
        self.current_prompt_pos = parent._prompt_pos
        if self.get_current_line_to_cursor():
            last_obj = self.get_last_obj()
            if last_obj and not last_obj.isdigit():
                self.show_docstring(last_obj)
        self.insert_text(text)
    
    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        
        if key == Qt.Key_Question and not self.has_selected_text() and \
          self.set_inspector_enabled:
            self._key_question(text)
        elif key == Qt.Key_ParenLeft and not self.has_selected_text() \
          and self.set_inspector_enabled:
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
class SpyderIPythonWidget(RichIPythonWidget):
    """
    Spyder's IPython widget

    This class has custom control and page_control widgets, additional methods
    to provide missing functionality and a couple more keyboard shortcuts.
    """
    def __init__(self, *args, **kw):
        # To override the Qt widget used by RichIPythonWidget
        self.custom_control = IPythonControlWidget
        self.custom_page_control = IPythonPageControlWidget
        super(SpyderIPythonWidget, self).__init__(*args, **kw)
        self.set_background_color()
        
        # --- Spyder variables ---
        self.ipyclient = None
        
        # --- Keyboard shortcuts ---
        inspectsc = QShortcut(QKeySequence("Ctrl+I"), self,
                              self._control.inspect_current_object)
        inspectsc.setContext(Qt.WidgetWithChildrenShortcut)
        clear_consolesc = QShortcut(QKeySequence("Ctrl+L"), self,
                                    self.clear_console)
        clear_consolesc.setContext(Qt.WidgetWithChildrenShortcut)
        
        # --- IPython variables ---
        # To send an interrupt signal to the Spyder kernel
        self.custom_interrupt = True
        
        # To restart the Spyder kernel in case it dies
        self.custom_restart = True
    
    #---- Public API ----------------------------------------------------------
    def set_ipyclient(self, ipyclient):
        """Bind this IPython widget to an IPython client widget
        (see spyderlib/plugins/ipythonconsole.py)"""
        self.ipyclient = ipyclient
        self.exit_requested.connect(ipyclient.exit_callback)
    
    def show_banner(self):
        """Banner for IPython widgets with pylab message"""
        from IPython.core.usage import default_gui_banner
        banner = default_gui_banner
        
        pylab_o = CONF.get('ipython_console', 'pylab', True)
        autoload_pylab_o = CONF.get('ipython_console', 'pylab/autoload', True)
        mpl_installed = programs.is_module_installed('matplotlib')
        if mpl_installed and (pylab_o and autoload_pylab_o):
            backend_o = CONF.get('ipython_console', 'pylab/backend', 0)
            backends = {0: 'module://IPython.zmq.pylab.backend_inline',
                        1: 'Qt4Agg', 2: 'Qt4Agg', 3: 'MacOSX', 4: 'GTKAgg',
                        5: 'WXAgg', 6: 'TKAgg'}
            pylab_013_message = """
Welcome to pylab, a matplotlib-based Python environment [backend: %s].
For more information, type 'help(pylab)'.\n""" % backends[backend_o]
            pylab_1_message = """
Populating the interactive namespace from numpy and matplotlib"""
            if programs.is_module_installed('IPython', '>=1.0'):
                banner = banner + pylab_1_message
            else:
                banner = banner + pylab_013_message
        
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
    
    def clear_console(self):
        self.execute("%clear")
        
    def write_to_stdin(self, line):
        """
        Send raw characters to the IPython kernel through stdin
        but only if the kernel is currently looking for raw input.
        """
        if self._reading:
            if programs.is_module_installed('IPython', '>=1.0'):
                self.kernel_client.stdin_channel.input(line)
            else:
                self.kernel_manager.stdin_channel.input(line)
    
    def set_background_color(self):
        lightbg_o = CONF.get('ipython_console', 'light_color', True)
        if not lightbg_o:
            self.set_default_style(colors='linux')

    #---- IPython private methods ---------------------------------------------
    def _context_menu_make(self, pos):
        """Reimplement the IPython context menu"""
        menu = super(SpyderIPythonWidget, self)._context_menu_make(pos)
        return self.ipyclient.add_actions_to_context_menu(menu)
    
    def _banner_default(self):
        """
        Reimplement banner creation to let the user decide if he wants a
        banner or not
        """
        banner_o = CONF.get('ipython_console', 'show_banner', True)
        if banner_o:
            return self.show_banner()
        else:
            return ''
    
    #---- Qt methods ----------------------------------------------------------
    def focusInEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(SpyderIPythonWidget, self).focusInEvent(event)
    
    def focusOutEvent(self, event):
        """Reimplement Qt method to send focus change notification"""
        self.emit(SIGNAL('focus_changed()'))
        return super(SpyderIPythonWidget, self).focusOutEvent(event)

#-----------------------------------------------------------------------------
# Client widget
#-----------------------------------------------------------------------------
class IPythonClient(QWidget, SaveHistoryMixin):
    """
    Spyder IPython client or frontend.

    This is a layer on top of the IPython Qt widget (i.e. RichIPythonWidget +
    our additions = SpyderIPythonWidget), which becomes the ipywidget attribute
    of this class. We are doing this for several reasons:

    1. To add more variables and methods needed to connect the widget to other
       Spyder plugins and also increase its funcionality.
    2. To make it clear what has been added by us to IPython widgets.
    3. To avoid possible name conflicts between our widgets and theirs (e.g.
       self.history and self._history, respectively)
    """
    
    CONF_SECTION = 'ipython'
    SEPARATOR = '%s##---(%s)---' % (os.linesep*2, time.ctime())
    
    def __init__(self, plugin, history_filename, connection_file=None,
                 kernel_widget_id=None, menu_actions=None):
        super(IPythonClient, self).__init__(plugin)
        SaveHistoryMixin.__init__(self)
        self.options_button = None

        self.connection_file = connection_file
        self.kernel_widget_id = kernel_widget_id
        self.name = ''
        self.ipywidget = SpyderIPythonWidget(config=plugin.ipywidget_config(),
                                             local_kernel=False)
        self.ipywidget.hide()
        self.loading_widget = WebView(self)
        self.menu_actions = menu_actions
        self.history_filename = get_conf_path(history_filename)
        self.history = []
        self.namespacebrowser = None
        
        self.set_loading_widget_font()
        self.loading_page = self._create_loading_page()
        self.loading_widget.setHtml(self.loading_page)
        
        vlayout = QVBoxLayout()
        toolbar_buttons = self.get_toolbar_buttons()
        hlayout = QHBoxLayout()
        for button in toolbar_buttons:
            hlayout.addWidget(button)
        vlayout.addLayout(hlayout)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.ipywidget)
        vlayout.addWidget(self.loading_widget)
        self.setLayout(vlayout)
        
        self.exit_callback = lambda: plugin.close_console(client=self)
        
    #------ Public API --------------------------------------------------------
    def show_ipywidget(self):
        """Show ipywidget and configure it"""
        self.loading_widget.hide()
        self.ipywidget.show()
        self.loading_widget.setHtml(BLANK)
        self.get_control().setFocus()
        
        # Connect the IPython widget to this IPython client:
        # (see spyderlib/widgets/ipython.py for more details about this)
        self.ipywidget.set_ipyclient(self)
        
        # To save history
        self.ipywidget.executing.connect(
                                      lambda c: self.add_to_history(command=c))
        
        # To update history after execution
        self.ipywidget.executed.connect(self.update_history)
        
        # To update the Variable Explorer after execution
        self.ipywidget.executed.connect(self.auto_refresh_namespacebrowser)
    
    def show_kernel_error(self, error):
        """Show kernel initialization errors in the client"""
        # Remove explanation about how to kill the kernel
        # (doesn't apply to us)
        error = error.split('issues/2049')[-1]
        error = error.replace('\n', '<br>')
        # Remove unneeded blank lines at the beginning
        while error.startswith('<br>'):
            error = error[4:]
        message = _("An error ocurred while starting the kernel!")
        kernel_error_template = Template(KERNEL_ERROR)
        page = kernel_error_template.substitute(css_path=CSS_PATH,
                                                message=message,
                                                error=error)
        self.loading_widget.setHtml(page)
    
    def show_restart_animation(self):
        self.ipywidget.hide()
        self.loading_widget.setHtml(self.loading_page)
        self.loading_widget.show()
    
    def get_name(self):
        """Return client name"""
        return _("Console") + " " + self.name
    
    def get_control(self):
        """Return the text widget (or similar) to give focus to"""
        # page_control is the widget used for paging
        page_control = self.ipywidget._page_control
        if page_control and page_control.isVisible():
            return page_control
        else:
            return self.ipywidget._control

    def get_options_menu(self):
        """Return options menu"""
        # Kernel
        self.interrupt_action = create_action(self, _("Interrupt kernel"),
                                              icon=get_icon('terminate.png'),
                                              triggered=self.interrupt_kernel)
        self.restart_action = create_action(self, _("Restart kernel"),
                                            icon=get_icon('restart.png'),
                                            triggered=self.restart_kernel)
        # Main menu
        if self.menu_actions is not None:
            actions = [self.interrupt_action, self.restart_action, None] +\
                      self.menu_actions
        else:
            actions = [self.interrupt_action, self.restart_action]
        return actions
    
    def get_toolbar_buttons(self):
        """Return toolbar buttons list"""
        #TODO: Eventually add some buttons (Empty for now)
        # (see for example: spyderlib/widgets/externalshell/baseshell.py)
        buttons = []
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
                                    QKeySequence("Ctrl+I"),
                                    icon=get_std_icon('MessageBoxInformation'),
                                    triggered=self.inspect_object)
        clear_line_action = create_action(self, _("Clear line or block"),
                                          QKeySequence("Shift+Escape"),
                                          icon=get_icon('eraser.png'),
                                          triggered=self.clear_line)
        clear_console_action = create_action(self, _("Clear console"),
                                             QKeySequence("Ctrl+L"),
                                             icon=get_icon('clear.png'),
                                             triggered=self.clear_console)
        quit_action = create_action(self, _("&Quit"), icon='exit.png',
                                    triggered=self.exit_callback)
        add_actions(menu, (None, inspect_action, clear_line_action,
                           clear_console_action, None, quit_action))
        return menu
    
    def set_font(self, font):
        """Set IPython widget's font"""
        self.ipywidget.font = font
    
    def set_loading_widget_font(self):
        font = get_font('inspector', 'rich_text')
        self.loading_widget.set_font(font)
    
    def interrupt_kernel(self):
        """Interrupt the associanted Spyder kernel if it's running"""
        self.ipywidget.request_interrupt_kernel()
    
    def restart_kernel(self):
        """Restart the associanted Spyder kernel"""
        self.ipywidget.request_restart_kernel()
    
    def inspect_object(self):
        """Show how to inspect an object with our object inspector"""
        self.ipywidget._control.inspect_current_object()
    
    def clear_line(self):
        """Clear a console line"""
        self.ipywidget._keyboard_quit()
    
    def clear_console(self):
        """Clear the whole console"""
        self.ipywidget.execute("%clear")
    
    def if_kernel_dies(self, t):
        """
        Show a message in the console if the kernel dies.
        t is the time in seconds between the death and showing the message.
        """
        message = _("It seems the kernel died unexpectedly. Use "
                    "'Restart kernel' to continue using this console.")
        self.ipywidget._append_plain_text(message + '\n')
    
    def update_history(self):
        self.history = self.ipywidget._history
    
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
    
    #------ Private API -------------------------------------------------------
    def _create_loading_page(self):
        loading_template = Template(LOADING)
        loading_img = get_image_path('loading.gif')
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
        if programs.is_module_installed('IPython', '>=1.0'):
            kc = self.ipywidget.kernel_client
            if kc is not None:
                kc.hb_channel.pause()
        else:
            self.ipywidget.custom_restart = False
