Installation
============
The Qt console requires Qt, such as
`PyQt6 <https://pypi.org/project/PyQt6>`_,
`PySide6 <https://pypi.org/project/PySide6>`_,
`PyQt5 <https://pypi.org/project/PyQt5>`_,
`PySide2 <https://pypi.org/project/PySide2>`_.

Although `pip <https://pypi.python.org/pypi/pip>`_ and
`conda <http://conda.pydata.org/docs>`_ may be used to install the Qt console,
conda is simpler to use since it automatically installs PyQt.

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

Installing Qt (if needed)
-------------------------
We recommend installing PyQt with `conda <http://conda.pydata.org/docs>`_::

    conda install pyqt

or with pip::

    pip install PyQt5

For example with Linux Debian's system package manager, use::

   sudo apt-get install python3-pyqt5 # PyQt5 on Python 3

See also::

   `Installing Jupyter <https://jupyter.readthedocs.io/en/latest/install.html>`_
   The Qt console is part of the Jupyter ecosystem.
