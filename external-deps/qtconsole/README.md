# Jupyter QtConsole

[![Tests](https://github.com/spyder-ide/qtconsole/actions/workflows/tests.yaml/badge.svg)](https://github.com/spyder-ide/qtconsole/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/spyder-ide/qtconsole/badge.svg?branch=main)](https://coveralls.io/github/spyder-ide/qtconsole?branch=main)
[![Documentation Status](https://readthedocs.org/projects/qtconsole/badge/?version=stable)](https://qtconsole.readthedocs.io/en/stable/)

A rich Qt-based console for working with Jupyter kernels,
supporting rich media output, session export, and more.

The Qtconsole is a very lightweight application that largely feels like a terminal, but
provides a number of enhancements only possible in a GUI, such as inline
figures, proper multiline editing with syntax highlighting, graphical calltips,
and more.

This project is maintained by the Spyder development team and part of its organization.

![qtconsole](https://raw.githubusercontent.com/spyder-ide/qtconsole/master/docs/source/_images/qtconsole.png)

## Install Qtconsole
The Qtconsole requires Python bindings for Qt, such as [PyQt6](https://pypi.org/project/PyQt6/), [PySide6](https://pypi.org/project/PySide6/), [PyQt5](https://pypi.org/project/PyQt5/) or [PySide2](https://pypi.org/project/PySide2/).

Although [pip](https://pypi.python.org/pypi/pip) and
[conda](http://conda.pydata.org/docs) may be used to install the Qtconsole, conda
is simpler to use since it automatically installs PyQt5. Alternatively,
the Qtconsole installation with pip needs additional steps since pip doesn't install
the Qt requirement.

### Install using conda
To install:

    conda install qtconsole

**Note:** If the Qtconsole is installed using conda, it will **automatically**
install the Qt requirement as well.

### Install using pip
To install:

    pip install qtconsole

**Note:** Make sure that Qt is installed. Unfortunately, Qt is not
installed when using pip. The next section gives instructions on doing it.

### Installing Qt (if needed)
You can install PyQt5 with pip using the following command:

    pip install pyqt5

or with a system package manager on Linux. For Windows, PyQt binary packages may be
used.

**Note:** Additional information about using a system package manager may be
found in the [qtconsole documentation](https://qtconsole.readthedocs.io).

## Usage
To run the Qtconsole:

    jupyter qtconsole

## Resources
- [Project Jupyter website](https://jupyter.org)
- [Spyder website](https://www.spyder-ide.org)
- [Documentation for the Qtconsole](https://qtconsole.readthedocs.io/en/stable/)
- [Issues](https://github.com/spyder-ide/qtconsole/issues)
