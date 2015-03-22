# History of changes

## Version 2.3.4

### New features since v2.3.3

* Debugging
    * After pressing the Debug button (or `Ctrl+F5`) move to the first breakpoint
* IPython Console
    * Drop support for Sympy versions less than 0.7.3
* Python Console
    * Remove support to run system commands with ! (like !diff)
* Editor
    * Accept drops from compressed files on Windows

### Bug fixes (since v2.3.3)

**Issues**

* [Issue 2259](/spyder-ide/spyder/issues/2259) - spyder crashes if ipython installed but not pygments
* [Issue 2257](/spyder-ide/spyder/issues/2257) - Cannot plot inline in IPython console on Linux
* [Issue 2252](/spyder-ide/spyder/issues/2252) - Update French translations for 2.3.4
* [Issue 2245](/spyder-ide/spyder/issues/2245) - Importing a module with debugger causes "TypeError: decoding Unicode is not supported"
* [Issue 2239](/spyder-ide/spyder/issues/2239) - SyntaxErrors with Python 3.2
* [Issue 2234](/spyder-ide/spyder/issues/2234) - Object Inspector is not showing "No documentation available" for objects without docstring
* [Issue 2227](/spyder-ide/spyder/issues/2227) - IPython does not work with brewed or virtualenv Python(s) in MacOSX
* [Issue 2223](/spyder-ide/spyder/issues/2223) - Spyder2.3.3 Code completion breaks
* [Issue 2207](/spyder-ide/spyder/issues/2207) - Spyder's WM_CLASS is empty, resulting in unexpected behavior for task managers
* [Issue 2203](/spyder-ide/spyder/issues/2203) - Code completion issue with Jedi
* [Issue 2197](/spyder-ide/spyder/issues/2197) - IPython consoles are not named correctly when connecting to existing kernels and passing the full kernel path
* [Issue 2158](/spyder-ide/spyder/issues/2158) - runfile with path containing apostrophes (quotes) will not work
* [Issue 2151](/spyder-ide/spyder/issues/2151) - Long NumPy arrays throw off errors
* [Issue 2146](/spyder-ide/spyder/issues/2146) - Special character "!" is not processed correctly when debugging in Python consoles
* [Issue 2081](/spyder-ide/spyder/issues/2081) - Spyder crashes on Windows because of non-ascii chars in working directory
* [Issue 2058](/spyder-ide/spyder/issues/2058) - Don't execute external commands (!) when running pdb in python consoles
* [Issue 2034](/spyder-ide/spyder/issues/2034) - Execute until first breakpoint when pressing the Debug button
* [Issue 2032](/spyder-ide/spyder/issues/2032) - Dragging (not dropping) file from 7zip over spyder window causes TypeError in dragEnterEvent
* [Issue 1952](/spyder-ide/spyder/issues/1952) - spyderlib.utils.external overrides modules for script execution
* [Issue 1948](/spyder-ide/spyder/issues/1948) - spyder 2.3 ipython console startup code or file not working
* [Issue 1856](/spyder-ide/spyder/issues/1856) - Running in external system terminals is not working on Windows and Python 3
* [Issue 1845](/spyder-ide/spyder/issues/1845) - Spyder crashes on launch trying to load the project config file (.spyderproject)
* [Issue 1568](/spyder-ide/spyder/issues/1568) - raw_input borks with '!'
* [Issue 1529](/spyder-ide/spyder/issues/1529) - Plot A List Of Floats In Variable Explorer Not Possible
* [Issue 1380](/spyder-ide/spyder/issues/1380) - Problems with sitecustomize because of pickleshare library
* [Issue 1366](/spyder-ide/spyder/issues/1366) - "Highlight occurrences" setting is lost after IDE restart
* [Issue 1359](/spyder-ide/spyder/issues/1359) - Mac app - Sometimes it's not possible to get the user env vars
* [Issue 1321](/spyder-ide/spyder/issues/1321) - The PYTHONPATH manager on the Mac app does not work with the EPD64 interpreter
* [Issue 1151](/spyder-ide/spyder/issues/1151) - Ctrl-C doesn't copy to clipboard in object inspector

In this release they were closed 29 issues

**Pull requests**

* [PR 2255](/spyder-ide/spyder/pull/2255) - Update French translations
* [PR 2242](/spyder-ide/spyder/pull/2242) - Improve message for no docstring
* [PR 2233](/spyder-ide/spyder/pull/2233) - catch a reason to crash on startup
* [PR 2224](/spyder-ide/spyder/pull/2224) - Fix a bug in completion if callback value is not converted to string
* [PR 2219](/spyder-ide/spyder/pull/2219) - Open configuration file with utf-8 encoding on Windows and Python 2 
* [PR 2214](/spyder-ide/spyder/pull/2214) - Fix zlib segmentation fault in Anaconda 3.4 Linux

In this release they were merged 6 pull requests


----


## Version 2.3.3

### New features since v2.3.2

