# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pylint widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp
import pickle
import re
import sys
import time

# Third party imports
import pylint
from qtpy.compat import getopenfilename
from qtpy.QtCore import QByteArray, QProcess, Signal, Slot, QProcessEnvironment
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QTreeWidgetItem,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import get_conf_path, get_translation
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_toolbutton
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.comboboxes import (is_module_or_package,
                                       PythonModulesComboBox)
from spyder.widgets.onecolumntree import OneColumnTree
from spyder.plugins.pylint.utils import get_pylintrc_path
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor

# This is needed for testing this module as a stand alone script
try:
    _ = get_translation("pylint", "spyder_pylint")
except KeyError:
    import gettext
    _ = gettext.gettext


PYLINT_VER = pylint.__version__


# TODO: display results on 3 columns instead of 1: msg_id, lineno, message
class ResultsTree(OneColumnTree):
    sig_edit_goto = Signal(str, int, str)

    def __init__(self, parent):
        super().__init__(parent)
        self.filename = None
        self.results = None
        self.data = None
        self.set_title('')

    def activated(self, item):
        """Double-click event"""
        data = self.data.get(id(item))
        if data is not None:
            fname, lineno = data
            self.sig_edit_goto.emit(fname, lineno, '')

    def clicked(self, item):
        """Click event"""
        self.activated(item)

    def clear_results(self):
        self.clear()
        self.set_title('')

    def set_results(self, filename, results):
        self.filename = filename
        self.results = results
        self.refresh()

    def refresh(self):
        title = _('Results for ')+self.filename
        self.set_title(title)
        self.clear()
        self.data = {}
        # Populating tree
        results = ((_('Convention'),
                   ima.icon('convention'), self.results['C:']),
                   (_('Refactor'),
                   ima.icon('refactor'), self.results['R:']),
                   (_('Warning'),
                   ima.icon('warning'), self.results['W:']),
                   (_('Error'),
                   ima.icon('error'), self.results['E:']))
        for title, icon, messages in results:
            title += ' (%d message%s)' % (len(messages),
                                          's' if len(messages) > 1 else '')
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
                if module.startswith('.') or module == basename:
                    modname = osp.join(dirname, module)
                else:
                    modname = osp.join(dirname, *module.split('.'))
                if osp.isdir(modname):
                    modname = osp.join(modname, '__init__')
                for ext in ('.py', '.pyw'):
                    if osp.isfile(modname+ext):
                        modname = modname + ext
                        break
                if osp.isdir(self.filename):
                    parent = modules.get(modname)
                    if parent is None:
                        item = QTreeWidgetItem(title_item, [module],
                                               QTreeWidgetItem.Type)
                        item.setIcon(0, ima.icon('python'))
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
                msg_item.setIcon(0, ima.icon('arrow'))
                self.data[id(msg_item)] = (modname, lineno)


