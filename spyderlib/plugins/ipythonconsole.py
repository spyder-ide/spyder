# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""IPython Console plugin

Handles IPython clients (and in the future, will handle IPython kernels too
-- meanwhile, the external console plugin is handling them)"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QVBoxLayout, QMessageBox, QWidget, QGroupBox,
                                QLineEdit, QInputDialog, QTabWidget, QMenu,
                                QFontComboBox, QHBoxLayout, QApplication,
                                QToolButton)
from spyderlib.qt.QtCore import SIGNAL, Qt

import sys
import re

# Local imports
from spyderlib.baseconfig import _
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import (create_action, create_toolbutton,
                                       add_actions, mimedata2url)
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.ipython import IPythonApp, set_ipython_exit_callback
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage


class IPythonConsoleConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("IPython console")

    def setup_page(self):
        font_group = self.create_fontgroup(option=None, text=None,
                                    fontfilters=QFontComboBox.MonospacedFonts)

        # Interface Group
        interface_group = QGroupBox(_("Interface"))
        interface_layout = QVBoxLayout()
        interface_group.setLayout(interface_layout)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(font_group, interface_group),
                    _("Display"))

        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)


#XXX: For now, we add this layer to the IPython widget (which is the
#     `ipython_widget` attribute of this `IPythonClient` class) even if this is
#     quite featureless: the IPythonClient has a vertical layout which contains
#     only the IPython widget inside it. So we could have directly made the 
#     IPythonClient class inherit from the IPython widget's class. However,
#     the latter is not yet clearly defined: IPython API is quite unclear and 
#     confusing for this matter, so I prefered to add this layer. But that's 
#     just a start: we should replace it by the correct inheritance logic in 
#     time.
class IPythonClient(QWidget):
    """Find in files DockWidget"""
    CONF_SECTION = 'ipython'
    def __init__(self, parent, connection_file, kernel_widget_id, client_name,
                 ipython_widget):
        super(IPythonClient, self).__init__(parent)
        
        self.options_button = None

        self.connection_file = connection_file
        self.kernel_widget_id = kernel_widget_id
        self.client_name = client_name
        
        self.ipython_widget = ipython_widget
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ipython_widget)
        self.setLayout(layout)
        
    #------ Public API --------------------------------------------------------
    def get_name(self):
        """Return client name"""
        return _("Client") + " " + self.client_name
    
    def get_control(self):
        """Return the QPlainTextEdit widget (or similar) to give focus to"""
        return self.ipython_widget._control
    
    def set_exit_callback(self, exit_callback):
        """Set IPython widget exit callback"""
        set_ipython_exit_callback(self.ipython_widget, exit_callback)

    def get_options_menu(self):
        """Return options menu"""
        #TODO: Eventually add some options (Empty for now)
        # (see for example: spyderlib/widgets/externalshell/baseshell.py)
        return []
    
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
    
    def set_font(self, font):
        """Set IPython widget's font"""
        self.ipython_widget.font = font
            

