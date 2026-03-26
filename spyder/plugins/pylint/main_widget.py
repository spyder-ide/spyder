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
import logging
import os.path as osp
import sys
from dataclasses import dataclass

# Third party imports
from qtpy.QtCore import (
    QObject,
    QProcess,
    Qt,
    Signal,
)
from qtpy.QtWidgets import (
    QLabel,
    QTreeWidgetItem,
    QTreeWidget,
    QWidget,
)

# Local imports
from .linters import LinterMessage, LINTERS, LINTER_FOR_NAME
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor
from spyder.utils.icon_manager import ima


# --- Constants
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class PylintWidgetActions:
    RunCodeAnalysis = "run_analysis_action"
    ShowErrors = "errors_action"


class PylintWidgetMainToolbarSections:
    Main = "main_section"


class PylintWidgetToolbarItems:
    Label = "label"
    Stretcher = "stretcher"


# --- Helpers
# ----------------------------------------------------------------------------
@dataclass
class LinterProcess:
    process: QProcess
    stdout: str = ""
    stderr: str = ""


# ---- Widgets
# ----------------------------------------------------------------------------
class ResultsTree(QTreeWidget):
    LINE_ITEM_DATA_ROLE = Qt.ItemDataRole.UserRole

    sig_goto_requested = Signal(str, int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setColumnCount(4)
        self.setHeaderLabels(
            [
                _("Tool"),
                _("Line"),
                _("Rule"),
                _("Details"),
            ]
        )
        self.sortByColumn(1, Qt.SortOrder.AscendingOrder)

        self.itemClicked.connect(self.on_item_clicked)
        self.itemActivated.connect(self.on_item_activated)

        self.filename = ""

    def on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if item.childCount():
            item.setExpanded(not item.isExpanded())
        else:
            self.on_item_activated(item, column)

    def on_item_activated(self, item: QTreeWidgetItem, columnt: int) -> None:
        line = item.data(1, Qt.ItemDataRole.DisplayRole)
        if line is not None:
            self.sig_goto_requested.emit(self.filename, line, "")

    def add_top_level_item(
        self, source: str, failed: bool, count: int
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(self)

        # if not count:
        #     item.setDisabled(True)

        if count > 1 or count == 0:
            messages = _("messages")
        else:
            messages = _("message")
        fail_message = _(": Failed ") if failed else " "
        item.setText(0, f"{source}{fail_message}({count} {messages})")

        if failed:
            item.setIcon(0, ima.icon("error"))

        return item

    def clear_results(self, filename: str) -> None:
        self.filename = filename
        self.clear()

    def add_results(
        self,
        linter: str,
        failed: bool,
        messages: list[LinterMessage],
    ) -> None:
        top_level_item = self.add_top_level_item(linter, failed, len(messages))

        for msg in messages:
            item = QTreeWidgetItem(top_level_item)

            item.setData(1, Qt.ItemDataRole.DisplayRole, msg.line)

            if not msg.rule_id:
                item.setText(2, msg.rule_name)
            elif not msg.rule_name:
                item.setText(2, msg.rule_id)
            else:
                item.setText(2, f"{msg.rule_id} ({msg.rule_name})")

            item.setText(3, msg.message)


class PylintWidget(PluginMainWidget):
    """
    Pylint widget.
    """

    # PluginMainWidget API
    ENABLE_SPINNER = True
    SHOW_MESSAGE_WHEN_EMPTY = True
    IMAGE_WHEN_EMPTY = "code-analysis"
    MESSAGE_WHEN_EMPTY = _("Code not analyzed yet")
    DESCRIPTION_WHEN_EMPTY = _(
        "Run an analysis using configured tools to get feedback on style "
        "issues, bad practices, potential bugs, and suggested improvements "
        "in your code."
    )

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

    def __init__(self, name=None, plugin=None, parent=None) -> None:
        super().__init__(name, plugin, parent)

        # Attributes
        self.filename = ""
        self.project_dir = ""
        self.error_output = ""
        self.processes: dict[str, LinterProcess] = {}

        # Widgets
        self.toolbar_label = QLabel(self)
        self.toolbar_label.ID = PylintWidgetToolbarItems.Label

        self.results_widget = ResultsTree(self)
        self.set_content_widget(self.results_widget)

        # Signals
        self.results_widget.sig_goto_requested.connect(
            self.sig_edit_goto_requested
        )

    # --- Private API
    # ------------------------------------------------------------------------
    def _start(self) -> None:
        """Start the code analysis."""
        for linter in LINTERS:
            if not self.get_conf(f"use_{linter.name.lower()}", default=False):
                continue
            if not linter.is_available():
                continue

            process = QProcess(self)
            self.processes[linter.name] = LinterProcess(process)

            process.setProcessChannelMode(
                QProcess.ProcessChannelMode.SeparateChannels
            )
            process.setWorkingDirectory(linter.get_working_dir(self.filename))
            process.setProcessEnvironment(linter.get_environment())
            process.readyReadStandardOutput.connect(
                lambda linter_name=linter.name: self._read_output(linter_name)
            )
            process.readyReadStandardError.connect(
                lambda linter_name=linter.name: self._read_output(
                    linter_name, error=True
                )
            )
            process.finished.connect(
                lambda code, status, linter_name=linter.name: self._finished(
                    linter_name,
                    code,
                    status,
                )
            )
            process.errorOccurred.connect(
                lambda error, linter_name=linter.name: self._error_occured(
                    linter_name, error
                )
            )

            command = linter.get_command(self.filename, self.project_dir)
            process.start(command[0], command[1:])

    def _read_output(self, linter_name: str, error: bool = False) -> None:
        linter_process = self.processes[linter_name]

        if error:
            qbytes = linter_process.process.readAllStandardError()
        else:
            qbytes = linter_process.process.readAllStandardOutput()

        text = qbytes.data().decode("utf-8")
        if error:
            linter_process.stderr += text
        else:
            linter_process.stdout += text

    def _finished(
        self,
        linter_name: str,
        exit_code: int,
        exit_status: QProcess.ExitStatus,
    ) -> None:
        linter_process = self.processes.pop(linter_name)
        linter_process.process.deleteLater()

        linter = LINTER_FOR_NAME[linter_name]
        failed = (
            linter.exit_code_is_fatal(exit_code)
            or exit_status != QProcess.ExitStatus.NormalExit
        )

        if not failed:
            results = linter.parse_output(linter_process.stdout, self.filename)
        else:
            results = []
        self.results_widget.add_results(linter_name, failed, results)

        if failed or linter_process.stderr:
            self._add_error_section(linter_name)
            if exit_status == QProcess.ExitStatus.CrashExit:
                self.error_output += _("Crashed")
            if self.error_output:
                self.error_output += linter_process.stderr

        self.update_actions()

    def _error_occured(
        self, linter_name: str, error: QProcess.ProcessError
    ) -> None:
        linter_process = self.processes.pop(linter_name)
        linter_process.process.deleteLater()

        self.results_widget.add_results(linter_name, True, [])

        self._add_error_section(linter_name)
        if error == QProcess.ProcessError.FailedToStart:
            self.error_output += _(
                "Executable not found, "
                "insufficient permissions "
                "or failed to set working directory"
            )
        elif error == QProcess.ProcessError.Crashed:
            self.error_output += _("Crashed")
        else:  # Timedout, ReadError, WriteError, UnknownError
            self.error_output += _("Unknown error")

    def _is_running(self) -> bool:
        return any(
            (
                p.process.state() == QProcess.ProcessState.Running
                or p.process.state() == QProcess.ProcessState.Starting
            )
            for p in self.processes.values()
        )

    def _kill_all(self) -> None:
        while self.processes:
            _, linter_process = self.processes.popitem()
            QObject.disconnect(linter_process.process, None, None, None)
            linter_process.process.close()
            linter_process.process.waitForFinished(1000)
            linter_process.process.deleteLater()
        self.update_actions()

    def _reset(self, filename: str) -> None:
        self.filename = filename
        self.error_output = ""
        self.show_errors_action.setEnabled(False)
        self.results_widget.clear_results(filename)
        self.toolbar_label.setText(filename)
        self.update_actions()

    def _add_error_section(self, linter_name: str) -> None:
        if self.error_output:
            self.error_output += "\n" * (
                2 - self.error_output[-2:].count("\n")
            )
        self.error_output += f"{linter_name}\n{'=' * len(linter_name)}\n"

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _("Code Analysis")

    def get_focus_widget(self):
        return self.results_widget

    def setup(self):
        self.code_analysis_action = self.create_action(
            PylintWidgetActions.RunCodeAnalysis,
            text=_("Run code analysis"),
            tip=_("Run code analysis"),
            icon=self.create_icon("run"),
            triggered=self.sig_start_analysis_requested,
        )
        self.show_errors_action = self.create_action(
            PylintWidgetActions.ShowErrors,
            text=_("Errors"),
            tip=_("Show error output"),
            icon=self.create_icon("log"),
            triggered=self.show_error_output,
        )

        toolbar = self.get_main_toolbar()
        for item in [
            self.toolbar_label,
            self.create_stretcher(PylintWidgetToolbarItems.Stretcher),
            self.code_analysis_action,
            self.show_errors_action,
        ]:
            self.add_item_to_toolbar(
                item, toolbar, section=PylintWidgetMainToolbarSections.Main
            )

    def update_actions(self):
        if self._is_running():
            self.code_analysis_action.setIcon(self.create_icon("stop"))
            self.start_spinner()
        else:
            self.code_analysis_action.setIcon(self.create_icon("run"))
            self.stop_spinner()

        self.show_errors_action.setEnabled(len(self.error_output))

    def on_close(self):
        self.stop_code_analysis()

    # --- Public API
    # ------------------------------------------------------------------------
    def set_filename(self, filename: str) -> None:
        """
        Set current filename.

        If this method is called while still running it will stop the code
        analysis.
        """
        filename = osp.normpath(filename)  # Normalize path for Windows

        if self.filename == filename:
            return

        self.stop_code_analysis()
        self._reset(filename)

    def start_code_analysis(self) -> None:
        """
        Perform code analysis for currently set file.

        If this method is called while still running it will stop the code
        analysis.
        """
        if self._is_running():
            self.stop_code_analysis()
            return

        self.show_content_widget()
        self.start_spinner()
        self._reset(self.filename)
        self._start()
        self.update_actions()

    def stop_code_analysis(self) -> None:
        """
        Stop the code analysis process.
        """
        self._kill_all()

    def show_error_output(self) -> None:
        """
        Show output log dialog.
        """
        if self.error_output:
            output_dialog = TextEditor(
                self.error_output,
                title=_("Code Analysis errors"),
                parent=self,
                readonly=True,
            )
            output_dialog.resize(700, 500)
            output_dialog.exec_()


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run pylint widget test"""
    from spyder.utils.qthelpers import qapplication
    from unittest.mock import MagicMock

    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = "pylint"

    app = qapplication(test_time=20)
    widget = PylintWidget(name="pylint", plugin=plugin_mock)
    widget._setup()
    widget.setup()
    widget.resize(640, 480)
    widget.show()
    widget.set_filename(__file__)
    widget.start_code_analysis()
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()
