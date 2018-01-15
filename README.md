# Spyder - The Scientific PYthon Development EnviRonment

Copyright © Spyder Project Contributors.


## Project details
[![license](https://img.shields.io/pypi/l/spyder.svg)](./LICENSE)
[![pypi version](https://img.shields.io/pypi/v/spyder.svg)](https://pypi.python.org/pypi/spyder)
[![Join the chat at https://gitter.im/spyder-ide/public](https://badges.gitter.im/spyder-ide/spyder.svg)](https://gitter.im/spyder-ide/public)


## Build status
[![Travis status](https://travis-ci.org/spyder-ide/spyder.svg?branch=master)](https://travis-ci.org/spyder-ide/spyder)
[![AppVeyor status](https://ci.appveyor.com/api/projects/status/tvjcqa4kf53br8s0/branch/master?svg=true)](https://ci.appveyor.com/project/spyder-ide/spyder/branch/master)
[![CircleCI](https://circleci.com/gh/spyder-ide/spyder.svg?style=svg)](https://circleci.com/gh/spyder-ide/spyder)
[![Coverage Status](https://coveralls.io/repos/github/spyder-ide/spyder/badge.svg?branch=master)](https://coveralls.io/github/spyder-ide/spyder?branch=master)
[![codecov](https://codecov.io/gh/spyder-ide/spyder/branch/master/graph/badge.svg)](https://codecov.io/gh/spyder-ide/spyder)


## Overview

![screenshot](./img_src/screenshot.png)

Spyder is a Python development environment with many features for research,
data analysis, and scientific package creation:

* **Editor**

    Multi-language editor with function/class browser, code analysis
    features (pyflakes and pylint are currently supported), code
    completion, horizontal and vertical splitting, and goto definition.

* **Interactive console**

    IPython consoles with workspace and debugging support to
    instantly evaluate the code written in the Editor.
    Spyder consoles also come with Matplotlib figures integration.

* **Documentation viewer**

    Show documentation for any class or function call made either in the
    Editor or a Console.

* **Variable explorer**

    Explore variables created during the execution of a file. Editing
    them is also possible with several GUI based editors, like a
    dictionary and Numpy array ones.

* **Find in files**

    Search for queries across multiple files in your project,
    with full support for regular expressions.

* **File explorer**

    Interact with your filesystem from within the IDE.

* **History log**

    Browse an automatically de-duplicated listing of every command you run
    on any Spyder console.

Spyder may also be used as a PyQt5/PyQt4 extension library (module `spyder`).
For example, the Python interactive shell widget used in
Spyder may be embedded in your own PyQt5/PyQt4 application.


## Documentation

You can read the Spyder documentation online on
[PythonHosted](http://pythonhosted.org/spyder/).


## Installation

This section explains how to install the latest stable release of
Spyder. If you prefer testing the development version, please use
the `bootstrap` script (see the [appropriate section](#running-from-source) ).

For a more detail guide to installing Spyder, please refer to our
[installation instructions](http://pythonhosted.org/spyder/installation.html).

### The Easy/Recommended Way: Anaconda

The easiest way to install Spyder on any of our supported platforms
is to download it as part of the [Anaconda](https://www.anaconda.com/download/)
distribution, and use the `conda` package and environment manager to keep it
and your other packages installed and up to date.

If in doubt, you should always install Spyder via this method to avoid
unexpected issues we are unable to help you with; it generally has the
least likelihood of potential pitfalls for non-experts, and we may be
able to provide limited assistance if you do run into trouble.

### The Harder Way: Alternative distributions

**Important Note:** While we offer alternative Spyder installation options
for users who desire them, we currently lack the resources to offer individual
assistance for problems specific to installing via these alternative distributions.
Therefore, we recommend you switch to Anaconda if you encounter installation
issues you are unable to solve on your own.

**Windows**

Spyder is also included in the [WinPython](https://winpython.github.io/)
scientific Python distribution, although some users have reported bugs
specific to it.

**macOS**

Spyder can also be obtained through through [MacPorts](http://www.macports.org/),
though like its WinPython counterpart, the included version may be out of date
or have other MacPorts specific issues outside of Spyder's control.

**GNU/Linux**

You can often install Spyder through your distribution's package
manager (i.e. `apt-get`, `yum`, etc).

### The Expert Way: Installing with pip

**Warning:** While this installation method is a viable option for
experienced users, installing Spyder (and other SciPy stack packages)
with `pip` can lead to a number of tricky issues. While you are welcome
to try this on your own, we unfortunately do not have the resources to help you
if you do run into problems, except to recommend using Anaconda instead.

You can install Spyder with the `pip` package manager, which comes by
default with most Python installations, with the command:

`pip install spyder`

Once installed, you can upgrade Spyder to its latest version, by running:

`pip install --upgrade spyder`

Also, you may need to install a Qt binding with `pip` if running Python 2;
PyQt5 is strongly recommended though the legacy PyQt4 is also still supported.


## Running from a Github clone

Spyder can be run directly from the source code, hosted on the
[Spyder github repo](https://github.com/spyder-ide/spyder).
You may want to do this for fixing bugs in Spyder, adding new
features, learning how Spyder works or to try out development versions before
they are officially released.

If using `conda` (strongly recommended), this can be done by running the
following from the command line (the Anaconda Prompt, if on Windows):

```
conda install spyder
conda remove spyder
git clone https://github.com/spyder-ide/spyder.git
cd spyder
python bootstrap.py
```

Alternatively, you can use `pip` to install PyQt5 (or PyQt4) separately and
the other *runtime dependencies* listed below. However, beware:
this method is recommended for experts only, and you'll need to solve any
problems on your own. See the
[installation instructions](http://pythonhosted.org/spyder/installation.html)
for more details.


## Dependencies

**Important note**: Most if not all the dependencies listed below come
with *Anaconda* or other scien, so you don't need to install
them separately when installing one of these Scientific Python
distributions.

### Build dependencies

When installing Spyder from its source package, the only requirement is to have
a Python version greater than 2.7 or 3.3 (Python <=3.2 is not supported anymore).

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

Everyone is welcome to help with Spyder. Please read our
[contributing instructions](https://github.com/spyder-ide/spyder/blob/master/CONTRIBUTING.md)
to get started!


## Troubleshooting

Before posting a report, *please* carefully read our **[Troubleshooting Guide](https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)**
and search the [issue tracker](https://github.com/spyder-ide/spyder/issues)
for your error message and problem description, as the great majority of bugs
are either duplicates, or can be fixed on the user side with a few easy steps.
Thanks!


## More information

* For Spyder development details:

    <https://github.com/spyder-ide/spyder>

* For bug reports and feature requests:

    <https://github.com/spyder-ide/spyder/issues>

* For discussions and troubleshooting:

    <http://groups.google.com/group/spyderlib>
