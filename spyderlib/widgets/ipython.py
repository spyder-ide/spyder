# -*- coding:utf-8 -*-
#
# Copyright © 2011-2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython v0.13+ client's widget
"""

# IPython imports
try:  # 1.0
    from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
except ImportError: # 0.13
    from IPython.frontend.qt.console.rich_ipython_widget import RichIPythonWidget

# Qt imports
from spyderlib.qt.QtGui import QTextEdit, QKeySequence, QShortcut
from spyderlib.qt.QtCore import SIGNAL, Qt
from spyderlib.utils.qthelpers import restore_keyevent

# Local imports
from spyderlib.config import CONF
from spyderlib.utils import programs
from spyderlib.widgets.mixins import (BaseEditMixin, InspectObjectMixin,
                                      TracebackLinksMixin)


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
            pylab_message = """
Welcome to pylab, a matplotlib-based Python environment [backend: %s].
For more information, type 'help(pylab)'.\n""" % backends[backend_o]
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
