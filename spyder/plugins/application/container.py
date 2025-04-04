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
from qtpy.QtGui import QGuiApplication
from qtpy.QtWidgets import QAction, QMessageBox, QPushButton

# Local imports
from spyder import __docs_url__, __forum_url__, __trouble_url__
from spyder import dependencies
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.utils.installers import InstallerMissingDependencies
from spyder.config.base import get_conf_path, get_debug_level
from spyder.plugins.application.widgets import AboutDialog, InAppAppealStatus
from spyder.plugins.console.api import ConsoleActions
from spyder.utils.environ import UserEnvDialog
from spyder.utils.qthelpers import start_file, DialogManager
from spyder.widgets.dependencies import DependenciesDialog
from spyder.widgets.helperwidgets import MessageCheckBox


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
    SpyderSupportAction = "spyder_support_action"
    HelpSpyderAction = "help_spyder_action"
    SpyderAbout = "spyder_about_action"

    # Tools
    SpyderUserEnvVariables = "spyder_user_env_variables_action"

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
        self.dependencies_thread = QThread(None)
        self.dependencies_dialog = DependenciesDialog(self)

        # Attributes
        self.dialog_manager = DialogManager()
        self.inapp_appeal_status = InAppAppealStatus(self)

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
        self.support_group_action = self.create_action(
            ApplicationActions.SpyderSupportAction,
            _("Spyder support..."),
            triggered=lambda: start_file(__forum_url__))

        self.create_action(
            ApplicationActions.HelpSpyderAction,
            _("Help Spyder..."),
            icon=self.create_icon("inapp_appeal"),
            triggered=self.inapp_appeal_status.show_appeal
        )

        # About action
        self.about_action = self.create_action(
            ApplicationActions.SpyderAbout,
            _("About %s...") % "Spyder",
            icon=self.create_icon('MessageBoxInformation'),
            triggered=self.show_about,
            menurole=QAction.AboutRole)

        # Tools actions
        if os.name == 'nt':
            tip = _("Show and edit current user environment variables in "
                    "Windows registry (i.e. for all sessions)")
        else:
            tip = _("Show current user environment variables (i.e. for all "
                    "sessions)")
        self.user_env_action = self.create_action(
            ApplicationActions.SpyderUserEnvVariables,
            _("Current user environment variables..."),
            icon=self.create_icon('environment'),
            tip=tip,
            triggered=self.show_user_env_variables)

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
        if self.dependencies_thread is not None:
            self.dependencies_thread.quit()
            self.dependencies_thread.wait()

    @Slot()
    def show_about(self):
        """Show Spyder About dialog."""
        abt = AboutDialog(self)
        abt.show()

    @Slot()
    def show_user_env_variables(self):
        """Show Windows current user environment variables."""
        self.dialog_manager.show(UserEnvDialog(self))

    # ---- Dependencies
    # -------------------------------------------------------------------------
    def _set_dependencies(self):
        if dependencies.DEPENDENCIES:
            self.dependencies_dialog.set_data(dependencies.DEPENDENCIES)

    @Slot()
    def show_dependencies(self):
        """Show Spyder Dependencies dialog."""
        self.dependencies_dialog.show()

    def _compute_dependencies(self):
        """Compute dependencies without errors."""
        # Skip error when trying to register dependencies several times.
        # This can happen if the user tries to display the dependencies
        # dialog before dependencies_thread has finished.
        try:
            dependencies.declare_dependencies()
        except ValueError:
            pass

    def compute_dependencies(self):
        """Compute dependencies."""
        self.dependencies_thread.run = self._compute_dependencies
        self.dependencies_thread.finished.connect(
            self.report_missing_dependencies)
        self.dependencies_thread.finished.connect(self._set_dependencies)

        # This avoids computing missing deps before the window is fully up
        dependencies_timer = QTimer(self)
        dependencies_timer.setInterval(30000)
        dependencies_timer.setSingleShot(True)
        dependencies_timer.timeout.connect(self.dependencies_thread.start)
        dependencies_timer.start()

    @Slot()
    def report_missing_dependencies(self):
        """Show a QMessageBox with a list of missing hard dependencies."""
        missing_deps = dependencies.missing_dependencies()

        if missing_deps:
            InstallerMissingDependencies(missing_deps)

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
        self.menu_debug_logs.render()

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

            if self.get_conf('high_dpi_scaling'):
                return

            if self.dpi_messagebox is not None:
                self.dpi_messagebox.activateWindow()
                self.dpi_messagebox.raise_()
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

            # Show dialog always in the primary screen to prevent not being
            # able to see it if a screen gets disconnected while
            # in suspended state. See spyder-ide/spyder#16390
            dpi_messagebox_width = self.dpi_messagebox.rect().width()
            dpi_messagebox_height = self.dpi_messagebox.rect().height()
            screen_geometry = QGuiApplication.primaryScreen().geometry()
            x = (screen_geometry.width() - dpi_messagebox_width) / 2
            y = (screen_geometry.height() - dpi_messagebox_height) / 2

            # Convert coordinates to int to avoid a TypeError in Python 3.10
            # Fixes spyder-ide/spyder#17677
            self.dpi_messagebox.move(int(x), int(y))
            self.dpi_messagebox.adjustSize()
