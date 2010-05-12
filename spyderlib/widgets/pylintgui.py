# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Pylint widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from __future__ import with_statement

try:
    # PyQt4 4.3.3 on Windows (static DLLs) with py2exe installed:
    # -> pythoncom must be imported first, otherwise py2exe's boot_com_servers
    #    will raise an exception ("ImportError: DLL load failed [...]") when
    #    calling any of the QFileDialog static methods (getOpenFileName, ...)
    import pythoncom #@UnusedImport
except ImportError:
    pass

from PyQt4.QtGui import (QHBoxLayout, QWidget, QTreeWidgetItem, QMessageBox,
                         QVBoxLayout, QLabel, QFileDialog)
from PyQt4.QtCore import SIGNAL, QProcess, QByteArray, QString

import sys, os, time, cPickle
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import create_toolbutton, translate
from spyderlib.config import get_icon, get_conf_path
from spyderlib.widgets import OneColumnTree
from spyderlib.widgets.texteditor import TextEditor
from spyderlib.widgets.comboboxes import (PythonModulesComboBox,
                                          is_module_or_package)


PYLINT_PATH = programs.get_nt_program_name('pylint')

def is_pylint_installed():
    return programs.is_program_installed(PYLINT_PATH)

class ResultsTree(OneColumnTree):
    def __init__(self, parent):
        OneColumnTree.__init__(self, parent)
        self.filename = None
        self.results = None
        self.data = None
        self.set_title('')
        
    def activated(self):
        data = self.data.get(self.currentItem())
        if data is not None:
            fname, lineno = data
            self.parent().emit(SIGNAL("edit_goto(QString,int,QString)"),
                               fname, lineno, '')
        
    def set_results(self, filename, results):
        self.filename = filename
        self.results = results
        self.refresh()
        
    def refresh(self):
        title = translate('Pylint', 'Results for ')+self.filename
        self.set_title(title)
        self.clear()
        self.data = {}
        # Populating tree
        results = ((translate('Pylint', 'Convention'),
                    get_icon('convention.png'), self.results['C:']),
                   (translate('Pylint', 'Refactor'),
                    get_icon('refactor.png'), self.results['R:']),
                   (translate('Pylint', 'Warning'),
                    get_icon('warning.png'), self.results['W:']),
                   (translate('Pylint', 'Error'),
                    get_icon('error.png'), self.results['E:']))
        for title, icon, messages in results:
            title += ' (%d message%s)' % (len(messages),
                                          's' if len(messages)>1 else '')
            title_item = QTreeWidgetItem(self, [title])
            title_item.setIcon(0, icon)
            if not messages:
                title_item.setDisabled(True)
            modules = {}
            for module, lineno, message in messages:
                basename = osp.splitext(osp.basename(self.filename))[0]
                if not module.startswith(basename):
                    # Pylint bug
                    i_base = module.find(basename)
                    module = module[i_base:]
                dirname = osp.dirname(self.filename)
                if module.startswith('.'):
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
                        item = QTreeWidgetItem(title_item, [module])
                        item.setIcon(0, get_icon('py.png'))
                        modules[modname] = item
                        parent = item
                else:
                    parent = title_item
                msg_item = QTreeWidgetItem(parent,
                                           ["%d : %s" % (lineno, message)])
                msg_item.setIcon(0, get_icon('arrow.png'))
                self.data[msg_item] = (modname, lineno)


