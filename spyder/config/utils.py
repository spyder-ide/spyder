# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Utilities to define configuration values
"""

import os
import os.path as osp
import sys

from spyder.config.base import _

from spyder_kernels.utils import iofuncs


#==============================================================================
# Constants
#==============================================================================
# File types supported by the Editor up to Spyder 2.3
EDIT_FILETYPES = [
    (_("Python files"), ('.py', '.pyw', '.ipy')),
    (_("Cython/Pyrex files"), ('.pyx', '.pxd', '.pxi')),
    (_("C files"), ('.c', '.h')),
    (_("C++ files"), ('.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx')),
    (_("OpenCL files"), ('.cl', )),
    (_("Fortran files"), ('.f', '.for', '.f77', '.f90', '.f95', '.f2k',
                          '.f03', '.f08')),
    (_("IDL files"), ('.pro', )),
    (_("MATLAB files"), ('.m', )),
    (_("Julia files"), ('.jl',)),
    (_("Yaml files"), ('.yaml', '.yml',)),
    (_("Patch and diff files"), ('.patch', '.diff', '.rej')),
    (_("Batch files"), ('.bat', '.cmd')),
    (_("Text files"), ('.txt',)),
    (_("reStructuredText files"), ('.txt', '.rst')),
    (_("gettext files"), ('.po', '.pot')),
    (_("NSIS files"), ('.nsi', '.nsh')),
    (_("Web page files"), ('.scss', '.css', '.htm', '.html',)),
    (_("XML files"), ('.xml',)),
    (_("Javascript files"), ('.js',)),
    (_("Json files"), ('.json',)),
    (_("IPython notebooks"), ('.ipynb',)),
    (_("Enaml files"), ('.enaml',)),
    (_("Configuration files"), ('.properties', '.session', '.ini', '.inf',
                                '.reg', '.cfg', '.desktop')),
    (_("Markdown files"), ('.md', )),
]

# Filter for all files
ALL_FILTER = "%s (*)" % _("All files")

# Extensions supported by Spyder's Variable explorer
IMPORT_EXT = list(iofuncs.iofunctions.load_extensions.values())


#==============================================================================
# Auxiliary functions
#==============================================================================
def _create_filter(title, ftypes):
    return "%s (*%s)" % (title, " *".join(ftypes))


def _get_filters(filetypes):
    filters = []
    for title, ftypes in filetypes:
        filters.append(_create_filter(title, ftypes))
    filters.append(ALL_FILTER)
    return ";;".join(filters)


def _get_extensions(filetypes):
    ftype_list = []
    for _title, ftypes in filetypes:
        ftype_list += list(ftypes)
    return ftype_list


def _get_pygments_extensions():
    """Return all file type extensions supported by Pygments"""
    # NOTE: Leave this import here to keep startup process fast!
    import pygments.lexers as lexers

    extensions = []
    for lx in lexers.get_all_lexers():
        lexer_exts = lx[2]

        if lexer_exts:
            # Reference: This line was included for leaving untrimmed the
            # extensions not starting with `*`
            other_exts = [le for le in lexer_exts if not le.startswith('*')]
            # Reference: This commented line was replaced by the following one
            # to trim only extensions that start with '*'
            # lexer_exts = [le[1:] for le in lexer_exts]
            lexer_exts = [le[1:] for le in lexer_exts if le.startswith('*')]
            lexer_exts = [le for le in lexer_exts if not le.endswith('_*')]
            extensions = extensions + list(lexer_exts) + list(other_exts)

    return sorted(list(set(extensions)))


#==============================================================================
# Main functions
#==============================================================================
def get_filter(filetypes, ext):
    """Return filter associated to file extension"""
    if not ext:
        return ALL_FILTER
    for title, ftypes in filetypes:
        if ext in ftypes:
            return _create_filter(title, ftypes)
    else:
        return ''


def get_edit_filetypes():
    """Get all file types supported by the Editor"""
    # The filter details are not hidden on Windows, so we can't use
    # all Pygments extensions on that platform
    if os.name == 'nt':
        supported_exts = []
    else:
        try:
            supported_exts = _get_pygments_extensions()
        except Exception:
            supported_exts = []

    # NOTE: Try to not add too much extensions to this list to not
    # make the filter look too big on Windows
    favorite_exts = ['.py', '.R', '.jl', '.ipynb', '.md', '.pyw', '.pyx',
                     '.c', '.cpp', '.json', '.dat', '.csv', '.tsv', '.txt',
                     '.ini', '.html', '.js', '.h', '.bat']

    other_exts = [ext for ext in supported_exts if ext not in favorite_exts]
    all_exts = tuple(favorite_exts + other_exts)
    text_filetypes = (_("Supported text files"), all_exts)
    return [text_filetypes] + EDIT_FILETYPES


def get_edit_filters():
    """
    Return filters associated with the file types
    supported by the Editor
    """
    edit_filetypes = get_edit_filetypes()
    return _get_filters(edit_filetypes)


def get_edit_extensions():
    """
    Return extensions associated with the file types
    supported by the Editor
    """
    edit_filetypes = get_edit_filetypes()
    return _get_extensions(edit_filetypes)+['']


#==============================================================================
# Detection of OS specific versions
#==============================================================================
def is_ubuntu():
    """Detect if we are running in an Ubuntu-based distribution"""
    if sys.platform.startswith('linux') and osp.isfile('/etc/lsb-release'):
        release_info = open('/etc/lsb-release').read()
        if 'Ubuntu' in release_info:
            return True
        else:
            return False
    else:
        return False


def is_gtk_desktop():
    """Detect if we are running in a Gtk-based desktop"""
    if sys.platform.startswith('linux'):
        xdg_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
        if xdg_desktop:
            gtk_desktops = ['Unity', 'GNOME', 'XFCE']
            if any([xdg_desktop.startswith(d) for d in gtk_desktops]):
                return True
            else:
                return False
        else:
            return False
    else:
        return False


def is_kde_desktop():
    """Detect if we are running in a KDE desktop"""
    if sys.platform.startswith('linux'):
        xdg_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
        if xdg_desktop:
            if 'KDE' in xdg_desktop:
                return True
            else:
                return False
        else:
            return False
    else:
        return False


def is_anaconda():
    """
    Detect if we are running under Anaconda.

    Taken from https://stackoverflow.com/a/47610844/438386
    """
    is_conda = osp.exists(osp.join(sys.prefix, 'conda-meta'))
    return is_conda