* Editor
    * Use the [Jedi](http://http://jedi.jedidjah.ch) library to do code completions
    * Add `Ctrl+=` as a shortcut to do Zoom in and `Ctrl+0` to reset zoom
    * Add an option to show blank spaces, under the Source menu. There is also an option to make this permanent under `Preferences > Editor`.
* IPython Console
    * Don't print DataFrames as html tables because this won't be supported since IPython 3.0
    * Drop support for IPython 0.13
    * Support the upcoming 3.0 version
    * Add `Ctrl+T` as shortcut to open new consoles
    * Simplify how consoles are named
* Variable Explorer
    * More optimizations to handle big DataFrames and NumPy arrays (i.e. with more than 1e6 elements).
* Main Window
    * Add `Ctrl+W` and `Ctrl+F4` to close tabs in all platforms
    * Show shortcuts to move to each pane in `View > Panes`

### Bug fixes (since v2.3.2)

* [Issue 670](/spyder-ide/spyder/issues/670) - Visual help for indentation: draw spaces and tabs
* [Issue 987](/spyder-ide/spyder/issues/987) - Allow the file explorer to open any file into the editor as text
* [Issue 1213](/spyder-ide/spyder/issues/1213) - Augment or replace rope with Jedi
* [Issue 1461](/spyder-ide/spyder/issues/1461) - Kill button 'clicked' signal is connected but never disconnected on the python shell
* [Issue 1469](/spyder-ide/spyder/issues/1469) - Add support to get code completions for compiled modules (e.g. OpenCV)
* [Issue 1484](/spyder-ide/spyder/issues/1484) - Debug ignores breakpoints, if there's no ASCII characters in a file path
* [Issue 1574](/spyder-ide/spyder/issues/1574) - Creating file gives TypeError on Python 3
* [Issue 1718](/spyder-ide/spyder/issues/1718) - Keyboard shortcut to come back to normal zoom level
* [Issue 1808](/spyder-ide/spyder/issues/1808) - Shortcuts to create and close IPython consoles
* [Issue 1911](/spyder-ide/spyder/issues/1911) - Transition to git and github
* [Issue 1930](/spyder-ide/spyder/issues/1930) - Evaluating cell or selection in Python consoles takes ages
* [Issue 1946](/spyder-ide/spyder/issues/1946) - Spyder with GTK/GTKAgg backend on GNOME freezes
* [Issue 1987](/spyder-ide/spyder/issues/1987) - Matplotlib backend in Mac can't be changed when using PySide
* [Issue 1990](/spyder-ide/spyder/issues/1990) - exception in spyder internal console when typing 'exit(' in editor
* [Issue 1993](/spyder-ide/spyder/issues/1993) - autocomplete in the middle of a word
* [Issue 2006](/spyder-ide/spyder/issues/2006) - Your IPython frontend and kernel versions are incompatible
* [Issue 2019](/spyder-ide/spyder/issues/2019) - Winpdb (F7) doesn't work in Python 3
* [Issue 2022](/spyder-ide/spyder/issues/2022) - TkAgg backend unresponsive window on Linux and OS X
* [Issue 2040](/spyder-ide/spyder/issues/2040) - Improve inline backend options
* [Issue 2049](/spyder-ide/spyder/issues/2049) - Pandas Dataframe not opening in Variable Explorer
* [Issue 2064](/spyder-ide/spyder/issues/2064) - "About spyder" and "Report issue ..." output errors
* [Issue 2072](/spyder-ide/spyder/issues/2072) - Unable to bring up tutorial
* [Issue 2074](/spyder-ide/spyder/issues/2074) - Profiler - sorting by Total Time sorts by string order, not numeric order
* [Issue 2080](/spyder-ide/spyder/issues/2080) - Bug on Variable Explorer while viewing DataFrames, with timestamp columns
* [Issue 2082](/spyder-ide/spyder/issues/2082) - Missing py27 dmg download
* [Issue 2092](/spyder-ide/spyder/issues/2092) - PYTHON pathmanager on windows 8 does not work properly
* [Issue 2105](/spyder-ide/spyder/issues/2105) - Spyder 2.3.2 freezes when viewing big collections on the Variable Explorer
* [Issue 2108](/spyder-ide/spyder/issues/2108) - UnicodeDecodeError in the Internal console when trying to run a file with non-ascii chars and synatx errors in it
* [Issue 2109](/spyder-ide/spyder/issues/2109) - Go to definition menu item inactive with rope present.
* [Issue 2126](/spyder-ide/spyder/issues/2126) - iPython console rendering of pandas.DataFrame._repr_html_() note in changelog
* [Issue 2139](/spyder-ide/spyder/issues/2139) - Small typo in Help : Plotting examples 
* [Issue 2143](/spyder-ide/spyder/issues/2143) - Closing takes a long time with Python 3.4
* [Issue 2160](/spyder-ide/spyder/issues/2160) - UnicodeDecodeError when inspecting pandas DataFrame in ipython console
* [Issue 2190](/spyder-ide/spyder/issues/2190) - Update French translations for 2.3.3


----


## Version 2.3.2

### New features since v2.3.1

* Editor
    * Improve cells visualization
    * Add support for drag selection and improve look of line number area
    * Open on it any text file present in the File Explorer
    * View and edit IPython notebooks as Json files
    * Syntax highlighting for Json and Yaml files
* Variable Explorer:
    * Import csv files as DataFrames (if Pandas is present)
    * Improve browsing speed for NumPy arrays and DataFrames with more than 1e5 rows
* Debugging
    * Make it easier to set conditions through the Breakpoints pane
* IPython Console
    * Add a stop button to easily stop computations
* Python Console
    * Fixes various issues with unicode

### Bug fixes (since v2.3.1)

* [Issue 556](/spyder-ide/spyder/issues/556) - Deal with DOS/Windows encoding
* [Issue 681](/spyder-ide/spyder/issues/681) - Allow printing Unicode characters
* [Issue 875](/spyder-ide/spyder/issues/875) - Add indication that console is busy
* [Issue 883](/spyder-ide/spyder/issues/883) - Open all text files in the Editor from the File Explorer
* [Issue 1200](/spyder-ide/spyder/issues/1200) - Strings with accents and variable explorer
* [Issue 1546](/spyder-ide/spyder/issues/1546) - Spyder issues with unicode under windows
* [Issue 1767](/spyder-ide/spyder/issues/1767) - Some support for the ipynb format
* [Issue 1774](/spyder-ide/spyder/issues/1774) - can't open preferences or interpreter after changing path to intepreter
* [Issue 1789](/spyder-ide/spyder/issues/1789) - Getting warning "WARNING: Unexpected error discovering local network interfaces: 'SysOutput' object has no attribute 'flush"
* [Issue 1809](/spyder-ide/spyder/issues/1809) - Shortcut to get to file explorer
* [Issue 1812](/spyder-ide/spyder/issues/1812) - Erros when pressing Tab key in the Editor
* [Issue 1830](/spyder-ide/spyder/issues/1830) - Don't modify python default system encoding in the console
* [Issue 1832](/spyder-ide/spyder/issues/1832) - Select line via line numbers
* [Issue 1847](/spyder-ide/spyder/issues/1847) - Preferences panel don't appear
* [Issue 1849](/spyder-ide/spyder/issues/1849) - Support yaml files in editor
* [Issue 1859](/spyder-ide/spyder/issues/1859) - Latest rope breaks the Object Inspector
* [Issue 1874](/spyder-ide/spyder/issues/1874) - Wheel mouse scrolling not enabled in numberlinemarker or flag area
* [Issue 1877](/spyder-ide/spyder/issues/1877) - Cell higlighting and scrollbar
* [Issue 1878](/spyder-ide/spyder/issues/1878) - Cell highlighting on startup
* [Issue 1891](/spyder-ide/spyder/issues/1891) - Sorting Variable explorer gives a traceback
* [Issue 1892](/spyder-ide/spyder/issues/1892) - Spyder crashes because pyzmq is missing
* [Issue 1949](/spyder-ide/spyder/issues/1949) - Spyder 'support for graphics' should not require pylab
* [Issue 1953](/spyder-ide/spyder/issues/1953) - Please do not break API in minor releases
* [Issue 1958](/spyder-ide/spyder/issues/1958) - Disable Variable Explorer auto-refresh feature by default
* [Issue 1961](/spyder-ide/spyder/issues/1961) - opening bracket in editor or console: focus switches to internal console (which also display an error)
* [Issue 1970](/spyder-ide/spyder/issues/1970) - Connecting to an IPython kernel through ssh hangs if you have never connected to hostname before  
* [Issue 1973](/spyder-ide/spyder/issues/1973) - Pandas DataFrame in variable explorer can crash the app if it gets out of memory
* [Issue 1975](/spyder-ide/spyder/issues/1975) - Improve confusing "UMD has deleted" message
* [Issue 1978](/spyder-ide/spyder/issues/1978) - 'Edit' context menu in Variable Explorer should work in all columns
* [Issue 1979](/spyder-ide/spyder/issues/1979) - Spyder crashes or hangs when creating some pandas DataFrame's
* [Issue 1982](/spyder-ide/spyder/issues/1982) - Middle mouse button *CUTS* text in editor in linux
* [Issue 2004](/spyder-ide/spyder/issues/2004) - Open sys.stdin with the right encoding in the console for Python 2
* [Issue 2005](/spyder-ide/spyder/issues/2005) - Error when running files in folders with UTF-8 in path
* [Issue 2008](/spyder-ide/spyder/issues/2008) - Wrong path to favicon.ico
* [Issue 2015](/spyder-ide/spyder/issues/2015) - Printing large pandas DataFrame clears iPython terminal 
* [Issue 2033](/spyder-ide/spyder/issues/2033) - Link to new WinPython site
* [Issue 2042](/spyder-ide/spyder/issues/2042) - IPython console doens't work with Pygments 2.0rc1
* [Issue 2044](/spyder-ide/spyder/issues/2044) - Autocomplete in the editor appends the completed variable onto the preceding expression if there's a token in between


----


## Version 2.3.1

### New features since v2.3.0

* Variable Explorer
    * Support for Pandas DataFrame's and TimeSerie's types
    * Support for Numpy 3D arrays
    * Drag and drop works for all its supported file types (e.g. images, mat files, json files, etc)
* Editor
    * F9 runs the current line under the cursor if nothing is selected
    * Focus remains on it after evaluating cells and selections (an option was added to return to the old behavior)
* IPython console
    * Connect to external kernels through ssh
* Object Inspector
    * Add a tutorial for beginners
* Main Window
    * Improve style on Mac

### Bug fixes (since v2.3.1)

* [Issue 93](/spyder-ide/spyder/issues/93) - Variable explorer: allow array editor to deal with arrays with more than 2 dimensions
* [Issue 1160](/spyder-ide/spyder/issues/1160) - Variable Explorer: add support for pandas objects
* [Issue 1305](/spyder-ide/spyder/issues/1305) - mayavi plot hangs when IPython graphics backend is inline (default)
* [Issue 1319](/spyder-ide/spyder/issues/1319) - Spyder is not getting its taskbar icon right in Win 7/8
* [Issue 1445](/spyder-ide/spyder/issues/1445) - Linux style middle mouse button paste not executed in console
* [Issue 1530](/spyder-ide/spyder/issues/1530) - Wrong encoding for date in pylint widget
* [Issue 1590](/spyder-ide/spyder/issues/1590) - Add numpy matrices as a supported type to the Variable Explorer
* [Issue 1604](/spyder-ide/spyder/issues/1604) - spyder 2.2.5 freezes with netCDF4-python
* [Issue 1627](/spyder-ide/spyder/issues/1627) - Run selection (F9) changes focus to Python interpreter, but ex-Matlab users expect the focus to remain on the editor
* [Issue 1670](/spyder-ide/spyder/issues/1670) - Provide a "Run current line" feature
* [Issue 1690](/spyder-ide/spyder/issues/1690) - Feature request: connect to existing IPython kernel over ssh
* [Issue 1699](/spyder-ide/spyder/issues/1699) - Option to disable middle button paste
* [Issue 1783](/spyder-ide/spyder/issues/1783) - The new cell delimiter when converting a notebook to python file is # In[`*`]
* [Issue 1863](/spyder-ide/spyder/issues/1863) - Ctrl-C doesn't work in a *restarted* IPython console
* [Issue 1893](/spyder-ide/spyder/issues/1893) - Matplotlib plots do not display correctly in 2.3.0 (when running in dedicated python interpreter)


----


## Version 2.3.0

### New features since v2.2

* Python 3 support
* Editor
    * Use the Tab key to do code completions
    * Highlight cells, i.e. portions of a file delimited by separators of the form `# %%`
    * First-class support for Enaml files
    * Syntax highlighting for Julia files
    * Use Shift+Tab to show the signature corresponding to a function/method while it's been called
    * Do code completions using the tokens (or words) found in a file
    * Token-based completions work for any file type supported by the Editor
    * Add a new tooltip widget (borrowed from the IPython project) to better handle how to show function signatures
* IPython console
    * Assign the keyboard shortcut Ctrl+Shift+I to move to it
    * Open a console by default at startup
    * Give visual feedback when opening a console
    * Show kernel error messages in the client tab
* Object Inspector
    * Add an intro message to explain how to use it
    * New style based on the Bootswatch Cerulean theme
* Main Window
    * Reorganize several menus
* Under the hood
    * Improve startup time
    * Develop a new way to update configuration defaults (that doesn't involve resetting user settings)

### Bug fixes (since v2.2)

* [Issue 696](/spyder-ide/spyder/issues/696) - Use Tab to do code completion in the Editor
* [Issue 944](/spyder-ide/spyder/issues/944) - Add Python 3 support
* [Issue 1068](/spyder-ide/spyder/issues/1068) - Shortcut key to switch to IPython console
* [Issue 1082](/spyder-ide/spyder/issues/1082) - IPython console: multiprocessing print output goes to kernel not client
* [Issue 1152](/spyder-ide/spyder/issues/1152) - Use the Editor/Console fonts for the code completion widget
* [Issue 1243](/spyder-ide/spyder/issues/1243) - Bootstrap fails under Python 3.2
* [Issue 1356](/spyder-ide/spyder/issues/1356) - IPython ImportError by not using absolute_import
* [Issue 1374](/spyder-ide/spyder/issues/1374) - IPython 1.0dev is giving "ImportError: No module named kernelmanager"
* [Issue 1402](/spyder-ide/spyder/issues/1402) - Execute pyflakes, pep8, ... with the Python interpreter specified in Preferences>Console
* [Issue 1420](/spyder-ide/spyder/issues/1420) - Deactivate pager by default in the iPython console (because it's perceived as a freeze)
* [Issue 1424](/spyder-ide/spyder/issues/1424) - Object inspector is broken for external console
* [Issue 1429](/spyder-ide/spyder/issues/1429) - Windows installer for Python 3.3 doesn't finish correctly
* [Issue 1437](/spyder-ide/spyder/issues/1437) - Corrupted contents when saving non-unicode .py files with non-ASCII characters
* [Issue 1441](/spyder-ide/spyder/issues/1441) - Spyder has several problems to start on Windows because pywin32 is not installed
* [Issue 1465](/spyder-ide/spyder/issues/1465) - scientific_startup is defining print_function for Python 2.X interactive consoles
* [Issue 1466](/spyder-ide/spyder/issues/1466) - unicode_literals breaks PySide
* [Issue 1467](/spyder-ide/spyder/issues/1467) - pyflakes flags print "" on python2 systems
* [Issue 1471](/spyder-ide/spyder/issues/1471) - IPython is not enabled in 2.3 (because of mismatched IPython version)
* [Issue 1473](/spyder-ide/spyder/issues/1473) - IPython kernel can't be started, complaining that 'sys' doesn't have attribute 'argv'
* [Issue 1475](/spyder-ide/spyder/issues/1475) - Plotting from the Variable Explorer is not working for IPython consoles
* [Issue 1479](/spyder-ide/spyder/issues/1479) - Opening another file in a running Spyder from the terminal fails in Python 3
* [Issue 1496](/spyder-ide/spyder/issues/1496) - Ctrl+C don't interrupt computations in either the Console or IPython console
* [Issue 1513](/spyder-ide/spyder/issues/1513) - "Replace all" crashes (not always, but regularly)
* [Issue 1514](/spyder-ide/spyder/issues/1514) - Python 3 / Spyder 2.3 : impossible to run temporary script in current interpreter
* [Issue 1517](/spyder-ide/spyder/issues/1517) - Console/IPython console reappear each time Spyder starts
* [Issue 1519](/spyder-ide/spyder/issues/1519) - Old .spyder.ini is not copied to spyder.ini
* [Issue 1528](/spyder-ide/spyder/issues/1528) - Error while shutting down Spyder
* [Issue 1540](/spyder-ide/spyder/issues/1540) - Exception instead of dialog box
* [Issue 1542](/spyder-ide/spyder/issues/1542) - Braces/Parentheses/Brackets Highlighting is broken with v2.3.0dev6 on Windows/Python 3
* [Issue 1545](/spyder-ide/spyder/issues/1545) - Win32 "Spyder Documentation" fails to open
* [Issue 1556](/spyder-ide/spyder/issues/1556) - Show cells in the outline explorer
* [Issue 1562](/spyder-ide/spyder/issues/1562) - Make Windows installers create a desktop shortcut for Spyder
* [Issue 1567](/spyder-ide/spyder/issues/1567) - Accept newer versions of pyflakes
* [Issue 1618](/spyder-ide/spyder/issues/1618) - Please provide a way to not compile the documentation during the build process
* [Issue 1619](/spyder-ide/spyder/issues/1619) - Python3 invalid syntax in figureoptions.py
* [Issue 1623](/spyder-ide/spyder/issues/1623) - Mac app: Editor slow on mac after os update to mavericks
* [Issue 1628](/spyder-ide/spyder/issues/1628) - Profiler runs but doesn't show the results
* [Issue 1631](/spyder-ide/spyder/issues/1631) - Documentation problem with numpy.concatenate
* [Issue 1646](/spyder-ide/spyder/issues/1646) - Different numerical results from "runfile" and "execfile"
* [Issue 1649](/spyder-ide/spyder/issues/1649) - Variable Explorer does not show complex number variables
* [Issue 1653](/spyder-ide/spyder/issues/1653) - 2 popup windows during lauch
* [Issue 1664](/spyder-ide/spyder/issues/1664) - Window gone transparent after splash screen
* [Issue 1675](/spyder-ide/spyder/issues/1675) - Redifing any for numpy.any in the console
* [Issue 1692](/spyder-ide/spyder/issues/1692) - Minor problem with the new Tab completion functionality
* [Issue 1695](/spyder-ide/spyder/issues/1695) - Add "psutil" to the list of optional dependancies
* [Issue 1696](/spyder-ide/spyder/issues/1696) - Check marks in display > windows menu are unchecked by moving plugins
* [Issue 1697](/spyder-ide/spyder/issues/1697) - Variable explorer freezes spyder
* [Issue 1701](/spyder-ide/spyder/issues/1701) - pip install spyder does not work any longer (pip version >=1.5)
* [Issue 1715](/spyder-ide/spyder/issues/1715) - debian lintian4py check
* [Issue 1716](/spyder-ide/spyder/issues/1716) - Add new icon and scripts for python3 in Linux
* [Issue 1723](/spyder-ide/spyder/issues/1723) - .pyx Comment and syntax color error in editor
* [Issue 1731](/spyder-ide/spyder/issues/1731) - Support Julia files (.jl) in editor
* [Issue 1735](/spyder-ide/spyder/issues/1735) - Small correction in French translations
* [Issue 1745](/spyder-ide/spyder/issues/1745) - Fix over-aggressive code completion on dot
* [Issue 1746](/spyder-ide/spyder/issues/1746) - Errors when running empty cells
* [Issue 1752](/spyder-ide/spyder/issues/1752) - Unable to read Spyder Documentation. F1 key does not work
* [Issue 1753](/spyder-ide/spyder/issues/1753) - A fix for the behavior of spyderlib\utils\system.py on Windows
* [Issue 1763](/spyder-ide/spyder/issues/1763) - Editor with auto-closing bracket enabled : unabled to type "0" before ")"
* [Issue 1772](/spyder-ide/spyder/issues/1772) - Fix download links on the main page
* [Issue 1786](/spyder-ide/spyder/issues/1786) - problem of icon with spyder 2.3.0 beta4
* [Issue 1793](/spyder-ide/spyder/issues/1793) - Highlight current cell slows down the Editor on big files
* [Issue 1794](/spyder-ide/spyder/issues/1794) - Mouse pointer on vertical line
* [Issue 1819](/spyder-ide/spyder/issues/1819) - Quick layout change unsuccessful
* [Issue 1828](/spyder-ide/spyder/issues/1828) - QAction::eventFilter: Ambiguous shortcut overload: Ctrl+W
* [Issue 1829](/spyder-ide/spyder/issues/1829) - Keyboard shortcuts, Reset to default values errors
* [Issue 1836](/spyder-ide/spyder/issues/1836) - [CTRL]+F4 does not close tabs
* [Issue 1879](/spyder-ide/spyder/issues/1879) - Can't start bootstrap.py with pyqt
* [Issue 1881](/spyder-ide/spyder/issues/1881) - Bootstrap.py won't start with python3


----


## Version 2.2.5

### Bug fixes (since v2.2.4)

* [Issue 1322](/spyder-ide/spyder/issues/1322) - Problems with scientific_startup in other interpreters from the one Spyder is running on
* [Issue 1337](/spyder-ide/spyder/issues/1337) - Mac app - Update to Qt 4.8.4 for HDPI
* [Issue 1450](/spyder-ide/spyder/issues/1450) - IPython kernel cpu usage increases with time
* [Issue 1520](/spyder-ide/spyder/issues/1520) - LinuxColor for ipython plugin
* [Issue 1551](/spyder-ide/spyder/issues/1551) - /doc/installation.rst: update Arch Linux package link
* [Issue 1560](/spyder-ide/spyder/issues/1560) - spyder 2.2.3 incompatible with pylint 0.25.1 on Windows
* [Issue 1564](/spyder-ide/spyder/issues/1564) - Fix several Editor cell problems
* [Issue 1578](/spyder-ide/spyder/issues/1578) - Typo in your 'About Spyder...' dialog.
* [Issue 1581](/spyder-ide/spyder/issues/1581) - Cannot launch Spyder 2.2.4 installed from DMG on Mac OS X.
* [Issue 1589](/spyder-ide/spyder/issues/1589) - Mention what types of objects our Variable Explorer support in our docs
* [Issue 1595](/spyder-ide/spyder/issues/1595) - Fail to start an ipython console when variable explorer autorefresh is turned off in Preferences
* [Issue 1596](/spyder-ide/spyder/issues/1596) - Spelling mistake in dialog ('loose' --> 'lose')

### Other Changes (since v2.2.4)

* Update our Mac application to the latest versions of Python, Qt and PyQt (now it's based in Homebrew).
* Several important compatibility fixes for PySide.
* Improve our support for IPython 1.0+.

----

## Version 2.2.4

### Bug fixes (since v2.2.3)

* [Issue 347](/spyder-ide/spyder/issues/347) - Matplotlib hangs on Mac if using PySide
* [Issue 1265](/spyder-ide/spyder/issues/1265) - Create a Debug menu to easily show how to set breakpoints
* [Issue 1489](/spyder-ide/spyder/issues/1489) - Project Explorer does not load all projects in workspace.
* [Issue 1516](/spyder-ide/spyder/issues/1516) - Make Spyder compatible with both IPython 0.13 and 1.0
* [Issue 1531](/spyder-ide/spyder/issues/1531) - Pyflakes version check is looking for 0.5.0 only
* [Issue 1539](/spyder-ide/spyder/issues/1539) - /tmp/spyder is owned by the first user on the server to launch spyder

### Other Changes (since v2.2.3)

* Make Spyder compatible with SymPy 0.7.3+
* Add shortcuts to the tooltips of all toolbars
* Make IPython Console work better if Matplotlib is not installed

----

## Version 2.2.3

### Bug fixes (since v2.2.2)

* [Issue 634](/spyder-ide/spyder/issues/634) - Debugging: Lingering break points
* [Issue 639](/spyder-ide/spyder/issues/639) - Project Explorer: horizontal size issue (added an optional horizontal scrollbar. This option may be enabled/disabled in the widget context menu)
* [Issue 749](/spyder-ide/spyder/issues/749) - Outline Explorer: Duplicate entries
* [Issue 852](/spyder-ide/spyder/issues/852) - Implement matlab-like cell features
* [Issue 1388](/spyder-ide/spyder/issues/1388) - Add an "About Spyder dependencies" dialog box
* [Issue 1438](/spyder-ide/spyder/issues/1438) - "runfile" doesn't work correctly if unicode_literals has been imported (replaced backslashes by slashes in paths)
* [Issue 1515](/spyder-ide/spyder/issues/1515) - Add an option to use the same interpreter Spyder is running on as "Python executable" for external consoles
* [Issue 1522](/spyder-ide/spyder/issues/1522) - licenses of the images (especially the .png)
* [Issue 1526](/spyder-ide/spyder/issues/1526) - Build script (setup.py) includes the wrong version of pyflakes/rope in Windows installer
* [Issue 1527](/spyder-ide/spyder/issues/1527) - please include the LICENSE file in the source package

### Other Changes (since v2.2.2)

* New "Run selection" (F9), "Run cell" (Ctrl+Enter) and "Run cell and advance" (Shift+Enter) actions in "Run" menu entry, as a replacement to the old "Run selection or block" and "Run block and advance" actions.
* Added "Optional Dependencies" dialog box in "?" menu.
* Editor: added Monokai and Zenburn syntax coloring schemes.
* Keyboard shortcuts: removing deprecated shortcuts at startup. Otherwise, when renaming the name of a registered shortcut (in the code), the old shortcut will stay in Spyder configuration file and opening the Preferences dialog will show a shortcut conflict dialog box. In other words, shortcuts were added to configuration file when registered but never removed if they were removed from the registered shortcuts in the code (or if their context or name was renamed).
* External console tabs: fixed history browsing with Ctrl+Tab and added Shift+Ctrl+Tab support.
* Preferences>Console>Advanced: new option to switch between the default Python executable (i.e. the one used to run Spyder itself) and the custom Python executable that the user may choose freely. This change avoid side-effects when switching from a Python distribution to another on the same OS (with the same Spyder configuration file): many users do not change the Python executable and because of the way it was written in externalconsole.py, changing from a distribution of Python to another with the same Spyder config file could lead to an unexpected configuration (Spyder is executed with the new interpreter but scripts inside Spyder are executed with the old interpreter).
* Run Icons: removed deprecated images, updated other images to the new design
* setup.py/Windows installers: now building CHM documentation for Windows
* SPYDER_DEBUG environment variable now supports 3 levels of debug mode:
    * SPYDER_DEBUG=0 or False: debug mode is off
    * SPYDER_DEBUG=1 or True: debug level 1 is on (internal console is disconnected)
    * SPYDER_DEBUG=2: debug level 2 is on (+ logging coms with external Python processes)
    * SPYDER_DEBUG=3: debug level 3 is on (+ enabling -v option in external Python processes and debugging editor)

----

## Version 2.2.2

### Bug fixes (since v2.2.1)

* [Issue 1497](/spyder-ide/spyder/issues/1497) - Spyder 2.2.1 does not work with Python < 2.7
* [Issue 1498](/spyder-ide/spyder/issues/1498) - TypeError thrown by IPython Console when the pager is off
* [Issue 1499](/spyder-ide/spyder/issues/1499) - Console (Terminal) throws NotImplementedError for Home/End keys
* [Issue 1509](/spyder-ide/spyder/issues/1509) - Add support for javascript syntax highlighting
* [Issue 1510](/spyder-ide/spyder/issues/1510) - Problems with zooming in/out

### Other Changes (since v2.2.1)

* Add new icons to the Run, Debug and Main toolbars
* Update Pylint plugin to work with pylint 1.0
* Add Ctrl/Cmd+[+,-] to zoom in/out in the Editor
* Disable Crtl+MouseWheel to zoom in/out in Mac (See Issue 1509)

----

## Version 2.2.1

### Bug fixes (since v2.2.0)

* [Issue 1231](/spyder-ide/spyder/issues/1231) - Some strange messages are printed in the terminal when Spyder is running
* [Issue 1318](/spyder-ide/spyder/issues/1318) - Mac app - Unable to use the keyboard when completion widget is displayed and the app loses focus
* [Issue 1331](/spyder-ide/spyder/issues/1331) - Git Bash: Spyder's script has wrong shebang
* [Issue 1333](/spyder-ide/spyder/issues/1333) - Spyder is unable to detect git if installed with msysgit (Microsoft Windows PC's)
* [Issue 1370](/spyder-ide/spyder/issues/1370) - Unit tests exceptions in IPython are displayed in its kernel tab
* [Issue 1395](/spyder-ide/spyder/issues/1395) - Mac App - Importing matplotlib fails on Snow Leopard due to incompatible version of libpng
* [Issue 1399](/spyder-ide/spyder/issues/1399) - Recommend to use pip instead of easy_install
* [Issue 1426](/spyder-ide/spyder/issues/1426) - Background colour of Object Inspector (docstring) in Rich Text mode is same as the window's
* [Issue 1439](/spyder-ide/spyder/issues/1439) - Update pil_patch to be compatible with Pillow
* [Issue 1449](/spyder-ide/spyder/issues/1449) - Spyder --light is not functioning
* [Issue 1470](/spyder-ide/spyder/issues/1470) - Preferences size is not saved when using PySide
* [Issue 1472](/spyder-ide/spyder/issues/1472) - matplotlib plot's docstring is not rendered correctly in the Object Inspector

### Other Changes (since v2.2.0)

* All scientific libraries in our Mac application were updated to their latest releases.
* The _Run Settings_ dialog has now its own icon. Before it was the same as the _Preferences_ pane one.
* Update and improve our _Installation_ instructions for all platforms.
* Add support for Google TODO comments: "TODO(username@domain.com): blabla"

----

## Version 2.2.0

### New features since v2.1

* Better integration with IPython.
    * A dedicated preferences page from which you can set its most important options
    * An easy way to manage IPython kernels inside Spyder (i.e. interrupts and restarts).
    * Each console can be configured separately (which is not possible in IPython-qtconsole)
    * Each console is now connected to the Object Inspector and the History log.
    * Learn how to use IPython reading its documentation on the Object Inspector.
    * Find text in the console and pager using our Find Widget.
* A new MacOS X Application
    * We now provide a DMG for simple drag and drop installation.
    * The App comes with its own interpreter, which has the main Python scientific libraries preinstalled: Numpy, SciPy, Matplotlib, IPython, Pandas, Sympy, Scikit-learn and Scikit-image.
* A much improved debugging experience
    * A new debugger toolbar, quite similar in spirit to the one present in Matlab. It works with both Python and IPython consoles.
    * A new breakpoints widget, which lists all active breakpoints set in  open or closed files.
    * Breakpoints are updated in the Python and IPython consoles after being added or removed from the Editor.
* Several Editor improvements
    * Faster and more accurate code completions for the most important scientific packages
    * Zoom in and out with Ctrl + the mouse wheel
    * A new dark theme
    * Automatic insertion of colons
    * Automatic insertion of quotes
    * New syntax highlighters for Matlab, batch, ini, NSIS and IDL files.
* A better looking and faster Object Inspector
    * Several improvements to its style.
    * It can now show mathematical equations written in Latex, using the MathJax Sphinx plugin.
    * Rich text docs are now rendered in a thread to avoid UI lookup.
* Single instance mode
    * Users can now open Python scripts from their file explorer on the currently available instance.
    * Linux users can also open their files from the terminal.
* Spanish translation of the interface

### Bug fixes (since v2.1)

* [Issue 318](/spyder-ide/spyder/issues/318) - Create a widget to list all breakpoints
* [Issue 349](/spyder-ide/spyder/issues/349) - Add "Run selection or current block" action to Editor's context menu
* [Issue 448](/spyder-ide/spyder/issues/448) - Editor: disable code-related features inside comments (code completion, auto-indentation, ...)
* [Issue 466](/spyder-ide/spyder/issues/466) - Can't use Spyder to open python scripts (.py files) from the terminal or the file explorer
* [Issue 554](/spyder-ide/spyder/issues/554) - Improved debugger integration
* [Issue 609](/spyder-ide/spyder/issues/609) - Debugging: Unsetting a breakpoint in the editor isn't reflected until you restart debugging entirely
* [Issue 650](/spyder-ide/spyder/issues/650) - After deleting a directory set as working directory and changing to a new working directory the script won't run
* [Issue 687](/spyder-ide/spyder/issues/687) - Indentation error when trying to "run selection" on simple indented code
* [Issue 697](/spyder-ide/spyder/issues/697) - Create a DMG package for Spyder
* [Issue 764](/spyder-ide/spyder/issues/764) - Jump to the next result when pressing Enter in search field
* [Issue 836](/spyder-ide/spyder/issues/836) - Spyder is sometimes not detecting file changes from external editors
* [Issue 849](/spyder-ide/spyder/issues/849) - Breakpoints are ignored sometimes
* [Issue 853](/spyder-ide/spyder/issues/853) - Problems with code completion after adding submodules to ROPE_PREFS/extension_modules
* [Issue 865](/spyder-ide/spyder/issues/865) - Run selection (F9) in IPython console 0.11+: problem with indented blank lines
* [Issue 940](/spyder-ide/spyder/issues/940) - open_in_spyder not defined
* [Issue 955](/spyder-ide/spyder/issues/955) - Breakpoints in debugger do not move correctly when editing code
* [Issue 971](/spyder-ide/spyder/issues/971) - Add "Open with Spyder" entry to Windows File Explorer's context menu
* [Issue 994](/spyder-ide/spyder/issues/994) - mathjax does not get installed properly
* [Issue 997](/spyder-ide/spyder/issues/997) - Some docstrings are getting truncated in the object inspector
* [Issue 1008](/spyder-ide/spyder/issues/1008) - Fail on context menu call in project explorer when project files are inside symlinked dir
* [Issue 1018](/spyder-ide/spyder/issues/1018) - Menu locations, "Run Configurations" &  "Preferences"
* [Issue 1026](/spyder-ide/spyder/issues/1026) - Decide the best strategy to comment selections on the Editor
* [Issue 1032](/spyder-ide/spyder/issues/1032) - Running a script from editor does not send runfile() correctly to IPython Qt plugin
* [Issue 1050](/spyder-ide/spyder/issues/1050) - First implementation of the "IPython Console" plugin (single instance version)
* [Issue 1051](/spyder-ide/spyder/issues/1051) - New IPython Console (Spyder 2.2+): add support for the %edit magic command
* [Issue 1054](/spyder-ide/spyder/issues/1054) - New IPython Console (Spyder 2.2+): update variable explorer after new prompt
* [Issue 1055](/spyder-ide/spyder/issues/1055) - New IPython Console (Spyder 2.2+): add support for history management
* [Issue 1056](/spyder-ide/spyder/issues/1056) - New IPython Console (Spyder 2.2+): add an option to customize In/Out prompts
* [Issue 1057](/spyder-ide/spyder/issues/1057) - New IPython Console (Spyder 2.2+): Add our FindReplace widget to every console
* [Issue 1058](/spyder-ide/spyder/issues/1058) - New IPython Console (Spyder 2.2+): Add Ctrl+I keyboard shortcut to send an object the Object Inspector
* [Issue 1059](/spyder-ide/spyder/issues/1059) - New IPython Console (Spyder 2.2+): drop support for IPython in external console
* [Issue 1061](/spyder-ide/spyder/issues/1061) - New IPython Console (Spyder 2.2+): add support for "Find in files" plugin
* [Issue 1062](/spyder-ide/spyder/issues/1062) - New IPython Console (Spyder 2.2+): add a dedicated section in documentation
* [Issue 1064](/spyder-ide/spyder/issues/1064) - Editor performance issue since revision d98df4092e16
* [Issue 1069](/spyder-ide/spyder/issues/1069) - Focus goes to kernel not client with pdb in IPython client
* [Issue 1078](/spyder-ide/spyder/issues/1078) - IPython Console: Cannot interrupt started processes
* [Issue 1079](/spyder-ide/spyder/issues/1079) - Can't input Unicode in Internal Console
* [Issue 1081](/spyder-ide/spyder/issues/1081) - ipython-qtconsole not listed as optional dependency in Ubuntu
* [Issue 1083](/spyder-ide/spyder/issues/1083) - Make Ipython qtconsole widget more intuitive
* [Issue 1085](/spyder-ide/spyder/issues/1085) - IPython console: sometimes files are executed in wrong IPython
* [Issue 1094](/spyder-ide/spyder/issues/1094) - Error message when trying to save a file
* [Issue 1095](/spyder-ide/spyder/issues/1095) - Preferences Dialog doesn't remember size
* [Issue 1101](/spyder-ide/spyder/issues/1101) - Interrupt (Ctrl+C) in the console does not work in Spyder on Mac Os X
* [Issue 1106](/spyder-ide/spyder/issues/1106) - Spyder console crashes when trying to type in console after running script
* [Issue 1112](/spyder-ide/spyder/issues/1112) - Opening a file from the linux command line
* [Issue 1128](/spyder-ide/spyder/issues/1128) - please remove pyflakes and rope from the .zip files
* [Issue 1136](/spyder-ide/spyder/issues/1136) - IPython console: cannot connect to external kernels
* [Issue 1138](/spyder-ide/spyder/issues/1138) - Rich text in object inspector mishandles some scipy docstrings
* [Issue 1163](/spyder-ide/spyder/issues/1163) - Improve the spyder.desktop file fo easier integration into Linux
* [Issue 1169](/spyder-ide/spyder/issues/1169) - Saving variables does not retain uppercase letters of variable names
* [Issue 1179](/spyder-ide/spyder/issues/1179) - Pylint "go to line" does not work with the additional dot in filename
* [Issue 1186](/spyder-ide/spyder/issues/1186) - scipy.weave doesn't work in the Mac app
* [Issue 1191](/spyder-ide/spyder/issues/1191) - Inconsistent behaviour of the Editor on code completion and object introspection
* [Issue 1199](/spyder-ide/spyder/issues/1199) - spyderlib/utils/windows.py has incorrect encoding
* [Issue 1201](/spyder-ide/spyder/issues/1201) - Let the user set the default filter when opening file
* [Issue 1210](/spyder-ide/spyder/issues/1210) - Enhancement: Create sphinx rich text docstrings in QThread
* [Issue 1226](/spyder-ide/spyder/issues/1226) - MacOS X App - Can't import libraries from other Python interpreters
* [Issue 1227](/spyder-ide/spyder/issues/1227) - Auto inserted colon causes pylint error
* [Issue 1229](/spyder-ide/spyder/issues/1229) - Which version of ipython is needed for Spyder 2.2.0?
* [Issue 1230](/spyder-ide/spyder/issues/1230) - Better handle for mathjax and jquery embeded libraries on linux systems
* [Issue 1232](/spyder-ide/spyder/issues/1232) - Cmd-Space is not showing code-completion options
* [Issue 1233](/spyder-ide/spyder/issues/1233) - ERROR and WARNING when compiling the documentation
* [Issue 1234](/spyder-ide/spyder/issues/1234) - Edit .enaml files as text file
* [Issue 1236](/spyder-ide/spyder/issues/1236) - Fix Qt Network Access warning messages that appear on the terminal
* [Issue 1241](/spyder-ide/spyder/issues/1241) - 'Remove block comment' is not working
* [Issue 1242](/spyder-ide/spyder/issues/1242) - Can't start spyder2.2 on Win 7, crashes upon saving .spyder.ini
* [Issue 1249](/spyder-ide/spyder/issues/1249) - "Run block" and "Run File" are not working for external IPython kernels
* [Issue 1250](/spyder-ide/spyder/issues/1250) - Spyder crashes on launch if the project explorer is used
* [Issue 1252](/spyder-ide/spyder/issues/1252) - Expansion of nodes on tree view undoes itself
* [Issue 1253](/spyder-ide/spyder/issues/1253) - Spyder is not detecting the presence of iPython 0.13.1rc2 nor IPython 1.0dev
* [Issue 1258](/spyder-ide/spyder/issues/1258) - Focusing the "Replace with:" Text Box causes the editor to jump to the next instance of the item that's in the find box
* [Issue 1261](/spyder-ide/spyder/issues/1261) - IPython kernel/clients: error when closing an IPython console
* [Issue 1266](/spyder-ide/spyder/issues/1266) - Let the user eliminate breakpoints from the "Breakpoints widget"
* [Issue 1269](/spyder-ide/spyder/issues/1269) - Dataloss when Spyder gets confused about which file goes with which editor tab
* [Issue 1271](/spyder-ide/spyder/issues/1271) - Find and replace by empty string
* [Issue 1272](/spyder-ide/spyder/issues/1272) - Fix code completion speed issues on the Editor
* [Issue 1275](/spyder-ide/spyder/issues/1275) - Spyderlib fails to start new IPython consoles, raises socket exception
* [Issue 1277](/spyder-ide/spyder/issues/1277) - Enthought Python Distribution and Spyder DMG are not working well on Mac OS X
* [Issue 1281](/spyder-ide/spyder/issues/1281) - Mac App - Spyder swallows AssertionErrors while executing a file
* [Issue 1285](/spyder-ide/spyder/issues/1285) - Object Inspector Crashes when Reloading Page
* [Issue 1286](/spyder-ide/spyder/issues/1286) - Broken links in Help
* [Issue 1287](/spyder-ide/spyder/issues/1287) - Saving file under different file name in split-window mode lets non-focused window jump to first file
* [Issue 1288](/spyder-ide/spyder/issues/1288) - Some rope_patch improvements
* [Issue 1296](/spyder-ide/spyder/issues/1296) - Clickable tracebacks in console are not working in PySide
* [Issue 1298](/spyder-ide/spyder/issues/1298) - Mac App - matplotlib is not detecting ffmpeg to create animations
* [Issue 1299](/spyder-ide/spyder/issues/1299) - pylint keeps opening same file at startup
* [Issue 1309](/spyder-ide/spyder/issues/1309) - Clicking on filename in structure widget sets the cursor at the beginning of the file
* [Issue 1314](/spyder-ide/spyder/issues/1314) - QPainter warnings when moving/undocking widgets in main window
* [Issue 1315](/spyder-ide/spyder/issues/1315) - Project not closing files associated with after closing it
* [Issue 1325](/spyder-ide/spyder/issues/1325) - Spyder cannot be re-opened on Windows if parent console is closed
* [Issue 1327](/spyder-ide/spyder/issues/1327) - Allow global options for Run Configuration
* [Issue 1344](/spyder-ide/spyder/issues/1344) - Mac App - Spyder crashed and can't be open again
* [Issue 1345](/spyder-ide/spyder/issues/1345) - Code Review Request: Update breakpoints during pdb sessions
* [Issue 1347](/spyder-ide/spyder/issues/1347) - The spyder.desktop has an wrong line
* [Issue 1353](/spyder-ide/spyder/issues/1353) - Error messages in internal console when rope is not installed
* [Issue 1363](/spyder-ide/spyder/issues/1363) - 2.2rc installation takes a long time because of sphinx dependency
* [Issue 1364](/spyder-ide/spyder/issues/1364) - No spyder.ico after installation on Windows
* [Issue 1369](/spyder-ide/spyder/issues/1369) - Using the subprocess.check_output function breaks compatibility with Python 2.5 and 2.6
* [Issue 1371](/spyder-ide/spyder/issues/1371) - Crash when adding text to multiline comment is CSS
* [Issue 1372](/spyder-ide/spyder/issues/1372) - SphinxThread might return AttributeError


----


## Version 2.1.13.1

### Bug fixes (since v2.1.13)

* Spyder startup: fixed PyQt minimum version requirement test (the old poor comparison algorithm was considering that v4.10 was older than v4.4...) (See [Issue 1291](/spyder-ide/spyder/issues/1291))
* Console: Matplotlib was always imported even when the Matplotlib's Patch option was not available (i.e. the Matplotlib installed version was not compatible with the patch). As a consequence, even when disabling every console advanced option in preferences, the preloaded module list was huge
* Editor:
    * When closing Spyder with unsaved modified files, Spyder was asking confirmation as many times as there were editor windows. Only one confirmation is necessary because, with current editor design, all editor windows are synced.
    * When creating two new files, saving one of them will lead to temporarily mask the leading '`*`' indicating the fact that the other untitled file was not already saved. This is simply a display issue: internally, it is clear that the file is in a non-saved state and Spyder will ask for it to be saved when trying to close the file
    * Multiple windows: when saving a new untitled file, other editor windows were getting confused on file list order -- eventually leading to data loss
    * Open file dialog: default file type filter now matches the current file (See [Issue 1201](/spyder-ide/spyder/issues/1201))
* Fixed "PyQt Reference Guide" link

### Other changes (since v2.1.13)

* Editor: Ctrl+MouseWheel is now zooming in/out the editor text size (see [Issue 1270](/spyder-ide/spyder/issues/1270))
* About dialog box: changed the "This project is part of Python(x,y)" part to more general words (which are also closer to the initial meaning of this sentence) including a citation of WinPython


----


## Version 2.1.13

### Bug fixes (since v2.1.12)

* Fixed [Issue 1158](/spyder-ide/spyder/issues/1158): "pip install spyder" fails on non-Windows platforms due to a bug in pip installation process (missing spyderlib_win_postinstall.py script)
* File Explorer/Windows/Fixed "remove tree" feature: added an error handler in shutil.rmtree to be able to remove a non-empty folder with shutil.rmtree is not working on Windows when it contains read-only files
* (See [Issue 1106](/spyder-ide/spyder/issues/1106)) Fixed "error: unpack requires a string argument of length 8" related to socket communication between Spyder and the remote Python process
* Editor:
    * After splitting horizontally or vertically the editor window, filenames were not synchronized when saving a file as another name (see [Issue 1120](/spyder-ide/spyder/issues/1120))
    * Fixed error when trying to "Save as..." a file with extension to a file without any extension (see [Issue 1183](/spyder-ide/spyder/issues/1183))
    * pep8 code analysis: a new line character was abusively added by Spyder to source code before analyzing it because it's necessary for pyflakes but it's not for pep8! (see [Issue 1123](/spyder-ide/spyder/issues/1123))
    * Fixed UnboundLocalError when clicking on "Search/Replace" button if both search pattern and replace pattern fields are empty (see [Issue 1188](/spyder-ide/spyder/issues/1188))
* Pylint plugin/tree widget: "go to line" was not working when filename contained additionnal dots (see [Issue 1179](/spyder-ide/spyder/issues/1179))
* Fixed critical bug when an invalid/unsupported version of pyflakes is installed (see [Issue 1181](/spyder-ide/spyder/issues/1181))
* Editor/block comments: fixed remaining PyQt API v2 compatibility issues (see [Issue 905](/spyder-ide/spyder/issues/905))
* Variable explorer: more flexible name fixing algorithm (even if it's not a good practice to use reference names with upper case letters, we do not remove them anymore) -- See [Issue 1169](/spyder-ide/spyder/issues/1169)

### Other changes (since v2.1.12)

* Spyder about dialog box: added Python build architecture (32 or 64 bits)
* Find in files: fixed default 'exclude pattern' which was accidently excluding all files starting with 'build' instead of simply excluding 'build' folders as intended
* For the sake of consistency, now using single-clicks for activating entries of all tree widgets in Spyder ("Find in files" and "Pylint" are now consistent with the "Outline" explorer) -- See [Issue 1180](/spyder-ide/spyder/issues/1180)


----


## Version 2.1.12

### Bug fixes (since v2.1.11)

* Spyder settings: sometimes (virus protection?) the .ini file can't be written, and removing the .ini file before writing seems to help, as suggested [here](https://groups.google.com/forum/#!msg/spyderlib/a_P9JBJEZeE/gOK_Pr2WbE8J) (see [Issue 1086](/spyder-ide/spyder/issues/1086))
* Fixed Home/End key behaviour inconsistency on MacOS X (See [Issue 495](/spyder-ide/spyder/issues/495))
* Internal console: new option "Pop up internal console when errors were intercepted" -- default: False, which avoids loosing focus when a traceback is shown in the internal console... but features may also fail silently! (bugs could stay hidden a while before being taken care of) -- See [Issue 1016](/spyder-ide/spyder/issues/1016)
* Fixed "TypeError: file_saved(long,long).emit(): argument 1 has unexpected type 'long'" error occuring on some Linux 32-bit platforms -- See [Issue 1094](/spyder-ide/spyder/issues/1094)
* Console: find/replace widget "Search next/previous occurence" feature was broken

### Other changes (since v2.1.11)

* Portable version of Spyder (inside WinPython):
    * Spyder '?' menu: added documentation detection (.chm, .pdf) in sys.prefix\Doc (Windows-only)
    * Project explorer:
        * Handling errors when opening a workspace which has been moved
        * Workspace is now configured with relative paths, so it can be moved from a location to another and still be opened in Spyder
* Windows: moved the functions hiding parent console to spyderlib/utils/windows.py


----


### Version 2.1.11

### Bug fixes (since v2.1.10)

* Critical bugs:
    * Editor ([Issue 960](/spyder-ide/spyder/issues/960)): cannot open/save files from GUI (QFileDialog issue with PyQt4 v4.6)
* General:
    * Spyder menu bar: fixed menu ordering issue with Ubuntu/Unity
    * All console widgets: Shell widget: fixed "Clear terminal" (Ctrl+L) shortcut
* Console:
    * Cleaned up widget interactions after Python script execution (before this changeset, it was possible to send data to console, which not only was not needed but was generating disturbing errors in the internal console...)
* Editor:
    * If user accept to fix "mixed end-of-line characters", when opening file, the current editor was set as "modified" (the tab title had a `*` at the end) instead of the newly created editor
    * "occurrence highlighting" was highlighting previous word even if there was a whitespace between cursor and this word
    * Code analysis thread manager: handling errors while executing threads
    * "Replace all" was not regrouping changes into a single undo/redo step
    * "Find/Replace": replacements were not done for case unsensitive searches
    * Position of the 79-chars edge line is now more accurate on Linux, the older processed position was inaccurate with some font size of the classic "DejaVu Sans Mono" monospace font
* IPython:
    * Version detection was broken so Preferences...Console...External Modules was incorreclty hiding the command line options line edit
    * Because the detection was not working correctly, it was not possible to start an IPython kernel with the just released IPython 0.13
* Project explorer was sometimes producing AttributeError when loading because of the workspace was not defined at the beginning of the class constructor
* pyflakes code analysis function:
    * Handling files with invalid \x or null chars
    * This fixes a part of [Issue 1016](/spyder-ide/spyder/issues/1016) by handling the following pyflakes bugs:
      * http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674796
      * http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674797

### Other changes (since v2.1.10)

* Installer for Windows (bdist_wininst/bdist_msi):
    * added Start Menu shortcuts
    * added 'pyflakes' and 'rope' (if available in the repository) to the package list (this is not conventional but Spyder really need those tools and there is not decent package manager on Windows platforms, so...)
    * This change will make the Spyder building process simpler for Windows as the Python(x,y) won't be needed anymore to provide Start Menu shortcuts or to install 'rope' and 'pyflakes' at the same time. Now, there is no significative difference between the standard installers built with distutils (bdist_wininst or bdist_msi options) and the Python(x,y) plugin, except for the "package upgrade" ability (uninstall previous version) which is still not (and won't be) supported by distutils.


----


## Version 2.1.10

### Bug fixes (since v2.1.9)

* Critical bugs:
    * Spyder crashed at startup/TypeError: `_isdir()` takes exactly 1 argument (0 given). Affects only Windows platforms with Python 3.2.2+ or 2.7.3+)
    * Spyder was freezing when working with netCDF4 objects in the interactive console
    * Console: h5py was systematically imported to avoid crashes with the HDF5 plugin (Variable Explorer's I/O plugin). These ugly workarounds introduced with revision 3affc82ce081 were removed in this changeset to avoid side effects like DLL version conflict on Windows platforms. The main risk of this change is to break the HDF5 plugin on some configurations. But this is the best compromise.
* General:
    * Fixed regression: when no Qt library is installed (PyQt/PySide), warning the user with a Tkinter dialog box (if possible)
    * Fixed Preferences Dialog flickering issue introduced with revision a4e1565e93c5
    * Run configuration dialog: fixed Tab focus order behavior
    * Fixed "Run > Configure..." and "PYTHONPATH management" entry locations on MacOSX
    * Updated bootstrap script and Qt library selection logic to accomodate launch of Spyder using PySide while PyQt is also installed ([Issue 1013](/spyder-ide/spyder/issues/1013), see [Issue 975](/spyder-ide/spyder/issues/975) for additional background).
    * Fixed several encoding problems preventing Spyder from launching when the user's home directory contains non-ASCII characters ([Issue 812](/spyder-ide/spyder/issues/812), [Issue 1027](/spyder-ide/spyder/issues/2017)).
    * Debugging: [Issue 684](/spyder-ide/spyder/issues/684): Debug with winpdb will now use the command line options and working directory specified in the General Setting section of the Run Configuration dialog
* Console:
    * Changed "Clear shell" shortcut to "Ctrl+L" to avoid conflict with the Windows Task Manager shortcut on Windows platforms
    * Preferences/Advanced options: added option to start an IPython kernel at startup
* Editor:
    * When multiple files were open, close-clicking 1 file was closing 2 files on 64-bits OS
    * Conditional breakpoint could not be changed to regular breakpoint
    * Outline Explorer: removed obsolete decorated methods icon (a decorated method is now shown exactly as a regular method)
    * Top-left corner menu (file list): fixed common prefix removal feature
    * "Outline" item selection opened in incorrect split panel due to a lost signal when focus changed from an editor to another
    * when splitting window after changing a shortcut, old shortcut was still active
* Internal console/fixed an old regression: re-added help(), raw_input() support
* Profiler: tree was sometimes empty + fixed error when file path contained "&"
* File/Project explorer: fixed [by shchelokovskyy] Git commit/browse support
* Find in files: fixed crash due to a bug in the common prefix finder function

### Other changes (since v2.1.9)

* Checked Spyder's `rope` patch compatibility with rope v0.9.4
* IPython plugin (experimental):
    * added support for "Execute in current interpreter"
    * added support for "Execute selection or block (F9)"
    * imports from local directory did not work
    * when a new kernel is started in Console, tabifying the frontend to the Console (for the first created frontend) and the next frontends to the previously created frontend
    * clients (frontends) may now really be closed (see context menu). The associated kernel and related clients may be closed as well (a message box dialog ask the user about this)
    * added support for the "Object Inspector to/from IPython kernel" link
    * improved reliability of the "Editor to/from IPython kernel" link
    * fixed focus management issue (link with variable explorer and object inspector)


----


## Version 2.1.9

### Bug fixes (since v2.1.8)

* Run configuration/bugfix: command line options were not properly parsed
* Preferences dialog was not showing up with PySide installed *and* without PyQt4
* Editor:
    * Closing additional editor window produced traceback and primary editor breakdown
    * File/Open: embedded editor popped up even if there is one in a separate window
    * Selecting a part of a word raises an IndexError exception
    * Revert option was prompting for user input even on an unmodified buffer
    * Added missing .f77 file extensions for Fortran files filter
    * Occurence highlighting was not working when cursor was at the left side of a word and if the next character was ':', ',' or '(' (or any other character not matching the "word regexp")
* Console:
    * Console was unusable (endless tracebacks) when monitor was disabled
    * File drag'n drop was not working (should execute dropped file)
* (Experimental) IPython plugin:
    * Fixed compatibility issues with PyQt4 and IPython 0.12
    * Fixed multiple instances issue (it was not possible to open more than one IPython frontend) and other issues
    * IPython kernel connections were unpredictable ([Issue 977](/spyder-ide/spyder/issues/977))
* Dictionary editor (Variable explorer): fixed UnboundLocalError when context menu is called on an empty table
* Object inspector failed to show an error message due to unicode error
* Project Explorer:
    * "Show all files" option was broken after restarting Spyder
    * It was impossible to create a project from an existing directory located outside the workspace


----


## Version 2.1.8

### Bug fixes (since v2.1.7)

* Editor/Source code toolbar:
    * "Show task list" and "Go to the next task" actions: the "Show TODO/FIXME/XXX/HINT/TIP comments list" button was not working
    * "Show warning/error list" and "Go to the next warning/error" actions: the "Show code analysis warnings/errors" button was not working


----


## Version 2.1.7

### Bug fixes (since v2.1.6)

* Main window:
    * Detached dockwidgets were not painted after restarting Spyder ([Issue 880](/spyder-ide/spyder/issues/880))
* Console:
    * Enhanced Python interpreter: %clear command was broken since v2.1.5
* Object inspector's rich text mode: fixed unexpected indent error
* IPython plugin: fixed compatibility issue with latest v0.12dev (thanks to Boris Gorelik)

### Other changes (since v2.1.6)

* Variable explorer/Array editor: added support for masked arrays
* Showing Spyder's internal console automatically when there is a traceback
* Do not crash when a 3rd party plugin failed to import
* Editor:
    * Automatic insertion of single, double and triple quotes
    * Automatically colons insertion when pressing Enter after 'if', 'def', etc
    * Don't trigger code completion on comments if text ends with a dot
    * Added keyboard shortcut (Ctrl+Shift+Escape) to clear the console
    * Added keyboard shortcut (Ctrl+P) to print current file (thanks to fheday at gmail dot com for the contribution)
    * Code introspection features (code completion, calltips, go-to-definition) are now working even if script has syntax errors


----


## Version 2.1.6

### Bug fixes (since v2.1.5)

* Critical bug on certain Windows platforms (not sure yet if it's related to a particular version of PyQt or something else): all plugins (dockwidgets) were shown detached (or hidden) from the mainwindow at startup (this is related to the attempt fixing [Issue 880](/spyder-ide/spyder/issues/880))


----


## Version 2.1.5

### Bug fixes (since v2.1.4)

* Detached dockwidgets (Console, ...) were not painted after restarting Spyder
* Editor/Outline-bugfix: duplicate entries were shown when the editor was synchronizing file contents with disk
* File/Project explorer:
    * Fixed regression regarding [Issue 740](/spyder-ide/spyder/issues/740) (fixed in v2.1.0, re-introduced in v2.1.2): couldn't open files with non-ascii characters in their names
    * SCM support: commit/log actions were not working when right-clicking on a file instead of a folder
* Console:
    * Monitor/Introspection: fixed socket communication issue due to a MemoryError -- This error was mixing communication messages, causing various problems described in [Issue 857](/spyder-ide/spyder/issues/847) and [Issue 858](/spyder-ide/spyder/issues/858). This bug was reported by ruoyu0088, who also tried (and succeeded) to fix it and suggested a workaround which is implemented in this release
    * Fix critical console hang on OS X when using the "Run selection or current block feature" (see [Issue 502](/spyder-ide/spyder/issues/502))
    * Apply the right scheme color to the IPython console when there weren't any options provided by the user or when the only option was "-colors LightBG"
* Windows platforms:
    * "Preferences" dialog was not shown if account username contained non-ASCII characters
* Object Inspector:
    * Show signatures for docstrings sent from the Editor (see [Issue 690](/spyder-ide/spyder/issues/690))

### Other changes (since v2.1.4)

* Debugging: when a non-empty SPYDER_DEBUG environment variable exists, Spyder switch to debug mode (log files are created in user's home directory and debug prints are available in the terminal)
* Variable explorer/Dictionary editor: added option to plot histogram from a 1-D array
* Console:
    * standard Python interpreter is now a real Python interactive session: the older implementation was running a startup script and tried to emulate a standard Python interactive session (changing attributes like __name__, running the PYTHONSTARTUP script, etc.). But this implementation was not close enough to the standard Python interactive session, i.e. when you execute `python` outside Spyder, without any argument. A recent bug report confirmed this: the PYTHONSTARTUP script was executed but not exactly the same way as it is outside Spyder: for example, doing `from __future__ import division` in the startup script had no effect whereas it did outside Spyder.
    * when running a standard Python interpreter, instead of running the startup script (spyderlib/widgets/externalshell/startup.py), the shell widget (ExternalPythonShell) simply runs the python executable with -u -i options, that's all. So now, the PYTHONSTARTUP script is executed as expected.
    * Scientific startup script (default PYTHONSTARTUP in Spyder): added floating point division (from __future__ import division)
    * PySide support:
        * Added new "Qt (PyQt/PySide)" settings group in "External modules" tab
        * It is now possible to select the Qt-Python bindings library: default (i.e. depends on the QT_API environment variable), PyQt or PySide
        * The PyQt input hook has been adapted for PySide, so it is now possible to do interactive (non-blocking) plotting with PySide
    * New options for standard Python interpreters (no effect on IPython):
        * "Merge process standard output/error channels": merging the output channels of the process means that the standard error won't be written in red anymore, but this has the effect of speeding up display
        * "Colorize standard error channel using ANSI escape codes": this method is the only way to have colorized standard error channel when the output channels have been merged
* Internal console ([Issue 868](/spyder-ide/spyder/issues/868)): output is now immediately available
* "Maximize current plugin" action: now automatically shows the "Outline" plugin when maximizing the "Editor" plugin
* Editor/Outline comment separators: allow space betwee hash and dash, e.g "# --- Outline Separator"


----


## Version 2.1.4

### Bug fixes (since v2.1.3)

* Console:
    * *Critical bugfix* for IPython support: variable explorer link was broken (regression introduced with v2.1.3)

### Other changes (since v2.1.3)

* Console:
    * option "Open an IPython interperter at startup" is now *explicitely* disabled for IPython v0.11+ (these versions of IPython are not fully supported through Spyder's console plugin)


----


## Version 2.1.3

### Enhancements (since v2.1.2)

* Variable explorer performance were improved, especially when dealing with very long sequences -- See [this discussion](http://groups.google.com/group/spyderlib/browse_thread/thread/3a7ef892695e417a)
* Variable explorer / dictionary editor: added support for unknown objects -- this allows browsing any object attributes -- This is still experimental.

### Bug fixes (since v2.1.2)

* General:
    * Spyder preferences/bugfix: comboboxes with keys other than strings (e.g. the PyQt API selection combo box) were not initialized properly
    * Fixed memory leaks (QThread objects) in the "Editor" and "Find in files" plugins. In those two plugins, QThread objects were created, then started but were never garbage-collected after they finished their execution
* Editor:
    * Supported file types: added missing C++ file extensions (.cc, .hh, .hxx)
* Variable explorer:
    * Debugging: added support for editing objects within functions
    * Debugging: when debugging, variable explorer link was broken after restarting program
    * handling errors when trying to enable/disable autorefresh (if one of the running console has no monitor enabled)
* Project explorer:
    * when the workspace has not yet been defined, creating a new project not only warns the user but also proposes to set it right away


----


## Version 2.1.2

### Bug fixes (since v2.1.1)

* General:
    * Patched external path library to avoid a crash with a user HOME directory with non-ascii characters
    * Doc/README: warning the user about the fact that the 'python setup.py install' method does not uninstall a previous version
* Console:
    * Fixed "AccessInit: hash collision: 3 for both 1 and 1" error (see [Issue 595](/spyder-ide/spyder/issues/595))
* Project explorer:
    * empty workspace/critical bugfix: impossible to create/import projects from context menu (this bug was introduced with a recent revision and stayed unnoticed until then because one has to test this from an empty workspace)
    * it is now possible to rename projects (safely)
    * now handling the I/O errors (e.g. read-only configuration files) occuring when loading/saving projects or the workspace: warning the user when an IOError exception was raised and mention the projects which could not be saved properly
* File/Project explorer:
    * keyboard shortcut 'F2' (rename file/directory) was broken
    * the "Open" action (context menu) was failing silently for directories (expected behavior: open an external file explorer to browse the directory)
    * programs.start_file/bugfix: feature was not working on Windows 7
* Editor:
    * Fix empty username in new file template on OS X (patch by Christoph Gohle)
* Object inspector:
    * Rich text mode was not showing headings when invoked from editor ([Issue 690](/spyder-ide/spyder/issues/690))

### Enhancements (since v2.1.1)

* File/Project explorer:
    * Added "Delete" keyboard shortcut to remove selected file(s)/folder(s)
    * SCM integration: added support for TortoiseHg v2 (only v1 was supported)
* Console/Matplotlib options: the backend may now be set separately from the Matplotlib patch

### Other changes (since v2.1.1)

* Console:
    * The Matplotlib patch is only applied for Matplotlib <=v1.0
    * PyQt API version issues (error like "ValueError: API 'QString' has already been set to version 1"): the "ignore setapi errors" option is disabled by default, to avoid masking these errors and associated tracebacks


----


## Version 2.1.1

_Note:_ v2.1.1 is a minor update of v2.1.0 (licence issues and minor bug fixes

Follow Spyder news on our official blog:
http://spyder-ide.blogspot.com/

### Compatibility/Requirements

Since version 2.1:
* Spyder is now compatible with:
    * PyQt's API v1 (i.e. compatible with PyQt 4.4 and 4.5), the default Python 2 API
    * *and* PyQt's API v2 (this is the future: default Python 3 API and PySide-compatible API)
    * *and* with PySide (PySide support is still experimental as this library is still young but its stability is evolving rapidly)
* Editor/code analysis: Spyder now requires *pyflakes v0.5.0* (included in Windows installers).

### New features since v2.0.12

* New *Profiler* plugin (thanks to Santiago Jaramillo)
* New experimental *IPython* plugin embedding IPython's Qt console: see [here](http://spyder-ide.blogspot.com/2011/08/preview-of-new-ipython-plugin-for.html)
* General:
    * Main window:
        * added "Custom window layouts" management (see menu "View")/handling 3 custom layouts: default shortcuts Shift+Alt+FX to switch to/from layout #X and Ctrl+Shift+Alt+FX to set layout #X
        * "General" preferences page: added option to set the Qt windows style, depending on platform (Plastique, Cleanlooks, CDE, Windows...)
        * Menu "?": added menu entry to report Spyder issues, filling automatically informations on your configuration
        * Reorganized "Run"/"Source" menu, added "Interpreters" menu
        * Fixed application name for Gnome 3/Fedora 15
* Command line options: added option "--defaults" to reset settings (stored in .spyder.ini) to defaults (a lot of settings are preserved: shortcuts, window layouts, ...) -- this is less brutal than "--reset" which reset all settings by removing all configuration files related to Spyder
* *Outline* (function/class browser) is now a plugin in itself, embedded in its own dockwidget: Spyder's window layout is even more customizable than before
* *Code completion*
    * (Editor/Console): entries starting with an underscore character are now placed to the end of the suggested list
    * (Editor/Console): Import statements are now completed correctly
* *Console*:
    * Major code cleaning: running Python applications in Spyder has never been cleaner and is very close to a simple Python interpreter
    * Added built-in function `open_in_spyder` to open a file in Spyder's source code editor from the console
    * Standard Python interpreter:
        * now refresh the variable explorer at each new prompt (even if auto-refresh is disabled -- actually, this is the typical use case)
        * added support for basic special commands (%pwd, %ls, %clear) and system commands (starting with '!', e.g. !dir or !ls)
        * added ["scientific" startup script](http://spyder-ide.blogspot.com/2011/09/new-enhanced-scientific-python.html) with support for numpy, scipy and matplotlib
    * Preferences (External modules tab):
        * added an option to set PyQt API to v1 or v2 -- this avoids issues with Enthought Tool Suite or any other library/program using PyQt API v2 which is *not* the default API for Python 2
        * changed matplotlib patch to fix compatiblity issue with PyQt API v2
    * Preferences (Advanced Settings tab): added option "Python executable" to customize path to Python interpreter executable binary
* *Variable explorer*:
    * New HDF5 plugin by [DavidAnthonyPowell](http://code.google.com/u/DavidAnthonyPowell/): import/export HDF5 files to/from the variable explorer
    * Dictionary editor/Variable explorer:
        * Added support for more NumPy data types
        * Added action "Resize rows to contents" (partially implements feature requested with [Issue 807](/spyder-ide/spyder/issues/807))
* *Editor*:
    * find/replace:
        * added support for *multiline* regular expression search pattern
        * added support for *multiline* regular expression text replacement
        * added button "Highlight matches" to highlight all found results
    * syntax highlighting: added support for OpenCL, gettext files, patch/diff files, CSS and HTML files
    * support for "2 spaces" and "tabs" indentation characters
    * new code analysis feature: added support for the [pep8](http://pypi.python.org/pypi/pep8) style guide checker
    * "Comment" and "Uncomment" actions were replaced by a single "Comment/Uncommment" toggle action
    * (Fixes  [Issue 811](/spyder-ide/spyder/issues/811) ) "Run configuration": added "Run in an external system terminal" option
* *File explorer* and *Project explorer*:
    * great performance improvement (using a multithreaded file system model)
    * Added minimalist SCM support (Mercurial and git are currently supported)
* *File explorer*: added an option to "Show current directory only"
* *Project explorer*: this plugin was entirely rewritten to improve performances and usability
* *Pylint plugin*:
    * added option to save file before analyzing it
* Spyder's console embedded in your application (spyderlib.widgets.internalshell):
    * in traceback, a clickable link now opens the associated file in Spyder (if application was launched from Spyder with monitor enabled)
    * Application sample embedding Spyder's internal shell: upgraded to guidata v1.4+ (simplified build script a lot)
* Windows platforms specific changes:
    * (requires pywin32) Hiding the attached console window:
        * allow running Spyder with 'python.exe' without visible console (this avoid using 'pythonw.exe' which does not attach a console to the process, hence preventing standard I/O to be redirected in a subprocess executed within Spyder, e.g. in your own program)
        * the attached console may be shown/hidden from menu entry "View > Attached console window (debugging)"
* Major change for Windows/PyQt users: standard Python interpreter now supports interactive GUI manipulations thanks to a new Spyder-specific input hook (replacing PyQt's input hook which is not working within Spyder on Windows platforms) -- the input hook works even better than PyQt's builtin input hook (with a Python interpreter opened outside Spyder)
* Spyder's stand-alone version building process was improved. This version is now available on project's download page.

### Bug fixes (since v2.0.12)

* Spyder's main window:
    * QtDesigner and QtLinguist were not detected on Fedora
    * Console/Editor: code completion widget was partially hidden when working on two monitors and if Spyder's window was on the right screen
    * Fixed bugs due to too early/frequent calls to plugin refresh methods during startup
* Console:
    * IPython Interpreter: Turn off autoindent magic to avoid indentation errors with code with inline comments
* Editor:
    * Fortran syntax highlighter was made case insensitive
    * Fixed IndentationError when running first line of a file
    * Read only files allowed ".", "[", "(", etc. to be entered into the text editor
    * Fixed segmentation faults occuring after using the vertical-horizontal splitting feature
    * If a file name had non-ascii characters then code completion (and all other rope-based features) in the editor stopped working
    * Code analysis: fixed tasks pattern (for example, previous one was matching "TIP" in "MULTIPLICATION"... now it will match only single "TIP:" or "TIP ")
    * (Fixes  [Issue 704](/spyder-ide/spyder/issues/704)) Outline was showing the delimiters of block comments ('#------...-'), causing nesting inconsistencies because block comments are not indented properly with respect to the code around
    * Fixed several bugs with the "Run selection or current block" feature.
* Object inspector:
    * Rich text mode was failing for non-ascii docstrings
* Find/Replace widget:
    * Combo box history was populated only when pressing Enter (now pressing F3 to find next occurence will add the current entry to history)


----


## Version 2.0.12

### Bug fixes (since v2.0.11)

* (Fixes [Issue 476](/spyder-ide/spyder/issues/476)) Editor/bugfix: print preview was not working
* Completion widget/bugfix (editor/console): combo box was truncated by main window depending on its size
* widgets.sourcecode.base.TextEditBaseWidget/bugfix: parenting to None was not working
* Console/Text wrap mode: character wrapping was not implemented since we switched from QTextEdit to QPlainTextEdit
* (Fixes [Issue 649](/spyder-ide/spyder/issues/649)) Patch submitted by [DavidAnthonyPowell](http://code.google.com/u/DavidAnthonyPowell/) - Syntax highlighter does not recognise imaginary, binary or octal numbers
* Spyder's layout: fixed window position/size issues when maximized/fullscreen mode was active
* Object inspector: fixed minor bug (simple traceback in the internal console) when handling a sphinx error
* (Fixes [Issue 667](/spyder-ide/spyder/issues/667)) Editor/bugfix: Shift+Enter inserted lines that did not get line numbers
* (Fixes [Issue 672](/spyder-ide/spyder/issues/672)) Editor: TODO/FIXME were not detected if not followed by ':' (HINT/TIP were properly detected)

### Enhancements (since v2.0.11)

* (Fixes [Issue 655](/spyder-ide/spyder/issues/655)) Editor/pyflakes-powered code analysis: warnings are now ignored for lines containing "pyflakes:ignore"

### Other changes (since v2.0.11)

* Internal console (Spyder debugging only): turned off the multithreaded mode


----


## Version 2.0.11

### Bug fixes (since v2.0.9)

* (Fixes [Issue 616](/spyder-ide/spyder/issues/616)) Pylint plugin: tree widget header text was not updated when analyizing a new script (the last analyzed script name was still shown)
* Editor/completion widget/bugfix: pressing shift was hiding the completion combo box
* (Fixes [Issue 630](/spyder-ide/spyder/issues/630)) Added missing default settings for "Spyder light" (only necessary when installing from scratch and without any remaining .spyder.ini file)
* Editor/Console-bugfix: info tooltips (calltips) were hidden right after being shown (i.e. when typing any character after the left parenthesis)
* (Fixes [Issue 631](/spyder-ide/spyder/issues/631)) Drag and drop of files into editor on Linux was pasting path instead of opening the file
* (Fixes [Issue 640](/spyder-ide/spyder/issues/640)) Editor: block comment was not working correctly at end of file
* Code completion widget (Editor/Console) - bugfix: parenting to the ancestor widget was necessary on Linux
* (Fixes [Issue 546](/spyder-ide/spyder/issues/546)) (Contributor: [Alex Fargus](http://code.google.com/u/alex.fargus/)) C/Cpp syntax highlighting bugfix
* (Fixes [Issue 646](/spyder-ide/spyder/issues/646)) IPython integration: fixed pyreadline monkey-patch for pyreadline v1.7

### Enhancements (since v2.0.9)

* File explorer widget/plugin: improved performances (widget is now populated in a separate thread)
* Spyder crash dialog: warning the user about the '--reset' option (this will remove all configuration files)


----


## Version 2.0.9

### Bug fixes (since v2.0.8)

* Console: added option to ignore PyQt/sip errors when trying to set sip API (fixed Enthought Tool Suite 3.6.0 compatibility issue)
* utils.dochelpers.getargtxt/bugfix: retrieving builtin function arguments was no longer working
* (Fixes [Issue 499](/spyder-ide/spyder/issues/499)) Editor-related keyboard shortcuts were not applied after opening files
* (Fixes [Issue 575](/spyder-ide/spyder/issues/575)) Tab scroll buttons were not shown on OS X resulting in clamped/changing window sizes
* (Fixes [Issue 574](/spyder-ide/spyder/issues/574)) Debugging: Spyder only synced at debugger breakpoints
* (Fixes [Issue 576](/spyder-ide/spyder/issues/576)) "Source / Remove trailing spaces" was removing newline at the end of file (+ added support for "undo")
* (Fixes [Issue 582](/spyder-ide/spyder/issues/582)) Console: changing font preferences was requiring a restart to be fully taken into account
* (Fixes [Issue 562](/spyder-ide/spyder/issues/562)) Spyder was unable to restore editor's outline explorer tree when mixed ' and " characters were found in tree entries
* (Fixes [Issue 590](/spyder-ide/spyder/issues/590)) Shell/"Clear line" shortcut was not correct: this is actually "Shift+Escape" (not "Escape")
* (Fixes [Issue 591](/spyder-ide/spyder/issues/591)) History log was systematically erased when updating Spyder version
* Outline explorer/bugfix: when opening file, the 'show/hide all files' option was not applied (this was then applied when switching from a file to another)
* (Fixes [Issue 602](/spyder-ide/spyder/issues/602)) Backported from v2.1 a couple of bugfixes related to Editor and multiple panels
* Object inspector: when raised automatically above other dockwidgets, plugin refresh was unnecessarily triggered
* Editor/code completion-bugfix: some key events (e.g. Ctrl+V) were lost during code completion-related hang-up
* (Fixes [Issue 599](/spyder-ide/spyder/issues/599)) Multiline text pasting was not working in a newly opened console (i.e. first prompt)

### Enhancements (since v2.0.8)

* Major change/Translations: moved from 'QtLinguist' to 'gettext' (localizing Spyder should now be easier)
* Console: increased default maximum line count (buffer depth) up to 10,000 lines (instead of only 300 lines)
* Editor's rope-based introspection features (code completion, calltips, go to definition): new rope monkey-patch providing major performance improvements
* File explorer/Project explorer - opening file with associated application: now supported on all platforms
* Added action "Reset window layout" in "View" menu to reset main window layout to default
* Documentation: added page on debugging
* Editor: added syntax highlighters for diff/patch files (.diff, .patch, .rej) and gettext files (.po, .pot)
* (Fixes [Issue 537](/spyder-ide/spyder/issues/537)) Global working directory toolbar: removed label considering the fact that the toolbar widgets are quite explicit on its role (and the combo box tooltip is explaining it in detail)
* (Fixes [Issue 598](/spyder-ide/spyder/issues/598)) Added a .desktop file in source package
* (Fixes [Issue 87](/spyder-ide/spyder/issues/87)) Editor plugin's title now show the current script filename


----


## Version 2.0.8

### Bug fixes (since v2.0.6)

* Consoles/bugfix: saving history log (see context menu) was not working following a recent code cleaning/refactoring
* On non-Windows platforms, the file selection dialog "All files (*.*)" filter was not matching files without extension
* dochelpers.isdefined/bugfix: ignoring syntax errors while evaluating object
* Preferences Dialog (dialog box + keyboard shortcut page): improved size/resize behavior
* Editor: when cursor was on the very last line, Duplicate/Delete line features were getting stuck in an infinite loop
* Editor/duplicate line feature - fixed unexpected behavior: when duplicating selected text, text selection was extended to duplicated part
* Editor/bugfix with multiple editor windows: when opening file on one editor window, the top-left corner menu (file list) was not updated correctly in other editor windows
* Editor/fixed unexpected behavior: when clicking on the main window's outline explorer while a separate editor window had focus, the latter was used to show the associated line of code
* Project explorer: added new debugging options (profiling 'rope' calls)
* Console/Advanced settings/UMD module list: removing all entries (empty module list) was not working
* Editor/File list management dialog (Ctrl+E): double clicking/pressing Return on a listwidget item will switch to the associated file
* Editor/Tab bar: fixed missing tooltips issue (and missing file switch menu entries)
* Code completion/bugfix: list widget was not hiding as expected when pressing ':'
* Editor/fixed unexpected behavior: when some text was selected, "Ctrl+Left mouse click" was trying to "go to definition" instead of doing the standard drag n'drop feature
* Editor/bugfix: disabling code completion/calltips for non-Python source code (was not working -as expected- but was taking time to simply not work...)
* Editor/go to line: fixed unicode error
* Code editor/bugfix: cursor position was not restored when undoing an indent operation with "tab always indent" feature turned on *and* the cursor at the end of the line
* Tab behavior when "tab always indents" is turned off: inserting 4-(len(leading_text) % 4) spaces (instead of 4)
* Object inspector/bugfix: ignoring unknown objects when called automatically from editor/console, i.e. do not log, do not show 'no doc available'

### Other changes (since v2.0.6)

* Code editor syntax highlighting: added more keywords to Cython syntax highlighter (cpdef, inline, cimport and DEF)
* Added example of application using the Spyder's internal shell as a debugging console (demonstrates also the py2exe deployment procedure)
* Object inspector: added "Source" combo box (Console/Editor) -> object inspected from editor are now analyzed only with rope (if available) and then shown in object inspector
* Added keyboard shortcut to open Preferences Dialog (default: Ctrl+Alt+Shift+P)
* Editor: added "Copy line" feature (Ctrl+Alt+Down), similar to "Duplicate line" (Ctrl+Alt+Up) but paste text before the current line/selected text (instead of after)
* Array editor: added option to set row/col labels (resp. ylabels and xlabels)
* Editor/rope: improved performance for calltips/doc feature


----


## Version 2.0.6

### Bug fixes (since v2.0.5)

* Console: menu entries "Environment variables", "Current working directory" and "Show sys.path" were not disabled when the Monitor was turned off
* Preferences dialog box/Keyboard shortcuts:
    * conflicts are now ignored if shortcuts have different contexts *except* if one of this context is '`_`' (i.e. global context)
    * conflict warnings are now also shown when showing the preferences dialog box (not only when modifying shortcuts and applying changes)
* Drag/drop Python script to console: fixed TypeError (TypeError: start() got an unexpected keyword argument 'ask_for_arguments')
* Console base widget: added support for FF (Form Feed) ANSI sequence - Fixes bug in IPython console: 'cls' and 'clear' magic commands were inactive in IPython consoles
* Editor: code completion was sometimes very slow when editing files within a Spyder project
* Code editor: fixed "Delete line" feature (Ctrl+D) / was not working with multiline selection

### Other changes (since v2.0.5)

* Editor/80-column vertical edge line: added options to show/hide this line and change the column number
* Editor: added "Comment"/"Uncomment" actions to context menu
* Source code and shell editor widgets: code refactoring/cleaning (this should help people using these widgets outside Spyder)