class PylintWidget(QWidget):
    """
    Pylint widget
    """
    DATAPATH = get_conf_path('.pylint.results')
    VERSION = '1.0.2'
    
    def __init__(self, parent, max_entries=100):
        QWidget.__init__(self, parent)
        
        self.setWindowTitle("Pylint")
        
        self.output = None
        self.error_output = None
        
        self.max_entries = max_entries
        self.data = [self.VERSION]
        if osp.isfile(self.DATAPATH):
            try:
                data = cPickle.load(file(self.DATAPATH))
                if data[0] == self.VERSION:
                    self.data = data
            except EOFError:
                pass

        self.filecombo = PythonModulesComboBox(self)
        if self.data:
            self.remove_obsolete_items()
            self.filecombo.addItems(self.get_filenames())
        
        self.start_button = create_toolbutton(self, get_icon('run.png'),
                                    translate('Pylint', "Analyze"),
                                    tip=translate('Pylint', "Run analysis"),
                                    triggered=self.start)
        self.stop_button = create_toolbutton(self, get_icon('terminate.png'),
                                    translate('Pylint', "Stop"),
                                    tip=translate('Pylint',
                                                  "Stop current analysis"))
        self.connect(self.filecombo, SIGNAL('valid(bool)'),
                     self.start_button.setEnabled)
        self.connect(self.filecombo, SIGNAL('valid(bool)'), self.show_data)

        browse_button = create_toolbutton(self, get_icon('fileopen.png'),
                               tip=translate('Pylint', 'Select Python script'),
                               triggered=self.select_file)

        self.ratelabel = QLabel()
        self.datelabel = QLabel()
        self.log_button = create_toolbutton(self, get_icon('log.png'),
                                    translate('Pylint', "Output"),
                                    tip=translate('Pylint',
                                                  "Complete Pylint output"),
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
        
        if not is_pylint_installed():
            for widget in (self.treewidget, self.filecombo,
                           self.start_button, self.stop_button):
                widget.setDisabled(True)
            if os.name == 'nt' \
               and programs.is_module_installed("pylint"):
                # Pylint is installed but pylint script is not in PATH
                # (AFAIK, could happen only on Windows)
                text = translate('Pylint',
                     'Pylint script was not found. Please add "%s" to PATH.')
                text = unicode(text) % osp.join(sys.prefix, "Scripts")
            else:
                text = translate('Pylint', 'Please install <b>pylint</b>:')
                url = 'http://www.logilab.fr'
                text += ' <a href=%s>%s</a>' % (url, url)
            self.ratelabel.setText(text)
        else:
            self.show_data()
        
    def analyze(self, filename):
        if not is_pylint_installed():
            return
        filename = unicode(filename) # filename is a QString instance
        self.kill_if_running()
        index, _data = self.get_data(filename)
        if index is None:
            self.filecombo.addItem(filename)
            self.filecombo.setCurrentIndex(self.filecombo.count()-1)
        else:
            self.filecombo.setCurrentIndex(index)
        self.filecombo.selected()
        if self.filecombo.is_valid():
            self.start()
            
    def select_file(self):
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getOpenFileName(self,
                      translate('Pylint', "Select Python script"), os.getcwdu(),
                      translate('Pylint', "Python scripts")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        if filename:
            self.analyze(filename)
            
    def remove_obsolete_items(self):
        """Removing obsolete items"""
        self.data = [self.VERSION] + \
                    [(filename, data) for filename, data in self.data[1:]
                     if is_module_or_package(filename)]
        
    def get_filenames(self):
        return [filename for filename, _data in self.data[1:]]
    
    def get_data(self, filename):
        filename = osp.abspath(filename)
        for index, (fname, data) in enumerate(self.data[1:]):
            if fname == filename:
                return index, data
        else:
            return None, None
            
    def set_data(self, filename, data):
        filename = osp.abspath(filename)
        index, _data = self.get_data(filename)
        if index is not None:
            self.data.pop(index+1)
        self.data.append( (filename, data) )
        self.save()
        
    def set_max_entries(self, max_entries):
        self.max_entries = max_entries
        self.save()
        
    def save(self):
        while len(self.data) > self.max_entries+1:
            self.data.pop(1)
        cPickle.dump(self.data, file(self.DATAPATH, 'w'))
        
    def show_log(self):
        if self.output:
            TextEditor(self.output, title=translate('Pylint', "Pylint output"),
                       readonly=True, size=(700, 500)).exec_()
        
    def start(self):
        filename = unicode(self.filecombo.currentText())
        
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
        p_args = [osp.basename(filename)]
        self.process.start(PYLINT_PATH, p_args)
        
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, translate('Pylint', "Error"),
                                 translate('Pylint', "Process failed to start"))
    
    def set_running_state(self, state=True):
        self.start_button.setEnabled(not state)
        self.stop_button.setEnabled(state)
        
    def read_output(self, error=False):
        if error:
            self.process.setReadChannel(QProcess.StandardError)
        else:
            self.process.setReadChannel(QProcess.StandardOutput)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            if error:
                bytes += self.process.readAllStandardError()
            else:
                bytes += self.process.readAllStandardOutput()
        text = unicode( QString.fromLocal8Bit(bytes.data()) )
        if error:
            self.error_output += text
        else:
            self.output += text
        
    def finished(self):
        self.set_running_state(False)
        if not self.output:
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
            for prefix in results:
                if line.startswith(prefix):
                    break
            else:
                continue
            i1 = line.find(':')
            if i1 == -1:
                continue
            i2 = line.find(':', i1+1)
            if i2 == -1:
                continue
            line_nb = line[i1+1:i2].strip()
            if not line_nb:
                continue
            line_nb = int(line_nb)
            message = line[i2+1:]
            item = (module, line_nb, message)
            results[line[:i1+1]].append(item)                
            
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
            
        
        filename = unicode(self.filecombo.currentText())
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
        filename = unicode(self.filecombo.currentText())
        if not filename:
            return
        
        _index, data = self.get_data(filename)
        if data is None:
            text = translate('Pylint', 'Source code has not been rated yet.')
            self.treewidget.clear()
            date_text = ''
        else:
            datetime, rate, previous_rate, results = data
            if rate is None:
                text = translate('Pylint', 'Analysis did not succeed '
                                           '(see output for more details).')
                self.treewidget.clear()
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
                text = translate('Pylint', 'Global evaluation:')
                text = (text_style % text)+(rate_style % (color,
                                                          ('%s/10' % rate)))
                if previous_rate:
                    text_prun = translate('Pylint', 'previous run:')
                    text_prun = ' (%s %s/10)' % (text_prun, previous_rate)
                    text += prevrate_style % text_prun
                self.treewidget.set_results(filename, results)
                date_text = text_style % time.strftime("%d %b %Y %H:%M",
                                                       datetime)
            
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
