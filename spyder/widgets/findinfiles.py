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
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QSizePolicy,
                            QTreeWidgetItem, QVBoxLayout, QWidget,
                            QStyledItemDelegate, QStyleOptionViewItem,
                            QApplication, QStyle, QListWidgetItem)

# Local imports
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.encoding import is_text_file
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.comboboxes import PatternComboBox
from spyder.widgets.onecolumntree import OneColumnTree
from spyder.utils.qthelpers import create_toolbutton, get_icon

from spyder.config.gui import get_font
from spyder.widgets.waitingspinner import QWaitingSpinner


ON = 'on'
OFF = 'off'

CWD = 0
PROJECT = 1
FILE_PATH = 2
EXTERNAL_PATH = 4

MAX_PATH_LENGTH = 60
MAX_PATH_HISTORY = 15


def truncate_path(text):
    ellipsis = '...'
    part_len = (MAX_PATH_LENGTH - len(ellipsis)) / 2.0
    left_text = text[:int(math.ceil(part_len))]
    right_text = text[-int(math.floor(part_len)):]
    return left_text + ellipsis + right_text


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
        self.case_sensitive = True
        self.get_pythonpath_callback = None
        self.results = {}
        self.total_matches = 0
        self.is_file = False

    def initialize(self, path, is_file, exclude,
                   texts, text_re, case_sensitive):
        self.rootpath = path
        self.python_path = False
        self.hg_manifest = False
        self.exclude = re.compile(exclude)
        self.texts = texts
        self.text_re = text_re
        self.is_file = is_file
        self.stopped = False
        self.completed = False
        self.case_sensitive = case_sensitive

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
                    line_search = line
                    if not self.case_sensitive:
                        line_search = line_search.lower()
                    if self.text_re:
                        found = re.search(text, line_search)
                        if found is not None:
                            break
                    else:
                        found = line_search.find(text)
                        if found > -1:
                            break
                try:
                    line_dec = line.decode(enc)
                except UnicodeDecodeError:
                    line_dec = line
                if not self.case_sensitive:
                    line = line.lower()
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


class ExternalPathItem(QListWidgetItem):
    def __init__(self, parent, path):
        self.path = path
        QListWidgetItem.__init__(self, self.__repr__(), parent)

    def __repr__(self):
        if len(self.path) > MAX_PATH_LENGTH:
            return truncate_path(self.path)
        return self.path

    def __str__(self):
        return self.__repr__()

    def __unicode__(self):
        return self.__repr__()


