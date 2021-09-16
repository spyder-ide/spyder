# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Container Widget.

Holds references for base actions in the Application of Spyder.
"""

# Standard library imports
import os
import sys
import glob

# Third party imports
from qtpy.QtCore import Qt, QThread, QTimer, Signal, Slot
from qtpy.QtWidgets import QAction, QMessageBox, QPushButton

# Local imports
from spyder import __docs_url__, __forum_url__, __trouble_url__
from spyder import dependencies
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.utils import is_anaconda
from spyder.config.base import get_conf_path, get_debug_level
from spyder.plugins.console.api import ConsoleActions
from spyder.utils.qthelpers import start_file, DialogManager
from spyder.widgets.about import AboutDialog
from spyder.widgets.dependencies import DependenciesDialog
from spyder.widgets.helperwidgets import MessageCheckBox
from spyder.workers.updates import WorkerUpdates


WinUserEnvDialog = None
if os.name == 'nt':
    from spyder.utils.environ import WinUserEnvDialog

# Localization
_ = get_translation('spyder')


class ApplicationPluginMenus:
    DebugLogsMenu = "debug_logs_menu"


class LogsMenuSections:
    SpyderLogSection = "spyder_log_section"
    LSPLogsSection = "lsp_logs_section"


# Actions
class ApplicationActions:
    # Help
    # The name of the action needs to match the name of the shortcut so
    # 'spyder documentation' is used instead of something
    # like 'spyder_documentation'
    SpyderDocumentationAction = "spyder documentation"
    SpyderDocumentationVideoAction = "spyder_documentation_video_action"
    SpyderTroubleshootingAction = "spyder_troubleshooting_action"
    SpyderDependenciesAction = "spyder_dependencies_action"
    SpyderCheckUpdatesAction = "spyder_check_updates_action"
    SpyderSupportAction = "spyder_support_action"
    SpyderAbout = "spyder_about_action"

    # Tools
    SpyderWindowsEnvVariables = "spyder_windows_env_variables_action"

    # File
    # The name of the action needs to match the name of the shortcut
    # so 'Restart' is used instead of something like 'restart_action'
    SpyderRestart = "Restart"
    SpyderRestartDebug = "Restart in debug mode"


class ApplicationContainer(PluginMainContainer):

    sig_report_issue_requested = Signal()
    """
    Signal to request reporting an issue to Github.
    """

    sig_load_log_file = Signal(str)
    """
    Signal to load a log file
    """

    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin, parent)

        # Keep track of dpi message
        self.current_dpi = None
        self.dpi_messagebox = None

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        # Compute dependencies in a thread to not block the interface.
        self.dependencies_thread = QThread()

        # Attributes
        self.dialog_manager = DialogManager()
        self.give_updates_feedback = False
        self.thread_updates = None
        self.worker_updates = None

        # Actions
        # Documentation actions
        self.documentation_action = self.create_action(
            ApplicationActions.SpyderDocumentationAction,
            text=_("Spyder documentation"),
            icon=self.create_icon("DialogHelpButton"),
            triggered=lambda: start_file(__docs_url__),
            context=Qt.ApplicationShortcut,
            register_shortcut=True,
            shortcut_context="_")

        spyder_video_url = ("https://www.youtube.com/playlist"
                            "?list=PLPonohdiDqg9epClEcXoAPUiK0pN5eRoc")
        self.video_action = self.create_action(
            ApplicationActions.SpyderDocumentationVideoAction,
            text=_("Tutorial videos"),
            icon=self.create_icon("VideoIcon"),
            triggered=lambda: start_file(spyder_video_url))

        # Support actions
        self.trouble_action = self.create_action(
            ApplicationActions.SpyderTroubleshootingAction,
            _("Troubleshooting..."),
            triggered=lambda: start_file(__trouble_url__))
        self.report_action = self.create_action(
            ConsoleActions.SpyderReportAction,
            _("Report issue..."),
            icon=self.create_icon('bug'),
            triggered=self.sig_report_issue_requested)
        self.dependencies_action = self.create_action(
            ApplicationActions.SpyderDependenciesAction,
            _("Dependencies..."),
            triggered=self.show_dependencies,
            icon=self.create_icon('advanced'))
        self.check_updates_action = self.create_action(
            ApplicationActions.SpyderCheckUpdatesAction,
            _("Check for updates..."),
            triggered=self.check_updates)
        self.support_group_action = self.create_action(
            ApplicationActions.SpyderSupportAction,
            _("Spyder support..."),
            triggered=lambda: start_file(__forum_url__))

        # About action
        self.about_action = self.create_action(
            ApplicationActions.SpyderAbout,
            _("About %s...") % "Spyder",
            icon=self.create_icon('MessageBoxInformation'),
            triggered=self.show_about,
            menurole=QAction.AboutRole)

        # Tools actions
        if WinUserEnvDialog is not None:
            self.winenv_action = self.create_action(
                ApplicationActions.SpyderWindowsEnvVariables,
                _("Current user environment variables..."),
                icon=self.create_icon('win_env'),
                tip=_("Show and edit current user environment "
                      "variables in Windows registry "
                      "(i.e. for all sessions)"),
                triggered=self.show_windows_env_variables)
        else:
            self.winenv_action = None

        # Application base actions
        self.restart_action = self.create_action(
            ApplicationActions.SpyderRestart,
            _("&Restart"),
            icon=self.create_icon('restart'),
            tip=_("Restart"),
            triggered=self.restart_normal,
            context=Qt.ApplicationShortcut,
            shortcut_context="_",
            register_shortcut=True)

        self.restart_debug_action = self.create_action(
            ApplicationActions.SpyderRestartDebug,
            _("&Restart in debug mode"),
            tip=_("Restart in debug mode"),
            triggered=self.restart_debug,
            context=Qt.ApplicationShortcut,
            shortcut_context="_",
            register_shortcut=True)

        # Debug logs
        if get_debug_level() >= 2:
            self.menu_debug_logs = self.create_menu(
                ApplicationPluginMenus.DebugLogsMenu,
                _("Debug logs")
            )

            # The menu can't be built at startup because Completions can
            # start after Application.
            self.menu_debug_logs.aboutToShow.connect(
                self.create_debug_log_actions)

    def update_actions(self):
        pass

    # ---- Other functionality
    # -------------------------------------------------------------------------
    def on_close(self):
        """To call from Spyder when the plugin is closed."""
        self.dialog_manager.close_all()

    @Slot()
    def show_about(self):
        """Show Spyder About dialog."""
        abt = AboutDialog(self)
        abt.show()

    @Slot()
    def show_windows_env_variables(self):
        """Show Windows current user environment variables."""
        self.dialog_manager.show(WinUserEnvDialog(self))

    # ---- Updates
    # -------------------------------------------------------------------------
    def _check_updates_ready(self):
        """Show results of the Spyder update checking process."""

        # `feedback` = False is used on startup, so only positive feedback is
        # given. `feedback` = True is used when after startup (when using the
        # menu action, and gives feeback if updates are, or are not found.
        feedback = self.give_updates_feedback

        # Get results from worker
        update_available = self.worker_updates.update_available
        latest_release = self.worker_updates.latest_release
        error_msg = self.worker_updates.error

        # Release url
        if sys.platform == 'darwin':
            url_r = ('https://github.com/spyder-ide/spyder/releases/latest/'
                     'download/Spyder.dmg')
        else:
            url_r = ('https://github.com/spyder-ide/spyder/releases/latest/'
                     'download/Spyder_64bit_full.exe')
        url_i = 'https://docs.spyder-ide.org/installation.html'

        # Define the custom QMessageBox
        box = MessageCheckBox(icon=QMessageBox.Information,
                              parent=self)
        box.setWindowTitle(_("New Spyder version"))
        box.setAttribute(Qt.WA_ShowWithoutActivating)
        box.set_checkbox_text(_("Check for updates at startup"))
        box.setStandardButtons(QMessageBox.Ok)
        box.setDefaultButton(QMessageBox.Ok)

        # Adjust the checkbox depending on the stored configuration
        option = 'check_updates_on_startup'
        check_updates = self.get_conf(option)
        box.set_checked(check_updates)

        if error_msg is not None:
            msg = error_msg
            box.setText(msg)
            box.set_check_visible(False)
            box.exec_()
            check_updates = box.is_checked()
        else:
            if update_available:
                header = _("<b>Spyder {} is available!</b><br><br>").format(
                    latest_release)
                footer = _(
                    "For more information visit our "
                    "<a href=\"{}\">installation guide</a>."
                ).format(url_i)
                if is_anaconda():
                    content = _(
                        "<b>Important note:</b> Since you installed "
                        "Spyder with Anaconda, please <b>don't</b> use "
                        "<code>pip</code> to update it as that will break "
                        "your installation.<br><br>"
                        "Instead, run the following commands in a "
                        "terminal:<br>"
                        "<code>conda update anaconda</code><br>"
                        "<code>conda install spyder={}</code><br><br>"
                    ).format(latest_release)
                else:
                    content = _(
                        "Click <a href=\"{}\">this link</a> to "
                        "download it.<br><br>"
                    ).format(url_r)
                msg = header + content + footer
                box.setText(msg)
                box.set_check_visible(True)
                box.show()
                check_updates = box.is_checked()
            elif feedback:
                msg = _("Spyder is up to date.")
                box.setText(msg)
                box.set_check_visible(False)
                box.exec_()
                check_updates = box.is_checked()

        # Update checkbox based on user interaction
        self.set_conf(option, check_updates)

        # Enable check_updates_action after the thread has finished
        self.check_updates_action.setDisabled(False)

        # Provide feeback when clicking menu if check on startup is on
        self.give_updates_feedback = True

    @Slot()
    def check_updates(self, startup=False):
        """Check for spyder updates on github releases using a QThread."""
        # Disable check_updates_action while the thread is working
        self.check_updates_action.setDisabled(True)

        if self.thread_updates is not None:
            self.thread_updates.terminate()

        self.thread_updates = QThread(self)
        self.worker_updates = WorkerUpdates(self, startup=startup)
        self.worker_updates.sig_ready.connect(self._check_updates_ready)
        self.worker_updates.sig_ready.connect(self.thread_updates.quit)
        self.worker_updates.moveToThread(self.thread_updates)
        self.thread_updates.started.connect(self.worker_updates.start)

        # Delay starting this check to avoid blocking the main window
        # while loading.
        # Fixes spyder-ide/spyder#15839
        updates_timer = QTimer(self)
        updates_timer.setInterval(3000)
        updates_timer.setSingleShot(True)
        updates_timer.timeout.connect(self.thread_updates.start)
        updates_timer.start()

    # ---- Dependencies
    # -------------------------------------------------------------------------
    @Slot()
    def show_dependencies(self):
        """Show Spyder Dependencies dialog."""
        dlg = DependenciesDialog(self)
        dlg.set_data(dependencies.DEPENDENCIES)
        dlg.show()

    def compute_dependencies(self):
        """Compute dependencies"""
        self.dependencies_thread.run = dependencies.declare_dependencies
        self.dependencies_thread.finished.connect(
            self.report_missing_dependencies)

        # This avoids computing missing deps before the window is fully up
        dependencies_timer = QTimer(self)
        dependencies_timer.setInterval(10000)
        dependencies_timer.setSingleShot(True)
        dependencies_timer.timeout.connect(self.dependencies_thread.start)
        dependencies_timer.start()

    @Slot()
    def report_missing_dependencies(self):
        """Show a QMessageBox with a list of missing hard dependencies."""
        missing_deps = dependencies.missing_dependencies()

        if missing_deps:
            # We change '<br>' by '\n', in order to replace the '<'
            # that appear in our deps by '&lt' (to not break html
            # formatting) and finally we restore '<br>' again.
            missing_deps = (missing_deps.replace('<br>', '\n').
                            replace('<', '&lt;').replace('\n', '<br>'))

            message = (
                _("<b>You have missing dependencies!</b>"
                  "<br><br><tt>%s</tt><br>"
                  "<b>Please install them to avoid this message.</b>"
                  "<br><br>"
                  "<i>Note</i>: Spyder could work without some of these "
                  "dependencies, however to have a smooth experience when "
                  "using Spyder we <i>strongly</i> recommend you to install "
                  "all the listed missing dependencies.<br><br>"
                  "Failing to install these dependencies might result in bugs."
                  " Please be sure that any found bugs are not the direct "
                  "result of missing dependencies, prior to reporting a new "
                  "issue."
                  ) % missing_deps
            )

            message_box = QMessageBox(self)
            message_box.setIcon(QMessageBox.Critical)
            message_box.setAttribute(Qt.WA_DeleteOnClose)
            message_box.setAttribute(Qt.WA_ShowWithoutActivating)
            message_box.setStandardButtons(QMessageBox.Ok)
            message_box.setWindowModality(Qt.NonModal)
            message_box.setWindowTitle(_('Error'))
            message_box.setText(message)
            message_box.show()

    # ---- Restart
    # -------------------------------------------------------------------------
    @Slot()
    def restart_normal(self):
        """Restart in standard mode."""
        os.environ['SPYDER_DEBUG'] = ''
        self.sig_restart_requested.emit()

    @Slot()
    def restart_debug(self):
        """Restart in debug mode."""
        box = QMessageBox(self)
        box.setWindowTitle(_("Question"))
        box.setIcon(QMessageBox.Question)
        box.setText(
            _("Which debug mode do you want Spyder to restart in?")
        )

        button_verbose = QPushButton(_('Verbose'))
        button_minimal = QPushButton(_('Minimal'))
        box.addButton(button_verbose, QMessageBox.AcceptRole)
        box.addButton(button_minimal, QMessageBox.AcceptRole)
        box.setStandardButtons(QMessageBox.Cancel)
        box.exec_()

        if box.clickedButton() == button_minimal:
            os.environ['SPYDER_DEBUG'] = '2'
        elif box.clickedButton() == button_verbose:
            os.environ['SPYDER_DEBUG'] = '3'
        else:
            return

        self.sig_restart_requested.emit()

    # ---- Log files
    # -------------------------------------------------------------------------
    def create_debug_log_actions(self):
        """Create an action for each lsp and debug log file."""
        self.menu_debug_logs.clear_actions()

        files = [os.environ['SPYDER_DEBUG_FILE']]
        files += glob.glob(os.path.join(get_conf_path('lsp_logs'), '*.log'))

        debug_logs_actions = []
        for file in files:
            action = self.create_action(
                file,
                os.path.basename(file),
                tip=file,
                triggered=lambda _, file=file: self.load_log_file(file),
                overwrite=True,
                register_action=False
            )
            debug_logs_actions.append(action)

        # Add Spyder log on its own section
        self.add_item_to_menu(
            debug_logs_actions[0],
            self.menu_debug_logs,
            section=LogsMenuSections.SpyderLogSection
        )

        # Add LSP logs
        for action in debug_logs_actions[1:]:
            self.add_item_to_menu(
                action,
                self.menu_debug_logs,
                section=LogsMenuSections.LSPLogsSection
            )

        # Render menu
        self.menu_debug_logs._render()

    def load_log_file(self, file):
        """Load log file in editor"""
        self.sig_load_log_file.emit(file)

    # ---- DPI changes
    # -------------------------------------------------------------------------
    def set_window(self, window):
        """Set window property of main window."""
        self._window = window

    def handle_new_screen(self, new_screen):
        """Connect DPI signals for new screen."""
        if new_screen is not None:
            new_screen_dpi = new_screen.logicalDotsPerInch()
            if self.current_dpi != new_screen_dpi:
                self.show_dpi_change_message(new_screen_dpi)
            else:
                new_screen.logicalDotsPerInchChanged.connect(
                    self.show_dpi_change_message)

    def handle_dpi_change_response(self, result, dpi):
        """Handle dpi change message dialog result."""
        if self.dpi_messagebox.is_checked():
            self.set_conf('show_dpi_message', False)

        self.dpi_messagebox = None

        if result == 0:  # Restart button was clicked
            # Activate HDPI auto-scaling option since is needed for a
            # proper display when using OS scaling
            self.set_conf('normal_screen_resolution', False)
            self.set_conf('high_dpi_scaling', True)
            self.set_conf('high_dpi_custom_scale_factor', False)
            self.sig_restart_requested.emit()
        else:
            # Update current dpi for future checks
            self.current_dpi = dpi

    def show_dpi_change_message(self, dpi):
        """Show message to restart Spyder since the DPI scale changed."""
        if not self.get_conf('show_dpi_message'):
            return

        if self.current_dpi != dpi:
            # Check the window state to not show the message if the window
            # is in fullscreen mode.
            window = self._window.windowHandle()
            if (window.windowState() == Qt.WindowFullScreen and
                    sys.platform == 'darwin'):
                return

            if self.dpi_messagebox is not None:
                return

            self.dpi_messagebox = MessageCheckBox(icon=QMessageBox.Warning,
                                                  parent=self)

            self.dpi_messagebox.set_checkbox_text(_("Don't show again."))
            self.dpi_messagebox.set_checked(False)
            self.dpi_messagebox.set_check_visible(True)

            self.dpi_messagebox.setText(
                _
                ("A monitor scale change was detected. <br><br>"
                 "We recommend restarting Spyder to ensure that it's properly "
                 "displayed. If you don't want to do that, please be sure to "
                 "activate the option<br><br><tt>Enable auto high DPI scaling"
                 "</tt><br><br>in <tt>Preferences > Application > "
                 "Interface</tt>, in case Spyder is not displayed "
                 "correctly.<br><br>"
                 "Do you want to restart Spyder?"))

            self.dpi_messagebox.addButton(_('Restart now'), QMessageBox.NoRole)
            dismiss_button = self.dpi_messagebox.addButton(
                _('Dismiss'), QMessageBox.NoRole)
            self.dpi_messagebox.setDefaultButton(dismiss_button)
            self.dpi_messagebox.finished.connect(
                lambda result: self.handle_dpi_change_response(result, dpi))
            self.dpi_messagebox.open()
