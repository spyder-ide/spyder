#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities to process and convert svg images to png using palette colors.
"""

# Standard library imports
from __future__ import absolute_import, division, print_function

import logging
import os
import re
import sys
import tempfile

# Third party imports
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication

# Local imports
from qdarkstyle import (IMAGES_PATH, PACKAGE_PATH, QRC_FILE,
                        STYLES_SCSS_FILEPATH, SVG_PATH)


IMAGE_BLACKLIST = ['base_palette']

TEMPLATE_QRC_HEADER = '''
<RCC warning="WARNING! File created programmatically. All changes made in this file will be lost!">
  <qresource prefix="{resource_prefix}">
'''

TEMPLATE_QRC_FILE = '    <file>rc/{fname}</file>'

TEMPLATE_QRC_FOOTER = '''
  </qresource>
  <qresource prefix="{style_prefix}">
      <file>style.qss</file>
  </qresource>
</RCC>
'''

_logger = logging.getLogger(__name__)


def _get_file_color_map(fname, palette):
    """
    Return map of files (i.e states) to color from given palette.
    """
    color_disabled = palette.COLOR_BACKGROUND_4
    color_focus = palette.COLOR_ACCENT_5
    color_pressed = palette.COLOR_ACCENT_2
    color_normal = palette.COLOR_TEXT_1

    name, ext = fname.split('.')
    file_colors = {
        fname: color_normal,
        name + '_disabled.' + ext: color_disabled,
        name + '_focus.' + ext: color_focus,
        name + '_pressed.' + ext: color_pressed,
    }

    return file_colors


def _create_colored_svg(svg_path, temp_svg_path, color):
    """
    Replace base svg with fill color.
    """
    with open(svg_path, 'r') as fh:
        data = fh.read()

    base_color = '#ff0000'  # Hardcoded in base svg files
    new_data = data.replace(base_color, color)

    with open(temp_svg_path, 'w') as fh:
        fh.write(new_data)


def convert_svg_to_png(svg_path, png_path, height, width):
    """
    Convert svg files to png files using Qt.
    """
    size = QSize(height, width)
    icon = QIcon(svg_path)
    pixmap = icon.pixmap(size)
    img = pixmap.toImage()
    img.save(png_path)


def create_palette_image(base_svg_path=SVG_PATH, path=IMAGES_PATH,
                         palette=None):
    """
    Create palette image svg and png image on specified path.
    """
    # Needed to use QPixmap
    _ = QApplication([])

    if palette is None:
        print("Please pass a palette class in order to create its "
              "associated images")
        sys.exit(1)

    if palette.ID is None:
        print("A QDarkStyle palette requires an ID!")
        sys.exit(1)

    base_palette_svg_path = os.path.join(base_svg_path, 'base_palette.svg')
    palette_svg_path = os.path.join(path, palette.ID, 'palette.svg')
    palette_png_path = os.path.join(path, palette.ID, 'palette.png')

    _logger.info("Creating palette image ...")
    _logger.info("Base SVG: %s" % base_palette_svg_path)
    _logger.info("To SVG: %s" % palette_svg_path)
    _logger.info("To PNG: %s" % palette_png_path)

    with open(base_palette_svg_path, 'r') as fh:
        data = fh.read()

    color_palette = palette.color_palette()

    for color_name, color_value in color_palette.items():
        data = data.replace('{{ ' + color_name + ' }}', color_value.lower())

    with open(palette_svg_path, 'w+') as fh:
        fh.write(data)

    convert_svg_to_png(palette_svg_path, palette_png_path, 4000, 4000)

    return palette_svg_path, palette_png_path


def create_images(base_svg_path=SVG_PATH, rc_path=None, palette=None):
    """Create resources `rc` png image files from base svg files and palette.

    Search all SVG files in `base_svg_path` excluding IMAGE_BLACKLIST,
    change its colors using `palette` creating temporary SVG files, for each
    state generating PNG images for each size `heights`.

    Args:
        base_svg_path (str, optional): [description]. Defaults to SVG_PATH.
        rc_path (str, optional): [description].
        palette (Palette, optional): Palette.
    """

    # Needed to use QPixmap
    _ = QApplication([])

    if palette is None:
        print("Please pass a palette class in order to create its "
              "associated file")
        sys.exit(1)

    if palette.ID is None:
        print("A QDarkStyle palette requires an ID!")
        sys.exit(1)

    if not rc_path:
        rc_path = os.path.join(PACKAGE_PATH, palette.ID, 'rc')

    temp_dir = tempfile.mkdtemp()
    svg_fnames = [f for f in os.listdir(base_svg_path) if f.endswith('.svg')]
    base_height = 32

    # See: https://doc.qt.io/qt-5/scalability.html
    heights = {
        32: '.png',
        64: '@2x.png',
    }

    _logger.info("Creating images ...")
    _logger.info("SVG folder: %s" % base_svg_path)
    _logger.info("TMP folder: %s" % temp_dir)
    _logger.info("PNG folder: %s" % rc_path)

    num_svg = len(svg_fnames)
    num_png = 0
    num_ignored = 0

    # Get rc links from scss to check matches
    rc_list = get_rc_links_from_scss()
    num_rc_list = len(rc_list)

    for height, ext in heights.items():
        width = height

        _logger.debug(" Size HxW (px): %s X %s" % (height, width))

        for svg_fname in svg_fnames:
            svg_name = svg_fname.split('.')[0]

            # Skip blacklist
            if svg_name not in IMAGE_BLACKLIST:
                svg_path = os.path.join(base_svg_path, svg_fname)
                color_files = _get_file_color_map(svg_fname, palette=palette)

                _logger.debug("  Working on: %s"
                              % os.path.basename(svg_fname))

                # Replace colors and create all file for different states
                for color_svg_name, color in color_files.items():
                    temp_svg_path = os.path.join(temp_dir, color_svg_name)
                    _create_colored_svg(svg_path, temp_svg_path, color)

                    png_fname = color_svg_name.replace('.svg', ext)
                    png_path = os.path.join(rc_path, png_fname)
                    convert_svg_to_png(temp_svg_path, png_path, height, width)
                    num_png += 1
                    _logger.debug("   Creating: %s"
                                  % os.path.basename(png_fname))

                    # Check if the rc_name is in the rc_list from scss
                    # only for the base size
                    if height == base_height:
                        rc_base = os.path.basename(rc_path)
                        png_base = os.path.basename(png_fname)
                        rc_name = '/' + os.path.join(rc_base, png_base)
                        try:
                            rc_list.remove(rc_name)
                        except ValueError:
                            pass
            else:
                num_ignored += 1
                _logger.debug("  Ignored blacklist: %s"
                              % os.path.basename(svg_fname))

    _logger.info("# SVG files: %s" % num_svg)
    _logger.info("# SVG ignored: %s" % num_ignored)
    _logger.info("# PNG files: %s" % num_png)
    _logger.info("# RC links: %s" % num_rc_list)
    _logger.info("# RC links not in RC: %s" % len(rc_list))
    _logger.info("RC links not in RC: %s" % rc_list)


def generate_qrc_file(resource_prefix='qss_icons', style_prefix='qdarkstyle',
                      palette=None):
    """
    Generate the QRC file programmaticaly.

    Search all RC folder for PNG images and create a QRC file.

    Args:
        resource_prefix (str, optional): Prefix used in resources.
            Defaults to 'qss_icons'.
        style_prefix (str, optional): Prefix used to this style.
            Defaults to 'qdarkstyle'.
        palette (Palette, optional): Palette.
    """

    files = []

    if palette is None:
        print("Please pass a palette class in order to create its "
              "qrc file")
        sys.exit(1)

    if palette.ID is None:
        print("A QDarkStyle palette requires an ID!")
        sys.exit(1)

    rc_path = os.path.join(PACKAGE_PATH, palette.ID, 'rc')
    qrc_filepath = os.path.join(PACKAGE_PATH, palette.ID, QRC_FILE)
    resource_prefix = resource_prefix + '/' + palette.ID
    style_prefix = style_prefix + '/' + palette.ID

    _logger.info("Generating QRC file ...")
    _logger.info("Resource prefix: %s" % resource_prefix)
    _logger.info("Style prefix: %s" % style_prefix)

    _logger.info("Searching in: %s" % rc_path)

    # Search by png images
    for fname in sorted(os.listdir(rc_path)):
        files.append(TEMPLATE_QRC_FILE.format(fname=fname))

    # Join parts
    qrc_content = (TEMPLATE_QRC_HEADER.format(resource_prefix=resource_prefix)
                   + '\n'.join(files)
                   + TEMPLATE_QRC_FOOTER.format(style_prefix=style_prefix))

    _logger.info("Writing in: %s" % qrc_filepath)

    # Write qrc file
    with open(qrc_filepath, 'w') as fh:
        fh.write(qrc_content)


def get_rc_links_from_scss(pattern=r"\/.*\.png"):
    """
    Get all rc links from scss file returning the list of unique links.

    Args:
        pattern (str): regex pattern to find the links.

    Returns:
        list(str): list of unique links found.
    """

    with open(STYLES_SCSS_FILEPATH, 'r') as fh:
        data = fh.read()

    lines = data.split("\n")
    compiled_exp = re.compile('(' + pattern + ')')

    rc_list = []

    for line in lines:
        match = re.search(compiled_exp, line)
        if match:
            rc_list.append(match.group(1))

    rc_list = list(set(rc_list))

    return rc_list
