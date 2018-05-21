Overview
========

Spyder is a Python development environment with the following key features:

Key features:

* general features:
  
  * MATLAB-like PYTHONPATH management dialog box (works with all consoles)
  * Windows only: current user environment variables editor
  * direct links to documentation (Python, Matplotlib, !NumPy, !Scipy, etc.)
  * direct link to Python(x,y) launcher
  * direct links to !QtDesigner, !QtLinguist and !QtAssistant (Qt documentation)
    
* *preferences* dialog box:
  
  * keyboard shortcuts
  * syntax coloring schemes (source editor, history log, help)
  * console: background color (black/white), automatic code completion, etc.
  * and a lot more...
    
* :doc:`editor`:
  
  * syntax coloring (Python, C/C++, Fortran)
  * *breakpoints* and *conditional breakpoints* (debugger: `pdb`)
  * run or debug Python scripts (see console features)
  * *run configuration* dialog box:
    
    * working directory
    * command line options
    * run in a new Python interpreter or in an existing Python interpreter or IPython client
    * Python interpreter command line options
      
  * *code outline explorer*: functions, classes, if/else/try/... statements
  * *powerful code introspection features* (powered by `rope`):
    
    * *code completion*
    * *calltips*
    * *go-to-definition*: go to object (any symbol: function, class, attribute, etc.) definition by pressing Ctrl+Left mouse click on word or Ctrl+G (default shortcut)
      
  * *occurrence highlighting*
  * typing helpers (optional):
    
    * automatically insert closing parentheses, braces and brackets
    * automatically unindent after 'else', 'elif', 'finally', etc.
      
  * *to-do* lists (TODO, FIXME, XXX)
  * errors/warnings (real-time *code analysis* provided by `pyflakes`)
  * integrated static code analysis (using `pylint`)
  * direct link to `winpdb` external debugger
    
* :doc:`console`:
  
  * *all consoles are executed in a separate process*
  * *code completion*/calltips and automatic link to help (see below)
  * open Python interpreters or basic terminal command windows
  * run Python scripts (see source editor features)
  * *variable explorer*:
    
    * *GUI-based editors* for a lot of data types (numbers, strings, lists, arrays, dictionaries, ...)
    * *import/export data* from/to a lot of file types (text files, !NumPy files, MATLAB files)
    * multiple array/list/dict editor instances at once, thus allowing to compare variable contents
    * data visualization
      
* :doc:`historylog`
* :doc:`help`:
  
  * provide documentation or source code on any Python object (class, function, module, ...)
  * documentation may be displayed as an html page thanks to the rich text mode (powered by `sphinx`)
    
* :doc:`onlinehelp`: automatically generated html documentation on installed Python modules
* :doc:`findinfiles`: find string occurrences in a directory, a mercurial repository or directly in PYTHONPATH (support for regular expressions and  included/excluded string lists)
* :doc:`fileexplorer`
* :doc:`projects`


Spyder may also be used as a PyQt5 extension library (module
'spyder'). For example, the Python interactive shell widget
used in Spyder may be embedded in your own PyQt5 application.
