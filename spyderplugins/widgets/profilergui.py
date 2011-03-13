# -*- coding: utf-8 -*-
#
# Copyright © 2011 Santiago Jaramillo
# based on pylintgui.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Profiler widget

See the official documentation on python profiling:
http://docs.python.org/library/profile.html

Questions for Pierre and others:
    - Where in the menu should profiler go?  Run > Profile code ?
    - Is the shortcut F10 ok?
"""

from __future__ import with_statement

try:
    # PyQt4 4.3.3 on Windows (static DLLs) with py2exe installed:
    # -> pythoncom must be imported first, otherwise py2exe's boot_com_servers
    #    will raise an exception ("ImportError: DLL load failed [...]") when
    #    calling any of the QFileDialog static methods (getOpenFileName, ...)
    import pythoncom #@UnusedImport
except ImportError:
    pass

from PyQt4.QtGui import (QHBoxLayout, QWidget, QMessageBox,
                         QVBoxLayout, QLabel, QFileDialog,
                         QTreeWidget, QTreeWidgetItem)
from PyQt4.QtCore import SIGNAL, QProcess, QByteArray, QString, Qt

import sys, os, time

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import create_toolbutton, translate
from spyderlib.config import get_icon, get_conf_path
from spyderlib.widgets.texteditor import TextEditor
from spyderlib.widgets.comboboxes import (PythonModulesComboBox,
                                          is_module_or_package)
from spyderlib.config import get_font


# FIXME: is this the right way to check for modules?
#PROFILER_PATH = 'profile'
PROFILER_PATH = 'cProfile'
PSTATS_PATH = 'pstats'

def is_profiler_installed():
    return (programs.is_module_installed(PROFILER_PATH) and
            programs.is_module_installed(PSTATS_PATH))


class ProfilerWidget(QWidget):
    """
    Profiler widget
    """
    DATAPATH = get_conf_path('.profiler.results')
    VERSION = '0.0.1'
    
    def __init__(self, parent, max_entries=100):
        QWidget.__init__(self, parent)
        
        self.setWindowTitle("Profiler")
        
        self.output = None
        self.error_output = None
        
        self.filecombo = PythonModulesComboBox(self)
        
        self.start_button = create_toolbutton(self, icon=get_icon('run.png'),
                                    text=translate('Profiler', "Profile"),
                                    tip=translate('Profiler', "Run profiler"),
                                    triggered=self.start, text_beside_icon=True)
        self.stop_button = create_toolbutton(self,
                                    icon=get_icon('terminate.png'),
                                    text=translate('Profiler', "Stop"),
                                    tip=translate('Profiler',
                                                  "Stop current profiling"),
                                    text_beside_icon=True)
        self.connect(self.filecombo, SIGNAL('valid(bool)'),
                     self.start_button.setEnabled)
        #self.connect(self.filecombo, SIGNAL('valid(bool)'), self.show_data)
        # FIXME: The combobox emits this signal on almost any event
        #        triggering show_data() too early, too often. 

        browse_button = create_toolbutton(self, icon=get_icon('fileopen.png'),
                               tip=translate('Profiler', 'Select Python script'),
                               triggered=self.select_file)

        self.datelabel = QLabel()

        self.log_button = create_toolbutton(self, icon=get_icon('log.png'),
                                    text=translate('Profiler', "Output"),
                                    text_beside_icon=True,
                                    tip=translate('Profiler',
                                                  "Show program's output"),
                                    triggered=self.show_log)

        self.datatree = ProfilerDataTree(self)

        self.collapse_button = create_toolbutton(self, icon=get_icon('collapse.png'),
                                    triggered=lambda dD=-1:self.datatree.change_view(dD),
                                    tip='Collapse one level up')
        self.expand_button = create_toolbutton(self, icon=get_icon('expand.png'),
                                    triggered=lambda dD=1:self.datatree.change_view(dD),
                                    tip='Expand one level down')

        
        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.filecombo)
        hlayout1.addWidget(browse_button)
        hlayout1.addWidget(self.start_button)
        hlayout1.addWidget(self.stop_button)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.collapse_button)
        hlayout2.addWidget(self.expand_button)
        hlayout2.addStretch()
        hlayout2.addWidget(self.datelabel)
        hlayout2.addStretch()
        hlayout2.addWidget(self.log_button)
        
        layout = QVBoxLayout()
        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)
        layout.addWidget(self.datatree)
        self.setLayout(layout)
        
        self.process = None
        self.set_running_state(False)
        
        if not is_profiler_installed():
            for widget in (self.datatree, self.filecombo,
                           self.start_button, self.stop_button):
                widget.setDisabled(True)
            if os.name == 'nt' \
               and programs.is_module_installed("profile"):
                # The following is a comment from the pylint plugin:
                # Module is installed but script is not in PATH
                # (AFAIK, could happen only on Windows)
                text = translate('Profiler',
                     'Profiler script was not found. Please add "%s" to PATH.')
                text = unicode(text) % os.path.join(sys.prefix, "Scripts")
            else:
                text = translate('Profiler',
                    ('Please install the modules '+
                     '<b>profile</b> and <b>pstats</b>:'))
                # FIXME: need the actual website
                url = 'http://www.python.org'
                text += ' <a href=%s>%s</a>' % (url, url)
            self.datelabel.setText(text)
        else:
            pass # self.show_data()
                
    def analyze(self, filename):
        if not is_profiler_installed():
            return
        filename = unicode(filename) # filename is a QString instance
        self.kill_if_running()
        #index, _data = self.get_data(filename)
        index=None # FIXME: storing data is not implemented yet
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
        filename = QFileDialog.getOpenFileName(self,
                      translate('Profiler', "Select Python script"), os.getcwdu(),
                      translate('Profiler', "Python scripts")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        if filename:
            self.analyze(filename)
        
    def show_log(self):
        if self.output:
            TextEditor(self.output, title=translate('Profiler', "Profiler output"),
                       readonly=True, size=(700, 500)).exec_()
    
    def show_errorlog(self):
        if self.error_output:
            TextEditor(self.error_output, title=translate('Profiler', "Profiler output"),
                       readonly=True, size=(700, 500)).exec_()
        
    def start(self):
        self.datelabel.setText('Profiling, please wait...')
        filename = unicode(self.filecombo.currentText())
        
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.setWorkingDirectory(os.path.dirname(filename))
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
        p_args = [os.path.basename(filename)]
        
        # FIXME: Use the system path to 'python' as opposed to hardwired
        p_args = ['-m', PROFILER_PATH, '-o', self.DATAPATH, os.path.basename(filename)]
        self.process.start('python', p_args)
        
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, translate('Profiler', "Error"),
                                 translate('Profiler', "Process failed to start"))
    
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
        self.show_errorlog()  # If errors occurred, show them.
        self.output = self.error_output + self.output
        # FIXME: figure out if show_data should be called here or
        #        as a signal from the combobox
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

        self.datatree.load_data(self.DATAPATH)
        self.datatree.show_tree()
            
        text_style = "<span style=\'color: #444444\'><b>%s </b></span>"
        date_text = text_style % time.strftime("%d %b %Y %H:%M",time.localtime())
        self.datelabel.setText(date_text)


class ProfilerDataTree(QTreeWidget):
    '''Convenience tree widget (with built-in model) to store and view profiler data.

    The quantities calculated by the profiler are as follows (from profile.Profile) :
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
    '''
    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.headersList = ['Function/Module','TotalTime','LocalTime','Calls','File:line']
        self.iconDict = {'module':'console/python.png','function':'editor/function.png',
                         'builtin':'console/python_t.png','constructor':'editor/class.png'}
        self.profdata = []   # To be filled by self.load_data()
        self.stats = []      # To be filled by self.load_data()
        self.setColumnCount(len(self.headersList))
        self.setHeaderLabels(self.headersList)
        self.initialize_view()

    def initialize_view(self):
        '''Clean the tree and view parameters'''
        self.clear()
        self.itemDepth = 0   # To be use for collapsing/expanding one level
        self.itemsList = []  # To be use for collapsing/expanding one level
        self.currentViewDepth = 1

    def load_data(self,profDataFile):
        '''Load profiler data saved by profile/cProfile module'''
        import pstats
        self.profdata = pstats.Stats(profDataFile)
        self.stats = self.profdata.stats

    def find_root(self):
        '''Find a function without a caller'''
        for key,value in self.stats.iteritems():
            if not value[4]:
                return key
    
    def find_root_skip_profilerfuns(self):
        '''Define root ignoring profiler-specific functions.'''
        # FIXME: this is specific to module 'profile' and has to be
        #        changed for cProfile
        #return ('', 0, 'execfile')     # For 'profile' module   
        return ('~', 0, '<execfile>')     # For 'cProfile' module   
    
    def find_callees(self,parent):
        '''Find all functions called by (parent) function.'''
        # FIXME: This implementation is very inneficient, because it
        #        traverses all the data to find children nodes (callees)
        childrenList = []
        for key,value in self.stats.iteritems():
            if parent in value[4]:
                childrenList.append(key)
        return childrenList

    def show_tree(self):
        '''Populate the tree with profiler data and display it.'''
        self.initialize_view() # Clear before re-populating
        self.setItemsExpandable(True)
        self.setSortingEnabled(False)
        #rootKey = self.find_root()  # This root contains profiler overhead
        rootKey = self.find_root_skip_profilerfuns()
        self.populate_tree(self,self.find_callees(rootKey))
        self.resizeColumnToContents(0)
        self.setSortingEnabled(True)
        self.sortItems(1,Qt.DescendingOrder) # FIXME: hardcoded index
        self.change_view(1)

    def function_info(self, functionKey):
        '''Returns processed information about the function's name and file.'''
        nodeType = 'function'
        fileName,lineNumber,functionName = functionKey
        if functionName=='<module>':
            modulePath, moduleName = os.path.split(fileName)
            nodeType = 'module'
            if moduleName == '__init__.py':
                modulePath, moduleName = os.path.split(modulePath)
            functionName = '<' + moduleName + '>'
        if not fileName or fileName=='~':
            fileAndLine = '(built-in)'
            nodeType = 'builtin'
        else:
            if functionName=='__init__':
                nodeType = 'constructor'                
            fileAndLine = '%s : %d'%(fileName,lineNumber)
        return fileName,lineNumber,functionName,fileAndLine,nodeType

    def populate_tree(self,parentItem,childrenList):
        '''Recursive method to create each item (and associated data) in the tree.'''
        for childKey in childrenList:
            self.itemDepth +=1
            fileName,lineNumber,functionName,fileAndLine,nodeType = self.function_info(childKey)
            primCalls,totalCalls,locTime,cumTime,callers = self.stats[childKey]
            childItem = QTreeWidgetItem(parentItem)
            self.itemsList.append(childItem)
            childItem.setData(0,Qt.UserRole,self.itemDepth)

            # FIXME: indexes to data should be defined by a dictionary on init
            childItem.setToolTip(0,'Function or module name')
            childItem.setData(0,Qt.DisplayRole,functionName)
            childItem.setIcon(0,get_icon(self.iconDict[nodeType]))

            childItem.setToolTip(1,'Time in function (including sub-functions)')
            #childItem.setData(1,Qt.DisplayRole,cumTime)
            childItem.setData(1,Qt.DisplayRole,QString('%1').arg(cumTime,0,'f',3))
            childItem.setTextAlignment(1,Qt.AlignCenter)

            childItem.setToolTip(2,'Local time in function (not in sub-functions)')
            #childItem.setData(2,Qt.DisplayRole,locTime)
            childItem.setData(2,Qt.DisplayRole,QString('%1').arg(locTime,0,'f',3))
            childItem.setTextAlignment(2,Qt.AlignCenter)

            childItem.setToolTip(3,'Total number of calls (including recursion)')
            childItem.setData(3,Qt.DisplayRole,totalCalls)
            childItem.setTextAlignment(3,Qt.AlignCenter)

            childItem.setToolTip(4,'File:line where function is defined')
            childItem.setData(4,Qt.DisplayRole,fileAndLine)
            #childItem.setExpanded(True)
            if self.is_recursive(childItem):
                childItem.setData(4,Qt.DisplayRole,'(recursion)')
                childItem.setDisabled(True)
            else:
                self.populate_tree(childItem,self.find_callees(childKey))
            self.itemDepth -= 1
    
    def is_recursive(self,childItem):
        '''Returns True is a function is a descendant of itself.'''
        ancestor = childItem.parent()
        # FIXME: indexes to data should be defined by a dictionary on init
        while ancestor:
            if (childItem.data(0,Qt.DisplayRole)==ancestor.data(0,Qt.DisplayRole) and
                childItem.data(4,Qt.DisplayRole)==ancestor.data(4,Qt.DisplayRole)):
                return True
            else:
                ancestor = ancestor.parent()
        return False
            
    def change_view(self,changeInDepth):
        '''Change the view depth by expand or collapsing all same-level nodes'''
        self.currentViewDepth += changeInDepth
        if self.currentViewDepth < 1:
            self.currentViewDepth = 1
        for item in self.itemsList:
            itemDepth = item.data(0,Qt.UserRole).toInt()[0]
            isItemBelowLevel =  itemDepth<self.currentViewDepth
            item.setExpanded(isItemBelowLevel)                
    

def test():
    """Run widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = ProfilerWidget(None)
    widget.show()
    #widget.analyze(__file__)
    widget.analyze('/var/tmp/test001.py')
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    test()
