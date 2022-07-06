.. _changelog:

Changes in Jupyter Qt console
=============================

.. _5.3:

5.3
~~~

5.3.0
-----

`5.3.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.3.0>`__

Additions
+++++++++

* Add support for PyQt6.

Changes
+++++++

* Don't show spurious blank lines when running input statements.
* Fix showing Latex images with dark background colors.
* Drop support for Python 3.6

.. _5.2:

5.2
~~~

5.2.2
-----

`5.2.2 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.2.2>`__

* Fix implicit int to float conversion for Python 3.10 compatibility.
* Fix building documentation in ReadTheDocs.

5.2.1
-----

`5.2.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.2.1>`__

* Fix error when deleting CallTipWidget.
* Another fix for the 'Erase in Line' ANSI code.

5.2.0
-----

`5.2.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.2.0>`__

Changes
+++++++

- Fix hidden execution requests.
- Fix ANSI code for erase line.

.. _5.1:

5.1
~~~

5.1.1
-----

`5.1.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.1.1>`__

* Improve handling of different keyboard combinations.
* Move cursor to the beginning of buffer if on the same line.

5.1.0
-----

`5.1.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.1.0>`__

Additions
+++++++++

- Two new keyboard shortcuts: Ctrl + Up/Down to go to the beginning/end
  of the buffer.

Changes
+++++++

- Monkeypatch RegexLexer only while in use by qtconsole.
- Import Empty from queue module.


.. _5.0:

5.0
~~~

5.0.3
-----

`5.0.3 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.0.3>`__

* Emit kernel_restarted signal only after a kernel crash.

5.0.2
-----

`5.0.2 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.0.2>`__

* Fix launching issue with Big Sur
* Remove partial prompt on copy

5.0.1
-----

`5.0.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.0.1>`__

* Add python_requires to setup.py for Python 3.6+ compatibility

5.0.0
-----

`5.0.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/5.0>`__

Additions
+++++++++

- Add option to set completion type while running.

Changes
+++++++

- Emit kernel_restarted after restarting kernel.
- Drop support for Python 2.7 and 3.5.


.. _4.7:

4.7
~~~

.. _4.7.7:

4.7.7
-----

`4.7.7 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.7>`__

* Change font width calculation to use horizontalAdvance

.. _4.7.6:

4.7.6
-----

`4.7.6 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.6>`__

* Replace qApp with QApplication.instance().
* Fix QFontMetrics.width deprecation.

.. _4.7.5:

4.7.5
-----

`4.7.5 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.5>`__

* Print input if there is no prompt.

.. _4.7.4:

4.7.4
-----

`4.7.4 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.4>`__

* Fix completion widget text for paths and files.
* Make Qtconsole work on Python 3.8 and Windows.

.. _4.7.3:

4.7.3
-----

`4.7.3 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.3>`__

* Fix all misuses of QtGui.

.. _4.7.2:

4.7.2
-----

`4.7.2 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.2>`__

* Set updated prompt as previous prompt object in JupyterWidget.
* Fix some Qt incorrect imports.

.. _4.7.1:

4.7.1
-----

`4.7.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.1>`__

* Remove common prefix from path completions.
* Use QtWidgets instead of QtGui to create QMenu instances.

4.7.0
-----

`4.7.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.7.0>`__

Additions
+++++++++

- Use qtpy as the shim layer for Python Qt bindings and remove our own
  shim.

Changes
+++++++

- Remove code to expand tabs to spaces.
- Skip history if it is the same as the input buffer.


.. _4.6:

4.6
~~~

4.6.0
-----

`4.6.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.6>`__

Additions
+++++++++

- Add an option to configure scrollbar visibility.

Changes
+++++++

- Avoid introducing a new line when executing code.


.. _4.5:

4.5
~~~

.. _4.5.5:

4.5.5
-----

`4.5.5 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.5.5>`__

* Set console to read only after input.
* Allow text to be added before the prompt while autocompleting.
* Scroll when adding text even when not executing.

.. _4.5.4:

4.5.4
-----

`4.5.4 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.5.4>`__

- Fix emoji highlighting.

.. _4.5.3:

4.5.3
-----

`4.5.3 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.5.3>`__

- Fix error when closing comms.
- Fix prompt automatically scrolling down on execution.

.. _4.5.2:

4.5.2
-----

`4.5.2 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.5.2>`__

- Remove deprecation warnings in Python 3.8
- Improve positioning and content of completion widget.
- Scroll down for output from remote commands.

.. _4.5.1:

4.5.1
-----

`4.5.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.5.1>`__

- Only use setuptools in setup.py to fix uploading tarballs to PyPI.

4.5.0
-----

`4.5.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.5>`__

Additions
+++++++++

