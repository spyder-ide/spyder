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
from spyder.api.widgets import PluginMainContainer
from spyder.plugins.maininterpreter.widgets.status import InterpreterStatus
from spyder.utils.misc import get_python_executable


class MainInterpreterContainer(PluginMainContainer):
    DEFAULT_OPTIONS = {
        'default': True,
        'custom': False,
        'custom_interpreter': '',
    }

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
    def setup(self, options):

        self.interpreter_status = InterpreterStatus(
            parent=self,
            interpreter=self.get_main_interpreter()
        )

        self.interpreter_status.sig_open_preferences_requested.connect(
            self.sig_open_preferences_requested)

        # TODO: Automatically connect sig_option_changed from widgets that
        # inherit from SpyderWidgetMixin to the container's signal of the
        # same name.
        self.interpreter_status.sig_option_changed.connect(
            self.sig_option_changed)

    def update_actions(self):
        pass

    def on_option_update(self, option, value):
        if option in ['default', 'custom_interpreter', 'custom'] and value:
            self._update_status()
            self.sig_interpreter_changed.emit()

            # Set new interpreter
            executable = osp.normpath(self.get_option('custom_interpreter'))
            if (option in ['custom', 'custom_interpreter'] and
                    osp.isfile(executable)):
                self.sig_add_to_custom_interpreters_requested.emit(executable)

    # ---- Public API
    def get_main_interpreter(self):
        if self.get_option('default'):
            return get_python_executable()
        else:
            executable = osp.normpath(self.get_option('custom_interpreter'))

            # Check if custom interpreter is stil present
            if osp.isfile(executable):
                return executable
            else:
                return get_python_executable()

    # ---- Private API
    def _update_status(self):
        """Update status widget."""
        self.interpreter_status.update_interpreter(
            self.get_main_interpreter())
