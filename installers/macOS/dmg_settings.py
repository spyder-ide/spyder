# -*- coding: utf-8 -*-
"""
Settings file for building the dmg disk image.
Adapted from dmgbuild example: https://github.com/al45tair/dmgbuild/blob/master/examples/settings.py

"""
import os.path

application = defines.get('app', None)
appname = os.path.basename(application)

format = 'UDBZ'

# Volume size
size = None

# Files to include
files = [ application ]

# Symlinks to create
symlinks = { 'Applications': '/Applications' }

# Volume icon
badge_icon = defines.get('badge_icon')

# Where to put the icons
icon_locations = {
    appname:        (140, 120),
    'Applications': (500, 120)
    }

# Background
background = 'builtin-arrow'

default_view = 'icon-view'

text_size = 14
icon_size = 96
