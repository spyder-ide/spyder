# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Find in files widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from __future__ import with_statement, print_function
import fnmatch
import os
import os.path as osp
import re
import sys
import math
import traceback

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtGui import QAbstractTextDocumentLayout, QTextDocument
from qtpy.QtCore import QMutex, QMutexLocker, Qt, QThread, Signal, Slot, QSize
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QRadioButton, QSizePolicy,
                            QTreeWidgetItem, QVBoxLayout, QWidget,
                            QStyledItemDelegate, QStyleOptionViewItem,
                            QApplication, QStyle)

# Local imports
from spyder.config.base import _
from spyder.py3compat import getcwd, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_toolbutton
from spyder.utils.encoding import is_text_file
from spyder.widgets.comboboxes import PatternComboBox
from spyder.widgets.onecolumntree import OneColumnTree

from spyder.config.gui import get_font
from spyder.widgets.waitingspinner import QWaitingSpinner


ON = 'on'
OFF = 'off'


class SearchThread(QThread):
    """Find in files search thread"""
    sig_finished = Signal(bool)
    sig_current_file = Signal(str)
    sig_current_folder = Signal(str)
    sig_file_match = Signal(tuple, int)
    sig_out_print = Signal(object)

    def __init__(self, parent):
        QThread.__init__(self, parent)
        self.mutex = QMutex()
        self.stopped = None
        self.results = None
        self.pathlist = None
        self.total_matches = None
        self.error_flag = None
        self.rootpath = None
        self.python_path = None
        self.hg_manifest = None
        self.exclude = None
        self.texts = None
        self.text_re = None
        self.completed = None
        self.get_pythonpath_callback = None
        self.results = {}
        self.total_matches = 0
        self.is_file = False

    def initialize(self, path, is_file, exclude, texts, text_re):
        self.rootpath = path
        self.python_path = False
        self.hg_manifest = False
        self.exclude = re.compile(exclude)
        self.texts = texts
        self.text_re = text_re
        self.is_file = is_file
        self.stopped = False
        self.completed = False

    def run(self):
        try:
            self.filenames = []
            if self.is_file:
                self.find_string_in_file(self.rootpath)
            else:
                self.find_files_in_path(self.rootpath)
        except Exception:
            # Important note: we have to handle unexpected exceptions by
            # ourselves because they won't be catched by the main thread
            # (known QThread limitation/bug)
            traceback.print_exc()
            self.error_flag = _("Unexpected error: see internal console")
        self.stop()
        self.sig_finished.emit(self.completed)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def find_files_in_path(self, path):
        if self.pathlist is None:
            self.pathlist = []
        self.pathlist.append(path)
        for path, dirs, files in os.walk(path):
            with QMutexLocker(self.mutex):
                if self.stopped:
                    return False
            try:
                for d in dirs[:]:
                    dirname = os.path.join(path, d)
                    if re.search(self.exclude, dirname + os.sep):
                        dirs.remove(d)
                for f in files:
                    filename = os.path.join(path, f)
                    if re.search(self.exclude, filename):
                        continue
                    if is_text_file(filename):
                        self.find_string_in_file(filename)
            except re.error:
                self.error_flag = _("invalid regular expression")
                return False
        return True

    def find_string_in_file(self, fname):
        self.error_flag = False
        self.sig_current_file.emit(fname)
        try:
            for lineno, line in enumerate(open(fname, 'rb')):
                for text, enc in self.texts:
                    if self.text_re:
                        found = re.search(text, line)
                        if found is not None:
                            break
                    else:
                        found = line.find(text)
                        if found > -1:
                            break
                try:
                    line_dec = line.decode(enc)
                except UnicodeDecodeError:
                    line_dec = line
                if self.text_re:
                    for match in re.finditer(text, line):
                        self.total_matches += 1
                        self.sig_file_match.emit((osp.abspath(fname),
                                                  lineno + 1,
                                                  match.start(),
                                                  match.end(), line_dec),
                                                 self.total_matches)
                else:
                    found = line.find(text)
                    while found > -1:
                        self.total_matches += 1
                        self.sig_file_match.emit((osp.abspath(fname),
                                                  lineno + 1,
                                                  found,
                                                  found + len(text), line_dec),
                                                 self.total_matches)
                        for text, enc in self.texts:
                            found = line.find(text, found + 1)
                            if found > -1:
                                break
        except IOError as xxx_todo_changeme:
            (_errno, _strerror) = xxx_todo_changeme.args
            self.error_flag = _("permission denied errors were encountered")
        self.completed = True

    def get_results(self):
        return self.results, self.pathlist, self.total_matches, self.error_flag


