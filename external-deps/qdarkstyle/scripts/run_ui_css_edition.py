#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process qrc, ui, image, and screenshot files, then run example in while loop.
"""

# Standard library imports
from __future__ import absolute_import, print_function

import argparse
from subprocess import call
import os
import sys
import tempfile

# Constants
SCRIPTS_PATH = os.path.abspath(os.path.dirname(__file__))


def main():
    """Process qrc and ui files, then run example in while loop."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--palette',
                        default='dark',
                        choices=['dark', 'light'],
                        type=str,
                        help="Palette to display",)

    # Parsing arguments from command line
    args = parser.parse_args()
    palette = args.palette

    styled = None
    no_styled = None
    themes = {'Styled': styled, 'No styled': no_styled}
    while True:
        for theme_name, theme_process in themes.items():
            try:
                theme_process.kill()
            except AttributeError:
                print(theme_name + ' not running!')
            except Exception:
                print(theme_name + ' still running!')
            else:
                print(theme_name + ' was killed!')

        print(sys.argv)

        # Process qrc files
        process_qrc = os.path.join(SCRIPTS_PATH, '../qdarkstyle/utils/__main__.py')
        call(['python', process_qrc], shell=True)

        # Show window
        example = os.path.join(SCRIPTS_PATH, '../qdarkstyle/example/__main__.py')

        # Open styled window
        styled = call(['python', example, '--palette', palette] + sys.argv[1:], shell=True)

        # Open unstyled window
        no_styled = call(['python', example, '--palette', 'none'] + sys.argv[1:], shell=True)

        if styled or no_styled:
            print('Unf! It not worked! Please, check the error(s).')
            break


if __name__ == "__main__":
    sys.exit(main())
