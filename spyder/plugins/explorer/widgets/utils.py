# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Explorer widget utilities."""

# Standard library imports
import os
import os.path as osp
import re
import subprocess
import sys

# Third-party imports
from qtpy.QtCore import QFileInfo, Slot
from qtpy.QtWidgets import QFileIconProvider, QMessageBox

# Local imports
from spyder.api.translations import get_translation
from spyder.py3compat import str_lower
from spyder.utils import encoding
from spyder.utils.icon_manager import ima


_ = get_translation('spyder')


def open_file_in_external_explorer(filename):
    if sys.platform == "darwin":
        subprocess.call(["open", "-R", filename])
    elif os.name == 'nt':
        subprocess.call(["explorer", "/select,", filename])
    else:
        filename = os.path.dirname(filename)
        subprocess.call(["xdg-open", filename])


def show_in_external_file_explorer(fnames=None):
    """Show files in external file explorer

    Args:
        fnames (list): Names of files to show.
    """
    if not isinstance(fnames, (tuple, list)):
        fnames = [fnames]
    for fname in fnames:
        open_file_in_external_explorer(fname)


def fixpath(path):
    """Normalize path fixing case, making absolute and removing symlinks"""
    norm = osp.normcase if os.name == 'nt' else osp.normpath
    return norm(osp.abspath(osp.realpath(path)))


def create_script(fname):
    """Create a new Python script"""
    text = os.linesep.join(["# -*- coding: utf-8 -*-", "", ""])
    try:
        encoding.write(str(text), fname, 'utf-8')
    except EnvironmentError as error:
        QMessageBox.critical(_("Save Error"),
                             _("<b>Unable to save file '%s'</b>"
                               "<br><br>Error message:<br>%s"
                               ) % (osp.basename(fname), str(error)))


def listdir(path, include=r'.', exclude=r'\.pyc$|^\.', folders_only=False):
    """List files and directories"""
    namelist = []
    dirlist = [str(osp.pardir)]
    for item in os.listdir(str(path)):
        if re.search(exclude, item):
            continue
        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif folders_only:
            continue
        elif re.search(include, item):
            namelist.append(item)
    return sorted(dirlist, key=str_lower) + sorted(namelist, key=str_lower)


def has_subdirectories(path, include, exclude):
    """Return True if path has subdirectories"""
    try:
        # > 1 because of '..'
        return len(listdir(path, include, exclude, folders_only=True)) > 1
    except (IOError, OSError):
        return False


class IconProvider(QFileIconProvider):
    """Project tree widget icon provider"""

    def __init__(self, treeview):
        super(IconProvider, self).__init__()
        self.treeview = treeview

    @Slot(int)
    @Slot(QFileInfo)
    def icon(self, icontype_or_qfileinfo):
        """Reimplement Qt method"""
        if isinstance(icontype_or_qfileinfo, QFileIconProvider.IconType):
            return super(IconProvider, self).icon(icontype_or_qfileinfo)
        else:
            qfileinfo = icontype_or_qfileinfo
            fname = osp.normpath(str(qfileinfo.absoluteFilePath()))
            if osp.isfile(fname) or osp.isdir(fname):
                icon = ima.get_icon_by_extension_or_type(fname,
                                                         scale_factor=1.0)
            else:
                icon = ima.icon('binary')
            return icon
