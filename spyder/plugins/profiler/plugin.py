# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler Plugin.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import ApplicationMenus, Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import (ProfilerWidget,
                                                         ProfilerWidgetActions,
                                                         is_profiler_installed)
from spyder.plugins.run.widgets import get_run_configuration

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class ProfilerActions:
    ProfileCurrentFile = 'profile_current_filename_action'


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Editor, Plugins.VariableExplorer]
    TABIFY = Plugins.Help
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_started = Signal()
    """This signal is emitted to inform the profiling process has started."""

    sig_finished = Signal()
    """This signal is emitted to inform the profile profiling has finished."""

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Profiler")

    def get_description(self):
        return _("Profile your scripts and find bottlenecks.")

    def get_icon(self):
        path = osp.join(self.get_path(), self.IMG_PATH)
        return self.create_icon('profiler', path=path)

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        widget.sig_edit_goto_requested.connect(editor.load)
        widget.sig_started.connect(self.sig_started)
        widget.sig_finished.connect(self.sig_finished)

        run_action = self.create_action(
            ProfilerActions.ProfileCurrentFile,
            text=_("Run profiler"),
            tip=_("Run profiler"),
            icon=self.create_icon('run'),
            triggered=self.run_profiler,
        )
        run_action.setEnabled(is_profiler_installed())

        run_menu = self.get_application_menu(ApplicationMenus.Run)
        self.add_item_to_application_menu(run_action, menu=run_menu)

        # TODO: On a separate PR when core plugin is merged
        # self.main.editor.pythonfile_dependent_actions += [profiler_act]

    # --- Public API
    # ------------------------------------------------------------------------
    def run_profiler(self):
        """
        Run profiler.

        Notes
        -----
        This method will check if the file on the editor can be saved first.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor.save():
            self.switch_to_plugin()
            self.analyze(editor.get_current_filename())

    def stop_profiler(self):
        """
        Stop profiler.
        """
        self.get_widget().stop()

    def analyze(self, filename):
        """
        Run profile analysis on `filename`.

        Parameters
        ----------
        filename: str
            Path to file to analyze.
        """
        # TODO: how to get access to this in a better way?
        pythonpath = self.main.get_spyder_pythonpath()

        wdir, args = None, []
        runconf = get_run_configuration(filename)
        if runconf is not None:
            if runconf.wdir_enabled:
                wdir = runconf.wdir

            if runconf.args_enabled:
                args = runconf.args

        self.get_widget().analyze(
            filename,
            wdir=wdir,
            args=args,
            pythonpath=pythonpath,
        )
