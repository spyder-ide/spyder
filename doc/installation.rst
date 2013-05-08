Installation
============

Dependencies
------------

Requirements:

* Python 2.5+ 
* PyQt4 4.4+ or PySide 1.1.1+ (PyQt4 is recommended)

Recommended modules:

* pyflakes v0.5.0+ (real-time code analysis)
* rope 0.9.2+ (editor code completion, calltips and go-to-definition)
* sphinx 0.6+ (object inspector's rich text mode)
* numpy (N-dimensional arrays)
* scipy (signal/image processing)
* matplotlib (2D/3D plotting)
* psutil 0.3+ (memory/CPU usage in status bar)

Optional modules:

* IPython 0.13 (enhanced Python interpreter)

  - Version 1.0 is not supported yet
  - On Ubuntu you need to install ipython-qtconsole
  - On Fedora you need to install ipython-gui
  - On Gentoo you need to install ipython with the qt4 USE flag

* pylint (code analysis)
* pep8 (style analysis)

.. note::

    Since v2.0, the `QScintilla` library (source code editor widgets for 
    `PyQt4`) is no longer needed as Spyder is relying on pure Python/Qt
    features (provided by `PyQt4` or `PySide`).


Running from source
-------------------

It is possible to run Spyder directly from unpacked source folder 
using Spyder's bootstrap script:

    ``python bootstrap.py``

This is especially useful for beta-testing, troubleshooting and development 
of Spyder itself.


Installation
------------

This section explains how to install the latest *stable* release of Spyder.
If you prefer testing the development version, please use the bootstrap script
(see previous section).

From the source package (see section 'Building dependencies'), you may 
install Spyder using the integrated setup.py script based on Python 
standard library `distutils` with the following command:

    ``python setup.py install``

Note that `distutils` does *not* uninstall previous versions of Python 
packages: it simply copies files on top of an existing installation. 
When using this command, it is thus highly recommended to uninstall 
manually any previous version of Spyder by removing the associated 
directories ('spyderlib' and 'spyderplugins' in your site-packages 
directory).

From the Python package index, you may simply install Spyder *and* 
upgrade an existing installation using `pip`:
http://pypi.python.org/pypi

But the easiest way to install the last stable release of Spyder is:

* on Windows, using an executable installer (http://spyderlib.googlecode.com) or through Python(x,y) (http://pythonxy.googlecode.com)
* on Mac OSX, using our DMG installer (http://spyderlib.googlecode.com), the Anaconda Python Distribution (https://store.continuum.io/cshop/anaconda/) or through MacPorts
* on GNU/Linux, through your package manager

For more details on supported platforms, please go to http://spyderlib.googlecode.com.

.. note::

    On MacOS X 10.6-10.8, it is known that the MacPorts version of Spyder is
    raising this error: `ValueError: unknown locale: UTF-8`.
    To fix it you will have to set these environment variables in ~/.profile 
    (or ~/.bashrc) manually::
        
        export LANG=en_US.UTF-8
        export LC_ALL=en_US.UTF-8


Help and support
----------------

Spyder websites:

* Downloads, bug reports and feature requests: http://spyderlib.googlecode.com
* Discussions: http://groups.google.com/group/spyderlib
