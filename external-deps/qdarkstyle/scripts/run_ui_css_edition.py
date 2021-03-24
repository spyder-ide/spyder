#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process qrc, ui, image, and screenshot files, then run example in while loop.
"""

# Standard library imports
from __future__ import absolute_import, print_function
from subprocess import call
import os
import sys

# Constants
SCRIPTS_PATH = os.path.abspath(os.path.dirname(__file__))
REPO_PATH = os.path.dirname(SCRIPTS_PATH)


def main():
    """Process qrc and ui files, then run example in while loop."""
    dark = None
    no_dark = None
    themes = {'Dark': dark, 'No Dark': no_dark}
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

        # Process images
        process_images = os.path.join(SCRIPTS_PATH, 'process_images.py')
        call(['python', process_images])

        # Process qrc files
        process_qrc = os.path.join(SCRIPTS_PATH, 'process_qrc.py')
        call(['python', process_qrc])

        # Process ui files
        process_ui = os.path.join(SCRIPTS_PATH, 'process_ui.py')
        call(['python', process_ui])

        # Create screenshots
        example = os.path.join(REPO_PATH, 'example', 'example.py')
        call(['python', example, '--screenshots'])
        call(['python', example, '--no_dark', '--screenshots'])

        # Open dark example
        dark = call(['python', example] + sys.argv[1:])

        # Open no dark example
        no_dark = call(['python', example, '--no_dark'] + sys.argv[1:])

        if dark or no_dark:
            print('Unf! It not worked! Please, check the error(s).')
            break


if __name__ == "__main__":
    sys.exit(main())