class IPythonConsole(SpyderPluginWidget):
    """IPython Console plugin"""
    CONF_SECTION = 'ipython_console'
    CONFIGWIDGET_CLASS = IPythonConsoleConfigPage
    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)
        
        self.ipython_app = None

        self.tabwidget = None
        self.menu_actions = None
        
        self.shellwidgets = []
        
        # Initialize plugin
        self.initialize_plugin()
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        if hasattr(self.tabwidget, 'setDocumentMode')\
           and not sys.platform == 'darwin':
            # Don't set document mode to true on OSX because it generates
            # a crash when the console is detached from the main window
            # Fixes Issue 561
            self.tabwidget.setDocumentMode(True)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh_plugin)
        self.connect(self.tabwidget, SIGNAL('move_data(int,int)'),
                     self.move_tab)
                     
        self.tabwidget.set_close_function(self.close_console)

        layout.addWidget(self.tabwidget)
        
        self.setLayout(layout)
            
        # Accepting drops
        self.setAcceptDrops(True)

    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('IPython console')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('ipython.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        shellwidget = self.tabwidget.currentWidget()
        if shellwidget is not None:
            return shellwidget.get_control()
        
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        client_action = create_action(self, _("New IPython client..."), None,
                    'ipython.png', _("Open a new IPython client (frontend)"),
                    triggered=self.new_client)

        interact_menu_actions = [None, client_action]
        self.menu_actions = [client_action]
        
        self.main.interact_menu_actions += interact_menu_actions
        
        return self.menu_actions+interact_menu_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        for shellwidget in self.shellwidgets:
            shellwidget.close()
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        clientwidget = None
        if self.tabwidget.count():
            clientwidget = self.tabwidget.currentWidget()
            clientwidget.get_control().setFocus()
            widgets = clientwidget.get_toolbar_buttons()+[5]
        else:
            widgets = []
        self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})
        self.emit(SIGNAL('update_plugin_title()'))
    
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        font = self.get_plugin_font()
        for shellwidget in self.shellwidgets:
            shellwidget.set_font(font)
    
    #------ Public API --------------------------------------------------------
    def get_clients(self):
        """Return IPython client widgets list"""
        return [sw for sw in self.shellwidgets
                if isinstance(sw, IPythonClient)]
        
