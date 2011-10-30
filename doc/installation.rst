Installation
============

Dependencies
------------

Requirements:
    * Python 2.5+ 
    * PyQt4 4.4+ or PySide 1.0.8+

Recommended modules:
    * pyflakes v0.5.0+ (real-time code analysis)
    * rope 0.9.2+ (editor code completion, calltips and go-to-definition)
    * sphinx 0.6+ (object inspector's rich text mode)
    * numpy (N-dimensional arrays)
    * scipy (signal/image processing)
    * matplotlib (2D/3D plotting)

Optional modules:
    * IPython (enhanced Python interpreter)
    * pylint (code analysis)
    * pep8 (style analysis)

.. note::

    Since v2.0, the `QScintilla` library (source code editor widgets for 
    `PyQt4`) is no longer needed as Spyder is relying on pure Python/Qt
    features (provided by `PyQt4` or `PySide`).


Installation
------------

From the source package:
    `python setup.py install`


Running from source
-------------------

It is also possible to run Spyder directly from unpacked source folder:
    `python bootstrap.py`

This is especially useful for troubleshooting and development of Spyder itself.


Help and support
----------------

Spyder websites:
    * Downloads, bug reports and feature requests: http://spyderlib.googlecode.com
    * Discussions: http://groups.google.com/group/spyderlib
