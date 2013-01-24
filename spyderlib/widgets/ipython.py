# -*- coding:utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.13+ client widget
"""

# IPython imports
from IPython.frontend.qt.kernelmanager import QtKernelManager
from IPython.frontend.qt.console.qtconsoleapp import IPythonQtConsoleApp
from IPython.lib.kernel import find_connection_file
from IPython.core.application import BaseIPythonApplication
from IPython.frontend.qt.console.qtconsoleapp import IPythonConsoleApp
from IPython.frontend.qt.console.rich_ipython_widget import RichIPythonWidget

from spyderlib.qt.QtGui import QTextEdit, QKeySequence, QShortcut
from spyderlib.qt.QtCore import SIGNAL, Qt
from spyderlib.utils.qthelpers import restore_keyevent

# Local imports
from spyderlib.config import CONF
from spyderlib.widgets.sourcecode import mixins


class IPythonControlWidget(QTextEdit, mixins.BaseEditMixin,
                           mixins.TracebackLinksMixin,
                           mixins.InspectObjectMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins to use as the
    control widget for IPython clients
    """
    QT_CLASS = QTextEdit
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        mixins.BaseEditMixin.__init__(self)
        mixins.TracebackLinksMixin.__init__(self)
        mixins.InspectObjectMixin.__init__(self)
        self.calltips = False # To not use Spyder calltips
        self.found_results = []
    
    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.emit(SIGNAL("visibility_changed(bool)"), True)
    
    def _key_question(self, text):
        """Action for '?'"""
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
        
        if key == Qt.Key_Question and not self.has_selected_text():
            self._key_question(text)
        else:
            # Let the parent widget handle the key press event
            QTextEdit.keyPressEvent(self, event)


class IPythonPageControlWidget(QTextEdit, mixins.BaseEditMixin):
    """
    Subclass of QTextEdit with features from Spyder's mixins.BaseEditMixin to
    use as the paging widget for IPython clients
    """
    QT_CLASS = QTextEdit
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        mixins.BaseEditMixin.__init__(self)
        self.found_results = []
    
    def showEvent(self, event):
        """Reimplement Qt Method"""
        self.emit(SIGNAL("visibility_changed(bool)"), True)
    
    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        
        if key == Qt.Key_Slash and self.isVisible():
            self.emit(SIGNAL("show_find_widget()"))


class SpyderIPythonWidget(RichIPythonWidget):
    """Spyder's IPython widget"""
    def __init__(self, *args, **kw):
        # To override the Qt widget used by RichIPythonWidget
        self.custom_control = IPythonControlWidget
        self.custom_page_control = IPythonPageControlWidget
        super(SpyderIPythonWidget, self).__init__(*args, **kw)
        
        # --- Spyder variables ---
        self.ipython_client = None
        
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
    def set_ipython_client(self, ipython_client):
        """Bind this IPython widget to an IPython client widget
        (see spyderlib/plugins/ipythonconsole.py)"""
        self.ipython_client = ipython_client
        self.exit_requested.connect(ipython_client.exit_callback)
    
    def show_banner(self):
        """Banner for IPython clients with pylab message"""
        from IPython.core.usage import default_gui_banner
        banner = default_gui_banner
        
        pylab_o = CONF.get('ipython_console', 'pylab', True)
        if pylab_o:
            backend_o = CONF.get('ipython_console', 'pylab/backend', 0)
            backends = {0: 'module://IPython.zmq.pylab.backend_inline',
                        1: 'Qt4Agg', 2: 'Qt4Agg', 3: 'MacOSX', 4: 'GTKAgg',
                        5: 'WXAgg', 6: 'TKAgg'}
            pylab_message = """
Welcome to pylab, a matplotlib-based Python environment [backend: %s].
For more information, type 'help(pylab)'.\n""" % backends[backend_o]
            banner = banner + pylab_message
        
        sympy_o = CONF.get('ipython_console', 'symbolic_math', True)
        if sympy_o:
            lines = """
These commands were executed:
from __future__ import division
from sympy import *
x, y, z, t = symbols('x y z t')
k, m, n = symbols('k m n', integer=True)
f, g, h = symbols('f g h', cls=Function)
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
            self.kernel_manager.stdin_channel.input(line)

    #---- IPython private methods ---------------------------------------------
    def _context_menu_make(self, pos):
        """Reimplement the IPython context menu"""
        menu = super(SpyderIPythonWidget, self)._context_menu_make(pos)
        return self.ipython_client.add_actions_to_context_menu(menu)
    
    def _banner_default(self):
        """Reimplement banner creation to let the user decide if he wants a
        banner or not"""
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


#TODO: We have to ask an IPython developer to read this, I'm sure that we are
#      not using the IPython API as it should be... at least I hope so!
#----> See "IPython developers review" [1] & [2] in plugins/ipythonconsole.py
#----> See "IPython developers review" [3] here below
#==============================================================================
# For IPython developers review [3]
class IPythonApp(IPythonQtConsoleApp):
    def initialize_all_except_qt(self, argv=None):
        BaseIPythonApplication.initialize(self, argv=argv)
        IPythonConsoleApp.initialize(self, argv=argv)
    
    def create_kernel_manager(self, connection_file=None):
        """Create a kernel manager"""
        cf = find_connection_file(connection_file, profile='default')
        kernel_manager = QtKernelManager(connection_file=cf,
                                         config=self.config)
        kernel_manager.load_connection_file()
        kernel_manager.start_channels()
        return kernel_manager

    def config_color_scheme(self):
        """Set the color scheme for clients.
        
        In 0.13 this property needs to be set on the App and not on the
        widget, so that the widget can be initialized with the right
        scheme.
        TODO: This is a temporary measure until we create proper stylesheets
        for the widget using our own color schemes, which by the way can be
        passed directly to it.
        """
        dark_color_o = CONF.get('ipython_console', 'dark_color', False)
        if dark_color_o:
            self.config.ZMQInteractiveShell.colors = 'Linux'
        else:
            self.config.ZMQInteractiveShell.colors = 'LightBG'
    
    def create_new_client(self, connection_file=None, config=None):
        """Create and return a new client (frontend)
        from connection file basename"""
        kernel_manager = self.create_kernel_manager(connection_file)
        self.config_color_scheme()
        if config is not None:
            widget = SpyderIPythonWidget(config=config, local_kernel=False)
        else:
            widget = SpyderIPythonWidget(config=self.config, local_kernel=False)
        self.init_colors(widget)
        widget.kernel_manager = kernel_manager
        return widget
#==============================================================================


if __name__ == '__main__':
    from spyderlib.qt.QtGui import QApplication
    
    iapp = IPythonApp()
    iapp.initialize(["--pylab=inline"])
    
    widget1 = iapp.create_new_client()
    widget1.show()

    # Ugly pause but that's just for testing    
    import time
    time.sleep(2)
    
    widget2 = iapp.create_new_client()
    widget2.show()
    
    # Start the application main loop.
    QApplication.instance().exec_()
