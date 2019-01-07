# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Autosave components for the Editor plugin and the EditorStack widget"""

# Standard library imports
import logging
import os
import os.path as osp

# Third party imports
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.base import _, get_conf_path
from spyder.config.main import CONF
from spyder.plugins.editor.widgets.recover import RecoveryDialog


logger = logging.getLogger(__name__)


class AutosaveForPlugin(object):
    """Component of editor plugin implementing autosave functionality."""

    # Interval (in ms) between two autosaves
    DEFAULT_AUTOSAVE_INTERVAL = 60 * 1000

    def __init__(self, editor):
        """
        Constructor.

        Autosave is disabled after construction and needs to be enabled
        explicitly if required.

        Args:
            editor (Editor): editor plugin.
        """
        self.editor = editor
        self.timer = QTimer(self.editor)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.do_autosave)
        self._enabled = False  # Can't use setter here
        self._interval = self.DEFAULT_AUTOSAVE_INTERVAL

    @property
    def enabled(self):
        """
        Get or set whether autosave component is enabled.

        The setter will start or stop the autosave component if appropriate.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, new_enabled):
        if new_enabled == self.enabled:
            return
        self.stop_autosave_timer()
        self._enabled = new_enabled
        self.start_autosave_timer()

    @property
    def interval(self):
        """
        Interval between two autosaves, in milliseconds.

        The setter will perform an autosave if the interval is changed and
        autosave is enabled.
        """
        return self._interval

    @interval.setter
    def interval(self, new_interval):
        if new_interval == self.interval:
            return
        self.stop_autosave_timer()
        self._interval = new_interval
        if self.enabled:
            self.do_autosave()

    def start_autosave_timer(self):
        """
        Start a timer which calls do_autosave() after `self.interval`.

        The autosave timer is only started if autosave is enabled.
        """
        if self.enabled:
            self.timer.start(self.interval)

    def stop_autosave_timer(self):
        """Stop the autosave timer."""
        self.timer.stop()

    def do_autosave(self):
        """Instruct current editorstack to autosave files where necessary."""
        logger.debug('Autosave triggered')
        stack = self.editor.get_current_editorstack()
        stack.autosave.autosave_all()
        self.start_autosave_timer()

    def try_recover_from_autosave(self):
        """Offer to recover files from autosave."""
        autosave_dir = get_conf_path('autosave')
        autosave_mapping = CONF.get('editor', 'autosave_mapping', {})
        dialog = RecoveryDialog(autosave_dir, autosave_mapping,
                                parent=self.editor)
        dialog.exec_if_nonempty()
        self.recover_files_to_open = dialog.files_to_open[:]


class AutosaveForStack(object):
    """
    Component of EditorStack implementing autosave functionality.

    Attributes:
        stack (EditorStack): editor stack this component belongs to.
        name_mapping (dict): map between names of opened and autosave files.
    """

    def __init__(self, editorstack):
        """
        Constructor.

        Args:
            editorstack (EditorStack): editor stack this component belongs to.
        """
        self.stack = editorstack
        self.name_mapping = {}

    def create_unique_autosave_filename(self, filename, autosave_dir):
        """
        Create unique autosave file name for specified file name.

        Args:
            filename (str): original file name
            autosave_dir (str): directory in which autosave files are stored
        """
        basename = osp.basename(filename)
        autosave_filename = osp.join(autosave_dir, basename)
        if autosave_filename in self.name_mapping.values():
            counter = 0
            root, ext = osp.splitext(basename)
            while autosave_filename in self.name_mapping.values():
                counter += 1
                autosave_basename = '{}-{}{}'.format(root, counter, ext)
                autosave_filename = osp.join(autosave_dir, autosave_basename)
        return autosave_filename

    def remove_autosave_file(self, fileinfo):
        """
        Remove autosave file for specified file.

        This function also updates `self.autosave_mapping` and clears the
        `changed_since_autosave` flag.
        """
        filename = fileinfo.filename
        if filename not in self.name_mapping:
            return
        autosave_filename = self.name_mapping[filename]
        try:
            os.remove(autosave_filename)
        except EnvironmentError:
            pass  # TODO Show errors
        del self.name_mapping[filename]
        self.stack.sig_option_changed.emit(
                'autosave_mapping', self.name_mapping)
        logger.debug('Removing autosave file %s', autosave_filename)

    def get_autosave_filename(self, filename):
        """
        Get name of autosave file for specified file name.

        This function uses the dict in `self.name_mapping`. If `filename` is
        in the mapping, then return the corresponding autosave file name.
        Otherwise, construct a unique file name and update the mapping.

        Args:
            filename (str): original file name
        """
        try:
            autosave_filename = self.name_mapping[filename]
        except KeyError:
            autosave_dir = get_conf_path('autosave')
            if not osp.isdir(autosave_dir):
                os.mkdir(autosave_dir)  # TODO Handle errors
            autosave_filename = self.create_unique_autosave_filename(
                    filename, autosave_dir)
            self.name_mapping[filename] = autosave_filename
            self.stack.sig_option_changed.emit(
                    'autosave_mapping', self.name_mapping)
            logger.debug('New autosave file name')
        return autosave_filename

    def autosave(self, index):
        """
        Autosave a file.

        Do nothing if the `changed_since_autosave` flag is not set or the file
        is newly created (and thus not named by the user). Otherwise, save a
        copy of the file with the name given by `self.get_autosave_filename()`
        and clear the `changed_since_autosave` flag. Errors raised when saving
        are silently ignored.

        Args:
            index (int): index into self.stack.data
        """
        finfo = self.stack.data[index]
        document = finfo.editor.document()
        if not document.changed_since_autosave or finfo.newly_created:
            return
        autosave_filename = self.get_autosave_filename(finfo.filename)
        logger.debug('Autosaving %s to %s', finfo.filename, autosave_filename)
        try:
            self.stack._write_to_file(finfo, autosave_filename)
            document.changed_since_autosave = False
        except EnvironmentError as error:
            action = (_('Error while autosaving {} to {}')
                      .format(finfo.filename, autosave_filename))
            msgbox = AutosaveErrorMessageBox(action, error)
            msgbox.exec_()

    def autosave_all(self):
        """Autosave all opened files."""
        for index in range(self.stack.get_stack_count()):
            self.autosave(index)


class AutosaveErrorMessageBox(QMessageBox):
    """Dialog window notifying user of autosave related errors."""

    def __init__(self, action, error):
        """
        Constructor.

        Args:
            action (str): what Spyder was trying to do when error occured
            error (Exception): the error that occured
        """
        logger.error(action, exc_info=error)
        header = _('Error message:')
        txt = '<br>{}<br><br>{}<br>{!s}'.format(action, header, error)
        QMessageBox.__init__(
            self, QMessageBox.Critical, _('Autosave Error'), txt)
