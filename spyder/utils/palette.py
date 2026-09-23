# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Palette for theme used in Spyder.
"""

# Local imports
from spyder.config.manager import CONF
from spyder.utils.theme_manager import THEME_MANAGER


def _get_theme_palette():
    """
    Get SpyderPalette from theme manager.

    Returns
    -------
    class
        SpyderPalette class from the loaded theme, or None if loading fails.
    """
    default_theme = "spyder_themes.spyder/dark"
    selected = CONF.get(
        "appearance", "selected", default=default_theme
    )

    # Set new default theme in case users set before one of old ones
    if "spyder_themes" not in selected:
        selected = default_theme
        CONF.set("appearance", "selected", default_theme)

    selected = THEME_MANAGER.canonical_theme_variant_id(selected)

    if "/" in selected:
        theme_name, ui_mode = selected.rsplit("/", 1)
        THEME_MANAGER.export_theme_to_config(
            theme_name, ui_mode, replace=False
        )

    if "/" in selected:
        theme_name, ui_mode = selected.rsplit("/", 1)
    else:
        theme_name = selected
        ui_mode = "dark"

    # Load the theme
    palette_class, __ = THEME_MANAGER.load_theme(theme_name, ui_mode)
    return palette_class


SpyderPalette = _get_theme_palette()
