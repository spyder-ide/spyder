#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities for processing SASS and images from default and custom palette.
"""

# Standard library imports
from __future__ import absolute_import, print_function

import glob
import os
from subprocess import call

# Local imports
from qdarkstyle import PACKAGE_PATH
from qdarkstyle.utils.images import (create_images, create_palette_image,
                                     generate_qrc_file)
from qdarkstyle.utils.scss import create_qss


def run_process(args, palette):
    """Process qrc files."""
    # Generate qrc file based on the content of the resources folder

    id_ = palette.ID

    # Create palette and resources png images
    print('Generating {} palette image ...'.format(id_))
    create_palette_image(palette=palette)

    print('Generating {} images ...'.format(id_))
    create_images(palette=palette)

    print('Generating {} qrc ...'.format(id_))
    generate_qrc_file(palette=palette)

    print('Converting .qrc to _rc.py and/or .rcc ...')

    if not args.qrc_dir:
        main_dir = os.path.join(PACKAGE_PATH, palette.ID)
        os.chdir(main_dir)

    for qrc_file in glob.glob('*.qrc'):
        # get name without extension
        filename = os.path.splitext(qrc_file)[0]

        print(filename, '...')
        ext = '_rc.py'
        ext_c = '.rcc'

        # Create variables SCSS files and compile SCSS files to QSS
        print('Compiling SCSS/SASS files to QSS ...')
        create_qss(palette=palette)

        # creating names
        py_file_pyqt5 = 'pyqt5_' + filename + ext
        py_file_pyqt = 'pyqt_' + filename + ext
        py_file_pyside = 'pyside_' + filename + ext
        py_file_pyside2 = 'pyside2_' + filename + ext
        py_file_qtpy = '' + filename + ext
        py_file_pyqtgraph = 'pyqtgraph_' + filename + ext

        # calling external commands
        if args.create in ['pyqt', 'pyqtgraph', 'all']:
            print("Compiling for PyQt4 ...")
            try:
                call(['pyrcc4', '-py3', qrc_file, '-o', py_file_pyqt], shell=True)
            except FileNotFoundError:
                print("You must install pyrcc4")

        if args.create in ['pyqt5', 'qtpy', 'all']:
            print("Compiling for PyQt5 ...")
            try:
                call(['pyrcc5', qrc_file, '-o', py_file_pyqt5], shell=True)
            except FileNotFoundError:
                print("You must install pyrcc5")

        if args.create in ['pyside', 'all']:
            print("Compiling for PySide ...")
            try:
                call(['pyside-rcc', '-py3', qrc_file, '-o', py_file_pyside], shell=True)
            except FileNotFoundError:
                print("You must install pyside-rcc")

        if args.create in ['pyside2', 'all']:
            print("Compiling for PySide 2...")
            try:
                call(['pyside2-rcc', qrc_file, '-o', py_file_pyside2], shell=True)
            except FileNotFoundError:
                print("You must install pyside2-rcc")

        if args.create in ['qtpy', 'all']:
            print("Compiling for QtPy ...")
            # special case - qtpy - syntax is PyQt5
            with open(py_file_pyqt5, 'r') as file:
                filedata = file.read()

            # replace the target string
            filedata = filedata.replace('from PyQt5', 'from qtpy')

            with open(py_file_qtpy, 'w+') as file:
                # write the file out again
                file.write(filedata)

            if args.create not in ['pyqt5']:
                os.remove(py_file_pyqt5)

        if args.create in ['pyqtgraph', 'all']:
            print("Compiling for PyQtGraph ...")
            # special case - pyqtgraph - syntax is PyQt4
            with open(py_file_pyqt, 'r') as file:
                filedata = file.read()

            # replace the target string
            filedata = filedata.replace('from PyQt4', 'from pyqtgraph.Qt')

            with open(py_file_pyqtgraph, 'w+') as file:
                # write the file out again
                file.write(filedata)
