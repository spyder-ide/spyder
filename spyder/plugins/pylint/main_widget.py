# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pylint widget."""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os
import os.path as osp
import pickle
import re
import sys
import time

# Third party imports
import pylint
from qtpy.QtCore import (QByteArray, QProcess, QProcessEnvironment, Qt,
                         Signal, Slot)
from qtpy.QtWidgets import (QInputDialog, QLabel, QMessageBox,
                            QTreeWidgetItem, QVBoxLayout)
from qtpy.compat import getopenfilename

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainWidget
from spyder.config.base import get_conf_path, running_in_mac_app
from spyder.config.gui import is_dark_interface
from spyder.plugins.pylint.utils import get_pylintrc_path
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor
from spyder.utils import icon_manager as ima
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.comboboxes import (PythonModulesComboBox,
                                       is_module_or_package)
from spyder.widgets.onecolumntree import OneColumnTree, OneColumnTreeActions, \
    OneColumnTreeContextMenuSections

# Localization
_ = get_translation("spyder")

# --- Constants
# ----------------------------------------------------------------------------
PYLINT_VER = pylint.__version__
MIN_HISTORY_ENTRIES = 5
MAX_HISTORY_ENTRIES = 100
DANGER_COLOR = "#FF0000"
WARNING_COLOR = "#EE5500"
SUCCESS_COLOR = "#22AA22"

# TODO: There should be some palette from the appearance plugin so this
# is easier to use
if is_dark_interface():
    MAIN_TEXT_COLOR = "white"
    MAIN_PREVRATE_COLOR = "white"
else:
    MAIN_TEXT_COLOR = "#444444"
    MAIN_PREVRATE_COLOR = "#666666"


class PylintWidgetActions:
    ChangeHistory = "change_history_depth_action"
    RunCodeAnalysis = "run analysis"
    BrowseFile = "browse_action"
    ShowLog = "log_action"


class PylintWidgetOptionsMenuSections:
    Global = "global_section"
    Section = "section_section"
    History = "history_section"


class PylintWidgetMainToolBarSections:
    Main = "main_section"