- Add Comms to qtconsole.
- Add kernel language name as an attribute of JupyterWidget.

Changes
+++++++

- Use new traitlets API with decorators.


.. _4.4:

4.4
~~~

.. _4.4.4:

4.4.4
-----

`4.4.4 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.4.4>`__

- Prevent cursor from moving to the end of the line while debugging.

.. _4.4.3:

4.4.3
-----

`4.4.3 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.4.3>`__

- Fix complete statements check inside indented block for Python after
  the IPython 7 release.
- Improve auto-scrolling during execution.

.. _4.4.2:

4.4.2
-----

`4.4.2 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.4.2>`__

- Fix incompatibility with PyQt5 5.11.

.. _4.4.1:

4.4.1
-----

`4.4.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.4.1>`__

- Fix setting width and height when displaying images with IPython's Image.
- Avoid displaying errors when using Matplotlib to generate pngs from Latex.

.. _4.4.0:

4.4.0
-----

`4.4.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.4>`__

Additions
+++++++++

- :kbd:`Control-D` enters an EOT character if kernel is executing and input is
  empty.
- Implement block indent on multiline selection with :kbd:`Tab`.
- Change the syntax highlighting style used in the console at any time. It can
  be done in the menu ``View > Syntax Style``.

Changes
+++++++

- Change :kbd:`Control-Shift-A` to select cell contents first.
- Change default tab width to 4 spaces.
- Enhance handling of input from other clients.
- Don't block the console when the kernel is asked for completions.

Fixes
+++++

- Fix bug that make PySide2 a forbidden binding.
- Fix IndexError when copying prompts.
- Fix behavior of right arrow key.
- Fix behavior of :kbd:`Control-Backspace` and :kbd:`Control-Del`


.. _4.3:

4.3
~~~

.. _4.3.1:

4.3.1
-----

`4.3.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.3.1>`__

- Make %clear to delete previous output on Windows.
- Fix SVG rendering.

.. _4.3.0:

4.3.0
-----

`4.3 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.3>`__

Additions
+++++++++

- Add :kbd:`Shift-Tab` shortcut to unindent text
- Add :kbd:`Control-R` shortcut to rename the current tab
- Add :kbd:`Alt-R` shortcut to set the main window title
- Add :kbd:`Command-Alt-Left` and :kbd:`Command-Alt-Right` shortcut to switch
  tabs on macOS
- Add support for PySide2
- Add support for Python 3.5
- Add support for 24 bit ANSI color codes
- Add option to create new tab connected to the existing kernel

Changes
+++++++

- Rename `ConsoleWidget.width/height` traits to `console_width/console_height`
  to avoid a name clash with the `QWidget` properties. Note: the name change
  could be, in rare cases if a name collision exists, a code-breaking
  change.
- Change :kbd:`Tab` key behavior to always indent to the next increment of 4 spaces
- Change :kbd:`Home` key behavior to alternate cursor between the beginning of text
  (ignoring leading spaces) and beginning of the line
- Improve documentation of various options and clarified the docs in some places
- Move documentation to ReadTheDocs

Fixes
+++++

- Fix automatic indentation of new lines that are inserted in the middle of a
  cell
- Fix regression where prompt would never be shown for `--existing` consoles
- Fix `python.exe -m qtconsole` on Windows
- Fix showing error messages when running a script using `%run`
- Fix `invalid cursor position` error and subsequent freezing of user input
- Fix syntax coloring when attaching to non-IPython kernels
- Fix printing when using QT5
- Fix :kbd:`Control-K` shortcut (delete until end of line) on macOS
- Fix history browsing (:kbd:`Up`/:kbd:`Down` keys) when lines are longer than
  the terminal width
- Fix saving HTML with inline PNG for Python 3
- Various internal bugfixes

.. _4.2:

4.2
~~~

`4.2 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.2>`__

- various latex display fixes
- improvements for embedding in Qt applications (use existing Qt API if one is already loaded)


.. _4.1:

4.1
~~~

.. _4.1.1:

4.1.1
-----

`4.1.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.1.1>`__

- Set AppUserModelID for taskbar icon on Windows 7 and later

.. _4.1.0:

4.1.0
-----

`4.1 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.1>`__

-  fix regressions in copy/paste, completion
-  fix issues with inprocess IPython kernel
-  fix ``jupyter qtconsole --generate-config``

.. _4.0:

4.0
~~~

.. _4.0.1:

4.0.1
-----

-  fix installation issues, including setuptools entrypoints for Windows
-  Qt5 fixes

.. _4.0.0:

4.0.0
-----

`4.0 on GitHub <https://github.com/jupyter/qtconsole/milestones/4.0>`__

First release of the Qt console as a standalone package.
