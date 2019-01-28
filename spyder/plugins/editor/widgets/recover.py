# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dialog window for recovering files from autosave"""

# Standard library imports
from os import path as osp
import os
import shutil
import time

# Third party imports
from qtpy.compat import getsavefilename
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                            QMessageBox, QPushButton, QTableWidget,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _, running_under_pytest


def gather_file_data(name):
    """
    Gather data about a given file.

    Returns a dict with fields name, mtime and size, containing the relevant
    data for the fiel.
    """
    res = {'name': name}
    try:
        res['mtime'] = osp.getmtime(name)
        res['size'] = osp.getsize(name)
    except OSError:
        pass
    return res


def file_data_to_str(data):
    """
    Convert file data to a string for display.

    This function takes the file data produced by gather_file_data().
    """
    if not data:
        return _('<i>File name not recorded</i>')
    res = data['name']
    try:
        mtime_as_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                     time.localtime(data['mtime']))
        res += '<br><i>{}</i>: {}'.format(_('Last modified'), mtime_as_str)
        res += '<br><i>{}</i>: {} {}'.format(
                _('Size'), data['size'], _('bytes'))
    except KeyError:
        res += '<br>' + _('<i>File no longer exists</i>')
    return res


def recovery_data_key_function(item):
    """
    Convert item in `RecoveryDialog.data` to tuple so that it can be sorted.

    Sorting the tuples returned by this function will sort first by name of
    the original file, then by name of the autosave file. All items without an
    original file name will be at the end.
    """
    orig_dict, autosave_dict = item
    if orig_dict:
        return (0, orig_dict['name'], autosave_dict['name'])
    else:
        return (1, 0, autosave_dict['name'])


