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

# Standard library imports
from collections import namedtuple

# Third party imports
from qtconsole.styles import dark_color
from qtpy import PYQT_VERSION
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QFontDatabase, QKeySequence
from qtpy.QtWidgets import QShortcut

# Local imports
from spyder.config.manager import CONF
from spyder.py3compat import to_text_string
from spyder.utils import programs
from spyder.utils import syntaxhighlighters as sh


# To save metadata about widget shortcuts (needed to build our
# preferences page)
Shortcut = namedtuple('Shortcut', 'data')

# Stylesheet to remove the indicator that appears on tool buttons with a menu.
STYLE_BUTTON_CSS = "QToolButton::menu-indicator{image: none;}"

# Check for old PyQt versions
OLD_PYQT = programs.check_version(PYQT_VERSION, "5.12", "<")


def font_is_installed(font):
    """Check if font is installed"""
    return [fam for fam in QFontDatabase().families()
            if to_text_string(fam)==font]


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
    font.setPointSize(size)
    return font


def set_font(font, section='appearance', option='font'):
    """Set font properties in our config system."""
    CONF.set(section, option+'/family', to_text_string(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/italic', int(font.italic()))
    CONF.set(section, option+'/bold', int(font.bold()))

    # This function is only used to set fonts that were changed through
    # Preferences. And in that case it's not possible to set a delta.
    font_size_delta = 0

    FONT_CACHE[(section, option, font_size_delta)] = font


def _config_shortcut(action, context, name, keystr, parent):
    """
    Create a Shortcut namedtuple for a widget.

    The data contained in this tuple will be registered in our shortcuts
    preferences page.
    """
    qsc = QShortcut(QKeySequence(keystr), parent)
    qsc.activated.connect(action)
    qsc.setContext(Qt.WidgetWithChildrenShortcut)
    sc = Shortcut(data=(qsc, context, name))
    return sc


def get_color_scheme(name):
    """Get syntax color scheme"""
    color_scheme = {}
    for key in sh.COLOR_SCHEME_KEYS:
        color_scheme[key] = CONF.get(
            "appearance",
            "%s/%s" % (name, key),
            default=sh.COLOR_SCHEME_DEFAULT_VALUES[key])
    return color_scheme


def set_color_scheme(name, color_scheme, replace=True):
    """Set syntax color scheme"""
    section = "appearance"
    names = CONF.get("appearance", "names", [])
    for key in sh.COLOR_SCHEME_KEYS:
        option = "%s/%s" % (name, key)
        value = CONF.get(section, option, default=None)
        if value is None or replace or name not in names:
            CONF.set(section, option, color_scheme[key])
    names.append(to_text_string(name))
    CONF.set(section, "names", sorted(list(set(names))))


def set_default_color_scheme(name, replace=True):
    """Reset color scheme to default values"""
    assert name in sh.COLOR_SCHEME_NAMES
    set_color_scheme(name, sh.get_color_scheme(name), replace=replace)


def is_dark_font_color(color_scheme):
    """Check if the font color used in the color scheme is dark."""
    color_scheme = get_color_scheme(color_scheme)
    font_color, fon_fw, fon_fs = color_scheme['normal']
    return dark_color(font_color)


def is_dark_interface():
    ui_theme = CONF.get('appearance', 'ui_theme')
    color_scheme = CONF.get('appearance', 'selected')
    if ui_theme == 'dark':
        return True
    elif ui_theme == 'automatic':
        if not is_dark_font_color(color_scheme):
            return True
        else:
            return False
    else:
        return False


for _name in sh.COLOR_SCHEME_NAMES:
    set_default_color_scheme(_name, replace=False)
