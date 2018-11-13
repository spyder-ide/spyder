# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Autosave component for EditorStack"""

# Standard library imports
import logging
import os
import os.path as osp

# Local imports
from spyder.config.base import get_conf_path


logger = logging.getLogger(__name__)


class AutosaveComponentForEditorStack(object):
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
        os.remove(autosave_filename)
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
                os.mkdir(autosave_dir)
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
        except (IOError, OSError):
            pass

    def autosave_all(self):
        """Autosave all opened files."""
        for index in range(self.stack.get_stack_count()):
            self.autosave(index)
