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

# Qt imports
from spyderlib.qt.QtGui import (QVBoxLayout, QMessageBox, QGroupBox, QLineEdit,
                                QInputDialog, QTabWidget, QFontComboBox,
                                QApplication, QLabel)
from spyderlib.qt.QtCore import SIGNAL, Qt, QUrl

# Stdlib imports
import sys
import re
import os.path as osp

# IPython imports
from IPython.config.loader import Config, load_pyconfig_files
from IPython.core.application import get_ipython_dir
from IPython.lib.kernel import find_connection_file, get_connection_info
try:
    from IPython.qt.manager import QtKernelManager # 1.0
except ImportError:
    from IPython.frontend.qt.kernelmanager import QtKernelManager # 0.13
    
# Local imports
from spyderlib import dependencies
from spyderlib.baseconfig import _
from spyderlib.config import CONF
from spyderlib.utils.misc import get_error_match, remove_backslashes
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import get_icon, create_action
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.ipython import IPythonClient
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage
from spyderlib.py3compat import to_text_string, u


SYMPY_REQVER = '>=0.7.0'
dependencies.add("sympy", _("Symbolic mathematics for the IPython Console"),
                 required_version=SYMPY_REQVER)


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
                                              'light_color', True)
        dark_radio = self.create_radiobutton(_("Dark background"),
                                             'dark_color', False)
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
        pylab_group = QGroupBox(_("Support for graphics (Matplotlib)"))
        pylab_box = newcb(_("Activate support"), 'pylab')
        autoload_pylab_box = newcb(_("Automatically load Pylab and NumPy "
                                     "modules"),
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
        
        backend_box = self.create_combobox( _("Backend:")+"   ", backends,
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
        format_box = self.create_combobox(_("Format:")+"   ", formats,
                                       'pylab/inline/figure_format', default=0)
        resolution_spin = self.create_spinbox(
                          _("Resolution:")+"  ", " "+_("dpi"),
                          'pylab/inline/resolution', min_=56, max_=112, step=1,
                          tip=_("Only used when the format is PNG. Default is "
                                "72"))
        width_spin = self.create_spinbox(
                          _("Width:")+"  ", " "+_("inches"),
                          'pylab/inline/width', min_=2, max_=20, step=1,
                          tip=_("Default is 6"))
        height_spin = self.create_spinbox(
                          _("Height:")+"  ", " "+_("inches"),
                          'pylab/inline/height', min_=1, max_=20, step=1,
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
        
        # Spyder group
        spyder_group = QGroupBox(_("Spyder startup"))
        ipystartup_box = newcb(_("Open an IPython console at startup"),
                                 "open_ipython_at_startup")
        spyder_layout = QVBoxLayout()
        spyder_layout.addWidget(ipystartup_box)
        spyder_group.setLayout(spyder_layout)
        
        # ---- Advanced settings ----
        # Greedy completer group
        greedy_group = QGroupBox(_("Greedy completion"))
        greedy_label = QLabel(_("Enable <tt>Tab</tt> completion on elements "
                                "of lists, results of function calls, etc, "
                                "<i>without</i> assigning them to a "
                                "variable.<br>"
                                "For example, you can get completions on "
                                "things like <tt>li[0].&lt;Tab&gt;</tt> or "
                                "<tt>ins.meth().&lt;Tab&gt;</tt>"))
        greedy_label.setWordWrap(True)
        greedy_box = newcb(_("Use the greedy completer"), "greedy_completer",
                           tip="<b>Warning</b>: It can be unsafe because the "
                                "code is actually evaluated when you press "
                                "<tt>Tab</tt>.")
        
        greedy_layout = QVBoxLayout()
        greedy_layout.addWidget(greedy_label)
        greedy_layout.addWidget(greedy_box)
        greedy_group.setLayout(greedy_layout)
        
        # Autocall group
        autocall_group = QGroupBox(_("Autocall"))
        autocall_label = QLabel(_("Autocall makes IPython automatically call "
                                "any callable object even if you didn't type "
                                "explicit parentheses.<br>"
                                "For example, if you type <i>str 43</i> it "
                                "becomes <i>str(43)</i> automatically."))
        autocall_label.setWordWrap(True)
        
        smart = _('Smart')
        full = _('Full')
        autocall_opts = ((_('Off'), 0), (smart, 1), (full, 2))
        autocall_box = self.create_combobox(
                       _("Autocall:  "), autocall_opts, 'autocall', default=0,
                       tip=_("On <b>%s</b> mode, Autocall is not applied if "
                             "there are no arguments after the callable. On "
                             "<b>%s</b> mode, all callable objects are "
                             "automatically called (even if no arguments are "
                             "present).") % (smart, full))
        
        autocall_layout = QVBoxLayout()
        autocall_layout.addWidget(autocall_label)
        autocall_layout.addWidget(autocall_box)
        autocall_group.setLayout(autocall_layout)
        
        # Sympy group
        sympy_group = QGroupBox(_("Symbolic Mathematics"))
        sympy_label = QLabel(_("Perfom symbolic operations in the console "
                               "(e.g. integrals, derivatives, vector calculus, "
                               "etc) and get the outputs in a beautifully "
                               "printed style."))
        sympy_label.setWordWrap(True)
        sympy_box = newcb(_("Use symbolic math"), "symbolic_math",
                          tip=_("This option loads the Sympy library to work "
                                "with.<br>Please refer to its documentation to "
                                "learn how to use it."))
        
        sympy_layout = QVBoxLayout()
        sympy_layout.addWidget(sympy_label)
        sympy_layout.addWidget(sympy_box)
        sympy_group.setLayout(sympy_layout)
        
        sympy_present = programs.is_module_installed("sympy")
        if not sympy_present:
            self.set_option("symbolic_math", False)
            sympy_box.setEnabled(False)
            sympy_tip = _("This feature requires the Sympy library.\n"
                          "It seems you don't have it installed.")
            sympy_box.setToolTip(sympy_tip)
        
        # Prompts group
        prompts_group = QGroupBox(_("Prompts"))
        prompts_label = QLabel(_("Modify how Input and Output prompts are "
                                 "shown in the console."))
        prompts_label.setWordWrap(True)
        in_prompt_edit = self.create_lineedit(_("Input prompt:"),
                                    'in_prompt', '',
                                  _('Default is<br>'
                                    'In [&lt;span class="in-prompt-number"&gt;'
                                    '%i&lt;/span&gt;]:'),
                                    alignment=Qt.Horizontal)
        out_prompt_edit = self.create_lineedit(_("Output prompt:"),
                                   'out_prompt', '',
                                 _('Default is<br>'
                                   'Out[&lt;span class="out-prompt-number"&gt;'
                                   '%i&lt;/span&gt;]:'),
                                   alignment=Qt.Horizontal)
        
        prompts_layout = QVBoxLayout()
        prompts_layout.addWidget(prompts_label)
        prompts_layout.addWidget(in_prompt_edit)
        prompts_layout.addWidget(out_prompt_edit)
        prompts_group.setLayout(prompts_layout)

        # --- Tabs organization ---
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(font_group, interface_group, bg_group,
                                    source_code_group), _("Display"))
        tabs.addTab(self.create_tab(pylab_group, backend_group, inline_group),
                                    _("Graphics"))
        tabs.addTab(self.create_tab(spyder_group, run_lines_group,
                                    run_file_group), _("Startup"))
        tabs.addTab(self.create_tab(greedy_group, autocall_group, sympy_group,
                                    prompts_group), _("Advanced Settings"))

        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)


class IPythonConsole(SpyderPluginWidget):
    """
    IPython Console plugin

    This is a widget with tabs where each one is an IPythonClient
    """
    CONF_SECTION = 'ipython_console'
    CONFIGWIDGET_CLASS = IPythonConsoleConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        self.tabwidget = None
        self.menu_actions = None

        self.extconsole = None         # External console plugin
        self.inspector = None          # Object inspector plugin
        self.historylog = None         # History log plugin
        self.variableexplorer = None   # Variable explorer plugin
        
        self.clients = []
        
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
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client.get_control()

    def get_current_client(self):
        """
        Return the currently selected client
        """
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client

    def run_script_in_current_client(self, filename, wdir, args, debug):
        """Run script in current client, if any"""
        norm = lambda text: remove_backslashes(to_text_string(text))
        client = self.get_current_client()
        if client is not None:
            # Internal kernels, use runfile
            if client.kernel_widget_id is not None:
                line = "%s('%s'" % ('debugfile' if debug else 'runfile',
                                    norm(filename))
                if args:
                    line += ", args='%s'" % norm(args)
                if wdir:
                    line += ", wdir='%s'" % norm(wdir)
                line += ")"
            else: # External kernels, use %run
                line = "%run "
                if debug:
                    line += "-d "
                line += "\"%s\"" % to_text_string(filename)
                if args:
                    line += " %s" % norm(args)
            self.execute_python_code(line)
            self.visibility_changed(True)
            self.raise_()
        else:
            #XXX: not sure it can really happen
            QMessageBox.warning(self, _('Warning'),
                _("No IPython console is currently available to run <b>%s</b>."
                  "<br><br>Please open a new one and try again."
                  ) % osp.basename(filename), QMessageBox.Ok)

    def execute_python_code(self, lines):
        client = self.get_current_client()
        if client is not None:
            client.shellwidget.execute(to_text_string(lines))
            self.activateWindow()
            client.get_control().setFocus()

    def write_to_stdin(self, line):
        client = self.get_current_client()
        if client is not None:
            client.shellwidget.write_to_stdin(line)

    def create_new_client(self):
        """Create a new client"""
        client = IPythonClient(self, history_filename='history.py',
                               menu_actions=self.menu_actions)
        self.add_tab(client, name=client.get_name())
        self.main.extconsole.start_ipykernel(client)

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        create_client_action = create_action(self,
                                _("Open an &IPython console"),
                                None, 'ipython_console.png',
                                triggered=self.create_new_client)

        connect_to_kernel_action = create_action(self,
               _("Connect to an existing kernel"), None, None,
               _("Open a new IPython console connected to an existing kernel"),
               triggered=self.create_client_for_kernel)
        
        # Add the action to the 'Consoles' menu on the main window
        main_consoles_menu = self.main.consoles_menu_actions
        main_consoles_menu.insert(0, create_client_action)
        main_consoles_menu += [None, connect_to_kernel_action]
        
        # Plugin actions
        self.menu_actions = [create_client_action, connect_to_kernel_action]
        
        return self.menu_actions

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.extconsole, self)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)

        self.extconsole = self.main.extconsole
        self.inspector = self.main.inspector
        self.historylog = self.main.historylog
        self.variableexplorer = self.main.variableexplorer

        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)

        if self.main.editor is not None:
            self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                         self.main.editor.load)
            self.connect(self.main.editor,
                         SIGNAL('run_in_current_ipyclient(QString,QString,QString,bool)'),
                         self.run_script_in_current_client)
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        for client in self.clients:
            client.close()
        return True
    
    def refresh_plugin(self):
        """Refresh tabwidget"""
        client = None
        if self.tabwidget.count():
            # Give focus to the control widget of the selected tab
            client = self.tabwidget.currentWidget()
            control = client.get_control()
            control.setFocus()
            widgets = client.get_toolbar_buttons()+[5]
            
            # Change extconsole tab to the client's kernel widget
            idx = self.extconsole.get_shell_index_from_id(
                                                       client.kernel_widget_id)
            if idx is not None:
                self.extconsole.tabwidget.setCurrentIndex(idx)
        else:
            control = None
            widgets = []
        self.find_widget.set_editor(control)
        self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})
        self.main.last_console_plugin_focus_was_python = False
        self.emit(SIGNAL('update_plugin_title()'))
    
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        font_n = 'plugin_font'
        font_o = self.get_plugin_font()
        inspector_n = 'connect_to_oi'
        inspector_o = CONF.get('inspector', 'connect/ipython_console')
        for client in self.clients:
            control = client.get_control()
            if font_n in options:
                client.set_font(font_o)
            if inspector_n in options and control is not None:
                control.set_inspector_enabled(inspector_o)
    
    def kernel_and_frontend_match(self, connection_file):
        # Determine kernel version
        ci = get_connection_info(connection_file, unpack=True,
                                 profile='default')
        if u('control_port') in ci:
            kernel_ver = '>=1.0'
        else:
            kernel_ver = '<1.0'
        # is_module_installed checks if frontend version agrees with the
        # kernel one
        return programs.is_module_installed('IPython', version=kernel_ver)

    def create_kernel_manager_and_client(self, connection_file=None):
        """Create kernel manager and client"""
        cf = find_connection_file(connection_file, profile='default')
        kernel_manager = QtKernelManager(connection_file=cf, config=None)
        if programs.is_module_installed('IPython', '>=1.0'):
            kernel_client = kernel_manager.client()
            kernel_client.load_connection_file()
            kernel_client.start_channels()
            # To rely on kernel's heartbeat to know when a kernel has died
            kernel_client.hb_channel.unpause()
        else:
            kernel_client = None
            kernel_manager.load_connection_file()
            kernel_manager.start_channels()
        return kernel_manager, kernel_client

    def connect_client_to_kernel(self, client):
        """
        Connect a client to its kernel
        """
        connection_file = client.connection_file
        widget = client.shellwidget
        km, kc = self.create_kernel_manager_and_client(connection_file)
        widget.kernel_manager = km
        widget.kernel_client = kc
    
    #------ Private API -------------------------------------------------------
    def _show_rich_help(self, text):
        """Use our Object Inspector to show IPython help texts in rich mode"""
        from spyderlib.utils.inspector import sphinxify as spx
        
        context = spx.generate_context(name='', argspec='', note='',
                                       math=False)
        html_text = spx.sphinxify(text, context)
        inspector = self.inspector
        inspector.visibility_changed(True)
        inspector.raise_()
        inspector.switch_to_rich_text()
        inspector.set_rich_text_html(html_text,
                                     QUrl.fromLocalFile(spx.CSS_PATH))
    
    def _show_plain_help(self, text):
        """Use our Object Inspector to show IPython help texts in plain mode"""
        inspector = self.inspector
        inspector.visibility_changed(True)
        inspector.raise_()
        inspector.switch_to_plain_text()
        inspector.set_plain_text(text, is_code=False)
    
    #------ Public API --------------------------------------------------------
    def get_clients(self):
        """Return IPython client widgets list"""
        return [cl for cl in self.clients if isinstance(cl, IPythonClient)]
        
