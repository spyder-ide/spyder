# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Search thread."""

# Standard library imports
import os
import os.path as osp
import re
import stat
import traceback

# Third party imports
from qtpy.QtCore import QMutex, QMutexLocker, QThread, Signal

# Local imports
from spyder.api.translations import _
from spyder.utils.encoding import is_text_file
from spyder.utils.palette import SpyderPalette


# ---- Constants
# ----------------------------------------------------------------------------
ELLIPSIS = '...'
MAX_RESULT_LENGTH = 80
MAX_NUM_CHAR_FRAGMENT = 40


# ---- Thread
# ----------------------------------------------------------------------------
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

    def __init__(self, parent, search_text, text_color, max_results=1000):
        super().__init__(parent)
        self.search_text = search_text
        self.text_color = text_color
        self.max_results = max_results

        self.mutex = QMutex()
        self.stopped = None
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
        self.total_items = 0

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

                    # Only search in regular files (i.e. not pipes).
                    # The try/except is necessary to catch an error when
                    # Python can't get the file status due to too many levels
                    # of symbolic links.
                    # Fixes spyder-ide/spyder#20798
                    try:
                        st_file_mode = os.stat(filename).st_mode
                        if not stat.S_ISREG(st_file_mode):
                            continue
                    except OSError:
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
            except FileNotFoundError:
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

        # Process any pending results
        if self.is_file and self.partial_results:
            self.process_results()

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
            if self.total_items < self.max_results:
                filename, lineno, colno, match_end, line = result

                if filename not in self.files:
                    self.files.append(filename)
                    self.sig_file_match.emit(filename)
                    self.num_files += 1

                line = self.truncate_result(line, colno, match_end)
                item = (filename, lineno, colno, line, match_end)
                items.append(item)
                self.total_items += 1

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

        if len(line) > MAX_RESULT_LENGTH:
            offset = (len(line) - len(match)) // 2

            left = left.split(' ')
            num_left_words = len(left)

            if num_left_words == 1:
                left = left[0]
                if len(left) > MAX_NUM_CHAR_FRAGMENT:
                    left = ELLIPSIS + left[-offset:]
                left = [left]

            right = right.split(' ')
            num_right_words = len(right)

            if num_right_words == 1:
                right = right[0]
                if len(right) > MAX_NUM_CHAR_FRAGMENT:
                    right = right[:offset] + ELLIPSIS
                right = [right]

            left = left[-4:]
            right = right[:4]

            if len(left) < num_left_words:
                left = [ELLIPSIS] + left

            if len(right) < num_right_words:
                right = right + [ELLIPSIS]

            left = ' '.join(left)
            right = ' '.join(right)

            if len(left) > MAX_NUM_CHAR_FRAGMENT:
                left = ELLIPSIS + left[-30:]

            if len(right) > MAX_NUM_CHAR_FRAGMENT:
                right = right[:30] + ELLIPSIS

        match_color = SpyderPalette.COLOR_OCCURRENCE_4
        trunc_line = dict(
            text=''.join([left, match, right]),
            formatted_text=(
                f'<span style="color:{self.text_color}">'
                f'{html_escape(left)}'
                f'<span style="background-color:{match_color}">'
                f'{html_escape(match)}'
                f'</span>'
                f'{html_escape(right)}'
                f'</span>'
            )
        )

        return trunc_line

    def get_results(self):
        return self.results, self.pathlist, self.total_matches, self.error_flag
