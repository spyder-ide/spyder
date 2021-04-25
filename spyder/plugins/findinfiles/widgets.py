# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Find in files widget.
"""

# Standard library imports
import fnmatch
import math
import os
import os.path as osp
import re
import traceback

# Third party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import (QEvent, QMutex, QMutexLocker, QSize, Qt, QThread,
                         Signal, Slot)
from qtpy.QtGui import QAbstractTextDocumentLayout, QTextDocument
from qtpy.QtWidgets import (QApplication, QComboBox, QHBoxLayout,
                            QInputDialog, QLabel, QMessageBox, QSizePolicy,
                            QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                            QTreeWidgetItem)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.gui import get_font
from spyder.utils.encoding import is_text_file, to_unicode_from_fs
from spyder.utils.misc import regexp_error_msg
from spyder.utils.palette import SpyderPalette, QStylePalette
from spyder.widgets.comboboxes import PatternComboBox
# TODO: Use SpyderWidgetMixin on OneColumnTree
from spyder.widgets.onecolumntree import OneColumnTree

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
MAIN_TEXT_COLOR = QStylePalette.COLOR_TEXT_1

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


class FindInFilesWidgetActions:
    # Triggers
    Find = 'find_action'
    MaxResults = 'max_results_action'

    # Toggles
    ToggleCase = 'toggle_case_action'
    ToggleExcludeCase = 'toggle_exclude_case_action'
    ToggleExcludeRegex = 'togle_use_regex_on_exlude_action'
    ToggleMoreOptions = 'toggle_more_options_action'
    ToggleSearchRegex = 'toggle_use_regex_on_search_action'


class FindInFilesWidgetToolbars:
    Exclude = 'exclude_toolbar'
    Location = 'location_toolbar'


class FindInFilesWidgetMainToolbarSections:
    Main = 'main_section'


class FindInFilesWidgetExcludeToolbarSections:
    Main = 'main_section'


class FindInFilesWidgetLocationToolbarSections:
    Main = 'main_section'


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
    sig_finished = Signal(bool)
    sig_current_file = Signal(str)
    sig_current_folder = Signal(str)
    sig_file_match = Signal(object)
    sig_line_match = Signal(object, object)
    sig_out_print = Signal(object)

    # Batch power sizes (2**power)
    power = 0       # 0**1 = 1
    max_power = 9   # 2**9 = 512

    def __init__(self, parent, search_text, text_color=None):
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

        line_match_format = ('<span style="color:{0}">{{0}}'
                             '<b>{{1}}</b>{{2}}</span>')
        line_match_format = line_match_format.format(self.text_color)

        left = html_escape(left)
        right = html_escape(right)
        match = html_escape(match)
        trunc_line = line_match_format.format(left, match, right)
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

    def __init__(self, external_path_history=[], parent=None):
        super().__init__(parent)
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

    def __init__(self, parent, lineno, colno, match, font,
                 text_color=None):
        self.lineno = lineno
        self.colno = colno
        self.match = match
        self.text_color = text_color
        self.font = font
        super().__init__(parent, [self.__repr__()], QTreeWidgetItem.Type)

    def __repr__(self):
        match = str(self.match).rstrip()
        _str = ("<!-- LineMatchItem -->"
                "<p style=\"color:'{4}';\"><b>{1}</b> ({2}): "
                "<span style='font-family:{0};"
                "font-size:75%;'>{3}</span></p>")
        return _str.format(self.font.family(), self.lineno, self.colno, match,
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

        title_format = ('<!-- FileMatchItem -->'
                        '<b style="color:{2}">{0}</b>'
                        '&nbsp;&nbsp;&nbsp;'
                        '<small style="color:{2}"><em>{1}</em>'
                        '</small>')
        title = (title_format.format(osp.basename(filename),
                                     osp.dirname(filename),
                                     text_color))
        super().__init__(parent, [title], QTreeWidgetItem.Type)

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
        size = QSize(int(doc.idealWidth()), int(doc.size().height()))
        return size


class ResultsBrowser(OneColumnTree):
    sig_edit_goto_requested = Signal(str, int, str, int, int)
    sig_max_results_reached = Signal()

    def __init__(self, parent, text_color=None, max_results=1000):
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
            self.files[filename] = FileMatchItem(
                self, filename, self.sorting, self.text_color)
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


class FindInFilesWidget(PluginMainWidget):
    """
    Find in files widget.
    """

    ENABLE_SPINNER = True
    REGEX_INVALID = f"background-color:{SpyderPalette.COLOR_ERROR_2};"
    REGEX_ERROR = _("Regular expression error")

    # Signals
    sig_edit_goto_requested = Signal(str, int, str, int, int)
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
    start_column: int
        Starting column of found word.
    end_column:
        Ending column of found word.
    """

    sig_finished = Signal()
    """
    This signal is emitted to inform the search process has finished.
    """

    sig_max_results_reached = Signal()
    """
    This signal is emitted to inform the search process has finished due
    to reaching the maximum number of results.
    """

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent=parent)
        self.set_conf('text_color', MAIN_TEXT_COLOR)
        self.set_conf('hist_limit', MAX_PATH_HISTORY)

        # Attributes
        self.text_color = self.get_conf('text_color')
        self.supported_encodings = self.get_conf('supported_encodings')
        self.search_thread = None
        self.running = False
        self.more_options_action = None
        self.extras_toolbar = None

        search_text = self.get_conf('search_text', '')
        path_history = self.get_conf('path_history', [])
        exclude = self.get_conf('exclude')

        if not isinstance(search_text, (list, tuple)):
            search_text = [search_text]

        if not isinstance(exclude, (list, tuple)):
            exclude = [exclude]

        if not isinstance(path_history, (list, tuple)):
            path_history = [path_history]

        # Widgets
        self.search_text_edit = PatternComboBox(
            self,
            search_text,
            _("Search pattern"),
        )
        self.search_in_label = QLabel(_('Search in:'))
        self.exclude_label = QLabel(_('Exclude:'))
        self.path_selection_combo = SearchInComboBox(path_history, self)
        self.exclude_pattern_edit = PatternComboBox(
            self,
            exclude,
            _("Exclude pattern"),
        )
        self.result_browser = ResultsBrowser(
            self,
            text_color=self.text_color,
            max_results=self.get_conf('max_results'),
        )

        # Setup
        self.exclude_label.setBuddy(self.exclude_pattern_edit)
        exclude_idx = self.get_conf('exclude_index', None)
        if (exclude_idx is not None and exclude_idx >= 0
                and exclude_idx < self.exclude_pattern_edit.count()):
            self.exclude_pattern_edit.setCurrentIndex(exclude_idx)

        search_in_index = self.get_conf('search_in_index', None)
        self.path_selection_combo.set_current_searchpath_index(
            search_in_index)

        # Layout
        layout = QHBoxLayout()
        layout.addWidget(self.result_browser)
        self.setLayout(layout)

        # Signals
        self.path_selection_combo.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)
        self.search_text_edit.valid.connect(lambda valid: self.find())
        self.exclude_pattern_edit.valid.connect(lambda valid: self.find())
        self.result_browser.sig_edit_goto_requested.connect(
            self.sig_edit_goto_requested)
        self.result_browser.sig_max_results_reached.connect(
            self.sig_max_results_reached)
        self.result_browser.sig_max_results_reached.connect(
            self._stop_and_reset_thread)
        self.search_text_edit.sig_resized.connect(self._update_size)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _("Find")

    def get_focus_widget(self):
        return self.search_text_edit

    def setup(self):
        self.search_regexp_action = self.create_action(
            FindInFilesWidgetActions.ToggleSearchRegex,
            text=_('Regular expression'),
            tip=_('Regular expression'),
            icon=self.create_icon('regex'),
            toggled=True,
            initial=self.get_conf('search_text_regexp'),
            option='search_text_regexp'
        )
        self.case_action = self.create_action(
            FindInFilesWidgetActions.ToggleExcludeCase,
            text=_("Case sensitive"),
            tip=_("Case sensitive"),
            icon=self.create_icon("format_letter_case"),
            toggled=True,
            initial=self.get_conf('case_sensitive'),
            option='case_sensitive'
        )
        self.find_action = self.create_action(
            FindInFilesWidgetActions.Find,
            text=_("&Find in files"),
            tip=_("Search text in multiple files"),
            icon=self.create_icon('find'),
            triggered=self.find,
            register_shortcut=False,
        )
        self.exclude_regexp_action = self.create_action(
            FindInFilesWidgetActions.ToggleExcludeRegex,
            text=_('Regular expression'),
            tip=_('Regular expression'),
            icon=self.create_icon('regex'),
            toggled=True,
            initial=self.get_conf('exclude_regexp'),
            option='exclude_regexp'
        )
        self.exclude_case_action = self.create_action(
            FindInFilesWidgetActions.ToggleCase,
            text=_("Exclude case sensitive"),
            tip=_("Exclude case sensitive"),
            icon=self.create_icon("format_letter_case"),
            toggled=True,
            initial=self.get_conf('exclude_case_sensitive'),
            option='exclude_case_sensitive'
        )
        self.more_options_action = self.create_action(
            FindInFilesWidgetActions.ToggleMoreOptions,
            text=_('Show advanced options'),
            tip=_('Show advanced options'),
            icon=self.create_icon("options_more"),
            toggled=True,
            initial=self.get_conf('more_options'),
            option='more_options'
        )
        self.set_max_results_action = self.create_action(
            FindInFilesWidgetActions.MaxResults,
            text=_('Set maximum number of results'),
            tip=_('Set maximum number of results'),
            triggered=lambda x=None: self.set_max_results(),
        )

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.search_text_edit, self.search_regexp_action,
                     self.case_action, self.more_options_action,
                     self.find_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=FindInFilesWidgetMainToolbarSections.Main,
            )

        # Exclude Toolbar
        self.extras_toolbar = self.create_toolbar(
            FindInFilesWidgetToolbars.Exclude)
        for item in [self.exclude_label, self.exclude_pattern_edit,
                     self.exclude_regexp_action, self.create_stretcher()]:
            self.add_item_to_toolbar(
                item,
                toolbar=self.extras_toolbar,
                section=FindInFilesWidgetExcludeToolbarSections.Main,
            )

        # Location toolbar
        location_toolbar = self.create_toolbar(
            FindInFilesWidgetToolbars.Location)
        for item in [self.search_in_label, self.path_selection_combo]:
            self.add_item_to_toolbar(
                item,
                toolbar=location_toolbar,
                section=FindInFilesWidgetLocationToolbarSections.Main,
            )

        menu = self.get_options_menu()
        self.add_item_to_menu(
            self.set_max_results_action,
            menu=menu,
        )

    def update_actions(self):
        self.find_action.setIcon(self.create_icon(
            'stop' if self.running else 'find'))

        if self.extras_toolbar and self.more_options_action:
            self.extras_toolbar.setVisible(
                self.more_options_action.isChecked())

    @on_conf_change(option='more_options')
    def on_more_options_update(self, value):
        self.exclude_pattern_edit.setMinimumWidth(
            self.search_text_edit.width())

        if value:
            icon = self.create_icon('options_less')
            tip = _('Hide advanced options')
        else:
            icon = self.create_icon('options_more')
            tip = _('Show advanced options')

        if self.extras_toolbar:
            self.extras_toolbar.setVisible(value)

        if self.more_options_action:
            self.more_options_action.setIcon(icon)
            self.more_options_action.setToolTip(tip)

    @on_conf_change(option='max_results')
    def on_max_results_update(self, value):
        self.result_browser.set_max_results(value)

    # --- Private API
    # ------------------------------------------------------------------------
    def _update_size(self, size, old_size):
        self.exclude_pattern_edit.setMinimumWidth(size.width())

    def _get_options(self):
        """
        Get search options.
        """
        text_re = self.search_regexp_action.isChecked()
        exclude_re = self.exclude_regexp_action.isChecked()
        case_sensitive = self.case_action.isChecked()

        # Clear fields
        self.search_text_edit.lineEdit().setStyleSheet("")
        self.exclude_pattern_edit.lineEdit().setStyleSheet("")
        self.exclude_pattern_edit.setToolTip("")
        self.search_text_edit.setToolTip("")

        utext = str(self.search_text_edit.currentText())
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

        exclude = str(self.exclude_pattern_edit.currentText())

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
                exclude_edit = self.exclude_pattern_edit.lineEdit()
                exclude_edit.setStyleSheet(self.REGEX_INVALID)
                tooltip = self.REGEX_ERROR + ': ' + str(error_msg)
                self.exclude_pattern_edit.setToolTip(tooltip)
                return None
            else:
                exclude = re.compile(exclude)

        # Validate text regular expression
        if text_re:
            error_msg = regexp_error_msg(texts[0][0])
            if error_msg:
                self.search_text_edit.lineEdit().setStyleSheet(
                    self.REGEX_INVALID)
                tooltip = self.REGEX_ERROR + ': ' + str(error_msg)
                self.search_text_edit.setToolTip(tooltip)
                return None
            else:
                texts = [(re.compile(x[0]), x[1]) for x in texts]

        return (path, file_search, exclude, texts, text_re, case_sensitive)

    def _update_options(self):
        """
        Extract search options from widgets and set the corresponding option.
        """
        hist_limit = self.get_conf('hist_limit')
        search_texts = [str(self.search_text_edit.itemText(index))
                        for index in range(self.search_text_edit.count())]
        excludes = [str(self.exclude_pattern_edit.itemText(index))
                    for index in range(self.exclude_pattern_edit.count())]
        path_history = self.path_selection_combo.get_external_paths()

        self.set_conf('path_history', path_history)
        self.set_conf('search_text', search_texts[:hist_limit])
        self.set_conf('exclude', excludes[:hist_limit])
        self.set_conf('path_history', path_history[-hist_limit:])
        self.set_conf(
            'exclude_index', self.exclude_pattern_edit.currentIndex())
        self.set_conf(
            'search_in_index', self.path_selection_combo.currentIndex())

    def _handle_search_complete(self, completed):
        """
        Current search thread has finished.
        """
        self.result_browser.set_sorting(ON)
        self.result_browser.expandAll()
        if self.search_thread is None:
            return

        self.sig_finished.emit()
        found = self.search_thread.get_results()
        self._stop_and_reset_thread()
        if found is not None:
            self.result_browser.show()

        self.stop_spinner()
        self.update_actions()

    def _stop_and_reset_thread(self, ignore_results=False):
        """Stop current search thread and clean-up."""
        if self.search_thread is not None:
            if self.search_thread.isRunning():
                if ignore_results:
                    self.search_thread.sig_finished.disconnect(
                        self.search_complete)
                self.search_thread.stop()
                self.search_thread.wait()

            self.search_thread.setParent(None)
            self.search_thread = None

        self.running = False
        self.stop_spinner()
        self.update_actions()

    # --- Public API
    # ------------------------------------------------------------------------
    @property
    def path(self):
        """Return the current path."""
        return self.path_selection_combo.path

    @property
    def project_path(self):
        """Return the current project path."""
        return self.path_selection_combo.project_path

    @property
    def file_path(self):
        """Return the current file path."""
        return self.path_selection_combo.file_path

    def set_directory(self, directory):
        """
        Set directory as current path.

        Parameters
        ----------
        directory: str
            Directory path string.
        """
        self.path_selection_combo.path = osp.abspath(directory)

    def set_project_path(self, path):
        """
        Set path as current project path.

        Parameters
        ----------
        path: str
            Project path string.
        """
        self.path_selection_combo.set_project_path(path)

    def disable_project_search(self):
        """Disable project search path in combobox."""
        self.path_selection_combo.set_project_path(None)

    def set_file_path(self, path):
        """
        Set path as current file path.

        Parameters
        ----------
        path: str
            File path string.
        """
        self.path_selection_combo.file_path = path

    def set_search_text(self, text):
        """
        Set current search text.

        Parameters
        ----------
        text: str
            Search string.

        Notes
        -----
        If `text` is empty, focus will be given to the search lineedit and no
        search will be performed.
        """
        if text:
            self.search_text_edit.add_text(text)
            self.search_text_edit.lineEdit().selectAll()

        self.search_text_edit.setFocus()

    def find(self):
        """
        Start/stop find action.

        Notes
        -----
        If there is no search running, this will start the search. If there is
        a search running, this will stop it.
        """
        if self.running:
            self.stop()
        else:
            self.start()

    def stop(self):
        """Stop find thread."""
        self._stop_and_reset_thread()

    def start(self):
        """Start find thread."""
        options = self._get_options()
        if options is None:
            return

        self._stop_and_reset_thread(ignore_results=True)
        search_text = self.search_text_edit.currentText()

        # Update and set options
        self._update_options()

        # Start
        self.running = True
        self.start_spinner()
        self.search_thread = SearchThread(self, search_text, self.text_color)
        self.search_thread.sig_finished.connect(self._handle_search_complete)
        self.search_thread.sig_file_match.connect(
            self.result_browser.append_file_result
        )
        self.search_thread.sig_line_match.connect(
            self.result_browser.append_result
        )
        self.result_browser.clear_title(search_text)
        self.search_thread.initialize(*self._get_options())
        self.search_thread.start()
        self.update_actions()

    def add_external_path(self, path):
        """
        Parameters
        ----------
        path: str
            Path to add to combobox.
        """
        self.path_selection_combo.add_external_path(path)

    def set_max_results(self, value=None):
        """
        Set maximum amount of results to add to the result browser.

        Parameters
        ----------
        value: int, optional
            Number of results. If None an input dialog will be used.
            Default is None.
        """
        if value is None:
            # Create dialog
            dialog = QInputDialog(self)

            # Set dialog properties
            dialog.setModal(False)
            dialog.setWindowTitle(self.get_name())
            dialog.setLabelText(_('Set maximum number of results: '))
            dialog.setInputMode(QInputDialog.IntInput)
            dialog.setIntRange(1, 10000)
            dialog.setIntStep(1)
            dialog.setIntValue(self.get_conf('max_results'))

            # Connect slot
            dialog.intValueSelected.connect(
                lambda value: self.set_conf('max_results', value))

            dialog.show()
        else:
            self.set_conf('max_results', value)


def test():
    """
    Run Find in Files widget test.
    """
    # Standard library imports
    from os.path import dirname
    import sys
    from unittest.mock import MagicMock

    # Local imports
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'find_in_files'
    widget = FindInFilesWidget('find_in_files', plugin=plugin_mock)
    widget.CONF_SECTION = 'find_in_files'
    widget._setup()
    widget.setup()
    widget.resize(640, 480)
    widget.show()
    external_paths = [
        dirname(__file__),
        dirname(dirname(__file__)),
        dirname(dirname(dirname(__file__))),
        dirname(dirname(dirname(dirname(__file__)))),
    ]
    for path in external_paths:
        widget.add_external_path(path)

    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
