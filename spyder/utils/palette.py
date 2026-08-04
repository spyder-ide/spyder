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
    selected = CONF.get(
        "appearance", "selected", default="spyder_themes.spyder/dark"
    )

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
