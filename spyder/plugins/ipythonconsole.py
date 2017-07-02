# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console plugin based on QtConsole
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import atexit
import codecs
import os
import os.path as osp
import uuid
import sys

# Third party imports
from jupyter_client.connect import find_connection_file
from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir
from qtconsole.client import QtKernelClient
from qtconsole.manager import QtKernelManager
from qtpy import PYQT5
from qtpy.compat import getopenfilename
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox,
                            QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                            QLabel, QLineEdit, QMessageBox, QPushButton,
                            QTabWidget, QVBoxLayout, QWidget)
from traitlets.config.loader import Config, load_pyconfig_files
from zmq.ssh import tunnel as zmqtunnel
try:
    import pexpect
except ImportError:
    pexpect = None

# Local imports
from spyder import dependencies
from spyder.config.base import (_, DEV, get_conf_path, get_home_dir,
                                get_module_path)
from spyder.config.main import CONF
from spyder.plugins import SpyderPluginWidget
from spyder.plugins.configdialog import PluginConfigPage
from spyder.py3compat import is_string, PY2, to_text_string
from spyder.utils.ipython.kernelspec import SpyderKernelSpec
from spyder.utils.ipython.style import create_qss_style
from spyder.utils.qthelpers import create_action, MENU_SEPARATOR
from spyder.utils import icon_manager as ima
from spyder.utils import encoding, programs
from spyder.utils.misc import get_error_match, remove_backslashes
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.ipythonconsole import ClientWidget
from spyder.widgets.tabs import Tabs


# Dependencies
SYMPY_REQVER = '>=0.7.3'
dependencies.add("sympy", _("Symbolic mathematics in the IPython Console"),
                 required_version=SYMPY_REQVER, optional=True)

CYTHON_REQVER = '>=0.21'
dependencies.add("cython", _("Run Cython files in the IPython Console"),
                 required_version=CYTHON_REQVER, optional=True)

QTCONSOLE_REQVER = ">=4.2.0"
dependencies.add("qtconsole", _("Integrate the IPython console"),
                 required_version=QTCONSOLE_REQVER)

IPYTHON_REQVER = ">=4.0;<6.0" if PY2 else ">=4.0"
dependencies.add("IPython", _("IPython interactive python environment"),
                 required_version=IPYTHON_REQVER)

#------------------------------------------------------------------------------
# Existing kernels
#------------------------------------------------------------------------------
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
        cf_open_btn.clicked.connect(self.select_connection_file)

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
        kf_open_btn.clicked.connect(self.select_ssh_key)

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
        self.accept_btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.accept_btns.accepted.connect(self.accept)
        self.accept_btns.rejected.connect(self.reject)

        # Dialog layout
        layout = QVBoxLayout(self)
        layout.addWidget(main_label)
        layout.addLayout(cf_layout)
        layout.addWidget(self.rm_cb)
        layout.addLayout(ssh_form)
        layout.addWidget(self.accept_btns)
                
        # remote kernel checkbox enables the ssh_connection_form
        def ssh_set_enabled(state):
            for wid in [self.hn, self.kf, kf_open_btn, self.pw]:
                wid.setEnabled(state)
            for i in range(ssh_form.rowCount()):
                ssh_form.itemAt(2 * i).widget().setEnabled(state)
       
        ssh_set_enabled(self.rm_cb.checkState())
        self.rm_cb.stateChanged.connect(ssh_set_enabled)

    def select_connection_file(self):
        cf = getopenfilename(self, _('Open connection file'),
                             jupyter_runtime_dir(), '*.json;;*.*')[0]
        self.cf.setText(cf)

    def select_ssh_key(self):
        kf = getopenfilename(self, _('Select ssh key'),
                             get_home_dir(), '*.pem;;*.*')[0]
        self.kf.setText(kf)

    @staticmethod
    def get_connection_parameters(parent=None, dialog=None):
        if not dialog:
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
            path = dialog.cf.text()
            _dir, filename = osp.dirname(path), osp.basename(path)
            if _dir == '' and not filename.endswith('.json'):
                path = osp.join(jupyter_runtime_dir(), 'kernel-'+path+'.json')
            return (path, None, None, None, accepted)


