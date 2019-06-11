![Spyder — The Scientific Python Development Environment](https://raw.githubusercontent.com/spyder-ide/spyder/master/img_src/spyder_readme_banner.png)

*Copyright © 2009–2019 [Spyder Project Contributors](
https://github.com/spyder-ide/spyder/graphs/contributors)*

*Some source files and icons may be under other authorship/licenses; see
[NOTICE.txt](https://github.com/spyder-ide/spyder/blob/master/NOTICE.txt).*


[![license](https://img.shields.io/pypi/l/spyder.svg)](./LICENSE.txt)
[![pypi version](https://img.shields.io/pypi/v/spyder.svg)](https://pypi.org/project/spyder/)
[![conda version](https://img.shields.io/conda/vn/conda-forge/spyder.svg)](https://www.anaconda.com/download/)
[![download count](https://img.shields.io/conda/dn/conda-forge/spyder.svg)](https://www.anaconda.com/download/)
[![OpenCollective Backers](https://opencollective.com/spyder/backers/badge.svg?color=blue)](#backers)
[![OpenCollective Sponsors](https://opencollective.com/spyder/sponsors/badge.svg?color=blue)](#sponsors)
[![Join the chat at https://gitter.im/spyder-ide/public](https://badges.gitter.im/spyder-ide/spyder.svg)](https://gitter.im/spyder-ide/public)<br>
[![PyPI status](https://img.shields.io/pypi/status/spyder.svg)](https://github.com/spyder-ide/spyder)
[![Travis status](https://travis-ci.org/spyder-ide/spyder.svg?branch=master)](https://travis-ci.org/spyder-ide/spyder)
[![CircleCI](https://circleci.com/gh/spyder-ide/spyder.svg?style=shield)](https://circleci.com/gh/spyder-ide/spyder)
[![Azure](https://dev.azure.com/spyder-ide/spyder/_apis/build/status/spyder-ide.spyder?branchName=master)](https://dev.azure.com/spyder-ide/spyder/_build/latest?definitionId=1?branchName=master)
[![Coverage Status](https://coveralls.io/repos/github/spyder-ide/spyder/badge.svg?branch=master)](https://coveralls.io/github/spyder-ide/spyder?branch=master)
[![codecov](https://codecov.io/gh/spyder-ide/spyder/branch/master/graph/badge.svg)](https://codecov.io/gh/spyder-ide/spyder)

![Screenshot of Spyder's main window](https://raw.githubusercontent.com/spyder-ide/spyder/master/img_src/screenshot.png)

----

## Help support Spyder, the community-developed scientific IDE!

Thanks to your continuing support, we are on track for a
Spyder 4 release in early 2019 with all of your most-requested features
(a new debugger and completion architecture, better Projects, new Editor
functionality, full Variable Explorer object support, a built-in dark theme
and [much more](https://github.com/spyder-ide/spyder/wiki/Roadmap))!

Spyder development is made possible by contributions from our global user
community, along with organizations like [NumFOCUS](https://www.numfocus.org)
and [Quansight](https://www.quansight.com).
There are numerous [ways you can help](
https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder), many of
which don't require any programming. If you'd like to make a [donation](
https://opencollective.com/spyder/donate) to help fund further improvements,
we're on [OpenCollective](https://opencollective.com/spyder).

Thanks for all you do to make the Spyder project thrive! [More details](
https://github.com/spyder-ide/spyder/wiki/Current-Funding-and-Development-Status)

----

## Overview

Spyder is a powerful scientific environment written in Python, for Python,
and designed by and for scientists, engineers and data analysts. It offers a
unique combination of the advanced editing, analysis, debugging, and profiling
functionality of a comprehensive development tool with the data exploration,
interactive execution, deep inspection, and beautiful visualization
capabilities of a scientific package.

Beyond its many built-in features, its abilities can be extended even further
via its plugin system and API. Furthermore, Spyder can also be used as a PyQt5
extension library, allowing you to build upon its functionality and embed
its components, such as the interactive console, in your own software.

For more general information about Spyder and to stay up to date on the
latest Spyder news and information, please check out [our new website](
https://www.spyder-ide.org/).


## Core components

* **Editor**

    Work efficiently in a multi-language editor with a function/class browser,
    real-time code analysis tools (`pyflakes`, `pylint`, and `pycodestyle`),
    automatic code completion (`jedi` and `rope`),
    horizontal/vertical splitting, and go-to-definition.

* **Interactive console**

    Harness the power of as many IPython consoles as you like with full
    workspace and debugging support, all within the flexibility of a full
    GUI interface. Instantly run your code by line, cell, or file,
    and render plots right inline with the output or in interactive windows.

* **Documentation viewer**

    Render documentation in real-time with Sphinx for any class or function,
    whether external or user-created, from either the Editor or a Console.

* **Variable explorer**

    Inspect any variables, functions or objects created during your session.
    Editing and interaction is supported with many common types, including
    numeric/strings/bools, Python lists/tuples/dictionaries, dates/timedeltas,
    Numpy arrays, Pandas index/series/dataframes, PIL/Pillow images, and more.

* **Development tools**

    Examine your code with the static analyzer, trace its execution with the
    interactive debugger, and unleash its performance with the profiler.
    Keep things organized with project support and a builtin file explorer, and
    use find in files to search across entire projects with full regex support.


## Documentation

You can read the Spyder documentation online on [the Spyder Docs website](
https://docs.spyder-ide.org/).


## Installation

For a detailed guide to installing Spyder, please refer to our
[installation instructions](https://docs.spyder-ide.org/installation.html).

The easiest way to install Spyder on any of our supported platforms
is to download it as part of the [Anaconda](https://www.anaconda.com/download/)
distribution, and use the `conda` package and environment manager to keep it
and your other packages installed and up to date.

If in doubt, you should always install Spyder via this method to avoid
unexpected issues we are unable to help you with; it generally has the
least likelihood of potential pitfalls for non-experts, and we may be
able to provide limited assistance if you do run into trouble.

Other install options exist, including:

* The [WinPython](https://winpython.github.io/) distribution for Windows
* The [MacPorts](https://www.macports.org/) project for macOS
* Your distribution's package manager (i.e. `apt-get`, `yum`, etc) on Linux
* The `pip` package manager, included with most Python installations

**However**, we lack the resources to provide individual support for users who
install via these methods, and they may be out of date or contain bugs outside
our control, so we recommend the Anaconda version instead if you run into issues.


## Troubleshooting

Before posting a report, *please* carefully read our **[Troubleshooting Guide](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)**
and search the [issue tracker](https://github.com/spyder-ide/spyder/issues)
for your error message and problem description, as the great majority of bugs
are either duplicates, or can be fixed on the user side with a few easy steps.
Thanks!


## Contributing and Credits

Spyder was originally created by [Pierre Raybaut](
https://github.com/PierreRaybaut), and is currently maintained by
[Carlos Córdoba](https://github.com/ccordoba12) and an international
community of volunteers.

You can join us—everyone is welcome to help with Spyder!
Please read our [contributing instructions](
https://github.com/spyder-ide/spyder/blob/master/CONTRIBUTING.md)
to get started!

Certain source files are distributed under other compatible permissive licenses
and/or originally by other authors.
The icons for the Spyder 3 theme are derived from [Font Awesome](
https://fontawesome.com/) 4.7 (© 2016 David Gandy; SIL OFL 1.1).
Most Spyder 2 theme icons are sourced from the [Crystal Project icon set](
https://www.everaldo.com) (© 2006-2007 Everaldo Coelho; LGPL 2.1+).
Other Spyder 2 icons are from [Yusuke Kamiyamane](
http://p.yusukekamiyamane.com/) (© 2013 Yusuke Kamiyamane; CC-BY 3.0),
the [FamFamFam Silk icon set](http://www.famfamfam.com/lab/icons/silk/)
(© 2006 Mark James; CC-BY 2.5), and the [KDE Oxygen icons](
https://www.kde.org/) (© 2007 KDE Artists; LGPL 3.0+).

See [NOTICE.txt](https://github.com/spyder-ide/spyder/blob/master/NOTICE.txt)
for full legal information.


## Running from a Github clone

Spyder can be run directly from the source code, hosted on the
[Spyder github repo](https://github.com/spyder-ide/spyder).
You may want to do this for fixing bugs in Spyder, adding new
features, learning how Spyder works or to try out development versions before
they are officially released.

If using `conda` (strongly recommended), this can be done by running the
following from the command line (the Anaconda Prompt, if on Windows):

```bash
conda install spyder
conda remove spyder
git clone https://github.com/spyder-ide/spyder.git
cd spyder
python bootstrap.py
```

You also need to make sure the correct `spyder-kernels` version is installed
for the version of Spyder you are testing. The above procedure will give you
`spyder-kernels` 0.x for the `3.x` branch (Spyder 3),
so to run the `master` branch (Spyder 4) you need to additionally execute:

```bash
conda install -c spyder-ide spyder-kernels=1.*
```

Alternatively, you can use `pip` to install PyQt5 and the other
*runtime dependencies* listed below. However, beware:
this method is recommended for experts only, and you'll need to solve any
problems on your own.

See the [installation instructions](
https://docs.spyder-ide.org/installation.html) for more details on all of this.


## Dependencies

**Important Note**: Most or all of the dependencies listed below come
with *Anaconda* and other scientific Python distributions, so you don't need
to install them separately in those cases.

### Build dependencies

When installing Spyder from its source package, the only requirement is to have
a Python version greater than 2.7 or 3.4 (Python <=3.3 is no longer supported).

### Runtime dependencies

* **Python** 2.7 or 3.4+: The core language Spyder is written in and for.
* **PyQt5** 5.6+: Python bindings for Qt, used for Spyder's GUI.
* **qtconsole** 4.5.0+: Enhanced Python interpreter.
* **Python-language-server**: Editor code completion, calltips
  go-to-definition and real-time code analysis
* **Sphinx**: Rich text mode for the Help pane.
* **Pygments** 2.0+: Syntax highlighting for all file types it supports.
* **Pylint**: Static code analysis.
* **Psutil**: CPU and memory usage on the status bar.
* **Nbconvert**: Manipulation of notebooks in the Editor.
* **Qtawesome** 0.5.7+: To have an icon theme based on FontAwesome.
* **Pickleshare**: Show import completions on the Python consoles.
* **PyZMQ**: Client for the language server protocol (LSP).
* **QtPy** 1.5.0+: Abstraction layer for Python Qt bindings so that Spyder
  can run on multiple Qt bindings and versions.
* **Chardet**: Character encoding auto-detection in Python.
* **Numpydoc**: Used by Jedi to get function return types from Numpydocstrings.
* **Cloudpickle**: Serialize variables in the IPython kernel to send to Spyder.
* **spyder-kernels** 1.2.0+: Jupyter kernels for the Spyder console.
* **keyring**: Save Github credentials to report errors securely.
* **QDarkStyle** 2.6.4+: A dark stylesheet for Qt applications, used for Spyder's dark theme.
* **atomicwrites**: Atomic file writes.
* **pexpect**/**paramiko**: Connect to remote kernels through SSH.
* **diff-match-patch**: Compute text file diff changes during edition.
* **watchdog**: Watch file changes on project directories.

### Optional dependencies

* **Matplotlib**: 2D/3D plotting in the IPython console.
* **Pandas**: View and edit DataFrames and Series in the Variable Explorer.
* **Numpy**: View and edit 2- or 3-dimensional arrays in the Variable Explorer.
* **SymPy**: Symbolic mathematics in the IPython console.
* **SciPy**: Import Matlab workspace files in the Variable Explorer.
* **Cython**: Run Cython files in the IPython console.


## Sponsors

Spyder is funded thanks to the generous support of


[![Quansight](https://static.wixstatic.com/media/095d2c_2508c560e87d436ea00357abc404cf1d~mv2.png/v1/crop/x_0,y_9,w_915,h_329/fill/w_380,h_128,al_c,usm_0.66_1.00_0.01/095d2c_2508c560e87d436ea00357abc404cf1d~mv2.png)](https://www.quansight.com/)[![Numfocus](https://i2.wp.com/numfocus.org/wp-content/uploads/2017/07/NumFocus_LRG.png?fit=320%2C148&ssl=1)](https://numfocus.org/)


and the donations we have received from our users around the world through [Open Collective](https://opencollective.com/spyder/):

[![Sponsors](https://opencollective.com/spyder/sponsors.svg)](https://opencollective.com/spyder#support)


## More information

[Main Website](https://www.spyder-ide.org/)

[Download Spyder (with Anaconda)](https://www.anaconda.com/download/)

[Online Documentation](https://docs.spyder-ide.org/)

[Spyder Github](https://github.com/spyder-ide/spyder)

[Troubleshooting Guide and FAQ](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)

[Development Wiki](https://github.com/spyder-ide/spyder/wiki/Dev:-Index)

[Gitter Chatroom](https://gitter.im/spyder-ide/public)

[Google Group](https://groups.google.com/group/spyderlib)

[@Spyder_IDE on Twitter](https://twitter.com/spyder_ide)

[@SpyderIDE on Facebook](https://www.facebook.com/SpyderIDE/)

[Support Spyder on OpenCollective](https://opencollective.com/spyder/)
