# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Find in files widget.
"""

# Standard library imports
import math
import os
import os.path as osp
import re
import stat
import traceback

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import (QEvent, QMutex, QMutexLocker, QPoint, QSize, Qt,
                         QThread, Signal, Slot)
from qtpy.QtGui import QAbstractTextDocumentLayout, QTextDocument
from qtpy.QtWidgets import (QApplication, QComboBox, QMessageBox, QSizePolicy,
                            QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                            QTreeWidgetItem)

# Local imports
from spyder.api.translations import get_translation
from spyder.config.gui import get_font
from spyder.utils import icon_manager as ima
from spyder.utils.encoding import is_text_file, to_unicode_from_fs
from spyder.utils.palette import SpyderPalette
from spyder.widgets.onecolumntree import OneColumnTree

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
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

# These additional pixels account for operating system spacing differences
EXTRA_BUTTON_PADDING = 10


# --- Utils
# ----------------------------------------------------------------------------
def truncate_path(text):
    ellipsis = '...'
    part_len = (MAX_PATH_LENGTH - len(ellipsis)) / 2.0
    left_text = text[:int(math.ceil(part_len))]
    right_text = text[-int(math.floor(part_len)):]
    return left_text + ellipsis + right_text


class SearchThread(QThread):
    """Find in files search thread."""
    PYTHON_EXTENSIONS = ['.py', '.pyw', '.pyx', '.ipy', '.pyi', '.pyt']

    USEFUL_EXTENSIONS = [
        '.ipynb', '.md',  '.c', '.cpp', '.h', '.cxx', '.f', '.f03', '.f90',
        '.json', '.dat', '.csv', '.tsv', '.txt', '.md', '.rst', '.yml',
        '.yaml', '.ini', '.bat', '.sh', '.ui'
    ]

    SKIPPED_EXTENSIONS = ['.svg']

    sig_finished = Signal(bool)
    sig_current_file = Signal(str)
    sig_current_folder = Signal(str)
    sig_file_match = Signal(object)
    sig_line_match = Signal(object, object)
    sig_out_print = Signal(object)

    # Batch power sizes (2**power)
    power = 0       # 0**1 = 1
    max_power = 9   # 2**9 = 512

    def __init__(self, parent, search_text, text_color):
        super().__init__(parent)
        self.mutex = QMutex()
        self.stopped = None
        self.search_text = search_text
        self.text_color = text_color
        self.pathlist = None
        self.total_matches = None
        self.error_flag = None
        self.rootpath = None
        self.exclude = None
        self.texts = None
        self.text_re = None
        self.completed = None
        self.case_sensitive = True
        self.total_matches = 0
        self.is_file = False
        self.results = {}

        self.num_files = 0
        self.files = []
        self.partial_results = []

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
                # For directories
                for d in dirs[:]:
                    with QMutexLocker(self.mutex):
                        if self.stopped:
                            return False

                    dirname = os.path.join(path, d)

                    # Only search in regular directories
                    st_dir_mode = os.stat(dirname).st_mode
                    if not stat.S_ISDIR(st_dir_mode):
                        dirs.remove(d)

                    if (self.exclude and
                            re.search(self.exclude, dirname + os.sep)):
                        # Exclude patterns defined by the user
                        dirs.remove(d)
                    elif d.startswith('.'):
                        # Exclude all dot dirs.
                        dirs.remove(d)

                # For files
                for f in files:
                    with QMutexLocker(self.mutex):
                        if self.stopped:
                            return False

                    filename = os.path.join(path, f)
                    ext = osp.splitext(filename)[1]

                    # Only search in regular files (i.e. not pipes)
                    st_file_mode = os.stat(filename).st_mode
                    if not stat.S_ISREG(st_file_mode):
                        continue

                    # Exclude patterns defined by the user
                    if self.exclude and re.search(self.exclude, filename):
                        continue

                    # Don't search in plain text files with skipped extensions
                    # (e.g .svg)
                    if ext in self.SKIPPED_EXTENSIONS:
                        continue

                    # It's much faster to check for extension first before
                    # validating if the file is plain text.
                    if (ext in self.PYTHON_EXTENSIONS or
                            ext in self.USEFUL_EXTENSIONS or
                            is_text_file(filename)):
                        self.find_string_in_file(filename)
            except re.error:
                self.error_flag = _("invalid regular expression")
                return False

        # Process any pending results
        if self.partial_results:
            self.process_results()

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
                        bstart, bend = match.start(), match.end()
                        try:
                            # Go from binary position to utf8 position
                            start = len(line[:bstart].decode(enc))
                            end = start + len(line[bstart:bend].decode(enc))
                        except UnicodeDecodeError:
                            start = bstart
                            end = bend
                        self.partial_results.append((osp.abspath(fname),
                                                     lineno + 1,
                                                     start,
                                                     end,
                                                     line_dec))
                        if len(self.partial_results) > (2**self.power):
                            self.process_results()
                            if self.power < self.max_power:
                                self.power += 1
                else:
                    found = line.find(text)
                    while found > -1:
                        with QMutexLocker(self.mutex):
                            if self.stopped:
                                return False
                        self.total_matches += 1
                        try:
                            # Go from binary position to utf8 position
                            start = len(line[:found].decode(enc))
                            end = start + len(text.decode(enc))
                        except UnicodeDecodeError:
                            start = found
                            end = found + len(text)

                        self.partial_results.append((osp.abspath(fname),
                                                     lineno + 1,
                                                     start,
                                                     end,
                                                     line_dec))
                        if len(self.partial_results) > (2**self.power):
                            self.process_results()
                            if self.power < self.max_power:
                                self.power += 1

                        for text, enc in self.texts:
                            found = line.find(text, found + 1)
                            if found > -1:
                                break

        except IOError as xxx_todo_changeme:
            (_errno, _strerror) = xxx_todo_changeme.args
            self.error_flag = _("permission denied errors were encountered")

        self.completed = True

    def process_results(self):
        """
        Process all matches found inside a file.

        Creates the necessary files and emits signal for the creation of file
        item.

        Creates the necessary data for lines found and emits signal for the
        creation of line items in batch.

        Creates the title based on the last entry of the lines batch.
        """
        items = []
        num_matches = self.total_matches
        for result in self.partial_results:
            filename, lineno, colno, match_end, line = result

            if filename not in self.files:
                self.files.append(filename)
                self.sig_file_match.emit(filename)
                self.num_files += 1

            line = self.truncate_result(line, colno, match_end)
            item = (filename, lineno, colno, line, match_end)
            items.append(item)

        # Process title
        title = "'%s' - " % self.search_text
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
        title = title + text

        self.partial_results = []
        self.sig_line_match.emit(items, title)

    def truncate_result(self, line, start, end):
        """
        Shorten text on line to display the match within `max_line_length`.
        """
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

        line = str(line)
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

        left = html_escape(left)
        right = html_escape(right)
        match = html_escape(match)

        match_color = SpyderPalette.COLOR_OCCURRENCE_4
        trunc_line = (
            f'<span style="color:{self.text_color}">'
            f'{left}'
            f'<span style="background-color:{match_color}">{match}</span>'
            f'{right}'
            f'</span>'
        )

        return trunc_line

    def get_results(self):
        return self.results, self.pathlist, self.total_matches, self.error_flag


# --- Widgets
# ----------------------------------------------------------------------------
class SearchInComboBox(QComboBox):
    """
    Non editable combo box handling the path locations of the FindOptions
    widget.
    """

    # Signals
    sig_redirect_stdio_requested = Signal(bool)

    def __init__(self, external_path_history=[], parent=None, id_=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(_('Search directory'))
        self.setEditable(False)

        self.path = ''
        self.project_path = None
        self.file_path = None
        self.external_path = None

        if id_ is not None:
            self.ID = id_

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
        return [str(self.itemText(i))
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

    def set_current_searchpath_index(self, index):
        """Set the current index of this combo box."""
        if index is not None:
            index = min(index, self.count() - 1)
            index = CWD if index in [CLEAR_LIST, SELECT_OTHER] else index
        else:
            index = CWD

        self.setCurrentIndex(index)

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
            self.external_path = str(self.itemText(idx))

    @Slot()
    def select_directory(self):
        """Select directory"""
        self.sig_redirect_stdio_requested.emit(False)
        directory = getexistingdirectory(
            self,
            _("Select directory"),
            self.path,
        )
        if directory:
            directory = to_unicode_from_fs(osp.abspath(directory))

        self.sig_redirect_stdio_requested.emit(True)
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


class LineMatchItem(QTreeWidgetItem):

    def __init__(self, parent, lineno, colno, match, font, text_color):
        self.lineno = lineno
        self.colno = colno
        self.match = match
        self.text_color = text_color
        self.font = font
        super().__init__(parent, [self.__repr__()], QTreeWidgetItem.Type)

    def __repr__(self):
        match = str(self.match).rstrip()
        _str = (
            f"<!-- LineMatchItem -->"
            f"<p style=\"color:'{self.text_color}';\">"
            f"<b>{self.lineno}</b> ({self.colno}): "
            f"<span style='font-family:{self.font.family()};"
            f"font-size:{self.font.pointSize()}pt;'>{match}</span></p>"
        )
        return _str

    def __unicode__(self):
        return self.__repr__()

    def __str__(self):
        return self.__repr__()

    def __lt__(self, x):
        return self.lineno < x.lineno

    def __ge__(self, x):
        return self.lineno >= x.lineno


class FileMatchItem(QTreeWidgetItem):

    def __init__(self, parent, path, filename, sorting, text_color):

        self.sorting = sorting
        self.filename = osp.basename(filename)

        # Get relative dirname according to the path we're searching in.
        dirname = osp.dirname(filename)
        rel_dirname = dirname.split(path)[1]
        if rel_dirname.startswith(osp.sep):
            rel_dirname = rel_dirname[1:]

        title = (
            f'<!-- FileMatchItem -->'
            f'<b style="color:{text_color}">{osp.basename(filename)}</b>'
            f'&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{text_color}">'
            f'<em>{rel_dirname}</em>'
            f'</span>'
        )

        super().__init__(parent, [title], QTreeWidgetItem.Type)

        self.setIcon(0, ima.get_icon_by_extension_or_type(filename, 1.0))
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
        super().__init__(parent)
        self._margin = None

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        text = options.text
        doc.setHtml(text)
        doc.setDocumentMargin(0)

        # This needs to be an empty string to avoid the overlapping the
        # normal text of the QTreeWidgetItem
        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText,
                                        options, None)
        painter.save()

        painter.translate(textRect.topLeft() + QPoint(0, 4))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSize(int(doc.idealWidth()), int(doc.size().height()))
        return size


class ResultsBrowser(OneColumnTree):
    sig_edit_goto_requested = Signal(str, int, str, int, int)
    sig_max_results_reached = Signal()

    def __init__(self, parent, text_color, max_results=1000):
        super().__init__(parent)
        self.search_text = None
        self.results = None
        self.max_results = max_results
        self.total_matches = None
        self.error_flag = None
        self.completed = None
        self.sorting = {}
        self.font = get_font()
        self.data = None
        self.files = None
        self.root_items = None
        self.text_color = text_color
        self.path = None

        # Setup
        self.set_title('')
        self.set_sorting(OFF)
        self.setSortingEnabled(False)
        self.setItemDelegate(ItemDelegate(self))
        self.setUniformRowHeights(True)  # Needed for performance
        self.sortByColumn(0, Qt.AscendingOrder)

        # Only show the actions for collaps/expand all entries in the widget
        # For further information see spyder-ide/spyder#13178
        self.common_actions = self.common_actions[:2]

        # Signals
        self.header().sectionClicked.connect(self.sort_section)

    def activated(self, item):
        """Double-click event."""
        itemdata = self.data.get(id(self.currentItem()))
        if itemdata is not None:
            filename, lineno, colno, colend = itemdata
            self.sig_edit_goto_requested.emit(
                filename, lineno, self.search_text, colno, colend - colno)

    def set_sorting(self, flag):
        """Enable result sorting after search is complete."""
        self.sorting['status'] = flag
        self.header().setSectionsClickable(flag == ON)

    @Slot(int)
    def sort_section(self, idx):
        self.setSortingEnabled(True)

    def clicked(self, item):
        """Click event."""
        self.activated(item)

    def clear_title(self, search_text):
        self.font = get_font()
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

    @Slot(object)
    def append_file_result(self, filename):
        """Real-time update of file items."""
        if len(self.data) < self.max_results:
            self.files[filename] = FileMatchItem(self, self.path, filename,
                                                 self.sorting, self.text_color)
            self.files[filename].setExpanded(True)
            self.num_files += 1

    @Slot(object, object)
    def append_result(self, items, title):
        """Real-time update of line items."""
        if len(self.data) >= self.max_results:
            self.set_title(_('Maximum number of results reached! Try '
                             'narrowing the search.'))
            self.sig_max_results_reached.emit()
            return

        available = self.max_results - len(self.data)
        if available < len(items):
            items = items[:available]

        self.setUpdatesEnabled(False)
        self.set_title(title)
        for item in items:
            filename, lineno, colno, line, match_end = item
            file_item = self.files.get(filename, None)
            if file_item:
                item = LineMatchItem(file_item, lineno, colno, line,
                                     self.font, self.text_color)
                self.data[id(item)] = (filename, lineno, colno, match_end)
        self.setUpdatesEnabled(True)

    def set_max_results(self, value):
        """Set maximum amount of results to add."""
        self.max_results = value

    def set_path(self, path):
        """Set path where the search is performed."""
        self.path = path
