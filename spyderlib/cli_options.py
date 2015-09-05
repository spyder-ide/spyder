# -*- coding: utf-8 -*-
#
# Copyright © 2012 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import optparse

def get_options():
    """
    Convert options into commands
    return commands, message
    """
    parser = optparse.OptionParser(usage="spyder [options] files")
    parser.add_option('-l', '--light', action='store_true', default=False,
                      help="Light version (all add-ons are disabled)")
    parser.add_option('--new-instance', action='store_true', default=False,
                      help="Run a new instance of Spyder, even if the single "
                           "instance mode has been turned on (default)")
    parser.add_option('--session', dest="startup_session", default='',
                      help="Startup session")
    parser.add_option('--defaults', dest="reset_to_defaults",
                      action='store_true', default=False,
                      help="Reset configuration settings to defaults")
    parser.add_option('--reset', dest="reset_session",
                      action='store_true', default=False,
                      help="Remove all configuration files!")
    parser.add_option('--optimize', action='store_true', default=False,
                      help="Optimize Spyder bytecode (this may require "
                           "administrative privileges)")
    parser.add_option('-w', '--workdir', dest="working_directory", default=None,
                      help="Default working directory")
    parser.add_option('--show-console', action='store_true', default=False,
                      help="Do not hide parent console window (Windows)")
    parser.add_option('--multithread', dest="multithreaded",
                      action='store_true', default=False,
                      help="Internal console is executed in another thread "
                           "(separate from main application thread)")
    parser.add_option('--profile', action='store_true', default=False,
                      help="Profile mode (internal test, "
                           "not related with Python profiling)")
    options, args = parser.parse_args()
    return options, args
