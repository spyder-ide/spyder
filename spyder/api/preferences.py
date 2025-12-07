# -----------------------------------------------------------------------------
# Copyright (c) 2016- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
API to create an entry in Spyder Preferences associated to a given plugin.
"""

from __future__ import annotations

# Standard library imports
import types
import sys
from typing import TYPE_CHECKING

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias  # noqa: ICN003

# Local imports
from spyder.api.utils import PrefixedTuple
from spyder.config.manager import CONF
from spyder.config.types import ConfigurationKey
from spyder.widgets.config import SpyderConfigPage, BaseConfigTab

if TYPE_CHECKING:
    from qtpy.QtGui import QIcon

    from spyder.api.plugins import SpyderPluginV2
    import spyder.plugins.preferences.widget


OptionSet: TypeAlias = set[ConfigurationKey]
"""Type alias for a set of keys mapping to valid Spyder configuration values.

A :class:`set` of :class:`spyder.config.types.ConfigurationKey`\\s.
"""


class SpyderPreferencesTab(BaseConfigTab):
    """
    Widget that represents a tab on a preference page.

    All calls to :class:`spyder.widgets.config.SpyderConfigPage` attributes
    are resolved via delegation.
    """

    TITLE: str | None = None
    """Name of the tab to display; must be set on the child implementations."""

    def __init__(self, parent: SpyderConfigPage) -> None:
        """
        Create a new tab on the given ``parent`` config page.

        Parameters
        ----------
        parent : spyder.widgets.config.SpyderConfigPage
            The config page the tab will live on, to be this widget's parent.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If :attr:`TITLE` has not been set on the child implementation.
        """
        super().__init__(parent)
        self.parent = parent

        if self.TITLE is None or not isinstance(self.TITLE, str):
            raise ValueError("TITLE must be a str")

    def apply_settings(self) -> OptionSet:
        """
        Hook to manually apply settings that cannot be applied automatically.

        Reimplement this if the configuration tab has complex widgets that
        cannot be created with any of the ``self.create_*`` calls.
        This call should return a :class:`set` containing the configuration
        options that changed.

        Returns
        -------
        OptionSet
            The :class:`set` of Spyder
            :class:`~spyder.config.types.ConfigurationKey`\\s that were
            manually applied.
        """
        return set({})

    def is_valid(self) -> bool:
        """
        Return ``False`` if the tab contents are invalid, ``True`` otherwise.

        This method can be overriden to perform complex checks.

        Returns
        -------
        bool
            Whether the tab contents are valid.
        """
        return True

    def __getattr__(self, attr):
        this_class_dir = dir(self)
        if attr not in this_class_dir:
            return getattr(self.parent, attr)
        else:
            return super().__getattr__(attr)

    def setLayout(self, layout):
        """Remove default margins around the layout by default."""
        layout.setContentsMargins(0, 0, 0, 0)
        super().setLayout(layout)


class PluginConfigPage(SpyderConfigPage):
    """
    A Spyder :guilabel:`Preferences` page for a single plugin.

    This widget exposes the options a plugin offers for configuration as
    an entry in Spyder's :guilabel:`Preferences` dialog.
    """

    # TODO: Temporal attribute to handle which appy_settings method to use
    # the one of the conf page or the one in the plugin, while the config
    # dialog system is updated.
    APPLY_CONF_PAGE_SETTINGS = False

    def __init__(
        self,
        plugin: SpyderPluginV2,
        parent: spyder.plugins.preferences.widget.ConfigDialog,
    ) -> None:
        """
        Create a Spyder :guilabel:`Preferences` page for a plugin.

        Parameters
        ----------
        plugin : SpyderPluginV2
            The plugin to create the configuration page for.
        parent : spyder.plugins.preferences.widgets.configdialog.ConfigDialog
            The main Spyder :guilabel:`Preferences` dialog, parent widget
            to this one.

        Returns
        -------
        None
        """
        self.plugin = plugin
        self.main = parent.main

        if hasattr(plugin, "CONF_SECTION"):
            self.CONF_SECTION = plugin.CONF_SECTION

        if hasattr(plugin, "get_font"):
            self.get_font = plugin.get_font

        if not self.APPLY_CONF_PAGE_SETTINGS:
            self._patch_apply_settings(plugin)

        SpyderConfigPage.__init__(self, parent)

    def _wrap_apply_settings(self, func):
        """
        Wrap apply_settings call to ensure that a user-defined custom call
        is called alongside the Spyder Plugin API configuration propagation
        call.
        """

        def wrapper(self, options):
            opts = self.previous_apply_settings() or set({})
            opts |= options
            self.aggregate_sections_partials(opts)
            func(opts)

        return types.MethodType(wrapper, self)

    def _patch_apply_settings(self, plugin):
        self.previous_apply_settings = self.apply_settings
        self.apply_settings = self._wrap_apply_settings(plugin.apply_conf)
        self.get_option = plugin.get_conf
        self.set_option = plugin.set_conf
        self.remove_option = plugin.remove_conf

    def aggregate_sections_partials(self, opts: OptionSet) -> None:
        """
        Aggregate options by sections in order to notify observers.

        Parameters
        ----------
        opts : OptionSet
            The options to aggregate by section.

        Returns
        -------
        None
        """
        to_update = {}
        for opt in opts:
            if isinstance(opt, tuple):
                # This is necessary to filter tuple options that do not
                # belong to a section.
                if len(opt) == 2 and opt[0] is None:
                    opt = opt[1]

            section = self.CONF_SECTION
            if opt in self.cross_section_options:
                section = self.cross_section_options[opt]
            section_options = to_update.get(section, [])
            section_options.append(opt)
            to_update[section] = section_options

        for section in to_update:
            section_prefix = PrefixedTuple()
            # Notify section observers
            CONF.notify_observers(
                section, "__section", recursive_notification=False
            )
            for opt in to_update[section]:
                if isinstance(opt, tuple):
                    opt = opt[:-1]
                    section_prefix.add_path(opt)
            # Notify prefixed observers
            for prefix in section_prefix:
                try:
                    CONF.notify_observers(
                        section, prefix, recursive_notification=False
                    )
                except Exception:
                    # Prevent unexpected failures on tests
                    pass

    def get_name(self) -> str:
        """
        Return plugin name to use in preferences page title and message boxes.

        Normally you do not have to reimplement it, as the plugin name
        in the preferences page will be the same as the plugin title.

        Returns
        -------
        str
            The plugin this preference page corresponds to.
        """
        return self.plugin.get_name()

    def get_icon(self) -> QIcon:
        """
        Return the plugin icon to use in the preferences page.

        Normally you do not have to reimplement it, as the plugin icon
        in the preferences page will be the same as the main plugin icon.

        Returns
        -------
        QIcon
            The plugin's icon.
        """
        return self.plugin.get_icon()

    def setup_page(self) -> None:
        """
        Set up the configuration page widget.

        You need to implement this method to set the layout of the
        preferences page.

        For example:

        .. code-block:: python

            layout = QVBoxLayout()
            layout.addWidget(...)
            ...
            self.setLayout(layout)

        Returns
        -------
        None
        """
        raise NotImplementedError

    def apply_settings(self) -> OptionSet:
        """
        Hook to manually apply settings that cannot be applied automatically.

        Reimplement this if the configuration tab has complex widgets that
        cannot be created with any of the ``self.create_*`` calls.
        This call should return a :class:`set` containing the configuration
        options that changed.

        Returns
        -------
        OptionSet
            The :class:`set` of Spyder
            :class:`~spyder.config.types.ConfigurationKey`\\s that were
            manually applied.
        """
        return set({})