class FindOptions(QWidget):
    """Find widget with options"""
    REGEX_INVALID = "background-color:rgb(255, 175, 90);"
    find = Signal()
    stop = Signal()
    redirect_stdio = Signal(bool)

    def __init__(self, parent, search_text, search_text_regexp, search_path,
                 exclude, exclude_idx, exclude_regexp,
                 supported_encodings, in_python_path, more_options):
        QWidget.__init__(self, parent)

        if search_path is None:
            search_path = getcwd()

        self.path = ''
        self.project_path = None
        self.file_path = None

        if not isinstance(search_text, (list, tuple)):
            search_text = [search_text]
        if not isinstance(search_path, (list, tuple)):
            search_path = [search_path]
        if not isinstance(exclude, (list, tuple)):
            exclude = [exclude]

        self.supported_encodings = supported_encodings

        # Layout 1
        hlayout1 = QHBoxLayout()
        self.search_text = PatternComboBox(self, search_text,
                                           _("Search pattern"))
        self.edit_regexp = create_toolbutton(self,
                                             icon=ima.icon('advanced'),
                                             tip=_('Regular expression'))
        self.edit_regexp.setCheckable(True)
        self.edit_regexp.setChecked(search_text_regexp)
        self.more_widgets = ()
        self.more_options = create_toolbutton(self,
                                              toggled=self.toggle_more_options)
        self.more_options.setCheckable(True)
        self.more_options.setChecked(more_options)

        self.ok_button = create_toolbutton(self, text=_("Search"),
                                           icon=ima.icon('find'),
                                           triggered=lambda: self.find.emit(),
                                           tip=_("Start search"),
                                           text_beside_icon=True)
        self.ok_button.clicked.connect(self.update_combos)
        self.stop_button = create_toolbutton(self, text=_("Stop"),
                                             icon=ima.icon('editclear'),
                                             triggered=lambda:
                                             self.stop.emit(),
                                             tip=_("Stop search"),
                                             text_beside_icon=True)
        self.stop_button.setEnabled(False)
        for widget in [self.search_text, self.edit_regexp,
                       self.ok_button, self.stop_button, self.more_options]:
            hlayout1.addWidget(widget)

        # Layout 2
        hlayout2 = QHBoxLayout()
        self.exclude_pattern = PatternComboBox(self, exclude,
                                               _("Excluded filenames pattern"))
        if exclude_idx is not None and exclude_idx >= 0 \
           and exclude_idx < self.exclude_pattern.count():
            self.exclude_pattern.setCurrentIndex(exclude_idx)
        self.exclude_regexp = create_toolbutton(self,
                                                icon=ima.icon('advanced'),
                                                tip=_('Regular expression'))
        self.exclude_regexp.setCheckable(True)
        self.exclude_regexp.setChecked(exclude_regexp)
        exclude_label = QLabel(_("Exclude:"))
        exclude_label.setBuddy(self.exclude_pattern)
        for widget in [exclude_label, self.exclude_pattern,
                       self.exclude_regexp]:
            hlayout2.addWidget(widget)

        # Layout 3
        hlayout3 = QHBoxLayout()

        self.global_path_search = QRadioButton(_("Current Working "
                                                 "Directory"), self)
        self.global_path_search.setChecked(True)
        self.global_path_search.setToolTip(_("Search in all files and "
                                             "directories present on the"
                                             "current Spyder path"))

        self.project_search = QRadioButton(_("Project"), self)
        self.project_search.setToolTip(_("Search in all files and "
                                         "directories present on the"
                                         "current project path (If opened)"))

        self.project_search.setEnabled(False)

        self.file_search = QRadioButton(_("File"), self)
        self.file_search.setToolTip(_("Search in current opened file"))

        for wid in [self.global_path_search,
                    self.project_search, self.file_search]:
            hlayout3.addWidget(wid)

        hlayout3.addStretch(1)

        self.search_text.valid.connect(lambda valid: self.find.emit())
        self.exclude_pattern.valid.connect(lambda valid: self.find.emit())

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addLayout(hlayout1)
        vlayout.addLayout(hlayout2)
        vlayout.addLayout(hlayout3)
        self.more_widgets = (hlayout2,)
        self.toggle_more_options(more_options)
        self.setLayout(vlayout)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    @Slot(bool)
    def toggle_more_options(self, state):
        for layout in self.more_widgets:
            for index in range(layout.count()):
                if state and self.isVisible() or not state:
                    layout.itemAt(index).widget().setVisible(state)
        if state:
            icon = ima.icon('options_less')
            tip = _('Hide advanced options')
        else:
            icon = ima.icon('options_more')
            tip = _('Show advanced options')
        self.more_options.setIcon(icon)
        self.more_options.setToolTip(tip)

    def update_combos(self):
        self.search_text.lineEdit().returnPressed.emit()
        self.exclude_pattern.lineEdit().returnPressed.emit()

    def set_search_text(self, text):
        if text:
            self.search_text.add_text(text)
            self.search_text.lineEdit().selectAll()
        self.search_text.setFocus()

    def get_options(self, all=False):
        # Getting options
        self.search_text.lineEdit().setStyleSheet("")
        self.exclude_pattern.lineEdit().setStyleSheet("")

        utext = to_text_string(self.search_text.currentText())
        if not utext:
            return
        try:
            texts = [(utext.encode('utf-8'), 'utf-8')]
        except UnicodeEncodeError:
            texts = []
            for enc in self.supported_encodings:
                try:
                    texts.append((utext.encode(enc), enc))
                except UnicodeDecodeError:
                    pass
        text_re = self.edit_regexp.isChecked()
        exclude = to_text_string(self.exclude_pattern.currentText())
        exclude_re = self.exclude_regexp.isChecked()
        python_path = False

        global_path_search = self.global_path_search.isChecked()
        project_search = self.project_search.isChecked()
        file_search = self.file_search.isChecked()

        if global_path_search:
            path = self.path
        elif project_search:
            path = self.project_path
        else:
            path = self.file_path

        # Finding text occurrences
        if not exclude_re:
            exclude = fnmatch.translate(exclude)
        else:
            try:
                exclude = re.compile(exclude)
            except Exception:
                exclude_edit = self.exclude_pattern.lineEdit()
                exclude_edit.setStyleSheet(self.REGEX_INVALID)
                return None

        if text_re:
            try:
                texts = [(re.compile(x[0]), x[1]) for x in texts]
            except Exception:
                self.search_text.lineEdit().setStyleSheet(self.REGEX_INVALID)
                return None

        if all:
            search_text = [to_text_string(self.search_text.itemText(index))
                           for index in range(self.search_text.count())]
            exclude = [to_text_string(self.exclude_pattern.itemText(index))
                       for index in range(self.exclude_pattern.count())]
            exclude_idx = self.exclude_pattern.currentIndex()
            more_options = self.more_options.isChecked()
            return (search_text, text_re, [],
                    exclude, exclude_idx, exclude_re,
                    python_path, more_options)
        else:
            return (path, file_search, exclude, texts, text_re)

    @Slot()
    def select_directory(self):
        """Select directory"""
        self.redirect_stdio.emit(False)
        directory = getexistingdirectory(self, _("Select directory"),
                                         self.dir_combo.currentText())
        if directory:
            self.set_directory(directory)
        self.redirect_stdio.emit(True)

    def set_directory(self, directory):
        self.path = to_text_string(osp.abspath(to_text_string(directory)))

    def set_project_path(self, path):
        self.project_path = to_text_string(osp.abspath(to_text_string(path)))
        self.project_search.setEnabled(True)

    def disable_project_search(self):
        self.project_search.setEnabled(False)
        self.project_search.setChecked(False)
        self.project_path = None

    def set_file_path(self, path):
        self.file_path = path

    def keyPressEvent(self, event):
        """Reimplemented to handle key events"""
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.find.emit()
        elif event.key() == Qt.Key_F and ctrl and shift:
            # Toggle find widgets
            self.parent().toggle_visibility.emit(not self.isVisible())
        else:
            QWidget.keyPressEvent(self, event)


