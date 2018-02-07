# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import argparse

def get_options(argv=None):
    """
    Convert options into commands
    return commands, message
    """
    parser = argparse.ArgumentParser(usage="spyder [options] files")
    parser.add_argument('--new-instance', action='store_true', default=False,
                      help="Run a new instance of Spyder, even if the single "
                           "instance mode has been turned on (default)")
    parser.add_argument('--defaults', dest="reset_to_defaults",
                      action='store_true', default=False,
                      help="Reset configuration settings to defaults")
    parser.add_argument('--reset', dest="reset_config_files",
                      action='store_true', default=False,
                      help="Remove all configuration files!")
    parser.add_argument('--optimize', action='store_true', default=False,
                      help="Optimize Spyder bytecode (this may require "
                           "administrative privileges)")
    parser.add_argument('-w', '--workdir', dest="working_directory", default=None,
                      help="Default working directory")
    parser.add_argument('--hide-console', action='store_true', default=False,
                      help="Hide parent console window (Windows)")
    parser.add_argument('--show-console', action='store_true', default=False,
                      help="(Deprecated) Does nothing, now the default behavior "
                      "is to show the console")
    parser.add_argument('--multithread', dest="multithreaded",
                      action='store_true', default=False,
                      help="Internal console is executed in another thread "
                           "(separate from main application thread)")
    parser.add_argument('--profile', action='store_true', default=False,
                      help="Profile mode (internal test, "
                           "not related with Python profiling)")
    parser.add_argument('--window-title', type=str, default=None,
                      help="String to show in the main window title")
    parser.add_argument('-p', '--project', default=None, type=str,
                      dest="open_project",
                      help="Path that contains an Spyder project")
    parser.add_argument('files', nargs='*')
    options = parser.parse_args(argv)
    args = options.files
    return options, args
