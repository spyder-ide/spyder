# Spyder - The Scientific PYthon Development EnviRonment

Copyright © Spyder Project Contributors.

## Project details
[![license](https://img.shields.io/pypi/l/spyder.svg)](./LICENSE)
[![pypi version](https://img.shields.io/pypi/v/spyder.svg)](https://pypi.python.org/pypi/spyder)
[![Join the chat at https://gitter.im/spyder-ide/public](https://badges.gitter.im/spyder-ide/spyder.svg)](https://gitter.im/spyder-ide/public)
[![OpenCollective Backers](https://opencollective.com/spyder/backers/badge.svg?color=blue)](#backers)
[![OpenCollective Sponsors](https://opencollective.com/spyder/sponsors/badge.svg?color=blue)](#sponsors)

## Build status
[![Travis status](https://travis-ci.org/spyder-ide/spyder.svg?branch=master)](https://travis-ci.org/spyder-ide/spyder)
[![AppVeyor status](https://ci.appveyor.com/api/projects/status/tvjcqa4kf53br8s0/branch/master?svg=true)](https://ci.appveyor.com/project/spyder-ide/spyder/branch/master)
[![CircleCI](https://circleci.com/gh/spyder-ide/spyder.svg?style=svg)](https://circleci.com/gh/spyder-ide/spyder)
[![Coverage Status](https://coveralls.io/repos/github/spyder-ide/spyder/badge.svg?branch=master)](https://coveralls.io/github/spyder-ide/spyder?branch=master)
[![codecov](https://codecov.io/gh/spyder-ide/spyder/branch/master/graph/badge.svg)](https://codecov.io/gh/spyder-ide/spyder)

----

## Important Announcement: Spyder is unfunded!

Since mid November/2017, [Anaconda, Inc](https://www.anaconda.com/) has
stopped funding Spyder development, after doing it for the past 18
months. Because of that, development will focus from now on maintaining
Spyder 3 at a much slower pace than before.

If you want to contribute to maintain Spyder, please consider donating at

https://opencollective.com/spyder

We appreciate all the help you can provide us and can't thank you enough for
supporting the work of Spyder devs and Spyder development.

If you want to know more about this, please read this
[page](https://github.com/spyder-ide/spyder/wiki/Anaconda-stopped-funding-Spyder).

----

## Overview

![screenshot](./img_src/screenshot.png)

Spyder is a Python development environment with a lot of features:

* **Editor**

    Multi-language editor with function/class browser, code analysis
    features (pyflakes and pylint are currently supported), code
    completion, horizontal and vertical splitting, and goto definition.

* **Interactive console**

    Python or IPython consoles with workspace and debugging support to
    instantly evaluate the code written in the Editor. It also comes
    with Matplotlib figures integration. 

* **Documentation viewer**

    Show documentation for any class or function call made either in the
    Editor or a Console.

* **Variable explorer**

    Explore variables created during the execution of a file. Editing
    them is also possible with several GUI based editors, like a
    dictionary and Numpy array ones.

* **Find in files**

    Supporting regular expressions and mercurial repositories

* **File explorer**

* **History log**

Spyder may also be used as a PyQt5/PyQt4 extension library (module
`spyder`). For example, the Python interactive shell widget used in
Spyder may be embedded in your own PyQt5/PyQt4 application.


## Documentation

You can read the Spyder documentation at:

http://pythonhosted.org/spyder/


## Installation

This section explains how to install the latest stable release of
Spyder. If you prefer testing the development version, please use
the `bootstrap` script (see next section).

The easiest way to install Spyder is:

### On Windows:

Using one (and only one) of these scientific Python distributions:

1. [Anaconda](http://continuum.io/downloads)
2. [WinPython](https://winpython.github.io/)
3. [Python(x,y)](http://python-xy.github.io)

### On Mac OSX:

- Using the [Anaconda Distribution](http://continuum.io/downloads).
- Through [MacPorts](http://www.macports.org/).

### On GNU/Linux

- Through your distribution package manager (i.e. `apt-get`, `yum`,
  etc).
- Using the [Anaconda Distribution](http://continuum.io/downloads).
- Installing from source (see below).

### Cross-platform way from source

You can also install Spyder with the `pip` package manager, which comes by
default with most Python installations. For that you need to use the
command:

    pip install spyder

To upgrade Spyder to its latest version, if it was installed before, you need
to run

    pip install --upgrade spyder

For more details on supported platforms, please refer to our
[installation instructions](http://pythonhosted.org/spyder/installation.html).

**Important note**: This does not install the graphical Python libraries (i.e.
PyQt5 or PyQt4) that Spyder depends on. Those have to be installed separately
after installing Python.


## Running from source

The fastest way to run Spyder is to get the source code using git, install
PyQt5 or PyQt4, and run these commands:

1. Install our *runtime dependencies* (see below).
2. `cd /your/spyder/git-clone`
3. `python bootstrap.py`

You may want to do this for fixing bugs in Spyder, adding new
features, learning how Spyder works or just getting a taste of it.


## Dependencies

**Important note**: Most if not all the dependencies listed below come
with *Anaconda*, *WinPython* and *Python(x,y)*, so you don't need to install
them separately when installing one of these Scientific Python
distributions.

### Build dependencies

When installing Spyder from its source package, the only requirement is to have
a Python version greater than 2.7 (Python 3.2 is not supported anymore).

### Runtime dependencies

* **Python** 2.7 or 3.3+
* **PyQt5** 5.2+ or **PyQt4** 4.6+: PyQt5 is recommended.
* **qtconsole** 4.2.0+: Enhanced Python interpreter.
* **Rope** 0.9.4+ and **Jedi** 0.9.0+: Editor code completion, calltips
  and go-to-definition.
* **Pyflakes**: Real-time code analysis.
* **Sphinx**: Rich text mode for the Help pane.
* **Pygments** 2.0+: Syntax highlighting for all file types it supports.
* **Pylint**: Static code analysis.
* **Pycodestyle**: Style analysis.
* **Psutil**: CPU and memory usage on the status bar.
* **Nbconvert**: Manipulation of notebooks in the Editor.
* **Qtawesome** 0.4.1+: To have an icon theme based on FontAwesome.
* **Pickleshare**: Show import completions on the Python consoles.
* **PyZMQ**: Run introspection services asynchronously.
* **QtPy** 1.2.0+: Abstracion layer for Python Qt bindings so that Spyder can run on PyQt4
  and PyQt5.
* **Chardet**: Character encoding auto-detection in Python.
* **Numpydoc**: Used by Jedi to get return types for functions with Numpydoc docstrings.
* **Cloudpickle**: Serialize variables in the IPython kernel to send them to Spyder.

### Optional dependencies

* **Matplotlib**: 2D/3D plotting in the Python and IPython consoles.
* **Pandas**: View and edit DataFrames and Series in the Variable Explorer.
* **Numpy**: View and edit two or three dimensional arrays in the Variable Explorer.
* **SymPy**: Symbolic mathematics in the IPython console.
* **SciPy**: Import Matlab workspace files in the Variable Explorer.
* **Cython**: Run Cython files in the IPython console.


## Contributing

Everyone is welcome to contribute. Please read our
[contributing instructions](https://github.com/spyder-ide/spyder/blob/master/CONTRIBUTING.md),
then get started!


## Backers

Support us with a monthly donation and help us continue our activities.

[![Backers](https://opencollective.com/spyder/backers.svg)](https://opencollective.com/spyder#support)


## Sponsors

Become a sponsor to get your logo on our README on Github.

[![Sponsors](https://opencollective.com/spyder/sponsors.svg)](https://opencollective.com/spyder#support)


## More information

* For code development please go to:

    <https://github.com/spyder-ide/spyder>

* For bug reports and feature requests:

    <https://github.com/spyder-ide/spyder/issues>

* For discussions and troubleshooting:

    <http://groups.google.com/group/spyderlib>
