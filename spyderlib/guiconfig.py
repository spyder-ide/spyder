# -*- coding: utf-8 -*-
#
# Copyright © 2009-2012 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder GUI-related configuration management
(for non-GUI configuration, see spyderlib/baseconfig.py)

Important note regarding shortcuts:
    For compatibility with QWERTZ keyboards, one must avoid using the following
    shortcuts:
        Ctrl + Alt + Q, W, F, G, Y, X, C, V, B, N
"""

from collections import namedtuple

from spyderlib.qt.QtGui import QFont, QFontDatabase, QShortcut, QKeySequence
from spyderlib.qt.QtCore import Qt

from spyderlib.config import CONF
from spyderlib.userconfig import NoDefault
from spyderlib.widgets.sourcecode import syntaxhighlighters as sh
from spyderlib.py3compat import to_text_string


# To save metadata about widget shortcuts (needed to build our
# preferences page)
Shortcut = namedtuple('Shortcut', 'data')


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
        print("Warning: None of the following fonts is installed: %r" % families)
        return QFont().family()


FONT_CACHE = {}
def get_font(section, option=None):
    """Get console font properties depending on OS and user options"""
    font = FONT_CACHE.get((section, option))
    if font is None:
        if option is None:
            option = 'font'
        else:
            option += '/font'
        families = CONF.get(section, option+"/family", None)
        if families is None:
            return QFont()
        family = get_family(families)
        weight = QFont.Normal
        italic = CONF.get(section, option+'/italic', False)
        if CONF.get(section, option+'/bold', False):
            weight = QFont.Bold
        size = CONF.get(section, option+'/size', 9)
        font = QFont(family, size, weight)
        font.setItalic(italic)
        FONT_CACHE[(section, option)] = font
    return font


def set_font(font, section, option=None):
    """Set font"""
    if option is None:
        option = 'font'
    else:
        option += '/font'
    CONF.set(section, option+'/family', to_text_string(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/italic', int(font.italic()))
    CONF.set(section, option+'/bold', int(font.bold()))
    FONT_CACHE[(section, option)] = font


def get_shortcut(context, name, default=NoDefault):
    """Get keyboard shortcut (key sequence string)"""
    return CONF.get('shortcuts', '%s/%s' % (context, name), default=default)


def set_shortcut(context, name, keystr):
    """Set keyboard shortcut (key sequence string)"""
    CONF.set('shortcuts', '%s/%s' % (context, name), keystr)


def new_shortcut(keystr, parent, action):
    """Define a new shortcut according to a keysequence string"""
    sc = QShortcut(QKeySequence(keystr), parent, action)
    sc.setContext(Qt.WidgetWithChildrenShortcut)
    return sc


def create_shortcut(action, context, name, parent):
    """Creates a Shortcut namedtuple for a widget"""
    keystr = get_shortcut(context, name)
    qsc = new_shortcut(keystr, parent, action)
    sc = Shortcut(data=(qsc, name, keystr))
    return sc


def iter_shortcuts():
    """Iterate over keyboard shortcuts"""
    for option in CONF.options('shortcuts'):
        context, name = option.split("/", 1)
        yield context, name, get_shortcut(context, name)


def remove_deprecated_shortcuts(data):
    """Remove deprecated shortcuts (shortcuts in CONF but not registered)"""
    section = 'shortcuts'
    options = [('%s/%s' % (context, name)).lower() for (context, name) in data]
    for option, _ in CONF.items(section, raw=CONF.raw):
        if option not in options:
            CONF.remove_option(section, option)
            if len(CONF.items(section, raw=CONF.raw)) == 0:
                CONF.remove_section(section)


def reset_shortcuts():
    """Reset keyboard shortcuts to default values"""
    CONF.reset_to_defaults(section='shortcuts')


def get_color_scheme(name):
    """Get syntax color scheme"""
    color_scheme = {}
    for key in sh.COLOR_SCHEME_KEYS:
        color_scheme[key] = CONF.get("color_schemes", "%s/%s" % (name, key))
    return color_scheme


def set_color_scheme(name, color_scheme, replace=True):
    """Set syntax color scheme"""
    section = "color_schemes"
    names = CONF.get("color_schemes", "names", [])
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


for _name in sh.COLOR_SCHEME_NAMES:
    set_default_color_scheme(_name, replace=False)
CUSTOM_COLOR_SCHEME_NAME = "Custom"
set_color_scheme(CUSTOM_COLOR_SCHEME_NAME, sh.get_color_scheme("Spyder"),
                 replace=False)
