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
from qtpy.QtCore import (QEvent, QMutex, QMutexLocker, QSize, Qt, QThread,
                         Signal, Slot)
from qtpy.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
                            QMessageBox, QSizePolicy, QStyle,
                            QStyledItemDelegate, QStyleOptionViewItem,
                            QTreeWidgetItem, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.main import EXCLUDE_PATTERNS
from spyder.py3compat import to_text_string, PY2
from spyder.utils import icon_manager as ima
from spyder.utils.encoding import is_text_file, to_unicode_from_fs
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.comboboxes import PatternComboBox
from spyder.widgets.onecolumntree import OneColumnTree
from spyder.utils.misc import regexp_error_msg
from spyder.utils.qthelpers import create_toolbutton
from spyder.config.gui import get_font
from spyder.widgets.waitingspinner import QWaitingSpinner


ON = 'on'
OFF = 'off'

CWD = 0
PROJECT = 1
FILE_PATH = 2
SELECT_OTHER = 4
CLEAR_LIST = 5
EXTERNAL_PATHS = 7

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
        self.exclude = None
        self.texts = None
        self.text_re = None
        self.completed = None
        self.case_sensitive = True
        self.results = {}
        self.total_matches = 0
        self.is_file = False

    def initialize(self, path, is_file, exclude,
                   texts, text_re, case_sensitive):
        self.rootpath = path
        if exclude:
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
                    with QMutexLocker(self.mutex):
                        if self.stopped:
                            return False
                    dirname = os.path.join(path, d)
                    if (self.exclude and
                            re.search(self.exclude, dirname + os.sep)):
                        dirs.remove(d)
                    elif d == '.git' or d == '.hg':
                        dirs.remove(d)
                for f in files:
                    with QMutexLocker(self.mutex):
                        if self.stopped:
                            return False
                    filename = os.path.join(path, f)
                    if self.exclude and re.search(self.exclude, filename):
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
                    with QMutexLocker(self.mutex):
                        if self.stopped:
                            return False
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
                        with QMutexLocker(self.mutex):
                            if self.stopped:
                                return False
                        self.total_matches += 1
                        self.sig_file_match.emit((osp.abspath(fname),
                                                  lineno + 1,
                                                  match.start(),
                                                  match.end(), line_dec),
                                                 self.total_matches)
                else:
                    found = line.find(text)
                    while found > -1:
                        with QMutexLocker(self.mutex):
                            if self.stopped:
                                return False
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