#    def get_kernels(self):
#        """Return IPython kernel widgets list"""
#        return [sw for sw in self.shellwidgets
#                if isinstance(sw, IPythonKernel)]
#        

    def get_focus_client(self):
        """Return client shellwidget which has focus, if any"""
        widget = QApplication.focusWidget()
        for client in self.get_clients():
            if widget is client or widget is client.get_control():
                return client

    def new_client(self, connection_file=None, kernel_widget_id=None):
        """Create a new IPython client"""
        cf = connection_file
        if cf is None:
            example = _('(example: `kernel-3764.json`, or simply `3764`)')
            while True:
                cf, valid = QInputDialog.getText(self, _('IPython'),
                          _('IPython kernel connection file:')+'\n'+example,
                          QLineEdit.Normal)
                if valid:
                    cf = str(cf)
                    if cf.isdigit():
                        cf = 'kernel-%s.json' % cf
                    if re.match('^kernel-(\d+).json', cf):
                        break
                else:
                    return

        # Generating the client name
        match = re.match('^kernel-(\d+).json', cf)
        count = 0
        while True:
            client_name = match.groups()[0]+'/'+chr(65+count)
            for clw in self.get_clients():
                if clw.client_name == client_name:
                    break
            else:
                break
            count += 1

        # Creating the IPython client widget
        try:
            self.register_client(cf, kernel_widget_id, client_name)
        except (IOError, UnboundLocalError):
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to IPython kernel "
                                   "<b>`%s`") % cf)
            return

    def register_client(self, connection_file, kernel_widget_id, client_name):
        """Register new IPython client"""
        iapp = self.ipython_app
        argv = ['--existing']+[connection_file]
        if iapp is None:
            self.ipython_app = iapp = IPythonApp()
            iapp.initialize_all_except_qt(argv=argv)
        iapp.parse_command_line(argv=argv)
        ipython_widget = iapp.new_client_from_existing()

        shellwidget = IPythonClient(self, connection_file, kernel_widget_id,
                                    client_name, ipython_widget)
        exit_callback = lambda widget=shellwidget:\
                            self.close_console(widget=shellwidget)
        shellwidget.set_exit_callback(exit_callback)
        
        # Apply settings to newly created client widget:
        shellwidget.set_font( self.get_plugin_font() )
        
        self.add_tab(shellwidget, name=shellwidget.get_name())
        self.connect(shellwidget, SIGNAL('focus_changed()'),
                     lambda: self.emit(SIGNAL('focus_changed()')))
    
    def close_related_ipython_clients(self, client):
        """Close all IPython clients related to *connection_file*,
        except the plugin *except_this_one*"""
        for clw in self.shellwidgets[:]:
            if clw is not client and\
               clw.connection_file == client.connection_file:
                self.close_console(widget=clw)
    
    def get_ipython_widget(self, kernel_widget_id):
        """Return IPython widget (ipython_plugin.ipython_widget) 
        associated to kernel_widget_id"""
        for clw in self.shellwidgets:
            if clw.kernel_widget_id == kernel_widget_id:
                return clw.ipython_widget
        else:
            raise ValueError, "Unknown kernel widget ID %r" % kernel_widget_id
        
    def add_tab(self, widget, name):
        """Add tab"""
        self.shellwidgets.append(widget)
        index = self.tabwidget.addTab(widget, get_icon('ipython.png'), name)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        widget.get_control().setFocus()
        
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        shell = self.shellwidgets.pop(index_from)
        self.shellwidgets.insert(index_to, shell)
        self.emit(SIGNAL('update_plugin_title()'))
        
    def close_console(self, index=None, widget=None):
        """Close console tab from index or widget (or close current tab)"""
        if not self.tabwidget.count():
            return
        if widget is not None:
            index = self.tabwidget.indexOf(widget)
        if index is None and widget is None:
            index = self.tabwidget.currentIndex()
        if index is not None:
            widget = self.tabwidget.widget(index)
        if isinstance(widget, IPythonClient):
            console = self.main.extconsole
            idx = console.get_shell_index_from_id(widget.kernel_widget_id)
            if idx is not None:
                answer = QMessageBox.question(self, self.get_plugin_title(),
                            _("%s will be closed.\n"
                              "Do you want to kill the associated kernel and "
                              "the all of its clients?") % widget.get_name(),
                            QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
                if answer == QMessageBox.Yes:
                    console.close_console(index=idx)
                    self.close_related_ipython_clients(widget)
                elif answer == QMessageBox.Cancel:
                    return
        widget.close()
        self.tabwidget.removeTab(index)
        self.shellwidgets.pop(index)
        self.emit(SIGNAL('update_plugin_title()'))

    #TODO: try and reimplement this block
    # (this is still the original code block copied from externalconsole.py)
#    def go_to_error(self, text):
#        """Go to error if relevant"""
#        match = get_error_match(unicode(text))
#        if match:
#            fname, lnb = match.groups()
#            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
#                      osp.abspath(fname), int(lnb), '')
            
    #----Drag and drop
    #TODO: try and reimplement this block
    # (this is still the original code block copied from externalconsole.py)
#    def dragEnterEvent(self, event):
#        """Reimplement Qt method
#        Inform Qt about the types of data that the widget accepts"""
#        source = event.mimeData()
#        if source.hasUrls():
#            if mimedata2url(source):
#                pathlist = mimedata2url(source)
#                shellwidget = self.tabwidget.currentWidget()
#                if all([is_python_script(unicode(qstr)) for qstr in pathlist]):
#                    event.acceptProposedAction()
#                elif shellwidget is None or not shellwidget.is_running():
#                    event.ignore()
#                else:
#                    event.acceptProposedAction()
#            else:
#                event.ignore()
#        elif source.hasText():
#            event.acceptProposedAction()            
#            
#    def dropEvent(self, event):
#        """Reimplement Qt method
#        Unpack dropped data and handle it"""
#        source = event.mimeData()
#        shellwidget = self.tabwidget.currentWidget()
#        if source.hasText():
#            qstr = source.text()
#            if is_python_script(unicode(qstr)):
#                self.start(qstr)
#            elif shellwidget:
#                shellwidget.shell.insert_text(qstr)
#        elif source.hasUrls():
#            pathlist = mimedata2url(source)
#            if all([is_python_script(unicode(qstr)) for qstr in pathlist]):
#                for fname in pathlist:
#                    self.start(fname)
#            elif shellwidget:
#                shellwidget.shell.drop_pathlist(pathlist)
#        event.acceptProposedAction()

