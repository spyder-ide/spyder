# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Internal Console Plugin.
"""

# Standard library imports
import logging

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.config.base import DEV
from spyder.plugins.console.widgets.main_widget import (
    ConsoleWidget, ConsoleWidgetActions)
from spyder.plugins.mainmenu.api import ApplicationMenus, FileMenuSections


# Logging
logger = logging.getLogger(__name__)


class Console(SpyderDockablePlugin):
    """
    Console widget
    """
    NAME = 'internal_console'
    WIDGET_CLASS = ConsoleWidget
    OPTIONAL = [Plugins.MainMenu]
    CONF_SECTION = NAME
    CONF_FILE = False
    TABIFY = [Plugins.IPythonConsole, Plugins.History]
    CAN_BE_DISABLED = False
    RAISE_AND_FOCUS = True

    # --- Signals
    # ------------------------------------------------------------------------
    sig_focus_changed = Signal()  # TODO: I think this is not being used now?

    sig_edit_goto_requested = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    sig_refreshed = Signal()
    """This signal is emitted when the interpreter buffer is flushed."""

    sig_help_requested = Signal(dict)
    """
    This signal is emitted to request help on a given object `name`.

    Parameters
    ----------
    help_data: dict
        Example `{'name': str, 'ignore_unknown': bool}`.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Internal console')

    def get_icon(self):
        return QIcon()

    def get_description(self):
        return _('Internal console running Spyder.')

    def on_initialize(self):
        widget = self.get_widget()

        # Signals
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_focus_changed.connect(self.sig_focus_changed)
        widget.sig_refreshed.connect(self.sig_refreshed)
        widget.sig_help_requested.connect(self.sig_help_requested)

        # Crash handling
        previous_crash = self.get_conf(
            'previous_crash',
            default='',
            section='main',
        )

        if previous_crash:
            error_data = dict(
                text=previous_crash,
                is_traceback=True,
                title="Segmentation fault crash",
                label=_("<h3>Spyder crashed during last session</h3>"),
                steps=_("Please provide any additional information you "
                        "might have about the crash."),
            )
            widget.handle_exception(error_data)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        widget = self.get_widget()
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # Actions
        mainmenu.add_item_to_application_menu(
            widget.quit_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            ConsoleWidgetActions.Quit,
            menu_id=ApplicationMenus.File)

    def update_font(self):
        font = self.get_font()
        self.get_widget().set_font(font)

    def on_close(self, cancelable=False):
        self.get_widget().dialog_manager.close_all()
        return True

    def on_mainwindow_visible(self):
        self.set_exit_function(self.main.closing)

        # Hide this plugin when not in development so that people don't
        # use it instead of the IPython console
        if DEV is None:
            self.toggle_view_action.setChecked(False)
            self.dockwidget.hide()

    # --- API
    # ------------------------------------------------------------------------
    @Slot()
    def report_issue(self):
        """Report an issue with the SpyderErrorDialog."""
        self.get_widget().report_issue()

    @property
    def error_dialog(self):
        """
        Error dialog attribute accesor.
        """
        return self.get_widget().error_dlg

    def close_error_dialog(self):
        """
        Close the error dialog if visible.
        """
        self.get_widget().close_error_dlg()

    def exit_interpreter(self):
        """
        Exit the internal console interpreter.

        This is equivalent to requesting the main application to quit.
        """
        self.get_widget().exit_interpreter()

    def execute_lines(self, lines):
        """
        Execute the given `lines` of code in the internal console.
        """
        self.get_widget().execute_lines(lines)

    def get_sys_path(self):
        """
        Return the system path of the internal console.
        """
        return self.get_widget().get_sys_path()

    @Slot(dict)
    def handle_exception(self, error_data, sender=None):
        """
        Handle any exception that occurs during Spyder usage.

        Parameters
        ----------
        error_data: dict
            The dictionary containing error data. The expected keys are:
            >>> error_data= {
                "text": str,
                "is_traceback": bool,
                "repo": str,
                "title": str,
                "label": str,
                "steps": str,
            }

        Notes
        -----
        The `is_traceback` key indicates if `text` contains plain text or a
        Python error traceback.

        The `title` and `repo` keys indicate how the error data should
        customize the report dialog and Github error submission.

        The `label` and `steps` keys allow customizing the content of the
        error dialog.
        """
        if sender is None:
            sender = self.sender()
        self.get_widget().handle_exception(
            error_data,
            sender=sender
        )

    def quit(self):
        """
        Send the quit request to the main application.
        """
        self.sig_quit_requested.emit()

    def restore_stds(self):
        """
        Restore stdout and stderr when using open file dialogs.
        """
        self.get_widget().restore_stds()

    def redirect_stds(self):
        """
        Redirect stdout and stderr when using open file dialogs.
        """
        self.get_widget().redirect_stds()

    def set_exit_function(self, func):
        """
        Set the callback function to execute when the `exit_interpreter` is
        called.
        """
        self.get_widget().set_exit_function(func)

    def start_interpreter(self, namespace):
        """
        Start the internal console interpreter.

        Stdin and stdout are now redirected through the internal console.
        """
        widget = self.get_widget()
        widget.start_interpreter(namespace)

    def set_namespace_item(self, name, value):
        """
        Add an object to the namespace dictionary of the internal console.
        """
        self.get_widget().set_namespace_item(name, value)