# --- Widgets
# ----------------------------------------------------------------------------
# TODO: display results on 3 columns instead of 1: msg_id, lineno, message
class ResultsTree(OneColumnTree):
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

    sig_edit_ignore_rule = Signal(str, int, str)
    """
    This signal will be fired when the user request to ignore a pylint rule
    in a given file and row.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Line number in the file specified in "path".
    word: str
        Rule id to add in the ignore comment.
    """

    IgnoreRuleAction = "ignore_rule_action"

    def __init__(self, parent):
        super().__init__(parent)
        self.filename = None
        self.results = None
        self.data = None
        self.set_title("")
        self.__ignore_rule_action_connections = []
        self.__ignore_rule_action = self.create_action(
            self.IgnoreRuleAction,
            text=_("Ignore"),
            tip=_("Add a pylint ignore comment for this issue"),
            register_shortcut=False,
            triggered=(lambda: None)
        )
        self.add_item_to_menu(
            self.__ignore_rule_action,
            self.menu,
            section=OneColumnTreeContextMenuSections.Global,
        )

    def __clear_ignore_rule_action_connections(self):
        [self.__ignore_rule_action.triggered.disconnect(
            ignore_rule_action_connection) for ignore_rule_action_connection in
            self.__ignore_rule_action_connections]
        self.__ignore_rule_action_connections = []

    def __connect_item_to_ignore_rule_action(self, item):
        self.__clear_ignore_rule_action_connections()
        def action(): return self.ignore_lint_rule(item)
        self.__ignore_rule_action_connections.append(action)
        self.__ignore_rule_action.triggered.connect(action)

    def ignore_lint_rule(self, item):
        fname, lineno, ruleid = self.data.get(id(item))
        self.sig_edit_ignore_rule.emit(fname, lineno, ruleid)

    def activated(self, item):
        """Double-click event"""
        data = self.data.get(id(item))
        if data is not None:
            fname, lineno, _ = data
            self.sig_edit_goto_requested.emit(fname, lineno, "")

    def clicked(self, item):
        """Click event"""
        self.activated(item)

    def clear_results(self):
        self.clear()
        self.set_title("")

    def set_results(self, filename, results):
        self.filename = filename
        self.results = results
        self.refresh()

    def refresh(self):
        title = _("Results for ") + self.filename
        self.set_title(title)
        self.clear()
        self.data = {}

        # Populating tree
        results = (
            (_("Convention"), ima.icon("convention"), self.results["C:"]),
            (_("Refactor"), ima.icon("refactor"), self.results["R:"]),
            (_("Warning"), ima.icon("warning"), self.results["W:"]),
            (_("Error"), ima.icon("error"), self.results["E:"]),
        )
        for title, icon, messages in results:
            title += " (%d message%s)" % (len(messages),
                                          "s" if len(messages) > 1 else "")
            title_item = QTreeWidgetItem(self, [title], QTreeWidgetItem.Type)
            title_item.setIcon(0, icon)
            if not messages:
                title_item.setDisabled(True)

            modules = {}
            for message_data in messages:
                # If message data is legacy version without message_name
                if len(message_data) == 4:
                    message_data = tuple(list(message_data) + [None])

                module, lineno, message, msg_id, message_name = message_data

                basename = osp.splitext(osp.basename(self.filename))[0]
                if not module.startswith(basename):
                    # Pylint bug
                    i_base = module.find(basename)
                    module = module[i_base:]

                dirname = osp.dirname(self.filename)
                if module.startswith(".") or module == basename:
                    modname = osp.join(dirname, module)
                else:
                    modname = osp.join(dirname, *module.split("."))

                if osp.isdir(modname):
                    modname = osp.join(modname, "__init__")

                for ext in (".py", ".pyw"):
                    if osp.isfile(modname + ext):
                        modname = modname + ext
                        break

                if osp.isdir(self.filename):
                    parent = modules.get(modname)
                    if parent is None:
                        item = QTreeWidgetItem(title_item, [module],
                                               QTreeWidgetItem.Type)
                        item.setIcon(0, ima.icon("python"))
                        modules[modname] = item
                        parent = item
                else:
                    parent = title_item

                if len(msg_id) > 1:
                    if not message_name:
                        message_string = "{msg_id} "
                    else:
                        message_string = "{msg_id} ({message_name}) "

                message_string += "line {lineno}: {message}"
                message_string = message_string.format(
                    msg_id=msg_id, message_name=message_name,
                    lineno=lineno, message=message)
                msg_item = QTreeWidgetItem(
                    parent, [message_string], QTreeWidgetItem.Type)
                msg_item.setIcon(0, ima.icon("arrow"))
                self.data[id(msg_item)] = (modname, lineno, msg_id)

    def contextMenuEvent(self, event):
        current_item = self.currentItem()
        if id(current_item) in self.data:
            self.__ignore_rule_action.setVisible(True)
            self.__connect_item_to_ignore_rule_action(current_item)
        else:
            self.__ignore_rule_action.setVisible(False)
        return super(ResultsTree, self).contextMenuEvent(event)


