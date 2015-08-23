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

# Stdlib imports
import atexit
import os
import os.path as osp
import sys

# Qt imports
from spyderlib.qt.QtGui import (QVBoxLayout, QHBoxLayout, QFormLayout, 
                                QMessageBox, QGroupBox, QDialogButtonBox,
                                QDialog, QTabWidget, QFontComboBox, 
                                QCheckBox, QApplication, QLabel,QLineEdit,
                                QPushButton, QKeySequence, QWidget)
from spyderlib.qt.compat import getopenfilename
from spyderlib.qt.QtCore import SIGNAL, Qt

# IPython imports
from IPython.core.application import get_ipython_dir
from IPython.kernel.connect import find_connection_file
from IPython.qt.manager import QtKernelManager
try: # IPython = "<=2.0"
    from IPython.external.ssh import tunnel as zmqtunnel
    import IPython.external.pexpect as pexpect
except ImportError:
    from zmq.ssh import tunnel as zmqtunnel      # analysis:ignore
    try:
        import pexpect                           # analysis:ignore
    except ImportError:
        pexpect = None                           # analysis:ignore

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
from spyderlib.py3compat import to_text_string


SYMPY_REQVER = '>=0.7.3'
dependencies.add("sympy", _("Symbolic mathematics in the IPython Console"),
                 required_version=SYMPY_REQVER)


# Replacing pyzmq openssh_tunnel method to work around the issue
# https://github.com/zeromq/pyzmq/issues/589 which was solved in pyzmq
# https://github.com/zeromq/pyzmq/pull/615
def _stop_tunnel(cmd):
    pexpect.run(cmd)