class LineMatchItem(QTreeWidgetItem):
    def __init__(self, parent, lineno, colno, match):
        self.lineno = lineno
        self.colno = colno
        self.match = match
        QTreeWidgetItem.__init__(self, parent, [self.__repr__()],
                                 QTreeWidgetItem.Type)

    def __repr__(self):
        match = to_text_string(self.match).rstrip()
        font = get_font()
        _str = to_text_string("<b>{1}</b> ({2}): "
                              "<span style='font-family:{0};"
                              "font-size:75%;'>{3}</span>")
        return _str.format(font.family(), self.lineno, self.colno, match)

    def __unicode__(self):
        return self.__repr__()

    def __str__(self):
        return self.__repr__()

    def __lt__(self, x):
        return self.lineno < x.lineno

    def __ge__(self, x):
        return self.lineno >= x.lineno


class FileMatchItem(QTreeWidgetItem):
    def __init__(self, parent, filename, sorting):

        self.sorting = sorting
        self.filename = osp.basename(filename)

        title_format = to_text_string('<b>{0}</b><br>'
                                      '<small><em>{1}</em>'
                                      '</small>')
        title = (title_format.format(osp.basename(filename),
                                     osp.dirname(filename)))
        QTreeWidgetItem.__init__(self, parent, [title], QTreeWidgetItem.Type)

        self.setToolTip(0, filename)

    def __lt__(self, x):
        if self.sorting['status'] == ON:
            return self.filename < x.filename
        else:
            return False

    def __ge__(self, x):
        if self.sorting['status'] == ON:
            return self.filename >= x.filename
        else:
            return False


class ItemDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        QStyledItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setHtml(options.text)

        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
        painter.save()

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())

        return QSize(doc.idealWidth(), doc.size().height())


class ResultsBrowser(OneColumnTree):
    sig_edit_goto = Signal(str, int, str)

    def __init__(self, parent):
        OneColumnTree.__init__(self, parent)
        self.search_text = None
        self.results = None
        self.total_matches = None
        self.error_flag = None
        self.completed = None
        self.sorting = {}
        self.data = None
        self.files = None
        self.set_title('')
        self.set_sorting(OFF)
        self.setSortingEnabled(False)
        self.root_items = None
        self.sortByColumn(0, Qt.AscendingOrder)
        self.setItemDelegate(ItemDelegate(self))
        self.setUniformRowHeights(False)
        self.header().sectionClicked.connect(self.sort_section)

    def activated(self, item):
        """Double-click event"""
        itemdata = self.data.get(id(self.currentItem()))
        if itemdata is not None:
            filename, lineno, colno = itemdata
            self.sig_edit_goto.emit(filename, lineno, self.search_text)

    def set_sorting(self, flag):
        """Enable result sorting after search is complete."""
        self.sorting['status'] = flag
        self.header().setSectionsClickable(flag == ON)

    @Slot(int)
    def sort_section(self, idx):
        self.setSortingEnabled(True)

    def clicked(self, item):
        """Click event"""
        self.activated(item)

    def clear_title(self, search_text):
        self.clear()
        self.setSortingEnabled(False)
        self.num_files = 0
        self.data = {}
        self.files = {}
        self.set_sorting(OFF)
        self.search_text = search_text
        title = "'%s' - " % search_text
        text = _('String not found')
        self.set_title(title + text)

    def truncate_result(self, line, start, end):
        ellipsis = '...'
        max_line_length = 80
        max_num_char_fragment = 40

        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }

        def html_escape(text):
            """Produce entities within text."""
            return "".join(html_escape_table.get(c, c) for c in text)

        line = to_text_string(line)
        left, match, right = line[:start], line[start:end], line[end:]

        if len(line) > max_line_length:
            offset = (len(line) - len(match)) // 2

            left = left.split(' ')
            num_left_words = len(left)

            if num_left_words == 1:
                left = left[0]
                if len(left) > max_num_char_fragment:
                    left = ellipsis + left[-offset:]
                left = [left]

            right = right.split(' ')
            num_right_words = len(right)

            if num_right_words == 1:
                right = right[0]
                if len(right) > max_num_char_fragment:
                    right = right[:offset] + ellipsis
                right = [right]

            left = left[-4:]
            right = right[:4]

            if len(left) < num_left_words:
                left = [ellipsis] + left

            if len(right) < num_right_words:
                right = right + [ellipsis]

            left = ' '.join(left)
            right = ' '.join(right)

            if len(left) > max_num_char_fragment:
                left = ellipsis + left[-30:]

            if len(right) > max_num_char_fragment:
                right = right[:30] + ellipsis

        line_match_format = to_text_string('{0}<b>{1}</b>{2}')
        left = html_escape(left)
        right = html_escape(right)
        match = html_escape(match)
        trunc_line = line_match_format.format(left, match, right)
        return trunc_line

    @Slot(tuple, int)
    def append_result(self, results, num_matches):
        """Real-time update of search results"""
        filename, lineno, colno, match_end, line = results

        if filename not in self.files:
            file_item = FileMatchItem(self, filename, self.sorting)
            file_item.setExpanded(True)
            self.files[filename] = file_item
            self.num_files += 1

        search_text = self.search_text
        title = "'%s' - " % search_text
        nb_files = self.num_files
        if nb_files == 0:
            text = _('String not found')
        else:
            text_matches = _('matches in')
            text_files = _('file')
            if nb_files > 1:
                text_files += 's'
            text = "%d %s %d %s" % (num_matches, text_matches,
                                    nb_files, text_files)
        self.set_title(title + text)

        file_item = self.files[filename]
        line = self.truncate_result(line, colno, match_end)
        item = LineMatchItem(file_item, lineno, colno, line)
        self.data[id(item)] = (filename, lineno, colno)


