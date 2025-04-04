# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Contains the bookmarsks utilities.
"""
# Standard imports
import os.path as osp


def _load_all_bookmarks(slots):
    """Load all bookmarks from config."""
    if not slots:
        slots = {}
    for slot_num in list(slots.keys()):
        if not osp.isfile(slots[slot_num][0]):
            slots.pop(slot_num)
    return slots


def load_bookmarks(filename, slots):
    """Load all bookmarks for a specific file from config."""
    bookmarks = _load_all_bookmarks(slots)
    return {k: v for k, v in bookmarks.items() if v[0] == filename}


def load_bookmarks_without_file(filename, slots):
    """Load all bookmarks but those from a specific file."""
    bookmarks = _load_all_bookmarks(slots)
    return {k: v for k, v in bookmarks.items() if v[0] != filename}


def update_bookmarks(filename, bookmarks, old_slots):
    """
    Compute an updated version of all the bookmarks from a specific file.

    Parameters
    ----------
    filename : str
        File path that the bookmarks are related too.
    bookmarks : dict
        New or changed bookmarks for the file.
    old_slots : dict
        Base general bookmarks entries available before any changes where done.

    Returns
    -------
    updated_slots : dict
        Updated general bookmarks.

    """
    if not osp.isfile(filename):
        return
    updated_slots = load_bookmarks_without_file(filename, old_slots)
    for slot_num, content in bookmarks.items():
        updated_slots[slot_num] = [filename, content[0], content[1]]
    return updated_slots
