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

import os
import os.path as osp

from spyderlib.qt.QtGui import QLabel, QIcon, QPixmap, QFont, QFontDatabase

from spyderlib.baseconfig import get_module_data_path
from spyderlib.config import CONF
from spyderlib.userconfig import NoDefault
from spyderlib.widgets.sourcecode.syntaxhighlighters import (
                                 COLOR_SCHEME_KEYS, COLOR_SCHEME_NAMES, COLORS)

IMG_PATH = []
def add_image_path(path):
    if not osp.isdir(path):
        return
    global IMG_PATH
    IMG_PATH.append(path)
    for _root, dirs, _files in os.walk(path):
        for dir in dirs:
            IMG_PATH.append(osp.join(path, dir))

add_image_path(get_module_data_path('spyderlib', relpath='images'))

from spyderlib.otherplugins import PLUGIN_PATH
if PLUGIN_PATH is not None:
    add_image_path(osp.join(PLUGIN_PATH, 'images'))

def get_image_path(name, default="not_found.png"):
    """Return image absolute path"""
    for img_path in IMG_PATH:
        full_path = osp.join(img_path, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        return osp.abspath(osp.join(img_path, default))

def get_icon( name, default=None ):
    """Return image inside a QIcon object"""
    if default is None:
        return QIcon(get_image_path(name))
    elif isinstance(default, QIcon):
        icon_path = get_image_path(name, default=None)
        return default if icon_path is None else QIcon(icon_path)
    else:
        return QIcon(get_image_path(name, default))

def get_image_label( name, default="not_found.png" ):
    """Return image inside a QLabel object"""
    label = QLabel()
    label.setPixmap(QPixmap(get_image_path(name, default)))
    return label

def font_is_installed(font):
    """Check if font is installed"""
    return [fam for fam in QFontDatabase().families() if unicode(fam)==font]
    
def get_family(families):
    """Return the first installed font family in family list"""
    if not isinstance(families, list):
        families = [ families ]
    for family in families:
        if font_is_installed(family):
            return family
    else:
        print "Warning: None of the following fonts is installed: %r" % families
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
    CONF.set(section, option+'/family', unicode(font.family()))
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
    
def iter_shortcuts():
    """Iterate over keyboard shortcuts"""
    for option in CONF.options('shortcuts'):
        context, name = option.split("/", 1)
        yield context, name, get_shortcut(context, name)
        
def reset_shortcuts():
    """Reset keyboard shortcuts to default values"""
    CONF.remove_section('shortcuts')

def get_color_scheme(name):
    """Get syntax color scheme"""
    color_scheme = {}
    for key in COLOR_SCHEME_KEYS:
        color_scheme[key] = CONF.get("color_schemes", "%s/%s" % (name, key))
    return color_scheme

def set_color_scheme(name, color_scheme, replace=True):
    """Set syntax color scheme"""
    section = "color_schemes"
    names = CONF.get("color_schemes", "names", [])
    for key in COLOR_SCHEME_KEYS:
        option = "%s/%s" % (name, key)
        value = CONF.get(section, option, default=None)
        if value is None or replace or name not in names:
            CONF.set(section, option, color_scheme[key])
    names.append(unicode(name))
    CONF.set(section, "names", sorted(list(set(names))))

def set_default_color_scheme(name, replace=True):
    """Reset color scheme to default values"""
    assert name in COLOR_SCHEME_NAMES
    set_color_scheme(name, COLORS[name], replace=replace)

for _name in COLOR_SCHEME_NAMES:
    set_default_color_scheme(_name, replace=False)
CUSTOM_COLOR_SCHEME_NAME = "Custom"
set_color_scheme(CUSTOM_COLOR_SCHEME_NAME, COLORS["Spyder"], replace=False)
