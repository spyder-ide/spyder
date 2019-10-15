# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Utils to handle Switcher elements.
"""

# Standard library imports
import os
import os.path as osp
import sys

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, PY2
from spyder.utils import icon_manager as ima

if PY2:
    from itertools import izip as zip


def shorten_paths(path_list, is_unsaved):
    """
    Takes a list of paths and tries to "intelligently" shorten them all. The
    aim is to make it clear to the user where the paths differ, as that is
    likely what they care about. Note that this operates on a list of paths
    not on individual paths.

    If the path ends in an actual file name, it will be trimmed off.
    """
    # TODO: at the end, if the path is too long, should do a more dumb kind of
    # shortening, but not completely dumb.

    # Convert the path strings to a list of tokens and start building the
    # new_path using the drive
    path_list = path_list[:]  # Make a local copy
    new_path_list = []
    common_prefix = osp.dirname(osp.commonprefix(path_list))

    for ii, (path, is_unsav) in enumerate(zip(path_list, is_unsaved)):
        if is_unsav:
            new_path_list.append(_('unsaved file'))
            path_list[ii] = None
        else:
            drive, path = osp.splitdrive(osp.dirname(path))
            new_path_list.append(drive + osp.sep)
            path_list[ii] = [part for part in path.split(osp.sep) if part]

    def recurse_level(level_idx):
        sep = os.sep

        # If toks are all empty we need not have recursed here
        if not any(level_idx.values()):
            return

        # Firstly, find the longest common prefix for all in the level
        # s = len of longest common prefix
        sample_toks = list(level_idx.values())[0]
        if not sample_toks:
            s = 0
        else:
            for s, sample_val in enumerate(sample_toks):
                if not all(len(toks) > s and toks[s] == sample_val
                           for toks in level_idx.values()):
                    break

        # Shorten longest common prefix
        if s == 0:
            short_form = ''
        else:
            if s == 1:
                short_form = sample_toks[0]
            elif s == 2:
                short_form = sample_toks[0] + sep + sample_toks[1]
            else:
                short_form = "..." + sep + sample_toks[s-1]
            for idx in level_idx:
                new_path_list[idx] += short_form + sep
                level_idx[idx] = level_idx[idx][s:]

        # Group the remaining bit after the common prefix, shorten, and recurse
        while level_idx:
            k, group = 0, level_idx  # k is length of the group's common prefix
            while True:
                # Abort if we've gone beyond end of one or more in the group
                prospective_group = {idx: toks for idx, toks
                                     in group.items() if len(toks) == k}
                if prospective_group:
                    if k == 0:  # we spit out the group with no suffix
                        group = prospective_group
                    break
                # Only keep going if all n still match on the kth token
                _, sample_toks = next(iteritems(group))
                prospective_group = {idx: toks for idx, toks
                                     in group.items()
                                     if toks[k] == sample_toks[k]}
                if len(prospective_group) == len(group) or k == 0:
                    group = prospective_group
                    k += 1
                else:
                    break
            _, sample_toks = next(iteritems(group))
            if k == 0:
                short_form = ''
            elif k == 1:
                short_form = sample_toks[0]
            elif k == 2:
                short_form = sample_toks[0] + sep + sample_toks[1]
            else:  # k > 2
                short_form = sample_toks[0] + "..." + sep + sample_toks[k-1]
            for idx in group.keys():
                new_path_list[idx] += short_form + (sep if k > 0 else '')
                del level_idx[idx]
            recurse_level({idx: toks[k:] for idx, toks in group.items()})

    recurse_level({i: pl for i, pl in enumerate(path_list) if pl})

    if common_prefix:
        result_paths = []
        for path in new_path_list:
            path_elements = path.rstrip(os.sep).split(common_prefix)
            if len(path_elements) > 1:
                result_paths.append("...{}".format(path_elements[-1]))
            else:
                result_paths.append(path)
    else:
        result_paths = [path.rstrip(os.sep) for path in new_path_list]

    return result_paths


def get_file_icon(path):
    """Get icon for file by extension."""

    if sys.platform == 'darwin':
        scale_factor = 0.9
    elif os.name == 'nt':
        scale_factor = 0.8
    else:
        scale_factor = 0.6

    return ima.get_icon_by_extension_or_type(path, scale_factor)
