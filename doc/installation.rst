Installation
============

Spyder is quite easy to install on Windows, Linux and MacOS X. Just the read the
following instructions with care.

Installing on Windows Vista/7/8/10
----------------------------------

The easy way
~~~~~~~~~~~~

Spyder is already included in these *Python Scientific Distributions*:

#. `Anaconda <http://continuum.io/downloads.html>`_
#. `WinPython <https://winpython.github.io/>`_
#. `Python(x,y) <https://code.google.com/p/pythonxy>`_

You can start using it immediately after installing one of them (you only need
to install one!).


The hard way
~~~~~~~~~~~~

If you want to install Spyder directly, you need to follow these steps:

#. Install the necessary `requirements`_

#. Install the `optional modules`_

#. Installing Spyder itself:

   You need to download and install the .exe file that corresponds to your Python
   version and architecture from
   `this page <https://github.com/spyder-ide/spyder/releases>`_.


Updating Spyder
~~~~~~~~~~~~~~~

You can update Spyder by:

* Updating Anaconda, WinPython, Python(x,y).

* Installing a new .exe file from the page mentioned above (this will automatically
  uninstall any previous version *only if* this version was installed with the same
  kind of installer - i.e. not with an .msi installer).

|

Installing on MacOS X
----------------------

The easy way
~~~~~~~~~~~~

Thanks to the Spyder team and `Continuum <http://www.continuum.io/>`_, you have
two alternatives:

#. Use the `Anaconda <http://continuum.io/downloads.html>`_ Python distribution.

#. Use our DMG installers, which can be found
   `here <https://github.com/spyder-ide/spyder/releases>`_.

  .. note::
     
     The minimal version to run our DMG's is Mavericks (10.9) since
     Spyder 2.3.5. Previous versions work on Lion (10.7) or higher.


The hard way
~~~~~~~~~~~~

Thanks to the *MacPorts* project, Spyder can be installed using its ``port`` package manager.
There are `several versions`__ available from which you can choose from.

__ http://www.macports.org/ports.php?by=name&substr=spyder

  .. warning::

     It is known that the MacPorts version of Spyder is raising this error:
     ``ValueError: unknown locale: UTF-8``, which doesn't let it start correctly.
   
     To fix it you will have to set these environment variables in your
     ``~/.profile`` (or ``~/.bashrc``) manually::
        
        export LANG=en_US.UTF-8
        export LC_ALL=en_US.UTF-8

|

Installing on Linux
-------------------

Please refer to the `Requirements`_ section to see what other packages you
might need.

#. **Ubuntu**:

   * Using the official package manager: ``sudo apt-get install spyder``.

     .. note::

        This package could be slightly outdated. If you find that is the case,
        please use the Debian package mentioned below.

   * Using the `pip <https://pypi.python.org/pypi/pip/>`_ package manager:

     * Installing: ``sudo pip install spyder``
     * Updating: ``sudo pip install -U spyder``

#. **Debian Unstable**:
  
   Using the package manager: ``sudo apt-get install spyder``

   The Spyder's official Debian package is available `here`__ 
  
   __ http://packages.debian.org/fr/sid/spyder.


#. **Other Distributions**

   Spyder is also available in other GNU/Linux distributions, like

   * `Archlinux <https://aur.archlinux.org/packages/?K=spyder>`_

   * `Fedora <https://admin.fedoraproject.org/pkgdb/acls/name/spyder?_csrf_token=ab2ac812ed6df3abdf42981038a56d3d87b34128>`_

   * `Gentoo <http://packages.gentoo.org/package/dev-python/spyder>`_

   * `openSUSE <https://build.opensuse.org/package/show?package=python-spyder&project=home%3Aocefpaf>`_

   * `Mageia <http://mageia.madb.org/package/show/name/spyder>`_

   Please refer to your distribution's documentation to learn how to install it
   there.

|

Installing or running directly from source
------------------------------------------

Requirements
~~~~~~~~~~~~

The requirements to run Spyder are:

* `Python <http://www.python.org/>`_ 2.7 or >=3.3

