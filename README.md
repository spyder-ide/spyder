# Spyder - The Scientific PYthon Development EnviRonment

Copyright © 2009-2013 Pierre Raybaut.
Licensed under the terms of the MIT License
(see `spyderlib/__init__.py` for details)


## Overview

Spyder is a Python development environment with tons of features:
    
* Editor
    
    Multi-language editor with function/class browser, code analysis
    features (pyflakes and pylint are currently supported), code
    completion, horizontal and vertical splitting, and goto definition.

* Interactive console

    Python or IPython consoles with workspace and debugging support to
    instantly evaluate the code written in the Editor. It also comes
    with Matplotlib figures integration. 

* Documentation viewer

    Show documentation for any class or function call made either in the
    Editor or a Console.

* Variable explorer

    Explore variables created during the execution of a file. Editing
    them is also possible with several GUI based editors, like a
    dictionary and Numpy array ones.

* Find in files feature

    Supporting regular expressions and mercurial repositories

* File/directories explorer

* History log

Spyder may also be used as a PyQt4/PySide extension library (module 
`spyderlib`). For example, the Python interactive shell widget used in
Spyder may be embedded in your own PyQt4/PySide application.


## Installation
    
This section explains how to install the latest stable release of 
Spyder. If you prefer testing the development version, please use 
the `bootstrap` script (see next section).

The easiest way to install Spyder is:
            
* On Windows:

    - Using one of our executable installers, which can be found
      [here](https://bitbucket.org/spyder-ide/spyderlib/downloads).
    - Or using one of these scientific Python distributions:
        1. [Python(x,y)](http://pythonxy.googlecode.com)
        2. [WinPython](https://winpython.github.io/)
        3. [Anaconda](http://continuum.io/downloads)

* On Mac OSX:

    - Using our DMG installer, which can be found
      [here](https://bitbucket.org/spyder-ide/spyderlib/downloads).
    - Using the [Anaconda Distribution](http://continuum.io/downloads).
    - Through [MacPorts](http://www.macports.org/).
            
* On GNU/Linux

    - Through your distribution package manager (i.e. `apt-get`, `yum`,
    etc).
    - Using the [Anaconda Distribution](http://continuum.io/downloads).
    - Installing from source (see below).

### Installing from source

You can also install Spyder from its zip source package. For that you need to
download and uncompress the file called `spyder-x.y.z.zip`, which can be
found [here](https://bitbucket.org/spyder-ide/spyderlib/downloads). Then you need to
use the integrated `setup.py` script that comes with it and which is based
on the Python standard library `distutils` module, with the following command:

    python setup.py install

Note that `distutils` does *not* uninstall previous versions of Python 
packages: it simply copies files on top of an existing installation. 
When using this command, it is thus highly recommended to uninstall 
manually any previous version of Spyder by removing the associated 
directories ('spyderlib' and 'spyderplugins') from your site-packages 
directory).

From the [Python package index](http://pypi.python.org/pypi), you also
may install Spyder *and* upgrade an existing installation using `pip`
with this command

    pip install --upgrade spyder

For more details on supported platforms, please go to
<http://pythonhosted.org/spyder/installation.html>.


## Dependencies

*Imnportant note*: Most if not all the dependencies listed below come
with Python(x,y), WinPython and Anaconda, so you don't need to install
them separately when installing one of these scientific Python
distributions.

### Build dependencies

When installing Spyder from its source package (using the command
`python setup.py install`), the only requirements is to have a Python version
greater than 2.6.

### Runtime dependencies

* Python 2.6+

* PyQt4 4.6+ or PySide 1.2.0+ (PyQt4 is recommended)
            
### Recommended modules

* Rope v0.9.2+ (editor code completion, calltips and go-to-definition)

* Pyflakes v0.5.0+ (real-time code analysis)

* Sphinx v0.6+ (object inspector's rich text mode)

* Numpy (N-dimensional arrays)

* Scipy (signal/image processing)

* Matplotlib (2D/3D plotting)

* IPython 0.13 (enhanced Python interpreter)

    In Ubuntu you need to install `ipython-qtconsole`, on Fedora
    `ipython-gui` and on Gentoo `ipython` with the `qt4` USE flag.

### Optional modules

* Pygments (syntax highlighting for several file types).

* Pylint (static code analysis).

* Pep8 (style analysis).


## Running from source

It is possible to run Spyder directly (i.e. without installation)
from the unpacked zip folder (see *Installing from source*) using
Spyder's bootstrap script like this:

    python bootstrap.py

This is especially useful for beta-testing, troubleshooting 
and development of Spyder itself.


## Build Windows installers

From the source package, you may build Windows installers to distribute
Spyder on all supported platforms and versions of Python.

Spyder has a single code base supporting both Python 2 and Python 3 but
the Windows installer will target a specific version of Python because
of the two external libraries included in the Windows installers
('pyflakes' and 'rope') which have specific versions for Python 2 and 3.
 
Moreover, despite the fact that Spyder code base supports all Python
architectures (32 and 64bit), the Windows installers will also target
specific architectures because of a limitation of the way `distutils`
works (see <http://bugs.python.org/issue6792>).

Example of Spyder binary installers for Windows:

* Python 2.7 and 32bit: spyder-2.3.0-win32-py2.7.exe
* Python 2.7 and 64bit: spyder-2.3.0-win-amd64-py2.7.exe
* Python 3.3 and 32bit: spyder-2.3.0-win32-py3.3.exe
* Python 3.3 and 64bit: spyder-2.3.0-win-amd64-py3.3.exe


## More information

* For code development please go to

    <https://bitbucket.org/spyder-ide/spyderlib/>
    
* For bug reports and feature requests
           
    <http://code.google.com/p/spyderlib/issues>

* For discussions and troubleshooting:

    <http://groups.google.com/group/spyderlib>