class SearchInComboBox(QComboBox):
    """
    Non editable combo box handling the path locations of the FindOptions
    widget.
    """
    def __init__(self, external_path_history=[], parent=None):
        super(SearchInComboBox, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(_('Search directory'))
        self.setEditable(False)

        self.path = ''
        self.project_path = None
        self.file_path = None
        self.external_path = None

        self.addItem(_("Current working directory"))
        ttip = ("Search in all files and directories present on the current"
                " Spyder path")
        self.setItemData(0, ttip, Qt.ToolTipRole)

        self.addItem(_("Project"))
        ttip = _("Search in all files and directories present on the"
                 " current project path (if opened)")
        self.setItemData(1, ttip, Qt.ToolTipRole)
        self.model().item(1, 0).setEnabled(False)

        self.addItem(_("File").replace('&', ''))
        ttip = _("Search in current opened file")
        self.setItemData(2, ttip, Qt.ToolTipRole)

        self.insertSeparator(3)

        self.addItem(_("Select other directory"))
        ttip = _("Search in other folder present on the file system")
        self.setItemData(4, ttip, Qt.ToolTipRole)

        self.addItem(_("Clear this list"))
        ttip = _("Clear the list of other directories")
        self.setItemData(5, ttip, Qt.ToolTipRole)

        self.insertSeparator(6)

        for path in external_path_history:
            self.add_external_path(path)

        self.currentIndexChanged.connect(self.path_selection_changed)
        self.view().installEventFilter(self)

    def add_external_path(self, path):
        """
        Adds an external path to the combobox if it exists on the file system.
        If the path is already listed in the combobox, it is removed from its
        current position and added back at the end. If the maximum number of
        paths is reached, the oldest external path is removed from the list.
        """
        if not osp.exists(path):
            return
        self.removeItem(self.findText(path))
        self.addItem(path)
        self.setItemData(self.count() - 1, path, Qt.ToolTipRole)
        while self.count() > MAX_PATH_HISTORY + EXTERNAL_PATHS:
            self.removeItem(EXTERNAL_PATHS)

    def get_external_paths(self):
        """Returns a list of the external paths listed in the combobox."""
        return [to_text_string(self.itemText(i))
                for i in range(EXTERNAL_PATHS, self.count())]

    def clear_external_paths(self):
        """Remove all the external paths listed in the combobox."""
        while self.count() > EXTERNAL_PATHS:
            self.removeItem(EXTERNAL_PATHS)

    def get_current_searchpath(self):
        """
        Returns the path corresponding to the currently selected item
        in the combobox.
        """
        idx = self.currentIndex()
        if idx == CWD:
            return self.path
        elif idx == PROJECT:
            return self.project_path
        elif idx == FILE_PATH:
            return self.file_path
        else:
            return self.external_path

    def is_file_search(self):
        """Returns whether the current search path is a file."""
        if self.currentIndex() == FILE_PATH:
            return True
        else:
            return False

    @Slot()
    def path_selection_changed(self):
        """Handles when the current index of the combobox changes."""
        idx = self.currentIndex()
        if idx == SELECT_OTHER:
            external_path = self.select_directory()
            if len(external_path) > 0:
                self.add_external_path(external_path)
                self.setCurrentIndex(self.count() - 1)
            else:
                self.setCurrentIndex(CWD)
        elif idx == CLEAR_LIST:
            reply = QMessageBox.question(
                    self, _("Clear other directories"),
                    _("Do you want to clear the list of other directories?"),
                    QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.clear_external_paths()
            self.setCurrentIndex(CWD)
        elif idx >= EXTERNAL_PATHS:
            self.external_path = to_text_string(self.itemText(idx))

    @Slot()
    def select_directory(self):
        """Select directory"""
        self.__redirect_stdio_emit(False)
        directory = getexistingdirectory(
                self, _("Select directory"), self.path)
        if directory:
            directory = to_unicode_from_fs(osp.abspath(directory))
        self.__redirect_stdio_emit(True)
        return directory

    def set_project_path(self, path):
        """
        Sets the project path and disables the project search in the combobox
        if the value of path is None.
        """
        if path is None:
            self.project_path = None
            self.model().item(PROJECT, 0).setEnabled(False)
            if self.currentIndex() == PROJECT:
                self.setCurrentIndex(CWD)
        else:
            path = osp.abspath(path)
            self.project_path = path
            self.model().item(PROJECT, 0).setEnabled(True)

    def eventFilter(self, widget, event):
        """Used to handle key events on the QListView of the combobox."""
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Delete:
            index = self.view().currentIndex().row()
            if index >= EXTERNAL_PATHS:
                # Remove item and update the view.
                self.removeItem(index)
                self.showPopup()
                # Set the view selection so that it doesn't bounce around.
                new_index = min(self.count() - 1, index)
                new_index = 0 if new_index < EXTERNAL_PATHS else new_index
                self.view().setCurrentIndex(self.model().index(new_index, 0))
                self.setCurrentIndex(new_index)
            return True
        return QComboBox.eventFilter(self, widget, event)

    def __redirect_stdio_emit(self, value):
        """
        Searches through the parent tree to see if it is possible to emit the
        redirect_stdio signal.
        This logic allows to test the SearchInComboBox select_directory method
        outside of the FindInFiles plugin.
        """
        parent = self.parent()
        while parent is not None:
            try:
                parent.redirect_stdio.emit(value)
            except AttributeError:
                parent = parent.parent()
            else:
                break


class FindOptions(QWidget):
    """Find widget with options"""
    REGEX_INVALID = "background-color:rgb(255, 80, 80);"
    REGEX_ERROR = _("Regular expression error")

    find = Signal()
    stop = Signal()
    redirect_stdio = Signal(bool)

    def __init__(self, parent, search_text, search_text_regexp,
                 exclude, exclude_idx, exclude_regexp,
                 supported_encodings, more_options,
                 case_sensitive, external_path_history, options_button=None):
        QWidget.__init__(self, parent)

        if not isinstance(search_text, (list, tuple)):
            search_text = [search_text]
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
                                             icon=ima.icon('regex'),
                                             tip=_('Regular expression'))
        self.case_button = create_toolbutton(self,
                                             icon=ima.icon(
                                                     "format_letter_case"),
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
                                             icon=ima.icon('stop'),
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
                                               _("Exclude pattern"))
        if exclude_idx is not None and exclude_idx >= 0 \
           and exclude_idx < self.exclude_pattern.count():
            self.exclude_pattern.setCurrentIndex(exclude_idx)
        self.exclude_regexp = create_toolbutton(self,
                                                icon=ima.icon('regex'),
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
        self.path_selection_combo = SearchInComboBox(
                external_path_history, parent)

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

    def update_combos(self):
        self.search_text.lineEdit().returnPressed.emit()
        self.exclude_pattern.lineEdit().returnPressed.emit()

    def set_search_text(self, text):
        if text:
            self.search_text.add_text(text)
            self.search_text.lineEdit().selectAll()
        self.search_text.setFocus()

    def get_options(self, to_save=False):
        """Get options"""
        text_re = self.edit_regexp.isChecked()
        exclude_re = self.exclude_regexp.isChecked()
        case_sensitive = self.case_button.isChecked()

        # Return current options for them to be saved when closing
        # Spyder.
        if to_save:
            search_text = [to_text_string(self.search_text.itemText(index))
                           for index in range(self.search_text.count())]
            exclude = [to_text_string(self.exclude_pattern.itemText(index))
                       for index in range(self.exclude_pattern.count())]
            exclude_idx = self.exclude_pattern.currentIndex()
            path_history = self.path_selection_combo.get_external_paths()
            more_options = self.more_options.isChecked()
            return (search_text, text_re,
                    exclude, exclude_idx,
                    exclude_re, more_options,
                    case_sensitive, path_history)

        # Clear fields
        self.search_text.lineEdit().setStyleSheet("")
        self.exclude_pattern.lineEdit().setStyleSheet("")
        self.search_text.setToolTip("")
        self.exclude_pattern.setToolTip("")

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

        exclude = to_text_string(self.exclude_pattern.currentText())

        if not case_sensitive:
            texts = [(text[0].lower(), text[1]) for text in texts]

        file_search = self.path_selection_combo.is_file_search()
        path = self.path_selection_combo.get_current_searchpath()

        if not exclude_re:
            items = [fnmatch.translate(item.strip())
                     for item in exclude.split(",")
                     if item.strip() != '']
            exclude = '|'.join(items)

        # Validate exclude regular expression
        if exclude:
            error_msg = regexp_error_msg(exclude)
            if error_msg:
                exclude_edit = self.exclude_pattern.lineEdit()
                exclude_edit.setStyleSheet(self.REGEX_INVALID)
                tooltip = self.REGEX_ERROR + u': ' + to_text_string(error_msg)
                self.exclude_pattern.setToolTip(tooltip)
                return None
            else:
                exclude = re.compile(exclude)

        # Validate text regular expression
        if text_re:
            error_msg = regexp_error_msg(texts[0][0])
            if error_msg:
                self.search_text.lineEdit().setStyleSheet(self.REGEX_INVALID)
                tooltip = self.REGEX_ERROR + u': ' + to_text_string(error_msg)
                self.search_text.setToolTip(tooltip)
                return None
            else:
                texts = [(re.compile(x[0]), x[1]) for x in texts]

        return (path, file_search, exclude, texts, text_re, case_sensitive)

    @property
    def path(self):
        return self.path_selection_combo.path

    def set_directory(self, directory):
        self.path_selection_combo.path = osp.abspath(directory)

    @property
    def project_path(self):
        return self.path_selection_combo.project_path

    def set_project_path(self, path):
        self.path_selection_combo.set_project_path(path)

    def disable_project_search(self):
        self.path_selection_combo.set_project_path(None)

    @property
    def file_path(self):
        return self.path_selection_combo.file_path

    def set_file_path(self, path):
        self.path_selection_combo.file_path = path

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
    def __init__(self, parent, lineno, colno, match, text_color=None):
        self.lineno = lineno
        self.colno = colno
        self.match = match
        self.text_color = text_color
        QTreeWidgetItem.__init__(self, parent, [self.__repr__()],
                                 QTreeWidgetItem.Type)

    def __repr__(self):
        match = to_text_string(self.match).rstrip()
        font = get_font()
        _str = to_text_string("<p style=color:'{4}'><b>{1}</b> ({2}): "
                              "<span style='font-family:{0};"
                              "font-size:75%;'>{3}</span></p>")
        return _str.format(font.family(), self.lineno, self.colno, match,
                           self.text_color)

    def __unicode__(self):
        return self.__repr__()

    def __str__(self):
        return self.__repr__()

    def __lt__(self, x):
        return self.lineno < x.lineno

    def __ge__(self, x):
        return self.lineno >= x.lineno


class FileMatchItem(QTreeWidgetItem):
    def __init__(self, parent, filename, sorting, text_color=None):

        self.sorting = sorting
        self.filename = osp.basename(filename)

        title_format = to_text_string('<b style="color:{2}">{0}</b><br>'
                                      '<small style="color:{2}"><em>{1}</em>'
                                      '</small>')
        title = (title_format.format(osp.basename(filename),
                                     osp.dirname(filename),
                                     text_color))
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

    def __init__(self, parent, text_color=None):
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
        self.text_color = text_color
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
        ellipsis = u'...'
        max_line_length = 80
        max_num_char_fragment = 40

        html_escape_table = {
            u"&": u"&amp;",
            u'"': u"&quot;",
            u"'": u"&apos;",
            u">": u"&gt;",
            u"<": u"&lt;",
        }

        def html_escape(text):
            """Produce entities within text."""
            return u"".join(html_escape_table.get(c, c) for c in text)

        if PY2:
            line = to_text_string(line, encoding='utf8')
        else:
            line = to_text_string(line)
        left, match, right = line[:start], line[start:end], line[end:]

        if len(line) > max_line_length:
            offset = (len(line) - len(match)) // 2

            left = left.split(u' ')
            num_left_words = len(left)

            if num_left_words == 1:
                left = left[0]
                if len(left) > max_num_char_fragment:
                    left = ellipsis + left[-offset:]
                left = [left]

            right = right.split(u' ')
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

            left = u' '.join(left)
            right = u' '.join(right)

            if len(left) > max_num_char_fragment:
                left = ellipsis + left[-30:]

            if len(right) > max_num_char_fragment:
                right = right[:30] + ellipsis

        line_match_format = (u'<span style="color:{0}">{{0}}'
                             '<b>{{1}}</b>{{2}}</span>')
        line_match_format = line_match_format.format(self.text_color)

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
            file_item = FileMatchItem(self, filename, self.sorting,
                                      self.text_color)
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
        item = LineMatchItem(file_item, lineno, colno, line, self.text_color)
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
                 search_text="",
                 search_text_regexp=False,
                 exclude=EXCLUDE_PATTERNS[0],
                 exclude_idx=None,
                 exclude_regexp=False,
                 supported_encodings=("utf-8", "iso-8859-1", "cp1252"),
                 more_options=True,
                 case_sensitive=False,
                 external_path_history=[],
                 options_button=None,
                 text_color=None):
        QWidget.__init__(self, parent)

        self.setWindowTitle(_('Find in files'))

        self.search_thread = None
        self.status_bar = FileProgressBar(self)
        self.status_bar.hide()

        self.find_options = FindOptions(self, search_text,
                                        search_text_regexp,
                                        exclude, exclude_idx,
                                        exclude_regexp,
                                        supported_encodings,
                                        more_options,
                                        case_sensitive,
                                        external_path_history,
                                        options_button=options_button)
        self.find_options.find.connect(self.find)
        self.find_options.stop.connect(self.stop_and_reset_thread)

        self.result_browser = ResultsBrowser(self, text_color=text_color)

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
    from os.path import dirname
    app = qapplication()
    widget = FindInFilesWidget(None)
    widget.resize(640, 480)
    widget.show()
    external_paths = [
            dirname(__file__),
            dirname(dirname(__file__)),
            dirname(dirname(dirname(__file__))),
            dirname(dirname(dirname(dirname(__file__))))
            ]
    for path in external_paths:
        widget.find_options.path_selection_combo.add_external_path(path)
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
