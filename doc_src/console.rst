Console
=======

The **Console** is where you may enter, interact with and visualize data, 
inside a command interpreter (Python or IPython).
All the commands entered in the console are executed in a separate process,
thus allowing the user to interrupt any process at any time.

Many command windows may be created in the **Console**:

    * Python interpreter
    * IPython interpreter (the external module `IPython` is required)
    * Running Python script
    * System command window (this terminal emulation window has quite limited 
      features compared to a real terminal, so GNU/Linux users will certainly 
      prefer to use the system terminal instead, i.e. outside Spyder)

Python-based command windows support the following features:

    * Code completion and calltips
    * Variable explorer with GUI-based editors for arrays, lists, 
      dictionaries, strings, etc.
    * Debugging with standard Python debugger (`pdb`): at each breakpoint 
      the corresponding script is opened in the **Editor** at the breakpoint 
      line number
    * User Module Deleter (see below)


Related plugins:
    * :doc:`inspector`
    * :doc:`historylog`
    * :doc:`editor`
    * :doc:`explorer`


Reloading modules: the User Module Deleter (UMD)
------------------------------------------------

When working with Python scripts interactively, one must keep in mind that 
Python import modules from the source code on disk only at the first import: 
during this first import, the byte code is generated (.pyc file) if necessary, 
and when re-importing the same module, the byte code will be directly used 
even if the source code file (.py[w] file) has changed meanwhile.
For example, when running two times a module named for example 'mod_a' which 
is importing a module named 'mod_b'

When enabled, the User Module Deleter (UMD) force the Python interpreter to 
reload modules completely when executing a Python script.

When enabled, this option will systematically reload imported modules since its 
activation. In other words, if you would like some modules to be loaded only 
once, you may import them before enabling the option.
