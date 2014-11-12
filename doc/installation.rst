Installation
============

Spyder is quite easy to install on Windows, Linux and MacOS X. Just the read the
following instructions with care.


Installing on MacOS X
----------------------

The easy way
~~~~~~~~~~~~

Thanks to the Spyder team and `Continuum <http://www.continuum.io/>`_, you have
two alternatives:

#. Use the Anaconda Python distribution, which can be downloaded on this
   `site <http://continuum.io/downloads.html>`_.

#. Use our dmg installer, which can be found
   `here <https://code.google.com/p/spyderlib/downloads/list>`_.

  .. warning::
   
     *This is not necessary anymore since version 2.2.5.*
     
     * To be able to use the app that comes with this dmg on *Mountain Lion* (10.8)
       you need to install `XQuartz <http://xquartz.macosforge.org/>`_ first.
     * To generate plots in *Snow Leopard* (10.6) you need to install first
       `this <http://ethan.tira-thompson.com/Mac_OS_X_Ports_files/libpng%20%28universal%29.dmg>`_
       (more recent) version of ``libpng``.


The hard way
~~~~~~~~~~~~

Thanks to the *MacPorts* project, Spyder can be installed using its ``port`` package manager.
There are `several versions`__ available from which you can choose from.

__ http://www.macports.org/ports.php?by=name&substr=spyder MacPorts

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

Please refer to the `Recommended modules`_ section to see what other packages you
might need.

#. **Ubuntu**:
  
   * Using the official package manager: ``sudo apt-get install spyder``.
  
     .. note::
     
        This package could be slightly outdated. If you find that is the case,
        please use the Debian package mentioned below.
  
   * Using the `pip <https://pypi.python.org/pypi/pip/>`_ package manager:
  
     * Requirements: ``sudo apt-get install python-qt4 python-sphinx``
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

Installing on Windows XP/Vista/7/8
----------------------------------

The easy way
~~~~~~~~~~~~

Spyder is already included in these *Python Scientific Distributions*:

#. `Python(x,y) <https://code.google.com/p/pythonxy>`_
#. `WinPython <https://winpython.github.io/>`_
#. `Anaconda <http://continuum.io/downloads.html>`_

You can start using it immediately after installing one of them (you only need
to install one!).


The hard way
~~~~~~~~~~~~

If you want to install Spyder directly, you need to follow these steps:

#. Install the essential requirements:

   * `The Python language <http://www.python.org/>`_
   * `PyQt4 <http://www.riverbankcomputing.co.uk/software/pyqt/download>`_

#. Install optional modules:

   These are the most important modules to do scientific programming with Python

   * `numpy <http://numpy.scipy.org/>`_
   * `scipy <http://www.scipy.org/>`_
   * `matplotlib <http://matplotlib.sourceforge.net/>`_
   * `IPython <http://ipython.org/install.html#downloads>`_
   * `Python Imaging Library <https://pypi.python.org/pypi/Pillow>`_
  
#. Installing Spyder itself:

   You need to download and install the .exe file that corresponds to your Python
   version and architecture from
   `this page <http://code.google.com/p/spyderlib/downloads/list>`_.


Updating Spyder
~~~~~~~~~~~~~~~

You can update Spyder by:

* Updating Python(x,y), WinPython or Anaconda.

* Installing a new .exe file from the page mentioned above (this will automatically
  uninstall any previous version *only if* this version was installed with the same
  kind of installer - i.e. not with an .msi installer).

|

Installing or running directly from source
------------------------------------------

Requirements
~~~~~~~~~~~~

The minimal requirements to run Spyder are

* `Python <http://www.python.org/>`_ 2.6+
  
* `PyQt4 <http://www.riverbankcomputing.co.uk/software/pyqt/download>`_ >= v4.6 or
  `PySide <http://pyside.org/>`_ >=1.2.0 (PyQt4 is recommended).


Recommended modules
~~~~~~~~~~~~~~~~~~~

We recommend you to install these modules to get the most out of Spyder:

* `IPython <http://ipython.org/install.html#downloads>`_ -- for an enhanced Python
  interpreter.
  
 .. note::
  
    - On *Ubuntu* you need to install ``ipython-qtconsole``.
    - On *Fedora*, ``ipython-gui``
    - And on *Gentoo* ``ipython`` with the ``qt4`` USE flag
  
* `sphinx <http://sphinx.pocoo.org>`_ >= v0.6  -- for the Object Inspector's rich
  text mode and to get our documentation.

* `rope <http://rope.sourceforge.net/>`_ 0.9.x (x>=0) -- for code completion,
  go-to-definition and calltips on the Editor.

* `pyflakes <http://pypi.python.org/pypi/pyflakes>`_  0.x (x>=5) -- for real-time
  code analysis.

* `pylint <http://www.logilab.org/project/pylint>`_  -- for static code analysis.

* `pep8 <https://pypi.python.org/pypi/pep8>`_ -- for style analysis.

* `numpy <http://numpy.scipy.org/>`_ -- for N-dimensional arrays.

* `scipy <http://www.scipy.org/>`_ -- for signal and image processing.

* `matplotlib <http://matplotlib.sourceforge.net/>`_ -- for 2D and 3D plotting.

* `psutil <http://code.google.com/p/psutil/>`_  -- for memory/CPU usage in the status
  bar.


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

#. Install `Mercurial <http://mercurial.selenic.com/>`_, a simple and powerful
   source control management tool.

#. Clone the Spyder source code repository with the command:

   ``hg clone https://bitbucket.org/spyder-ide/spyderlib``

#. To keep your repository up-to-date, run

   ``hg pull -u``
   
   inside the cloned directory.

#. (*Optional*) If you want to read the documentation, you must build it first with
   the command
  
   ``python setup.py build_doc``

|

Help and support
----------------

Spyder websites:

* For bug reports and feature requests you can go to our
  `website <http://spyderlib.googlecode.com>`_.
* For discussions and help requests, you can suscribe to our
  `Google Group <http://groups.google.com/group/spyderlib>`_.
