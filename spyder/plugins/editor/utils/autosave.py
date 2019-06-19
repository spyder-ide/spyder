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

# Local imports
from spyder.config.base import _, get_conf_path
from spyder.config.main import CONF
from spyder.plugins.editor.widgets.autosaveerror import AutosaveErrorDialog
from spyder.plugins.editor.widgets.recover import RecoveryDialog


logger = logging.getLogger(__name__)


class AutosaveForPlugin(object):
    """
    Component of editor plugin implementing autosave functionality.

    Attributes:
        name_mapping (dict): map between names of opened and autosave files.
        file_hashes (dict): map between file names and hash of their contents.
            This is used for both files opened in the editor and their
            corresponding autosave files.
    """

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
        self.name_mapping = {}
        self.file_hashes = {}
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

    def register_autosave_for_stack(self, autosave_for_stack):
        """
        Register an AutosaveForStack object.

        This replaces the `name_mapping` and `file_hashes` attributes
        in `autosave_for_stack` with references to the corresponding
        attributes of `self`, so that all AutosaveForStack objects
        share the same data.
        """
        autosave_for_stack.name_mapping = self.name_mapping
        autosave_for_stack.file_hashes = self.file_hashes


class AutosaveForStack(object):
    """
    Component of EditorStack implementing autosave functionality.

    In Spyder, the `name_mapping` and `file_hashes` are set to references to
    the corresponding variables in `AutosaveForPlugin`.

    Attributes:
        stack (EditorStack): editor stack this component belongs to.
        name_mapping (dict): map between names of opened and autosave files.
        file_hashes (dict): map between file names and hash of their contents.
            This is used for both files opened in the editor and their
            corresponding autosave files.
    """

    def __init__(self, editorstack):
        """
        Constructor.

        Args:
            editorstack (EditorStack): editor stack this component belongs to.
        """
        self.stack = editorstack
        self.name_mapping = {}
        self.file_hashes = {}

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

    def remove_autosave_file(self, filename):
        """
        Remove autosave file for specified file.

        This function also updates `self.name_mapping` and `self.file_hashes`.
        """
        if filename not in self.name_mapping:
            return
        autosave_filename = self.name_mapping[filename]
        try:
            os.remove(autosave_filename)
        except EnvironmentError as error:
            action = (_('Error while removing autosave file {}')
                      .format(autosave_filename))
            msgbox = AutosaveErrorDialog(action, error)
            msgbox.exec_if_enabled()
        del self.name_mapping[filename]
        del self.file_hashes[autosave_filename]
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
                try:
                    os.mkdir(autosave_dir)
                except EnvironmentError as error:
                    action = _('Error while creating autosave directory')
                    msgbox = AutosaveErrorDialog(action, error)
                    msgbox.exec_if_enabled()
            autosave_filename = self.create_unique_autosave_filename(
                    filename, autosave_dir)
            self.name_mapping[filename] = autosave_filename
            self.stack.sig_option_changed.emit(
                    'autosave_mapping', self.name_mapping)
            logger.debug('New autosave file name')
        return autosave_filename

    def maybe_autosave(self, index):
        """
        Autosave a file if necessary.

        If the file is newly created (and thus not named by the user), do
        nothing.  If the current contents are the same as the autosave file
        (if it exists) or the original file (if no autosave filee exists),
        then do nothing. If the current contents are the same as the file on
        disc, but the autosave file is different, then remove the autosave
        file. In all other cases, autosave the file.

        Args:
            index (int): index into self.stack.data
        """
        finfo = self.stack.data[index]
        if finfo.newly_created:
            return
        orig_filename = finfo.filename
        orig_hash = self.file_hashes[orig_filename]
        new_hash = self.stack.compute_hash(finfo)
        if orig_filename in self.name_mapping:
            autosave_filename = self.name_mapping[orig_filename]
            autosave_hash = self.file_hashes[autosave_filename]
            if new_hash != autosave_hash:
                if new_hash == orig_hash:
                    self.remove_autosave_file(orig_filename)
                else:
                    self.autosave(finfo)
        else:
            if new_hash != orig_hash:
                self.autosave(finfo)

    def autosave(self, finfo):
        """
        Autosave a file.

        Save a copy in a file with name `self.get_autosave_filename()` and
        update the cached hash of the autosave file. An error dialog notifies
        the user of any errors raised when saving.

        Args:
            fileinfo (FileInfo): file that is to be autosaved.
        """
        autosave_filename = self.get_autosave_filename(finfo.filename)
        logger.debug('Autosaving %s to %s', finfo.filename, autosave_filename)
        try:
            self.stack._write_to_file(finfo, autosave_filename)
            autosave_hash = self.stack.compute_hash(finfo)
            self.file_hashes[autosave_filename] = autosave_hash
        except EnvironmentError as error:
            action = (_('Error while autosaving {} to {}')
                      .format(finfo.filename, autosave_filename))
            msgbox = AutosaveErrorDialog(action, error)
            msgbox.exec_if_enabled()

    def autosave_all(self):
        """Autosave all opened files where necessary."""
        for index in range(self.stack.get_stack_count()):
            self.maybe_autosave(index)
