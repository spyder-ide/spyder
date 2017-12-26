# -*- coding:utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Client widget for the IPython Console

This is the widget used on all its tabs
"""

# Standard library imports
from __future__ import absolute_import  # Fix for Issue 1356

import codecs
import os
import os.path as osp
from string import Template
from threading import Thread
from time import ctime, time, strftime, gmtime

# Third party imports (qtpy)
from qtpy.QtCore import QUrl, QTimer, Signal, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QMenu, QMessageBox,
                            QToolButton, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _, get_image_path, get_module_source_path
from spyder.config.gui import get_font, get_shortcut
from spyder.utils import icon_manager as ima
from spyder.utils import sourcecode
from spyder.utils.encoding import get_coding
from spyder.utils.environ import RemoteEnvDialog
from spyder.utils.ipython.style import create_qss_style
from spyder.utils.programs import TEMPDIR
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, DialogManager,
                                    MENU_SEPARATOR)
from spyder.py3compat import to_text_string
from spyder.widgets.browser import WebView
from spyder.widgets.ipythonconsole import ShellWidget
from spyder.widgets.mixins import SaveHistoryMixin
from spyder.widgets.variableexplorer.collectionseditor import CollectionsEditor


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
# Client widget
#-----------------------------------------------------------------------------
class ClientWidget(QWidget, SaveHistoryMixin):
    """
    Client widget for the IPython Console

    This is a widget composed of a shell widget and a WebView info widget
    to print different messages there.
    """

    SEPARATOR = '{0}## ---({1})---'.format(os.linesep*2, ctime())
    INITHISTORY = ['# -*- coding: utf-8 -*-',
                   '# *** Spyder Python Console History Log ***',]

    append_to_history = Signal(str, str)

    def __init__(self, plugin, id_,
                 history_filename, config_options,
                 additional_options, interpreter_versions,
                 connection_file=None, hostname=None,
                 menu_actions=None, slave=False,
                 external_kernel=False, given_name=None,
                 options_button=None,
                 show_elapsed_time=False,
                 reset_warning=True):
        super(ClientWidget, self).__init__(plugin)
        SaveHistoryMixin.__init__(self, history_filename)

        # --- Init attrs
        self.id_ = id_
        self.connection_file = connection_file
        self.hostname = hostname
        self.menu_actions = menu_actions
        self.slave = slave
        self.external_kernel = external_kernel
        self.given_name = given_name
        self.show_elapsed_time = show_elapsed_time
        self.reset_warning = reset_warning

        # --- Other attrs
        self.options_button = options_button
        self.stop_button = None
        self.reset_button = None
        self.stop_icon = ima.icon('stop')
        self.history = []
        self.allow_rename = True
        self.stderr_dir = None

        # --- Widgets
        self.shellwidget = ShellWidget(config=config_options,
                                       ipyclient=self,
                                       additional_options=additional_options,
                                       interpreter_versions=interpreter_versions,
                                       external_kernel=external_kernel,
                                       local_kernel=True)
        self.infowidget = WebView(self)
        self.set_infowidget_font()
        self.loading_page = self._create_loading_page()
        self._show_loading_page()

        # Elapsed time
        self.time_label = None
        self.t0 = None
        self.timer = QTimer(self)

        # --- Layout
        vlayout = QVBoxLayout()
        toolbar_buttons = self.get_toolbar_buttons()

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.create_time_label())
        hlayout.addStretch(0)
        for button in toolbar_buttons:
            hlayout.addWidget(button)

        vlayout.addLayout(hlayout)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.shellwidget)
        vlayout.addWidget(self.infowidget)
        self.setLayout(vlayout)

        # --- Exit function
        self.exit_callback = lambda: plugin.close_client(client=self)

        # --- Dialog manager
        self.dialog_manager = DialogManager()

        # Show timer
        self.update_time_label_visibility()

    #------ Public API --------------------------------------------------------
    @property
    def kernel_id(self):
        """Get kernel id"""
        if self.connection_file is not None:
            json_file = osp.basename(self.connection_file)
            return json_file.split('.json')[0]

    @property
    def stderr_file(self):
        """Filename to save kernel stderr output."""
        stderr_file = None
        if self.connection_file is not None:
            stderr_file = self.kernel_id + '.stderr'
            if self.stderr_dir is not None:
                stderr_file = osp.join(self.stderr_dir, stderr_file)
            else:
                try:
                    if not osp.isdir(TEMPDIR):
                        os.makedirs(TEMPDIR)
                    stderr_file = osp.join(TEMPDIR, stderr_file)
                except (IOError, OSError):
                    stderr_file = None
        return stderr_file

    def configure_shellwidget(self, give_focus=True):
        """Configure shellwidget after kernel is started"""
        if give_focus:
            self.get_control().setFocus()

        # Set exit callback
        self.shellwidget.set_exit_callback()

        # To save history
        self.shellwidget.executing.connect(self.add_to_history)

        # For Mayavi to run correctly
        self.shellwidget.executing.connect(
            self.shellwidget.set_backend_for_mayavi)

        # To update history after execution
        self.shellwidget.executed.connect(self.update_history)

        # To update the Variable Explorer after execution
        self.shellwidget.executed.connect(
            self.shellwidget.refresh_namespacebrowser)

        # To enable the stop button when executing a process
        self.shellwidget.executing.connect(self.enable_stop_button)

        # To disable the stop button after execution stopped
        self.shellwidget.executed.connect(self.disable_stop_button)

        # To show kernel restarted/died messages
        self.shellwidget.sig_kernel_restarted.connect(
            self.kernel_restarted_message)

        # To correctly change Matplotlib backend interactively
        self.shellwidget.executing.connect(
            self.shellwidget.change_mpl_backend)

        # To show env and sys.path contents
        self.shellwidget.sig_show_syspath.connect(self.show_syspath)
        self.shellwidget.sig_show_env.connect(self.show_env)

        # To sync with working directory toolbar
        self.shellwidget.executed.connect(self.shellwidget.get_cwd)

        # To apply style
        if not create_qss_style(self.shellwidget.syntax_style)[1]:
            self.shellwidget.silent_execute("%colors linux")
        else:
            self.shellwidget.silent_execute("%colors lightbg")

        # To hide the loading page
        self.shellwidget.sig_prompt_ready.connect(self._hide_loading_page)

        # Show possible errors when setting Matplotlib backend
        self.shellwidget.sig_prompt_ready.connect(
            self._show_mpl_backend_errors)

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
        """Show kernel initialization errors in infowidget."""
        # Replace end of line chars with <br>
        eol = sourcecode.get_eol_chars(error)
        if eol:
            error = error.replace(eol, '<br>')

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
        if self.given_name is None:
            # Name according to host
            if self.hostname is None:
                name = _("Console")
            else:
                name = self.hostname
            # Adding id to name
            client_id = self.id_['int_id'] + u'/' + self.id_['str_id']
            name = name + u' ' + client_id
        else:
            name = self.given_name + u'/' + self.id_['str_id']
        return name

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
        reset_action = create_action(self, _("Remove all variables"),
                                     icon=ima.icon('editdelete'),
                                     triggered=self.reset_namespace)

        self.show_time_action = create_action(self, _("Show elapsed time"),
                                         toggled=self.set_elapsed_time_visible)

        env_action = create_action(
                        self,
                        _("Show environment variables"),
                        icon=ima.icon('environ'),
                        triggered=self.shellwidget.get_env
                     )

        syspath_action = create_action(
                            self,
                            _("Show sys.path contents"),
                            icon=ima.icon('syspath'),
                            triggered=self.shellwidget.get_syspath
                         )

        self.show_time_action.setChecked(self.show_elapsed_time)
        additional_actions = [reset_action,
                              MENU_SEPARATOR,
                              env_action,
                              syspath_action,
                              self.show_time_action]

        if self.menu_actions is not None:
            return self.menu_actions + additional_actions
        else:
            return additional_actions

    def get_toolbar_buttons(self):
        """Return toolbar buttons list."""
        buttons = []

        # Code to add the stop button
        if self.stop_button is None:
            self.stop_button = create_toolbutton(
                                   self,
                                   text=_("Stop"),
                                   icon=self.stop_icon,
                                   tip=_("Stop the current command"))
            self.disable_stop_button()
            # set click event handler
            self.stop_button.clicked.connect(self.stop_button_click_handler)
        if self.stop_button is not None:
            buttons.append(self.stop_button)

        # Reset namespace button
        if self.reset_button is None:
            self.reset_button = create_toolbutton(
                                    self,
                                    text=_("Remove"),
                                    icon=ima.icon('editdelete'),
                                    tip=_("Remove all variables"),
                                    triggered=self.reset_namespace)
        if self.reset_button is not None:
            buttons.append(self.reset_button)

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
                                          QKeySequence(get_shortcut(
                                                  'console',
                                                  'clear line')),
                                          triggered=self.clear_line)

        reset_namespace_action = create_action(self, _("Remove all variables"),
                                               QKeySequence(get_shortcut(
                                                       'ipython_console',
                                                       'reset namespace')),
                                               icon=ima.icon('editdelete'),
                                               triggered=self.reset_namespace)

        clear_console_action = create_action(self, _("Clear console"),
                                             QKeySequence(get_shortcut('console',
                                                               'clear shell')),
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

    def set_color_scheme(self, color_scheme):
        """Set IPython color scheme."""
        self.shellwidget.set_color_scheme(color_scheme)

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
        sw = self.shellwidget

        message = _('Are you sure you want to restart the kernel?')
        buttons = QMessageBox.Yes | QMessageBox.No
        result = QMessageBox.question(self, _('Restart kernel?'),
                                      message, buttons)

        if result == QMessageBox.Yes:
            if sw.kernel_manager:
                if self.infowidget.isVisible():
                    self.infowidget.hide()
                    sw.show()
                try:
                    sw.kernel_manager.restart_kernel()
                except RuntimeError as e:
                    sw._append_plain_text(
                        _('Error restarting kernel: %s\n') % e,
                        before_prompt=True
                    )
                else:
                    sw.reset(clear=True)
                    sw._append_html(_("<br>Restarting kernel...\n<hr><br>"),
                                    before_prompt=False)
            else:
                sw._append_plain_text(
                    _('Cannot restart a kernel not started by Spyder\n'),
                    before_prompt=True
                )

    @Slot(str)
    def kernel_restarted_message(self, msg):
        """Show kernel restarted/died messages."""
        try:
            stderr = codecs.open(self.stderr_file, 'r',
                                 encoding='utf-8').read()
        except UnicodeDecodeError:
            # This is needed since the stderr file could be encoded
            # in something different to utf-8.
            # See issue 4191
            try:
                stderr = self._read_stderr()
            except:
                stderr = None
        except (OSError, IOError):
            stderr = None

        if stderr:
            self.show_kernel_error('<tt>%s</tt>' % stderr)
        else:
            self.shellwidget._append_html("<br>%s<hr><br>" % msg,
                                          before_prompt=False)


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
        self.shellwidget.reset_namespace(warning=self.reset_warning,
                                         message=True)

    def update_history(self):
        self.history = self.shellwidget._history

    @Slot(object)
    def show_syspath(self, syspath):
        """Show sys.path contents."""
        if syspath is not None:
            editor = CollectionsEditor()
            editor.setup(syspath, title="sys.path contents", readonly=True,
                         width=600, icon=ima.icon('syspath'))
            self.dialog_manager.show(editor)
        else:
            return

    @Slot(object)
    def show_env(self, env):
        """Show environment variables."""
        self.dialog_manager.show(RemoteEnvDialog(env))

    def create_time_label(self):
        """Create elapsed time label widget (if necessary) and return it"""
        if self.time_label is None:
            self.time_label = QLabel()
        return self.time_label

    def show_time(self, end=False):
        """Text to show in time_label."""
        if self.time_label is None:
            return
        elapsed_time = time() - self.t0
        if elapsed_time > 24 * 3600: # More than a day...!
            fmt = "%d %H:%M:%S"
        else:
            fmt = "%H:%M:%S"
        if end:
            color = "#AAAAAA"
        else:
            color = "#AA6655"
        text = "<span style=\'color: %s\'><b>%s" \
               "</b></span>" % (color, strftime(fmt, gmtime(elapsed_time)))
        self.time_label.setText(text)

    def update_time_label_visibility(self):
        """Update elapsed time visibility."""
        self.time_label.setVisible(self.show_elapsed_time)

    @Slot(bool)
    def set_elapsed_time_visible(self, state):
        """Slot to show/hide elapsed time label."""
        self.show_elapsed_time = state
        if self.time_label is not None:
            self.time_label.setVisible(state)

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

    def _show_loading_page(self):
        """Show animation while the kernel is loading."""
        self.shellwidget.hide()
        self.infowidget.show()
        self.infowidget.setHtml(self.loading_page,
                                QUrl.fromLocalFile(CSS_PATH))

    def _hide_loading_page(self):
        """Hide animation shown while the kernel is loading."""
        self.infowidget.hide()
        self.shellwidget.show()
        self.infowidget.setHtml(BLANK)
        self.shellwidget.sig_prompt_ready.disconnect(self._hide_loading_page)

    def _read_stderr(self):
        """Read the stderr file of the kernel."""
        stderr_text = open(self.stderr_file, 'rb').read()
        encoding = get_coding(stderr_text)
        stderr = to_text_string(stderr_text, encoding)
        return stderr

    def _show_mpl_backend_errors(self):
        """
        Show possible errors when setting the selected Matplotlib backend.
        """
        if not self.external_kernel:
            self.shellwidget.silent_execute(
                    "get_ipython().kernel._show_mpl_backend_errors()")
        self.shellwidget.sig_prompt_ready.disconnect(
            self._show_mpl_backend_errors)
