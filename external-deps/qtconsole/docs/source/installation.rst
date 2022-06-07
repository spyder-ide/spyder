Installation
============
The Qt console requires Qt, such as
`PyQt5 <https://www.riverbankcomputing.com/software/pyqt/intro>`_,
`PyQt4 <https://www.riverbankcomputing.com/software/pyqt/download>`_, or
`PySide <http://pyside.github.io/docs/pyside>`_.

Although `pip <https://pypi.python.org/pypi/pip>`_ and
`conda <http://conda.pydata.org/docs>`_ may be used to install the Qt console,
conda is simpler to use since it automatically installs PyQt. Alternatively,
qtconsole installation with pip needs additional steps since pip cannot install
the Qt requirement.

Install using conda
-------------------
To install::

    conda install qtconsole

.. note::

    If the Qt console is installed using conda, it will **automatically**
    install the Qt requirement as well.

Install using pip
-----------------
To install::

    pip install qtconsole

.. important::

    Make sure that Qt is installed. Unfortunately, Qt cannot be
    installed using pip. The next section gives instructions on installing Qt.

Installing Qt (if needed)
-------------------------
We recommend installing PyQt with `conda <http://conda.pydata.org/docs>`_::

    conda install pyqt

or with a system package manager. For Windows, PyQt binary packages may be
used.

For example with Linux Debian's system package manager, use::

   sudo apt-get install python3-pyqt5 # PyQt5 on Python 3
   sudo apt-get install python3-pyqt4 # PyQt4 on Python 3
   sudo apt-get install python-qt4    # PyQt4 on Python 2

.. seealso::

   `Installing Jupyter <https://jupyter.readthedocs.io/en/latest/install.html>`_
   The Qt console is part of the Jupyter ecosystem.
