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

# Third party imports
from qtpy.QtCore import Qt, QThread, Slot
from qtpy.QtWidgets import QMessageBox, QAction

# Local imports
from spyder import (
    __docs_url__, __forum_url__, __project_url__, __trouble_url__)
from spyder import dependencies
from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.base import DEV
from spyder.config.utils import is_anaconda
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


class ApplicationContainer(PluginMainContainer):
    def setup(self):
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
            triggered=self.show_about)
        if sys.platform == 'darwin':
            self.about_action.setMenuRole(QAction.AboutRole)

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
            triggered=self.sig_restart_requested,
            context=Qt.ApplicationShortcut,
            shortcut_context="_",
            register_shortcut=True)

        # Initialize
        if DEV is None and self.get_conf('check_updates_on_startup'):
            self.give_updates_feedback = False
            self.check_updates(startup=True)

    def update_actions(self):
        pass

    def on_close(self):
        self.dialog_manager.close_all()

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
        url_r = __project_url__ + '/releases/tag/v{}'.format(latest_release)
        url_i = 'https://docs.spyder-ide.org/installation.html'

        # Define the custom QMessageBox
        box = MessageCheckBox(icon=QMessageBox.Information,
                              parent=self)
        box.setWindowTitle(_("New Spyder version"))
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
                        "Please go to <a href=\"{}\">this page</a> to "
                        "download it.<br><br>"
                    ).format(url_r)
                msg = header + content + footer
                box.setText(msg)
                box.set_check_visible(True)
                box.exec_()
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
        self.thread_updates.start()

    @Slot()
    def show_dependencies(self):
        """Show Spyder Dependencies dialog."""
        dlg = DependenciesDialog(self)
        dlg.set_data(dependencies.DEPENDENCIES)
        dlg.show()

    @Slot()
    def show_about(self):
        """Show Spyder About dialog."""
        abt = AboutDialog(self)
        abt.show()

    @Slot()
    def show_windows_env_variables(self):
        """Show Windows current user environment variables."""
        self.dialog_manager.show(WinUserEnvDialog(self))

    @Slot()
    def report_missing_dependencies(self):
        """Show a QMessageBox with a list of missing hard dependencies."""
        # Declare dependencies before trying to detect the missing ones
        dependencies.declare_dependencies()
        missing_deps = dependencies.missing_dependencies()

        if missing_deps:
            # We change '<br>' by '\n', in order to replace the '<'
            # that appear in our deps by '&lt' (to not break html
            # formatting) and finally we restore '<br>' again.
            missing_deps = (missing_deps.replace('<br>', '\n').
                            replace('<', '&lt;').replace('\n', '<br>'))

            QMessageBox.critical(
                self, _('Error'),
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
                  ) % missing_deps, QMessageBox.Ok)
