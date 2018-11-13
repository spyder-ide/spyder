# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Autosave component for the editor plugin"""

# Standard library imports
import logging

# Third party imports
from qtpy.QtCore import QTimer

# Local imports
from spyder.config.base import get_conf_path
from spyder.config.main import CONF
from spyder.plugins.editor.widgets.recover import RecoveryDialog


logger = logging.getLogger(__name__)


class AutosaveComponentForEditorPlugin(object):
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
