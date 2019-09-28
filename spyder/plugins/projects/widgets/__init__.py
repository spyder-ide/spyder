# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Projects"""

# Local imports
from spyder.plugins.projects.projecttypes import EmptyProject
from spyder.plugins.projects.projecttypes.python import PythonProject


def get_available_project_types():
    """Get available project types."""
    return ([EmptyProject] +
            get_available_project_types_plugins())


def get_available_project_types_plugins():
    """Return available project types."""
    return []


#def components(path):
#    '''
#    Returns the individual components of the given file path
#    string (for the local operating system).
#
#    The returned components, when joined with os.path.join(), point to
#    the same location as the original path.
#    '''
#    components = []
#    # The loop guarantees that the returned components can be
#    # os.path.joined with the path separator and point to the same
#    # location:
#    while True:
#        (new_path, tail) = osp.split(path)  # Works on any platform
#        components.append(tail)
#        if new_path == path:  # Root (including drive, on Windows) reached
#            break
#        path = new_path
#    components.append(new_path)
#
#    components.reverse()  # First component first
#    return components
#
#
#def longest_prefix(iter0, iter1):
#    '''
#    Returns the longest common prefix of the given two iterables.
#    '''
#    longest_prefix = []
#    for (elmt0, elmt1) in itertools.izip(iter0, iter1):
#        if elmt0 != elmt1:
#            break
#        longest_prefix.append(elmt0)
#    return longest_prefix
#
#
#def common_prefix_path(path0, path1):
#    return os.path.join(*longest_prefix(components(path0), components(path1)))
#

#
#def has_children_files(path, include, exclude, show_all):
#    """Return True if path has children files"""
#    try:
#        return len(listdir(path, include, exclude, show_all)) > 0
#    except (IOError, OSError):
#        return False
#
#
#def is_drive_path(path):
#    """Return True if path is a drive (Windows)"""
#    path = osp.abspath(path)
#    return osp.normpath(osp.join(path, osp.pardir)) == path
#
#
#def get_dir_icon(dirname, project):
#    """Return appropriate directory icon"""
#    if is_drive_path(dirname):
#        return get_std_icon('DriveHDIcon')
#    prefix = 'pp_' if dirname in project.get_pythonpath() else ''
#    if dirname == project.root_path:
#        if project.is_opened():
#            return get_icon(prefix+'project.png')
#        else:
#            return get_icon('project_closed.png')
#    elif osp.isfile(osp.join(dirname, '__init__.py')):
#        return get_icon(prefix+'package.png')
#    else:
#        return get_icon(prefix+'folder.png')
