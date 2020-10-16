# -*- coding: utf-8 -*-
"""
Settings file for building the dmg disk image.
Adapted from dmgbuild example:
    https://github.com/al45tair/dmgbuild/blob/master/examples/settings.py

"""
format = 'UDBZ'

# Volume size
size = None

# Symlinks to create
symlinks = {'Applications': '/Applications'}

# Background
background = 'builtin-arrow'

default_view = 'icon-view'

text_size = 14
icon_size = 96
