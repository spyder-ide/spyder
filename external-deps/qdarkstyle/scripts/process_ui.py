# -*- coding: utf-8 -*-
"""Script to process UI files (convert .ui to .py).

It compiles .ui files to be used with PyQt4, PyQt5, PySide, QtPy, PyQtGraph.
You just need to run (it has default values) from script folder.

To run this script you need to have these tools available on system:

    - pyuic4 for PyQt4 and PyQtGraph
    - pyuic5 for PyQt5 and QtPy
    - pyside-uic for Pyside
    - pyside2-uic for Pyside2

Links to understand those tools:

    - pyuic4: http://pyqt.sourceforge.net/Docs/PyQt4/designer.html#pyuic4
    - pyuic5: http://pyqt.sourceforge.net/Docs/PyQt5/designer.html#pyuic5
    - pyside-uic: https://www.mankier.com/1/pyside-uic
    - pyside2-uic: https://wiki.qt.io/Qt_for_Python_UiFiles (Documentation Incomplete)

"""

# Standard library imports
from __future__ import absolute_import, print_function
from subprocess import call
import argparse
import glob
import os
import sys

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(HERE)


def main(arguments):
    """Process UI files."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ui_dir',
                        default=os.path.join(REPO_ROOT, 'example', 'ui'),
                        type=str,
                        help="UI files directory, relative to current directory.",)
    parser.add_argument('--create',
                        default='qtpy',
                        choices=['pyqt', 'pyqt5', 'pyside', 'pyside2', 'qtpy', 'pyqtgraph', 'all'],
                        type=str,
                        help="Choose which one would be generated.")

    args = parser.parse_args(arguments)

    print('Changing directory to: ', args.ui_dir)
    os.chdir(args.ui_dir)

    print('Converting .ui to .py ...')

    for ui_file in glob.glob('*.ui'):
        # get name without extension
        filename = os.path.splitext(ui_file)[0]
        print(filename, '...')
        ext = '.py'

        # creating names
        py_file_pyqt5 = filename + '_pyqt5_ui' + ext
        py_file_pyqt = filename + '_pyqt_ui' + ext
        py_file_pyside = filename + '_pyside_ui' + ext
        py_file_pyside2 = filename + '_pyside2_ui' + ext
        py_file_qtpy = filename + '_ui' + ext
        py_file_pyqtgraph = filename + '_pyqtgraph_ui' + ext

        # calling external commands
        if args.create in ['pyqt', 'pyqtgraph', 'all']:
            try:
                call(['pyuic4', '--import-from=qdarkstyle', ui_file, '-o', py_file_pyqt])
            except Exception as er:
                print("You must install pyuic4 %s" % str(er))
            else:
                print("Compiling using pyuic4 ...")

        if args.create in ['pyqt5', 'qtpy', 'all']:
            try:
                call(['pyuic5', '--import-from=qdarkstyle', ui_file, '-o', py_file_pyqt5])
            except Exception as er:
                print("You must install pyuic5 %s" % str(er))
            else:
                print("Compiling using pyuic5 ...")

        if args.create in ['pyside', 'all']:
            try:
                call(['pyside-uic', '--import-from=qdarkstyle', ui_file, '-o', py_file_pyside])
            except Exception as er:
                print("You must install pyside-uic %s" % str(er))
            else:
                print("Compiling using pyside-uic ...")

        if args.create in ['pyside2', 'all']:
            try:
                call(['pyside2-uic', '--import-from=qdarkstyle', ui_file, '-o', py_file_pyside2])
            except Exception as er:
                print("You must install pyside2-uic %s" % str(er))
            else:
                print("Compiling using pyside2-uic ...")

        if args.create in ['qtpy', 'all']:
            print("Creating also for qtpy ...")
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
            print("Creating also for pyqtgraph ...")
            # special case - pyqtgraph - syntax is PyQt4
            with open(py_file_pyqt, 'r') as file:
                filedata = file.read()

            # replace the target string
            filedata = filedata.replace('from PyQt4', 'from pyqtgraph.Qt')

            with open(py_file_pyqtgraph, 'w+') as file:
                # write the file out again
                file.write(filedata)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
