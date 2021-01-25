# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Container Widget.

Holds references for base actions in the Main Menu of Spyder.
"""

# Third party imports
from qtpy.QtCore import QThread, Slot
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder import __project_url__
from spyder import dependencies
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainContainer
from spyder.config.base import DEV
from spyder.config.utils import is_anaconda
from spyder.widgets.about import AboutDialog
from spyder.widgets.dependencies import DependenciesDialog
from spyder.widgets.helperwidgets import MessageCheckBox
from spyder.workers.updates import WorkerUpdates


# Localization
_ = get_translation('spyder')


# Actions
class MainMenuActions:
    # Support
    SpyderDependenciesAction = "spyder_dependencies_action"
    SpyderCheckUpdatesAction = "spyder_check_updates_action"

    # About
    SpyderAbout = "spyder_about_action"


class MainMenuContainer(PluginMainContainer):

    DEFAULT_OPTIONS = {
        'check_updates_on_startup': True
    }

    def setup(self, options=DEFAULT_OPTIONS):
        # Attributes
        self.give_updates_feedback = False
        self.thread_updates = None
        self.worker_updates = None

        # Actions
        self.check_updates_action = self.create_action(
            MainMenuActions.SpyderCheckUpdatesAction,
            _("Check for updates..."),
            triggered=self.check_updates)
        self.dependencies_action = self.create_action(
            MainMenuActions.SpyderDependenciesAction,
            _("Dependencies..."),
            triggered=self.show_dependencies,
            icon=self.create_icon('advanced'))
        self.about_action = self.create_action(
            MainMenuActions.SpyderAbout,
            _("About %s...") % "Spyder",
            icon=self.create_icon('MessageBoxInformation'),
            triggered=self.show_about)

        # Initialize
        if DEV is None and options.get('main', 'check_updates_on_startup'):
            self.give_updates_feedback = False
            self.check_updates(startup=True)

    def on_option_update(self, option, value):
        pass

    def update_actions(self):
        pass

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
        check_updates = self.get_option(option)
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
        self.set_option(option, check_updates)

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
