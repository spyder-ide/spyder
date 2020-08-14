# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Core Plugin.
"""

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.api.widgets.toolbars import ApplicationToolBar
from spyder.api.widgets.menus import ApplicationMenu
from spyder.plugins.core.confpage import MainConfigPage
from spyder.plugins.core.container import CoreWidget


# Localization
_ = get_translation('spyder')


# --- Constants
class CoreStatusWidgets:
    Conda = 'conda_status_widget'
    Memory = 'memory_status_widget'
    CPU = 'cpu_status_widget'
    Clock = 'clock_status_widget'
    

class Core(SpyderPluginV2):
    NAME = 'core'
    CONTAINER_CLASS = CoreWidget
    CONF_SECTION = 'main'
    CONF_FILE = False
    CONF_WIDGET_CLASS = MainConfigPage

    def get_name(self):
        return _('General')

    def get_icon(self):
        return self.create_icon('genprefs')

    def get_description(self):
        return _('Provide Core user interface management')

    def register(self):
        # --- Menus
        self.create_application_menu("file_menu", _("&File"))
        self.create_application_menu("edit_menu", _("&Edit"))
        self.create_application_menu("search_menu", _("&Search"))
        self.create_application_menu("source_menu", _("Sour&ce"))
        self.create_application_menu("debug_menu", _("&Debug"))
        self.create_application_menu("consoles_menu", _("C&onsoles"))
        self.create_application_menu("projects_menu", _("&Projects"))
        self.create_application_menu("tools_menu", _("&Tools"))
        self.create_application_menu("view_menu", _("&View"))
        self.create_application_menu("help_menu", _("&Help"))

        # --- Toolbars
        self.create_application_toolbar("file_toolbar", _("File toolbar"))
        self.create_application_toolbar("edit_toolbar", _("Edit toolbar"))
        self.create_application_toolbar("search_toolbar", _("Search toolbar"))
        self.create_application_toolbar("source_toolbar", _("Source toolbar"))
        self.create_application_toolbar("run_toolbar", _("Run toolbar"))
        self.create_application_toolbar("debug_toolbar", _("Debug toolbar"))

        # --- Extendable actions
        # File
        self.create_action(
            'open_action', 
            text=_('Open'),
            icon=self.create_icon('undo'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'save_action', 
            text=_('Save'),
            icon=self.create_icon('undo'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'save_all_action', 
            text=_('Save all'),
            icon=self.create_icon('undo'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'close_action', 
            text=_('Close'),
            icon=self.create_icon('undo'),
            extendable=True,
            shortcut_context='_',
        )

        # Edit
        self.create_action(
            'undo_action', 
            text=_('Undo'),
            icon=self.create_icon('undo'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'redo_action',
            text=_('Redo'),
            icon=self.create_icon('redo'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'copy_action',
            text=_('Copy'),
            icon=self.create_icon('editcopy'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'cut_action',
            text=_('Cut'),
            icon=self.create_icon('editcut'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            'paste_action',
            text=_('Paste'),
            icon=self.create_icon('editpaste'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            "select_all_action",
            text=_("Select All"),
            icon=self.create_icon('selectall'),
            extendable=True,
            shortcut_context='_',
        )

        # Find
        self.create_action(
            "find_action",
            text=_("Find"),
            icon=self.create_icon('selectall'),
            extendable=True,
            shortcut_context='_',
        )
        self.create_action(
            "replace_action",
            text=_("Replace"),
            icon=self.create_icon('selectall'),
            extendable=True,
            shortcut_context='_',
        )

        # Run
        self.create_action(
            'run_action', 
            text=_('Run'),
            icon=self.create_icon('run'),
            extendable=True,
            shortcut_context='_',
        )

        # --- Status widgets
        self.add_application_status_widget(
            CoreStatusWidgets.Conda,
            self.conda_status,
            -1,
        )
        self.add_application_status_widget(
            CoreStatusWidgets.Memory,
            self.mem_status,
            -1,
        )
        self.add_application_status_widget(
            CoreStatusWidgets.CPU,
            self.cpu_status,
            -1,
        )
        self.add_application_status_widget(
            CoreStatusWidgets.Clock,
            self.clock_status,
            -1,
        )

    # --- API
    # ------------------------------------------------------------------------
    def create_application_menu(self, name, title):
        """
        TODO:
        """
        self.add_application_menu(name, ApplicationMenu(self.main, title))

    def create_application_toolbar(self, name, title):
        """
        TODO:
        """
        self.add_application_toolbar(
            name, ApplicationToolBar(self.main, title))

    @property
    def mem_status(self):
        return self.get_container().mem_status

    @property
    def cpu_status(self):
        return self.get_container().cpu_status

    @property
    def clock_status(self):
        return self.get_container().cpu_status

    @property
    def conda_status(self):
        return self.get_container().conda_status
