# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder GUI-related configuration management
(for non-GUI configuration, see spyder/config/base.py)

Important note regarding shortcuts:
    For compatibility with QWERTZ keyboards, one must avoid using the following
    shortcuts:
        Ctrl + Alt + Q, W, F, G, Y, X, C, V, B, N
"""

# Third party imports
from qtpy import QT_VERSION
from qtpy.QtGui import QFont, QFontDatabase

# Local imports
from spyder.config.base import _is_conf_ready
from spyder.config.manager import CONF


def font_is_installed(font):
    """Check if font is installed"""
    db = QFontDatabase() if QT_VERSION.startswith("5") else QFontDatabase
    return [fam for fam in db.families() if str(fam) == font]


def get_family(families):
    """Return the first installed font family in family list"""
    if not isinstance(families, list):
        families = [ families ]
    for family in families:
        if font_is_installed(family):
            return family
    else:
        print("Warning: None of the following fonts is installed: %r" % families)  # spyder: test-skip
        return QFont().family()


FONT_CACHE = {}

def get_font(section='appearance', option='font', font_size_delta=0):
    """Get console font properties depending on OS and user options"""
    font = FONT_CACHE.get((section, option, font_size_delta))

    if font is None:
        families = CONF.get(section, option+"/family", None)

        if families is None:
            return QFont()

        family = get_family(families)
        weight = QFont.Normal
        italic = CONF.get(section, option+'/italic', False)

        if CONF.get(section, option+'/bold', False):
            weight = QFont.Bold

        size = CONF.get(section, option+'/size', 9) + font_size_delta
        font = QFont(family, size, weight)
        font.setItalic(italic)
        FONT_CACHE[(section, option, font_size_delta)] = font

    size = CONF.get(section, option+'/size', 9) + font_size_delta
    if size > 0:
        font.setPointSize(size)
    return font


def set_font(font, section='appearance', option='font'):
    """Set font properties in our config system."""
    CONF.set(section, option+'/family', str(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/italic', int(font.italic()))
    CONF.set(section, option+'/bold', int(font.bold()))

    # This function is only used to set fonts that were changed through
    # Preferences. And in that case it's not possible to set a delta.
    font_size_delta = 0

    FONT_CACHE[(section, option, font_size_delta)] = font


def is_dark_interface():
    """
    Check if current interface is dark mode.

    Determines the interface mode by inspecting the selected theme variant.
    Theme variants follow the format 'theme_name/mode' (e.g., 'solarized/dark').
    Returns True if config is not ready to avoid segfaults during initialization.
    """
    # Don't access config if it's not ready to avoid segfaults
    if not _is_conf_ready():
        return True

    try:
        # Use default value if config doesn't exist or isn't initialized yet
        selected = CONF.get("appearance", "selected", "spyder_themes.spyder/dark")
        # Import here so spyder.config.gui can load before spyder.utils.theme_manager.
        from spyder.utils.theme_manager import ThemeManager

        selected = ThemeManager.canonical_theme_variant_id(selected)

        if "/" in selected:
            _, ui_mode = selected.rsplit("/", 1)
            return ui_mode == "dark"

        # Default to dark if no mode specified (shouldn't happen with new themes)
        return True
    except (AttributeError, ImportError, RuntimeError, OSError):
        # If CONF is not initialized, config file doesn't exist, or there's
        # an error accessing it, default to dark mode
        return True
