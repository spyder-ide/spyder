# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based on pylintgui.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler widget.

See the official documentation on python profiling:
https://docs.python.org/3/library/profile.html
"""

# Standard library imports
import logging
import os
import os.path as osp
import re
import sys
import time
from itertools import islice

# Third party imports
from qtpy.compat import getopenfilename, getsavefilename
from qtpy.QtCore import QByteArray, QProcess, QProcessEnvironment, Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QApplication, QLabel, QMessageBox, QTreeWidget,
                            QTreeWidgetItem, QVBoxLayout)

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import get_conf_path
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor
from spyder.py3compat import to_text_string
from spyder.utils.misc import add_pathlist_to_PYTHONPATH, getcwd_or_home
from spyder.utils.palette import SpyderPalette, QStylePalette
from spyder.utils.programs import shell_split
from spyder.utils.qthelpers import get_item_user_text, set_item_user_text
from spyder.widgets.comboboxes import PythonModulesComboBox

# Localization
_ = get_translation('spyder')

# Logging
logger = logging.getLogger(__name__)


# --- Constants
# ----------------------------------------------------------------------------
MAIN_TEXT_COLOR = QStylePalette.COLOR_TEXT_1

class ProfilerWidgetActions:
    # Triggers
    Browse = 'browse_action'
    Clear = 'clear_action'
    Collapse = 'collapse_action'
    Expand = 'expand_action'
    LoadData = 'load_data_action'
    Run = 'run_action'
    SaveData = 'save_data_action'
    ShowOutput = 'show_output_action'


class ProfilerWidgetToolbars:
    Information = 'information_toolbar'


class ProfilerWidgetMainToolbarSections:
    Main = 'main_section'


class ProfilerWidgetInformationToolbarSections:
    Main = 'main_section'


# --- Utils
# ----------------------------------------------------------------------------
def is_profiler_installed():
    from spyder.utils.programs import is_module_installed
    return is_module_installed('cProfile') and is_module_installed('pstats')


def gettime_s(text):
    """
    Parse text and return a time in seconds.

    The text is of the format 0h : 0.min:0.0s:0 ms:0us:0 ns.
    Spaces are not taken into account and any of the specifiers can be ignored.
    """
    pattern = r'([+-]?\d+\.?\d*) ?([mμnsinh]+)'
    matches = re.findall(pattern, text)
    if len(matches) == 0:
        return None
    time = 0.
    for res in matches:
        tmp = float(res[0])
        if res[1] == 'ns':
            tmp *= 1e-9
        elif res[1] == u'\u03BCs':
            tmp *= 1e-6
        elif res[1] == 'ms':
            tmp *= 1e-3
        elif res[1] == 'min':
            tmp *= 60
        elif res[1] == 'h':
            tmp *= 3600
        time += tmp
    return time


# --- Widgets
# ----------------------------------------------------------------------------
class ProfilerWidget(PluginMainWidget):
    """
    Profiler widget.
    """
    ENABLE_SPINNER = True
    DATAPATH = get_conf_path('profiler.results')

    # --- Signals
    # ------------------------------------------------------------------------
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

    sig_redirect_stdio_requested = Signal(bool)
    """
    This signal is emitted to request the main application to redirect
    standard output/error when using Open/Save/Browse dialogs within widgets.

    Parameters
    ----------
    redirect: bool
        Start redirect (True) or stop redirect (False).
    """

    sig_started = Signal()
    """This signal is emitted to inform the profiling process has started."""

    sig_finished = Signal()
    """This signal is emitted to inform the profile profiling has finished."""

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)
        self.set_conf('text_color', MAIN_TEXT_COLOR)

        # Attributes
        self._last_wdir = None
        self._last_args = None
        self._last_pythonpath = None
        self.error_output = None
        self.output = None
        self.running = False
        self.text_color = self.get_conf('text_color')

        # Widgets
        self.process = None
        self.filecombo = PythonModulesComboBox(self)
        self.datatree = ProfilerDataTree(self)
        self.datelabel = QLabel()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.datatree)
        self.setLayout(layout)

        # Signals
        self.datatree.sig_edit_goto_requested.connect(
            self.sig_edit_goto_requested)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Profiler')

    def get_focus_widget(self):
        return self.datatree

    def setup(self):
        self.start_action = self.create_action(
            ProfilerWidgetActions.Run,
            text=_("Run profiler"),
            tip=_("Run profiler"),
            icon=self.create_icon('run'),
            triggered=self.run,
        )
        browse_action = self.create_action(
            ProfilerWidgetActions.Browse,
            text='',
            tip=_('Select Python script'),
            icon=self.create_icon('fileopen'),
            triggered=lambda x: self.select_file(),
        )
        self.log_action = self.create_action(
            ProfilerWidgetActions.ShowOutput,
            text=_("Output"),
            tip=_("Show program's output"),
            icon=self.create_icon('log'),
            triggered=self.show_log,
        )
        self.collapse_action = self.create_action(
            ProfilerWidgetActions.Collapse,
            text=_('Collapse'),
            tip=_('Collapse one level up'),
            icon=self.create_icon('collapse'),
            triggered=lambda x=None: self.datatree.change_view(-1),
        )
        self.expand_action = self.create_action(
            ProfilerWidgetActions.Expand,
            text=_('Expand'),
            tip=_('Expand one level down'),
            icon=self.create_icon('expand'),
            triggered=lambda x=None: self.datatree.change_view(1),
        )
        self.save_action = self.create_action(
            ProfilerWidgetActions.SaveData,
            text=_("Save data"),
            tip=_('Save profiling data'),
            icon=self.create_icon('filesave'),
            triggered=self.save_data,
        )
        self.load_action = self.create_action(
            ProfilerWidgetActions.LoadData,
            text=_("Load data"),
            tip=_('Load profiling data for comparison'),
            icon=self.create_icon('fileimport'),
            triggered=self.compare,
        )
        self.clear_action = self.create_action(
            ProfilerWidgetActions.Clear,
            text=_("Clear comparison"),
            tip=_("Clear comparison"),
            icon=self.create_icon('editdelete'),
            triggered=self.clear,
        )
        self.clear_action.setEnabled(False)

        # Main Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.filecombo, browse_action, self.start_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=ProfilerWidgetMainToolbarSections.Main,
            )

        # Secondary Toolbar
        secondary_toolbar = self.create_toolbar(
            ProfilerWidgetToolbars.Information)
        for item in [self.collapse_action, self.expand_action,
                     self.create_stretcher(), self.datelabel,
                     self.create_stretcher(), self.log_action,
                     self.save_action, self.load_action, self.clear_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=secondary_toolbar,
                section=ProfilerWidgetInformationToolbarSections.Main,
            )

        # Setup
        if not is_profiler_installed():
            # This should happen only on certain GNU/Linux distributions
            # or when this a home-made Python build because the Python
            # profilers are included in the Python standard library
            for widget in (self.datatree, self.filecombo,
                           self.start_action):
                widget.setDisabled(True)
            url = 'https://docs.python.org/3/library/profile.html'
            text = '%s <a href=%s>%s</a>' % (_('Please install'), url,
                                             _("the Python profiler modules"))
            self.datelabel.setText(text)

    def update_actions(self):
        if self.running:
            icon = self.create_icon('stop')
        else:
            icon = self.create_icon('run')
        self.start_action.setIcon(icon)

        self.start_action.setEnabled(bool(self.filecombo.currentText()))

    # --- Private API
    # ------------------------------------------------------------------------
    def _kill_if_running(self):
        """Kill the profiling process if it is running."""
        if self.process is not None:
            if self.process.state() == QProcess.Running:
                self.process.kill()
                self.process.waitForFinished()

        self.update_actions()

    def _finished(self, exit_code, exit_status):
        """
        Parse results once the profiling process has ended.

        Parameters
        ----------
        exit_code: int
            QProcess exit code.
        exit_status: str
            QProcess exit status.
        """
        self.running = False
        self.show_errorlog()  # If errors occurred, show them.
        self.output = self.error_output + self.output
        self.datelabel.setText('')
        self.show_data(justanalyzed=True)
        self.update_actions()

    def _read_output(self, error=False):
        """
        Read otuput from QProcess.

        Parameters
        ----------
        error: bool, optional
            Process QProcess output or error channels. Default is False.
        """
        if error:
            self.process.setReadChannel(QProcess.StandardError)
        else:
            self.process.setReadChannel(QProcess.StandardOutput)

        qba = QByteArray()
        while self.process.bytesAvailable():
            if error:
                qba += self.process.readAllStandardError()
            else:
                qba += self.process.readAllStandardOutput()

        text = to_text_string(qba.data(), encoding='utf-8')
        if error:
            self.error_output += text
        else:
            self.output += text

    # --- Public API
    # ------------------------------------------------------------------------
    def save_data(self):
        """Save data."""
        title = _( "Save profiler result")
        filename, _selfilter = getsavefilename(
            self,
            title,
            getcwd_or_home(),
            _("Profiler result") + " (*.Result)",
        )

        if filename:
            self.datatree.save_data(filename)

    def compare(self):
        """Compare previous saved run with last run."""
        filename, _selfilter = getopenfilename(
            self,
            _("Select script to compare"),
            getcwd_or_home(),
            _("Profiler result") + " (*.Result)",
        )

        if filename:
            self.datatree.compare(filename)
            self.show_data()
            self.clear_action.setEnabled(True)

    def clear(self):
        """Clear data in tree."""
        self.datatree.compare(None)
        self.datatree.hide_diff_cols(True)
        self.show_data()
        self.clear_action.setEnabled(False)

    def analyze(self, filename, wdir=None, args=None, pythonpath=None):
        """
        Start the profiling process.

        Parameters
        ----------
        wdir: str
            Working directory path string. Default is None.
        args: list
            Arguments to pass to the profiling process. Default is None.
        pythonpath: str
            Python path string. Default is None.
        """
        if not is_profiler_installed():
            return

        self._kill_if_running()

        # TODO: storing data is not implemented yet
        # index, _data = self.get_data(filename)
        combo = self.filecombo
        items = [combo.itemText(idx) for idx in range(combo.count())]
        index = None
        if index is None and filename not in items:
            self.filecombo.addItem(filename)
            self.filecombo.setCurrentIndex(self.filecombo.count() - 1)
        else:
            self.filecombo.setCurrentIndex(self.filecombo.findText(filename))

        self.filecombo.selected()
        if self.filecombo.is_valid():
            if wdir is None:
                wdir = osp.dirname(filename)

            self.start(wdir, args, pythonpath)

    def select_file(self, filename=None):
        """
        Select filename to profile.

        Parameters
        ----------
        filename: str, optional
            Path to filename to profile. default is None.

        Notes
        -----
        If no `filename` is provided an open filename dialog will be used.
        """
        if filename is None:
            self.sig_redirect_stdio_requested.emit(False)
            filename, _selfilter = getopenfilename(
                self,
                _("Select Python script"),
                getcwd_or_home(),
                _("Python scripts") + " (*.py ; *.pyw)"
            )
            self.sig_redirect_stdio_requested.emit(True)

        if filename:
            self.analyze(filename)

    def show_log(self):
        """Show process output log."""
        if self.output:
            output_dialog = TextEditor(
                self.output,
                title=_("Profiler output"),
                readonly=True,
                parent=self,
            )
            output_dialog.resize(700, 500)
            output_dialog.exec_()

    def show_errorlog(self):
        """Show process error log."""
        if self.error_output:
            output_dialog = TextEditor(
                self.error_output,
                title=_("Profiler output"),
                readonly=True,
                parent=self,
            )
            output_dialog.resize(700, 500)
            output_dialog.exec_()

    def start(self, wdir=None, args=None, pythonpath=None):
        """
        Start the profiling process.

        Parameters
        ----------
        wdir: str
            Working directory path string. Default is None.
        args: list
            Arguments to pass to the profiling process. Default is None.
        pythonpath: str
            Python path string. Default is None.
        """
        filename = to_text_string(self.filecombo.currentText())
        if wdir is None:
            wdir = self._last_wdir
            if wdir is None:
                wdir = osp.basename(filename)

        if args is None:
            args = self._last_args
            if args is None:
                args = []

        if pythonpath is None:
            pythonpath = self._last_pythonpath

        self._last_wdir = wdir
        self._last_args = args
        self._last_pythonpath = pythonpath

        self.datelabel.setText(_('Profiling, please wait...'))

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.setWorkingDirectory(wdir)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(
            lambda: self._read_output(error=True))
        self.process.finished.connect(
            lambda ec, es=QProcess.ExitStatus: self._finished(ec, es))
        self.process.finished.connect(self.stop_spinner)

        if pythonpath is not None:
            env = [to_text_string(_pth)
                   for _pth in self.process.systemEnvironment()]
            add_pathlist_to_PYTHONPATH(env, pythonpath)
            processEnvironment = QProcessEnvironment()
            for envItem in env:
                envName, __, envValue = envItem.partition('=')
                processEnvironment.insert(envName, envValue)

            processEnvironment.insert("PYTHONIOENCODING", "utf8")
            self.process.setProcessEnvironment(processEnvironment)

        self.output = ''
        self.error_output = ''
        self.running = True
        self.start_spinner()

        p_args = ['-m', 'cProfile', '-o', self.DATAPATH]
        if os.name == 'nt':
            # On Windows, one has to replace backslashes by slashes to avoid
            # confusion with escape characters (otherwise, for example, '\t'
            # will be interpreted as a tabulation):
            p_args.append(osp.normpath(filename).replace(os.sep, '/'))
        else:
            p_args.append(filename)

        if args:
            p_args.extend(shell_split(args))

        executable = sys.executable
        if executable.endswith("spyder.exe"):
            # py2exe distribution
            executable = "python.exe"

        self.process.start(executable, p_args)
        running = self.process.waitForStarted()
        if not running:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Process failed to start"),
            )
        self.update_actions()

    def stop(self):
        """Stop the running process."""
        self.running = False
        self.process.kill()
        self.stop_spinner()
        self.update_actions()

    def run(self):
        """Toggle starting or running the profiling process."""
        if self.running:
            self.stop()
        else:
            self.start()

    def show_data(self, justanalyzed=False):
        """
        Show analyzed data on results tree.

        Parameters
        ----------
        justanalyzed: bool, optional
            Default is False.
        """
        if not justanalyzed:
            self.output = None

        self.log_action.setEnabled(self.output is not None
                                   and len(self.output) > 0)
        self._kill_if_running()
        filename = to_text_string(self.filecombo.currentText())
        if not filename:
            return

        self.datelabel.setText(_('Sorting data, please wait...'))
        QApplication.processEvents()

        self.datatree.load_data(self.DATAPATH)
        self.datatree.show_tree()

        text_style = "<span style=\'color: %s\'><b>%s </b></span>"
        date_text = text_style % (self.text_color,
                                  time.strftime("%Y-%m-%d %H:%M:%S",
                                                time.localtime()))
        self.datelabel.setText(date_text)


class TreeWidgetItem( QTreeWidgetItem ):
    def __init__(self, parent=None):
        QTreeWidgetItem.__init__(self, parent)

    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            if column == 1 or column == 3:  # TODO: Hardcoded Column
                t0 = gettime_s(self.text(column))
                t1 = gettime_s(otherItem.text(column))
                if t0 is not None and t1 is not None:
                    return t0 > t1

            return float( self.text(column) ) > float( otherItem.text(column) )
        except ValueError:
            return self.text(column) > otherItem.text(column)


class ProfilerDataTree(QTreeWidget, SpyderWidgetMixin):
    """
    Convenience tree widget (with built-in model)
    to store and view profiler data.

    The quantities calculated by the profiler are as follows
    (from profile.Profile):
    [0] = The number of times this function was called, not counting direct
          or indirect recursion,
    [1] = Number of times this function appears on the stack, minus one
    [2] = Total time spent internal to this function
    [3] = Cumulative time that this function was present on the stack.  In
          non-recursive functions, this is the total execution time from start
          to finish of each invocation of a function, including time spent in
          all subfunctions.
    [4] = A dictionary indicating for each function name, the number of times
          it was called by us.
    """
    SEP = r"<[=]>"  # separator between filename and linenumber
    # (must be improbable as a filename to avoid splitting the filename itself)

    # Signals
    sig_edit_goto_requested = Signal(str, int, str)

    def __init__(self, parent=None):
        super().__init__(parent, class_parent=parent)
        self.header_list = [_('Function/Module'), _('Total Time'), _('Diff'),
                            _('Local Time'), _('Diff'), _('Calls'), _('Diff'),
                            _('File:line')]
        self.icon_list = {
            'module': self.create_icon('python'),
            'function': self.create_icon('function'),
            'builtin': self.create_icon('python'),
            'constructor': self.create_icon('class')
        }
        self.profdata = None   # To be filled by self.load_data()
        self.stats = None      # To be filled by self.load_data()
        self.item_depth = None
        self.item_list = None
        self.items_to_be_shown = None
        self.current_view_depth = None
        self.compare_file = None
        self.setColumnCount(len(self.header_list))
        self.setHeaderLabels(self.header_list)
        self.initialize_view()
        self.itemActivated.connect(self.item_activated)
        self.itemExpanded.connect(self.item_expanded)

    def set_item_data(self, item, filename, line_number):
        """Set tree item user data: filename (string) and line_number (int)"""
        set_item_user_text(item, '%s%s%d' % (filename, self.SEP, line_number))

    def get_item_data(self, item):
        """Get tree item user data: (filename, line_number)"""
        filename, line_number_str = get_item_user_text(item).split(self.SEP)
        return filename, int(line_number_str)

    def initialize_view(self):
        """Clean the tree and view parameters"""
        self.clear()
        self.item_depth = 0   # To be use for collapsing/expanding one level
        self.item_list = []  # To be use for collapsing/expanding one level
        self.items_to_be_shown = {}
        self.current_view_depth = 0

    def load_data(self, profdatafile):
        """Load profiler data saved by profile/cProfile module"""
        import pstats
        # Fixes spyder-ide/spyder#6220.
        try:
            stats_indi = [pstats.Stats(profdatafile), ]
        except (OSError, IOError):
            self.profdata = None
            return
        self.profdata = stats_indi[0]

        if self.compare_file is not None:
            # Fixes spyder-ide/spyder#5587.
            try:
                stats_indi.append(pstats.Stats(self.compare_file))
            except (OSError, IOError) as e:
                QMessageBox.critical(
                    self, _("Error"),
                    _("Error when trying to load profiler results. "
                      "The error was<br><br>"
                      "<tt>{0}</tt>").format(e))
                self.compare_file = None
        map(lambda x: x.calc_callees(), stats_indi)
        self.profdata.calc_callees()
        self.stats1 = stats_indi
        self.stats = stats_indi[0].stats

    def compare(self,filename):
        self.hide_diff_cols(False)
        self.compare_file = filename

    def hide_diff_cols(self, hide):
        for i in (2,4,6):
            self.setColumnHidden(i, hide)

    def save_data(self, filename):
        """Save profiler data."""
        self.stats1[0].dump_stats(filename)

    def find_root(self):
        """Find a function without a caller"""
        # Fixes spyder-ide/spyder#8336.
        if self.profdata is not None:
            self.profdata.sort_stats("cumulative")
        else:
            return
        for func in self.profdata.fcn_list:
            if ('~', 0) != func[0:2] and not func[2].startswith(
                    '<built-in method exec>'):
                # This skips the profiler function at the top of the list
                # it does only occur in Python 3
                return func

    def find_callees(self, parent):
        """Find all functions called by (parent) function."""
        # FIXME: This implementation is very inneficient, because it
        #        traverses all the data to find children nodes (callees)
        return self.profdata.all_callees[parent]

    def show_tree(self):
        """Populate the tree with profiler data and display it."""
        self.initialize_view() # Clear before re-populating
        self.setItemsExpandable(True)
        self.setSortingEnabled(False)
        rootkey = self.find_root()  # This root contains profiler overhead
        if rootkey is not None:
            self.populate_tree(self, self.find_callees(rootkey))
            self.resizeColumnToContents(0)
            self.setSortingEnabled(True)
            self.sortItems(1, Qt.AscendingOrder) # FIXME: hardcoded index
            self.change_view(1)

    def function_info(self, functionKey):
        """Returns processed information about the function's name and file."""
        node_type = 'function'
        filename, line_number, function_name = functionKey
        if function_name == '<module>':
            modulePath, moduleName = osp.split(filename)
            node_type = 'module'
            if moduleName == '__init__.py':
                modulePath, moduleName = osp.split(modulePath)
            function_name = '<' + moduleName + '>'
        if not filename or filename == '~':
            file_and_line = '(built-in)'
            node_type = 'builtin'
        else:
            if function_name == '__init__':
                node_type = 'constructor'
            file_and_line = '%s : %d' % (filename, line_number)
        return filename, line_number, function_name, file_and_line, node_type

    @staticmethod
    def format_measure(measure):
        """Get format and units for data coming from profiler task."""
        # Convert to a positive value.
        measure = abs(measure)

        # For number of calls
        if isinstance(measure, int):
            return to_text_string(measure)

        # For time measurements
        if 1.e-9 < measure <= 1.e-6:
            measure = u"{0:.2f} ns".format(measure / 1.e-9)
        elif 1.e-6 < measure <= 1.e-3:
            measure = u"{0:.2f} \u03BCs".format(measure / 1.e-6)
        elif 1.e-3 < measure <= 1:
            measure = u"{0:.2f} ms".format(measure / 1.e-3)
        elif 1 < measure <= 60:
            measure = u"{0:.2f} s".format(measure)
        elif 60 < measure <= 3600:
            m, s = divmod(measure, 3600)
            if s > 60:
                m, s = divmod(measure, 60)
                s = to_text_string(s).split(".")[-1]
            measure = u"{0:.0f}.{1:.2s} min".format(m, s)
        else:
            h, m = divmod(measure, 3600)
            if m > 60:
                m /= 60
            measure = u"{0:.0f}h:{1:.0f}min".format(h, m)
        return measure

    def color_string(self, x):
        """Return a string formatted delta for the values in x.

        Args:
            x: 2-item list of integers (representing number of calls) or
               2-item list of floats (representing seconds of runtime).

        Returns:
            A list with [formatted x[0], [color, formatted delta]], where
            color reflects whether x[1] is lower, greater, or the same as
            x[0].
        """
        diff_str = ""
        color = "black"

        if len(x) == 2 and self.compare_file is not None:
            difference = x[0] - x[1]
            if difference:
                color, sign = ((SpyderPalette.COLOR_SUCCESS_1, '-')
                               if difference < 0
                               else (SpyderPalette.COLOR_ERROR_1, '+'))
                diff_str = '{}{}'.format(sign, self.format_measure(difference))
        return [self.format_measure(x[0]), [diff_str, color]]

    def format_output(self, child_key):
        """ Formats the data.

        self.stats1 contains a list of one or two pstat.Stats() instances, with
        the first being the current run and the second, the saved run, if it
        exists.  Each Stats instance is a dictionary mapping a function to
        5 data points - cumulative calls, number of calls, total time,
        cumulative time, and callers.

        format_output() converts the number of calls, total time, and
        cumulative time to a string format for the child_key parameter.
        """
        data = [x.stats.get(child_key, [0, 0, 0, 0, {}]) for x in self.stats1]
        return (map(self.color_string, islice(zip(*data), 1, 4)))

    def populate_tree(self, parentItem, children_list):
        """Recursive method to create each item (and associated data) in the tree."""
        for child_key in children_list:
            self.item_depth += 1
            (filename, line_number, function_name, file_and_line, node_type
             ) = self.function_info(child_key)

            ((total_calls, total_calls_dif), (loc_time, loc_time_dif), (cum_time,
             cum_time_dif)) = self.format_output(child_key)

            child_item = TreeWidgetItem(parentItem)
            self.item_list.append(child_item)
            self.set_item_data(child_item, filename, line_number)

            # FIXME: indexes to data should be defined by a dictionary on init
            child_item.setToolTip(0, _('Function or module name'))
            child_item.setData(0, Qt.DisplayRole, function_name)
            child_item.setIcon(0, self.icon_list[node_type])

            child_item.setToolTip(1, _('Time in function '\
                                       '(including sub-functions)'))
            child_item.setData(1, Qt.DisplayRole, cum_time)
            child_item.setTextAlignment(1, Qt.AlignRight)

            child_item.setData(2, Qt.DisplayRole, cum_time_dif[0])
            child_item.setForeground(2, QColor(cum_time_dif[1]))
            child_item.setTextAlignment(2, Qt.AlignLeft)

            child_item.setToolTip(3, _('Local time in function '\
                                      '(not in sub-functions)'))

            child_item.setData(3, Qt.DisplayRole, loc_time)
            child_item.setTextAlignment(3, Qt.AlignRight)

            child_item.setData(4, Qt.DisplayRole, loc_time_dif[0])
            child_item.setForeground(4, QColor(loc_time_dif[1]))
            child_item.setTextAlignment(4, Qt.AlignLeft)

            child_item.setToolTip(5, _('Total number of calls '\
                                       '(including recursion)'))

            child_item.setData(5, Qt.DisplayRole, total_calls)
            child_item.setTextAlignment(5, Qt.AlignRight)

            child_item.setData(6, Qt.DisplayRole, total_calls_dif[0])
            child_item.setForeground(6, QColor(total_calls_dif[1]))
            child_item.setTextAlignment(6, Qt.AlignLeft)

            child_item.setToolTip(7, _('File:line '\
                                       'where function is defined'))
            child_item.setData(7, Qt.DisplayRole, file_and_line)
            #child_item.setExpanded(True)
            if self.is_recursive(child_item):
                child_item.setData(7, Qt.DisplayRole, '(%s)' % _('recursion'))
                child_item.setDisabled(True)
            else:
                callees = self.find_callees(child_key)
                if self.item_depth < 3:
                    self.populate_tree(child_item, callees)
                elif callees:
                    child_item.setChildIndicatorPolicy(child_item.ShowIndicator)
                    self.items_to_be_shown[id(child_item)] = callees
            self.item_depth -= 1

    def item_activated(self, item):
        filename, line_number = self.get_item_data(item)
        self.sig_edit_goto_requested.emit(filename, line_number, '')

    def item_expanded(self, item):
        if item.childCount() == 0 and id(item) in self.items_to_be_shown:
            callees = self.items_to_be_shown[id(item)]
            self.populate_tree(item, callees)

    def is_recursive(self, child_item):
        """Returns True is a function is a descendant of itself."""
        ancestor = child_item.parent()
        # FIXME: indexes to data should be defined by a dictionary on init
        while ancestor:
            if (child_item.data(0, Qt.DisplayRole
                                ) == ancestor.data(0, Qt.DisplayRole) and
                child_item.data(7, Qt.DisplayRole
                                ) == ancestor.data(7, Qt.DisplayRole)):
                return True
            else:
                ancestor = ancestor.parent()
        return False

    def get_top_level_items(self):
        """Iterate over top level items"""
        return [self.topLevelItem(_i) for _i in range(self.topLevelItemCount())]

    def get_items(self, maxlevel):
        """Return all items with a level <= `maxlevel`"""
        itemlist = []
        def add_to_itemlist(item, maxlevel, level=1):
            level += 1
            for index in range(item.childCount()):
                citem = item.child(index)
                itemlist.append(citem)
                if level <= maxlevel:
                    add_to_itemlist(citem, maxlevel, level)
        for tlitem in self.get_top_level_items():
            itemlist.append(tlitem)
            if maxlevel > 0:
                add_to_itemlist(tlitem, maxlevel=maxlevel)
        return itemlist

    def change_view(self, change_in_depth):
        """Change the view depth by expand or collapsing all same-level nodes"""
        self.current_view_depth += change_in_depth
        if self.current_view_depth < 0:
            self.current_view_depth = 0
        self.collapseAll()
        if self.current_view_depth > 0:
            for item in self.get_items(maxlevel=self.current_view_depth-1):
                item.setExpanded(True)


# =============================================================================
# Tests
# =============================================================================
def primes(n):
    """
    Simple test function
    Taken from http://www.huyng.com/posts/python-performance-analysis/
    """
    if n==2:
        return [2]
    elif n<2:
        return []
    s=list(range(3,n+1,2))
    mroot = n ** 0.5
    half=(n+1)//2-1
    i=0
    m=3
    while m <= mroot:
        if s[i]:
            j=(m*m-3)//2
            s[j]=0
            while j<half:
                s[j]=0
                j+=m
        i=i+1
        m=2*i+3
    return [2]+[x for x in s if x]


def test():
    """Run widget test"""
    from spyder.utils.qthelpers import qapplication
    import inspect
    import tempfile
    from unittest.mock import MagicMock

    primes_sc = inspect.getsource(primes)
    fd, script = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as f:
        f.write("# -*- coding: utf-8 -*-" + "\n\n")
        f.write(primes_sc + "\n\n")
        f.write("primes(100000)")

    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'profiler'

    app = qapplication(test_time=5)
    widget = ProfilerWidget('test', plugin=plugin_mock)
    widget._setup()
    widget.setup()
    widget.resize(800, 600)
    widget.show()
    widget.analyze(script)
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
