Installation
============

Spyder is quite easy to install on Windows, Linux and macOS; just read the
following instructions with care.

This section explains how to install the latest stable release of Spyder.
If you prefer testing the development version, please use the
``bootstrap`` script (see next section).

If you run into problems, before posting a report,
*please* consult our comprehensive
`Troubleshooting Guide <https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ>`_
and search the `issue tracker <https://github.com/spyder-ide/spyder/issues>`_
for your error message and problem description, as these methods are known to
fix or at least isolate the vast majority of install-related problems.
Thanks!


The Easy/Recommended Way: Anaconda
----------------------------------

Spyder is included in the `Anaconda <https://www.anaconda.com/download/>`_
Python distribution, which comes with everything you need to get started in
an all-in-one package.

This is the easiest way to install Spyder for any of our supported platforms,
and the way we recommend to avoid unexpected issues we aren't able to
help you with. If in doubt, you should install via this method;
it generally has the least likelihood of potential pitfalls for non-experts,
and we may be able to provide limited assistance if you do run into trouble.


The Harder Way: Alternative distributions
-----------------------------------------

**Important Note:** While we offer alternative Spyder installation options
for users who desire them, we currently lack the resources to offer individual
assistance for problems specific to installing via these alternative distributions.
Therefore, we recommend you switch to Anaconda if you encounter installation
issues you are unable to solve on your own.

Windows
~~~~~~~

Spyder is also included in the `WinPython <https://winpython.github.io/>`_
scientific Python distribution, although some users have reported bugs specific
to it. You can use it immediately after installing, just like with Anaconda.

macOS
~~~~~

Thanks to the `*MacPorts* project <http://www.macports.org/>`_, Spyder can be
installed using its ``port`` package manager; however, it may be out of date
or have MacPorts-specific issues outside of Spyder's control.

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

GNU/Linux
~~~~~~~~~

Please refer to the `Requirements`_ section to see what other packages you
might need.

**Ubuntu**:

Using the official package manager: ``sudo apt-get install spyder``.

     .. note::

        This package could be slightly outdated. If you find that is the case,
        please use the Debian package mentioned below.


**Debian Unstable**:

Using the package manager: ``sudo apt-get install spyder``

The Spyder's official Debian package is available `here`__

__ http://packages.debian.org/fr/sid/spyder.


**Other Distributions**

Spyder is also available in other GNU/Linux distributions, like

* `Archlinux <https://aur.archlinux.org/packages/?K=spyder>`_

* `Fedora <https://apps.fedoraproject.org/packages/spyder>`_

* `Gentoo <http://packages.gentoo.org/package/dev-python/spyder>`_

* `openSUSE <https://build.opensuse.org/package/show/devel:languages:python/spyder>`_

* `Mageia <http://mageia.madb.org/package/show/name/spyder>`_

Please refer to your distribution's documentation to learn how to install it
there.

|


The Expert Way: Installing with pip
-----------------------------------

**Warning:** While this installation method is a viable option for
experienced users, installing Spyder (and other SciPy stack packages)
with `pip` can lead to a number of tricky issues. While you are welcome
to try this on your own, we unfortunately do not have the resources to help you
if you do run into problems, except to recommend using Anaconda instead.


Requirements
~~~~~~~~~~~~

The requirements to run Spyder are:

* `Python <http://www.python.org/>`_ 2.7 or >=3.3

* `PyQt5 <https://www.riverbankcomputing.com/software/pyqt/download5>`_ >=5.2 or
  `PyQt4 <https://www.riverbankcomputing.com/software/pyqt/download>`_ >=4.6.0
  (PyQt5 is recommended).

* `Qtconsole <http://jupyter.org/qtconsole/stable/>`_ >=4.2.0 -- for an
  enhanced Python interpreter.

* `Rope <http://rope.sourceforge.net/>`_ >=0.9.4 and
  `Jedi <http://jedi.jedidjah.ch/en/latest/>`_ >=0.9.0 -- for code completion,
  go-to-definition and calltips on the Editor.

* `Pyflakes <http://pypi.python.org/pypi/pyflakes>`_  -- for real-time
  code analysis.

* `Sphinx <http://sphinx.pocoo.org>`_ -- for the Help pane rich text mode
  and to get our documentation.

* `Pygments <http://pygments.org/>`_ >=2.0 -- for syntax highlighting and code
  completion in the Editor of all file types it supports.

* `Pylint <http://www.logilab.org/project/pylint>`_  -- for static code analysis.

* `Pycodestyle <https://pypi.python.org/pypi/pycodestyle>`_ -- for style analysis.

* `Psutil <http://code.google.com/p/psutil/>`_  -- for memory/CPU usage in the status
  bar.

* `Nbconvert <http://nbconvert.readthedocs.org/>`_ -- to manipulate Jupyter notebooks
  on the Editor.

* `Qtawesome <https://github.com/spyder-ide/qtawesome>`_ >=0.4.1 -- for an icon theme based on
  FontAwesome.

