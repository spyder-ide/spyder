Console
=======

*DRAFT: this page has not been completely updated from Spyder v1.1 to v2.0*

The Spyder console run programs (Python interpreter or system terminal) in a 
separate process:

    * Run Python scripts
    * Open Python interpreters
    * Open IPython interpreters
    * Open terminals (terminals have quite limited features so GNU/Linux users 
      will certainly prefer to use the system terminal instead)

Python/IPython interpreters (or running Python scripts) support the following 
features:

    * Variable explorer
    * Debugging with `pdb`
    * Code completion and calltips
    * User Module Deleter


Related plugins:
    * :doc:`inspector`
    * :doc:`historylog`
    * :doc:`editor`
    * :doc:`explorer`


Reloading modules: the User Module Deleter (UMD)
------------------------------------------------

When enabled, the User Module Deleter (UMD) force the Python interpreter to 
reload modules completely when executing import statements. This feature is 
however disabled by default because some modules may be not work properly with 
it.

When enabled, this option will systematically reload imported modules since its 
activation. In other words, if you would like some modules to be loaded only 
once, you may import them before enabling the option.


Special commands
----------------

The following special commands are supported by the interactive console.

- Edit script

  ``edit foobar.py`` will open ``foobar.py`` with Spyder's editor.
  ``xedit foobar.py`` will open ``foobar.py`` with the external editor.

- Execute script

  ``run foobar.py`` will execute ``foobar.py`` in interactive console.

- Remove references

  ``clear x, y`` will remove references named ``x`` and ``y``.
  
- Shell commands

  ``!cmd`` will execute system command ``cmd`` (example ``!ls`` on Linux or
  ``!dir`` on Windows).
  
- Python help

  ``object?`` will show ``object``'s help in documentation viewer.
  
- GUI-based editor

  ``oedit(object)`` will open an appropriate GUI-based editor to modify object
  ``object`` and will return the result.


The Workspace
-------------

The workspace is a global variable browser for the interactive console with the 
features described below.

.. image:: images/workspace1.png

The following screenshots show some interesting features such as editing 
lists, strings, dictionaries, NumPy arrays, or plotting/showing NumPy arrays
data.

.. image:: images/listeditor.png

.. image:: images/texteditor.png

.. image:: images/dicteditor.png

.. image:: images/arrayeditor.png

.. image:: images/workspace-plot.png

.. image:: images/workspace-imshow.png

The default Workspace configuration allows to browse global variables without 
slowing the interactive console even with very large NumPy arrays, lists or 
dictionaries. The trick is to truncate values, to hide collection contents 
(i.e. showing '<list @ address>' instead of list contents) and to show only 
mininum and maximum values for NumPy arrays (see context menu options on the 
screenshot at the top of this page).

However, most of the time, choosing the opposite options won't have too much 
effect on interactive console's performance:

.. image:: images/workspace2.png

