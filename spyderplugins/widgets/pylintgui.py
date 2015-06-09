# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Pylint widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement, print_function

from spyderlib.qt.QtGui import (QHBoxLayout, QWidget, QTreeWidgetItem,
                                QMessageBox, QVBoxLayout, QLabel)
from spyderlib.qt.QtCore import SIGNAL, QProcess, QByteArray, QTextCodec
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import getopenfilename

import sys
import os
import os.path as osp
import time
import re
import subprocess

# Local imports
from spyderlib import dependencies
from spyderlib.utils import programs
from spyderlib.utils.encoding import to_unicode_from_fs
from spyderlib.utils.qthelpers import get_icon, create_toolbutton
from spyderlib.baseconfig import get_conf_path, get_translation
from spyderlib.widgets.onecolumntree import OneColumnTree
from spyderlib.widgets.texteditor import TextEditor
from spyderlib.widgets.comboboxes import (PythonModulesComboBox,
                                          is_module_or_package)
from spyderlib.py3compat import PY3, to_text_string, getcwd, pickle
_ = get_translation("p_pylint", dirname="spyderplugins")


PYLINT = 'pylint'
if PY3:
    if programs.find_program('pylint3'):
        PYLINT = 'pylint3'
    elif programs.find_program('python3-pylint'):
        PYLINT = 'python3-pylint'

PYLINT_PATH = programs.find_program(PYLINT)


def get_pylint_version():
    """Return pylint version"""
    global PYLINT_PATH
    if PYLINT_PATH is None:
        return
    process = subprocess.Popen([PYLINT, '--version'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=osp.dirname(PYLINT_PATH),
                               shell=True if os.name == 'nt' else False)
    lines = to_unicode_from_fs(process.stdout.read()).splitlines()
    if lines:
        regex = '({0}*|pylint-script.py) ([0-9\.]*)'.format(PYLINT)
        match = re.match(regex, lines[0])
        if match is not None:
            return match.groups()[1]


PYLINT_REQVER = '>=0.25'
PYLINT_VER = get_pylint_version()
dependencies.add("pylint", _("Static code analysis"),
                 required_version=PYLINT_REQVER, installed_version=PYLINT_VER)


#TODO: display results on 3 columns instead of 1: msg_id, lineno, message
class ResultsTree(OneColumnTree):
    def __init__(self, parent):
        OneColumnTree.__init__(self, parent)
        self.filename = None
        self.results = None
        self.data = None
        self.set_title('')
        
    def activated(self, item):
        """Double-click event"""
        data = self.data.get(id(item))
        if data is not None:
            fname, lineno = data
            self.parent().emit(SIGNAL("edit_goto(QString,int,QString)"),
                               fname, lineno, '')

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
                    get_icon('convention.png'), self.results['C:']),
                   (_('Refactor'),
                    get_icon('refactor.png'), self.results['R:']),
                   (_('Warning'),
                    get_icon('warning.png'), self.results['W:']),
                   (_('Error'),
                    get_icon('error.png'), self.results['E:']))
        for title, icon, messages in results:
            title += ' (%d message%s)' % (len(messages),
                                          's' if len(messages)>1 else '')
            title_item = QTreeWidgetItem(self, [title], QTreeWidgetItem.Type)
            title_item.setIcon(0, icon)
            if not messages:
                title_item.setDisabled(True)
            modules = {}
            for module, lineno, message, msg_id in messages:
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
                        item.setIcon(0, get_icon('py.png'))
                        modules[modname] = item
                        parent = item
                else:
                    parent = title_item
                if len(msg_id) > 1:
                    text = "[%s] %d : %s" % (msg_id, lineno, message)
                else:
                    text = "%d : %s" % (lineno, message)
                msg_item = QTreeWidgetItem(parent, [text], QTreeWidgetItem.Type)
                msg_item.setIcon(0, get_icon('arrow.png'))
                self.data[id(msg_item)] = (modname, lineno)


