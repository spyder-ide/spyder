# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import optparse

def get_options():
    """
    Convert options into commands
    return commands, message
    """
    parser = optparse.OptionParser(usage="spyder [options] files")
    parser.add_option('--new-instance', action='store_true', default=False,
                      help="Run a new instance of Spyder, even if the single "
                           "instance mode has been turned on (default)")
    parser.add_option('--defaults', dest="reset_to_defaults",
                      action='store_true', default=False,
                      help="Reset configuration settings to defaults")
    parser.add_option('--reset', dest="reset_config_files",
                      action='store_true', default=False,
                      help="Remove all configuration files!")
    parser.add_option('--optimize', action='store_true', default=False,
                      help="Optimize Spyder bytecode (this may require "
                           "administrative privileges)")
    parser.add_option('-w', '--workdir', dest="working_directory", default=None,
                      help="Default working directory")
    parser.add_option('--hide-console', action='store_true', default=False,
                      help="Hide parent console window (Windows)")
    parser.add_option('--show-console', action='store_true', default=False,
                      help="(Deprecated) Do nothing, now the default behavior "
                      "is to show the console")
    parser.add_option('--multithread', dest="multithreaded",
                      action='store_true', default=False,
                      help="Internal console is executed in another thread "
                           "(separate from main application thread)")
    parser.add_option('--profile', action='store_true', default=False,
                      help="Profile mode (internal test, "
                           "not related with Python profiling)")
    parser.add_option('--window-title', type=str, default=None,
                      help="String to show in the main window title")
    parser.add_option('-p', '--project', default=None, type=str,
                      dest="open_project",
                      help="Path that contains an Spyder project")
    options, args = parser.parse_args()
    return options, args