* Pickleshare -- To show import completions on the Editor and Consoles.

* `PyZMQ <https://github.com/zeromq/pyzmq>`_ -- To run introspection services on the
  Editor asynchronously.

* `QtPy <https://github.com/spyder-ide/qtpy>`_ >=1.2.0 -- To run Spyder with PyQt4 or
  PyQt5 seamlessly.

* `Chardet <https://github.com/chardet/chardet>`_ >=2.0.0-- Character encoding auto-detection
  in Python.

* `Numpydoc <https://github.com/numpy/numpydoc>`_ Used by Jedi to get return types for
  functions with Numpydoc docstrings.

* `Cloudpickle <https://github.com/cloudpipe/cloudpickle>`_ Serialize variables in the
  IPython kernel to send them to Spyder.


Optional modules
~~~~~~~~~~~~~~~~

* `Matplotlib <https://matplotlib.org/>`_ >=1.0 -- for 2D and 3D plotting
  in the consoles.

* `Pandas <http://pandas.pydata.org/>`_ >=0.13.1 -- for view and editing DataFrames
  and Series in the Variable Explorer.

* `Numpy <http://numpy.scipy.org/>`_ -- for view and editing two or three
  dimensional arrays in the Variable Explorer.

* `Sympy <http://www.sympy.org/es/>`_ >=0.7.3 -- for working with symbolic mathematics
  in the IPython console.

* `Scipy <http://www.scipy.org/>`_ -- for importing Matlab workspace files in
  the Variable Explorer.

* `Cython <http://cython.org/>`_ >=0.21 -- Run Cython files or Python files that
  depend on Cython libraries in the IPython console.


Installation procedure
~~~~~~~~~~~~~~~~~~~~~~

You can install Spyder with the ``pip`` package manager, which comes by
default with most Python installations.
Before installing Spyder itself by this method, you need to acquire the
`Python programming language <http://www.python.org/>`_

Then, to install Spyder and its other dependencies, run ``pip install spyder``.
You may need to separately install a Qt binding with ``pip`` if running Python 2;
PyQt5 is strongly recommended though the legacy PyQt4 is also still supported.


Run without installing
~~~~~~~~~~~~~~~~~~~~~~

You can execute Spyder without installing it first by following these steps:

#. Unzip the source package available for download on the
   `Spyder Github repo <https://github.com/spyder-ide/spyder>`_
   (or clone from Github, see the next section)
#. Change current directory to the unzipped directory
#. Run Spyder with the command ``python bootstrap.py``
#. (*Optional*) Build the documentation with ``python setup.py build_doc``.

This is especially useful for beta-testing, troubleshooting and helping develop
Spyder itself.

|


Updating Spyder
---------------

You can update Spyder by:

* Updating Anaconda (recommended), WinPython, MacPorts, or
  through your system package manager, if you installed via those options.

  With Anaconda, just run (in Anaconda Prompt if on Windows)
  ``conda update spyder``
  to update Spyder specifically, and
  ``conda update anaconda``
  to update the rest of the distribution, as desired.

* If you installed Spyder via the advanced/crossplatform method,
  ``pip``, run
  ``pip install --upgrade spyder``

  .. note::

     This command will also update all Spyder dependencies

|


Installing the development version
----------------------------------

If you want to try the next Spyder version before it is released, you can!
You may want to do this for fixing bugs in Spyder, adding new
features, learning how Spyder works or just getting a taste of it.
For more information, please see the CONTRIBUTING.md document included
with the Spyder source or on Github, or for further detail consult the
`online development wiki <https://github.com/spyder-ide/spyder/wiki>`_ .

To do so:

#. Install Spyder `requirements`_

   The recommended and easiest way to do this is with ``conda``:
    ``conda install spyder``
    then
    ``conda remove spyder``

   This installs all of Spyder's dependencies into the environment along with
   the stable/packaged version of Spyder itself, and then removes the latter.

#. Install `Git <http://git-scm.com/downloads>`_, a powerful
   source control management tool.

#. Clone the Spyder source code repository with the command:

   ``git clone https://github.com/spyder-ide/spyder.git``

#. Run Spyder with the ``bootstrap.py`` script from within the cloned directory:
   ``python bootstrap.py``

#. To keep your repository up-to-date, run

   ``git pull``

   inside the cloned directory.

#. (*Optional*) If you want to read the documentation, you must build it first
   with the command

   ``python setup.py build_doc``

|


Help and support
----------------

Spyder websites:

* For a comprehensive guide to spyder troubleshooting, including
  installation issues, read our `Troubleshooting Guide and FAQ
  <https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ>`_.
* For bug reports and feature requests you can go to our
  `website <https://github.com/spyder-ide/spyder/issues>`_.
* For general and development-oriented information, visit
  `our Github wiki <https://github.com/spyder-ide/spyder/wiki>`_.
* For discussions and help requests, you can subscribe to our
  `Google Group <http://groups.google.com/group/spyderlib>`_.
