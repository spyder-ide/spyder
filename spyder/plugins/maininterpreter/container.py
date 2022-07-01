# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main interpreter container."""

# Standard library imports
import os.path as osp

# Third-party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.maininterpreter.widgets.status import InterpreterStatus
from spyder.utils.misc import get_python_executable


class MainInterpreterContainer(PluginMainContainer):

    sig_open_preferences_requested = Signal()
    """
    Signal to open the main interpreter preferences.
    """

    sig_interpreter_changed = Signal()
    """
    Signal to report that the interpreter has changed.
    """

    sig_add_to_custom_interpreters_requested = Signal(str)
    """
    Signal to request adding an interpreter to the list of custom ones.
    """

    # ---- PluginMainContainer API
    def setup(self):

        self.interpreter_status = InterpreterStatus(
            parent=self,
            interpreter=self.get_main_interpreter()
        )

        self.interpreter_status.sig_open_preferences_requested.connect(
            self.sig_open_preferences_requested)

    def update_actions(self):
        pass

    @on_conf_change(option=['default', 'custom_interpreter', 'custom'])
    def on_interpreter_changed(self, option, value):
        if ((option == 'default' and value) or
                (option == 'custom' and not value)):
            executable = get_python_executable()
        else:
            executable = osp.normpath(self.get_conf('custom_interpreter'))
            self.sig_add_to_custom_interpreters_requested.emit(executable)

        # Setting executable option that will be used by other plugins in Spyder.
        if executable != self.get_conf('executable'):
            self.set_conf('executable', executable)

    @on_conf_change(option=['executable'])
    def on_executable_changed(self, value):
        # announce update
        self._update_status()
        self.sig_interpreter_changed.emit()

    def on_close(self):
        self.interpreter_status.close()

    # ---- Public API
    def get_main_interpreter(self):
        return self.get_conf('executable', get_python_executable())

    # ---- Private API
    def _update_status(self):
        """Update status widget."""
        self.interpreter_status.update_interpreter(
            self.get_main_interpreter())