#    def get_kernels(self):
#        """Return IPython kernel widgets list"""
#        return [sw for sw in self.shellwidgets
#                if isinstance(sw, IPythonKernel)]
#        

    def get_focus_client(self):
        """Return current client with focus, if any"""
        widget = QApplication.focusWidget()
        for client in self.get_clients():
            if widget is client or widget is client.get_control():
                return client

    def create_client_for_kernel(self):
        """Create a client connected to an existing kernel"""
        example = _("(for example: kernel-3764.json, or simply 3764)")
        while True:
            cf, valid = QInputDialog.getText(self, _('IPython'),
                          _('Provide an IPython kernel connection file:')+\
                          '\n'+example,
                          QLineEdit.Normal)
            if valid:
                cf = str(cf)
                match = re.match('(kernel-|^)([a-fA-F0-9-]+)(.json|$)', cf)
                if match is not None:
                    kernel_num = match.groups()[1]
                    if kernel_num:
                        cf = 'kernel-%s.json' % kernel_num
                        break
            else:
                return

        # Generating the client name and setting kernel_widget_id
        match = re.match('^kernel-([a-fA-F0-9-]+).json', cf)
        count = 0
        kernel_widget_id = None
        while True:
            client_name = match.groups()[0]
            if '-' in client_name:  # Avoid long names
                client_name = client_name.split('-')[0]
            client_name = client_name + '/' + chr(65+count)
            for cl in self.get_clients():
                if cl.name == client_name:
                    kernel_widget_id = cl.kernel_widget_id
                    break
            else:
                break
            count += 1
        
        # Trying to get kernel_widget_id from the currently opened kernels if
        # the previous procedure fails. This could happen when the first
        # client connected to a kernel is closed but the kernel is left open
        # and you try to connect new clients to it
        if kernel_widget_id is None:
            for sw in self.extconsole.shellwidgets:
                if sw.connection_file == cf:
                    kernel_widget_id = id(sw)

        # Verifying if the kernel exists
        try:
            find_connection_file(cf, profile='default')
        except (IOError, UnboundLocalError):
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to IPython <b>%s") % cf)
            return
        
        # Verifying if frontend and kernel have compatible versions
        if not self.kernel_and_frontend_match(cf):
            QMessageBox.critical(self,
                                 _("Mismatch between kernel and frontend"),
                                 _("Your IPython frontend and kernel versions "
                                   "are <b>incompatible!!</b>"
                                   "<br><br>"
                                   "We're sorry but we can't create an IPython "
                                   "console for you."
                                ), QMessageBox.Ok)
            return
        
        # Creating the client
        client = IPythonClient(self, history_filename='history.py',
                               connection_file=cf,
                               kernel_widget_id=kernel_widget_id,
                               menu_actions=self.menu_actions)
        self.add_tab(client, name=client.get_name())
        self.register_client(client, client_name)

    def ipywidget_config(self):
        """Generate a Config instance for IPython widgets using our config
        system
        
        This let us create each widget with its own config (as oppossed to
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

    def register_client(self, client, name, restart=False):
        """Register new IPython client"""
        self.connect_client_to_kernel(client)
        client.show_shellwidget()
        client.name = name
        
        # If we are restarting the kernel we just need to rename the client tab
        if restart:
            self.rename_ipyclient_tab(client)
            return
        
        shellwidget = client.shellwidget
        control = shellwidget._control
        page_control = shellwidget._page_control
        
        # For tracebacks
        self.connect(control, SIGNAL("go_to_error(QString)"), self.go_to_error)

        # Handle kernel interrupts
        extconsoles = self.extconsole.shellwidgets
        kernel_widget = None
        if extconsoles:
            if extconsoles[-1].connection_file == client.connection_file:
                kernel_widget = extconsoles[-1]
                shellwidget.custom_interrupt_requested.connect(
                                              kernel_widget.keyboard_interrupt)
        if kernel_widget is None:
            shellwidget.custom_interrupt_requested.connect(
                                                      client.interrupt_message)
        
        # Handle kernel restarts asked by the user
        if kernel_widget is not None:
            shellwidget.custom_restart_requested.connect(
                                 lambda cl=client: self.restart_kernel(client))
        else:
            shellwidget.custom_restart_requested.connect(client.restart_message)
        
        # Print a message if kernel dies unexpectedly
        shellwidget.custom_restart_kernel_died.connect(
                                            lambda t: client.if_kernel_dies(t))
        
        # Connect text widget to our inspector
        if kernel_widget is not None and self.inspector is not None:
            control.set_inspector(self.inspector)
            control.set_inspector_enabled(CONF.get('inspector',
                                                   'connect/ipython_console'))

        # Connect to our variable explorer
        if kernel_widget is not None and self.variableexplorer is not None:
            nsb = self.variableexplorer.currentWidget()
            # When the autorefresh button is active, our kernels
            # start to consume more and more CPU during time
            # Fix Issue 1450
            # ----------------
            # When autorefresh is off by default we need the next
            # line so that kernels don't start to consume CPU
            # Fix Issue 1595
            nsb.auto_refresh_button.setChecked(True)
            nsb.auto_refresh_button.setChecked(False)
            nsb.auto_refresh_button.setEnabled(False)
            nsb.set_ipyclient(client)
            client.set_namespacebrowser(nsb)
        
        # Connect client to our history log
        if self.historylog is not None:
            self.historylog.add_history(client.history_filename)
            self.connect(client, SIGNAL('append_to_history(QString,QString)'),
                         self.historylog.append_to_history)
        
        # Apply settings to newly created client widget:
        client.set_font( self.get_plugin_font() )
        
        # Add tab and connect focus signal to client's control widget
        self.connect(control, SIGNAL('focus_changed()'),
                     lambda: self.emit(SIGNAL('focus_changed()')))
        
        # Update the find widget if focus changes between control and
        # page_control
        self.find_widget.set_editor(control)
        if page_control:
            self.connect(page_control, SIGNAL('focus_changed()'),
                         lambda: self.emit(SIGNAL('focus_changed()')))
            self.connect(control, SIGNAL('visibility_changed(bool)'),
                         self.refresh_plugin)
            self.connect(page_control, SIGNAL('visibility_changed(bool)'),
                         self.refresh_plugin)
            self.connect(page_control, SIGNAL('show_find_widget()'),
                         self.find_widget.show)

        # Update client name
        self.rename_ipyclient_tab(client)
    
    def open_client_at_startup(self):
        if self.get_option('open_ipython_at_startup', False):
            self.create_new_client()
    
    def close_related_ipyclients(self, client):
        """Close all IPython clients related to *client*, except itself"""
        for cl in self.clients[:]:
            if cl is not client and \
              cl.connection_file == client.connection_file:
                self.close_console(client=cl)
    
    def get_shellwidget_by_kernelwidget_id(self, kernel_id):
        """Return the IPython widget associated to a kernel widget id"""
        for cl in self.clients:
            if cl.kernel_widget_id == kernel_id:
                return cl.shellwidget
        else:
            raise ValueError("Unknown kernel widget ID %r" % kernel_id)
        
    def add_tab(self, widget, name):
        """Add tab"""
        self.clients.append(widget)
        index = self.tabwidget.addTab(widget, get_icon('ipython_console.png'),
                                      name)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        self.activateWindow()
        widget.get_control().setFocus()
        
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        client = self.clients.pop(index_from)
        self.clients.insert(index_to, client)
        self.emit(SIGNAL('update_plugin_title()'))
        
    def close_console(self, index=None, client=None, force=False):
        """Close console tab from index or widget (or close current tab)"""
        if not self.tabwidget.count():
            return
        if client is not None:
            index = self.tabwidget.indexOf(client)
        if index is None and client is None:
            index = self.tabwidget.currentIndex()
        if index is not None:
            client = self.tabwidget.widget(index)

        # Check if related clients or kernels are opened
        # and eventually ask before closing them
        if not force and isinstance(client, IPythonClient):
            idx = self.extconsole.get_shell_index_from_id(
                                                       client.kernel_widget_id)
            if idx is not None:
                close_all = True
                if self.get_option('ask_before_closing'):
                    ans = QMessageBox.question(self, self.get_plugin_title(),
                           _("%s will be closed.\n"
                             "Do you want to kill the associated kernel "
                             "and all of its clients?") % client.get_name(),
                           QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
                    if ans == QMessageBox.Cancel:
                        return
                    close_all = ans == QMessageBox.Yes
                if close_all:
                    self.extconsole.close_console(index=idx,
                                                  from_ipyclient=True)
                    self.close_related_ipyclients(client)
        client.close()
        
        # Note: client index may have changed after closing related widgets
        self.tabwidget.removeTab(self.tabwidget.indexOf(client))
        self.clients.remove(client)

        self.emit(SIGNAL('update_plugin_title()'))
        
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(to_text_string(text))
        if match:
            fname, lnb = match.groups()
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                      osp.abspath(fname), int(lnb), '')
    
    def show_intro(self):
        """Show intro to IPython help"""
        from IPython.core.usage import interactive_usage
        self._show_rich_help(interactive_usage)
    
    def show_guiref(self):
        """Show qtconsole help"""
        from IPython.core.usage import gui_reference
        self._show_rich_help(gui_reference)
    
    def show_quickref(self):
        """Show IPython Cheat Sheet"""
        from IPython.core.usage import quick_reference
        self._show_plain_help(quick_reference)
    
    def get_client_index_from_id(self, client_id):
        """Return client index from id"""
        for index, client in enumerate(self.clients):
            if id(client) == client_id:
                return index
    
    def rename_ipyclient_tab(self, client):
        """Add the pid of the kernel process to an IPython client tab"""
        index = self.get_client_index_from_id(id(client))
        self.tabwidget.setTabText(index, client.get_name())
    
    def restart_kernel(self, client):
        """
        Create a new kernel and connect it to `client` if the user asks for it
        """
        # Took this bit of code (until if result == ) from the IPython project
        # (qt/frontend_widget.py - restart_kernel).
        # Licensed under the BSD license
        message = _('Are you sure you want to restart the kernel?')
        buttons = QMessageBox.Yes | QMessageBox.No
        result = QMessageBox.question(self, _('Restart kernel?'),
                                      message, buttons)
        if result == QMessageBox.Yes:
            client.show_restart_animation()
            
            # Close old kernel tab
            idx = self.extconsole.get_shell_index_from_id(client.kernel_widget_id)
            self.extconsole.close_console(index=idx, from_ipyclient=True)
            
            # Create a new one and connect it to the client
            self.main.extconsole.start_ipykernel(client)
        
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

