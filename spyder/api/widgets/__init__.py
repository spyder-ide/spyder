# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Widgets to extend Spyder through its API.
"""


class PluginMainWidgetWidgets:
    """Basic widgets any :class:`~spyder.api.plugins.SpyderDockablePlugin` has."""

    CornerWidget: str = "corner_widget"
    """Right-corner pane toolbar buttons, just left of the options button."""

    MainToolbar: str = "main_toolbar_widget"
    """The primary pane toolbar, left-aligned."""

    OptionsToolButton: str = "options_button_widget"
    """The pane's "hamburger menu", on the very right of the toolbar area."""

    Spinner: str = "spinner_widget"
    """An optional progress spinner widget in the toolbar."""


class PluginMainWidgetActions:
    """Common menu actions for :class:`~spyder.api.plugins.SpyderDockablePlugin`\\s."""

    ClosePane: str = "close_pane"
    """Close the plugin's pane."""

    DockPane: str = "dock_pane"
    """Re-dock a popped-out pane to the Spyder main window."""

    UndockPane: str = "undock_pane"
    """Pop out a plugin's pane into a separate floating window."""

    LockUnlockPosition: str = "lock_unlock_position"
    """Toggle whether a pane can be freely moved around the Spyder window."""
