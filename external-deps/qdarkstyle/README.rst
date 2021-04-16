QDarkStyleSheet
===============

|Build Status| |Docs Status| |Latest PyPI version| |License: MIT|
|License: CC BY 4.0| |Conduct|

The most complete dark/light style sheet for Qt applications (Qt4*, Qt5,
PySide*, PySide2, PyQt4*, PyQt5, QtPy, PyQtGraph, Qt.Py) for Python
2*/3 and C++.

`Check out the complete documentation. <https://qdarkstylesheet.readthedocs.io/en/latest/screenshots.html>`__


What is new?
------------


Version 3
~~~~~~~~~

In the current version 3, `qdarkstyle` is now working as a theme framework,
currently for dark/light themes, keeping styled widgets identical throughout
theme colors.

The palette has been redefined and improved (UI/UX) to accept more colors
and to be able to implement new themes thanks to the
`Spyder team <https://github.com/spyder-ide/spyder>`__ collaboration.

The current stable version is using Python 3 (preferable 3.6+) and Qt5
(PyQt5 and PySide 2).

We still preparing the portability to Qt6 since we need changes in
`QtPy <https://github.com/spyder-ide/qtpy>`__ dependency project.

[*] Python 2, as well as Qt4 (PyQt4 and PySide), will not be supported anymore.
They still there as it is, but no back-compatibility, fixes, nor features
will be implemented.

Version 2
~~~~~~~~~

We moved to QtPy to simplify your code in v2.8, thus this is a required
dependency now. We included special patches in three main categories:
operating system, Qt/binding version, application.

Included in that, lots of widgets' styles were included/fixed. A Qt
application example (Python only) with almost all types of widgets and
combinations were included to serve as a portfolio and a checklist for
new styles.

We have added SCSS in v2.7, so the palette can be accessed programmatically.
Also, many scripts were added to give freedom to developers who want to
change the colors of our palette. All images and icons were revised, also
creating SVG files for all of them.

In version 2.6 and later, a restructure stylesheet is provided. The
palette has only 9 colors. Most widgets are revised and their styles
were improved. We also provide a command line (script) to get info that
could be used when opening issues. See the image below.


Version 1
~~~~~~~~~

First stable release of QDarkStyle.


Installation
------------


Python
~~~~~~

From PyPI: Get the latest stable version of ``qdarkstyle`` package using
*pip* (preferable):

    .. code:: bash

        pip install qdarkstyle


From code: Download/clone the project, go to ``qdarkstyle`` folder then:

-  You can use the *setup* script and pip install.

    .. code:: bash

        pip install .


-  Or, you can use the *setup* script with Python:

    .. code:: bash

        python setup.py install


C++
~~~

