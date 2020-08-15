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
import os

# Third party imports
from qtpy.QtCore import QObject, QUrl, Signal, Slot
from qtpy.QtGui import QDesktopServices, QIcon

# Local imports
from spyder import __forum_url__, __trouble_url__
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.menus import ApplicationMenus, HelpMenuSections
from spyder.api.translations import get_translation
from spyder.app.utils import get_python_doc_path
from spyder.config.base import running_under_pytest
from spyder.plugins.console.widgets.main_widget import ConsoleWidget
from spyder.utils import programs

# Localization
_ = get_translation('spyder')

# Logging
logger = logging.getLogger(__name__)


class ConsoleActions:
    About = "about_action"
    CheckUpdates = "check_updates_action"
    OpenWebDocumentation = "open_web_documentation_action"
    # FIXME: normalize action names
    OpenLocalDocumentation = "spyder documentation"
    OpenGuide = "open_troubleshoorting_guide_action"
    OpenSpyderSupport = "open_spyder_support_action"
    ReportIssue = "report_issues_action"
    ShowDependencies = "show_dependencies_action"


class Console(SpyderDockablePlugin):
    """
    Console widget
    """
    NAME = 'internal_console'
    WIDGET_CLASS = ConsoleWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        'color_theme': ('appearance', 'selected'),
    }
    TABIFY = [Plugins.IPythonConsole, Plugins.History]

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
    def get_name(self):
        return _('Internal console')

    def get_icon(self):
        return QIcon()

    def get_description(self):
        return _('Internal console running Spyder.')

    def register(self):
        widget = self.get_widget()

        # Signals
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_focus_changed.connect(self.sig_focus_changed)
        widget.sig_quit_requested.connect(self.sig_quit_requested)
        widget.sig_refreshed.connect(self.sig_refreshed)
        widget.sig_help_requested.connect(self.sig_help_requested)

        # Crash handling
        previous_crash = self.get_conf_option(
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

        # Actions
        documentation_actions = []
        support_actions = []
        external_actions = []

        spyder_doc = 'https://docs.spyder-ide.org/'
        doc_action = self.create_action(
            ConsoleActions.OpenWebDocumentation,
            text=_("Spyder documentation"),
            icon=self.create_icon('DialogHelpButton'),
            triggered=lambda: programs.start_file(spyder_doc),
            register_shortcut=True,
            shortcut_context="_",
            context=Qt.ApplicationShortcut,
        )
        trouble_action = self.create_action(
            ConsoleActions.OpenGuide,
            text=_("Troubleshooting..."),
            triggered=self.open_guide,
        )
        dep_action = self.create_action(
            ConsoleActions.ShowDependencies,
            text=_("Dependencies..."),
            triggered=self.show_dependencies,
            icon=self.create_icon('advanced')
        )
        report_action = self.create_action(
            ConsoleActions.ReportIssue,
            text=_("Report issue..."),
            icon=self.create_icon('bug'),
            triggered=self.report_issue,
        )
        support_action = self.create_action(
            ConsoleActions.OpenSpyderSupport,
            text=_("Spyder support..."),
            triggered=self.open_google_group,
        )
        self.check_updates_action = self.create_action(
            ConsoleActions.CheckUpdates,
            text=_("Check for updates..."),
            triggered=self.check_updates,
        )
        about_action = self.create_action(
            ConsoleActions.About,
            _("About %s...") % "Spyder",
            icon=self.create_icon('MessageBoxInformation'),
            triggered=self.show_about,
        )
        documentation_actions += [about_action, doc_action]
        support_actions += [
            trouble_action,
            report_action,
            dep_action,
            self.check_updates_action,
            support_action,
        ]

        python_doc_path = get_python_doc_path()
        if python_doc_path is not None:
            pydoc_act = self.create_action(
                ConsoleActions.OpenLocalDocumentation,
                text=_("Python documentation"),
                triggered=lambda: programs.start_file(python_doc_path))

            documentation_action.append(pydoc_act)

        # FIXME: Move to help plugin.
        # if self.help is not None:
        #     tut_action = create_action(self, _("Spyder tutorial"),
        #                                triggered=self.help.show_tutorial)
        # else:
        #     tut_action = None

        # # FIXME:
        # # Windows-only: documentation located in sys.prefix/Doc
        # ipm_actions = []
        # def add_ipm_action(text, path):
        #     """Add installed Python module doc action to help submenu"""
        #     # QAction.triggered works differently for PySide and PyQt
        #     path = file_uri(path)
        #     if not API == 'pyside':
        #         slot=lambda _checked, path=path: programs.start_file(path)
        #     else:
        #         slot=lambda path=path: programs.start_file(path)
        #     action = create_action(self, text,
        #             icon='%s.png' % osp.splitext(path)[1][1:],
        #             triggered=slot)
        #     ipm_actions.append(action)
        # sysdocpth = osp.join(sys.prefix, 'Doc')
        # if osp.isdir(sysdocpth): # exists on Windows, except frozen dist.
        #     for docfn in os.listdir(sysdocpth):
        #         pt = r'([a-zA-Z\_]*)(doc)?(-dev)?(-ref)?(-user)?.(chm|pdf)'
        #         match = re.match(pt, docfn)
        #         if match is not None:
        #             pname = match.groups()[0]
        #             if pname not in ('Python', ):
        #                 add_ipm_action(pname, osp.join(sysdocpth, docfn))

        # # Installed Python modules submenu (Windows only)
        # if ipm_actions:
        #     pymods_menu = QMenu(_("Installed Python modules"), self)
        #     add_actions(pymods_menu, ipm_actions)
        #     self.help_menu_actions.append(pymods_menu)

        # Online documentation
        online_menu = self.QMenu(_("Online documentation"), self)
        # webres_actions = create_module_bookmark_actions(self,
        #                                                 self.BOOKMARKS)
        # webres_actions.insert(2, None)
        # webres_actions.insert(5, None)
        # webres_actions.insert(8, None)
        # add_actions(web_resources, webres_actions)
        # self.help_menu_actions.append(web_resources)

        # Qt assistant link
        if sys.platform.startswith('linux'):
            qta_exe = "assistant"

        # FIXME:
        qta_act = create_program_action(
            self,
            _("Qt documentation"),
            qta_exe,
        )

        if qta_act:
            external_actions += [qta_act]

        # Add actions to Help menu
        help_menu = self.get_application_menu(ApplicationMenus.Help)
        for item in documentation_actions:
            self.add_item_to_application_menu(
                item,
                menu=help_menu,
                section=HelpMenuSections.Documentation,
            )

        for item in support_actions:
            self.add_item_to_application_menu(
                item,
                menu=help_menu,
                section=HelpMenuSections.Support,
            )
    def update_font(self):
        font = self.get_font()
        self.get_widget().set_font(font)

    def on_close(self, cancelable=False):
        self.get_widget().dialog_manager.close_all()
        return True

    def on_mainwindow_visible(self):
        self.set_exit_function(self.main.closing)

        self.check_updates(startup=True)

        # Show dialog with missing dependencies
        if not running_under_pytest():
            self.report_missing_dependencies()

    # --- API
    # ------------------------------------------------------------------------
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
    def handle_exception(self, error_data):
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
        self.get_widget().handle_exception(
            error_data,
            sender=self.sender(),
            internal_plugins=self._main._INTERNAL_PLUGINS,
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
        widget.change_option('namespace', namespace)
        widget.start_interpreter(namespace)

    def set_namespace_item(self, name, value):
        """
        Add an object to the namespace dictionary of the internal console.
        """
        self.get_widget().set_namespace_item(name, value)

    @Slot()
    def show_about(self):
        """
        Show About Spyder dialog box.
        """
        self.get_widget().show_about()

    @Slot()
    def show_dependencies(self):
        """
        Show Spyder's Dependencies dialog box.
        """
        self.get_widget().show_dependencies()

    @Slot()
    def report_issue(self):
        """
        Report a general Spyder issue to Github.
        """
        self.get_widget().report_issue()

    @Slot()
    def open_guide(self):
        """
        Open Spyder troubleshooting guide in a web browser.
        """
        url = QUrl(__trouble_url__)
        QDesktopServices.openUrl(url)

    @Slot()
    def open_google_group(self):
        """
        Open Spyder Google Group in a web browser.
        """
        url = QUrl(__forum_url__)
        QDesktopServices.openUrl(url)

    @Slot()
    def check_updates(self, startup=False):
        """
        Check for spyder updates on github releases.
        """
        self.get_widget().check_updates(startup=startup)

    def report_missing_dependencies(self):
        """
        Show a QMessageBox with a list of missing hard dependencies.
        """
        self.get_widget().report_missing_dependencies()
