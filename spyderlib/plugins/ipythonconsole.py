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
                                QToolButton, QLabel)
from spyderlib.qt.QtCore import SIGNAL, Qt

import sys
import re
import os.path as osp

from IPython.config.loader import Config

# Local imports
from spyderlib.baseconfig import _
from spyderlib.config import get_icon
from spyderlib.utils import programs
from spyderlib.utils.misc import get_error_match
from spyderlib.utils.qthelpers import (create_action, create_toolbutton,
                                       add_actions, mimedata2url)
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.ipython import IPythonApp
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage


class IPythonConsoleConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("IPython console")

    def setup_page(self):
        newcb = self.create_checkbox
        mpl_present = programs.is_module_installed("matplotlib")
        
        # --- Display ---
        font_group = self.create_fontgroup(option=None, text=None,
                                    fontfilters=QFontComboBox.MonospacedFonts)

        # Interface Group
        interface_group = QGroupBox(_("Interface"))
        banner_box = newcb(_("Display initial banner"), 'show_banner',
                      tip=_("This option lets you hide the message shown at\n"
                            "the top of the console when it's opened."))
        gui_comp_box = newcb(_("Use a completion widget"),
                             'use_gui_completion',
                             tip=_("Use a widget instead of plain text "
                                   "output for tab completion"))
        pager_box = newcb(_("Use a pager to display additional text inside "
                            "the console"), 'use_pager',
                            tip=_("Useful if you don't want to fill the "
                                  "console with long help or completion texts.\n"
                                  "Note: Use the Q key to get out of the "
                                  "pager."))
        calltips_box = newcb(_("Display balloon tips"), 'show_calltips')
        ask_box = newcb(_("Ask for confirmation before closing"),
                        'ask_before_closing')

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(banner_box)
        interface_layout.addWidget(gui_comp_box)
        interface_layout.addWidget(pager_box)
        interface_layout.addWidget(calltips_box)
        interface_layout.addWidget(ask_box)
        interface_group.setLayout(interface_layout)
        
        # Background Color Group
        bg_group = QGroupBox(_("Background color"))
        light_radio = self.create_radiobutton(_("Light background"),
                                              'light_color')
        dark_radio = self.create_radiobutton(_("Dark background"),
                                             'dark_color')
        bg_layout = QVBoxLayout()
        bg_layout.addWidget(light_radio)
        bg_layout.addWidget(dark_radio)
        bg_group.setLayout(bg_layout)

        # Source Code Group
        source_code_group = QGroupBox(_("Source code"))
        buffer_spin = self.create_spinbox(
                _("Buffer:  "), _(" lines"),
                'buffer_size', min_=-1, max_=1000000, step=100,
                tip=_("Set the maximum number of lines of text shown in the\n"
                      "console before truncation. Specifying -1 disables it\n"
                      "(not recommended!)"))
        source_code_layout = QVBoxLayout()
        source_code_layout.addWidget(buffer_spin)
        source_code_group.setLayout(source_code_layout)
        
        # --- Graphics ---
        # Pylab Group
        pylab_group = QGroupBox(_("Support for graphics (Pylab)"))
        pylab_box = newcb(_("Activate support"), 'pylab')
        autoload_pylab_box = newcb(_("Automatically load Pylab and NumPy"),
                               'pylab/autoload',
                               tip=_("This lets you load graphics support "
                                     "without importing \nthe commands to do "
                                     "plots. Useful to work with other\n"
                                     "plotting libraries different to "
                                     "Matplotlib or to develop \nGUIs with "
                                     "Spyder."))
        autoload_pylab_box.setEnabled(self.get_option('pylab') and mpl_present)
        self.connect(pylab_box, SIGNAL("toggled(bool)"),
                     autoload_pylab_box.setEnabled)
        
        pylab_layout = QVBoxLayout()
        pylab_layout.addWidget(pylab_box)
        pylab_layout.addWidget(autoload_pylab_box)
        pylab_group.setLayout(pylab_layout)
        
        if not mpl_present:
            self.set_option('pylab', False)
            self.set_option('pylab/autoload', False)
            pylab_group.setEnabled(False)
            pylab_tip = _("This feature requires the Matplotlib library.\n"
                          "It seems you don't have it installed.")
            pylab_box.setToolTip(pylab_tip)
        
        # Pylab backend Group
        inline = _("Inline")
        automatic = _("Automatic")
        backend_group = QGroupBox(_("Graphics backend"))
        bend_label = QLabel(_("Decide how graphics are going to be displayed "
                              "in the console. If unsure, please select "
                              "<b>%s</b> to put graphics inside the "
                              "console or <b>%s</b> to interact with "
                              "them (through zooming and panning) in a "
                              "separate window.") % (inline, automatic))
        bend_label.setWordWrap(True)

        backends = [(inline, 0), (automatic, 1), ("Qt", 2)]
        # TODO: Add gtk3 when 0.13 is released
        if sys.platform == 'darwin':
            backends.append( ("Mac OSX", 3) )
        if programs.is_module_installed('pygtk'):
            backends.append( ("Gtk", 4) )
        if programs.is_module_installed('wxPython'):
            backends.append( ("Wx", 5) )
        if programs.is_module_installed('_tkinter'):
            backends.append( ("Tkinter", 6) )
        backends = tuple(backends)
        
        backend_box = self.create_combobox( _("Backend:   "), backends,
                                       'pylab/backend', default=0,
                                       tip=_("This option will be applied the "
                                             "next time a console is opened."))
        
        backend_layout = QVBoxLayout()
        backend_layout.addWidget(bend_label)
        backend_layout.addWidget(backend_box)
        backend_group.setLayout(backend_layout)
        backend_group.setEnabled(self.get_option('pylab') and mpl_present)
        self.connect(pylab_box, SIGNAL("toggled(bool)"),
                     backend_group.setEnabled)
        
        # Inline backend Group
        inline_group = QGroupBox(_("Inline backend"))
        inline_label = QLabel(_("Decide how to render the figures created by "
                                "this backend"))
        inline_label.setWordWrap(True)
        formats = (("PNG", 0), ("SVG", 1))
        format_box = self.create_combobox( _("Format:   "), formats,
                                       'pylab/inline/figure_format', default=0)
        resolution_spin = self.create_spinbox(
                          _("Resolution:  "), _(" dpi"),
                          'pylab/inline/resolution', min_=56, max_=112, step=1,
                          tip=_("Only used when the format is PNG. Default is "
                                "72"))
        width_spin = self.create_spinbox(
                          _("Width:  "), _(" inches"),
                          'pylab/inline/width', min_=4, max_=20, step=1,
                          tip=_("Default is 6"))
        height_spin = self.create_spinbox(
                          _("Height:  "), _(" inches"),
                          'pylab/inline/height', min_=4, max_=20, step=1,
                          tip=_("Default is 4"))
        
        inline_layout = QVBoxLayout()
        inline_layout.addWidget(inline_label)
        inline_layout.addWidget(format_box)
        inline_layout.addWidget(resolution_spin)
        inline_layout.addWidget(width_spin)
        inline_layout.addWidget(height_spin)
        inline_group.setLayout(inline_layout)
        inline_group.setEnabled(self.get_option('pylab') and mpl_present)
        self.connect(pylab_box, SIGNAL("toggled(bool)"),
                     inline_group.setEnabled)

        # --- Startup ---
        # Run lines Group
        run_lines_group = QGroupBox(_("Run code"))
        run_lines_label = QLabel(_("You can run several lines of code when "
                                   "a console is started. Please introduce "
                                   "each one separated by commas, for "
                                   "example:<br>"
                                   "<i>import os, import sys</i>"))
        run_lines_label.setWordWrap(True)
        run_lines_edit = self.create_lineedit(_("Lines:"), 'startup/run_lines',
                                              '', alignment=Qt.Horizontal)
        
        run_lines_layout = QVBoxLayout()
        run_lines_layout.addWidget(run_lines_label)
        run_lines_layout.addWidget(run_lines_edit)
        run_lines_group.setLayout(run_lines_layout)
        
        # Run file Group
        run_file_group = QGroupBox(_("Run a file"))
        run_file_label = QLabel(_("You can also run a whole file at startup "
                                  "instead of just some lines (This is "
                                  "similar to have a PYTHONSTARTUP file)."))
        run_file_label.setWordWrap(True)
        file_radio = newcb(_("Use the following file:"),
                           'startup/use_run_file', False)
        run_file_browser = self.create_browsefile('', 'startup/run_file', '')
        run_file_browser.setEnabled(False)
        self.connect(file_radio, SIGNAL("toggled(bool)"),
                     run_file_browser.setEnabled)
        
        run_file_layout = QVBoxLayout()
        run_file_layout.addWidget(run_file_label)
        run_file_layout.addWidget(file_radio)
        run_file_layout.addWidget(run_file_browser)
        run_file_group.setLayout(run_file_layout)

        # --- Tabs organization ---
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(font_group, interface_group, bg_group,
                                    source_code_group), _("Display"))
        tabs.addTab(self.create_tab(pylab_group, backend_group, inline_group),
                                    _("Graphics"))
        tabs.addTab(self.create_tab(run_lines_group, run_file_group),
                                    _("Startup"))

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
    def __init__(self, plugin, connection_file, kernel_widget_id, client_name,
                 ipython_widget):
        super(IPythonClient, self).__init__(plugin)
        self.options_button = None

        self.connection_file = connection_file
        self.kernel_widget_id = kernel_widget_id
        self.client_name = client_name
        
        self.ipython_widget = ipython_widget
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ipython_widget)
        self.setLayout(layout)
        
        self.exit_callback = lambda: plugin.close_console(widget=self)

        # Connect the IPython widget to this IPython client:
        # (see spyderlib/widgets/ipython.py for more details about this)
        ipython_widget.set_ipython_client(self)
        
    #------ Public API --------------------------------------------------------
    def get_name(self):
        """Return client name"""
        return _("Client") + " " + self.client_name
    
    def get_control(self):
        """Return the text widget (or similar) to give focus to"""
        return self.ipython_widget._control

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
    
    def add_actions_to_context_menu(self, menu):
        """Add actions to IPython widget context menu"""
        # See spyderlib/widgets/ipython.py for more details on this method
        quit_action = create_action(self, _("&Quit"), icon='exit.png',
                                    triggered=self.exit_callback)
        add_actions(menu, (None, quit_action))
        return menu
    
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
        self.initialize_application()

        self.tabwidget = None
        self.menu_actions = None
        
        self.inspector = None # Object inspector plugin
        
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

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        self.register_widget_shortcuts("Editor", self.find_widget)
        
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)
            
        # Accepting drops
        self.setAcceptDrops(True)
    
    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('IPython console')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('ipython_console.png')
    
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
                    'ipython_console.png',
                    _("Open a new IPython client (frontend)"),
                    triggered=self.new_client)

        interact_menu_actions = [None, client_action]
        self.menu_actions = [client_action]
        
        self.main.interact_menu_actions += interact_menu_actions
        
        return self.menu_actions+interact_menu_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
        self.inspector = self.main.inspector
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        
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
            editor = clientwidget.get_control()
            editor.setFocus()
            widgets = clientwidget.get_toolbar_buttons()+[5]
        else:
            editor = None
            widgets = []
        self.find_widget.set_editor(editor)
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
                    kernel_widget_id = clw.kernel_widget_id
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

    def client_config(self):
        """Generate a Config instance for IPython clients using our config
        system
        
        This let us create each client with its own config (as oppossed to
        IPythonQtConsoleApp, where all clients have the same config)
        """
        cfg = Config()
        
        # Gui completion widget
        gui_comp_o = self.get_option('use_gui_completion')
        if programs.is_module_installed('IPython', '>0.12'):
            completions = {True: 'droplist', False: 'ncurses'}
            cfg.IPythonWidget.gui_completion = completions[gui_comp_o]
        else:
            cfg.IPythonWidget.gui_completion = gui_comp_o

        # Pager
        pager_o = self.get_option('use_pager')
        if pager_o:
            cfg.IPythonWidget.paging = 'inside'
        else:
            cfg.IPythonWidget.paging = 'none'
        
        # Calltips
        calltips_o = self.get_option('show_calltips')
        cfg.IPythonWidget.enable_calltips = calltips_o

        # Buffer size
        buffer_size_o = self.get_option('buffer_size')
        cfg.IPythonWidget.buffer_size = buffer_size_o
        
        return cfg
    
    def initialize_application(self):
        """Initialize IPython application"""
        #======================================================================
        # For IPython developers review [1]
        self.ipython_app = IPythonApp()
        # Is the following line really necessary?
        #self.ipython_app.initialize_all_except_qt()
        #======================================================================

    def register_client(self, connection_file, kernel_widget_id, client_name):
        """Register new IPython client"""
        #======================================================================
        # For IPython developers review [2]
        ipython_widget = self.ipython_app.create_new_client(connection_file,
                                                   config=self.client_config())
        #======================================================================

        shellwidget = IPythonClient(self, connection_file, kernel_widget_id,
                                    client_name, ipython_widget)
        self.connect(shellwidget.get_control(), SIGNAL("go_to_error(QString)"),
                     self.go_to_error)
        
        if self.inspector is not None:
            shellwidget.get_control().set_inspector(self.inspector)
        
        # Apply settings to newly created client widget:
        shellwidget.set_font( self.get_plugin_font() )
        
        self.add_tab(shellwidget, name=shellwidget.get_name())
        self.connect(shellwidget, SIGNAL('focus_changed()'),
                     lambda: self.emit(SIGNAL('focus_changed()')))
        self.find_widget.set_editor(shellwidget.get_control())
    
    def close_related_ipython_clients(self, client):
        """Close all IPython clients related to *client*, except itself"""
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
        index = self.tabwidget.addTab(widget, get_icon('ipython_console.png'),
                                      name)
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
        
    def close_console(self, index=None, widget=None, force=False):
        """Close console tab from index or widget (or close current tab)"""
        if not self.tabwidget.count():
            return
        if widget is not None:
            index = self.tabwidget.indexOf(widget)
        if index is None and widget is None:
            index = self.tabwidget.currentIndex()
        if index is not None:
            widget = self.tabwidget.widget(index)

        # Check if related clients or kernels are opened
        # and eventually ask before closing them
        if not force and isinstance(widget, IPythonClient):
            console = self.main.extconsole
            idx = console.get_shell_index_from_id(widget.kernel_widget_id)
            if idx is not None:
                close_all = True
                if self.get_option('ask_before_closing'):
                    ans = QMessageBox.question(self, self.get_plugin_title(),
                           _("%s will be closed.\n"
                             "Do you want to kill the associated kernel "
                             "and all of its clients?") % widget.get_name(),
                           QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
                    if ans == QMessageBox.Cancel:
                        return
                    close_all = ans == QMessageBox.Yes
                if close_all:
                    console.close_console(index=idx)
                    self.close_related_ipython_clients(widget)
        widget.close()
        
        # Note: widget index may have changed after closing related widgets
        self.tabwidget.removeTab(self.tabwidget.indexOf(widget))
        self.shellwidgets.remove(widget)

        self.emit(SIGNAL('update_plugin_title()'))
        
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(unicode(text))
        if match:
            fname, lnb = match.groups()
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                      osp.abspath(fname), int(lnb), '')
            
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

