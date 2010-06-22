# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder configuration management

Important note regarding shortcuts:
    For compatibility with QWERTZ keyboards, one must avoid using the following
    shortcuts:
        Ctrl + Alt + Q, W, F, G, Y, X, C, V, B, N
"""

import os, sys
import os.path as osp
from datetime import date
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont, QFontDatabase

# Local import
from userconfig import UserConfig, get_home_dir

DATA_DEV_PATH = osp.dirname(__file__)
DOC_DEV_PATH = osp.join(DATA_DEV_PATH, 'doc')

# The two following lines are patched when making the debian package:
DATA_PATH = DATA_DEV_PATH # @@@DATA_PATH@@@
DOC_PATH = DOC_DEV_PATH # @@@DOC_PATH@@@

FILTERS = [int, long, float, list, dict, tuple, str, unicode, date]
try:
    from numpy import ndarray
    FILTERS.append(ndarray)
except ImportError:
    pass
try:
    from PIL.Image import Image
    FILTERS.append(Image)
except ImportError:
    pass

# Max number of filter iterations for worskpace display:
# (for workspace saving, itermax == -1, see Workspace.save)
ITERMAX = -1 #XXX: To be adjusted if it takes too much to compute... 2, 3?

EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc', 'typecodes',
            '__builtins__', '__main__', '__doc__']

def type2str(types):
    """Convert types to strings"""
    return [typ.__name__ for typ in types]

def str2type(strings):
    """Convert strings to types"""
    return tuple( [eval(string) for string in strings] )

SANS_SERIF = ['Sans Serif', 'DejaVu Sans', 'Bitstream Vera Sans',
              'Bitstream Charter', 'Lucida Grande', 'Verdana', 'Geneva',
              'Lucid', 'Arial', 'Helvetica', 'Avant Garde', 'sans-serif']
SANS_SERIF.insert(0, unicode(QFont().family()))

MONOSPACE = ['Monospace', 'DejaVu Sans Mono', 'Consolas', 'Courier New',
             'Bitstream Vera Sans Mono', 'Andale Mono', 'Liberation Mono',
             'Monaco', 'Courier', 'monospace', 'Fixed', 'Terminal']
MEDIUM = 10
SMALL = 9

# Note: These default hexstates are no longer used --> too much bugs
#       Now, the default window layout is done programmatically (see spyder.py)
#       when the .ini file doesn't exist or when the --reset option is passed
#STATE1 = '000000ff00000000fd0000000100000001000004ec0000026ffc0200000001fc000000380000026f0000018700fffffffc0100000002fb000000120045006400690074006f0072005f00640077010000000000000280000000db00fffffffc0000028400000268000001ca00fffffffc0200000002fc0000003800000161000000e001000015fa000000010100000006fb0000001200500079006c0069006e0074005f006400770000000000ffffffff000000e400fffffffb0000001a004f006e006c0069006e006500480065006c0070005f006400770100000000ffffffff0000017800fffffffb00000024004f0062006a0065006300740049006e00730070006500630074006f0072005f006400770100000000ffffffff0000019000fffffffb000000180057006f0072006b00730070006100630065005f006400770100000000ffffffff0000005000fffffffb00000016004500780070006c006f007200650072005f006400770100000000ffffffff0000007400fffffffb0000001c00460069006e00640049006e00460069006c00650073005f006400770100000328000001c4000001ca00fffffffc0000019d0000010a000000a301000015fa000000000100000003fb000000140043006f006e0073006f006c0065005f006400770100000000ffffffff0000005900fffffffb0000002400450078007400650072006e0061006c0043006f006e0073006f006c0065005f006400770100000000ffffffff0000009100fffffffb0000001a0048006900730074006f00720079004c006f0067005f00640077010000026900000283000000d700ffffff000000000000026f00000004000000040000000800000008fc00000001000000020000000800000018006d00610069006e005f0074006f006f006c00620061007201000000000000003700000000000000000000001800660069006c0065005f0074006f006f006c0062006100720100000037000000750000000000000000000000200061006e0061006c0079007300690073005f0074006f006f006c00620061007201000000ac0000006d00000000000000000000001600720075006e005f0074006f006f006c0062006100720100000119000000390000000000000000000000180065006400690074005f0074006f006f006c00620061007201000001520000005800000000000000000000001800660069006e0064005f0074006f006f006c00620061007201000001aa0000008c00000000000000000000001400770073005f0074006f006f006c00620061007201000002360000006d00000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c01000002a3000002370000000000000000'
#STATE2 = '000000ff00000000fd0000000200000000000004ec0000035efc0200000006fc000000380000035e000001c100fffffffc0200000002fc00000038000001d1000000dd00fffffffc0100000002fb00000016004500780070006c006f007200650072005f0064007701000000000000011d0000007400fffffffc00000121000003cb000000db00fffffffa000000000100000002fb000000120045006400690074006f0072005f00640077010000000000000184000000db00fffffffb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000000ffffffff0000000000000000fc0000020d00000189000000e000fffffffc0100000002fc00000000000002b1000001ca00fffffffa000000020100000004fb0000001c00460069006e00640049006e00460069006c00650073005f006400770100000000ffffffff000001ca00fffffffb0000002400450078007400650072006e0061006c0043006f006e0073006f006c0065005f006400770100000000ffffffff0000009100fffffffb000000140043006f006e0073006f006c0065005f006400770100000000ffffffff0000005900fffffffb0000001a0048006900730074006f00720079004c006f0067005f006400770100000000ffffffff000000d700fffffffc000002b5000002370000019000fffffffa000000000200000005fb0000001a004f006e006c0069006e006500480065006c0070005f006400770100000000ffffffff0000004400fffffffb00000024004f0062006a0065006300740049006e00730070006500630074006f0072005f006400770100000000ffffffff0000008b00fffffffb000000180057006f0072006b00730070006100630065005f006400770100000000ffffffff0000005d00fffffffb0000001200500079006c0069006e0074005f006400770100000000ffffffff000000a700fffffffb000000180044006f0063005600690065007700650072005f00640077010000028d000001460000000000000000fc0000015b000000b80000000000fffffffa000000000200000002fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f00640077020000030a00000111000001d70000019dfb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000000ffffffff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff000000000000000000000001fffffffc00000365fc0200000002fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f0064007700000000380000039b0000000000000000fc000001e4000001ef0000000000fffffffa000000000100000001fb0000001c00530061006600650043006f006e0073006f006c0065005f006400770100000000ffffffff0000000000000000000000000000035e00000004000000040000000800000008fc00000001000000020000000800000018006d00610069006e005f0074006f006f006c00620061007201000000000000003700000000000000000000001800660069006c0065005f0074006f006f006c0062006100720100000037000000880000000000000000000000200061006e0061006c0079007300690073005f0074006f006f006c00620061007201000000bfffffffff00000000000000000000001600720075006e005f0074006f006f006c0062006100720100000128000000750000000000000000000000180065006400690074005f0074006f006f006c006200610072010000019d0000005600000000000000000000001800660069006e0064005f0074006f006f006c00620061007201000001f30000006d00000000000000000000001400770073005f0074006f006f006c00620061007201000002600000006d00000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c01000002cd0000024d0000000000000000'

try:
    from matplotlib import rcParams
    width, height = rcParams['figure.figsize']
    dpi = rcParams['figure.dpi']
    MPL_SIZE = (width*dpi, height*dpi)
except ImportError:
    MPL_SIZE = (400, 300)

DEFAULTS = [
            ('main',
             {
              'translation': True,
              'window/size': (1260, 740),
              'window/is_maximized': False,
              'window/is_fullscreen': False,
              'window/position': (10, 10),
#              'window/state': STATE1,
              'lightwindow/size': (650, 400),
              'lightwindow/position': (30, 30),
              'workaround/gnome_qscintilla': False,
              }),
            ('scintilla',
             {
              'margins/backgroundcolor': 'white',
              'margins/foregroundcolor': 'darkGray',
              'foldmarginpattern/backgroundcolor': 0xEEEEEE,
              'foldmarginpattern/foregroundcolor': 0xEEEEEE,
              }),
            ('shell_appearance',
             {
              'default_style/foregroundcolor': 0x000000,
              'default_style/backgroundcolor': 0xFFFFFF,
              'default_style/bold': False,
              'default_style/italic': False,
              'default_style/underline': False,
              'error_style/foregroundcolor': 0xFF0000,
              'error_style/backgroundcolor': 0xFFFFFF,
              'error_style/bold': False,
              'error_style/italic': False,
              'error_style/underline': False,
              'traceback_link_style/foregroundcolor': 0x0000FF,
              'traceback_link_style/backgroundcolor': 0xFFFFFF,
              'traceback_link_style/bold': True,
              'traceback_link_style/italic': False,
              'traceback_link_style/underline': True,
              'prompt_style/foregroundcolor': 0x00AA00,
              'prompt_style/backgroundcolor': 0xFFFFFF,
              'prompt_style/bold': True,
              'prompt_style/italic': False,
              'prompt_style/underline': False,
              'calltips/font/family': MONOSPACE,
              'calltips/font/size': SMALL,
              'calltips/font/italic': False,
              'calltips/font/bold': False,
              'calltips/size': 600,
              # This only applys to QPlainTextEdit-based widgets:
              'completion/font/family': MONOSPACE,
              'completion/font/size': SMALL,
              'completion/font/italic': False,
              'completion/font/bold': False,
              'completion/size': (300, 180),
              }),
            ('shell',
             {
              'shortcut': "Ctrl+Shift+C",
              'max_line_count': 300,
              'working_dir_history': 30,
              'working_dir_adjusttocontents': False,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              'calltips': True,
              'codecompletion/auto': False,
              'codecompletion/enter-key': True,
              'codecompletion/case-sensitivity': True,
              'codecompletion/select-single': True,
              'codecompletion/from-document': False,
              'external_editor/path': 'SciTE',
              'external_editor/gotoline': '-goto:',
              }),
            ('external_shell',
             {
              'shortcut': "Ctrl+Shift+X",
              'max_line_count': 300,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              'single_tab': True,
              'calltips': True,
              'codecompletion/auto': False,
              'codecompletion/enter-key': True,
              'codecompletion/case-sensitivity': True,
              'codecompletion/select-single': True,
              'codecompletion/from-document': False,
              'filters': type2str(FILTERS),
              'itermax': ITERMAX,
              'excluded_names': EXCLUDED,
              'exclude_private': True,
              'exclude_upper': True,
              'exclude_unsupported': True,
              'inplace': False,
              'truncate': True,
              'minmax': True,
              'collvalue': False,
              'show_icontext': False,
              'umd/enabled': True,
              'umd/verbose': True,
              'umd/namelist': ['guidata', 'guiqwt'],
              }),
            ('editor',
             {
              'printer_header/font/family': SANS_SERIF,
              'printer_header/font/size': MEDIUM,
              'printer_header/font/italic': False,
              'printer_header/font/bold': False,
              'shortcut': "Ctrl+Shift+E",
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': False,
              'wrapflag': True,
              'code_analysis': True,
              'class_browser': True,
              'toolbox_panel': True,
              'code_folding': True,
              'check_eol_chars': True,
              'tab_always_indent': True,
              'fullpath_sorting': True,
              'api': osp.join(DATA_PATH, 'python.api'),
              'max_recent_files': 20,
              'currentline/backgroundcolor': "#EEFFDD",
              'foundline/backgroundcolor': "#DDFFDD",
              }),
            ('historylog',
             {
              'shortcut': "Ctrl+Shift+H",
              'enable': True,
              'max_entries': 100,
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              }),
            ('inspector',
             {
              'shortcut': "Ctrl+Shift+I",
              'enable': True,
              'max_history_entries': 20,
              'font/family': MONOSPACE,
              'font/size': SMALL,
              'font/italic': False,
              'font/bold': False,
              'wrap': True,
              'automatic_import': True,
              }),
            ('onlinehelp',
             {
              'shortcut': "Ctrl+Shift+D",
              'enable': True,
              'zoom_factor': .8,
              'max_history_entries': 20,
              }),
            ('project_explorer',
             {
              'shortcut': "Ctrl+Shift+P",
              'enable': True,
              }),
            ('arrayeditor',
             {
              'font/family': MONOSPACE,
              'font/size': SMALL,
              'font/italic': False,
              'font/bold': False,
              }),
            ('texteditor',
             {
              'font/family': MONOSPACE,
              'font/size': MEDIUM,
              'font/italic': False,
              'font/bold': False,
              }),
            ('dicteditor',
             {
              'font/family': MONOSPACE,
              'font/size': SMALL,
              'font/italic': False,
              'font/bold': False,
              }),
            ('explorer',
             {
              'enable': True,
              'wrap': True,
              'name_filters': ['*.py', '*.pyw', '*.pth',
                               '*.npy', '*.mat', '*.spydata'],
              'valid_filetypes': ['', '.py', '.pyw', '.spydata', '.npy', '.pth',
                                  '.txt', '.csv', '.mat', '.h5'],
              'show_hidden': True,
              'show_all': False,
              'show_toolbar': True,
              'show_icontext': True,
              }),
            ('find_in_files',
             {
              'enable': True,
              'supported_encodings': ["utf-8", "iso-8859-1", "cp1252"],
              'include': [r'\.pyw?$|\.txt$|\.c$|\.cpp$|\.h$|\.hpp$|\.f$|\.ini$', '.'],
              'include_regexp': True,
              'exclude': [r'\.pyc$|\.pyo$|\.orig$|\.hg|\.svn'],
              'exclude_regexp': True,
              'search_text_regexp': True,
              'search_text': [''],
              'search_text_samples': [r'# ?TODO|# ?FIXME|# ?XXX'],
              'in_python_path': False,
              'more_options': True,
              }),
            ('pylint',
             {
              'enable': True,
              'max_entries': 50,
              }),
            ]

DEV = not __file__.startswith(sys.prefix)
DEV = False
from spyderlib import __version__
_subfolder = '.spyder%s' % __version__.split('.')[0]
CONF = UserConfig('spyder', defaults=DEFAULTS, load=(not DEV),
                  version='1.0.6', subfolder=_subfolder)
# Removing old .spyder.ini location:
old_location = osp.join(get_home_dir(), '.spyder.ini')
if osp.isfile(old_location):
    os.remove(old_location)

def get_conf_path(filename=None):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(get_home_dir(), _subfolder)
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)

IMG_PATH_ROOT = osp.join(DATA_PATH, 'images')
IMG_PATH = [IMG_PATH_ROOT]
for root, dirs, files in os.walk(IMG_PATH_ROOT):
    for dir in dirs:
        IMG_PATH.append(osp.join(IMG_PATH_ROOT, dir))

def get_image_path( name, default="not_found.png" ):
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
    