class PylintWidget(QWidget):
    """
    Pylint widget
    """
    DATAPATH = get_conf_path('pylint.results')
    VERSION = '1.1.0'
    redirect_stdio = Signal(bool)
    start_analysis = Signal()

    def __init__(self, parent, max_entries=100, options_button=None,
                 text_color=None, prevrate_color=None, top_max_entries=100):
        super().__init__(parent)

        self.setWindowTitle("Pylint")

        self.parent = parent
        self.output = None
        self.error_output = None
        self.filename = None
        self.text_color = text_color
        self.prevrate_color = prevrate_color
        self.max_entries = max_entries
        self.top_max_entries = top_max_entries
        self.rdata = []
        if osp.isfile(self.DATAPATH):
            try:
                data = pickle.loads(open(self.DATAPATH, 'rb').read())
                if data[0] == self.VERSION:
                    self.rdata = data[1:]
            except (EOFError, ImportError):
                pass

        self.filecombo = PythonModulesComboBox(self)
        self.filecombo.setInsertPolicy(self.filecombo.InsertAtTop)

        self.start_button = create_toolbutton(
            self,
            icon=ima.icon('run'),
            text=_("Analyze"),
            tip=_("Run analysis"),
            triggered=self.analyze_button_handler,
            text_beside_icon=True)
        self.stop_button = create_toolbutton(
            self,
            icon=ima.icon('stop'),
            text=_("Stop"),
            tip=_("Stop current analysis"),
            text_beside_icon=True)
        self.filecombo.valid.connect(self.start_button.setEnabled)
        self.filecombo.valid.connect(self.check_new_file)

        browse_button = create_toolbutton(
            self,
            icon=ima.icon('fileopen'),
            tip=_('Select Python file'),
            triggered=self.select_file)

        self.ratelabel = QLabel()
        self.datelabel = QLabel()
        self.log_button = create_toolbutton(
            self,
            icon=ima.icon('log'),
            text=_("Output"),
            text_beside_icon=True,
            tip=_("Complete output"),
            triggered=self.show_log)
        self.treewidget = ResultsTree(self)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.filecombo)
        hlayout1.addWidget(browse_button)
        hlayout1.addWidget(self.start_button)
        hlayout1.addWidget(self.stop_button)
        if options_button:
            hlayout1.addWidget(options_button)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.ratelabel)
        hlayout2.addStretch()
        hlayout2.addWidget(self.datelabel)
        hlayout2.addStretch()
        hlayout2.addWidget(self.log_button)

        layout = QVBoxLayout()
        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

        self.process = None
        self.set_running_state(False)
        self.show_data()

        if self.rdata:
            self.remove_obsolete_items()
            self.filecombo.insertItems(0, self.get_filenames())
            self.start_button.setEnabled(self.filecombo.is_valid())
        else:
            self.start_button.setEnabled(False)

        if self.parent:
            self.curr_filenames = self.parent.get_option(
                'history_filenames', [])
        else:
            self.curr_filenames = []

        for f in self.curr_filenames[::-1]:
            self.set_filename(f)

    def check_new_file(self):
        fname = self.get_filename()
        if fname != self.filename:
            self.filename = fname
            self.show_data()

    def get_filename(self):
        """Get current filename in combobox."""
        return self.filecombo.currentText()

    @Slot(str)
    def set_filename(self, filename):
        """Set filename without performing code analysis."""
        filename = str(filename)  # filename is a QString instance
        self.kill_if_running()
        index, _data = self.get_data(filename)
        is_parent = self.parent is not None

        if filename not in self.curr_filenames:
            self.filecombo.insertItem(0, filename)
            self.curr_filenames.insert(0, filename)
            self.filecombo.setCurrentIndex(0)
        else:
            index = self.filecombo.findText(filename)
            self.filecombo.removeItem(index)
            self.curr_filenames.pop(index)
            self.filecombo.insertItem(0, filename)
            self.curr_filenames.insert(0, filename)
            self.filecombo.setCurrentIndex(0)

        num_elements = self.filecombo.count()
        if is_parent:
            if num_elements > self.parent.get_option('max_entries'):
                self.filecombo.removeItem(num_elements - 1)
        self.filecombo.selected()

    def change_history_limit(self, new_limit):
        """Change the number of files listed in the history combobox."""
        if self.filecombo.count() > new_limit:
            num_elements = self.filecombo.count()
            diff = num_elements - new_limit
            for __ in range(diff):
                num_elements = self.filecombo.count()
                self.filecombo.removeItem(num_elements - 1)
            self.filecombo.selected()
        else:
            num_elements = self.filecombo.count()
            diff = new_limit - num_elements
            for i in range(num_elements, num_elements + diff):
                if i >= len(self.curr_filenames):
                    break
                act_filename = self.curr_filenames[i]
                self.filecombo.insertItem(i, act_filename)

    def save_history(self):
        """Save the current history filenames."""
        if self.parent:
            list_save_files = []
            for f in self.curr_filenames:
                if _('untitled') not in f:
                    list_save_files.append(f)
            self.curr_filenames = list_save_files[:self.top_max_entries]
            self.parent.set_option('history_filenames', self.curr_filenames)
        else:
            self.curr_filenames = []

    def analyze(self, filename=None):
        """
        Perform code analysis for given `filename`.

        If `filename` is None default to current filename in combobox.
        """
        if filename is not None:
            self.set_filename(filename)

        if self.filecombo.is_valid():
            self.start()

    @Slot()
    def select_file(self):
        self.redirect_stdio.emit(False)
        filename, _selfilter = getopenfilename(
                self, _("Select Python file"),
                getcwd_or_home(), _("Python files")+" (*.py ; *.pyw)")
        self.redirect_stdio.emit(True)
        if filename:
            self.analyze(filename)

    def remove_obsolete_items(self):
        """Removing obsolete items"""
        self.rdata = [(filename, data) for filename, data in self.rdata
                      if is_module_or_package(filename)]

    def get_filenames(self):
        return [filename for filename, _data in self.rdata]

    def get_data(self, filename):
        filename = osp.abspath(filename)
        for index, (fname, data) in enumerate(self.rdata):
            if fname == filename:
                return index, data
        else:
            return None, None

    def set_data(self, filename, data):
        filename = osp.abspath(filename)
        index, _data = self.get_data(filename)
        if index is not None:
            self.rdata.pop(index)
        self.rdata.insert(0, (filename, data))
        self.save()

    def save(self):
        while len(self.rdata) > self.max_entries:
            self.rdata.pop(-1)
        pickle.dump([self.VERSION]+self.rdata, open(self.DATAPATH, 'wb'), 2)

    @Slot()
    def show_log(self):
        if self.output:
            output_dialog = TextEditor(
                self.output,
                title=_("Pylint output"),
                parent=self,
                readonly=True
            )
            output_dialog.resize(700, 500)
            output_dialog.exec_()

    @Slot()
    def analyze_button_handler(self):
        """Try to start code analysis when Analyze button pressed."""
        self.start_analysis.emit()

    def get_pylintrc_path(self, filename):
        """Get the path to the most proximate pylintrc config to the file."""
        parent = self.parentWidget()
        if parent is not None:
            project_dir = parent.main.projects.get_active_project_path()
        else:
            project_dir = None
        search_paths = [
            osp.dirname(filename),  # File's directory
            getcwd_or_home(),  # Working directory
            project_dir,  # Project directory
            osp.expanduser("~"),  # Home directory
        ]
        return get_pylintrc_path(search_paths=search_paths)

    @Slot()
    def start(self):
        """Start the code analysis."""
        filename = str(self.filecombo.currentText())

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.setWorkingDirectory(getcwd_or_home())
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(
                                          lambda: self.read_output(error=True))
        self.process.finished.connect(lambda ec, es=QProcess.ExitStatus:
                                      self.finished(ec, es))
        self.stop_button.clicked.connect(self.process.kill)

        self.output = ''
        self.error_output = ''

        if PYLINT_VER is not None:
            pylint_args = [
                '-m', 'pylint', '--output-format=text',
                '--msg-template='
                "'{msg_id}:{symbol}:{line:3d},{column}: {msg}'"]

        pylintrc_path = self.get_pylintrc_path(filename=filename)
        if pylintrc_path is not None:
            pylint_args += ['--rcfile={}'.format(pylintrc_path)]

        pylint_args.append(filename)
        processEnvironment = QProcessEnvironment()
        processEnvironment.insert("PYTHONIOENCODING", "utf8")
        self.process.setProcessEnvironment(processEnvironment)

        self.process.start(sys.executable, pylint_args)

        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, _("Error"),
                                 _("Process failed to start"))

    def set_running_state(self, state=True):
        self.start_button.setEnabled(not state)
        self.stop_button.setEnabled(state)

    def read_output(self, error=False):
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
        text = str(qba.data(), 'utf-8')
        if error:
            self.error_output += text
        else:
            self.output += text

    def finished(self, exit_code, exit_status):
        self.set_running_state(False)
        if not self.output:
            if self.error_output:
                QMessageBox.critical(self, _("Error"), self.error_output)
                print("pylint error:\n\n" + self.error_output, file=sys.stderr)
            return

        # Convention, Refactor, Warning, Error
        results = {'C:': [], 'R:': [], 'W:': [], 'E:': []}
        txt_module = '************* Module '

        module = ''  # Should not be needed - just in case something goes wrong
        for line in self.output.splitlines():
            if line.startswith(txt_module):
                # New module
                module = line[len(txt_module):]
                continue
            # Supporting option include-ids: ('R3873:' instead of 'R:')
            if not re.match(r'^[CRWE]+([0-9]{4})?:', line):
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
                    item = int(item.split(',')[0])

                items[key_name] = item
                idx_0 = idx_1 + 1
            else:
                pylint_item = (module, items["line_nb"], items["message"],
                               items["msg_id"], items["message_name"])
                results[line[0] + ':'].append(pylint_item)

        # Rate
        rate = None
        txt_rate = 'Your code has been rated at '
        i_rate = self.output.find(txt_rate)
        if i_rate > 0:
            i_rate_end = self.output.find('/10', i_rate)
            if i_rate_end > 0:
                rate = self.output[i_rate+len(txt_rate):i_rate_end]

        # Previous run
        previous = ''
        if rate is not None:
            txt_prun = 'previous run: '
            i_prun = self.output.find(txt_prun, i_rate_end)
            if i_prun > 0:
                i_prun_end = self.output.find('/10', i_prun)
                previous = self.output[i_prun+len(txt_prun):i_prun_end]

        filename = str(self.filecombo.currentText())
        self.set_data(filename, (time.localtime(), rate, previous, results))
        self.output = self.error_output + self.output
        self.show_data(justanalyzed=True)

    def kill_if_running(self):
        if self.process is not None:
            if self.process.state() == QProcess.Running:
                self.process.kill()
                self.process.waitForFinished()

    def show_data(self, justanalyzed=False):
        if not justanalyzed:
            self.output = None
        self.log_button.setEnabled(self.output is not None
                                   and len(self.output) > 0)
        self.kill_if_running()
        filename = str(self.filecombo.currentText())
        if not filename:
            return

        _index, data = self.get_data(filename)
        if data is None:
            text = _('Source code has not been rated yet.')
            self.treewidget.clear_results()
            date_text = ''
        else:
            datetime, rate, previous_rate, results = data
            if rate is None:
                text = _('Analysis did not succeed '
                         '(see output for more details).')
                self.treewidget.clear_results()
                date_text = ''
            else:
                text_style = "<span style=\'color: %s\'><b>%s </b></span>"
                rate_style = "<span style=\'color: %s\'><b>%s</b></span>"
                prevrate_style = "<span style=\'color: %s\'>%s</span>"
                color = "#FF0000"
                if float(rate) > 5.:
                    color = "#22AA22"
                elif float(rate) > 3.:
                    color = "#EE5500"
                text = _('Global evaluation:')
                text = ((text_style % (self.text_color, text))
                        + (rate_style % (color, ('%s/10' % rate))))
                if previous_rate:
                    text_prun = _('previous run:')
                    text_prun = ' (%s %s/10)' % (text_prun, previous_rate)
                    text += prevrate_style % (self.prevrate_color, text_prun)
                self.treewidget.set_results(filename, results)
                date = time.strftime("%Y-%m-%d %H:%M:%S", datetime)
                date_text = text_style % (self.text_color, date)

        self.ratelabel.setText(text)
        self.datelabel.setText(date_text)


# =============================================================================
# Tests
# =============================================================================

def test():
    """Run pylint widget test"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=20)
    widget = PylintWidget(None)
    widget.resize(640, 480)
    widget.show()
    widget.analyze(__file__)
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
