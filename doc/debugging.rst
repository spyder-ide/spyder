Debugging
=========

Debugging in Spyder is supported thanks to the following Python modules:

* `pdb`: the Python debugger, which is included in Python standard library.
    
* `winpdb`: a graphical frontend to `pdb`, which is an external package 
  (in the :doc:`editor`, press F7 to run `winpdb` on the currently edited 
  script).
    
Debugging with pdb
------------------

The Python debugger is partly integrated in Spyder:

* Breakpoints may be defined in the :doc:`editor`.

  * Simple breakpoints can be set from the Run menu, by keyboard shortcut
    (F12 by default), or by double-click to the left of line numbers
    in the :doc:`editor`.
  * Conditional breakpoints can also be set from the Run menu, by
    keyboard shortcut (Shift+F12 by default), or by Shift+double-click
    to the left of line numbers in the :doc:`editor`.

* The current frame (debugging step) is highlighted in the :doc:`editor`.
* At each breakpoint, globals may be accessed through 
  the :doc:`variableexplorer`.

For a simple, yet quite complete introduction to `pdb`, you may read this:
http://pythonconquerstheuniverse.wordpress.com/category/python-debugger/


Related plugins:

* :doc:`editor`
* :doc:`console`