class FileProgressBar(QWidget):
    """Simple progress spinner with a label"""
    MAX_LABEL_LENGTH = 60

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.status_text = QLabel(self)
        self.spinner = QWaitingSpinner(self, centerOnParent=False)
        self.spinner.setNumberOfLines(12)
        self.spinner.setInnerRadius(2)
        self.spinner.start()
        layout = QHBoxLayout()
        layout.addWidget(self.spinner)
        layout.addWidget(self.status_text)
        self.setLayout(layout)

    def __truncate(self, text):
        ellipsis = '...'
        part_len = (self.MAX_LABEL_LENGTH - len(ellipsis)) / 2.0
        left_text = text[:int(math.ceil(part_len))]
        right_text = text[-int(math.floor(part_len)):]
        return left_text + ellipsis + right_text

    @Slot(str)
    def set_label_path(self, path, folder=False):
        text = self.__truncate(path)
        if not folder:
            status_str = _(u' Scanning: {0}'.format(text))
        else:
            status_str = _(u' Searching for files in folder: {0}'.format(text))
        self.status_text.setText(status_str)

    def reset(self):
        self.status_text.setText(_("  Searching for files..."))


class FindInFilesWidget(QWidget):
    """
    Find in files widget
    """
    sig_finished = Signal()

    def __init__(self, parent,
                 search_text=r"# ?TODO|# ?FIXME|# ?XXX",
                 search_text_regexp=True, search_path=None,
                 exclude=r"\.pyc$|\.orig$|\.hg|\.svn", exclude_idx=None,
                 exclude_regexp=True,
                 supported_encodings=("utf-8", "iso-8859-1", "cp1252"),
                 in_python_path=False, more_options=False):
        QWidget.__init__(self, parent)

        self.setWindowTitle(_('Find in files'))

        self.search_thread = None
        self.search_path = ''
        self.get_pythonpath_callback = None

        self.status_bar = FileProgressBar(self)
        self.status_bar.hide()
        self.find_options = FindOptions(self, search_text, search_text_regexp,
                                        search_path,
                                        exclude, exclude_idx, exclude_regexp,
                                        supported_encodings, in_python_path,
                                        more_options)
        self.find_options.find.connect(self.find)
        self.find_options.stop.connect(self.stop_and_reset_thread)

        self.result_browser = ResultsBrowser(self)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.result_browser)

        layout = QVBoxLayout()
        left, _x, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom)
        layout.addWidget(self.find_options)
        layout.addLayout(hlayout)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)

    def set_search_text(self, text):
        """Set search pattern"""
        self.find_options.set_search_text(text)

    def find(self):
        """Call the find function"""
        options = self.find_options.get_options()
        if options is None:
            return
        self.stop_and_reset_thread(ignore_results=True)
        self.search_thread = SearchThread(self)
        self.search_thread.get_pythonpath_callback = \
                                                self.get_pythonpath_callback
        self.search_thread.sig_finished.connect(self.search_complete)
        self.search_thread.sig_current_file.connect(
            lambda x: self.status_bar.set_label_path(x, folder=False)
        )
        self.search_thread.sig_current_folder.connect(
            lambda x: self.status_bar.set_label_path(x, folder=True)
        )
        self.search_thread.sig_file_match.connect(
            self.result_browser.append_result
        )
        self.search_thread.sig_out_print.connect(
            lambda x: sys.stdout.write(str(x) + "\n")
        )
        self.status_bar.reset()
        self.result_browser.clear_title(
            self.find_options.search_text.currentText())
        self.search_thread.initialize(*options)
        self.search_thread.start()
        self.find_options.ok_button.setEnabled(False)
        self.find_options.stop_button.setEnabled(True)
        self.status_bar.show()

    def stop_and_reset_thread(self, ignore_results=False):
        """Stop current search thread and clean-up"""
        if self.search_thread is not None:
            if self.search_thread.isRunning():
                if ignore_results:
                    self.search_thread.sig_finished.disconnect(
                        self.search_complete)
                self.search_thread.stop()
                self.search_thread.wait()
            self.search_thread.setParent(None)
            self.search_thread = None

    def closing_widget(self):
        """Perform actions before widget is closed"""
        self.stop_and_reset_thread(ignore_results=True)

    def search_complete(self, completed):
        """Current search thread has finished"""
        self.result_browser.set_sorting(ON)
        self.find_options.ok_button.setEnabled(True)
        self.find_options.stop_button.setEnabled(False)
        self.status_bar.hide()
        self.result_browser.expandAll()
        if self.search_thread is None:
            return
        self.sig_finished.emit()
        found = self.search_thread.get_results()
        self.stop_and_reset_thread()
        if found is not None:
            results, pathlist, nb, error_flag = found
            self.result_browser.show()


def test():
    """Run Find in Files widget test"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    widget = FindInFilesWidget(None)
    widget.resize(640, 480)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
