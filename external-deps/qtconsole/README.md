# Jupyter QtConsole

![Windows tests](https://github.com/jupyter/qtconsole/workflows/Windows%20tests/badge.svg)
![Macos tests](https://github.com/jupyter/qtconsole/workflows/Macos%20tests/badge.svg)
![Linux tests](https://github.com/jupyter/qtconsole/workflows/Linux%20tests/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/jupyter/qtconsole/badge.svg?branch=master)](https://coveralls.io/github/jupyter/qtconsole?branch=master)
[![Documentation Status](https://readthedocs.org/projects/qtconsole/badge/?version=stable)](https://qtconsole.readthedocs.io/en/stable/)
[![Google Group](https://img.shields.io/badge/-Google%20Group-lightgrey.svg)](https://groups.google.com/forum/#!forum/jupyter)

A rich Qt-based console for working with Jupyter kernels,
supporting rich media output, session export, and more.

The Qtconsole is a very lightweight application that largely feels like a terminal, but
provides a number of enhancements only possible in a GUI, such as inline
figures, proper multiline editing with syntax highlighting, graphical calltips,
and more.

![qtconsole](https://raw.githubusercontent.com/jupyter/qtconsole/master/docs/source/_images/qtconsole.png)

## Install Qtconsole
The Qtconsole requires Python bindings for Qt, such as [PyQt5](http://www.riverbankcomputing.com/software/pyqt/intro),
[PyQt4](https://www.riverbankcomputing.com/software/pyqt/download),
or [PySide](http://pyside.github.io/docs/pyside).

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

More installation instructions for PyQt can be found in the [PyQt5 documentation](http://pyqt.sourceforge.net/Docs/PyQt5/installation.html) and [PyQt4 documentation](http://pyqt.sourceforge.net/Docs/PyQt4/installation.html)

Source packages for Windows/Linux/MacOS can be found here: [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5) and [PyQt4](https://riverbankcomputing.com/software/pyqt/download).


## Usage
To run the Qtconsole:

    jupyter qtconsole

## Resources
- [Project Jupyter website](https://jupyter.org)
- Documentation for the Qtconsole
  * [latest version](https://qtconsole.readthedocs.io/en/latest/) [[PDF](https://media.readthedocs.org/pdf/qtconsole/latest/qtconsole.pdf)]
  * [stable version](https://qtconsole.readthedocs.io/en/stable/) [[PDF](https://media.readthedocs.org/pdf/qtconsole/stable/qtconsole.pdf)]
- [Documentation for Project Jupyter](https://jupyter.readthedocs.io/en/latest/index.html) [[PDF](https://media.readthedocs.org/pdf/jupyter/latest/jupyter.pdf)]
- [Issues](https://github.com/jupyter/qtconsole/issues)
- [Technical support - Jupyter Google Group](https://groups.google.com/forum/#!forum/jupyter)
