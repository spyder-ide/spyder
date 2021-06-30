# -*- coding: utf-8 -*-
"""Script to process QRC files (convert .qrc to _rc.py and .rcc).

The script will attempt to compile the qrc file using the following tools:

    - pyrcc4 for PyQt4 and PyQtGraph (Python)
    - pyrcc5 for PyQt5 and QtPy (Python)
    - pyside-rcc for PySide (Python)
    - pyside2-rcc for PySide2 (Python)
    - rcc for Qt4 and Qt5 (C++)

Delete the compiled files that you don't want to use manually after
running this script.

Links to understand those tools:

    - pyrcc4: http://pyqt.sourceforge.net/Docs/PyQt4/resources.html#pyrcc4
    - pyrcc5: http://pyqt.sourceforge.net/Docs/PyQt5/resources.html#pyrcc5
    - pyside-rcc: https://www.mankier.com/1/pyside-rcc
    - pyside2-rcc: https://doc.qt.io/qtforpython/overviews/resources.html (Documentation Incomplete)
    - rcc on Qt4: http://doc.qt.io/archives/qt-4.8/rcc.html
    - rcc on Qt5: http://doc.qt.io/qt-5/rcc.html

"""

# Standard library imports
from __future__ import absolute_import, print_function

import argparse
import glob
import os
import sys
from subprocess import call

# Third party imports
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Local imports
from qdarkstyle import PACKAGE_PATH
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
from qdarkstyle.utils import run_process
from qdarkstyle.utils.images import (create_images, create_palette_image,
                                     generate_qrc_file)
from qdarkstyle.utils.scss import create_qss


class QSSFileHandler(FileSystemEventHandler):
    """QSS File observer."""

    def __init__(self, parser_args):
        """QSS File observer."""
        super(QSSFileHandler, self).__init__()
        self.args = parser_args

    def on_modified(self, event):
        """Handle file system events."""
        if event.src_path.endswith('.qss'):
            run_process(self.args)
            print('\n')


def main():
    """Process QRC files."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--qrc_dir',
                        default=None,
                        type=str,
                        help="QRC file directory, relative to current directory.",)
    parser.add_argument('--create',
                        default='qtpy',
                        choices=['pyqt', 'pyqt5', 'pyside', 'pyside2', 'qtpy', 'pyqtgraph', 'qt', 'qt5', 'all'],
                        type=str,
                        help="Choose which one would be generated.")
    parser.add_argument('--watch', '-w',
                        action='store_true',
                        help="Watch for file changes.")

    args = parser.parse_args()

    if args.watch:
        path = PACKAGE_PATH
        observer = Observer()
        handler = QSSFileHandler(parser_args=args)
        observer.schedule(handler, path, recursive=True)
        try:
            print('\nWatching QSS file for changes...\nPress Ctrl+C to exit\n')
            observer.start()
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        for palette in [DarkPalette, LightPalette]:
            run_process(args, palette)


if __name__ == "__main__":
    sys.exit(main())