class RecoveryDialog(QDialog):
    def __init__(self, autosave_dir, autosave_mapping, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.setSpacing(self.layout.spacing() * 3)
        self.autosave_dir = autosave_dir
        self.autosave_mapping = autosave_mapping
        self.files_to_open = []
        self.gather_data()
        self.add_label()
        self.add_table()
        self.add_cancel_button()
        self.setWindowTitle(_('Recover from autosave'))

    def gather_data(self):
        """
        Gather data about files which may be recovered.

        The data is stored in self.data as a list of tuples with the data
        pertaining to the original file and the autosave file. Each element of
        the tuple is a dict as returned by gather_file_data().
        """
        self.data = []
        try:
            FileNotFoundError
        except NameError:  # Python 2
            FileNotFoundError = OSError
        # In Python 3, easier to use os.scandir()
        try:
            for name in os.listdir(self.autosave_dir):
                full_name = osp.join(self.autosave_dir, name)
                if osp.isdir(full_name):
                    continue
                for orig, autosave in self.autosave_mapping.items():
                    if autosave == full_name:
                        orig_dict = gather_file_data(orig)
                        break
                else:
                    orig_dict = None
                autosave_dict = gather_file_data(full_name)
                self.data.append((orig_dict, autosave_dict))
        except FileNotFoundError:  # autosave dir does not exist
            pass
        self.data.sort(key=recovery_data_key_function)
        self.num_enabled = len(self.data)

    def add_label(self):
        """Add label with explanation at top of dialog window."""
        txt = _('Autosave files found. What would you like to do?\n\n'
                'This dialog will be shown again on next startup if any '
                'autosave files are not restored, moved or deleted.')
        label = QLabel(txt, self)
        label.setWordWrap(True)
        self.layout.addWidget(label)

    def add_label_to_table(self, row, col, txt):
        """Add a label to specified cell in table."""
        label = QLabel(txt)
        label.setMargin(5)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setCellWidget(row, col, label)

    def add_table(self):
        """Add table with info about files to be recovered."""
        table = QTableWidget(len(self.data), 3, self)
        self.table = table

        labels = [_('Original file'), _('Autosave file'), _('Actions')]
        table.setHorizontalHeaderLabels(labels)
        table.verticalHeader().hide()

        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setSelectionMode(QTableWidget.NoSelection)

        # Show horizontal grid lines
        table.setShowGrid(False)
        table.setStyleSheet('::item { border-bottom: 1px solid gray }')

        for idx, (original, autosave) in enumerate(self.data):
            self.add_label_to_table(idx, 0, file_data_to_str(original))
            self.add_label_to_table(idx, 1, file_data_to_str(autosave))

            widget = QWidget()
            layout = QHBoxLayout()

            tooltip = _('Recover the autosave file to its original location, '
                        'replacing the original if it exists.')
            button = QPushButton(_('Restore'))
            button.setToolTip(tooltip)
            button.clicked.connect(
                    lambda checked, my_idx=idx: self.restore(my_idx))
            layout.addWidget(button)

            tooltip = _('Delete the autosave file.')
            button = QPushButton(_('Discard'))
            button.setToolTip(tooltip)
            button.clicked.connect(
                    lambda checked, my_idx=idx: self.discard(my_idx))
            layout.addWidget(button)

            tooltip = _('Display the autosave file (and the original, if it '
                        'exists) in Spyder\'s Editor. You will have to move '
                        'or delete it manually.')
            button = QPushButton(_('Open'))
            button.setToolTip(tooltip)
            button.clicked.connect(
                    lambda checked, my_idx=idx: self.open_files(my_idx))
            layout.addWidget(button)

            widget.setLayout(layout)
            self.table.setCellWidget(idx, 2, widget)

        table.resizeRowsToContents()
        table.resizeColumnsToContents()

        # Need to add the "+ 2" because otherwise the table scrolls a tiny
        # amount; no idea why
        width = table.horizontalHeader().length() + 2
        height = (table.verticalHeader().length()
                  + table.horizontalHeader().height() + 2)
        table.setFixedSize(width, height)
        self.layout.addWidget(table)

    def add_cancel_button(self):
        """Add a cancel button at the bottom of the dialog window."""
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def restore(self, idx):
        orig, autosave = self.data[idx]
        if orig:
            orig_name = orig['name']
        else:
            orig_name, ignored = getsavefilename(
                self, _('Restore autosave file to ...'),
                osp.basename(autosave['name']))
            if not orig_name:
                return
        try:
            try:
                os.replace(autosave['name'], orig_name)
            except (AttributeError, OSError):
                # os.replace() does not exist on Python 2 and fails if the
                # files are on different file systems (issue #8631)
                shutil.copy2(autosave['name'], orig_name)
                os.remove(autosave['name'])
            self.deactivate(idx)
        except EnvironmentError as error:
            text = (_('Unable to restore {} using {}')
                    .format(orig_name, autosave['name']))
            self.report_error(text, error)

    def discard(self, idx):
        ignored, autosave = self.data[idx]
        try:
            os.remove(autosave['name'])
            self.deactivate(idx)
        except EnvironmentError as error:
            text = _('Unable to discard {}').format(autosave['name'])
            self.report_error(text, error)

    def open_files(self, idx):
        orig, autosave = self.data[idx]
        if orig:
            self.files_to_open.append(orig['name'])
        self.files_to_open.append(autosave['name'])
        self.deactivate(idx)

    def report_error(self, text, error):
        heading = _('Error message:')
        msgbox = QMessageBox(
            QMessageBox.Critical, _('Restore'),
            _('<b>{}</b><br><br>{}<br>{}').format(text, heading, error),
            parent=self)
        msgbox.exec_()

    def deactivate(self, idx):
        for col in range(self.table.columnCount()):
            self.table.cellWidget(idx, col).setEnabled(False)
        self.num_enabled -= 1
        if self.num_enabled == 0:
            self.accept()

    def exec_if_nonempty(self):
        """Execute dialog window if there is data to show."""
        if self.data:
            return self.exec_()
        else:
            return QDialog.Accepted

    def exec_(self):
        """Execute dialog window."""
        if running_under_pytest():
            return QDialog.Accepted
        return super(RecoveryDialog, self).exec_()


def make_temporary_files(tempdir):
    """
    Make temporary files to simulate a recovery use case.

    Create a directory under tempdir containing some original files and another
    directory with autosave files. Return a tuple with the name of the
    directory with the original files, the name of the directory with the
    autosave files, and the autosave mapping.
    """
    orig_dir = osp.join(tempdir, 'orig')
    os.mkdir(orig_dir)
    autosave_dir = osp.join(tempdir, 'autosave')
    os.mkdir(autosave_dir)
    autosave_mapping = {}

    # ham.py: Both original and autosave files exist, mentioned in mapping
    orig_file = osp.join(orig_dir, 'ham.py')
    with open(orig_file, 'w') as f:
        f.write('ham = "original"\n')
    autosave_file = osp.join(autosave_dir, 'ham.py')
    with open(autosave_file, 'w') as f:
        f.write('ham = "autosave"\n')
    autosave_mapping[orig_file] = autosave_file

    # spam.py: Only autosave file exists, mentioned in mapping
    orig_file = osp.join(orig_dir, 'spam.py')
    autosave_file = osp.join(autosave_dir, 'spam.py')
    with open(autosave_file, 'w') as f:
        f.write('spam = "autosave"\n')
    autosave_mapping[orig_file] = autosave_file

    # eggs.py: Only original files exists, mentioned in mapping
    orig_file = osp.join(orig_dir, 'eggs.py')
    with open(orig_file, 'w') as f:
        f.write('eggs = "original"\n')
    autosave_file = osp.join(autosave_dir, 'eggs.py')
    autosave_mapping[orig_file] = autosave_file

    # cheese.py: Only autosave file exists, not mentioned in mapping
    autosave_file = osp.join(autosave_dir, 'cheese.py')
    with open(autosave_file, 'w') as f:
        f.write('cheese = "autosave"\n')

    return orig_dir, autosave_dir, autosave_mapping


def test():  # pragma: no cover
    """Display recovery dialog for manual testing."""
    import shutil
    import tempfile
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    tempdir = tempfile.mkdtemp()
    _, autosave_dir, autosave_mapping = make_temporary_files(tempdir)
    dialog = RecoveryDialog(autosave_dir, autosave_mapping)
    dialog.exec_()
    print('files_to_open =', dialog.files_to_open)  # spyder: test-skip
    shutil.rmtree(tempdir)


if __name__ == "__main__":  # pragma: no cover
    test()
