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
from spyder import __forum_url__, __trouble_url__, dependencies
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.console.widgets.main_widget import ConsoleWidget

# Localization
_ = get_translation('spyder')

# Logging
logger = logging.getLogger(__name__)


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

        # # Help menu
        # trouble_action = create_action(self,
        #                                 _("Troubleshooting..."),
        #                                 triggered=self.trouble_guide)
        # dep_action = create_action(self, _("Dependencies..."),
        #                             triggered=self.show_dependencies,
        #                             icon=ima.icon('advanced'))
        # report_action = create_action(self,
        #                                 _("Report issue..."),
        #                                 icon=ima.icon('bug'),
        #                                 triggered=self.report_issue)
        # support_action = create_action(self,
        #                                 _("Spyder support..."),
        #                                 triggered=self.google_group)
        # self.check_updates_action = create_action(self,
        #                                         _("Check for updates..."),
        #                                         triggered=self.check_updates)

        # self.help_menu_actions = [doc_action, tut_action, shortcuts_action,
        #                           self.tours_menu,
        #                           MENU_SEPARATOR, trouble_action,
        #                           report_action, dep_action,
        #                           self.check_updates_action, support_action,
        #                           MENU_SEPARATOR]
        # # Python documentation
        # if get_python_doc_path() is not None:
        #     pydoc_act = create_action(self, _("Python documentation"),
        #                         triggered=lambda:
        #                         programs.start_file(get_python_doc_path()))
        #     self.help_menu_actions.append(pydoc_act)



        # # Spyder documentation
        # spyder_doc = 'https://docs.spyder-ide.org/'
        # doc_action = create_action(self, _("Spyder documentation"),
        #                            icon=ima.icon('DialogHelpButton'),
        #                            triggered=lambda:
        #                            programs.start_file(spyder_doc))
        # self.register_shortcut(doc_action, "_",
        #                        "spyder documentation")

        # if self.help is not None:
        #     tut_action = create_action(self, _("Spyder tutorial"),
        #                                triggered=self.help.show_tutorial)
        # else:
        #     tut_action = None

        # shortcuts_action = create_action(self, _("Shortcuts Summary"),
        #                                  shortcut="Meta+F1",
        #                                  triggered=self.show_shortcuts_dialog)

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
        # # Online documentation
        # web_resources = QMenu(_("Online documentation"), self)
        # webres_actions = create_module_bookmark_actions(self,
        #                                                 self.BOOKMARKS)
        # webres_actions.insert(2, None)
        # webres_actions.insert(5, None)
        # webres_actions.insert(8, None)
        # add_actions(web_resources, webres_actions)
        # self.help_menu_actions.append(web_resources)
        # # Qt assistant link
        # if sys.platform.startswith('linux') and not PYQT5:
        #     qta_exe = "assistant-qt4"
        # else:
        #     qta_exe = "assistant"
        # qta_act = create_program_action(self, _("Qt documentation"),
        #                                 qta_exe)
        # if qta_act:
        #     self.help_menu_actions += [qta_act, None]

        # # About Spyder
        # about_action = create_action(self,
        #                         _("About %s...") % "Spyder",
        #                         icon=ima.icon('MessageBoxInformation'),
        #                         triggered=self.show_about)
        # self.help_menu_actions += [MENU_SEPARATOR, about_action]

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
    def trouble_guide(self):
        """
        Open Spyder troubleshooting guide in a web browser.
        """
        url = QUrl(__trouble_url__)
        QDesktopServices.openUrl(url)

    @Slot()
    def google_group(self):
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
