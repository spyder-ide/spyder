#!/usr/bin/env python

"""Generates a configuration options document for Sphinx.

Using this helper tool, a reStructuredText document can be created from
reading the config options from the JupyterQtConsole source code that may
be set in config file, `jupyter_qtconsole_config.py`, and writing to the rST
doc, `config_options.rst`.

"""
import os.path
from qtconsole.qtconsoleapp import JupyterQtConsoleApp

header = """\
Configuration options
=====================

These options can be set in the configuration file,
``~/.jupyter/jupyter_qtconsole_config.py``, or
at the command line when you start Qt console.

You may enter ``jupyter qtconsole --help-all`` to get information
about all available configuration options.

Options
-------
"""

destination = os.path.join(os.path.dirname(__file__), 'source/config_options.rst')

def main():
    with open(destination, 'w') as f:
        f.write(header)
        f.write(JupyterQtConsoleApp().document_config_options())

if __name__ == '__main__':
    main()
