# History of changes

## Version 3.0.2 (2016/11/20)

### New features

* Add an option under *Preferences > General* to enable/disable high DPI scaling (disabled by default).
* Add a menu entry in the Projects menu to cleanly delete projects.
* Add the shortcuts Ctrl+U and Ctrl+Shift+U to turn text into lower/uppercase respectively.

### Bugs fixed

**Issues**

* [Issue 3647](https://github.com/spyder-ide/spyder/issues/3647) - "%reset -s" is giving an error in the IPython console
* [Issue 3618](https://github.com/spyder-ide/spyder/issues/3618) - Removing a project deletes also the files on the disk
* [Issue 3609](https://github.com/spyder-ide/spyder/issues/3609) - New release dialog is un-clickable
* [Issue 3588](https://github.com/spyder-ide/spyder/issues/3588) - Files are opened twice at startup if a project is active
* [Issue 3583](https://github.com/spyder-ide/spyder/issues/3583) - Error when connecting to external kernels
* [Issue 3575](https://github.com/spyder-ide/spyder/issues/3575) - Cannot press Enter after underscore in File Switcher
* [Issue 3564](https://github.com/spyder-ide/spyder/issues/3564) - Error when reloading modules in the IPython Console in Python 2
* [Issue 3561](https://github.com/spyder-ide/spyder/issues/3561) - Working Directory toolbar is not working for IPython Consoles
* [Issue 3553](https://github.com/spyder-ide/spyder/issues/3553) - Spyder fails to launch because of Unicode errors in create_kernel_spec
* [Issue 3522](https://github.com/spyder-ide/spyder/issues/3522) - Dependencies diaog not updating correctly when installing dependencies while spyder is running
* [Issue 3519](https://github.com/spyder-ide/spyder/issues/3519) - Cannot set Maximum Number of Recent Files
* [Issue 3513](https://github.com/spyder-ide/spyder/issues/3513) - Spyder does not free up memory after closing windows with datasets in the Variable explorer
* [Issue 3489](https://github.com/spyder-ide/spyder/issues/3489) - Display problems on systems that use 'display scaling'
* [Issue 3444](https://github.com/spyder-ide/spyder/issues/3444) - Reports of Kernel Death are greatly exagerated
* [Issue 3436](https://github.com/spyder-ide/spyder/issues/3436) - Default file extension should be .py instead of empty
* [Issue 3430](https://github.com/spyder-ide/spyder/issues/3430) - Update translations
* [Issue 3214](https://github.com/spyder-ide/spyder/issues/3214) - Indentation after a line with [] and {} is reset
* [Issue 3127](https://github.com/spyder-ide/spyder/issues/3127) - Spyder fails to launch because of errors in spyder.ini
* [Issue 2159](https://github.com/spyder-ide/spyder/issues/2159) - Built-in 'print' statement is displayed as two different colors depending on indentation
* [Issue 1669](https://github.com/spyder-ide/spyder/issues/1669) - Menu item and shortcut to toggle UPPER and lower case of selected text
* [Issue 1665](https://github.com/spyder-ide/spyder/issues/1665) - sympy shadows matplotlib in ipython console
* [Issue 1373](https://github.com/spyder-ide/spyder/issues/1373) - Editor autoindentation fails after list, dict

In this release 22 issues were closed

**Pull requests**

* [PR 3702](https://github.com/spyder-ide/spyder/pull/3702) - PR: Update French translation
* [PR 3694](https://github.com/spyder-ide/spyder/pull/3694) - Restore icons in the code completion widget
* [PR 3687](https://github.com/spyder-ide/spyder/pull/3687) - Increase time to detect if an IPython kernel is alive
* [PR 3681](https://github.com/spyder-ide/spyder/pull/3681) - Update Spanish translation
* [PR 3679](https://github.com/spyder-ide/spyder/pull/3679) - Update Russian translations
* [PR 3664](https://github.com/spyder-ide/spyder/pull/3664) - Free memory when closing a Variable Explorer editor
* [PR 3661](https://github.com/spyder-ide/spyder/pull/3661) - IPython Console: Fix error when running "%reset -s"
* [PR 3660](https://github.com/spyder-ide/spyder/pull/3660) - IPython Console: Simple fix after PR #3641
* [PR 3642](https://github.com/spyder-ide/spyder/pull/3642) - PR: Fix unclickable update message box
* [PR 3641](https://github.com/spyder-ide/spyder/pull/3641) - PR: Fix error when trying to add a non-ascii module in Python 2 to the UMR blacklist
* [PR 3629](https://github.com/spyder-ide/spyder/pull/3629) - PR: Add shortcut for Upper/Lower functionality
* [PR 3626](https://github.com/spyder-ide/spyder/pull/3626) - PR: Added management for delete operation of a project
* [PR 3622](https://github.com/spyder-ide/spyder/pull/3622) - Fix connection between the IPython Console and the Working Directory toolbar
* [PR 3621](https://github.com/spyder-ide/spyder/pull/3621) - Some corrections after pull request #3580
* [PR 3619](https://github.com/spyder-ide/spyder/pull/3619) - Fix another error when connecting to external kernels
* [PR 3615](https://github.com/spyder-ide/spyder/pull/3615) - PR: Allow underscore to be valid for Enter in File Switcher
* [PR 3599](https://github.com/spyder-ide/spyder/pull/3599) - Load default settings if there is any error in spyder.ini
* [PR 3596](https://github.com/spyder-ide/spyder/pull/3596) - PR: New warning message in IPython console when both pylab and sympy are enabled
* [PR 3590](https://github.com/spyder-ide/spyder/pull/3590) - Fix builtin and keywords highlighting depending on indentation
* [PR 3589](https://github.com/spyder-ide/spyder/pull/3589) - Don't open files saved as part of a project twice at startup
* [PR 3582](https://github.com/spyder-ide/spyder/pull/3582) - PR: Added a verification for the existence of the 'text/plain' key
* [PR 3581](https://github.com/spyder-ide/spyder/pull/3581) - PR: remove spyder/widgets/tests/__init__.py because of error in execution of pytest -rxs
* [PR 3580](https://github.com/spyder-ide/spyder/pull/3580) - PR: Set default file extension in save dialog
* [PR 3576](https://github.com/spyder-ide/spyder/pull/3576) - Fix autoindentation after data structures.
* [PR 3572](https://github.com/spyder-ide/spyder/pull/3572) - PR: Change deprecated funtion QInputDialog.getInteger for QInputDialog.getInt
* [PR 3551](https://github.com/spyder-ide/spyder/pull/3551) - Add option to set/unset dpi scaling for screens that are not high resolution
* [PR 3543](https://github.com/spyder-ide/spyder/pull/3543) - PR: Change of the label in the dependencies dialog

In this release 27 pull requests were merged


----


## Version 3.0.1 (2016-10-19)

### Bugfixes

**Issues**

* [Issue 3528](https://github.com/spyder-ide/spyder/issues/3528) - Cannot see numpy datatypes in variable explorer
* [Issue 3518](https://github.com/spyder-ide/spyder/issues/3518) - Spyder hangs with big numpy structured arrays
* [Issue 3484](https://github.com/spyder-ide/spyder/issues/3484) - Fix menus in macOS
* [Issue 3475](https://github.com/spyder-ide/spyder/issues/3475) - Cannot type left parenthesis in ipdb when automatic Help is turned on
* [Issue 3472](https://github.com/spyder-ide/spyder/issues/3472) - Cannot connect to existing ipython kernel after upgrading to 3.0
* [Issue 3471](https://github.com/spyder-ide/spyder/issues/3471) - "Local variable 'reply' referenced before assignment" on debugger exit
* [Issue 3454](https://github.com/spyder-ide/spyder/issues/3454) - ImportError with create_app.py
* [Issue 3453](https://github.com/spyder-ide/spyder/issues/3453) - Update docs for Projects
* [Issue 3317](https://github.com/spyder-ide/spyder/issues/3317) - Console/Editor lose focus when auto-connected to help
* [Issue 2284](https://github.com/spyder-ide/spyder/issues/2284) - Very slow boot time on Mac app

In this release 10 issues were closed

**Pull requests**

* [PR 3560](https://github.com/spyder-ide/spyder/pull/3560) - Update documentation
* [PR 3550](https://github.com/spyder-ide/spyder/pull/3550) - Prevent WebEngine to steal focus when setting html on the page
* [PR 3548](https://github.com/spyder-ide/spyder/pull/3548) - Fix some ipdb issues
* [PR 3546](https://github.com/spyder-ide/spyder/pull/3546) - Truncate all values shown in the Variable Explorer
* [PR 3544](https://github.com/spyder-ide/spyder/pull/3544) - Don't try to get shape and ndim for objects that are not ndarrays
* [PR 3541](https://github.com/spyder-ide/spyder/pull/3541) - Update create_app.py for Spyder 3.0
* [PR 3540](https://github.com/spyder-ide/spyder/pull/3540) - Fix problems when connecting to external kernels
* [PR 3501](https://github.com/spyder-ide/spyder/pull/3501) - PR: Handle Mac menubar icon bug
* [PR 3499](https://github.com/spyder-ide/spyder/pull/3499) - Testing: Pin conda-build to 2.0.0

In this release 9 pull requests were merged


----


## Version 3.0 (2016-09-24)

### New features

#### Main Window

* The *Object Inspector* pane was renamed to *Help*.
* Add a new icon theme based on FontAwesome.
* Add an *Introduction* interactive tutorial (under the `Help` menu).
* Add new default layouts (Horizontal, Vertical, Matlab and Rstudio), and also the
  possibility to name custom layouts.
* Panes that are tabbed next to each other can now be rearranged by dragging and
  dropping their tabs.
* Check for Spyder updates at startup, and also if you go to the menu entry
  `Help > Check for updates`.
* Add the shortcut `Shift+Alt+R` to restart the application.
* Add an option to warn when exiting the application, under
  `Preferences > General > Interface > Prompt when exiting`.
* Add Portuguese, Russian and Japanese translations.
* Remove light mode

#### Editor

* Add highlighting and code completion to all file types supported by Pygments
  (a syntax highlighting library)
* Use `Ctrl+M` and `Ctrl+Alt+M` to visually create matrices and vectors. It also
  works on the Python and IPython consoles.
* Add a new file switcher inspired by the Sublime Text one, which can be called
  with the `Ctrl+P` shortcut. It can also be used to look for classes, functions
  and methods inside a file, using the `@my_function` syntax.

#### Projects

* A new menu entry called *Projects* was added to the main window with all
  actions related to projects.
* A project now saves the state of open files in the Editor, so that people can
  easily work on different coding efforts at the same time.
* The project's path is added to `PYTHONPATH`, so that Python packages
  developed as part of a project can be easily imported in Spyder consoles.
* The project explorer now shows a file tree view of the current project, as
  other editors and IDEs do (e.g. Sublime Text and VSCode).
* Projects are completely optional and not imposed on users, i.e. users can work
  without creating any project.

#### Settings

* Keyboard shortcuts can now be entered in an easier and more intuitive way.
* Add a menu entry to reset to default settings, under
  `Tools > Reset Spyder to factory defaults`.
* The language used in the main interface can now be changed. The option to
  do it is present in `General > Advanced Settings`.
* `Syntax coloring` now has a preview of the selected theme and it's able to
  change the current theme for all plugins.
* Plain and Rich text fonts for all plugins are now changed in
  `General > Appearance`.
* Add a new entry called `Python interpreter` to allow people to select the
  interpreter used for all Python and IPython consoles (this was before in
  `Console > Advanced settings`).
* Rename the `Console` entry to `Python console`.

#### IPython console

* Drop support for IPython 3.0 and older versions.
* Support the new `qtconsole` package instead.
* Communicate directly with IPython kernels instead of doing it through the
  Python  console.

#### Debugging

* Enter debugging mode if running a file generates errors. This is not activated
  by default but you can do it by going to `Run > Configure > General settings`.

#### Profiler

* Add the ability to save and restore profiler data to compare speed improvements.

#### Working directory toolbar

* Get directory completions by pressing the `Tab` key twice on it.

#### API Changes

##### Major changes

* The `spyderlib` module was renamed to `spyder`
* `spyderplugins` has been removed and its plugins have been assigned to different
  different modules (`spyder_profiler`, `spyder_breakpoints`, etc) still
  distributed with the Spyder package.

##### Minor changes

* `spyderlib.widgets.dicteditor.DictEditor` has been renamed to
  `spyder.widgets.variableexplorer.collectionseditor.CollectionsEditor`.
* `spyderlib/widgets/dicteditorutils.py` has been renamed to
  `spyder/widgets/variableexplorer/utils.py`.
* `spyderlib/widgets/externalshell/namespacebrowser.py` has been moved to
  `spyder/widgets/variableexplorer`.
* `spyderlib/widgets/externalshell/syntaxhighlighters.py` has been moved to
  `spyder/utils/`.
* Variable Explorer editor widgets were moved from `spyderlib.widgets`
  to `spyder.widgets.variableexplorer`:
    * `spyder.widgets.variableexplorer.arrayeditor`
    * `spyder.widgets.variableexplorer.collectionseditor`
    * `spyder.widgets.variableexplorer.objecteditor`
    * `spyder.widgets.variableexplorer.texteditor`
    * `spyder.widgets.variableexplorer.dataframeeditor`
* Modules used for configuration options (e.g. `spyderlib.config`,
  `spyderlib.baseconfig`, etc) were moved to a new namespace called
  `spyder.config`.
* Modules and files related to the application have been moved to
  `spyder.app`.
* `spyderlib/plugins/projectexplorer.py` has been renamed to
  `spyder/plugins/projects.py`
* `spyderlib/widgets/projectexplorer.py` has been renamed to
  `spyder/widgets/projects/explorer.py`
* `spyderlib/plugins/inspector.py` was renamed to
  `spyder/plugins/help.py`.
* `spyderlib/utils/inspector` was renamed to `spyder/utils/help`.
* `spyderlib.qt` was removed.
* `spyderlib/widgets/ipython.py` was broken in several files inside
   `spyder/widgets/ipythonconsole`.
* `spyder/widgets/externalshell/{sitecustomize.py, osx_app_site.py}` were
  moved to `spyder/utils/site`
* `spyder/widgets/externalshell/start_ipython_kernel.py` was moved to
  `spyder/utils/ipython`

#### Under the hood

* Drop support for Python 2.6 and 3.2.
* Support PyQt5.
* Drop official support for PySide. Support for it will have to come from the community.
* Move our settings directory to `HOME/.spyder{-py3}`. Previous location was `HOME/.spyder2{-py3}`
* On Linux we now follow the XDG specification to save our settings, i.e. they are saved in
  `~/.config/spyder{-py3}` or `$XDG_CONFIG_HOME/spyder{-py3}` if `$XDG_CONFIG_HOME` is
  defined.
* Use the new (pythonic) style for signals and slots.
* Test Spyder with the help of Travis and AppVeyor.
* Code completions and help retrieval on the Editor are done asynchronously using a
  client/server architecture based on PyZMQ.
* Spyder now uses the `qtpy` package to be able to work with PyQt4 and PyQt5 seamlessly.

### Bugfixes

**Issues**

* [Issue 3428](https://github.com/spyder-ide/spyder/issues/3428) - runfile is not defined ?
* [Issue 3427](https://github.com/spyder-ide/spyder/issues/3427) - Spyder is opening black DOS windows now

In this release 2 issues were closed

**Pull requests**

* [PR 3451](https://github.com/spyder-ide/spyder/pull/3451) - Update Brazilian Portuguese translation
* [PR 3450](https://github.com/spyder-ide/spyder/pull/3450) - Update Spanish translation
* [PR 3446](https://github.com/spyder-ide/spyder/pull/3446) - Some fixes for Appveyor and Travis
* [PR 3442](https://github.com/spyder-ide/spyder/pull/3442) - Avoid showing cmd consoles when starting IPython kernels on Windows
* [PR 3441](https://github.com/spyder-ide/spyder/pull/3441) - Update Russian translation
* [PR 3439](https://github.com/spyder-ide/spyder/pull/3439) - Fix profiler
* [PR 3438](https://github.com/spyder-ide/spyder/pull/3438) - Add an init file to utils/site so it can be added to our tarballs

In this release 7 pull requests were merged


----


## Version 3.0beta7 (2016-09-16)

### Bugfixes

**Issues**

* [Issue 3419](https://github.com/spyder-ide/spyder/issues/3419) - IPython console: help window hijacks `?` keypress
* [Issue 3403](https://github.com/spyder-ide/spyder/issues/3403) - Error when opening project and cancelling
* [Issue 3354](https://github.com/spyder-ide/spyder/issues/3354) - IPython console run code lines not being saved in preferences
* [Issue 3109](https://github.com/spyder-ide/spyder/issues/3109) - Auto select the only IPython or Python console after startup
* [Issue 3011](https://github.com/spyder-ide/spyder/issues/3011) - Cannot connect to existing kernel with full path specified
* [Issue 2945](https://github.com/spyder-ide/spyder/issues/2945) - Cannot locate kernel json file when connecting to remote ipython kernel
* [Issue 2918](https://github.com/spyder-ide/spyder/issues/2918) - Spyder always switches back to IPython kernel from IPyhton console
* [Issue 2846](https://github.com/spyder-ide/spyder/issues/2846) - Import runfile() produces errors when using a virtualenv
* [Issue 2844](https://github.com/spyder-ide/spyder/issues/2844) - Spyder won't connect to kernel / IPython console after switching to an external interpreter
* [Issue 2790](https://github.com/spyder-ide/spyder/issues/2790) - Make "Ask for confirmation before closing tabs" in IPython console work for all consoles
* [Issue 2696](https://github.com/spyder-ide/spyder/issues/2696) - Enter in the IPython console inserts new line instead of executing current line after kernel restart
* [Issue 1860](https://github.com/spyder-ide/spyder/issues/1860) - Don't show IPython kernels in the Python console by default

In this release 12 issues were closed

**Pull requests**

* [PR 3423](https://github.com/spyder-ide/spyder/pull/3423) - Try to fix plotting on Windows for the Python Console
* [PR 3422](https://github.com/spyder-ide/spyder/pull/3422) - Don't try to use "?" to automatically get help in the IPython console
* [PR 3421](https://github.com/spyder-ide/spyder/pull/3421) - Don't show a message when users press cancel in the "Open project" dialog
* [PR 3420](https://github.com/spyder-ide/spyder/pull/3420) - Skip testing the Spyder kernel for IPython consoles
* [PR 3386](https://github.com/spyder-ide/spyder/pull/3386) - Allow plugins with no dockwidgets
* [PR 3368](https://github.com/spyder-ide/spyder/pull/3368) - Avoid eval() when reading config file
* [PR 2878](https://github.com/spyder-ide/spyder/pull/2878) - PR: Remove IPython kernels from the Python console and connect directly to them

In this release 7 pull requests were merged


----


## Version 3.0beta6 (2016-08-30)

### Bugfixes

**Issues**

* [Issue 3363](https://github.com/spyder-ide/spyder/issues/3363) - Spyder wont start unless file ".spyderproject" is deleted. UnpicklingError
* [Issue 3274](https://github.com/spyder-ide/spyder/issues/3274) - Text not visible in new file switcher in KDE
* [Issue 3211](https://github.com/spyder-ide/spyder/issues/3211) - Edited syntax coloring preferences are not applied or saved
* [Issue 3128](https://github.com/spyder-ide/spyder/issues/3128) - Project Explorer filename filter (minor)
* [Issue 3099](https://github.com/spyder-ide/spyder/issues/3099) - Can existing files be added to a Spyder project?
* [Issue 2887](https://github.com/spyder-ide/spyder/issues/2887) - Make .spyderproject a textfile
* [Issue 2636](https://github.com/spyder-ide/spyder/issues/2636) - Problems with filename extension for saved sessions 
* [Issue 2595](https://github.com/spyder-ide/spyder/issues/2595) - Spyder project renames/creates folders by removing first letter of imported directories
* [Issue 2460](https://github.com/spyder-ide/spyder/issues/2460) - Design for Projects in 3.0
* [Issue 1964](https://github.com/spyder-ide/spyder/issues/1964) - Project explorer doesn't refresh its contents
* [Issue 1947](https://github.com/spyder-ide/spyder/issues/1947) - New Project not getting created
* [Issue 1642](https://github.com/spyder-ide/spyder/issues/1642) - Files excluded by the filter list are displayed in the project explorer after start of spyder
* [Issue 1554](https://github.com/spyder-ide/spyder/issues/1554) - Add project's path to our PYTHONPATH so that it can be imported in the console
* [Issue 1320](https://github.com/spyder-ide/spyder/issues/1320) - Reorganize Spyder repository
* [Issue 1317](https://github.com/spyder-ide/spyder/issues/1317) - Make Project Explorer remember state of open files when reopening

In this release 15 issues were closed

**Pull requests**

* [PR 3377](https://github.com/spyder-ide/spyder/pull/3377) - Completely rewrite our support for Projects
* [PR 3370](https://github.com/spyder-ide/spyder/pull/3370) - Some improvements to our CI services
* [PR 3369](https://github.com/spyder-ide/spyder/pull/3369) - Remove some old files and directories
* [PR 3356](https://github.com/spyder-ide/spyder/pull/3356) - Remove icons from tabs for the Editor and IPython Console
* [PR 3355](https://github.com/spyder-ide/spyder/pull/3355) - Some improvements to our file switcher
* [PR 3277](https://github.com/spyder-ide/spyder/pull/3277) - Finish reorganization of the Spyder repo

In this release 6 pull requests were merged


----


## Version 3.0beta5 (2016-08-22)

### Bugfixes

**Issues**

* [Issue 3351](https://github.com/spyder-ide/spyder/issues/3351) - Spyder not opening because of problems with spyder.lock
* [Issue 3327](https://github.com/spyder-ide/spyder/issues/3327) - Drag and drop from OS file explorer is not working
* [Issue 3308](https://github.com/spyder-ide/spyder/issues/3308) - Variable Explorer fails to display DataFrame with categories
* [Issue 3306](https://github.com/spyder-ide/spyder/issues/3306) - Spyder unresponsive, requires forced quit (OS X)
* [Issue 3297](https://github.com/spyder-ide/spyder/issues/3297) - Pressing Ctrl+P twice opens file switcher twice
* [Issue 3293](https://github.com/spyder-ide/spyder/issues/3293) - F9 does not auto advance when it's at the last line
* [Issue 3288](https://github.com/spyder-ide/spyder/issues/3288) - "Quit Spyder" menu entry doesn't work in 3.0.0b4 (OS X 10.11)
* [Issue 3287](https://github.com/spyder-ide/spyder/issues/3287) - Spyder can't open a console because of problems with Beautiful Soup
* [Issue 3282](https://github.com/spyder-ide/spyder/issues/3282) - QApplication is used from QtGui instead of QtWidgets in app/spyder.py
* [Issue 2940](https://github.com/spyder-ide/spyder/issues/2940) - Variable explorer can't show Pandas objects containing timezone aware columns
* [Issue 2629](https://github.com/spyder-ide/spyder/issues/2629) - Use XDG_CONFIG_HOME for config directory on Linux
* [Issue 2465](https://github.com/spyder-ide/spyder/issues/2465) - Images are not rendered by the Help pane on Windows
* [Issue 2119](https://github.com/spyder-ide/spyder/issues/2119) - Spyder doesn't render well on HighDpi screens

In this release 13 issues were closed

**Pull requests**

* [PR 3366](https://github.com/spyder-ide/spyder/pull/3366) - Fix "Quit Spyder" action on OS X
* [PR 3357](https://github.com/spyder-ide/spyder/pull/3357) - Remove lock file as part of --reset
* [PR 3353](https://github.com/spyder-ide/spyder/pull/3353) - Rewrite computation of max and min in dataframe editor
* [PR 3352](https://github.com/spyder-ide/spyder/pull/3352) - Use XDG_CONFIG_HOME to save our settings on Linux
* [PR 3339](https://github.com/spyder-ide/spyder/pull/3339) - Fix dragging and dropping files to the Editor
* [PR 3338](https://github.com/spyder-ide/spyder/pull/3338) - Testing: Use Qt/PyQt 5.6 packages in Travis
* [PR 3336](https://github.com/spyder-ide/spyder/pull/3336) - PR: Update readme and organize badges
* [PR 3333](https://github.com/spyder-ide/spyder/pull/3333) - Enable high DPI scaling on Qt >= 5.6
* [PR 3325](https://github.com/spyder-ide/spyder/pull/3325) - Fix further freezes because of pyzmq
* [PR 3324](https://github.com/spyder-ide/spyder/pull/3324) - Make 'run line' add a blank line if on last line.
* [PR 3319](https://github.com/spyder-ide/spyder/pull/3319) - Test Spyder with Qt 5.6 in AppVeyor
* [PR 3315](https://github.com/spyder-ide/spyder/pull/3315) - Fix showing images in the Help plugin for Windows
* [PR 3313](https://github.com/spyder-ide/spyder/pull/3313) - Toggle file switcher when pressing its keyboard shortcut
* [PR 3312](https://github.com/spyder-ide/spyder/pull/3312) - Fix monkey-patching of QApplication
* [PR 3310](https://github.com/spyder-ide/spyder/pull/3310) - Fix error when Beautiful Soup is installed incorrectly
* [PR 3300](https://github.com/spyder-ide/spyder/pull/3300) - Re-include plugins in setup.py packages
* [PR 3295](https://github.com/spyder-ide/spyder/pull/3295) - PR: Fix/Find in files
* [PR 3294](https://github.com/spyder-ide/spyder/pull/3294) - Add keyboard shortcuts to context menu in editor
* [PR 3285](https://github.com/spyder-ide/spyder/pull/3285) - Japanese translation
* [PR 3273](https://github.com/spyder-ide/spyder/pull/3273) - Testing: Don't use particular tags when installing local conda packages

In this release 20 pull requests were merged


----


## Version 3.0beta4 (2016-07-01)

### Bugfixes

**Issues**

* [Issue 3267](https://github.com/spyder-ide/spyder/issues/3267) - Spyder 3.0 Beta3 fails to start in OS X
* [Issue 3237](https://github.com/spyder-ide/spyder/issues/3237) - Unable to see Float16 in Spyder Variable Explorer
* [Issue 3231](https://github.com/spyder-ide/spyder/issues/3231) - Deprecation warning from IPython 5.0.0b4
* [Issue 3230](https://github.com/spyder-ide/spyder/issues/3230) - Spyder is failing because of wrong qtpy version
* [Issue 3223](https://github.com/spyder-ide/spyder/issues/3223) - Spyder 3.0 Beta 3 crashing or freezing because of zmq problems
* [Issue 3219](https://github.com/spyder-ide/spyder/issues/3219) - Pylint report not jumping to line
* [Issue 3206](https://github.com/spyder-ide/spyder/issues/3206) - Local variable 'backends' referenced before assignment when starting IPython kernel
* [Issue 3188](https://github.com/spyder-ide/spyder/issues/3188) - Spyder crashes after creating a new file from Project/File Explorer
* [Issue 3187](https://github.com/spyder-ide/spyder/issues/3187) - Spyder crashes after deleting a folder in File explorer
* [Issue 3186](https://github.com/spyder-ide/spyder/issues/3186) - "New -> Module..." menu not saving the new module file to the disk
* [Issue 3159](https://github.com/spyder-ide/spyder/issues/3159) - Cannot search text in Help pane
* [Issue 3155](https://github.com/spyder-ide/spyder/issues/3155) - Exception raised when running script in external terminal
* [Issue 3150](https://github.com/spyder-ide/spyder/issues/3150) - Fix external plugins import
* [Issue 3116](https://github.com/spyder-ide/spyder/issues/3116) - Console panel resizing itself as new console tabs are opened
* [Issue 3020](https://github.com/spyder-ide/spyder/issues/3020) - DataFrame editor should first sort up, then down
* [Issue 3010](https://github.com/spyder-ide/spyder/issues/3010) - DataFrame editor should do a stable sort
* [Issue 2995](https://github.com/spyder-ide/spyder/issues/2995) - Variable explorer - Sequence break with wrong mapping
* [Issue 2976](https://github.com/spyder-ide/spyder/issues/2976) - Profiling hangs/freezes Spyder
* [Issue 2915](https://github.com/spyder-ide/spyder/issues/2915) - Problems with changing keyboard shortcuts on Mac
* [Issue 2914](https://github.com/spyder-ide/spyder/issues/2914) - Change keybinding for Replace text (⌘H) in the Editor on Mac
* [Issue 1462](https://github.com/spyder-ide/spyder/issues/1462) - Repeatable segfault while editing HTML file
* [Issue 872](https://github.com/spyder-ide/spyder/issues/872) - Quotes and colons autocompletion

In this release 22 issues were closed

**Pull requests**

* [PR 3271](https://github.com/spyder-ide/spyder/pull/3271) - Fix introspection plugin server restart and timeout
* [PR 3266](https://github.com/spyder-ide/spyder/pull/3266) - Fix searching text in our Web widgets
* [PR 3264](https://github.com/spyder-ide/spyder/pull/3264) - Support float16 values in array editor
* [PR 3261](https://github.com/spyder-ide/spyder/pull/3261) - Fix timeouts in AppVeyor
* [PR 3260](https://github.com/spyder-ide/spyder/pull/3260) - Fix handling of unmatched end-of-HTML-comment.
* [PR 3253](https://github.com/spyder-ide/spyder/pull/3253) - Update minimal required version of several of our dependencies
* [PR 3252](https://github.com/spyder-ide/spyder/pull/3252) - Change Replace shortcut from Ctrl/Cmd+H to Ctrl/Cmd+R
* [PR 3251](https://github.com/spyder-ide/spyder/pull/3251) - Fix problems in AppVeyor because of update in conda-build
* [PR 3248](https://github.com/spyder-ide/spyder/pull/3248) - Fix heartbeat in introspection client/server
* [PR 3240](https://github.com/spyder-ide/spyder/pull/3240) - Improve sorting in dataframe editor
* [PR 3235](https://github.com/spyder-ide/spyder/pull/3235) - Fix several problems with our shortcuts system
* [PR 3234](https://github.com/spyder-ide/spyder/pull/3234) - Create only one instance of IntrospectionManager for the application
* [PR 3233](https://github.com/spyder-ide/spyder/pull/3233) - Fixes for qtpy 1.1.0
* [PR 3228](https://github.com/spyder-ide/spyder/pull/3228) - Fix a bug preventing Spyder to open external file In Mac application 
* [PR 3227](https://github.com/spyder-ide/spyder/pull/3227) - Fix keyboard interrupt handling in plugin_server.py
* [PR 3222](https://github.com/spyder-ide/spyder/pull/3222) - Variable explorer: Disregard list1 when sorting list1 against list2
* [PR 3218](https://github.com/spyder-ide/spyder/pull/3218) - PR: Allow empty wdir option to run_python_script_in_terminal
* [PR 3217](https://github.com/spyder-ide/spyder/pull/3217) - Fix icon name in conda windows build script.
* [PR 3210](https://github.com/spyder-ide/spyder/pull/3210) - PR: Follow the Flask plugin model instead of namespace packages
* [PR 3209](https://github.com/spyder-ide/spyder/pull/3209) - Fix undefined `backends` when starting IPython kernel
* [PR 3190](https://github.com/spyder-ide/spyder/pull/3190) - Fix small Explorer bugs about file operations
* [PR 3177](https://github.com/spyder-ide/spyder/pull/3177) - PR: Fix automatic insertion of colon
* [PR 3174](https://github.com/spyder-ide/spyder/pull/3174) - PR: Fix tutorial images on Windows
* [PR 3095](https://github.com/spyder-ide/spyder/pull/3095) - Add some indentation tests
* [PR 3024](https://github.com/spyder-ide/spyder/pull/3024) - Added QMutex protection to write_output in Python consoles to avoid crashes when writing long outputs

In this release 25 pull requests were merged


----


## Version 3.0beta3 (2016-06-06)

### Bugfixes

**Issues**

* [Issue 3145](https://github.com/spyder-ide/spyder/issues/3145) - Spyder doesn't work with Qt 5.6
* [Issue 3129](https://github.com/spyder-ide/spyder/issues/3129) - Is there a way to modify the main window title?
* [Issue 3122](https://github.com/spyder-ide/spyder/issues/3122) - Test array builder widget
* [Issue 3115](https://github.com/spyder-ide/spyder/issues/3115) - Automatically advance to the next line after pressing F9
* [Issue 3113](https://github.com/spyder-ide/spyder/issues/3113) - Cannot change font or font size
* [Issue 3112](https://github.com/spyder-ide/spyder/issues/3112) - Cannot open preferences dialog because of missing PYQT5 constant
* [Issue 3101](https://github.com/spyder-ide/spyder/issues/3101) - Migrate to qtpy
* [Issue 3100](https://github.com/spyder-ide/spyder/issues/3100) - Migrate to qtpy: Remove internal Qt shim used by Spyder.
* [Issue 3084](https://github.com/spyder-ide/spyder/issues/3084) - Variable Explorer generates an error while editing a DataFrame
* [Issue 3078](https://github.com/spyder-ide/spyder/issues/3078) - (I)Python consoles are not setting PyQt API to #2
* [Issue 3073](https://github.com/spyder-ide/spyder/issues/3073) - Spyder doesn't work with QtWebEngine
* [Issue 3061](https://github.com/spyder-ide/spyder/issues/3061) - Different output for internal and external console on Windows
* [Issue 3053](https://github.com/spyder-ide/spyder/issues/3053) - Ctrl+I doesn't seem to work on the editor on current tree on Windows 
* [Issue 3041](https://github.com/spyder-ide/spyder/issues/3041) - Spyder crash with "too many files open" message
* [Issue 3033](https://github.com/spyder-ide/spyder/issues/3033) - Create a Remote Procedure Call helper
* [Issue 3022](https://github.com/spyder-ide/spyder/issues/3022) - Turn off module completion fallback
* [Issue 3021](https://github.com/spyder-ide/spyder/issues/3021) - Ghost completions
* [Issue 3013](https://github.com/spyder-ide/spyder/issues/3013) - "Goto definition" stopped working (3.0.0b2 Mac)
* [Issue 3009](https://github.com/spyder-ide/spyder/issues/3009) - Spyder crashes with Python 3.5 and pyqt4 if there are no existing configuration files
* [Issue 3000](https://github.com/spyder-ide/spyder/issues/3000) - Shortcuts: reset console / empty namespace
* [Issue 2986](https://github.com/spyder-ide/spyder/issues/2986) - Add context menu option for %reset
* [Issue 2968](https://github.com/spyder-ide/spyder/issues/2968) - Variable explorer gives an error when copying values
* [Issue 2912](https://github.com/spyder-ide/spyder/issues/2912) - Change keybinding for re-running last script
* [Issue 2910](https://github.com/spyder-ide/spyder/issues/2910) - Automatically set working directory in console
* [Issue 2900](https://github.com/spyder-ide/spyder/issues/2900) - 'Commit' command in File explorer not working in Spyder 3.0.0b2
* [Issue 2877](https://github.com/spyder-ide/spyder/issues/2877) - path module not available in 3.0.0b2
* [Issue 2853](https://github.com/spyder-ide/spyder/issues/2853) - Set all fonts to be one and only one for all plugins in spyder
* [Issue 2835](https://github.com/spyder-ide/spyder/issues/2835) - Control+C should not copy if it has nothing selected on the editor
* [Issue 2724](https://github.com/spyder-ide/spyder/issues/2724) - Editor very slow on Mac Yosemite and El Capitan
* [Issue 2703](https://github.com/spyder-ide/spyder/issues/2703) - File in Project Explorer is being executed(?) on dbl-click
* [Issue 2619](https://github.com/spyder-ide/spyder/issues/2619) - Spyder fails to start on light mode because of check_updates code
* [Issue 2438](https://github.com/spyder-ide/spyder/issues/2438) - Use a single font for all panes
* [Issue 2407](https://github.com/spyder-ide/spyder/issues/2407) - very slow auto completion with pandas
* [Issue 2376](https://github.com/spyder-ide/spyder/issues/2376) - Rename Object Inspector plug-in
* [Issue 2354](https://github.com/spyder-ide/spyder/issues/2354) - Context menu for tabs in editor should allow "close all but this" and "close all to the right"
* [Issue 2268](https://github.com/spyder-ide/spyder/issues/2268) - Start testing with pytest/pytest-qt and coverage for Spyder
* [Issue 1996](https://github.com/spyder-ide/spyder/issues/1996) - Unable to change the interface colors despite saving them in the preferences.
* [Issue 1750](https://github.com/spyder-ide/spyder/issues/1750) - Fail to do automatic indentation after comments
* [Issue 1730](https://github.com/spyder-ide/spyder/issues/1730) - 2 or 4 spaces, not 3
* [Issue 820](https://github.com/spyder-ide/spyder/issues/820) - Move all color-related options into Preferences -> Color scheme

In this release 40 issues were closed

**Pull requests**

* [PR 3204](https://github.com/spyder-ide/spyder/pull/3204) - Make "Spyder 3" the default icon theme
* [PR 3201](https://github.com/spyder-ide/spyder/pull/3201) - Fix AppVeyor failures
* [PR 3198](https://github.com/spyder-ide/spyder/pull/3198) - Support PyQt 5.6
* [PR 3151](https://github.com/spyder-ide/spyder/pull/3151) - More robust plugin initialization in layout
* [PR 3146](https://github.com/spyder-ide/spyder/pull/3146) - Editor: Move to next line in run_selection() if nothing selected
* [PR 3133](https://github.com/spyder-ide/spyder/pull/3133) - Add an option to set window title to the command line
* [PR 3120](https://github.com/spyder-ide/spyder/pull/3120) - PR: Add pytests for array builder, code coverage and quantified code
* [PR 3119](https://github.com/spyder-ide/spyder/pull/3119) - PR: fix Russian translation
* [PR 3105](https://github.com/spyder-ide/spyder/pull/3105) - Remove our internal Qt shim in favor of QtPy
* [PR 3098](https://github.com/spyder-ide/spyder/pull/3098) - PR: Migrate to qtpy
* [PR 3086](https://github.com/spyder-ide/spyder/pull/3086) - Fix interrupt handling on Windows
* [PR 3072](https://github.com/spyder-ide/spyder/pull/3072) - Added Russian translation. Updated POT file
* [PR 3062](https://github.com/spyder-ide/spyder/pull/3062) - Fix consoles encoding in Python 3
* [PR 3060](https://github.com/spyder-ide/spyder/pull/3060) - Start testing with Qt5 on Windows
* [PR 3049](https://github.com/spyder-ide/spyder/pull/3049) - Implement a new Async Server approach based on pyzmq to get completions on the Editor
* [PR 3043](https://github.com/spyder-ide/spyder/pull/3043) - Copying when nothing is selected no longer affects the clipboard.
* [PR 3036](https://github.com/spyder-ide/spyder/pull/3036) - PR: Improve Syntax Coloring preferences page and set color scheme for all plugins there
* [PR 3035](https://github.com/spyder-ide/spyder/pull/3035) - PR: Remove font groups from plugins and move to general preferences
* [PR 3034](https://github.com/spyder-ide/spyder/pull/3034) - Report missing hard dependencies after startup
* [PR 3032](https://github.com/spyder-ide/spyder/pull/3032) - Fix errant completions
* [PR 3029](https://github.com/spyder-ide/spyder/pull/3029) - Add shebang line to default template.py
* [PR 3023](https://github.com/spyder-ide/spyder/pull/3023) - Fix bug in get encoding from "coding" comment line
* [PR 3018](https://github.com/spyder-ide/spyder/pull/3018) - PR: Remove Jedi special code in tests and other minor fixes
* [PR 3015](https://github.com/spyder-ide/spyder/pull/3015) - Editor: Fix code completions when working with bootstrap
* [PR 2997](https://github.com/spyder-ide/spyder/pull/2997) - Added context menu option to reset IPython namespace
* [PR 2974](https://github.com/spyder-ide/spyder/pull/2974) - Center cell icon
* [PR 2973](https://github.com/spyder-ide/spyder/pull/2973) - PR: Show all supported text files when opening files with "File > Open"
* [PR 2971](https://github.com/spyder-ide/spyder/pull/2971) - Make run-cell icons pixel-perfect
* [PR 2957](https://github.com/spyder-ide/spyder/pull/2957) - PR: Select the word under cursor if nothing is selected in Find/Replace
* [PR 2955](https://github.com/spyder-ide/spyder/pull/2955) - PR: Make backspace move to parent directory in file explorer
* [PR 2952](https://github.com/spyder-ide/spyder/pull/2952) - PR: Enable 'Save All' if there are files to be saved
* [PR 2939](https://github.com/spyder-ide/spyder/pull/2939) - PR: More accurate test for text-like files
* [PR 2935](https://github.com/spyder-ide/spyder/pull/2935) - PR: Improving Spyder 3 icon theme
* [PR 2932](https://github.com/spyder-ide/spyder/pull/2932) - PR: Asynchronous introspection for the Editor
* [PR 2930](https://github.com/spyder-ide/spyder/pull/2930) - PR: fix not decorated slots connected to 'triggered' and 'clicked' signals
* [PR 2929](https://github.com/spyder-ide/spyder/pull/2929) - Hide Help plugin if Sphinx is not installed
* [PR 2919](https://github.com/spyder-ide/spyder/pull/2919) - PR: Synchronize entry in Working Directory toolbar with console's current working directory
* [PR 2917](https://github.com/spyder-ide/spyder/pull/2917) - PR: Create a new module called app and move there all modules related to our application
* [PR 2913](https://github.com/spyder-ide/spyder/pull/2913) - Move to use Jupyter imports and remove support for IPython 3
* [PR 2897](https://github.com/spyder-ide/spyder/pull/2897) - Fixed typos (thanks to Benjamin Weis)
* [PR 2890](https://github.com/spyder-ide/spyder/pull/2890) - Added .idea folder to .gitignore for PyCharm users
* [PR 2888](https://github.com/spyder-ide/spyder/pull/2888) - Add 3,5,6,7,8 spaces as options in indentation of the Editor
* [PR 2886](https://github.com/spyder-ide/spyder/pull/2886) - Remove official support for PySide
* [PR 2881](https://github.com/spyder-ide/spyder/pull/2881) - PR: Crashing on shortcut assignment with PyQt5
* [PR 2879](https://github.com/spyder-ide/spyder/pull/2879) - Use PyQt5 as default API
* [PR 2874](https://github.com/spyder-ide/spyder/pull/2874) - Remove light mode
* [PR 2873](https://github.com/spyder-ide/spyder/pull/2873) - Rename Object Inspector plugin to Help
* [PR 2669](https://github.com/spyder-ide/spyder/pull/2669) - PR: Use pygments in introspection
* [PR 2519](https://github.com/spyder-ide/spyder/pull/2519) - Add "close all but this" and "close all to the right" entries to the Editor context menu
* [PR 2184](https://github.com/spyder-ide/spyder/pull/2184) - Prevent cmd.exe shell windows popping up in the background when calling subprocess

In this release 50 pull requests were merged


----


## Version 3.0beta1/beta2 (2016-12-11)

### Bugfixes

**Issues**

* [Issue 2852](https://github.com/spyder-ide/spyder/issues/2852) - Create conda.recipe folder at repo level
* [Issue 2836](https://github.com/spyder-ide/spyder/issues/2836) - Dicom plugin error in bootstrap.py
* [Issue 2795](https://github.com/spyder-ide/spyder/issues/2795) - Option  'Automatic insertion of parentheses, braces and brackets' has issues when un-checked
* [Issue 2792](https://github.com/spyder-ide/spyder/issues/2792) - Changing IPython graphics backend to "Qt" will result in error when using Qt5
* [Issue 2788](https://github.com/spyder-ide/spyder/issues/2788) - Plots are requiring a Ctrl+C in the Python console when using the Qt4 backend on Windows
* [Issue 2779](https://github.com/spyder-ide/spyder/issues/2779) - Bundled rope version is causing Spyder to crash
* [Issue 2766](https://github.com/spyder-ide/spyder/issues/2766) - fix ArrayEditor under PyQt5
* [Issue 2763](https://github.com/spyder-ide/spyder/issues/2763) - Release 3.0 with PyQt5 as default
* [Issue 2756](https://github.com/spyder-ide/spyder/issues/2756) - fallback_plugin tests are failing
* [Issue 2748](https://github.com/spyder-ide/spyder/issues/2748) - Spyder freezes when large MaskedArrays are in memory
* [Issue 2737](https://github.com/spyder-ide/spyder/issues/2737) - UI issues with collapse/expand in the profiler
* [Issue 2736](https://github.com/spyder-ide/spyder/issues/2736) - Profiler config does not carry command line arguments correctly
* [Issue 2685](https://github.com/spyder-ide/spyder/issues/2685) - "unable to connect to the internet" nag screen in 3.0.0b1
* [Issue 2677](https://github.com/spyder-ide/spyder/issues/2677) - Autocomplete for working directory widget
* [Issue 2674](https://github.com/spyder-ide/spyder/issues/2674) - Add run cell (and run cell advance) to right click prompt
* [Issue 2672](https://github.com/spyder-ide/spyder/issues/2672) - Autocomplete does not insert correct word when requested with Ctrl+Space
* [Issue 2612](https://github.com/spyder-ide/spyder/issues/2612) - Fix version detection on the Dependencies dialog
* [Issue 2598](https://github.com/spyder-ide/spyder/issues/2598) - Cannot change between UI tabs on OSX
* [Issue 2597](https://github.com/spyder-ide/spyder/issues/2597) - new icon theme broken on OSX
* [Issue 2581](https://github.com/spyder-ide/spyder/issues/2581) - Autoparens appear when autocompleting in the import section
* [Issue 2574](https://github.com/spyder-ide/spyder/issues/2574) - Create wheels for Spyder
* [Issue 2573](https://github.com/spyder-ide/spyder/issues/2573) - Spyder is crashing with PyQt5.5.0 on Windows / Python 3.4
* [Issue 2569](https://github.com/spyder-ide/spyder/issues/2569) - Spyper cannot read yahoo stock price
* [Issue 2555](https://github.com/spyder-ide/spyder/issues/2555) - Main window is bigger than screen size, after a first start in Mac and KDE
* [Issue 2527](https://github.com/spyder-ide/spyder/issues/2527) - More suggestions for the "Spyder 3" icon theme
* [Issue 2481](https://github.com/spyder-ide/spyder/issues/2481) - Align boxes for different lines in preferences dialog
* [Issue 2471](https://github.com/spyder-ide/spyder/issues/2471) - Matplotlib Gtk backend is broken in Python consoles
* [Issue 2439](https://github.com/spyder-ide/spyder/issues/2439) - Rope not autocompleting when *args or **kwargs are present in function definition
* [Issue 2436](https://github.com/spyder-ide/spyder/issues/2436) - Background coloring in array view (variable explorer) doesn't work if array contains nans
* [Issue 2433](https://github.com/spyder-ide/spyder/issues/2433) - Argument cannot work in Spyder 2.3.4
* [Issue 2427](https://github.com/spyder-ide/spyder/issues/2427) - can't find pylint installed as python3-pylint
* [Issue 2422](https://github.com/spyder-ide/spyder/issues/2422) - Selecting line numbers from the side areas with pointer potentially buggy?
* [Issue 2420](https://github.com/spyder-ide/spyder/issues/2420) - Zoom should not be associated with a file
* [Issue 2408](https://github.com/spyder-ide/spyder/issues/2408) - Exception on autocomplete in the internal console
* [Issue 2404](https://github.com/spyder-ide/spyder/issues/2404) - Code completion raise exception when the editor widget is floating
* [Issue 2401](https://github.com/spyder-ide/spyder/issues/2401) - Unable to reset settings from the Main Window
* [Issue 2395](https://github.com/spyder-ide/spyder/issues/2395) - Can not show exception information correctly in IPython Console
* [Issue 2390](https://github.com/spyder-ide/spyder/issues/2390) - Code completion is failing on Python consoles
* [Issue 2389](https://github.com/spyder-ide/spyder/issues/2389) - Move helper widgets to helperwidgets.py
* [Issue 2386](https://github.com/spyder-ide/spyder/issues/2386) - Error in Python console on startup
* [Issue 2385](https://github.com/spyder-ide/spyder/issues/2385) - Can't report issue on master with PyQt5
* [Issue 2381](https://github.com/spyder-ide/spyder/issues/2381) - Disable post-crash popup in dev mode
* [Issue 2379](https://github.com/spyder-ide/spyder/issues/2379) - Spyder can't switch lines of code when those two lines are the last two in the file
* [Issue 2352](https://github.com/spyder-ide/spyder/issues/2352) - Some issues with code completion in the Editor
* [Issue 2348](https://github.com/spyder-ide/spyder/issues/2348) - Combobox to choose Matplotlib backend
* [Issue 2347](https://github.com/spyder-ide/spyder/issues/2347) - Add shortcuts to move to next/previous line in the Editor
* [Issue 2340](https://github.com/spyder-ide/spyder/issues/2340) - SublimeText-like file switching widget
* [Issue 2317](https://github.com/spyder-ide/spyder/issues/2317) - Object Inspector Text on Mac OS X is Misleading
* [Issue 2313](https://github.com/spyder-ide/spyder/issues/2313) - 'NoneType' is not iterable in introspection/fallback_plugin.py
* [Issue 2308](https://github.com/spyder-ide/spyder/issues/2308) - Python console stops running after first execution
* [Issue 2307](https://github.com/spyder-ide/spyder/issues/2307) - Enhancement: Add check for updates and allow for autoupdating inside spyder
* [Issue 2306](https://github.com/spyder-ide/spyder/issues/2306) - Enhancement: Add restart functionality to spyder.
* [Issue 2305](https://github.com/spyder-ide/spyder/issues/2305) - Profiling error
* [Issue 2300](https://github.com/spyder-ide/spyder/issues/2300) - Unable to start my Spyder
* [Issue 2289](https://github.com/spyder-ide/spyder/issues/2289) - Disable icons in menus on Mac OS X
* [Issue 2282](https://github.com/spyder-ide/spyder/issues/2282) - Incorrect setting of Qt API n°2
* [Issue 2277](https://github.com/spyder-ide/spyder/issues/2277) - "TypeError: decoding Unicode is not supported" when debugging
* [Issue 2275](https://github.com/spyder-ide/spyder/issues/2275) - Can not report issue from dev version
* [Issue 2274](https://github.com/spyder-ide/spyder/issues/2274) - Can not start spyder under python2 because guidata doesn't support PyQt5
* [Issue 2267](https://github.com/spyder-ide/spyder/issues/2267) - Move Conda Package Manager to its own repo
* [Issue 2251](https://github.com/spyder-ide/spyder/issues/2251) - Spyder crashing on very long output
* [Issue 2250](https://github.com/spyder-ide/spyder/issues/2250) - IPython 3.0 is showing a deprecation warning in the Internal Console
* [Issue 2249](https://github.com/spyder-ide/spyder/issues/2249) - TypeError: 'method' object is not connected: self.timer.timeout.disconnect(self.show_time)
* [Issue 2248](https://github.com/spyder-ide/spyder/issues/2248) - ImportError: No module named 'conda_api_q'
* [Issue 2235](https://github.com/spyder-ide/spyder/issues/2235) - Error when running Spyder with Python 2 and PyQt5
* [Issue 2231](https://github.com/spyder-ide/spyder/issues/2231) - Master has issues when plotting graphs through matplotlib in Python consoles
* [Issue 2213](https://github.com/spyder-ide/spyder/issues/2213) - Show absolute and relative (to the current file in Editor) images in Object inspector
* [Issue 2210](https://github.com/spyder-ide/spyder/issues/2210) - Icons as vector graphics to support retina displays
* [Issue 2204](https://github.com/spyder-ide/spyder/issues/2204) - Windows: something is preventing "File" and "Edit" menus being clicked
* [Issue 2141](https://github.com/spyder-ide/spyder/issues/2141) - File list management broken in master
* [Issue 2125](https://github.com/spyder-ide/spyder/issues/2125) - Removal of keyboard shortcut causes errors to be thrown
* [Issue 2117](https://github.com/spyder-ide/spyder/issues/2117) - Add missing methods to SpyderPluginMixin
* [Issue 2096](https://github.com/spyder-ide/spyder/issues/2096) - Feature Request: Add option to lock window/pane layout
* [Issue 2083](https://github.com/spyder-ide/spyder/issues/2083) - Spyder stopped working with Qt4.6
* [Issue 2061](https://github.com/spyder-ide/spyder/issues/2061) - Spyder cannot load matplotlib if the latter tries to use PyQt5
* [Issue 2047](https://github.com/spyder-ide/spyder/issues/2047) - Provide Keyboard Shortcut for Save As
* [Issue 2024](https://github.com/spyder-ide/spyder/issues/2024) - Add folders with subfolders with path manager
* [Issue 2010](https://github.com/spyder-ide/spyder/issues/2010) - runfile arguments with spaces
* [Issue 2001](https://github.com/spyder-ide/spyder/issues/2001) - inserting line break in code line does not align well on next line
* [Issue 1966](https://github.com/spyder-ide/spyder/issues/1966) - Add fallback syntax highlighter using Pygments autodetection
* [Issue 1940](https://github.com/spyder-ide/spyder/issues/1940) - Add search functionality for keyboard shortcuts
* [Issue 1924](https://github.com/spyder-ide/spyder/issues/1924) - Add interactive tutorials
* [Issue 1923](https://github.com/spyder-ide/spyder/issues/1923) - Bug when changing output and input prompts in the IPython console
* [Issue 1876](https://github.com/spyder-ide/spyder/issues/1876) - Editor: Move suggested completion item to top of window
* [Issue 1850](https://github.com/spyder-ide/spyder/issues/1850) - Calltip traceback while using Jedi
* [Issue 1761](https://github.com/spyder-ide/spyder/issues/1761) - F5 (run) saves editor file, but F10 (profile) does not
* [Issue 1749](https://github.com/spyder-ide/spyder/issues/1749) - Cycle tabs via Ctrl-PageUp/PageDown
* [Issue 1394](https://github.com/spyder-ide/spyder/issues/1394) - Let the user select his/her own localization settings
* [Issue 1387](https://github.com/spyder-ide/spyder/issues/1387) - Integrate post mortem debugging (like IEP)
* [Issue 1335](https://github.com/spyder-ide/spyder/issues/1335) - Add option for naming the custom layouts
* [Issue 1239](https://github.com/spyder-ide/spyder/issues/1239) - Include a package manager
* [Issue 1221](https://github.com/spyder-ide/spyder/issues/1221) - Spyder doesn't use Native OS X fullscreen
* [Issue 1212](https://github.com/spyder-ide/spyder/issues/1212) - Add keyboard shortcuts for beginning of line and end of line
* [Issue 1001](https://github.com/spyder-ide/spyder/issues/1001) - How to change UI language
* [Issue 729](https://github.com/spyder-ide/spyder/issues/729) - Enable assigning shortcuts for cursor navigation on the Editor
* [Issue 494](https://github.com/spyder-ide/spyder/issues/494) - Need to hit Enter to change a keyboard shortcut (unintuitive)
* [Issue 478](https://github.com/spyder-ide/spyder/issues/478) - Slash does not work as keyboard shortcut key
* [Issue 404](https://github.com/spyder-ide/spyder/issues/404) - Spyder becomes unresponsive while loading a large source file
* [Issue 195](https://github.com/spyder-ide/spyder/issues/195) - Backspace (\b) and carriage return (\r) characters are not printed correctly in the console

In this release 99 issues were closed

**Pull requests**

* [PR 2847](https://github.com/spyder-ide/spyder/pull/2847) - Use High dpi pixmaps
* [PR 2838](https://github.com/spyder-ide/spyder/pull/2838) - Import spyplugins only if there's a valid spec/module
* [PR 2831](https://github.com/spyder-ide/spyder/pull/2831) - Remove external dependencies
* [PR 2826](https://github.com/spyder-ide/spyder/pull/2826) - Remove imports from widgets/__init__ because they are making Spyder crash
* [PR 2825](https://github.com/spyder-ide/spyder/pull/2825) - Fix tests in Travis after a recent update of conda-build
* [PR 2813](https://github.com/spyder-ide/spyder/pull/2813) - Test spyplugins widgets on AppVeyor and other minor fixes
* [PR 2810](https://github.com/spyder-ide/spyder/pull/2810) - Restore the insertion of the "(" character when parameter close_parentheses_enabled is False
* [PR 2808](https://github.com/spyder-ide/spyder/pull/2808) - Make F10 (profile) save the current file before running
* [PR 2800](https://github.com/spyder-ide/spyder/pull/2800) - Fix problems in AppVeyor and Travis
* [PR 2786](https://github.com/spyder-ide/spyder/pull/2786) - Move the spyder script to the right place if it isn't present in the site Scripts directory
* [PR 2784](https://github.com/spyder-ide/spyder/pull/2784) - Fix runfile argument parsing error by using shlex
* [PR 2778](https://github.com/spyder-ide/spyder/pull/2778) - Use Appveyor to test on Windows
* [PR 2777](https://github.com/spyder-ide/spyder/pull/2777) - Fix important errors in Travis
* [PR 2776](https://github.com/spyder-ide/spyder/pull/2776) - Rename spyderlib.widgets.editors to spyderlib.widgets.variableexplorer
* [PR 2774](https://github.com/spyder-ide/spyder/pull/2774) - Add dependencies to pip
* [PR 2767](https://github.com/spyder-ide/spyder/pull/2767) - Fix arrayeditor import error in PyQt5
* [PR 2762](https://github.com/spyder-ide/spyder/pull/2762) - Start testing with PyQt5
* [PR 2761](https://github.com/spyder-ide/spyder/pull/2761) - Test Spyder with Python 3.5
* [PR 2758](https://github.com/spyder-ide/spyder/pull/2758) - Fix failing fallback_plugin tests and add to modules_test
* [PR 2752](https://github.com/spyder-ide/spyder/pull/2752) - Test widgets in Travis
* [PR 2750](https://github.com/spyder-ide/spyder/pull/2750) - Improved copying and selection behaviour of array editor
* [PR 2747](https://github.com/spyder-ide/spyder/pull/2747) - Don't use bootstrap on Travis
* [PR 2746](https://github.com/spyder-ide/spyder/pull/2746) - Move Variable Explorer widgets and utility libraries to its own namespace: widgets/varexp
* [PR 2741](https://github.com/spyder-ide/spyder/pull/2741) - Get rid of the last shim warning with IPython/Jupyter 4
* [PR 2740](https://github.com/spyder-ide/spyder/pull/2740) - Read correctly the run config for profiling
* [PR 2739](https://github.com/spyder-ide/spyder/pull/2739) - Fix collapse/expand buttons in profiler widget
* [PR 2718](https://github.com/spyder-ide/spyder/pull/2718) - Fix issue with qtawesome fonts not rendering on OS X
* [PR 2702](https://github.com/spyder-ide/spyder/pull/2702) - Fix tabbar issue in OSX
* [PR 2692](https://github.com/spyder-ide/spyder/pull/2692) - Add tab completions for PathCombobox
* [PR 2691](https://github.com/spyder-ide/spyder/pull/2691) - Fixed PyQt5 detection without QT_API env var
* [PR 2687](https://github.com/spyder-ide/spyder/pull/2687) - Opt out of certificate verification on check for updates
* [PR 2673](https://github.com/spyder-ide/spyder/pull/2673) - Fix single item completion
* [PR 2671](https://github.com/spyder-ide/spyder/pull/2671) - Test module importing on Travis
* [PR 2602](https://github.com/spyder-ide/spyder/pull/2602) - Revert auto open parens on completion
* [PR 2594](https://github.com/spyder-ide/spyder/pull/2594) - Import HelperToolButton from helperwidgets.py in arraybuilder
* [PR 2590](https://github.com/spyder-ide/spyder/pull/2590) - Redesign file switcher (a la Sublime Text)
* [PR 2587](https://github.com/spyder-ide/spyder/pull/2587) - Homogenize History Pane UI
* [PR 2585](https://github.com/spyder-ide/spyder/pull/2585) - Homogenize Object inspector UI
* [PR 2584](https://github.com/spyder-ide/spyder/pull/2584) - Homogenize variable explorer UI
* [PR 2583](https://github.com/spyder-ide/spyder/pull/2583) - Homogenize file explorer UI
* [PR 2582](https://github.com/spyder-ide/spyder/pull/2582) - Move MessageCheckBox widget from workers to helperwidgets.py
* [PR 2577](https://github.com/spyder-ide/spyder/pull/2577) - Make "copy" work better with numpy arrays
* [PR 2576](https://github.com/spyder-ide/spyder/pull/2576) - Fix issues in Python3/PyQt5.5
* [PR 2575](https://github.com/spyder-ide/spyder/pull/2575) - Reorganize repo: grouped config files inside spyderlib/config
* [PR 2565](https://github.com/spyder-ide/spyder/pull/2565) - Change plugins directory to spyplugins and make it a namespace package
* [PR 2559](https://github.com/spyder-ide/spyder/pull/2559) - Fix default layout dockwidget on first Spyder start
* [PR 2547](https://github.com/spyder-ide/spyder/pull/2547) - Fix resetting IPython custom exception hook
* [PR 2537](https://github.com/spyder-ide/spyder/pull/2537) - fix misspelled extension
* [PR 2533](https://github.com/spyder-ide/spyder/pull/2533) - Spyder 3 icon theme changes
* [PR 2523](https://github.com/spyder-ide/spyder/pull/2523) - Keyboard shortcut editor enhancements
* [PR 2511](https://github.com/spyder-ide/spyder/pull/2511) - New Spyder 3 icons for run-cell and run-cell inplace
* [PR 2504](https://github.com/spyder-ide/spyder/pull/2504) - Update Spyder 3 icon theme: vertical alignment of maximize/unmaximize
* [PR 2501](https://github.com/spyder-ide/spyder/pull/2501) - Make blank space less apparent.
* [PR 2492](https://github.com/spyder-ide/spyder/pull/2492) - proof read tutorial.rst and removed several typos
* [PR 2489](https://github.com/spyder-ide/spyder/pull/2489) - Remove warning message associated to language on Linux
* [PR 2488](https://github.com/spyder-ide/spyder/pull/2488) - Improve appearance of options inside the preferences dialog
* [PR 2480](https://github.com/spyder-ide/spyder/pull/2480) - Enable standard icons
* [PR 2457](https://github.com/spyder-ide/spyder/pull/2457) - Return default language in case no locale is found
* [PR 2445](https://github.com/spyder-ide/spyder/pull/2445) - Fix handling of jedi completions for jedi 0.9
* [PR 2426](https://github.com/spyder-ide/spyder/pull/2426) - Add option to toggle toolbars visibility
* [PR 2425](https://github.com/spyder-ide/spyder/pull/2425) - Add option in preferences to show/hide status bar
* [PR 2423](https://github.com/spyder-ide/spyder/pull/2423) - Reset spyder and restart from within running application
* [PR 2412](https://github.com/spyder-ide/spyder/pull/2412) - Open preferences dialog even if a plugin raises errors
* [PR 2410](https://github.com/spyder-ide/spyder/pull/2410) - Print git revision and branch in bootstrap.py instead of mercurial
* [PR 2409](https://github.com/spyder-ide/spyder/pull/2409) - Fix error when trying an empty complete in internal console
* [PR 2405](https://github.com/spyder-ide/spyder/pull/2405) - Avoid exception when the Editor is floating and users are trying to get completions
* [PR 2391](https://github.com/spyder-ide/spyder/pull/2391) - Fix #2390, completions in python console
* [PR 2382](https://github.com/spyder-ide/spyder/pull/2382) - Allow the last two lines in a file to be switched
* [PR 2371](https://github.com/spyder-ide/spyder/pull/2371) - Automatically add parens for function completions
* [PR 2369](https://github.com/spyder-ide/spyder/pull/2369) - Add drag support for dockwidgets sharing same position
* [PR 2367](https://github.com/spyder-ide/spyder/pull/2367) - New KeySequence Editor for Keyboard Shortcut Preferences
* [PR 2366](https://github.com/spyder-ide/spyder/pull/2366) - Update Path.py to version 7.3
* [PR 2357](https://github.com/spyder-ide/spyder/pull/2357) - Fix some completion issues on the Editor (issue #2352)
* [PR 2349](https://github.com/spyder-ide/spyder/pull/2349) - Add support for language selection in preferences
* [PR 2345](https://github.com/spyder-ide/spyder/pull/2345) - Add lock/unlock option for panes
* [PR 2337](https://github.com/spyder-ide/spyder/pull/2337) - Add Icons to Completions
* [PR 2331](https://github.com/spyder-ide/spyder/pull/2331) - Finish Introduction tour
* [PR 2328](https://github.com/spyder-ide/spyder/pull/2328) - README.md running from source is a killer feature
* [PR 2322](https://github.com/spyder-ide/spyder/pull/2322) - Make completions scroll to top of list
* [PR 2321](https://github.com/spyder-ide/spyder/pull/2321) - Add a check for updates method
* [PR 2319](https://github.com/spyder-ide/spyder/pull/2319) - Handle a connection abort error on shutdown
* [PR 2318](https://github.com/spyder-ide/spyder/pull/2318) - Fix Object inspector message for OSX
* [PR 2316](https://github.com/spyder-ide/spyder/pull/2316) - Use empty string instead of None for fallback.  Fixes #2313.
* [PR 2312](https://github.com/spyder-ide/spyder/pull/2312) - Fixes #2306: Add a restart method
* [PR 2309](https://github.com/spyder-ide/spyder/pull/2309) - Replace obsolete setTextColor method by setForeground in qtreewidgetitem
* [PR 2301](https://github.com/spyder-ide/spyder/pull/2301) - Run selection enabled even with empty selection
* [PR 2295](https://github.com/spyder-ide/spyder/pull/2295) - Update CHANGELOG.md
* [PR 2291](https://github.com/spyder-ide/spyder/pull/2291) - Add "func" to enaml highlighter
* [PR 2286](https://github.com/spyder-ide/spyder/pull/2286) - Setting Qt API n°2 for all supported objects
* [PR 2281](https://github.com/spyder-ide/spyder/pull/2281) - Add travis support for basic start of spyder
* [PR 2260](https://github.com/spyder-ide/spyder/pull/2260) - New set of icons based on FontAwesome
* [PR 2253](https://github.com/spyder-ide/spyder/pull/2253) - Try to avoid crashes on long output into Python console in a short time
* [PR 2243](https://github.com/spyder-ide/spyder/pull/2243) - Don't add invalid paths to IMG_PATH
* [PR 2237](https://github.com/spyder-ide/spyder/pull/2237) - Changed the IPython completion option from a checkbox to a combobox
* [PR 2226](https://github.com/spyder-ide/spyder/pull/2226) - Add PyQt5 to Qt binding choices for Python consoles
* [PR 2222](https://github.com/spyder-ide/spyder/pull/2222) - Update pep8 version shipped with spyder from 1.4.6 to 1.6.2
* [PR 2218](https://github.com/spyder-ide/spyder/pull/2218) - Update AUTHORS
* [PR 2217](https://github.com/spyder-ide/spyder/pull/2217) - Keybinding Enhancements
* [PR 2208](https://github.com/spyder-ide/spyder/pull/2208) - Fix issue 2204 in tour - blocking file and edit menu
* [PR 2205](https://github.com/spyder-ide/spyder/pull/2205) - Added Brazilian Portuguese translation
* [PR 2202](https://github.com/spyder-ide/spyder/pull/2202) - Allow tab cycling with ctrl+pageup/down
* [PR 2198](https://github.com/spyder-ide/spyder/pull/2198) - Fill in missing global run config options
* [PR 2189](https://github.com/spyder-ide/spyder/pull/2189) - Provide a base implementation for closing_plugin

In this release 103 pull requests were merged


----


## Version 2.3.9

### New features

* Preferences
    * Fix a crash when using certain versions of colorama (which is a Jedi dependency)
* Python and IPython consoles
    * Filter a RuntimeWarning generated for DataFrames with nan values
* Variable Explorer
    * Fix a freeze when binary strings can't be converted to unicode in Python 2
    * Fix a freeze with Numpy arrays containing strings

### Bug fixes

**Issues**

* [Issue 3067](../../issues/3067) - File left open in sitecustomize when executing it in Python 3
* [Issue 3031](../../issues/3031) - Variable Explorer freezes when certain binary data is loaded
* [Issue 2991](../../issues/2991) - RuntimeWarning with pandas.dataframes that contain np.nan values
* [Issue 2984](../../issues/2984) - Can't access Preferences in spyder
* [Issue 2983](../../issues/2983) - Freeze while assigning data from numpy array when the data is a string

In this release 5 issues were closed


----


## Version 2.3.8

### New features

* Python and IPython consoles
    * Fix a sitecustomize error when using Matplotlib 1.5 with Python 2 on Linux
* Variable Explorer
    * Add support for Pandas Series when using Pandas 0.17+
    * Fix a freeze when creating empty DataFrames in Python 2
    * Fix a freeze when working with big Numpy recarray's
* Under the hood
    * Avoid startup crashes when there are errors importing Numpy, SciPy or Pillow

### Bug fixes

**Issues**

* [Issue 2819](../../issues/2819) - Spyder fails to start because of an error with scipy
* [Issue 2815](../../issues/2815) - Variable explorer is not recognizing Pandas Series objects
* [Issue 2793](../../issues/2793) - Connecting to kernel fails because of update to Matplotlib 1.5
* [Issue 2791](../../issues/2791) - DataFrame with no rows gives error when trying to view it
* [Issue 2783](../../issues/2783) - Spyder freezes on assigning a fits table data
* [Issue 2744](../../issues/2744) - Spyder hangs when creating an empty DataFrame on Python 2

In this release 6 issues were closed


----


## Version 2.3.7

### New features

* Editor
    * Remove support for Jedi 0.9 because it was causing crashes
* Variable Explorer
    * Fix crashes and freezes when working with DataFrames on Python 2
* Under the hodd
    * Restore support for PySide

### Bug fixes

**Issues**

* [Issue 2709](../../issues/2709) - IPython console error when trying to use SymPy
* [Issue 2693](../../issues/2693) - README should link to manual
* [Issue 2689](../../issues/2689) - "Resize" button in variable explorer chops off the array
* [Issue 2684](../../issues/2684) - Applications directory link is broken in Spyder 2.3.6 dmg's
* [Issue 2680](../../issues/2680) - "Close all files" hangs Spyder
* [Issue 2661](../../issues/2661) - Conda package manager is packed in 2.3.6 win32 distribution leading to errors
* [Issue 2659](../../issues/2659) - Crash while getting completions of DataFrames on the Editor because of Jedi 0.9
* [Issue 2654](../../issues/2654) - Creating DataFrames in Python or IPython consoles make Spyder 2.3.6 to hang
* [Issue 2649](../../issues/2649) - PySide can not be used on 2.3.6
* [Issue 2296](../../issues/2296) - Line numbers misaligned when zooming and scrolling in Mac
* [Issue 2036](../../issues/2036) - Code analysis and tooltips are not displayed in Ubuntu

In this release 11 issues were closed

**Pull requests**

* [PR 2650](../../pull/2650) - Failed sip import blocks fallback to PySide

In this release 1 pull requests were merged


----


## Version 2.3.6

### New features

* IPython Console
    * Make it fully compatible with IPython/Jupyter 4.0
* Variable Explorer
    * Don't refresh it when focused to avoid slow downs when working with big data
    * Add variable name to DataFrame editor
    * Fix several crashes and freezes when working with DataFrames
* Under the hood
    * Use PyQt4 API #2 by default (API #1 is not supported anymore). This is necessary to support IPython/Jupyter 4.0

### Bug fixes

**Issues**

* [Issue 2625](../../issues/2625) - Multiple untitled files generate at close
* [Issue 2614](../../issues/2614) - Indenting at the first position in file fails/crashes
* [Issue 2608](../../issues/2608) - Crash after update IPython to 4.0
* [Issue 2596](../../issues/2596) - Call tips and auto completion tips go out of screen on a second monitor
* [Issue 2593](../../issues/2593) - Having a lof of data in the Variable explorer slows down Spyder considerably
* [Issue 2566](../../issues/2566) - Spyder crash on launch with Babel 2.0/Python 3.4
* [Issue 2560](../../issues/2560) - List of pandas dataframes in variable explorer slows down Spyder
* [Issue 2517](../../issues/2517) - Variable explorer auto-refreshes after kernel restarts
* [Issue 2514](../../issues/2514) - DataFrames with headers that contain BOM utf-8 data are freezing/crashing Spyder (in Python 2)
* [Issue 2491](../../issues/2491) - Spyder crashes when displaying DataFrames with duplicate column names in the Variable Explorer
* [Issue 2413](../../issues/2413) - Don't ask to confirm exit on default untitled files
* [Issue 2315](../../issues/2315) - Display object name in DataFrame editor

In this release 12 issues were closed

**Pull requests**

* [PR 2639](../../pull/2639) - Fix missing exception on Windows when importing data on the Variable Explorer
* [PR 2617](../../pull/2617) - Show call tips at right position when there are multiple screens
* [PR 2615](../../pull/2615) - Fix error when indenting on the first line of a file

In this release 3 pull requests were merged

----


## Version 2.3.5.2

**Note**: Versions 2.3.5 and 2.3.5.1 have serious startup bugs on Windows and Mac respectively.
Hence they are not listed here.

### New features

* Editor
    * Add support for Jedi 0.9
* IPython Console
    * Add initial support for IPython/Jupyter 4.0
* Main Window
    * Improve how Spyder looks in MacOS X
    * Several fixes to prevent startup crashes

### Bug fixes

**Issues**

* [Issue 2468](../../issues/2468) - 'Connect to existing kernel' fails if json file not in PWD
* [Issue 2466](../../issues/2466) - No Notification of Running Instance
* [Issue 2463](../../issues/2463) - Failure to preserve Matplotlib backend when using symbolic math
* [Issue 2456](../../issues/2456) - Launching IPython console fails because of errors importing Pandas or Matplotlib
* [Issue 2452](../../issues/2452) - os.system causes TypeError in Python 3
* [Issue 2448](../../issues/2448) - Spyder crashes using Variable Explorer with BeautifulSoup
* [Issue 2446](../../issues/2446) - When importing putting two periods in a row produces an error in a Python console
* [Issue 2363](../../issues/2363) - Spyder fails to start because of problems with lockfile
* [Issue 2356](../../issues/2356) - Block comment incorporating whitespace excludes last line
* [Issue 2341](../../issues/2341) - IPython console: "sre_constants.error: unbalanced parenthesis" while typing
* [Issue 2314](../../issues/2314) - Cell highlighting not updated after closing the FindReplace widget
* [Issue 2302](../../issues/2302) - Closing all files in editor shouldn't leave it empty
* [Issue 2299](../../issues/2299) - IPython preference "Automatically load Pylab and Numpy Modules" not followed
* [Issue 2298](../../issues/2298) - Cannot stop executing when runing a flask app with debug=True
* [Issue 2285](../../issues/2285) - Copying from Spyder and pasting into LibreOffice displays strange comments
* [Issue 2228](../../issues/2228) - Shortcut to run cells on Mac is not working
* [Issue 2188](../../issues/2188) - can't run win_post_install from pip
* [Issue 2171](../../issues/2171) - Spyder Mac apps (for Python 2 and 3) hang on startup with OSX 10.9.5
* [Issue 2028](../../issues/2028) - Background color of theme is not set properly on Mac OSX
* [Issue 1957](../../issues/1957) - Python 3 Mac app can't start Python or IPython consoles
* [Issue 1844](../../issues/1844) - "Set as current console's working directory" button not working on Python 3
* [Issue 1615](../../issues/1615) - Mac app - Matplotlib does not work with Canopy

In this release 22 issues were closed

**Pull requests**

* [PR 2486](../../pull/2486) - Stop using IPython.lib.kernel 0.13.2 shim and add initial support for Jupyter
* [PR 2484](../../pull/2484) - Remove unnecessary changes to detected kernel json file when connecting to external kernels
* [PR 2434](../../pull/2434) - Match for pylint when parsing pylint version
* [PR 2411](../../pull/2411) - Improve github issue template
* [PR 2377](../../pull/2377) - Fix the fact that spyder_win_post_install.py can't be run from pip
* [PR 2293](../../pull/2293) - Hide menu icons on Mac OS X
* [PR 2247](../../pull/2247) - Add support to run Python programs on xfce and xterm external terminals
* [PR 2216](../../pull/2216) - Fix broken png files: libpng 1.6.2 and newer has stricter iCCP rules

In this release 8 pull requests were merged


----


## Version 2.3.4

### New features

* Debugging
    * After pressing the Debug button (or `Ctrl+F5`) move to the first breakpoint
* IPython Console
    * Drop support for Sympy versions less than 0.7.3
* Python Console
    * Remove support to run system commands with ! (like `!diff`)
* Editor
    * Accept drops from compressed files on Windows

### Bug fixes

**Issues**

* [Issue 2259](../../issues/2259) - spyder crashes if ipython installed but not pygments
* [Issue 2257](../../issues/2257) - Cannot plot inline in IPython console on Linux
* [Issue 2252](../../issues/2252) - Update French translations for 2.3.4
* [Issue 2245](../../issues/2245) - Importing a module with debugger causes "TypeError: decoding Unicode is not supported"
* [Issue 2239](../../issues/2239) - SyntaxErrors with Python 3.2
* [Issue 2234](../../issues/2234) - Object Inspector is not showing "No documentation available" for objects without docstring
* [Issue 2227](../../issues/2227) - IPython does not work with brewed or virtualenv Python(s) in MacOSX
* [Issue 2223](../../issues/2223) - Spyder2.3.3 Code completion breaks
* [Issue 2207](../../issues/2207) - Spyder's WM_CLASS is empty, resulting in unexpected behavior for task managers
* [Issue 2203](../../issues/2203) - Code completion issue with Jedi
* [Issue 2197](../../issues/2197) - IPython consoles are not named correctly when connecting to existing kernels and passing the full kernel path
* [Issue 2158](../../issues/2158) - runfile with path containing apostrophes (quotes) will not work
* [Issue 2151](../../issues/2151) - Long NumPy arrays throw off errors
* [Issue 2146](../../issues/2146) - Special character "!" is not processed correctly when debugging in Python consoles
* [Issue 2081](../../issues/2081) - Spyder crashes on Windows because of non-ascii chars in working directory
* [Issue 2058](../../issues/2058) - Don't execute external commands (!) when running pdb in python consoles
* [Issue 2034](../../issues/2034) - Execute until first breakpoint when pressing the Debug button
* [Issue 2032](../../issues/2032) - Dragging (not dropping) file from 7zip over spyder window causes TypeError in dragEnterEvent
* [Issue 1952](../../issues/1952) - spyderlib.utils.external overrides modules for script execution
* [Issue 1948](../../issues/1948) - spyder 2.3 ipython console startup code or file not working
* [Issue 1856](../../issues/1856) - Running in external system terminals is not working on Windows and Python 3
* [Issue 1845](../../issues/1845) - Spyder crashes on launch trying to load the project config file (.spyderproject)
* [Issue 1568](../../issues/1568) - raw_input borks with '!'
* [Issue 1529](../../issues/1529) - Plot A List Of Floats In Variable Explorer Not Possible
* [Issue 1380](../../issues/1380) - Problems with sitecustomize because of pickleshare library
* [Issue 1366](../../issues/1366) - "Highlight occurrences" setting is lost after IDE restart
* [Issue 1359](../../issues/1359) - Mac app - Sometimes it's not possible to get the user env vars
* [Issue 1321](../../issues/1321) - The PYTHONPATH manager on the Mac app does not work with the EPD64 interpreter
* [Issue 1151](../../issues/1151) - Ctrl-C doesn't copy to clipboard in object inspector

In this release 29 issues were closed

**Pull requests**

* [PR 2255](../../pull/2255) - Update French translations
* [PR 2242](../../pull/2242) - Improve message for no docstring
* [PR 2233](../../pull/2233) - catch a reason to crash on startup
* [PR 2224](../../pull/2224) - Fix a bug in completion if callback value is not converted to string
* [PR 2219](../../pull/2219) - Open configuration file with utf-8 encoding on Windows and Python 2 
* [PR 2214](../../pull/2214) - Fix zlib segmentation fault in Anaconda 3.4 Linux

In this release 6 pull requests were merged


----


## Version 2.3.3

### New features

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

### Bug fixes

* [Issue 670](../../issues/670) - Visual help for indentation: draw spaces and tabs
* [Issue 987](../../issues/987) - Allow the file explorer to open any file into the editor as text
* [Issue 1213](../../issues/1213) - Augment or replace rope with Jedi
* [Issue 1461](../../issues/1461) - Kill button 'clicked' signal is connected but never disconnected on the python shell
* [Issue 1469](../../issues/1469) - Add support to get code completions for compiled modules (e.g. OpenCV)
* [Issue 1484](../../issues/1484) - Debug ignores breakpoints, if there's no ASCII characters in a file path
* [Issue 1574](../../issues/1574) - Creating file gives TypeError on Python 3
* [Issue 1718](../../issues/1718) - Keyboard shortcut to come back to normal zoom level
* [Issue 1808](../../issues/1808) - Shortcuts to create and close IPython consoles
* [Issue 1911](../../issues/1911) - Transition to git and github
* [Issue 1930](../../issues/1930) - Evaluating cell or selection in Python consoles takes ages
* [Issue 1946](../../issues/1946) - Spyder with GTK/GTKAgg backend on GNOME freezes
* [Issue 1987](../../issues/1987) - Matplotlib backend in Mac can't be changed when using PySide
* [Issue 1990](../../issues/1990) - exception in spyder internal console when typing 'exit(' in editor
* [Issue 1993](../../issues/1993) - autocomplete in the middle of a word
* [Issue 2006](../../issues/2006) - Your IPython frontend and kernel versions are incompatible
* [Issue 2019](../../issues/2019) - Winpdb (F7) doesn't work in Python 3
* [Issue 2022](../../issues/2022) - TkAgg backend unresponsive window on Linux and OS X
* [Issue 2040](../../issues/2040) - Improve inline backend options
* [Issue 2049](../../issues/2049) - Pandas Dataframe not opening in Variable Explorer
* [Issue 2064](../../issues/2064) - "About spyder" and "Report issue ..." output errors
* [Issue 2072](../../issues/2072) - Unable to bring up tutorial
* [Issue 2074](../../issues/2074) - Profiler - sorting by Total Time sorts by string order, not numeric order
* [Issue 2080](../../issues/2080) - Bug on Variable Explorer while viewing DataFrames, with timestamp columns
* [Issue 2082](../../issues/2082) - Missing py27 dmg download
* [Issue 2092](../../issues/2092) - PYTHON pathmanager on windows 8 does not work properly
* [Issue 2105](../../issues/2105) - Spyder 2.3.2 freezes when viewing big collections on the Variable Explorer
* [Issue 2108](../../issues/2108) - UnicodeDecodeError in the Internal console when trying to run a file with non-ascii chars and synatx errors in it
* [Issue 2109](../../issues/2109) - Go to definition menu item inactive with rope present.
* [Issue 2126](../../issues/2126) - iPython console rendering of pandas.DataFrame._repr_html_() note in changelog
* [Issue 2139](../../issues/2139) - Small typo in Help : Plotting examples 
* [Issue 2143](../../issues/2143) - Closing takes a long time with Python 3.4
* [Issue 2160](../../issues/2160) - UnicodeDecodeError when inspecting pandas DataFrame in ipython console
* [Issue 2190](../../issues/2190) - Update French translations for 2.3.3


----


## Version 2.3.2

### New features

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

### Bug fixes

* [Issue 556](../../issues/556) - Deal with DOS/Windows encoding
* [Issue 681](../../issues/681) - Allow printing Unicode characters
* [Issue 875](../../issues/875) - Add indication that console is busy
* [Issue 883](../../issues/883) - Open all text files in the Editor from the File Explorer
* [Issue 1200](../../issues/1200) - Strings with accents and variable explorer
* [Issue 1546](../../issues/1546) - Spyder issues with unicode under windows
* [Issue 1767](../../issues/1767) - Some support for the ipynb format
* [Issue 1774](../../issues/1774) - can't open preferences or interpreter after changing path to intepreter
* [Issue 1789](../../issues/1789) - Getting warning "WARNING: Unexpected error discovering local network interfaces: 'SysOutput' object has no attribute 'flush"
* [Issue 1809](../../issues/1809) - Shortcut to get to file explorer
* [Issue 1812](../../issues/1812) - Erros when pressing Tab key in the Editor
* [Issue 1830](../../issues/1830) - Don't modify python default system encoding in the console
* [Issue 1832](../../issues/1832) - Select line via line numbers
* [Issue 1847](../../issues/1847) - Preferences panel don't appear
* [Issue 1849](../../issues/1849) - Support yaml files in editor
* [Issue 1859](../../issues/1859) - Latest rope breaks the Object Inspector
* [Issue 1874](../../issues/1874) - Wheel mouse scrolling not enabled in numberlinemarker or flag area
* [Issue 1877](../../issues/1877) - Cell higlighting and scrollbar
* [Issue 1878](../../issues/1878) - Cell highlighting on startup
* [Issue 1891](../../issues/1891) - Sorting Variable explorer gives a traceback
* [Issue 1892](../../issues/1892) - Spyder crashes because pyzmq is missing
* [Issue 1949](../../issues/1949) - Spyder 'support for graphics' should not require pylab
* [Issue 1953](../../issues/1953) - Please do not break API in minor releases
* [Issue 1958](../../issues/1958) - Disable Variable Explorer auto-refresh feature by default
* [Issue 1961](../../issues/1961) - opening bracket in editor or console: focus switches to internal console (which also display an error)
* [Issue 1970](../../issues/1970) - Connecting to an IPython kernel through ssh hangs if you have never connected to hostname before  
* [Issue 1973](../../issues/1973) - Pandas DataFrame in variable explorer can crash the app if it gets out of memory
* [Issue 1975](../../issues/1975) - Improve confusing "UMD has deleted" message
* [Issue 1978](../../issues/1978) - 'Edit' context menu in Variable Explorer should work in all columns
* [Issue 1979](../../issues/1979) - Spyder crashes or hangs when creating some pandas DataFrame's
* [Issue 1982](../../issues/1982) - Middle mouse button *CUTS* text in editor in linux
* [Issue 2004](../../issues/2004) - Open sys.stdin with the right encoding in the console for Python 2
* [Issue 2005](../../issues/2005) - Error when running files in folders with UTF-8 in path
* [Issue 2008](../../issues/2008) - Wrong path to favicon.ico
* [Issue 2015](../../issues/2015) - Printing large pandas DataFrame clears iPython terminal 
* [Issue 2033](../../issues/2033) - Link to new WinPython site
* [Issue 2042](../../issues/2042) - IPython console doens't work with Pygments 2.0rc1
* [Issue 2044](../../issues/2044) - Autocomplete in the editor appends the completed variable onto the preceding expression if there's a token in between


----


## Version 2.3.1

### New features

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

### Bug fixes

* [Issue 93](../../issues/93) - Variable explorer: allow array editor to deal with arrays with more than 2 dimensions
* [Issue 1160](../../issues/1160) - Variable Explorer: add support for pandas objects
* [Issue 1305](../../issues/1305) - mayavi plot hangs when IPython graphics backend is inline (default)
* [Issue 1319](../../issues/1319) - Spyder is not getting its taskbar icon right in Win 7/8
* [Issue 1445](../../issues/1445) - Linux style middle mouse button paste not executed in console
* [Issue 1530](../../issues/1530) - Wrong encoding for date in pylint widget
* [Issue 1590](../../issues/1590) - Add numpy matrices as a supported type to the Variable Explorer
* [Issue 1604](../../issues/1604) - spyder 2.2.5 freezes with netCDF4-python
* [Issue 1627](../../issues/1627) - Run selection (F9) changes focus to Python interpreter, but ex-Matlab users expect the focus to remain on the editor
* [Issue 1670](../../issues/1670) - Provide a "Run current line" feature
* [Issue 1690](../../issues/1690) - Feature request: connect to existing IPython kernel over ssh
* [Issue 1699](../../issues/1699) - Option to disable middle button paste
* [Issue 1783](../../issues/1783) - The new cell delimiter when converting a notebook to python file is # In[`*`]
* [Issue 1863](../../issues/1863) - Ctrl-C doesn't work in a *restarted* IPython console
* [Issue 1893](../../issues/1893) - Matplotlib plots do not display correctly in 2.3.0 (when running in dedicated python interpreter)


----


## Version 2.3.0

### New features

* **Python 3 support**
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

### Bug fixes

* [Issue 696](../../issues/696) - Use Tab to do code completion in the Editor
* [Issue 944](../../issues/944) - Add Python 3 support
* [Issue 1068](../../issues/1068) - Shortcut key to switch to IPython console
* [Issue 1082](../../issues/1082) - IPython console: multiprocessing print output goes to kernel not client
* [Issue 1152](../../issues/1152) - Use the Editor/Console fonts for the code completion widget
* [Issue 1243](../../issues/1243) - Bootstrap fails under Python 3.2
* [Issue 1356](../../issues/1356) - IPython ImportError by not using absolute_import
* [Issue 1374](../../issues/1374) - IPython 1.0dev is giving "ImportError: No module named kernelmanager"
* [Issue 1402](../../issues/1402) - Execute pyflakes, pep8, ... with the Python interpreter specified in Preferences>Console
* [Issue 1420](../../issues/1420) - Deactivate pager by default in the iPython console (because it's perceived as a freeze)
* [Issue 1424](../../issues/1424) - Object inspector is broken for external console
* [Issue 1429](../../issues/1429) - Windows installer for Python 3.3 doesn't finish correctly
* [Issue 1437](../../issues/1437) - Corrupted contents when saving non-unicode .py files with non-ASCII characters
* [Issue 1441](../../issues/1441) - Spyder has several problems to start on Windows because pywin32 is not installed
* [Issue 1465](../../issues/1465) - scientific_startup is defining print_function for Python 2.X interactive consoles
* [Issue 1466](../../issues/1466) - unicode_literals breaks PySide
* [Issue 1467](../../issues/1467) - pyflakes flags print "" on python2 systems
* [Issue 1471](../../issues/1471) - IPython is not enabled in 2.3 (because of mismatched IPython version)
* [Issue 1473](../../issues/1473) - IPython kernel can't be started, complaining that 'sys' doesn't have attribute 'argv'
* [Issue 1475](../../issues/1475) - Plotting from the Variable Explorer is not working for IPython consoles
* [Issue 1479](../../issues/1479) - Opening another file in a running Spyder from the terminal fails in Python 3
* [Issue 1496](../../issues/1496) - Ctrl+C don't interrupt computations in either the Console or IPython console
* [Issue 1513](../../issues/1513) - "Replace all" crashes (not always, but regularly)
* [Issue 1514](../../issues/1514) - Python 3 / Spyder 2.3 : impossible to run temporary script in current interpreter
* [Issue 1517](../../issues/1517) - Console/IPython console reappear each time Spyder starts
* [Issue 1519](../../issues/1519) - Old .spyder.ini is not copied to spyder.ini
* [Issue 1528](../../issues/1528) - Error while shutting down Spyder
* [Issue 1540](../../issues/1540) - Exception instead of dialog box
* [Issue 1542](../../issues/1542) - Braces/Parentheses/Brackets Highlighting is broken with v2.3.0dev6 on Windows/Python 3
* [Issue 1545](../../issues/1545) - Win32 "Spyder Documentation" fails to open
* [Issue 1556](../../issues/1556) - Show cells in the outline explorer
* [Issue 1562](../../issues/1562) - Make Windows installers create a desktop shortcut for Spyder
* [Issue 1567](../../issues/1567) - Accept newer versions of pyflakes
* [Issue 1618](../../issues/1618) - Please provide a way to not compile the documentation during the build process
* [Issue 1619](../../issues/1619) - Python3 invalid syntax in figureoptions.py
* [Issue 1623](../../issues/1623) - Mac app: Editor slow on mac after os update to mavericks
* [Issue 1628](../../issues/1628) - Profiler runs but doesn't show the results
* [Issue 1631](../../issues/1631) - Documentation problem with numpy.concatenate
* [Issue 1646](../../issues/1646) - Different numerical results from "runfile" and "execfile"
* [Issue 1649](../../issues/1649) - Variable Explorer does not show complex number variables
* [Issue 1653](../../issues/1653) - 2 popup windows during lauch
* [Issue 1664](../../issues/1664) - Window gone transparent after splash screen
* [Issue 1675](../../issues/1675) - Redifing any for numpy.any in the console
* [Issue 1692](../../issues/1692) - Minor problem with the new Tab completion functionality
* [Issue 1695](../../issues/1695) - Add "psutil" to the list of optional dependancies
* [Issue 1696](../../issues/1696) - Check marks in display > windows menu are unchecked by moving plugins
* [Issue 1697](../../issues/1697) - Variable explorer freezes spyder
* [Issue 1701](../../issues/1701) - pip install spyder does not work any longer (pip version >=1.5)
* [Issue 1715](../../issues/1715) - debian lintian4py check
* [Issue 1716](../../issues/1716) - Add new icon and scripts for python3 in Linux
* [Issue 1723](../../issues/1723) - .pyx Comment and syntax color error in editor
* [Issue 1731](../../issues/1731) - Support Julia files (.jl) in editor
* [Issue 1735](../../issues/1735) - Small correction in French translations
* [Issue 1745](../../issues/1745) - Fix over-aggressive code completion on dot
* [Issue 1746](../../issues/1746) - Errors when running empty cells
* [Issue 1752](../../issues/1752) - Unable to read Spyder Documentation. F1 key does not work
* [Issue 1753](../../issues/1753) - A fix for the behavior of spyderlib\utils\system.py on Windows
* [Issue 1763](../../issues/1763) - Editor with auto-closing bracket enabled : unabled to type "0" before ")"
* [Issue 1772](../../issues/1772) - Fix download links on the main page
* [Issue 1786](../../issues/1786) - problem of icon with spyder 2.3.0 beta4
* [Issue 1793](../../issues/1793) - Highlight current cell slows down the Editor on big files
* [Issue 1794](../../issues/1794) - Mouse pointer on vertical line
* [Issue 1819](../../issues/1819) - Quick layout change unsuccessful
* [Issue 1828](../../issues/1828) - QAction::eventFilter: Ambiguous shortcut overload: Ctrl+W
* [Issue 1829](../../issues/1829) - Keyboard shortcuts, Reset to default values errors
* [Issue 1836](../../issues/1836) - [CTRL]+F4 does not close tabs
* [Issue 1879](../../issues/1879) - Can't start bootstrap.py with pyqt
* [Issue 1881](../../issues/1881) - Bootstrap.py won't start with python3


----


## Version 2.2.5

### Bug fixes

* [Issue 1322](../../issues/1322) - Problems with scientific_startup in other interpreters from the one Spyder is running on
* [Issue 1337](../../issues/1337) - Mac app - Update to Qt 4.8.4 for HDPI
* [Issue 1450](../../issues/1450) - IPython kernel cpu usage increases with time
* [Issue 1520](../../issues/1520) - LinuxColor for ipython plugin
* [Issue 1551](../../issues/1551) - /doc/installation.rst: update Arch Linux package link
* [Issue 1560](../../issues/1560) - spyder 2.2.3 incompatible with pylint 0.25.1 on Windows
* [Issue 1564](../../issues/1564) - Fix several Editor cell problems
* [Issue 1578](../../issues/1578) - Typo in your 'About Spyder...' dialog.
* [Issue 1581](../../issues/1581) - Cannot launch Spyder 2.2.4 installed from DMG on Mac OS X.
* [Issue 1589](../../issues/1589) - Mention what types of objects our Variable Explorer support in our docs
* [Issue 1595](../../issues/1595) - Fail to start an ipython console when variable explorer autorefresh is turned off in Preferences
* [Issue 1596](../../issues/1596) - Spelling mistake in dialog ('loose' --> 'lose')

### Other Changes

* Update our Mac application to the latest versions of Python, Qt and PyQt (now it's based in Homebrew).
* Several important compatibility fixes for PySide.
* Improve our support for IPython 1.0+.

----

## Version 2.2.4

### Bug fixes

* [Issue 347](../../issues/347) - Matplotlib hangs on Mac if using PySide
* [Issue 1265](../../issues/1265) - Create a Debug menu to easily show how to set breakpoints
* [Issue 1489](../../issues/1489) - Project Explorer does not load all projects in workspace.
* [Issue 1516](../../issues/1516) - Make Spyder compatible with both IPython 0.13 and 1.0
* [Issue 1531](../../issues/1531) - Pyflakes version check is looking for 0.5.0 only
* [Issue 1539](../../issues/1539) - /tmp/spyder is owned by the first user on the server to launch spyder

### Other Changes

* Make Spyder compatible with SymPy 0.7.3+
* Add shortcuts to the tooltips of all toolbars
* Make IPython Console work better if Matplotlib is not installed

----

## Version 2.2.3

### Bug fixes

* [Issue 634](../../issues/634) - Debugging: Lingering break points
* [Issue 639](../../issues/639) - Project Explorer: horizontal size issue (added an optional horizontal scrollbar. This option may be enabled/disabled in the widget context menu)
* [Issue 749](../../issues/749) - Outline Explorer: Duplicate entries
* [Issue 852](../../issues/852) - Implement matlab-like cell features
* [Issue 1388](../../issues/1388) - Add an "About Spyder dependencies" dialog box
* [Issue 1438](../../issues/1438) - "runfile" doesn't work correctly if unicode_literals has been imported (replaced backslashes by slashes in paths)
* [Issue 1515](../../issues/1515) - Add an option to use the same interpreter Spyder is running on as "Python executable" for external consoles
* [Issue 1522](../../issues/1522) - licenses of the images (especially the .png)
* [Issue 1526](../../issues/1526) - Build script (setup.py) includes the wrong version of pyflakes/rope in Windows installer
* [Issue 1527](../../issues/1527) - please include the LICENSE file in the source package

### Other Changes

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

### Bug fixes

* [Issue 1497](../../issues/1497) - Spyder 2.2.1 does not work with Python < 2.7
* [Issue 1498](../../issues/1498) - TypeError thrown by IPython Console when the pager is off
* [Issue 1499](../../issues/1499) - Console (Terminal) throws NotImplementedError for Home/End keys
* [Issue 1509](../../issues/1509) - Add support for javascript syntax highlighting
* [Issue 1510](../../issues/1510) - Problems with zooming in/out

### Other Changes

* Add new icons to the Run, Debug and Main toolbars
* Update Pylint plugin to work with pylint 1.0
* Add Ctrl/Cmd+[+,-] to zoom in/out in the Editor
* Disable Crtl+MouseWheel to zoom in/out in Mac (See Issue 1509)

----

## Version 2.2.1

### Bug fixes

* [Issue 1231](../../issues/1231) - Some strange messages are printed in the terminal when Spyder is running
* [Issue 1318](../../issues/1318) - Mac app - Unable to use the keyboard when completion widget is displayed and the app loses focus
* [Issue 1331](../../issues/1331) - Git Bash: Spyder's script has wrong shebang
* [Issue 1333](../../issues/1333) - Spyder is unable to detect git if installed with msysgit (Microsoft Windows PC's)
* [Issue 1370](../../issues/1370) - Unit tests exceptions in IPython are displayed in its kernel tab
* [Issue 1395](../../issues/1395) - Mac App - Importing matplotlib fails on Snow Leopard due to incompatible version of libpng
* [Issue 1399](../../issues/1399) - Recommend to use pip instead of easy_install
* [Issue 1426](../../issues/1426) - Background colour of Object Inspector (docstring) in Rich Text mode is same as the window's
* [Issue 1439](../../issues/1439) - Update pil_patch to be compatible with Pillow
* [Issue 1449](../../issues/1449) - Spyder --light is not functioning
* [Issue 1470](../../issues/1470) - Preferences size is not saved when using PySide
* [Issue 1472](../../issues/1472) - matplotlib plot's docstring is not rendered correctly in the Object Inspector

### Other Changes

* All scientific libraries in our Mac application were updated to their latest releases.
* The _Run Settings_ dialog has now its own icon. Before it was the same as the _Preferences_ pane one.
* Update and improve our _Installation_ instructions for all platforms.
* Add support for Google TODO comments: "TODO(username@domain.com): blabla"

----

## Version 2.2.0

### New features

* **Better integration with IPython**.
    * A dedicated preferences page from which you can set its most important options
    * An easy way to manage IPython kernels inside Spyder (i.e. interrupts and restarts).
    * Each console can be configured separately (which is not possible in IPython-qtconsole)
    * Each console is now connected to the Object Inspector and the History log.
    * Learn how to use IPython reading its documentation on the Object Inspector.
    * Find text in the console and pager using our Find Widget.
* A new **MacOS X Application**
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
* **Single instance mode**
    * Users can now open Python scripts from their file explorer on the currently available instance.
    * Linux users can also open their files from the terminal.
* Spanish translation of the interface

### Bug fixes

* [Issue 318](../../issues/318) - Create a widget to list all breakpoints
* [Issue 349](../../issues/349) - Add "Run selection or current block" action to Editor's context menu
* [Issue 448](../../issues/448) - Editor: disable code-related features inside comments (code completion, auto-indentation, ...)
* [Issue 466](../../issues/466) - Can't use Spyder to open python scripts (.py files) from the terminal or the file explorer
* [Issue 554](../../issues/554) - Improved debugger integration
* [Issue 609](../../issues/609) - Debugging: Unsetting a breakpoint in the editor isn't reflected until you restart debugging entirely
* [Issue 650](../../issues/650) - After deleting a directory set as working directory and changing to a new working directory the script won't run
* [Issue 687](../../issues/687) - Indentation error when trying to "run selection" on simple indented code
* [Issue 697](../../issues/697) - Create a DMG package for Spyder
* [Issue 764](../../issues/764) - Jump to the next result when pressing Enter in search field
* [Issue 836](../../issues/836) - Spyder is sometimes not detecting file changes from external editors
* [Issue 849](../../issues/849) - Breakpoints are ignored sometimes
* [Issue 853](../../issues/853) - Problems with code completion after adding submodules to ROPE_PREFS/extension_modules
* [Issue 865](../../issues/865) - Run selection (F9) in IPython console 0.11+: problem with indented blank lines
* [Issue 940](../../issues/940) - open_in_spyder not defined
* [Issue 955](../../issues/955) - Breakpoints in debugger do not move correctly when editing code
* [Issue 971](../../issues/971) - Add "Open with Spyder" entry to Windows File Explorer's context menu
* [Issue 994](../../issues/994) - mathjax does not get installed properly
* [Issue 997](../../issues/997) - Some docstrings are getting truncated in the object inspector
* [Issue 1008](../../issues/1008) - Fail on context menu call in project explorer when project files are inside symlinked dir
* [Issue 1018](../../issues/1018) - Menu locations, "Run Configurations" &  "Preferences"
* [Issue 1026](../../issues/1026) - Decide the best strategy to comment selections on the Editor
* [Issue 1032](../../issues/1032) - Running a script from editor does not send runfile() correctly to IPython Qt plugin
* [Issue 1050](../../issues/1050) - First implementation of the "IPython Console" plugin (single instance version)
* [Issue 1051](../../issues/1051) - New IPython Console (Spyder 2.2+): add support for the %edit magic command
* [Issue 1054](../../issues/1054) - New IPython Console (Spyder 2.2+): update variable explorer after new prompt
* [Issue 1055](../../issues/1055) - New IPython Console (Spyder 2.2+): add support for history management
* [Issue 1056](../../issues/1056) - New IPython Console (Spyder 2.2+): add an option to customize In/Out prompts
* [Issue 1057](../../issues/1057) - New IPython Console (Spyder 2.2+): Add our FindReplace widget to every console
* [Issue 1058](../../issues/1058) - New IPython Console (Spyder 2.2+): Add Ctrl+I keyboard shortcut to send an object the Object Inspector
* [Issue 1059](../../issues/1059) - New IPython Console (Spyder 2.2+): drop support for IPython in external console
* [Issue 1061](../../issues/1061) - New IPython Console (Spyder 2.2+): add support for "Find in files" plugin
* [Issue 1062](../../issues/1062) - New IPython Console (Spyder 2.2+): add a dedicated section in documentation
* [Issue 1064](../../issues/1064) - Editor performance issue since revision d98df4092e16
* [Issue 1069](../../issues/1069) - Focus goes to kernel not client with pdb in IPython client
* [Issue 1078](../../issues/1078) - IPython Console: Cannot interrupt started processes
* [Issue 1079](../../issues/1079) - Can't input Unicode in Internal Console
* [Issue 1081](../../issues/1081) - ipython-qtconsole not listed as optional dependency in Ubuntu
* [Issue 1083](../../issues/1083) - Make Ipython qtconsole widget more intuitive
* [Issue 1085](../../issues/1085) - IPython console: sometimes files are executed in wrong IPython
* [Issue 1094](../../issues/1094) - Error message when trying to save a file
* [Issue 1095](../../issues/1095) - Preferences Dialog doesn't remember size
* [Issue 1101](../../issues/1101) - Interrupt (Ctrl+C) in the console does not work in Spyder on Mac Os X
* [Issue 1106](../../issues/1106) - Spyder console crashes when trying to type in console after running script
* [Issue 1112](../../issues/1112) - Opening a file from the linux command line
* [Issue 1128](../../issues/1128) - please remove pyflakes and rope from the .zip files
* [Issue 1136](../../issues/1136) - IPython console: cannot connect to external kernels
* [Issue 1138](../../issues/1138) - Rich text in object inspector mishandles some scipy docstrings
* [Issue 1163](../../issues/1163) - Improve the spyder.desktop file fo easier integration into Linux
* [Issue 1169](../../issues/1169) - Saving variables does not retain uppercase letters of variable names
* [Issue 1179](../../issues/1179) - Pylint "go to line" does not work with the additional dot in filename
* [Issue 1186](../../issues/1186) - scipy.weave doesn't work in the Mac app
* [Issue 1191](../../issues/1191) - Inconsistent behaviour of the Editor on code completion and object introspection
* [Issue 1199](../../issues/1199) - spyderlib/utils/windows.py has incorrect encoding
* [Issue 1201](../../issues/1201) - Let the user set the default filter when opening file
* [Issue 1210](../../issues/1210) - Enhancement: Create sphinx rich text docstrings in QThread
* [Issue 1226](../../issues/1226) - MacOS X App - Can't import libraries from other Python interpreters
* [Issue 1227](../../issues/1227) - Auto inserted colon causes pylint error
* [Issue 1229](../../issues/1229) - Which version of ipython is needed for Spyder 2.2.0?
* [Issue 1230](../../issues/1230) - Better handle for mathjax and jquery embeded libraries on linux systems
* [Issue 1232](../../issues/1232) - Cmd-Space is not showing code-completion options
* [Issue 1233](../../issues/1233) - ERROR and WARNING when compiling the documentation
* [Issue 1234](../../issues/1234) - Edit .enaml files as text file
* [Issue 1236](../../issues/1236) - Fix Qt Network Access warning messages that appear on the terminal
* [Issue 1241](../../issues/1241) - 'Remove block comment' is not working
* [Issue 1242](../../issues/1242) - Can't start spyder2.2 on Win 7, crashes upon saving .spyder.ini
* [Issue 1249](../../issues/1249) - "Run block" and "Run File" are not working for external IPython kernels
* [Issue 1250](../../issues/1250) - Spyder crashes on launch if the project explorer is used
* [Issue 1252](../../issues/1252) - Expansion of nodes on tree view undoes itself
* [Issue 1253](../../issues/1253) - Spyder is not detecting the presence of iPython 0.13.1rc2 nor IPython 1.0dev
* [Issue 1258](../../issues/1258) - Focusing the "Replace with:" Text Box causes the editor to jump to the next instance of the item that's in the find box
* [Issue 1261](../../issues/1261) - IPython kernel/clients: error when closing an IPython console
* [Issue 1266](../../issues/1266) - Let the user eliminate breakpoints from the "Breakpoints widget"
* [Issue 1269](../../issues/1269) - Dataloss when Spyder gets confused about which file goes with which editor tab
* [Issue 1271](../../issues/1271) - Find and replace by empty string
* [Issue 1272](../../issues/1272) - Fix code completion speed issues on the Editor
* [Issue 1275](../../issues/1275) - Spyderlib fails to start new IPython consoles, raises socket exception
* [Issue 1277](../../issues/1277) - Enthought Python Distribution and Spyder DMG are not working well on Mac OS X
* [Issue 1281](../../issues/1281) - Mac App - Spyder swallows AssertionErrors while executing a file
* [Issue 1285](../../issues/1285) - Object Inspector Crashes when Reloading Page
* [Issue 1286](../../issues/1286) - Broken links in Help
* [Issue 1287](../../issues/1287) - Saving file under different file name in split-window mode lets non-focused window jump to first file
* [Issue 1288](../../issues/1288) - Some rope_patch improvements
* [Issue 1296](../../issues/1296) - Clickable tracebacks in console are not working in PySide
* [Issue 1298](../../issues/1298) - Mac App - matplotlib is not detecting ffmpeg to create animations
* [Issue 1299](../../issues/1299) - pylint keeps opening same file at startup
* [Issue 1309](../../issues/1309) - Clicking on filename in structure widget sets the cursor at the beginning of the file
* [Issue 1314](../../issues/1314) - QPainter warnings when moving/undocking widgets in main window
* [Issue 1315](../../issues/1315) - Project not closing files associated with after closing it
* [Issue 1325](../../issues/1325) - Spyder cannot be re-opened on Windows if parent console is closed
* [Issue 1327](../../issues/1327) - Allow global options for Run Configuration
* [Issue 1344](../../issues/1344) - Mac App - Spyder crashed and can't be open again
* [Issue 1345](../../issues/1345) - Code Review Request: Update breakpoints during pdb sessions
* [Issue 1347](../../issues/1347) - The spyder.desktop has an wrong line
* [Issue 1353](../../issues/1353) - Error messages in internal console when rope is not installed
* [Issue 1363](../../issues/1363) - 2.2rc installation takes a long time because of sphinx dependency
* [Issue 1364](../../issues/1364) - No spyder.ico after installation on Windows
* [Issue 1369](../../issues/1369) - Using the subprocess.check_output function breaks compatibility with Python 2.5 and 2.6
* [Issue 1371](../../issues/1371) - Crash when adding text to multiline comment is CSS
* [Issue 1372](../../issues/1372) - SphinxThread might return AttributeError


----


## Version 2.1.13.1

### Bug fixes

* Spyder startup: fixed PyQt minimum version requirement test (the old poor comparison algorithm was considering that v4.10 was older than v4.4...) (See [Issue 1291](../../issues/1291))
* Console: Matplotlib was always imported even when the Matplotlib's Patch option was not available (i.e. the Matplotlib installed version was not compatible with the patch). As a consequence, even when disabling every console advanced option in preferences, the preloaded module list was huge
* Editor:
    * When closing Spyder with unsaved modified files, Spyder was asking confirmation as many times as there were editor windows. Only one confirmation is necessary because, with current editor design, all editor windows are synced.
    * When creating two new files, saving one of them will lead to temporarily mask the leading '`*`' indicating the fact that the other untitled file was not already saved. This is simply a display issue: internally, it is clear that the file is in a non-saved state and Spyder will ask for it to be saved when trying to close the file
    * Multiple windows: when saving a new untitled file, other editor windows were getting confused on file list order -- eventually leading to data loss
    * Open file dialog: default file type filter now matches the current file (See [Issue 1201](../../issues/1201))
* Fixed "PyQt Reference Guide" link

### Other changes

* Editor: Ctrl+MouseWheel is now zooming in/out the editor text size (see [Issue 1270](../../issues/1270))
* About dialog box: changed the "This project is part of Python(x,y)" part to more general words (which are also closer to the initial meaning of this sentence) including a citation of WinPython


----


## Version 2.1.13

### Bug fixes

* Fixed [Issue 1158](../../issues/1158): "pip install spyder" fails on non-Windows platforms due to a bug in pip installation process (missing spyderlib_win_postinstall.py script)
* File Explorer/Windows/Fixed "remove tree" feature: added an error handler in shutil.rmtree to be able to remove a non-empty folder with shutil.rmtree is not working on Windows when it contains read-only files
* (See [Issue 1106](../../issues/1106)) Fixed "error: unpack requires a string argument of length 8" related to socket communication between Spyder and the remote Python process
* Editor:
    * After splitting horizontally or vertically the editor window, filenames were not synchronized when saving a file as another name (see [Issue 1120](../../issues/1120))
    * Fixed error when trying to "Save as..." a file with extension to a file without any extension (see [Issue 1183](../../issues/1183))
    * pep8 code analysis: a new line character was abusively added by Spyder to source code before analyzing it because it's necessary for pyflakes but it's not for pep8! (see [Issue 1123](../../issues/1123))
    * Fixed UnboundLocalError when clicking on "Search/Replace" button if both search pattern and replace pattern fields are empty (see [Issue 1188](../../issues/1188))
* Pylint plugin/tree widget: "go to line" was not working when filename contained additionnal dots (see [Issue 1179](../../issues/1179))
* Fixed critical bug when an invalid/unsupported version of pyflakes is installed (see [Issue 1181](../../issues/1181))
* Editor/block comments: fixed remaining PyQt API v2 compatibility issues (see [Issue 905](../../issues/905))
* Variable explorer: more flexible name fixing algorithm (even if it's not a good practice to use reference names with upper case letters, we do not remove them anymore) -- See [Issue 1169](../../issues/1169)

### Other changes

* Spyder about dialog box: added Python build architecture (32 or 64 bits)
* Find in files: fixed default 'exclude pattern' which was accidently excluding all files starting with 'build' instead of simply excluding 'build' folders as intended
* For the sake of consistency, now using single-clicks for activating entries of all tree widgets in Spyder ("Find in files" and "Pylint" are now consistent with the "Outline" explorer) -- See [Issue 1180](../../issues/1180)


----


## Version 2.1.12

### Bug fixes

* Spyder settings: sometimes (virus protection?) the .ini file can't be written, and removing the .ini file before writing seems to help, as suggested [here](https://groups.google.com/forum/#!msg/spyderlib/a_P9JBJEZeE/gOK_Pr2WbE8J) (see [Issue 1086](../../issues/1086))
* Fixed Home/End key behaviour inconsistency on MacOS X (See [Issue 495](../../issues/495))
* Internal console: new option "Pop up internal console when errors were intercepted" -- default: False, which avoids loosing focus when a traceback is shown in the internal console... but features may also fail silently! (bugs could stay hidden a while before being taken care of) -- See [Issue 1016](../../issues/1016)
* Fixed "TypeError: file_saved(long,long).emit(): argument 1 has unexpected type 'long'" error occuring on some Linux 32-bit platforms -- See [Issue 1094](../../issues/1094)
* Console: find/replace widget "Search next/previous occurrence" feature was broken

### Other changes

* Portable version of Spyder (inside WinPython):
    * Spyder '?' menu: added documentation detection (.chm, .pdf) in sys.prefix\Doc (Windows-only)
    * Project explorer:
        * Handling errors when opening a workspace which has been moved
        * Workspace is now configured with relative paths, so it can be moved from a location to another and still be opened in Spyder
* Windows: moved the functions hiding parent console to spyderlib/utils/windows.py


----


### Version 2.1.11

### Bug fixes

* Critical bugs:
    * Editor ([Issue 960](../../issues/960)): cannot open/save files from GUI (QFileDialog issue with PyQt4 v4.6)
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
    * This fixes a part of [Issue 1016](../../issues/1016) by handling the following pyflakes bugs:
      * http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674796
      * http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=674797

### Other changes

* Installer for Windows (bdist_wininst/bdist_msi):
    * added Start Menu shortcuts
    * added 'pyflakes' and 'rope' (if available in the repository) to the package list (this is not conventional but Spyder really need those tools and there is not decent package manager on Windows platforms, so...)
    * This change will make the Spyder building process simpler for Windows as the Python(x,y) won't be needed anymore to provide Start Menu shortcuts or to install 'rope' and 'pyflakes' at the same time. Now, there is no significative difference between the standard installers built with distutils (bdist_wininst or bdist_msi options) and the Python(x,y) plugin, except for the "package upgrade" ability (uninstall previous version) which is still not (and won't be) supported by distutils.


----


## Version 2.1.10

### Bug fixes

* Critical bugs:
    * Spyder crashed at startup/TypeError: `_isdir()` takes exactly 1 argument (0 given). Affects only Windows platforms with Python 3.2.2+ or 2.7.3+)
    * Spyder was freezing when working with netCDF4 objects in the interactive console
    * Console: h5py was systematically imported to avoid crashes with the HDF5 plugin (Variable Explorer's I/O plugin). These ugly workarounds introduced with revision 3affc82ce081 were removed in this changeset to avoid side effects like DLL version conflict on Windows platforms. The main risk of this change is to break the HDF5 plugin on some configurations. But this is the best compromise.
* General:
    * Fixed regression: when no Qt library is installed (PyQt/PySide), warning the user with a Tkinter dialog box (if possible)
    * Fixed Preferences Dialog flickering issue introduced with revision a4e1565e93c5
    * Run configuration dialog: fixed Tab focus order behavior
    * Fixed "Run > Configure..." and "PYTHONPATH management" entry locations on MacOSX
    * Updated bootstrap script and Qt library selection logic to accomodate launch of Spyder using PySide while PyQt is also installed ([Issue 1013](../../issues/1013), see [Issue 975](../../issues/975) for additional background).
    * Fixed several encoding problems preventing Spyder from launching when the user's home directory contains non-ASCII characters ([Issue 812](../../issues/812), [Issue 1027](../../issues/2017)).
    * Debugging: [Issue 684](../../issues/684): Debug with winpdb will now use the command line options and working directory specified in the General Setting section of the Run Configuration dialog
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

### Other changes

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

### Bug fixes

* Run configuration/bugfix: command line options were not properly parsed
* Preferences dialog was not showing up with PySide installed *and* without PyQt4
* Editor:
    * Closing additional editor window produced traceback and primary editor breakdown
    * File/Open: embedded editor popped up even if there is one in a separate window
    * Selecting a part of a word raises an IndexError exception
    * Revert option was prompting for user input even on an unmodified buffer
    * Added missing .f77 file extensions for Fortran files filter
    * Occurrence highlighting was not working when cursor was at the left side of a word and if the next character was ':', ',' or '(' (or any other character not matching the "word regexp")
* Console:
    * Console was unusable (endless tracebacks) when monitor was disabled
    * File drag'n drop was not working (should execute dropped file)
* (Experimental) IPython plugin:
    * Fixed compatibility issues with PyQt4 and IPython 0.12
    * Fixed multiple instances issue (it was not possible to open more than one IPython frontend) and other issues
    * IPython kernel connections were unpredictable ([Issue 977](../../issues/977))
* Dictionary editor (Variable explorer): fixed UnboundLocalError when context menu is called on an empty table
* Object inspector failed to show an error message due to unicode error
* Project Explorer:
    * "Show all files" option was broken after restarting Spyder
    * It was impossible to create a project from an existing directory located outside the workspace


----


## Version 2.1.8

### Bug fixes

* Editor/Source code toolbar:
    * "Show task list" and "Go to the next task" actions: the "Show TODO/FIXME/XXX/HINT/TIP comments list" button was not working
    * "Show warning/error list" and "Go to the next warning/error" actions: the "Show code analysis warnings/errors" button was not working


----


## Version 2.1.7

### Bug fixes

* Main window:
    * Detached dockwidgets were not painted after restarting Spyder ([Issue 880](../../issues/880))
* Console:
    * Enhanced Python interpreter: %clear command was broken since v2.1.5
* Object inspector's rich text mode: fixed unexpected indent error
* IPython plugin: fixed compatibility issue with latest v0.12dev (thanks to Boris Gorelik)

### Other changes

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

### Bug fixes

* Critical bug on certain Windows platforms (not sure yet if it's related to a particular version of PyQt or something else): all plugins (dockwidgets) were shown detached (or hidden) from the mainwindow at startup (this is related to the attempt fixing [Issue 880](../../issues/880))


----


## Version 2.1.5

### Bug fixes

* Detached dockwidgets (Console, ...) were not painted after restarting Spyder
* Editor/Outline-bugfix: duplicate entries were shown when the editor was synchronizing file contents with disk
* File/Project explorer:
    * Fixed regression regarding [Issue 740](../../issues/740) (fixed in v2.1.0, re-introduced in v2.1.2): couldn't open files with non-ascii characters in their names
    * SCM support: commit/log actions were not working when right-clicking on a file instead of a folder
* Console:
    * Monitor/Introspection: fixed socket communication issue due to a MemoryError -- This error was mixing communication messages, causing various problems described in [Issue 857](../../issues/847) and [Issue 858](../../issues/858). This bug was reported by ruoyu0088, who also tried (and succeeded) to fix it and suggested a workaround which is implemented in this release
    * Fix critical console hang on OS X when using the "Run selection or current block feature" (see [Issue 502](../../issues/502))
    * Apply the right scheme color to the IPython console when there weren't any options provided by the user or when the only option was "-colors LightBG"
* Windows platforms:
    * "Preferences" dialog was not shown if account username contained non-ASCII characters
* Object Inspector:
    * Show signatures for docstrings sent from the Editor (see [Issue 690](../../issues/690))

### Other changes

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
* Internal console ([Issue 868](../../issues/868)): output is now immediately available
* "Maximize current plugin" action: now automatically shows the "Outline" plugin when maximizing the "Editor" plugin
* Editor/Outline comment separators: allow space betwee hash and dash, e.g "# --- Outline Separator"


----


## Version 2.1.4

### Bug fixes

* Console:
    * *Critical bugfix* for IPython support: variable explorer link was broken (regression introduced with v2.1.3)

### Other changes

* Console:
    * option "Open an IPython interperter at startup" is now *explicitely* disabled for IPython v0.11+ (these versions of IPython are not fully supported through Spyder's console plugin)


----


## Version 2.1.3

### Enhancements

* Variable explorer performance were improved, especially when dealing with very long sequences -- See [this discussion](http://groups.google.com/group/spyderlib/browse_thread/thread/3a7ef892695e417a)
* Variable explorer / dictionary editor: added support for unknown objects -- this allows browsing any object attributes -- This is still experimental.

### Bug fixes

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

### Bug fixes

* General:
    * Patched external path library to avoid a crash with a user HOME directory with non-ascii characters
    * Doc/README: warning the user about the fact that the 'python setup.py install' method does not uninstall a previous version
* Console:
    * Fixed "AccessInit: hash collision: 3 for both 1 and 1" error (see [Issue 595](../../issues/595))
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
    * Rich text mode was not showing headings when invoked from editor ([Issue 690](../../issues/690))

### Enhancements

* File/Project explorer:
    * Added "Delete" keyboard shortcut to remove selected file(s)/folder(s)
    * SCM integration: added support for TortoiseHg v2 (only v1 was supported)
* Console/Matplotlib options: the backend may now be set separately from the Matplotlib patch

### Other changes

* Console:
    * The Matplotlib patch is only applied for Matplotlib <=v1.0
    * PyQt API version issues (error like "ValueError: API 'QString' has already been set to version 1"): the "ignore setapi errors" option is disabled by default, to avoid masking these errors and associated tracebacks


----


## Version 2.1.1

_Note:_ v2.1.1 is a minor update of v2.1.0 (licence issues and minor bug fixes)

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
        * Added action "Resize rows to contents" (partially implements feature requested with [Issue 807](../../issues/807))
* *Editor*:
    * find/replace:
        * added support for *multiline* regular expression search pattern
        * added support for *multiline* regular expression text replacement
        * added button "Highlight matches" to highlight all found results
    * syntax highlighting: added support for OpenCL, gettext files, patch/diff files, CSS and HTML files
    * support for "2 spaces" and "tabs" indentation characters
    * new code analysis feature: added support for the [pep8](http://pypi.python.org/pypi/pep8) style guide checker
    * "Comment" and "Uncomment" actions were replaced by a single "Comment/Uncommment" toggle action
    * (Fixes  [Issue 811](../../issues/811) ) "Run configuration": added "Run in an external system terminal" option
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
    * (Fixes  [Issue 704](../../issues/704)) Outline was showing the delimiters of block comments ('#------...-'), causing nesting inconsistencies because block comments are not indented properly with respect to the code around
    * Fixed several bugs with the "Run selection or current block" feature.
* Object inspector:
    * Rich text mode was failing for non-ascii docstrings
* Find/Replace widget:
    * Combo box history was populated only when pressing Enter (now pressing F3 to find next occurrence will add the current entry to history)


----


## Version 2.0.12

### Bug fixes

* (Fixes [Issue 476](../../issues/476)) Editor/bugfix: print preview was not working
* Completion widget/bugfix (editor/console): combo box was truncated by main window depending on its size
* widgets.sourcecode.base.TextEditBaseWidget/bugfix: parenting to None was not working
* Console/Text wrap mode: character wrapping was not implemented since we switched from QTextEdit to QPlainTextEdit
* (Fixes [Issue 649](../../issues/649)) Patch submitted by [DavidAnthonyPowell](http://code.google.com/u/DavidAnthonyPowell/) - Syntax highlighter does not recognise imaginary, binary or octal numbers
* Spyder's layout: fixed window position/size issues when maximized/fullscreen mode was active
* Object inspector: fixed minor bug (simple traceback in the internal console) when handling a sphinx error
* (Fixes [Issue 667](../../issues/667)) Editor/bugfix: Shift+Enter inserted lines that did not get line numbers
* (Fixes [Issue 672](../../issues/672)) Editor: TODO/FIXME were not detected if not followed by ':' (HINT/TIP were properly detected)

### Enhancements

* (Fixes [Issue 655](../../issues/655)) Editor/pyflakes-powered code analysis: warnings are now ignored for lines containing "pyflakes:ignore"

### Other changes

* Internal console (Spyder debugging only): turned off the multithreaded mode


----


## Version 2.0.11

### Bug fixes (since v2.0.9)

* (Fixes [Issue 616](../../issues/616)) Pylint plugin: tree widget header text was not updated when analyizing a new script (the last analyzed script name was still shown)
* Editor/completion widget/bugfix: pressing shift was hiding the completion combo box
* (Fixes [Issue 630](../../issues/630)) Added missing default settings for "Spyder light" (only necessary when installing from scratch and without any remaining .spyder.ini file)
* Editor/Console-bugfix: info tooltips (calltips) were hidden right after being shown (i.e. when typing any character after the left parenthesis)
* (Fixes [Issue 631](../../issues/631)) Drag and drop of files into editor on Linux was pasting path instead of opening the file
* (Fixes [Issue 640](../../issues/640)) Editor: block comment was not working correctly at end of file
* Code completion widget (Editor/Console) - bugfix: parenting to the ancestor widget was necessary on Linux
* (Fixes [Issue 546](../../issues/546)) (Contributor: [Alex Fargus](http://code.google.com/u/alex.fargus/)) C/Cpp syntax highlighting bugfix
* (Fixes [Issue 646](../../issues/646)) IPython integration: fixed pyreadline monkey-patch for pyreadline v1.7

### Enhancements (since v2.0.9)

* File explorer widget/plugin: improved performances (widget is now populated in a separate thread)
* Spyder crash dialog: warning the user about the '--reset' option (this will remove all configuration files)


----


## Version 2.0.9

### Bug fixes

* Console: added option to ignore PyQt/sip errors when trying to set sip API (fixed Enthought Tool Suite 3.6.0 compatibility issue)
* utils.dochelpers.getargtxt/bugfix: retrieving builtin function arguments was no longer working
* (Fixes [Issue 499](../../issues/499)) Editor-related keyboard shortcuts were not applied after opening files
* (Fixes [Issue 575](../../issues/575)) Tab scroll buttons were not shown on OS X resulting in clamped/changing window sizes
* (Fixes [Issue 574](../../issues/574)) Debugging: Spyder only synced at debugger breakpoints
* (Fixes [Issue 576](../../issues/576)) "Source / Remove trailing spaces" was removing newline at the end of file (+ added support for "undo")
* (Fixes [Issue 582](../../issues/582)) Console: changing font preferences was requiring a restart to be fully taken into account
* (Fixes [Issue 562](../../issues/562)) Spyder was unable to restore editor's outline explorer tree when mixed ' and " characters were found in tree entries
* (Fixes [Issue 590](../../issues/590)) Shell/"Clear line" shortcut was not correct: this is actually "Shift+Escape" (not "Escape")
* (Fixes [Issue 591](../../issues/591)) History log was systematically erased when updating Spyder version
* Outline explorer/bugfix: when opening file, the 'show/hide all files' option was not applied (this was then applied when switching from a file to another)
* (Fixes [Issue 602](../../issues/602)) Backported from v2.1 a couple of bugfixes related to Editor and multiple panels
* Object inspector: when raised automatically above other dockwidgets, plugin refresh was unnecessarily triggered
* Editor/code completion-bugfix: some key events (e.g. Ctrl+V) were lost during code completion-related hang-up
* (Fixes [Issue 599](../../issues/599)) Multiline text pasting was not working in a newly opened console (i.e. first prompt)

### Enhancements

* Major change/Translations: moved from 'QtLinguist' to 'gettext' (localizing Spyder should now be easier)
* Console: increased default maximum line count (buffer depth) up to 10,000 lines (instead of only 300 lines)
* Editor's rope-based introspection features (code completion, calltips, go to definition): new rope monkey-patch providing major performance improvements
* File explorer/Project explorer - opening file with associated application: now supported on all platforms
* Added action "Reset window layout" in "View" menu to reset main window layout to default
* Documentation: added page on debugging
* Editor: added syntax highlighters for diff/patch files (.diff, .patch, .rej) and gettext files (.po, .pot)
* (Fixes [Issue 537](../../issues/537)) Global working directory toolbar: removed label considering the fact that the toolbar widgets are quite explicit on its role (and the combo box tooltip is explaining it in detail)
* (Fixes [Issue 598](../../issues/598)) Added a .desktop file in source package
* (Fixes [Issue 87](../../issues/87)) Editor plugin's title now show the current script filename


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

### Bug fixes

* Console: menu entries "Environment variables", "Current working directory" and "Show sys.path" were not disabled when the Monitor was turned off
* Preferences dialog box/Keyboard shortcuts:
    * conflicts are now ignored if shortcuts have different contexts *except* if one of this context is '`_`' (i.e. global context)
    * conflict warnings are now also shown when showing the preferences dialog box (not only when modifying shortcuts and applying changes)
* Drag/drop Python script to console: fixed TypeError (TypeError: start() got an unexpected keyword argument 'ask_for_arguments')
* Console base widget: added support for FF (Form Feed) ANSI sequence - Fixes bug in IPython console: 'cls' and 'clear' magic commands were inactive in IPython consoles
* Editor: code completion was sometimes very slow when editing files within a Spyder project
* Code editor: fixed "Delete line" feature (Ctrl+D) / was not working with multiline selection

### Other changes

* Editor/80-column vertical edge line: added options to show/hide this line and change the column number
* Editor: added "Comment"/"Uncomment" actions to context menu
* Source code and shell editor widgets: code refactoring/cleaning (this should help people using these widgets outside Spyder)