- Download/clone the project and copy the following files to your
  application directory (keep the existing directory hierarchy).
  Substitute the **theme** by the currently available (dark/light)
  the theme you need to use.

    -  **qdarkstyle/theme/style.qss**
    -  **qdarkstyle/theme/style.qrc**
    -  **qdarkstyle/theme/rc/** (the whole directory)


-  Add **qdarkstyle/theme/style.qrc** to your **.pro file** as follows:

    .. code:: c++

        RESOURCES += qdarkstyle/theme/style.qrc


-  Load the stylesheet:

    .. code:: c++

        QFile f(":qdarkstyle/theme/style.qss");

        if (!f.exists())   {
            printf("Unable to set stylesheet, file not found\n");
        }
        else   {
            f.open(QFile::ReadOnly | QFile::Text);
            QTextStream ts(&f);
            qApp->setStyleSheet(ts.readAll());
        }


Note: The ":" in the file name is necessary to define that file as a
resource library. For more information see the discussion
`here <https://github.com/ColinDuquesnoy/QDarkStyleSheet/pull/87>`__.


Usage in applications
---------------------


If your project already uses QtPy or you need to set it programmatically,
it is far more simple

.. code:: python

    import sys
    import qdarkstyle
    import os

    # set the environment variable to use a specific wrapper
    # it can be set to pyqt, pyqt5, pyside or pyside2 (not implemented yet)
    # you do not need to use QtPy to set this variable
    os.environ['QT_API'] = 'pyqt5'

    # import from QtPy instead of doing it directly
    # note that QtPy always uses PyQt5 API
    from qtpy import QtWidgets

    # create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()

    # setup stylesheet
    # the default system in qdarkstyle uses qtpy environment variable
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    # run
    window.show()
    app.exec_()


If you are using PyQt5 directly, see the complete example

.. code:: python

    import sys
    import qdarkstyle
    from PyQt5 import QtWidgets

    # create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()

    # setup stylesheet
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    # or in new API
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

    # run
    window.show()
    app.exec_()


Here is an example using PySide2

.. code:: python

    import sys
    import qdarkstyle
    from PyQt5 import QtWidgets

    # create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()

    # setup stylesheet
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    # or in new API
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside2'))

    # run
    window.show()
    app.exec_()


If you use PyQtGraph, then the code is

.. code:: python

    import sys
    import qdarkstyle
    import os

    # set the environment variable to use a specific wrapper
    # it can be set to PyQt, PyQt5, PySide or PySide2 (not implemented yet)
    os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'

    # import from pyqtgraph instead of doing it directly
    # note that PyQtGraph always uses PyQt4 API
    from pyqtgraph.Qt import QtGui

    # create the application and the main window
    app = QtGui.QApplication(sys.argv)
    window = QtGui.QMainWindow()

    # setup stylesheet
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api=os.environ['PYQTGRAPH_QT_LIB'])

    # run
    window.show()
    app.exec_()

If you are using Qt.py, which is different from qtpy, you should install
qtpy then set both to the same binding.


Usage of example/portfolio
--------------------------


There is an example included in the package. You only need to have PySide2 or
PyQt5 installed on your system.

.. code:: bash

    # dark theme example
    $ qdarkstyle.example --palette=dark

    # light theme example
    $ qdarkstyle.example --palette=light

    # no theme/style sheet applied
    $ qdarkstyle.example --palette=none

    # check all options included
    $ qdarkstyle.example --help


Changelog
---------

Please, see `CHANGES <CHANGES.rst>`__ file.


License
-------

This project is licensed under the MIT license. Images contained in this
project is licensed under CC-BY license.

For more information see `LICENSE <LICENSE.rst>`__ file.


Authors
-------

For more information see `AUTHORS <AUTHORS.rst>`__ file.


Contributing
------------

Most widgets have been styled. If you find a widget that has not been
style, just open an issue on the issue tracker or, better, submit a pull
request.

If you want to contribute, see `CONTRIBUTING <CONTRIBUTING.rst>`__ file.

.. |Build Status| image:: https://travis-ci.org/ColinDuquesnoy/QDarkStyleSheet.png?branch=master
   :target: https://travis-ci.org/ColinDuquesnoy/QDarkStyleSheet
.. |Docs Status| image:: https://readthedocs.org/projects/qdarkstylesheet/badge/?version=latest&style=flat
   :target: https://qdarkstylesheet.readthedocs.io
.. |Latest PyPI version| image:: https://img.shields.io/pypi/v/QDarkStyle.svg
   :target: https://pypi.python.org/pypi/QDarkStyle
.. |License: MIT| image:: https://img.shields.io/dub/l/vibe-d.svg?color=lightgrey
   :target: https://opensource.org/licenses/MIT
.. |License: CC BY 4.0| image:: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg
   :target: https://creativecommons.org/licenses/by/4.0/
.. |Conduct| image:: https://img.shields.io/badge/code%20of%20conduct-contributor%20covenant-green.svg?style=flat&color=lightgrey
   :target: http://contributor-covenant.org/version/1/4/