* `PyQt5 <https://www.riverbankcomputing.com/software/pyqt/download5>`_ >=5.2 or
  `PyQt4 <https://www.riverbankcomputing.com/software/pyqt/download>`_ >=4.6.0
  (PyQt5 is recommended).

* `Qtconsole <http://jupyter.org/qtconsole/stable/>`_ >=4.0 -- for an
  enhanced Python interpreter.

* `Rope <http://rope.sourceforge.net/>`_ >=0.9.4 or
  `Jedi <http://jedi.jedidjah.ch/en/latest/>` 0.8.1 -- for code completion,
  go-to-definition and calltips on the Editor.

* `Pyflakes <http://pypi.python.org/pypi/pyflakes>`_  -- for real-time
  code analysis.

* `Sphinx <http://sphinx.pocoo.org>`_ -- for the Help pane rich text mode
  and to get our documentation.

* `Pygments <http://pygments.org/>`_ -- for syntax highlighting in the Editor of
  all file types it supports.

* `Pylint <http://www.logilab.org/project/pylint>`_  -- for static code analysis.

* `Pep8 <https://pypi.python.org/pypi/pep8>`_ -- for style analysis.

* `Psutil <http://code.google.com/p/psutil/>`_  -- for memory/CPU usage in the status
  bar.

* `Nbconvert <http://nbconvert.readthedocs.org/>`_ -- to manipulate Jupyter notebooks
  on the Editor

* Path.py and pickleshare -- To show import completions on the Editor and the
  consoles.


Optional modules
~~~~~~~~~~~~~~~~

* `Matplotlib <http://matplotlib.sourceforge.net/>`_ -- for 2D and 3D plotting in
  the consoles.

* `Pandas <http://pandas.pydata.org/>`_ -- for view and editing DataFrames and
  Series in the Variable Explorer.

* `Numpy <http://numpy.scipy.org/>`_ -- for view and editing two or three
  dimensional arrays in the Variable Explorer.

* `Sympy <http://www.sympy.org/es/>`_ -- for working with symbolic mathematics
  in the IPython console.

* `Scipy <http://www.scipy.org/>`_ -- for importing Matlab workspace files in
  the Variable Explorer.


Installation procedure
~~~~~~~~~~~~~~~~~~~~~~

#. Download and unzip the source package (spyder-*version*.zip):
#. Change your current directory to the unzipped directory
#. Run:

   * ``sudo python setup.py install``, on Linux or MacOS X, or
   * ``python setup.py install``, on Windows.

  .. warning::

     This procedure does *not* uninstall previous versions of Spyder, it simply 
     copies files on top of an existing installation. When using this command,
     it is thus highly recommended to uninstall manually any previous version of
     Spyder by removing the associated directories (``spyderlib`` and
     ``spyderplugins`` in your site-packages directory).


Run without installing
~~~~~~~~~~~~~~~~~~~~~~

You can execute Spyder without installing it first by following these steps:

#. Unzip the source package
#. Change current directory to the unzipped directory
#. Run Spyder with the command ``python bootstrap.py``
#. (*Optional*) Build the documentation with ``python setup.py build_doc``.

This is especially useful for beta-testing, troubleshooting and development 
of Spyder itself.

|

Installing the development version
----------------------------------

If you want to try the next Spyder version, you have to:

#. Install `Git <http://git-scm.com/downloads>`_, a powerful
   source control management tool.

#. Clone the Spyder source code repository with the command:

   ``git clone https://github.com/spyder-ide/spyder.git``

#. To keep your repository up-to-date, run

   ``git pull``
   
   inside the cloned directory.

#. (*Optional*) If you want to read the documentation, you must build it first with
   the command
  
   ``python setup.py build_doc``

|

Help and support
----------------

Spyder websites:

* For bug reports and feature requests you can go to our
  `website <https://github.com/spyder-ide/spyder/issues>`_.
* For discussions and help requests, you can suscribe to our
  `Google Group <http://groups.google.com/group/spyderlib>`_.