#------------------------------------------------------------------------------
# Config page
#------------------------------------------------------------------------------
class IPythonConsoleConfigPage(PluginConfigPage):

    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("IPython console")

    def setup_page(self):
        newcb = self.create_checkbox
        
        # Interface Group
        interface_group = QGroupBox(_("Interface"))
        banner_box = newcb(_("Display initial banner"), 'show_banner',
                      tip=_("This option lets you hide the message shown at\n"
                            "the top of the console when it's opened."))
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
        interface_layout.addWidget(pager_box)
        interface_layout.addWidget(calltips_box)
        interface_layout.addWidget(ask_box)
        interface_group.setLayout(interface_layout)

        comp_group = QGroupBox(_("Completion Type"))
        comp_label = QLabel(_("Decide what type of completion to use"))
        comp_label.setWordWrap(True)
        completers = [(_("Graphical"), 0), (_("Terminal"), 1), (_("Plain"), 2)]
        comp_box = self.create_combobox(_("Completion:")+"   ", completers,
                                        'completion_type')
        comp_layout = QVBoxLayout()
        comp_layout.addWidget(comp_label)
        comp_layout.addWidget(comp_box)
        comp_group.setLayout(comp_layout)

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
        autoload_pylab_box.setEnabled(self.get_option('pylab'))
        pylab_box.toggled.connect(autoload_pylab_box.setEnabled)
        
        pylab_layout = QVBoxLayout()
        pylab_layout.addWidget(pylab_box)
        pylab_layout.addWidget(autoload_pylab_box)
        pylab_group.setLayout(pylab_layout)
        
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

        backends = [(inline, 0), (automatic, 1), ("Qt5", 2), ("Qt4", 3)]

        if sys.platform == 'darwin':
            backends.append( ("OS X", 4) )
        if sys.platform.startswith('linux'):
            backends.append( ("Gtk3", 5) )
            backends.append( ("Gtk", 6) )
        if PY2:
            backends.append( ("Wx", 7) )
        backends.append( ("Tkinter", 8) )
        backends = tuple(backends)
        
        backend_box = self.create_combobox( _("Backend:")+"   ", backends,
                                       'pylab/backend', default=0,
                                       tip=_("This option will be applied the "
                                             "next time a console is opened."))
        
        backend_layout = QVBoxLayout()
        backend_layout.addWidget(bend_label)
        backend_layout.addWidget(backend_box)
        backend_group.setLayout(backend_layout)
        backend_group.setEnabled(self.get_option('pylab'))
        pylab_box.toggled.connect(backend_group.setEnabled)
        
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
        
        inline_v_layout = QVBoxLayout()
        inline_v_layout.addWidget(inline_label)
        inline_layout = QGridLayout()
        inline_layout.addWidget(format_box.label, 1, 0)
        inline_layout.addWidget(format_box.combobox, 1, 1)
        inline_layout.addWidget(resolution_spin.plabel, 2, 0)
        inline_layout.addWidget(resolution_spin.spinbox, 2, 1)
        inline_layout.addWidget(resolution_spin.slabel, 2, 2)
        inline_layout.addWidget(width_spin.plabel, 3, 0)
        inline_layout.addWidget(width_spin.spinbox, 3, 1)
        inline_layout.addWidget(width_spin.slabel, 3, 2)
        inline_layout.addWidget(height_spin.plabel, 4, 0)
        inline_layout.addWidget(height_spin.spinbox, 4, 1)
        inline_layout.addWidget(height_spin.slabel, 4, 2)
        inline_h_layout = QHBoxLayout()
        inline_h_layout.addLayout(inline_layout)
        inline_h_layout.addStretch(1)
        inline_v_layout.addLayout(inline_h_layout)
        inline_group.setLayout(inline_v_layout)
        inline_group.setEnabled(self.get_option('pylab'))
        pylab_box.toggled.connect(inline_group.setEnabled)

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
        file_radio.toggled.connect(run_file_browser.setEnabled)
        
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
                               "printed style (it requires the Sympy module)."))
        sympy_label.setWordWrap(True)
        sympy_box = newcb(_("Use symbolic math"), "symbolic_math",
                          tip=_("This option loads the Sympy library to work "
                                "with.<br>Please refer to its documentation to "
                                "learn how to use it."))
        
        sympy_layout = QVBoxLayout()
        sympy_layout.addWidget(sympy_label)
        sympy_layout.addWidget(sympy_box)
        sympy_group.setLayout(sympy_layout)

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
        prompts_g_layout  = QGridLayout()
        prompts_g_layout.addWidget(in_prompt_edit.label, 0, 0)
        prompts_g_layout.addWidget(in_prompt_edit.textbox, 0, 1)
        prompts_g_layout.addWidget(out_prompt_edit.label, 1, 0)
        prompts_g_layout.addWidget(out_prompt_edit.textbox, 1, 1)
        prompts_layout.addLayout(prompts_g_layout)
        prompts_group.setLayout(prompts_layout)

        # --- Tabs organization ---
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(interface_group, comp_group,
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


#------------------------------------------------------------------------------
# Plugin widget
#------------------------------------------------------------------------------
class IPythonConsole(SpyderPluginWidget):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """
    CONF_SECTION = 'ipython_console'
    CONFIGWIDGET_CLASS = IPythonConsoleConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    
    # Signals
    focus_changed = Signal()
    edit_goto = Signal((str, int, str), (str, int, str, bool))

    def __init__(self, parent, testing=False):
        """Ipython Console constructor."""
        if PYQT5:
            SpyderPluginWidget.__init__(self, parent, main = parent)
        else:
            SpyderPluginWidget.__init__(self, parent)

        self.tabwidget = None
        self.menu_actions = None

        self.help = None               # Help plugin
        self.historylog = None         # History log plugin
        self.variableexplorer = None   # Variable explorer plugin
        self.editor = None             # Editor plugin

        self.master_clients = 0
        self.clients = []
        self.mainwindow_close = False
        self.create_new_client_if_empty = True
        self.testing = testing

        # Initialize plugin
        if not self.testing:
            self.initialize_plugin()

        # Create temp dir on testing to save kernel errors
        if self.testing:
            if not osp.isdir(programs.TEMPDIR):
                os.mkdir(programs.TEMPDIR)

        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions, rename_tabs=True)
        if hasattr(self.tabwidget, 'setDocumentMode')\
           and not sys.platform == 'darwin':
            # Don't set document mode to true on OSX because it generates
            # a crash when the console is detached from the main window
            # Fixes Issue 561
            self.tabwidget.setDocumentMode(True)
        self.tabwidget.currentChanged.connect(self.refresh_plugin)
        self.tabwidget.move_data.connect(self.move_tab)

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
        if not self.testing:
            self.register_widget_shortcuts(self.find_widget)
        layout.addWidget(self.find_widget)

        self.setLayout(layout)

        # Accepting drops
        self.setAcceptDrops(True)

    #------ SpyderPluginMixin API ---------------------------------------------
    def update_font(self):
        """Update font from Preferences"""
        font = self.get_plugin_font()
        for client in self.clients:
            client.set_font(font)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        font_n = 'plugin_font'
        font_o = self.get_plugin_font()
        help_n = 'connect_to_oi'
        help_o = CONF.get('help', 'connect/ipython_console')
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = CONF.get('color_schemes', 'selected')
        for client in self.clients:
            control = client.get_control()
            if font_n in options:
                client.set_font(font_o)
            if help_n in options and control is not None:
                control.set_help_enabled(help_o)
            if color_scheme_n in options:
                client.set_color_scheme(color_scheme_o)

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
        return ima.icon('ipython_console')
    
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
        self.mainwindow_close = True
        for client in self.clients:
            client.shutdown()
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
        else:
            control = None
            widgets = []
        self.find_widget.set_editor(control)
        self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})
        if client and not self.testing:
            sw = client.shellwidget
            self.variableexplorer.set_shellwidget_from_id(id(sw))
            self.help.set_shell(sw)
        self.update_plugin_title.emit()

    def get_plugin_actions(self):
        """Return a list of actions related to plugin."""
        create_client_action = create_action(
                                   self,
                                   _("Open an &IPython console"),
                                   icon=ima.icon('ipython_console'),
                                   triggered=self.create_new_client,
                                   context=Qt.WidgetWithChildrenShortcut)
        self.register_shortcut(create_client_action, context="ipython_console",
                               name="New tab")

        restart_action = create_action(self, _("Restart kernel"),
                                       icon=ima.icon('restart'),
                                       triggered=self.restart_kernel,
                                       context=Qt.WidgetWithChildrenShortcut)
        self.register_shortcut(restart_action, context="ipython_console",
                               name="Restart kernel")

        connect_to_kernel_action = create_action(self,
               _("Connect to an existing kernel"), None, None,
               _("Open a new IPython console connected to an existing kernel"),
               triggered=self.create_client_for_kernel)
        
        rename_tab_action = create_action(self, _("Rename tab"),
                                       icon=ima.icon('rename'),
                                       triggered=self.tab_name_editor)
        
        # Add the action to the 'Consoles' menu on the main window
        main_consoles_menu = self.main.consoles_menu_actions
        main_consoles_menu.insert(0, create_client_action)
        main_consoles_menu += [MENU_SEPARATOR, restart_action,
                               connect_to_kernel_action]
        
        # Plugin actions
        self.menu_actions = [create_client_action, MENU_SEPARATOR,
                             restart_action, connect_to_kernel_action,
                             MENU_SEPARATOR, rename_tab_action]
        
        return self.menu_actions

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)

        self.help = self.main.help
        self.historylog = self.main.historylog
        self.variableexplorer = self.main.variableexplorer
        self.editor = self.main.editor
        self.explorer = self.main.explorer
        self.projects = self.main.projects

        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.edit_goto.connect(self.editor.load)
        self.edit_goto[str, int, str, bool].connect(
                         lambda fname, lineno, word, processevents:
                             self.editor.load(fname, lineno, word,
                                              processevents=processevents))
        self.editor.breakpoints_saved.connect(self.set_spyder_breakpoints)
        self.editor.run_in_current_ipyclient.connect(
                                         self.run_script_in_current_client)
        self.main.workingdirectory.set_current_console_wd.connect(
                                     self.set_current_client_working_directory)
        self.explorer.open_interpreter.connect(self.create_client_from_path)
        self.projects.open_interpreter.connect(self.create_client_from_path)

    #------ Public API (for clients) ------------------------------------------
    def get_clients(self):
        """Return clients list"""
        return [cl for cl in self.clients if isinstance(cl, ClientWidget)]

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

    def get_current_shellwidget(self):
        """Return the shellwidget of the current client"""
        client = self.get_current_client()
        if client is not None:
            return client.shellwidget

    def run_script_in_current_client(self, filename, wdir, args, debug,
                                     post_mortem, clear_variables):
        """Run script in current client, if any"""
        norm = lambda text: remove_backslashes(to_text_string(text))
        client = self.get_current_client()
        if client is not None:
            # Internal kernels, use runfile
            if client.get_kernel() is not None:
                line = "%s('%s'" % ('debugfile' if debug else 'runfile',
                                    norm(filename))
                if args:
                    line += ", args='%s'" % norm(args)
                if wdir:
                    line += ", wdir='%s'" % norm(wdir)
                if post_mortem:
                    line += ", post_mortem=True"
                line += ")"
            else: # External kernels, use %run
                line = "%run "
                if debug:
                    line += "-d "
                line += "\"%s\"" % to_text_string(filename)
                if args:
                    line += " %s" % norm(args)
            self.execute_code(line, clear_variables)
            self.visibility_changed(True)
            self.raise_()
        else:
            #XXX: not sure it can really happen
            QMessageBox.warning(self, _('Warning'),
                _("No IPython console is currently available to run <b>%s</b>."
                  "<br><br>Please open a new one and try again."
                  ) % osp.basename(filename), QMessageBox.Ok)

    def set_current_client_working_directory(self, directory):
        """Set current client working directory."""
        shellwidget = self.get_current_shellwidget()
        if shellwidget is not None:
            directory = encoding.to_unicode_from_fs(directory)
            shellwidget.set_cwd(directory)

    def execute_code(self, lines, clear_variables=False):
        """Execute code instructions."""
        sw = self.get_current_shellwidget()
        if sw is not None:
            if sw._reading:
                pass
            else:
                if clear_variables:
                    sw.reset_namespace(force=True)
                sw.execute(to_text_string(to_text_string(lines)))
            self.activateWindow()
            self.get_current_client().get_control().setFocus()

    def write_to_stdin(self, line):
        sw = self.get_current_shellwidget()
        if sw is not None:
            sw.write_to_stdin(line)

    @Slot()
    @Slot(bool)
    @Slot(str)
    @Slot(bool, str)
    def create_new_client(self, give_focus=True, path=''):
        """Create a new client"""
        self.master_clients += 1
        client_id = dict(int_id=to_text_string(self.master_clients),
                         str_id='A')
        cf = self._new_connection_file()
        client = ClientWidget(self, id_=client_id,
                              history_filename=get_conf_path('history.py'),
                              config_options=self.config_options(),
                              additional_options=self.additional_options(),
                              interpreter_versions=self.interpreter_versions(),
                              connection_file=cf,
                              menu_actions=self.menu_actions)
        self.add_tab(client, name=client.get_name())

        if cf is None:
            error_msg = _("The directory {} is not writable and it is "
                          "required to create IPython consoles. Please make "
                          "it writable.").format(jupyter_runtime_dir())
            client.show_kernel_error(error_msg)
            return

        # Check if ipykernel is present in the external interpreter.
        # Else we won't be able to create a client
        if not CONF.get('main_interpreter', 'default'):
            pyexec = CONF.get('main_interpreter', 'executable')
            ipykernel_present = programs.is_module_installed('ipykernel',
                                                            interpreter=pyexec)
            if not ipykernel_present:
                client.show_kernel_error(_("Your Python environment or "
                                     "installation doesn't "
                                     "have the <tt>ipykernel</tt> module "
                                     "installed on it. Without this module is "
                                     "not possible for Spyder to create a "
                                     "console for you.<br><br>"
                                     "You can install <tt>ipykernel</tt> by "
                                     "running in a terminal:<br><br>"
                                     "<tt>pip install ipykernel</tt><br><br>"
                                     "or<br><br>"
                                     "<tt>conda install ipykernel</tt>"))
                return

        self.connect_client_to_kernel(client, path)
        if client.shellwidget.kernel_manager is None:
            return
        self.register_client(client)

    @Slot()
    def create_client_for_kernel(self):
        """Create a client connected to an existing kernel"""
        connect_output = KernelConnectionDialog.get_connection_parameters(self)
        (connection_file, hostname, sshkey, password, ok) = connect_output
        if not ok:
            return
        else:
            self._create_client_for_kernel(connection_file, hostname, sshkey,
                                           password)

    def connect_client_to_kernel(self, client, path):
        """Connect a client to its kernel"""
        connection_file = client.connection_file
        stderr_file = client.stderr_file
        km, kc = self.create_kernel_manager_and_kernel_client(connection_file,
                                                              stderr_file)
        # An error occurred if this is True
        if is_string(km) and kc is None:
            client.shellwidget.kernel_manager = None
            client.show_kernel_error(km)
            return

        kc.started_channels.connect(lambda c=client: self.process_started(c))
        kc.stopped_channels.connect(lambda c=client: self.process_finished(c))
        kc.start_channels(shell=True, iopub=True)

        shellwidget = client.shellwidget
        shellwidget.kernel_manager = km
        shellwidget.kernel_client = kc

        if path:
            shellwidget.set_cwd(path)

    def set_editor(self):
        """Set the editor used by the %edit magic"""
        python = sys.executable
        if DEV:
            spyder_start_directory = get_module_path('spyder')
            bootstrap_script = osp.join(osp.dirname(spyder_start_directory),
                                        'bootstrap.py')
            editor = u'{0} {1} --'.format(python, bootstrap_script)
        else:
            import1 = "import sys"
            import2 = "from spyder.app.start import send_args_to_spyder"
            code = "send_args_to_spyder([sys.argv[-1]])"
            editor = u"{0} -c '{1}; {2}; {3}'".format(python,
                                                      import1,
                                                      import2,
                                                      code)
        return to_text_string(editor)

    def config_options(self):
        """
        Generate a Trailets Config instance for shell widgets using our
        config system

        This lets us create each widget with its own config
        """
        # ---- Jupyter config ----
        try:
            full_cfg = load_pyconfig_files(['jupyter_qtconsole_config.py'],
                                           jupyter_config_dir())

            # From the full config we only select the JupyterWidget section
            # because the others have no effect here.
            cfg = Config({'JupyterWidget': full_cfg.JupyterWidget})
        except:
            cfg = Config()

        # ---- Spyder config ----
        spy_cfg = Config()

        # Make the pager widget a rich one (i.e a QTextEdit)
        spy_cfg.JupyterWidget.kind = 'rich'

        # Gui completion widget
        completion_type_o = self.get_option('completion_type')
        completions = {0: "droplist", 1: "ncurses", 2: "plain"}
        spy_cfg.JupyterWidget.gui_completion = completions[completion_type_o]

        # Pager
        pager_o = self.get_option('use_pager')
        if pager_o:
            spy_cfg.JupyterWidget.paging = 'inside'
        else:
            spy_cfg.JupyterWidget.paging = 'none'

        # Calltips
        calltips_o = self.get_option('show_calltips')
        spy_cfg.JupyterWidget.enable_calltips = calltips_o

        # Buffer size
        buffer_size_o = self.get_option('buffer_size')
        spy_cfg.JupyterWidget.buffer_size = buffer_size_o

        # Prompts
        in_prompt_o = self.get_option('in_prompt')
        out_prompt_o = self.get_option('out_prompt')
        if in_prompt_o:
            spy_cfg.JupyterWidget.in_prompt = in_prompt_o
        if out_prompt_o:
            spy_cfg.JupyterWidget.out_prompt = out_prompt_o

        # Style
        color_scheme = CONF.get('color_schemes', 'selected')
        style_sheet = create_qss_style(color_scheme)[0]
        spy_cfg.JupyterWidget.style_sheet = style_sheet
        spy_cfg.JupyterWidget.syntax_style = color_scheme

        # Editor for %edit
        if CONF.get('main', 'single_instance'):
            spy_cfg.JupyterWidget.editor = self.set_editor()

        # Merge QtConsole and Spyder configs. Spyder prefs will have
        # prevalence over QtConsole ones
        cfg._merge(spy_cfg)
        return cfg

    def interpreter_versions(self):
        """Python and IPython versions used by clients"""
        if CONF.get('main_interpreter', 'default'):
            from IPython.core import release
            versions = dict(
                python_version = sys.version.split("\n")[0].strip(),
                ipython_version = release.version
            )
        else:
            import subprocess
            versions = {}
            pyexec = CONF.get('main_interpreter', 'executable')
            py_cmd = "%s -c 'import sys; print(sys.version.split(\"\\n\")[0])'" % \
                     pyexec
            ipy_cmd = "%s -c 'import IPython.core.release as r; print(r.version)'" \
                      % pyexec
            for cmd in [py_cmd, ipy_cmd]:
                try:
                    proc = programs.run_shell_command(cmd)
                    output, _err = proc.communicate()
                except subprocess.CalledProcessError:
                    output = ''
                output = output.decode().split('\n')[0].strip()
                if 'IPython' in cmd:
                    versions['ipython_version'] = output
                else:
                    versions['python_version'] = output

        return versions

    def additional_options(self):
        """
        Additional options for shell widgets that are not defined
        in JupyterWidget config options
        """
        options = dict(
            pylab=self.get_option('pylab'),
            autoload_pylab=self.get_option('pylab/autoload'),
            sympy=self.get_option('symbolic_math'),
            show_banner=self.get_option('show_banner')
        )

        return options

    def register_client(self, client, give_focus=True):
        """Register new client"""
        client.configure_shellwidget(give_focus=give_focus)

        # Local vars
        shellwidget = client.shellwidget
        control = shellwidget._control
        page_control = shellwidget._page_control

        # Create new clients with Ctrl+T shortcut
        shellwidget.new_client.connect(self.create_new_client)

        # For tracebacks
        control.go_to_error.connect(self.go_to_error)

        shellwidget.sig_pdb_step.connect(
                              lambda fname, lineno, shellwidget=shellwidget:
                              self.pdb_has_stopped(fname, lineno, shellwidget))

        # Connect text widget to Help
        if self.help is not None:
            control.set_help(self.help)
            control.set_help_enabled(CONF.get('help', 'connect/ipython_console'))

        # Connect client to our history log
        if self.historylog is not None:
            self.historylog.add_history(client.history_filename)
            client.append_to_history.connect(self.historylog.append_to_history)
        
        # Set font for client
        client.set_font( self.get_plugin_font() )
        
        # Connect focus signal to client's control widget
        control.focus_changed.connect(lambda: self.focus_changed.emit())
        
        # Update the find widget if focus changes between control and
        # page_control
        self.find_widget.set_editor(control)
        if page_control:
            page_control.focus_changed.connect(lambda: self.focus_changed.emit())
            control.visibility_changed.connect(self.refresh_plugin)
            page_control.visibility_changed.connect(self.refresh_plugin)
            page_control.show_find_widget.connect(self.find_widget.show)

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
        if not self.mainwindow_close and not force:
            close_all = True
            if self.get_option('ask_before_closing'):
                close = QMessageBox.question(self, self.get_plugin_title(),
                                       _("Do you want to close this console?"),
                                       QMessageBox.Yes | QMessageBox.No)
                if close == QMessageBox.No:
                    return
            if len(self.get_related_clients(client)) > 0:
                close_all = QMessageBox.question(self, self.get_plugin_title(),
                         _("Do you want to close all other consoles connected "
                           "to the same kernel as this one?"),
                           QMessageBox.Yes | QMessageBox.No)
            client.shutdown()
            if close_all == QMessageBox.Yes:
                self.close_related_clients(client)
        client.close()

        # Note: client index may have changed after closing related widgets
        self.tabwidget.removeTab(self.tabwidget.indexOf(client))
        self.clients.remove(client)
        if not self.tabwidget.count() and self.create_new_client_if_empty:
            self.create_new_client()
        self.update_plugin_title.emit()

    def get_client_index_from_id(self, client_id):
        """Return client index from id"""
        for index, client in enumerate(self.clients):
            if id(client) == client_id:
                return index

    def rename_client_tab(self, client):
        """Rename client's tab"""
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

    def restart(self):
        """
        Restart the console

        This is needed when we switch projects to update PYTHONPATH
        and the selected interpreter
        """
        self.master_clients = 0
        self.create_new_client_if_empty = False
        for i in range(len(self.clients)):
            client = self.clients[-1]
            try:
                client.shutdown()
            except Exception as e:
                QMessageBox.warning(self, _('Warning'),
                    _("It was not possible to restart the IPython console "
                      "when switching to this project. "
                      "The error was {0}").format(e), QMessageBox.Ok)
            self.close_client(client=client, force=True)
        self.create_new_client(give_focus=False)
        self.create_new_client_if_empty = True

    def pdb_has_stopped(self, fname, lineno, shellwidget):
        """Python debugger has just stopped at frame (fname, lineno)"""
        # This is a unique form of the edit_goto signal that is intended to
        # prevent keyboard input from accidentally entering the editor
        # during repeated, rapid entry of debugging commands.
        self.edit_goto[str, int, str, bool].emit(fname, lineno, '', False)
        self.activateWindow()
        shellwidget._control.setFocus()

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into all clients"""
        for cl in self.clients:
            cl.shellwidget.set_spyder_breakpoints()

    @Slot(str)
    def create_client_from_path(self, path):
        """Create a client with its cwd pointing to path"""
        self.create_new_client(path=path)

    #------ Public API (for kernels) ------------------------------------------
    def ssh_tunnel(self, *args, **kwargs):
        if os.name == 'nt':
            return zmqtunnel.paramiko_tunnel(*args, **kwargs)
        else:
            return openssh_tunnel(self, *args, **kwargs)

    def tunnel_to_kernel(self, connection_info, hostname, sshkey=None,
                         password=None, timeout=10):
        """
        Tunnel connections to a kernel via ssh.

        Remote ports are specified in the connection info ci.
        """
        lports = zmqtunnel.select_random_ports(4)
        rports = (connection_info['shell_port'], connection_info['iopub_port'],
                  connection_info['stdin_port'], connection_info['hb_port'])
        remote_ip = connection_info['ip']
        for lp, rp in zip(lports, rports):
            self.ssh_tunnel(lp, rp, hostname, remote_ip, sshkey, password,
                            timeout)
        return tuple(lports)

    def create_kernel_spec(self):
        """Create a kernel spec for our own kernels"""
        # Before creating our kernel spec, we always need to
        # set this value in spyder.ini
        if not self.testing:
            CONF.set('main', 'spyder_pythonpath',
                     self.main.get_spyder_pythonpath())
        return SpyderKernelSpec()

    def create_kernel_manager_and_kernel_client(self, connection_file,
                                                stderr_file):
        """Create kernel manager and client."""
        # Kernel spec
        kernel_spec = self.create_kernel_spec()
        if not kernel_spec.env.get('PYTHONPATH'):
            error_msg = _("This error was most probably caused by installing "
                          "Spyder in a directory with non-ascii characters "
                          "(i.e. characters with tildes, apostrophes or "
                          "non-latin symbols).<br><br>"
                          "To fix it, please <b>reinstall</b> Spyder in a "
                          "different location.")
            return (error_msg, None)

        # Kernel manager
        kernel_manager = QtKernelManager(connection_file=connection_file,
                                         config=None, autorestart=True)
        kernel_manager._kernel_spec = kernel_spec

        # Save stderr in a file to read it later in case of errors
        stderr = codecs.open(stderr_file, 'w', encoding='utf-8')
        kernel_manager.start_kernel(stderr=stderr)

        # Kernel client
        kernel_client = kernel_manager.client()

        # Increase time to detect if a kernel is alive
        # See Issue 3444
        kernel_client.hb_channel.time_to_dead = 6.0

        return kernel_manager, kernel_client

    def restart_kernel(self):
        """Restart kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            client.restart_kernel()

    #------ Public API (for tabs) ---------------------------------------------
    def add_tab(self, widget, name):
        """Add tab"""
        self.clients.append(widget)
        index = self.tabwidget.addTab(widget, name)
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
        self.update_plugin_title.emit()

    #------ Public API (for help) ---------------------------------------------
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(to_text_string(text))
        if match:
            fname, lnb = match.groups()
            self.edit_goto.emit(osp.abspath(fname), int(lnb), '')

    @Slot()
    def show_intro(self):
        """Show intro to IPython help"""
        from IPython.core.usage import interactive_usage
        self.help.show_rich_text(interactive_usage)

    @Slot()
    def show_guiref(self):
        """Show qtconsole help"""
        from qtconsole.usage import gui_reference
        self.help.show_rich_text(gui_reference, collapse=True)

    @Slot()
    def show_quickref(self):
        """Show IPython Cheat Sheet"""
        from IPython.core.usage import quick_reference
        self.help.show_plain_text(quick_reference)

    #------ Private API -------------------------------------------------------
    def _new_connection_file(self):
        """
        Generate a new connection file

        Taken from jupyter_client/console_app.py
        Licensed under the BSD license
        """
        # Check if jupyter_runtime_dir exists (Spyder addition)
        if not osp.isdir(jupyter_runtime_dir()):
            try:
                os.makedirs(jupyter_runtime_dir())
            except PermissionError:
                return None
        cf = ''
        while not cf:
            ident = str(uuid.uuid4()).split('-')[-1]
            cf = os.path.join(jupyter_runtime_dir(), 'kernel-%s.json' % ident)
            cf = cf if not os.path.exists(cf) else ''
        return cf

    def process_started(self, client):
        if self.help is not None:
            self.help.set_shell(client.shellwidget)
        if self.variableexplorer is not None:
            self.variableexplorer.add_shellwidget(client.shellwidget)

    def process_finished(self, client):
        if self.variableexplorer is not None:
            self.variableexplorer.remove_shellwidget(id(client.shellwidget))

    def connect_external_kernel(self, shellwidget):
        """
        Connect an external kernel to the Variable Explorer and Help, if
        it is a Spyder kernel.
        """
        sw = shellwidget
        kc = shellwidget.kernel_client
        if self.help is not None:
            self.help.set_shell(sw)
        if self.variableexplorer is not None:
            self.variableexplorer.add_shellwidget(sw)
            sw.set_namespace_view_settings()
            sw.refresh_namespacebrowser()
            kc.stopped_channels.connect(lambda :
                self.variableexplorer.remove_shellwidget(id(sw)))

    def _create_client_for_kernel(self, connection_file, hostname, sshkey,
                                  password):
        # Verifying if the connection file exists
        try:
            cf_path = osp.dirname(connection_file)
            cf_filename = osp.basename(connection_file)
            # To change a possible empty string to None
            cf_path = cf_path if cf_path else None
            connection_file = find_connection_file(filename=cf_filename, 
                                                   path=cf_path)
        except (IOError, UnboundLocalError):
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to "
                                   "<b>%s</b>") % connection_file)
            return

        # Getting the master name that corresponds to the client
        # (i.e. the i in i/A)
        master_name = None
        external_kernel = False
        slave_ord = ord('A') - 1
        kernel_manager = None
        for cl in self.get_clients():
            if connection_file in cl.connection_file:
                if cl.get_kernel() is not None:
                    kernel_manager = cl.get_kernel()
                connection_file = cl.connection_file
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
            external_kernel = True

        # Set full client name
        name = master_name + '/' + chr(slave_ord + 1)

        # Creating the client
        client = ClientWidget(self, name=name,
                              history_filename=get_conf_path('history.py'),
                              config_options=self.config_options(),
                              additional_options=self.additional_options(),
                              interpreter_versions=self.interpreter_versions(),
                              connection_file=connection_file,
                              menu_actions=self.menu_actions,
                              hostname=hostname,
                              external_kernel=external_kernel,
                              slave=True)

        # Create kernel client
        kernel_client = QtKernelClient(connection_file=connection_file)
        kernel_client.load_connection_file()
        if hostname is not None:
            try:
                connection_info = dict(ip = kernel_client.ip,
                                       shell_port = kernel_client.shell_port,
                                       iopub_port = kernel_client.iopub_port,
                                       stdin_port = kernel_client.stdin_port,
                                       hb_port = kernel_client.hb_port)
                newports = self.tunnel_to_kernel(connection_info, hostname,
                                                 sshkey, password)
                (kernel_client.shell_port,
                 kernel_client.iopub_port,
                 kernel_client.stdin_port,
                 kernel_client.hb_port) = newports
            except Exception as e:
                QMessageBox.critical(self, _('Connection error'),
                                   _("Could not open ssh tunnel. The "
                                     "error was:\n\n") + to_text_string(e))
                return

        # Assign kernel manager and client to shellwidget
        client.shellwidget.kernel_client = kernel_client
        client.shellwidget.kernel_manager = kernel_manager
        kernel_client.start_channels()
        if external_kernel:
            client.shellwidget.sig_is_spykernel.connect(
                    self.connect_external_kernel)
            client.shellwidget.is_spyder_kernel()

        # Adding a new tab for the client
        self.add_tab(client, name=client.get_name())

        # Register client
        self.register_client(client)

    def tab_name_editor(self):
        """Trigger the tab name editor."""
        index = self.tabwidget.currentIndex()
        self.tabwidget.tabBar().tab_name_editor.edit_tab(index)
