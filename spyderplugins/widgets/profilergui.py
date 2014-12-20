# -*- coding: utf-8 -*-
#
# Copyright © 2011 Santiago Jaramillo
# based on pylintgui.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Profiler widget

See the official documentation on python profiling:
http://docs.python.org/library/profile.html

Questions for Pierre and others:
    - Where in the menu should profiler go?  Run > Profile code ?
"""

from __future__ import with_statement

from spyderlib.qt.QtGui import (QHBoxLayout, QWidget, QMessageBox, QVBoxLayout,
                                QLabel, QTreeWidget, QTreeWidgetItem,
                                QApplication)
from spyderlib.qt.QtCore import SIGNAL, QProcess, QByteArray, Qt, QTextCodec
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import getopenfilename

import sys
import os
import os.path as osp
import time

# Local imports
from spyderlib.utils.qthelpers import (create_toolbutton, get_item_user_text,
                                       set_item_user_text, get_icon)
from spyderlib.utils.programs import shell_split
from spyderlib.baseconfig import get_conf_path, get_translation
from spyderlib.widgets.texteditor import TextEditor
from spyderlib.widgets.comboboxes import PythonModulesComboBox
from spyderlib.widgets.externalshell import baseshell
from spyderlib.py3compat import to_text_string, getcwd
_ = get_translation("p_profiler", dirname="spyderplugins")


def is_profiler_installed():
    from spyderlib.utils.programs import is_module_installed
    return is_module_installed('cProfile') and is_module_installed('pstats')


class ProfilerWidget(QWidget):
    """
    Profiler widget
    """
    DATAPATH = get_conf_path('profiler.results')
    VERSION = '0.0.1'
    
    def __init__(self, parent, max_entries=100):
        QWidget.__init__(self, parent)
        
        self.setWindowTitle("Profiler")
        
        self.output = None
        self.error_output = None
        
        self._last_wdir = None
        self._last_args = None
        self._last_pythonpath = None
        
        self.filecombo = PythonModulesComboBox(self)
        
        self.start_button = create_toolbutton(self, icon=get_icon('run.png'),
                                    text=_("Profile"),
                                    tip=_("Run profiler"),
                                    triggered=self.start, text_beside_icon=True)
        self.stop_button = create_toolbutton(self,
                                             icon=get_icon('stop.png'),
                                             text=_("Stop"),
                                             tip=_("Stop current profiling"),
                                             text_beside_icon=True)
        self.connect(self.filecombo, SIGNAL('valid(bool)'),
                     self.start_button.setEnabled)
        #self.connect(self.filecombo, SIGNAL('valid(bool)'), self.show_data)
        # FIXME: The combobox emits this signal on almost any event
        #        triggering show_data() too early, too often. 

        browse_button = create_toolbutton(self, icon=get_icon('fileopen.png'),
                               tip=_('Select Python script'),
                               triggered=self.select_file)

        self.datelabel = QLabel()

        self.log_button = create_toolbutton(self, icon=get_icon('log.png'),
                                            text=_("Output"),
                                            text_beside_icon=True,
                                            tip=_("Show program's output"),
                                            triggered=self.show_log)

        self.datatree = ProfilerDataTree(self)

        self.collapse_button = create_toolbutton(self,
                                                 icon=get_icon('collapse.png'),
                                                 triggered=lambda dD=-1:
                                                 self.datatree.change_view(dD),
                                                 tip=_('Collapse one level up'))
        self.expand_button = create_toolbutton(self,
                                               icon=get_icon('expand.png'),
                                               triggered=lambda dD=1:
                                               self.datatree.change_view(dD),
                                               tip=_('Expand one level down'))

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
        self.start_button.setEnabled(False)
        
        if not is_profiler_installed():
            # This should happen only on certain GNU/Linux distributions 
            # or when this a home-made Python build because the Python 
            # profilers are included in the Python standard library
            for widget in (self.datatree, self.filecombo,
                           self.start_button, self.stop_button):
                widget.setDisabled(True)
            url = 'http://docs.python.org/library/profile.html'
            text = '%s <a href=%s>%s</a>' % (_('Please install'), url,
                                             _("the Python profiler modules"))
            self.datelabel.setText(text)
        else:
            pass # self.show_data()
        
    def analyze(self, filename, wdir=None, args=None, pythonpath=None):
        if not is_profiler_installed():
            return
        self.kill_if_running()
        #index, _data = self.get_data(filename)
        index = None # FIXME: storing data is not implemented yet
        if index is None:
            self.filecombo.addItem(filename)
            self.filecombo.setCurrentIndex(self.filecombo.count()-1)
        else:
            self.filecombo.setCurrentIndex(self.filecombo.findText(filename))
        self.filecombo.selected()
        if self.filecombo.is_valid():
            if wdir is None:
                wdir = osp.dirname(filename)
            self.start(wdir, args, pythonpath)
            
    def select_file(self):
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename, _selfilter = getopenfilename(self, _("Select Python script"),
                           getcwd(), _("Python scripts")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        if filename:
            self.analyze(filename)
        
    def show_log(self):
        if self.output:
            TextEditor(self.output, title=_("Profiler output"),
                       readonly=True, size=(700, 500)).exec_()
    
    def show_errorlog(self):
        if self.error_output:
            TextEditor(self.error_output, title=_("Profiler output"),
                       readonly=True, size=(700, 500)).exec_()

    def start(self, wdir=None, args=None, pythonpath=None):
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
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.read_output)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     lambda: self.read_output(error=True))
        self.connect(self.process,
                     SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        self.connect(self.stop_button, SIGNAL("clicked()"), self.process.kill)

        if pythonpath is not None:
            env = [to_text_string(_pth)
                   for _pth in self.process.systemEnvironment()]
            baseshell.add_pathlist_to_PYTHONPATH(env, pythonpath)
            self.process.setEnvironment(env)
        
        self.output = ''
        self.error_output = ''
        
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
        filename = to_text_string(self.filecombo.currentText())
        if not filename:
            return

        self.datatree.load_data(self.DATAPATH)
        self.datelabel.setText(_('Sorting data, please wait...'))
        QApplication.processEvents()
        self.datatree.show_tree()
            
        text_style = "<span style=\'color: #444444\'><b>%s </b></span>"
        date_text = text_style % time.strftime("%d %b %Y %H:%M",
                                               time.localtime())
        self.datelabel.setText(date_text)


class TreeWidgetItem( QTreeWidgetItem ):
    def __init__(self, parent=None):
        QTreeWidgetItem.__init__(self, parent)
    
    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            return float( self.text(column) ) > float( otherItem.text(column) )
        except ValueError:
            return self.text(column) > otherItem.text(column)


class ProfilerDataTree(QTreeWidget):
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
    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.header_list = [_('Function/Module'), _('Total Time'),
                            _('Local Time'), _('Calls'), _('File:line')]
        self.icon_list = {'module':      'python.png',
                         'function':    'function.png',
                         'builtin':     'python_t.png',
                         'constructor': 'class.png'}
        self.profdata = None   # To be filled by self.load_data()
        self.stats = None      # To be filled by self.load_data()
        self.item_depth = None
        self.item_list = None
        self.items_to_be_shown = None
        self.current_view_depth = None
        self.setColumnCount(len(self.header_list))
        self.setHeaderLabels(self.header_list)
        self.initialize_view()
        self.connect(self, SIGNAL('itemActivated(QTreeWidgetItem*,int)'),
                     self.item_activated)
        self.connect(self, SIGNAL('itemExpanded(QTreeWidgetItem*)'),
                     self.item_expanded)

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
        self.profdata = pstats.Stats(profdatafile)
        self.profdata.calc_callees()
        self.stats = self.profdata.stats

    def find_root(self):
        """Find a function without a caller"""
        self.profdata.sort_stats("cumulative")
        for func in self.profdata.fcn_list:
            if ('~', 0, '<built-in method exec>') != func: 
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
        if rootkey:
            self.populate_tree(self, self.find_callees(rootkey))
            self.resizeColumnToContents(0)
            self.setSortingEnabled(True)
            self.sortItems(1, Qt.DescendingOrder) # FIXME: hardcoded index
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
    
    def populate_tree(self, parentItem, children_list):
        """Recursive method to create each item (and associated data) in the tree."""
        for child_key in children_list:
            self.item_depth += 1
            (filename, line_number, function_name, file_and_line, node_type
             ) = self.function_info(child_key)
            (primcalls, total_calls, loc_time, cum_time, callers
             ) = self.stats[child_key]
            child_item = TreeWidgetItem(parentItem)
            self.item_list.append(child_item)
            self.set_item_data(child_item, filename, line_number)

            # FIXME: indexes to data should be defined by a dictionary on init
            child_item.setToolTip(0, 'Function or module name')
            child_item.setData(0, Qt.DisplayRole, function_name)
            child_item.setIcon(0, get_icon(self.icon_list[node_type]))

            child_item.setToolTip(1, _('Time in function '\
                                       '(including sub-functions)'))
            #child_item.setData(1, Qt.DisplayRole, cum_time)
            child_item.setData(1, Qt.DisplayRole, '%.3f' % cum_time)
            child_item.setTextAlignment(1, Qt.AlignCenter)

            child_item.setToolTip(2, _('Local time in function '\
                                      '(not in sub-functions)'))
            #child_item.setData(2, Qt.DisplayRole, loc_time)
            child_item.setData(2, Qt.DisplayRole, '%.3f' % loc_time)
            child_item.setTextAlignment(2, Qt.AlignCenter)

            child_item.setToolTip(3, _('Total number of calls '\
                                       '(including recursion)'))
            child_item.setData(3, Qt.DisplayRole, total_calls)
            child_item.setTextAlignment(3, Qt.AlignCenter)

            child_item.setToolTip(4, _('File:line '\
                                       'where function is defined'))
            child_item.setData(4, Qt.DisplayRole, file_and_line)
            #child_item.setExpanded(True)
            if self.is_recursive(child_item):
                child_item.setData(4, Qt.DisplayRole, '(%s)' % _('recursion'))
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
        self.parent().emit(SIGNAL("edit_goto(QString,int,QString)"),
                           filename, line_number, '')
            
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
                child_item.data(4, Qt.DisplayRole
                                ) == ancestor.data(4, Qt.DisplayRole)):
                return True
            else:
                ancestor = ancestor.parent()
        return False
    
    def get_top_level_items(self):
        """Iterate over top level items"""
        return [self.topLevelItem(_i) for _i in range(self.topLevelItemCount())]
    
    def get_items(self, maxlevel):
        """Return items (excluding top level items)"""
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
            if maxlevel > 1:
                add_to_itemlist(tlitem, maxlevel=maxlevel)
        return itemlist
            
    def change_view(self, change_in_depth):
        """Change the view depth by expand or collapsing all same-level nodes"""
        self.current_view_depth += change_in_depth
        if self.current_view_depth < 1:
            self.current_view_depth = 1
        self.collapseAll()
        for item in self.get_items(maxlevel=self.current_view_depth):
            item.setExpanded(True)
    

def test():
    """Run widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = ProfilerWidget(None)
    widget.resize(800, 600)
    widget.show()
    #widget.analyze(__file__)
    widget.analyze(osp.join(osp.dirname(__file__), os.pardir, os.pardir,
                            'spyderlib/widgets', 'texteditor.py'))
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    test()