class PylintWidget(PluginMainWidget):
    """
    Pylint widget.
    """
    DEFAULT_OPTIONS = {
        "history_filenames": [],
        "max_entries": 30,
        "project_dir": None,
    }
    ENABLE_SPINNER = True

    DATAPATH = get_conf_path("pylint.results")
    VERSION = "1.1.0"

    # --- Signals
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

    sig_start_analysis_requested = Signal()
    """
    This signal will request the plugin to start the analysis. This is to be
    able to interact with other plugins, which can only be done at the plugin
    level.
    """

    sig_edit_ignore_rule = Signal(str, int, str)
    """
    This signal will be fired when the user request to ignore a pylint rule
    in a given file and row.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Line number in the file specified in "path".
    word: str
        Rule id to add in the ignore comment.
    """

    def __init__(self, name=None, plugin=None, parent=None,
                 options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent, options)

        # Attributes
        self._process = None
        self.output = None
        self.error_output = None
        self.filename = None
        self.rdata = []
        self.curr_filenames = self.get_option("history_filenames")
        self.code_analysis_action = None
        self.browse_action = None

        # Widgets
        self.filecombo = PythonModulesComboBox(self)
        self.ratelabel = QLabel(self)
        self.datelabel = QLabel(self)
        self.treewidget = ResultsTree(self)

        if osp.isfile(self.DATAPATH):
            try:
                with open(self.DATAPATH, "rb") as fh:
                    data = pickle.loads(fh.read())

                if data[0] == self.VERSION:
                    self.rdata = data[1:]
            except (EOFError, ImportError):
                pass

        # Widget setup
        self.filecombo.setInsertPolicy(self.filecombo.InsertAtTop)
        for fname in self.curr_filenames[::-1]:
            self.set_filename(fname)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

        # Signals
        self.filecombo.valid.connect(self._check_new_file)
        self.treewidget.sig_edit_goto_requested.connect(
            self.sig_edit_goto_requested)

        self.treewidget.sig_edit_ignore_rule.connect(
            self.sig_edit_ignore_rule)

    # --- Private API
    # ------------------------------------------------------------------------
    @Slot()
    def _start(self):
        """Start the code analysis."""
        self.start_spinner()
        self.output = ""
        self.error_output = ""
        self._process = process = QProcess(self)

        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.setWorkingDirectory(getcwd_or_home())
        process.readyReadStandardOutput.connect(self._read_output)
        process.readyReadStandardError.connect(
            lambda: self._read_output(error=True))
        process.finished.connect(
            lambda ec, es=QProcess.ExitStatus: self._finished(ec, es))

        command_args = self.get_command(self.get_filename())
        processEnvironment = QProcessEnvironment()
        processEnvironment.insert("PYTHONIOENCODING", "utf8")

        # resolve spyder-ide/spyder#14262
        if running_in_mac_app():
            pyhome = os.environ.get("PYTHONHOME")
            processEnvironment.insert("PYTHONHOME", pyhome)

        process.setProcessEnvironment(processEnvironment)
        process.start(sys.executable, command_args)
        running = process.waitForStarted()
        if not running:
            self.stop_spinner()
            QMessageBox.critical(
                self,
                _("Error"),
                _("Process failed to start"),
            )

    def _read_output(self, error=False):
        process = self._process
        if error:
            process.setReadChannel(QProcess.StandardError)
        else:
            process.setReadChannel(QProcess.StandardOutput)

        qba = QByteArray()
        while process.bytesAvailable():
            if error:
                qba += process.readAllStandardError()
            else:
                qba += process.readAllStandardOutput()

        text = str(qba.data(), "utf-8")
        if error:
            self.error_output += text
        else:
            self.output += text

        self.update_actions()

    def _finished(self, exit_code, exit_status):
        if not self.output:
            self.stop_spinner()
            if self.error_output:
                QMessageBox.critical(
                    self,
                    _("Error"),
                    self.error_output,
                )
                print("pylint error:\n\n" + self.error_output, file=sys.stderr)
            return

        filename = self.get_filename()
        rate, previous, results = self.parse_output(self.output)
        self._save_history()
        self.set_data(filename, (time.localtime(), rate, previous, results))
        self.output = self.error_output + self.output
        self.show_data(justanalyzed=True)
        self.update_actions()
        self.stop_spinner()

    def _check_new_file(self):
        fname = self.get_filename()
        if fname != self.filename:
            self.filename = fname
            self.show_data()

    def _is_running(self):
        process = self._process
        return process is not None and process.state() == QProcess.Running

    def _kill_process(self):
        self._process.kill()
        self._process.waitForFinished()
        self.stop_spinner()

    def _update_combobox_history(self):
        """Change the number of files listed in the history combobox."""
        max_entries = self.get_option("max_entries")
        if self.filecombo.count() > max_entries:
            num_elements = self.filecombo.count()
            diff = num_elements - max_entries
            for __ in range(diff):
                num_elements = self.filecombo.count()
                self.filecombo.removeItem(num_elements - 1)
            self.filecombo.selected()
        else:
            num_elements = self.filecombo.count()
            diff = max_entries - num_elements
            for i in range(num_elements, num_elements + diff):
                if i >= len(self.curr_filenames):
                    break
                act_filename = self.curr_filenames[i]
                self.filecombo.insertItem(i, act_filename)

    def _save_history(self):
        """Save the current history filenames."""
        if self.parent:
            list_save_files = []
            for fname in self.curr_filenames:
                if _("untitled") not in fname:
                    filename = osp.normpath(fname)
                    list_save_files.append(fname)

            self.curr_filenames = list_save_files[:MAX_HISTORY_ENTRIES]
            self.set_option("history_filenames", self.curr_filenames)
        else:
            self.curr_filenames = []

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _("Code Analysis")

    def get_focus_widget(self):
        return self.treewidget

    def setup(self, options):
        change_history_depth_action = self.create_action(
            PylintWidgetActions.ChangeHistory,
            text=_("History..."),
            tip=_("Set history maximum entries"),
            icon=self.create_icon("history"),
            triggered=self.change_history_depth,
        )
        self.code_analysis_action = self.create_action(
            PylintWidgetActions.RunCodeAnalysis,
            icon_text=_("Analyze"),
            text=_("Run code analysis"),
            tip=_("Run code analysis"),
            icon=self.create_icon("run"),
            triggered=lambda: self.sig_start_analysis_requested.emit(),
            context=Qt.ApplicationShortcut,
            register_shortcut=True
        )
        self.browse_action = self.create_action(
            PylintWidgetActions.BrowseFile,
            text=_("Select Python file"),
            tip=_("Select Python file"),
            icon=self.create_icon("fileopen"),
            triggered=self.select_file,
        )
        self.log_action = self.create_action(
            PylintWidgetActions.ShowLog,
            text=_("Output"),
            icon_text=_("Output"),
            tip=_("Complete output"),
            icon=self.create_icon("log"),
            triggered=self.show_log,
        )

        options_menu = self.get_options_menu()
        self.add_item_to_menu(
            self.treewidget.get_action(
                OneColumnTreeActions.CollapseAllAction),
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Global,
        )
        self.add_item_to_menu(
            self.treewidget.get_action(
                OneColumnTreeActions.ExpandAllAction),
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Global,
        )
        self.add_item_to_menu(
            self.treewidget.get_action(
                OneColumnTreeActions.CollapseSelectionAction),
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Section,
        )
        self.add_item_to_menu(
            self.treewidget.get_action(
                OneColumnTreeActions.ExpandSelectionAction),
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Section,
        )
        self.add_item_to_menu(
            change_history_depth_action,
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.History,
        )

        # Update OneColumnTree contextual menu
        self.add_item_to_menu(
            change_history_depth_action,
            menu=self.treewidget.menu,
            section=PylintWidgetOptionsMenuSections.History,
        )
        self.treewidget.restore_action.setVisible(False)

        toolbar = self.get_main_toolbar()
        for item in [self.filecombo, self.browse_action,
                     self.code_analysis_action]:
            self.add_item_to_toolbar(
                item,
                toolbar,
                section=PylintWidgetMainToolBarSections.Main,
            )

        secondary_toolbar = self.create_toolbar("secondary")
        for item in [self.ratelabel, self.create_stretcher(), self.datelabel,
                     self.create_stretcher(), self.log_action]:
            self.add_item_to_toolbar(
                item,
                secondary_toolbar,
                section=PylintWidgetMainToolBarSections.Main,
            )

        self.show_data()

        if self.rdata:
            self.remove_obsolete_items()
            self.filecombo.insertItems(0, self.get_filenames())
            self.code_analysis_action.setEnabled(self.filecombo.is_valid())
        else:
            self.code_analysis_action.setEnabled(False)

        # Signals
        self.filecombo.valid.connect(self.code_analysis_action.setEnabled)

    def on_option_update(self, option, value):
        if option == "max_entries":
            self._update_combobox_history()
        elif option == "history_filenames":
            self.curr_filenames = value
            self._update_combobox_history()

    def update_actions(self):
        fm = self.ratelabel.fontMetrics()
        toolbar = self.get_main_toolbar()
        width = max([fm.width(_("Stop")), fm.width(_("Analyze"))])
        widget = toolbar.widgetForAction(self.code_analysis_action)
        if widget:
            widget.setMinimumWidth(width * 1.5)

        if self._is_running():
            self.code_analysis_action.setIconText(_("Stop"))
            self.code_analysis_action.setIcon(self.create_icon("stop"))
        else:
            self.code_analysis_action.setIconText(_("Analyze"))
            self.code_analysis_action.setIcon(self.create_icon("run"))

        self.remove_obsolete_items()

    # --- Public API
    # ------------------------------------------------------------------------
    @Slot()
    @Slot(int)
    def change_history_depth(self, value=None):
        """
        Set history maximum entries.

        Parameters
        ----------
        value: int or None, optional
            The valur to set  the maximum history depth. If no value is
            provided, an input dialog will be launched. Default is None.
        """
        if value is None:
            dialog = QInputDialog(self)

            # Set dialog properties
            dialog.setModal(False)
            dialog.setWindowTitle(_("History"))
            dialog.setLabelText(_("Maximum entries"))
            dialog.setInputMode(QInputDialog.IntInput)
            dialog.setIntRange(MIN_HISTORY_ENTRIES, MAX_HISTORY_ENTRIES)
            dialog.setIntStep(1)
            dialog.setIntValue(self.get_option("max_entries"))

            # Connect slot
            dialog.intValueSelected.connect(
                lambda value: self.set_option("max_entries", value))

            dialog.show()
        else:
            self.set_option("max_entries", value)

    def get_filename(self):
        """
        Get current filename in combobox.
        """
        return str(self.filecombo.currentText())

    @Slot(str)
    def set_filename(self, filename):
        """
        Set current filename in combobox.
        """
        if self._is_running():
            self._kill_process()

        filename = str(filename)
        filename = osp.normpath(filename)  # Normalize path for Windows

        # Don't try to reload saved analysis for filename, if filename
        # is the one currently displayed.
        # Fixes spyder-ide/spyder#13347
        if self.get_filename() == filename:
            return

        index, _data = self.get_data(filename)

        if filename not in self.curr_filenames:
            self.filecombo.insertItem(0, filename)
            self.curr_filenames.insert(0, filename)
            self.filecombo.setCurrentIndex(0)
        else:
            try:
                index = self.filecombo.findText(filename)
                self.filecombo.removeItem(index)
                self.curr_filenames.pop(index)
            except IndexError:
                self.curr_filenames.remove(filename)
            self.filecombo.insertItem(0, filename)
            self.curr_filenames.insert(0, filename)
            self.filecombo.setCurrentIndex(0)

        num_elements = self.filecombo.count()
        if num_elements > self.get_option("max_entries"):
            self.filecombo.removeItem(num_elements - 1)

        self.filecombo.selected()

    def start_code_analysis(self, filename=None):
        """
        Perform code analysis for given `filename`.

        If `filename` is None default to current filename in combobox.

        If this method is called while still running it will stop the code
        analysis.
        """
        if self._is_running():
            self._kill_process()
        else:
            if filename is not None:
                self.set_filename(filename)

            if self.filecombo.is_valid():
                self._start()

        self.update_actions()

    def stop_code_analysis(self):
        """
        Stop the code analysis process.
        """
        if self._is_running():
            self._kill_process()

    def remove_obsolete_items(self):
        """
        Removing obsolete items.
        """
        self.rdata = [(filename, data) for filename, data in self.rdata
                      if is_module_or_package(filename)]

    def get_filenames(self):
        """
        Return all filenames for which there is data available.
        """
        return [filename for filename, _data in self.rdata]

    def get_data(self, filename):
        """
        Get and load code analysis data for given `filename`.
        """
        filename = osp.abspath(filename)
        for index, (fname, data) in enumerate(self.rdata):
            if fname == filename:
                return index, data
        else:
            return None, None

    def set_data(self, filename, data):
        """
        Set and save code analysis `data` for given `filename`.
        """
        filename = osp.abspath(filename)
        index, _data = self.get_data(filename)
        if index is not None:
            self.rdata.pop(index)

        self.rdata.insert(0, (filename, data))

        while len(self.rdata) > self.get_option("max_entries"):
            self.rdata.pop(-1)

        with open(self.DATAPATH, "wb") as fh:
            pickle.dump([self.VERSION] + self.rdata, fh, 2)

    def show_data(self, justanalyzed=False):
        """
        Show data in treewidget.
        """
        text_color = MAIN_TEXT_COLOR
        prevrate_color = MAIN_PREVRATE_COLOR

        if not justanalyzed:
            self.output = None

        self.log_action.setEnabled(self.output is not None
                                   and len(self.output) > 0)

        if self._is_running():
            self._kill_process()

        filename = self.get_filename()
        if not filename:
            return

        _index, data = self.get_data(filename)
        if data is None:
            text = _("Source code has not been rated yet.")
            self.treewidget.clear_results()
            date_text = ""
        else:
            datetime, rate, previous_rate, results = data
            if rate is None:
                text = _("Analysis did not succeed "
                         "(see output for more details).")
                self.treewidget.clear_results()
                date_text = ""
            else:
                text_style = "<span style=\"color: %s\"><b>%s </b></span>"
                rate_style = "<span style=\"color: %s\"><b>%s</b></span>"
                prevrate_style = "<span style=\"color: %s\">%s</span>"
                color = DANGER_COLOR
                if float(rate) > 5.:
                    color = SUCCESS_COLOR
                elif float(rate) > 3.:
                    color = WARNING_COLOR

                text = _("Global evaluation:")
                text = ((text_style % (text_color, text))
                        + (rate_style % (color, ("%s/10" % rate))))
                if previous_rate:
                    text_prun = _("previous run:")
                    text_prun = " (%s %s/10)" % (text_prun, previous_rate)
                    text += prevrate_style % (prevrate_color, text_prun)

                self.treewidget.set_results(filename, results)
                date = time.strftime("%Y-%m-%d %H:%M:%S", datetime)
                date_text = text_style % (text_color, date)

        self.ratelabel.setText(text)
        self.datelabel.setText(date_text)

    @Slot()
    def show_log(self):
        """
        Show output log dialog.
        """
        if self.output:
            output_dialog = TextEditor(
                self.output,
                title=_("Code analysis output"),
                parent=self,
                readonly=True
            )
            output_dialog.resize(700, 500)
            output_dialog.exec_()

    # --- Python Specific
    # ------------------------------------------------------------------------
    def get_pylintrc_path(self, filename):
        """
        Get the path to the most proximate pylintrc config to the file.
        """
        search_paths = [
            # File"s directory
            osp.dirname(filename),
            # Working directory
            getcwd_or_home(),
            # Project directory
            self.get_option("project_dir"),
            # Home directory
            osp.expanduser("~"),
        ]

        return get_pylintrc_path(search_paths=search_paths)

    @Slot()
    def select_file(self, filename=None):
        """
        Select filename using a open file dialog and set as current filename.

        If `filename` is provided, the dialog is not used.
        """
        if filename is None:
            self.sig_redirect_stdio_requested.emit(False)
            filename, _selfilter = getopenfilename(
                self,
                _("Select Python file"),
                getcwd_or_home(),
                _("Python files") + " (*.py ; *.pyw)",
            )
            self.sig_redirect_stdio_requested.emit(True)

        if filename:
            self.set_filename(filename)
            self.start_code_analysis()

    def get_command(self, filename):
        """
        Return command to use to run code analysis on given filename
        """
        command_args = []
        if PYLINT_VER is not None:
            command_args = [
                "-m",
                "pylint",
                "--output-format=text",
                "--msg-template="
                '{msg_id}:{symbol}:{line:3d},{column}: {msg}"',
            ]

        pylintrc_path = self.get_pylintrc_path(filename=filename)
        if pylintrc_path is not None:
            command_args += ["--rcfile={}".format(pylintrc_path)]

        command_args.append(filename)
        return command_args

    def parse_output(self, output):
        """
        Parse output and return current revious rate and results.
        """
        # Convention, Refactor, Warning, Error
        results = {"C:": [], "R:": [], "W:": [], "E:": []}
        txt_module = "************* Module "

        module = ""  # Should not be needed - just in case something goes wrong
        for line in output.splitlines():
            if line.startswith(txt_module):
                # New module
                module = line[len(txt_module):]
                continue
            # Supporting option include-ids: ("R3873:" instead of "R:")
            if not re.match(r"^[CRWE]+([0-9]{4})?:", line):
                continue

            items = {}
            idx_0 = 0
            idx_1 = 0
            key_names = ["msg_id", "message_name", "line_nb", "message"]
            for key_idx, key_name in enumerate(key_names):
                if key_idx == len(key_names) - 1:
                    idx_1 = len(line)
                else:
                    idx_1 = line.find(":", idx_0)

                if idx_1 < 0:
                    break

                item = line[(idx_0):idx_1]
                if not item:
                    break

                if key_name == "line_nb":
                    item = int(item.split(",")[0])

                items[key_name] = item
                idx_0 = idx_1 + 1
            else:
                pylint_item = (module, items["line_nb"], items["message"],
                               items["msg_id"], items["message_name"])
                results[line[0] + ":"].append(pylint_item)

        # Rate
        rate = None
        txt_rate = "Your code has been rated at "
        i_rate = output.find(txt_rate)
        if i_rate > 0:
            i_rate_end = output.find("/10", i_rate)
            if i_rate_end > 0:
                rate = output[i_rate + len(txt_rate):i_rate_end]

        # Previous run
        previous = ""
        if rate is not None:
            txt_prun = "previous run: "
            i_prun = output.find(txt_prun, i_rate_end)
            if i_prun > 0:
                i_prun_end = output.find("/10", i_prun)
                previous = output[i_prun + len(txt_prun):i_prun_end]

        return rate, previous, results


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run pylint widget test"""
    from spyder.utils.qthelpers import qapplication

    app = qapplication(test_time=20)
    options = PylintWidget.DEFAULT_OPTIONS.copy()
    widget = PylintWidget(name="pylint", options=options)
    widget._setup(options)
    widget.setup(options)
    widget.resize(640, 480)
    widget.show()
    widget.start_code_analysis(filename=__file__)
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