def openssh_tunnel(self, lport, rport, server, remoteip='127.0.0.1',
                   keyfile=None, password=None, timeout=0.4):
    if pexpect is None:
        raise ImportError("pexpect unavailable, use paramiko_tunnel")
    ssh="ssh "
    if keyfile:
        ssh += "-i " + keyfile
    
    if ':' in server:
        server, port = server.split(':')
        ssh += " -p %s" % port
    
    cmd = "%s -O check %s" % (ssh, server)
    (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
    if not exitstatus:
        pid = int(output[output.find("(pid=")+5:output.find(")")]) 
        cmd = "%s -O forward -L 127.0.0.1:%i:%s:%i %s" % (
            ssh, lport, remoteip, rport, server)
        (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
        if not exitstatus:
            atexit.register(_stop_tunnel, cmd.replace("-O forward",
                                                      "-O cancel",
                                                      1))
            return pid
    cmd = "%s -f -S none -L 127.0.0.1:%i:%s:%i %s sleep %i" % (
                                  ssh, lport, remoteip, rport, server, timeout)
    
    # pop SSH_ASKPASS from env
    env = os.environ.copy()
    env.pop('SSH_ASKPASS', None)
    
    ssh_newkey = 'Are you sure you want to continue connecting'
    tunnel = pexpect.spawn(cmd, env=env)
    failed = False
    while True:
        try:
            i = tunnel.expect([ssh_newkey, '[Pp]assword:'], timeout=.1)
            if i==0:
                host = server.split('@')[-1]
                question = _("The authenticity of host <b>%s</b> can't be "
                             "established. Are you sure you want to continue "
                             "connecting?") % host
                reply = QMessageBox.question(self, _('Warning'), question,
                                             QMessageBox.Yes | QMessageBox.No,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    tunnel.sendline('yes')
                    continue
                else:
                    tunnel.sendline('no')
                    raise RuntimeError(
                       _("The authenticity of the host can't be established"))
            if i==1 and password is not None:
                tunnel.sendline(password) 
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            if tunnel.exitstatus:
                raise RuntimeError(_("Tunnel '%s' failed to start") % cmd)
            else:
                return tunnel.pid
        else:
            if failed or password is None:
                raise RuntimeError(_("Could not connect to remote host"))
                # TODO: Use this block when pyzmq bug #620 is fixed
                # # Prompt a passphrase dialog to the user for a second attempt
                # password, ok = QInputDialog.getText(self, _('Password'),
                #             _('Enter password for: ') + server,
                #             echo=QLineEdit.Password)
                # if ok is False:
                #      raise RuntimeError('Could not connect to remote host.') 
            tunnel.sendline(password)
            failed = True


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
                        'pylab/inline/resolution', min_=50, max_=150, step=0.1,
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
        tabs.addTab(self.create_tab(run_lines_group, run_file_group),
                                    _("Startup"))
        tabs.addTab(self.create_tab(greedy_group, autocall_group, sympy_group,
                                    prompts_group), _("Advanced Settings"))

        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)


class KernelConnectionDialog(QDialog):
    """Dialog to connect to existing kernels (either local or remote)"""
    
    def __init__(self, parent=None):
        super(KernelConnectionDialog, self).__init__(parent)
        self.setWindowTitle(_('Connect to an existing kernel'))
        
        main_label = QLabel(_("Please enter the connection info of the kernel "
                              "you want to connect to. For that you can "
                              "either select its JSON connection file using "
                              "the <tt>Browse</tt> button, or write directly "
                              "its id, in case it's a local kernel (for "
                              "example <tt>kernel-3764.json</tt> or just "
                              "<tt>3764</tt>)."))
        main_label.setWordWrap(True)
        main_label.setAlignment(Qt.AlignJustify)
        
        # connection file
        cf_label = QLabel(_('Connection info:'))
        self.cf = QLineEdit()
        self.cf.setPlaceholderText(_('Path to connection file or kernel id'))
        self.cf.setMinimumWidth(250)
        cf_open_btn = QPushButton(_('Browse'))
        self.connect(cf_open_btn, SIGNAL('clicked()'),
                     self.select_connection_file)

        cf_layout = QHBoxLayout()
        cf_layout.addWidget(cf_label)
        cf_layout.addWidget(self.cf)
        cf_layout.addWidget(cf_open_btn)
        
        # remote kernel checkbox 
        self.rm_cb = QCheckBox(_('This is a remote kernel'))
        
        # ssh connection 
        self.hn = QLineEdit()
        self.hn.setPlaceholderText(_('username@hostname:port'))
        
        self.kf = QLineEdit()
        self.kf.setPlaceholderText(_('Path to ssh key file'))
        kf_open_btn = QPushButton(_('Browse'))
        self.connect(kf_open_btn, SIGNAL('clicked()'), self.select_ssh_key)

        kf_layout = QHBoxLayout()
        kf_layout.addWidget(self.kf)
        kf_layout.addWidget(kf_open_btn)
        
        self.pw = QLineEdit()
        self.pw.setPlaceholderText(_('Password or ssh key passphrase'))
        self.pw.setEchoMode(QLineEdit.Password)

        ssh_form = QFormLayout()
        ssh_form.addRow(_('Host name'), self.hn)
        ssh_form.addRow(_('Ssh key'), kf_layout)
        ssh_form.addRow(_('Password'), self.pw)
        
        # Ok and Cancel buttons
        accept_btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.connect(accept_btns, SIGNAL('accepted()'), self.accept)
        self.connect(accept_btns, SIGNAL('rejected()'), self.reject)

        # Dialog layout
        layout = QVBoxLayout(self)
        layout.addWidget(main_label)
        layout.addLayout(cf_layout)
        layout.addWidget(self.rm_cb)
        layout.addLayout(ssh_form)
        layout.addWidget(accept_btns)
                
        # remote kernel checkbox enables the ssh_connection_form
        def ssh_set_enabled(state):
            for wid in [self.hn, self.kf, kf_open_btn, self.pw]:
                wid.setEnabled(state)
            for i in range(ssh_form.rowCount()):
                ssh_form.itemAt(2 * i).widget().setEnabled(state)
       
        ssh_set_enabled(self.rm_cb.checkState())
        self.connect(self.rm_cb, SIGNAL('stateChanged(int)'), ssh_set_enabled)

    def select_connection_file(self):
        cf = getopenfilename(self, _('Open IPython connection file'),
                 osp.join(get_ipython_dir(), 'profile_default', 'security'),
                 '*.json;;*.*')[0]
        self.cf.setText(cf)

    def select_ssh_key(self):
        kf = getopenfilename(self, _('Select ssh key'), 
                             get_ipython_dir(), '*.pem;;*.*')[0]
        self.kf.setText(kf)

    @staticmethod
    def get_connection_parameters(parent=None):
        dialog = KernelConnectionDialog(parent)
        result = dialog.exec_()
        is_remote = bool(dialog.rm_cb.checkState())
        accepted = result == QDialog.Accepted
        if is_remote:
            falsy_to_none = lambda arg: arg if arg else None
            return (dialog.cf.text(),            # connection file
                falsy_to_none(dialog.hn.text()), # host name
                falsy_to_none(dialog.kf.text()), # ssh key file
                falsy_to_none(dialog.pw.text()), # ssh password
                accepted)                        # ok
        else:
            return (dialog.cf.text(), None, None, None, accepted)


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

        self.master_clients = 0
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
                     
        self.tabwidget.set_close_function(self.close_client)

        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabwidget)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        self.register_widget_shortcuts("Editor", self.find_widget)
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)
            
        # Accepting drops
        self.setAcceptDrops(True)
    
    #------ SpyderPluginMixin API ---------------------------------------------
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.extconsole, self)

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

    def toggle_view(self, checked):
        """Toggle view"""
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            # Start a client in case there are none shown
            if not self.clients:
                if self.main.is_setting_up:
                    self.create_new_client(give_focus=False)
                else:
                    self.create_new_client(give_focus=True)
        else:
            self.dockwidget.hide()
    
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

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        ctrl = "Cmd" if sys.platform == "darwin" else "Ctrl"
        main_create_client_action = create_action(self,
                                _("Open an &IPython console"),
                                None, 'ipython_console.png',
                                triggered=self.create_new_client,
                                tip=_("Use %s+T when the console is selected "
                                      "to open a new one") % ctrl)
        create_client_action = create_action(self,
                                _("Open a new console"),
                                QKeySequence("Ctrl+T"), 'ipython_console.png',
                                triggered=self.create_new_client)
        create_client_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)

        connect_to_kernel_action = create_action(self,
               _("Connect to an existing kernel"), None, None,
               _("Open a new IPython console connected to an existing kernel"),
               triggered=self.create_client_for_kernel)
        
        # Add the action to the 'Consoles' menu on the main window
        main_consoles_menu = self.main.consoles_menu_actions
        main_consoles_menu.insert(0, main_create_client_action)
        main_consoles_menu += [None, connect_to_kernel_action]
        
        # Plugin actions
        self.menu_actions = [create_client_action, connect_to_kernel_action]
        
        return self.menu_actions

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

    #------ Public API (for clients) ------------------------------------------
    def get_clients(self):
        """Return clients list"""
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
    
    def get_current_client(self):
        """Return the currently selected client"""
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

    def create_new_client(self, give_focus=True):
        """Create a new client"""
        self.master_clients += 1
        name = "%d/A" % self.master_clients
        client = IPythonClient(self, name=name, history_filename='history.py',
                               menu_actions=self.menu_actions)
        self.add_tab(client, name=client.get_name())
        self.main.extconsole.start_ipykernel(client, give_focus=give_focus)

    def register_client(self, client, restart=False, give_focus=True):
        """Register new client"""
        self.connect_client_to_kernel(client)
        client.show_shellwidget(give_focus=give_focus)
        
        # Local vars
        shellwidget = client.shellwidget
        control = shellwidget._control
        page_control = shellwidget._page_control

        # Create new clients with Ctrl+T shortcut
        self.connect(shellwidget, SIGNAL('new_ipyclient()'),
                     self.create_new_client)
        
        # Handle kernel interrupts
        extconsoles = self.extconsole.shellwidgets
        kernel_widget = None
        if extconsoles:
            if extconsoles[-1].connection_file == client.connection_file:
                kernel_widget = extconsoles[-1]
                if restart:
                    shellwidget.custom_interrupt_requested.disconnect()
                shellwidget.custom_interrupt_requested.connect(
                                              kernel_widget.keyboard_interrupt)
        if kernel_widget is None:
            shellwidget.custom_interrupt_requested.connect(
                                                      client.interrupt_message)

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

        # If we are restarting the kernel we need to rename
        # the client tab and do no more from here on
        if restart:
            self.rename_client_tab(client)
            return
        
        # For tracebacks
        self.connect(control, SIGNAL("go_to_error(QString)"), self.go_to_error)
        
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

        # Connect client to our history log
        if self.historylog is not None:
            self.historylog.add_history(client.history_filename)
            self.connect(client, SIGNAL('append_to_history(QString,QString)'),
                         self.historylog.append_to_history)
        
        # Set font for client
        client.set_font( self.get_plugin_font() )
        
        # Connect focus signal to client's control widget
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

    def close_client(self, index=None, client=None, force=False):
        """Close client tab from index or widget (or close current tab)"""
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
            kernel_index = self.extconsole.get_shell_index_from_id(
                                                       client.kernel_widget_id)
            close_all = True
            if len(self.get_related_clients(client)) > 0 and \
              self.get_option('ask_before_closing'):
                ans = QMessageBox.question(self, self.get_plugin_title(),
                       _("Do you want to close all other consoles connected "
                         "to the same kernel as this one?"),
                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                if ans == QMessageBox.Cancel:
                    return
                close_all = ans == QMessageBox.Yes
            if close_all:
                if kernel_index is not None:
                    self.extconsole.close_console(index=kernel_index,
                                                  from_ipyclient=True)
                self.close_related_clients(client)
        client.close()
        
        # Note: client index may have changed after closing related widgets
        self.tabwidget.removeTab(self.tabwidget.indexOf(client))
        self.clients.remove(client)
        self.emit(SIGNAL('update_plugin_title()'))

    def get_client_index_from_id(self, client_id):
        """Return client index from id"""
        for index, client in enumerate(self.clients):
            if id(client) == client_id:
                return index
    
    def rename_client_tab(self, client):
        """Add the pid of the kernel process to client tab"""
        index = self.get_client_index_from_id(id(client))
        self.tabwidget.setTabText(index, client.get_name())

    def get_related_clients(self, client):
        """
        Get all other clients that are connected to the same kernel as `client`
        """
        related_clients = []
        for cl in self.get_clients():
            if cl.connection_file == client.connection_file and \
              cl is not client:
                related_clients.append(cl)
        return related_clients

    def close_related_clients(self, client):
        """Close all clients related to *client*, except itself"""
        related_clients = self.get_related_clients(client)
        for cl in related_clients:
            self.close_client(client=cl, force=True)

    #------ Public API (for kernels) ------------------------------------------
    def ssh_tunnel(self, *args, **kwargs):
        if sys.platform == 'win32':
            return zmqtunnel.paramiko_tunnel(*args, **kwargs)
        else:
            return openssh_tunnel(self, *args, **kwargs)

    def tunnel_to_kernel(self, ci, hostname, sshkey=None, password=None, timeout=10):
        """tunnel connections to a kernel via ssh. remote ports are specified in
        the connection info ci."""
        lports = zmqtunnel.select_random_ports(4)
        rports = ci['shell_port'], ci['iopub_port'], ci['stdin_port'], ci['hb_port']
        remote_ip = ci['ip']
        for lp, rp in zip(lports, rports):
            self.ssh_tunnel(lp, rp, hostname, remote_ip, sshkey, password, timeout)
        return tuple(lports)

    def create_kernel_manager_and_client(self, connection_file=None,
                                         hostname=None, sshkey=None,
                                         password=None):
        """Create kernel manager and client"""
        cf = find_connection_file(connection_file)
        kernel_manager = QtKernelManager(connection_file=cf, config=None)
        kernel_client = kernel_manager.client()
        kernel_client.load_connection_file()
        if hostname is not None:
            try:
                newports = self.tunnel_to_kernel(dict(ip=kernel_client.ip,
                                      shell_port=kernel_client.shell_port,
                                      iopub_port=kernel_client.iopub_port,
                                      stdin_port=kernel_client.stdin_port,
                                      hb_port=kernel_client.hb_port),
                                      hostname, sshkey, password)
                (kernel_client.shell_port, kernel_client.iopub_port,
                 kernel_client.stdin_port, kernel_client.hb_port) = newports
            except Exception as e:
                QMessageBox.critical(self, _('Connection error'), 
                                   _("Could not open ssh tunnel. The "
                                     "error was:\n\n") + to_text_string(e))
                return None, None
        kernel_client.start_channels()
        # To rely on kernel's heartbeat to know when a kernel has died
        kernel_client.hb_channel.unpause()
        return kernel_manager, kernel_client

    def connect_client_to_kernel(self, client):
        """
        Connect a client to its kernel
        """
        km, kc = self.create_kernel_manager_and_client(client.connection_file, 
                                                       client.hostname,
                                                       client.sshkey,
                                                       client.password)
        if km is not None:
            widget = client.shellwidget
            widget.kernel_manager = km
            widget.kernel_client = kc

    def create_client_for_kernel(self):
        """Create a client connected to an existing kernel"""
        (cf, hostname,
         kf, pw, ok) = KernelConnectionDialog.get_connection_parameters(self)
        if not ok:
            return
        else:
            self._create_client_for_kernel(cf, hostname, kf, pw)

    def _create_client_for_kernel(self, cf, hostname, kf, pw):
        # Verifying if the connection file exists
        cf = osp.basename(cf)
        try:
            find_connection_file(cf)
        except (IOError, UnboundLocalError):
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to IPython <b>%s") % cf)
            return
        
        # Getting the master name that corresponds to the client
        # (i.e. the i in i/A)
        master_name = None
        slave_ord = ord('A') - 1
        for cl in self.get_clients():
            if cf in cl.connection_file:
                cf = cl.connection_file
                if master_name is None:
                    master_name = cl.name.split('/')[0]
                new_slave_ord = ord(cl.name.split('/')[1])
                if new_slave_ord > slave_ord:
                    slave_ord = new_slave_ord
        
        # If we couldn't find a client with the same connection file,
        # it means this is a new master client
        if master_name is None:
            self.master_clients += 1
            master_name = to_text_string(self.master_clients)
        
        # Set full client name
        name = master_name + '/' + chr(slave_ord + 1)
        
        # Getting kernel_widget_id from the currently open kernels.
        kernel_widget_id = None
        for sw in self.extconsole.shellwidgets:
            if sw.connection_file == cf.split('/')[-1]:  
                kernel_widget_id = id(sw)

        # Creating the client
        client = IPythonClient(self, name=name, history_filename='history.py',
                               connection_file=cf,
                               kernel_widget_id=kernel_widget_id,
                               menu_actions=self.menu_actions,
                               hostname=hostname, sshkey=kf, password=pw)
        
        # Adding the tab
        self.add_tab(client, name=client.get_name())
        
        # Connecting kernel and client
        self.register_client(client)

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
            self.extconsole.start_ipykernel(client)
    
    def get_shellwidget_by_kernelwidget_id(self, kernel_id):
        """Return the IPython widget associated to a kernel widget id"""
        for cl in self.clients:
            if cl.kernel_widget_id == kernel_id:
                return cl.shellwidget
        else:
            raise ValueError("Unknown kernel widget ID %r" % kernel_id)

    #------ Public API (for tabs) ---------------------------------------------
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

    #------ Public API (for help) ---------------------------------------------
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
        self.inspector.show_rich_text(interactive_usage)
    
    def show_guiref(self):
        """Show qtconsole help"""
        from IPython.core.usage import gui_reference
        self.inspector.show_rich_text(gui_reference, collapse=True)
    
    def show_quickref(self):
        """Show IPython Cheat Sheet"""
        from IPython.core.usage import quick_reference
        self.inspector.show_plain_text(quick_reference)
        
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