class FindOptions(QWidget):
    """Find widget with options"""
    REGEX_INVALID = "background-color:rgb(255, 175, 90);"
    find = Signal()
    stop = Signal()
    redirect_stdio = Signal(bool)

    def __init__(self, parent, search_text, search_text_regexp, search_path,
                 exclude, exclude_idx, exclude_regexp,
                 supported_encodings, in_python_path, more_options,
                 case_sensitive, external_path_history, options_button=None):
        QWidget.__init__(self, parent)

        if search_path is None:
            search_path = getcwd_or_home()

        self.path = ''
        self.project_path = None
        self.file_path = None
        self.external_path = None
        self.external_path_history = external_path_history

        if not isinstance(search_text, (list, tuple)):
            search_text = [search_text]
        if not isinstance(search_path, (list, tuple)):
            search_path = [search_path]
        if not isinstance(exclude, (list, tuple)):
            exclude = [exclude]
        if not isinstance(external_path_history, (list, tuple)):
            external_path_history = [external_path_history]

        self.supported_encodings = supported_encodings

        # Layout 1
        hlayout1 = QHBoxLayout()
        self.search_text = PatternComboBox(self, search_text,
                                           _("Search pattern"))
        self.edit_regexp = create_toolbutton(self,
                                             icon=ima.icon('advanced'),
                                             tip=_('Regular expression'))
        self.case_button = create_toolbutton(self,
                                             icon=get_icon("upper_lower.png"),
                                             tip=_("Case Sensitive"))
        self.case_button.setCheckable(True)
        self.case_button.setChecked(case_sensitive)
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
        for widget in [self.search_text, self.edit_regexp, self.case_button,
                       self.ok_button, self.stop_button, self.more_options]:
            hlayout1.addWidget(widget)
        if options_button:
            hlayout1.addWidget(options_button)

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

        search_on_label = QLabel(_("Search in:"))
        self.path_selection_combo = PatternComboBox(self, exclude,
                                                    _('Search directory'))
        self.path_selection_combo.setEditable(False)
        self.path_selection_contents = QListWidget(self.path_selection_combo)
        self.path_selection_contents.hide()
        self.path_selection_combo.setModel(
            self.path_selection_contents.model())

        self.path_selection_contents.addItem(_("Current working directory"))
        item = self.path_selection_contents.item(0)
        item.setToolTip(_("Search in all files and "
                          "directories present on the"
                          "current Spyder path"))

        self.path_selection_contents.addItem(_("Project"))
        item = self.path_selection_contents.item(1)
        item.setToolTip(_("Search in all files and "
                          "directories present on the"
                          "current project path "
                          "(If opened)"))
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        self.path_selection_contents.addItem(_("File").replace('&', ''))
        item = self.path_selection_contents.item(2)
        item.setToolTip(_("Search in current opened file"))

        self.path_selection_contents.addItem(_("Select other directory"))
        item = self.path_selection_contents.item(3)
        item.setToolTip(_("Search in other folder present on the file system"))

        self.path_selection_combo.insertSeparator(3)
        self.path_selection_combo.insertSeparator(5)
        for path in external_path_history:
            item = ExternalPathItem(None, path)
            self.path_selection_contents.addItem(item)

        self.path_selection_combo.currentIndexChanged.connect(
            self.path_selection_changed)

        hlayout3.addWidget(search_on_label)
        hlayout3.addWidget(self.path_selection_combo)

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

    @Slot()
    def path_selection_changed(self):
        idx = self.path_selection_combo.currentIndex()
        if idx == EXTERNAL_PATH:
            external_path = self.select_directory()
            if len(external_path) > 0:
                item = ExternalPathItem(None, external_path)
                self.path_selection_contents.addItem(item)

                total_items = (self.path_selection_combo.count() -
                               MAX_PATH_HISTORY)
                for i in range(6, total_items):
                    self.path_selection_contents.takeItem(i)

                self.path_selection_combo.setCurrentIndex(
                    self.path_selection_combo.count() - 1)
            else:
                self.path_selection_combo.setCurrentIndex(CWD)
        elif idx > EXTERNAL_PATH:
            item = self.path_selection_contents.item(idx)
            self.external_path = item.path

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
        case_sensitive = self.case_button.isChecked()
        python_path = False

        if not case_sensitive:
            texts = [(text[0].lower(), text[1]) for text in texts]

        file_search = False
        selection_idx = self.path_selection_combo.currentIndex()
        if selection_idx == CWD:
            path = self.path
        elif selection_idx == PROJECT:
            path = self.project_path
        elif selection_idx == FILE_PATH:
            path = self.file_path
            file_search = True
        else:
            path = self.external_path

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
            path_history = [to_text_string(
                            self.path_selection_contents.item(index))
                            for index in range(
                                6, self.path_selection_combo.count())]
            exclude_idx = self.exclude_pattern.currentIndex()
            more_options = self.more_options.isChecked()
            return (search_text, text_re, [],
                    exclude, exclude_idx, exclude_re,
                    python_path, more_options, case_sensitive, path_history)
        else:
            return (path, file_search, exclude, texts, text_re, case_sensitive)

    @Slot()
    def select_directory(self):
        """Select directory"""
        self.redirect_stdio.emit(False)
        directory = getexistingdirectory(self, _("Select directory"),
                                         self.path)
        if directory:
            directory = to_text_string(osp.abspath(to_text_string(directory)))
        self.redirect_stdio.emit(True)
        return directory

    def set_directory(self, directory):
        self.path = to_text_string(osp.abspath(to_text_string(directory)))

    def set_project_path(self, path):
        self.project_path = to_text_string(osp.abspath(to_text_string(path)))
        item = self.path_selection_contents.item(PROJECT)
        item.setFlags(item.flags() | Qt.ItemIsEnabled)

    def disable_project_search(self):
        item = self.path_selection_contents.item(PROJECT)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
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

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.status_text = QLabel(self)
        self.spinner = QWaitingSpinner(self, centerOnParent=False)
        self.spinner.setNumberOfLines(12)
        self.spinner.setInnerRadius(2)
        layout = QHBoxLayout()
        layout.addWidget(self.spinner)
        layout.addWidget(self.status_text)
        self.setLayout(layout)

    @Slot(str)
    def set_label_path(self, path, folder=False):
        text = truncate_path(path)
        if not folder:
            status_str = _(u' Scanning: {0}').format(text)
        else:
            status_str = _(u' Searching for files in folder: {0}').format(text)
        self.status_text.setText(status_str)

    def reset(self):
        self.status_text.setText(_("  Searching for files..."))

    def showEvent(self, event):
        """Override show event to start waiting spinner."""
        QWidget.showEvent(self, event)
        self.spinner.start()

    def hideEvent(self, event):
        """Override hide event to stop waiting spinner."""
        QWidget.hideEvent(self, event)
        self.spinner.stop()


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
                 in_python_path=False, more_options=False,
                 case_sensitive=True, external_path_history=[],
                 options_button=None):
        QWidget.__init__(self, parent)

        self.setWindowTitle(_('Find in files'))

        self.search_thread = None
        self.search_path = ''
        self.get_pythonpath_callback = None

        self.status_bar = FileProgressBar(self)
        self.status_bar.hide()

        self.find_options = FindOptions(self, search_text,
                                        search_text_regexp,
                                        search_path,
                                        exclude, exclude_idx,
                                        exclude_regexp,
                                        supported_encodings,
                                        in_python_path,
                                        more_options,
                                        case_sensitive,
                                        external_path_history,
                                        options_button=options_button)
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
        self.search_thread.get_pythonpath_callback = (
            self.get_pythonpath_callback)
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