class PylintWidget(QWidget):
    """
    Pylint widget
    """
    DATAPATH = get_conf_path('pylint.results')
    VERSION = '1.1.0'
    
    def __init__(self, parent, max_entries=100):
        QWidget.__init__(self, parent)
        
        self.setWindowTitle("Pylint")
        
        self.output = None
        self.error_output = None
        
        self.max_entries = max_entries
        self.rdata = []
        if osp.isfile(self.DATAPATH):
            try:
                data = pickle.loads(open(self.DATAPATH, 'rb').read())
                if data[0] == self.VERSION:
                    self.rdata = data[1:]
            except (EOFError, ImportError):
                pass

        self.filecombo = PythonModulesComboBox(self)
        if self.rdata:
            self.remove_obsolete_items()
            self.filecombo.addItems(self.get_filenames())
        
        self.start_button = create_toolbutton(self, icon=get_icon('run.png'),
                                    text=_("Analyze"),
                                    tip=_("Run analysis"),
                                    triggered=self.start, text_beside_icon=True)
        self.stop_button = create_toolbutton(self,
                                             icon=get_icon('stop.png'),
                                             text=_("Stop"),
                                             tip=_("Stop current analysis"),
                                             text_beside_icon=True)
        self.connect(self.filecombo, SIGNAL('valid(bool)'),
                     self.start_button.setEnabled)
        self.connect(self.filecombo, SIGNAL('valid(bool)'), self.show_data)

        browse_button = create_toolbutton(self, icon=get_icon('fileopen.png'),
                               tip=_('Select Python file'),
                               triggered=self.select_file)

        self.ratelabel = QLabel()
        self.datelabel = QLabel()
        self.log_button = create_toolbutton(self, icon=get_icon('log.png'),
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
        
        if PYLINT_PATH is None:
            for widget in (self.treewidget, self.filecombo,
                           self.start_button, self.stop_button):
                widget.setDisabled(True)
            if os.name == 'nt' \
               and programs.is_module_installed("pylint"):
                # Pylint is installed but pylint script is not in PATH
                # (AFAIK, could happen only on Windows)
                text = _('Pylint script was not found. Please add "%s" to PATH.')
                text = to_text_string(text) % osp.join(sys.prefix, "Scripts")
            else:
                text = _('Please install <b>pylint</b>:')
                url = 'http://www.logilab.fr'
                text += ' <a href=%s>%s</a>' % (url, url)
            self.ratelabel.setText(text)
        else:
            self.show_data()
        
    def analyze(self, filename):
        if PYLINT_PATH is None:
            return
        filename = to_text_string(filename) # filename is a QString instance
        self.kill_if_running()
        index, _data = self.get_data(filename)
        if index is None:
            self.filecombo.addItem(filename)
            self.filecombo.setCurrentIndex(self.filecombo.count()-1)
        else:
            self.filecombo.setCurrentIndex(self.filecombo.findText(filename))
        self.filecombo.selected()
        if self.filecombo.is_valid():
            self.start()
            
    def select_file(self):
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename, _selfilter = getopenfilename(self, _("Select Python file"),
                           getcwd(), _("Python files")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
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
        
    def show_log(self):
        if self.output:
            TextEditor(self.output, title=_("Pylint output"),
                       readonly=True, size=(700, 500)).exec_()
        
    def start(self):
        filename = to_text_string(self.filecombo.currentText())
        
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.setWorkingDirectory(osp.dirname(filename))
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.read_output)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     lambda: self.read_output(error=True))
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        self.connect(self.stop_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        self.output = ''
        self.error_output = ''
        
        plver = PYLINT_VER
        if plver is not None:
            if plver.split('.')[0] == '0':
                p_args = ['-i', 'yes']
            else:
                # Option '-i' (alias for '--include-ids') was removed in pylint
                # 1.0
                p_args = ["--msg-template='{msg_id}:{line:3d},"\
                          "{column}: {obj}: {msg}"]
            p_args += [osp.basename(filename)]
        else:
            p_args = [osp.basename(filename)]
        self.process.start(PYLINT_PATH, p_args)
        
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
        text = to_text_string( locale_codec.toUnicode(qba.data()) )
        if error:
            self.error_output += text
        else:
            self.output += text
        
    def finished(self):
        self.set_running_state(False)
        if not self.output:
            if self.error_output:
                QMessageBox.critical(self, _("Error"), self.error_output)
                print("pylint error:\n\n" + self.error_output, file=sys.stderr)
            return
        
        # Convention, Refactor, Warning, Error
        results = {'C:': [], 'R:': [], 'W:': [], 'E:': []}
        txt_module = '************* Module '
        
        module = '' # Should not be needed - just in case something goes wrong
        for line in self.output.splitlines():
            if line.startswith(txt_module):
                # New module
                module = line[len(txt_module):]
                continue
            # Supporting option include-ids: ('R3873:' instead of 'R:')
            if not re.match('^[CRWE]+([0-9]{4})?:', line):
                continue
            i1 = line.find(':')
            if i1 == -1:
                continue
            msg_id = line[:i1]
            i2 = line.find(':', i1+1)
            if i2 == -1:
                continue
            line_nb = line[i1+1:i2].strip()
            if not line_nb:
                continue
            line_nb = int(line_nb.split(',')[0])
            message = line[i2+1:]
            item = (module, line_nb, message, msg_id)
            results[line[0]+':'].append(item)
            
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
            
        
        filename = to_text_string(self.filecombo.currentText())
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
        self.log_button.setEnabled(self.output is not None \
                                   and len(self.output) > 0)
        self.kill_if_running()
        filename = to_text_string(self.filecombo.currentText())
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
                text_style = "<span style=\'color: #444444\'><b>%s </b></span>"
                rate_style = "<span style=\'color: %s\'><b>%s</b></span>"
                prevrate_style = "<span style=\'color: #666666\'>%s</span>"
                color = "#FF0000"
                if float(rate) > 5.:
                    color = "#22AA22"
                elif float(rate) > 3.:
                    color = "#EE5500"
                text = _('Global evaluation:')
                text = (text_style % text)+(rate_style % (color,
                                                          ('%s/10' % rate)))
                if previous_rate:
                    text_prun = _('previous run:')
                    text_prun = ' (%s %s/10)' % (text_prun, previous_rate)
                    text += prevrate_style % text_prun
                self.treewidget.set_results(filename, results)
                date = to_text_string(time.strftime("%d %b %Y %H:%M", datetime),
                                      encoding='utf8')
                date_text = text_style % date
            
        self.ratelabel.setText(text)
        self.datelabel.setText(date_text)


def test():
    """Run pylint widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = PylintWidget(None)
    widget.show()
    widget.analyze(__file__)
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    test()
