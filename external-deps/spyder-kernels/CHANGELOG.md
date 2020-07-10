# History of changes

## Version 1.9.2 (2020-07-10)

### Pull Requests Merged

* [PR 234](https://github.com/spyder-ide/spyder-kernels/pull/234) - PR: Fix a problem caused by ipykernel 5.3.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 231](https://github.com/spyder-ide/spyder-kernels/pull/231) - PR: Send comm config on every message, by [@impact27](https://github.com/impact27)
* [PR 230](https://github.com/spyder-ide/spyder-kernels/pull/230) - PR: Send comm config before any wait just to be sure, by [@impact27](https://github.com/impact27)
* [PR 229](https://github.com/spyder-ide/spyder-kernels/pull/229) - PR: Add warning on console if file is not saved, by [@impact27](https://github.com/impact27)
* [PR 228](https://github.com/spyder-ide/spyder-kernels/pull/228) - PR: Fix post_mortem interaction, by [@dalthviz](https://github.com/dalthviz)
* [PR 227](https://github.com/spyder-ide/spyder-kernels/pull/227) - PR: Create a constant for numeric Numpy types, by [@dalthviz](https://github.com/dalthviz)
* [PR 226](https://github.com/spyder-ide/spyder-kernels/pull/226) - PR: Backport PR 225, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 222](https://github.com/spyder-ide/spyder-kernels/pull/222) - PR: Remove the current working directory from sys.path for Python 3.7+, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 220](https://github.com/spyder-ide/spyder-kernels/pull/220) - PR: Make multithreading patch work for all OSes in Python 3, by [@steff456](https://github.com/steff456) ([12465](https://github.com/spyder-ide/spyder/issues/12465))

In this release 9 pull requests were closed.

----

## Version 1.9.1 (2020-05-06)

### Issues Closed

* [Issue 217](https://github.com/spyder-ide/spyder-kernels/issues/217) - Maximum recursion depth exceeded ([PR 218](https://github.com/spyder-ide/spyder-kernels/pull/218) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 219](https://github.com/spyder-ide/spyder-kernels/pull/219) - PR: Check that startup file exists, by [@impact27](https://github.com/impact27) ([12442](https://github.com/spyder-ide/spyder/issues/12442))
* [PR 218](https://github.com/spyder-ide/spyder-kernels/pull/218) - PR: Avoid an error when computing the shape of Pandas objects, by [@ccordoba12](https://github.com/ccordoba12) ([217](https://github.com/spyder-ide/spyder-kernels/issues/217))
* [PR 215](https://github.com/spyder-ide/spyder-kernels/pull/215) - PR: Fix post mortem functionality, by [@impact27](https://github.com/impact27)
* [PR 212](https://github.com/spyder-ide/spyder-kernels/pull/212) - PR: Set namespace correctly when running in new namespace, by [@impact27](https://github.com/impact27)
* [PR 211](https://github.com/spyder-ide/spyder-kernels/pull/211) - PR: Use Exception instead of ImportError in is_special_kernel_valid, by [@ccordoba12](https://github.com/ccordoba12)

In this release 5 pull requests were closed.

----

## Version 1.9.0 (2020-03-14)

### New features

* Allow IPython magics in code again.
* Allow PyQt applications to be run multiple times.
* Remove `__file__` after running a file.

### Pull Requests Merged

* [PR 209](https://github.com/spyder-ide/spyder-kernels/pull/209) - PR: Improve message about using invalid syntax in cells and files, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 208](https://github.com/spyder-ide/spyder-kernels/pull/208) - PR: Add flag to override data and handle NpzFile instances, by [@dalthviz](https://github.com/dalthviz)
* [PR 206](https://github.com/spyder-ide/spyder-kernels/pull/206) - PR: Move CI to github actions on branch 1.x, by [@goanpeca](https://github.com/goanpeca)
* [PR 204](https://github.com/spyder-ide/spyder-kernels/pull/204) - PR: Remove load_exception in CommBase, by [@impact27](https://github.com/impact27)
* [PR 200](https://github.com/spyder-ide/spyder-kernels/pull/200) - PR: Fix %varexp namespace, by [@impact27](https://github.com/impact27) ([6695](https://github.com/spyder-ide/spyder/issues/6695))
* [PR 199](https://github.com/spyder-ide/spyder-kernels/pull/199) - PR: Prevent completion from changing local objects while debugging, by [@impact27](https://github.com/impact27)
* [PR 198](https://github.com/spyder-ide/spyder-kernels/pull/198) - PR: Add method to check dependencies for special consoles, by [@dalthviz](https://github.com/dalthviz)
* [PR 195](https://github.com/spyder-ide/spyder-kernels/pull/195) - PR: Give access to the running namespace when refreshing variables, by [@impact27](https://github.com/impact27)
* [PR 193](https://github.com/spyder-ide/spyder-kernels/pull/193) - PR: Update test to work with IPython 7.10+, by [@impact27](https://github.com/impact27)
* [PR 192](https://github.com/spyder-ide/spyder-kernels/pull/192) - PR: Resend comm configuration on timeout, by [@impact27](https://github.com/impact27)
* [PR 190](https://github.com/spyder-ide/spyder-kernels/pull/190) - PR: Allow IPython magics in code again, by [@impact27](https://github.com/impact27) ([11023](https://github.com/spyder-ide/spyder/issues/11023))
* [PR 189](https://github.com/spyder-ide/spyder-kernels/pull/189) - PR: Patch PyQt to save created QApplication instances, by [@impact27](https://github.com/impact27) ([2970](https://github.com/spyder-ide/spyder/issues/2970))
* [PR 187](https://github.com/spyder-ide/spyder-kernels/pull/187) - PR: Remove `__file__` after running script, by [@impact27](https://github.com/impact27) ([1918](https://github.com/spyder-ide/spyder/issues/1918))

In this release 13 pull requests were closed.

----

## Version 1.8.1 (2019-12-05)


### Pull Requests Merged

* [PR 185](https://github.com/spyder-ide/spyder-kernels/pull/185) - PR: Process first frame in Pdb

In this release 1 pull request was closed.

----

## Version 1.8.0 (2019-11-18)

### New features

* Add an option to exclude callables and modules in namespace view.
* Add methods to update `sys.path` from Spyder.
* Add an option to execute IPython events in Pdb.

### Pull Requests Merged

* [PR 183](https://github.com/spyder-ide/spyder-kernels/pull/183) - PR: Add an option to namespace view settings to exclude callables and modules
* [PR 182](https://github.com/spyder-ide/spyder-kernels/pull/182) - PR: Use IPython completer for Pdb
* [PR 181](https://github.com/spyder-ide/spyder-kernels/pull/181) - PR: Add path update methods
* [PR 180](https://github.com/spyder-ide/spyder-kernels/pull/180) - PR: Cleanup spydercustomize
* [PR 179](https://github.com/spyder-ide/spyder-kernels/pull/179) - PR: Use a timeout in CommBase if a call passes one different from None
* [PR 178](https://github.com/spyder-ide/spyder-kernels/pull/178) - PR: Correctly set namespace while debugging
* [PR 175](https://github.com/spyder-ide/spyder-kernels/pull/175) - PR: Add an option to execute IPython events in Pdb
* [PR 174](https://github.com/spyder-ide/spyder-kernels/pull/174) - PR: Prevent pdb syntax error from blocking the console ([10588](https://github.com/spyder-ide/spyder/issues/10588))

In this release 8 pull requests were closed.

----

## Version 1.7.0 (2019-11-02)

### New features

* Create a new ZMQ socket for comms.
* Allow different frontends to have different pickle
  protocols.
* Add a way to ignore installed Python libraries while
  debugging

### Pull Requests Merged

* [PR 177](https://github.com/spyder-ide/spyder-kernels/pull/177) - PR: Update ipykernel required version ([2902](https://github.com/spyder-ide/spyder/issues/2902))
* [PR 176](https://github.com/spyder-ide/spyder-kernels/pull/176) - PR: Improve displayed type and value for generic objects
* [PR 169](https://github.com/spyder-ide/spyder-kernels/pull/169) - PR: Create a Comm socket
* [PR 168](https://github.com/spyder-ide/spyder-kernels/pull/168) - PR: Require more recent version of jupyter-client
* [PR 167](https://github.com/spyder-ide/spyder-kernels/pull/167) - PR: Don't demand that a file exists in Pdb
* [PR 166](https://github.com/spyder-ide/spyder-kernels/pull/166) - PR: Allow different frontends to have different pickle protocols
* [PR 152](https://github.com/spyder-ide/spyder-kernels/pull/152) - PR: Add a way to ignore installed Python libraries while debugging

In this release 7 pull requests were closed.

----

## Version 1.6.0 (2019-10-16)

### New features

* Allow IPython magics in Pdb.
* Allow Pdb to run multiline statments.
* Make `runfile` to retrieve code from Spyder.
* Add code completion to Pdb.

### Issues Closed

* [Issue 139](https://github.com/spyder-ide/spyder-kernels/issues/139) - Regression: runfile doesn't execute ipython magic ([PR 143](https://github.com/spyder-ide/spyder-kernels/pull/143))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 163](https://github.com/spyder-ide/spyder-kernels/pull/163) - PR: Fix tests that use setup_kernel
* [PR 162](https://github.com/spyder-ide/spyder-kernels/pull/162) - PR: Improve Pdb sigint handler
* [PR 161](https://github.com/spyder-ide/spyder-kernels/pull/161) - PR: Fix post-mortem debugging
* [PR 157](https://github.com/spyder-ide/spyder-kernels/pull/157) - PR: Fix breakpoint update ([10290](https://github.com/spyder-ide/spyder/issues/10290))
* [PR 154](https://github.com/spyder-ide/spyder-kernels/pull/154) - PR: Allow IPython magics in Pdb
* [PR 153](https://github.com/spyder-ide/spyder-kernels/pull/153) - PR: Add a setting to disable printing the stack on every Pdb command
* [PR 151](https://github.com/spyder-ide/spyder-kernels/pull/151) - PR: Remove Pdb Monkeypatching
* [PR 148](https://github.com/spyder-ide/spyder-kernels/pull/148) - PR: Allow Pdb to run multiline statments
* [PR 143](https://github.com/spyder-ide/spyder-kernels/pull/143) - PR: Make runfile to retrieve code from the Spyder editor and add it to linecache ([1643](https://github.com/spyder-ide/spyder/issues/1643), [139](https://github.com/spyder-ide/spyder-kernels/issues/139))
* [PR 133](https://github.com/spyder-ide/spyder-kernels/pull/133) - PR: Add code completion to Pdb

In this release 10 pull requests were closed.

----

## Version 1.5.0 (2019-09-15)

### New features

* Add a new debugcell builtin command.
* Make runfile work in an empty namespace by default.
* Improve the display of tracebacks.
* Use the highest pickle protocol available to serialize data.
* Use Jupyter comms to communicate with the Spyder frontend.
* This release also contains all fixes present in versions 0.5.1
  and 0.5.2.

### Issues Closed

* [Issue 147](https://github.com/spyder-ide/spyder-kernels/issues/147) - debugfile() got an unexpected keyword argument 'current_namespace' ([PR 150](https://github.com/spyder-ide/spyder-kernels/pull/150))
* [Issue 145](https://github.com/spyder-ide/spyder-kernels/issues/145) - KeyError on comms when restarting the kernel ([PR 146](https://github.com/spyder-ide/spyder-kernels/pull/146))
* [Issue 97](https://github.com/spyder-ide/spyder-kernels/issues/97) - Can't repeat runcell from terminal ([PR 112](https://github.com/spyder-ide/spyder-kernels/pull/112))
* [Issue 73](https://github.com/spyder-ide/spyder-kernels/issues/73) - Select a higher Pickle protocol in case Spyder and the kernel are running in Python 3.4+ ([PR 111](https://github.com/spyder-ide/spyder-kernels/pull/111))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 150](https://github.com/spyder-ide/spyder-kernels/pull/150) - PR: Add current_namespace kwarg to debugfile ([147](https://github.com/spyder-ide/spyder-kernels/issues/147))
* [PR 146](https://github.com/spyder-ide/spyder-kernels/pull/146) - PR: Set closed flag before deleting comms  ([145](https://github.com/spyder-ide/spyder-kernels/issues/145))
* [PR 144](https://github.com/spyder-ide/spyder-kernels/pull/144) - PR: Solve error with exit command not being defined in the debugger
* [PR 142](https://github.com/spyder-ide/spyder-kernels/pull/142) - PR: Set debug state before asking for input
* [PR 140](https://github.com/spyder-ide/spyder-kernels/pull/140) - PR: Update jupyter-client minimal required version
* [PR 137](https://github.com/spyder-ide/spyder-kernels/pull/137) - PR: Add a way to change foreground color of Sympy repr's
* [PR 136](https://github.com/spyder-ide/spyder-kernels/pull/136) - PR: Ask the frontend to save files before running them
* [PR 134](https://github.com/spyder-ide/spyder-kernels/pull/134) - PR: Improve the display of tracebacks and better handle namespace and __file__ during execution
* [PR 131](https://github.com/spyder-ide/spyder-kernels/pull/131) - PR: Make runfile work in an empty namespace
* [PR 130](https://github.com/spyder-ide/spyder-kernels/pull/130) - PR: Add .pickle files to .gitignore
* [PR 128](https://github.com/spyder-ide/spyder-kernels/pull/128) - PR: Fix deprecated import
* [PR 112](https://github.com/spyder-ide/spyder-kernels/pull/112) - PR: Use the comms API to improve runcell and add a new debugcell command ([97](https://github.com/spyder-ide/spyder-kernels/issues/97))
* [PR 111](https://github.com/spyder-ide/spyder-kernels/pull/111) - PR: Use Jupyter comms to communicate with the Spyder frontend ([73](https://github.com/spyder-ide/spyder-kernels/issues/73))

In this release 13 pull requests were closed.

----

## Version 1.4.0 (2019-06-24)

### New features

* Add entries necessary for the new Object Explorer to
  REMOTE_SETTINGS.
* This release also contains all features and fixes present in
  version 0.5.0

### Pull Requests Merged

* [PR 100](https://github.com/spyder-ide/spyder-kernels/pull/100) - PR: Add object explorer settings to REMOTE_SETTINGS

In this release 1 pull request was closed.

----

## Version 1.3.3 (2019-04-08)

### New features
* This release contains all features and fixes present in versions
  0.4.3 and 0.4.4

### Issues Closed

* [Issue 93](https://github.com/spyder-ide/spyder-kernels/issues/93) - test_np_threshold is failing ([PR 95](https://github.com/spyder-ide/spyder-kernels/pull/95))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 95](https://github.com/spyder-ide/spyder-kernels/pull/95) - PR: Change np.nan for np.inf in test_np_threshold ([93](https://github.com/spyder-ide/spyder-kernels/issues/93))

In this release 1 pull request was closed.

----

## Version 1.3.2 (2019-02-10)

Sister release for 0.4.2

----

## Version 1.3.1 (2019-02-03)

Sister release for 0.4.1

----

## Version 1.3.0 (2019-02-02)

### New features
* Make runcell set __file__ to the path of the file containing the cell
* This release also contains all features and fixes present in version
  0.4.

### Issues Closed

* [Issue 78](https://github.com/spyder-ide/spyder-kernels/issues/78) - Nopython jit of numba is not working in runcell ([PR 79](https://github.com/spyder-ide/spyder-kernels/pull/79))
* [Issue 76](https://github.com/spyder-ide/spyder-kernels/issues/76) - Detect the name of the file currently running the cell ([PR 77](https://github.com/spyder-ide/spyder-kernels/pull/77))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 79](https://github.com/spyder-ide/spyder-kernels/pull/79) - PR: Remove user module reloader from runcell ([78](https://github.com/spyder-ide/spyder-kernels/issues/78))
* [PR 77](https://github.com/spyder-ide/spyder-kernels/pull/77) - PR: Have runcell set __file__ to the path of the file containing the cell  ([76](https://github.com/spyder-ide/spyder-kernels/issues/76))
* [PR 72](https://github.com/spyder-ide/spyder-kernels/pull/72) - PR: Fix numpy printoptions format ([7885](https://github.com/spyder-ide/spyder/issues/7885))

In this release 3 pull requests were closed.

----

## Version 1.2 (2018-12-26)

### New features
* Add the `runcell` command to run cells from Spyder's editor
  without pasting their contents in the console.
* This release also contains all features and fixes present in
  version 0.3.

### Issues Closed

* [Issue 57](https://github.com/spyder-ide/spyder-kernels/issues/57) - Add a test for runcell ([PR 70](https://github.com/spyder-ide/spyder-kernels/pull/70))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 70](https://github.com/spyder-ide/spyder-kernels/pull/70) - PR: Add a test for the runcell command ([57](https://github.com/spyder-ide/spyder-kernels/issues/57))
* [PR 69](https://github.com/spyder-ide/spyder-kernels/pull/69) - PR: Start testing in macOS
* [PR 67](https://github.com/spyder-ide/spyder-kernels/pull/67) - PR: Drop using ci-helpers in our CIs
* [PR 58](https://github.com/spyder-ide/spyder-kernels/pull/58) - PR: runcell trigger post_execute before run_cell to end the run_cell pre_execute
* [PR 7](https://github.com/spyder-ide/spyder-kernels/pull/7) - PR: Add runcell to spydercustomize

In this release 5 pull requests were closed.

----

## Version 1.1 (2018-08-11)

### Issues Closed

* [Issue 14](https://github.com/spyder-ide/spyder-kernels/issues/14) - Startup lines to split with semicolon instead of comma ([PR 15](https://github.com/spyder-ide/spyder-kernels/pull/15))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 15](https://github.com/spyder-ide/spyder-kernels/pull/15) - PR: Separate startup run_lines with semicolon instead of comma ([14](https://github.com/spyder-ide/spyder-kernels/issues/14))

In this release 1 pull request was closed.

----

## Version 1.0.3 (2018-08-09)

Sister release for 0.2.6

----

## Version 1.0.2 (2018-08-09)

Sister release for 0.2.5

----

## Version 1.0.1 (2018-06-25)

Sister release for 0.2.4

----

## Version 1.0.0 (2018-06-24)

Initial release for Spyder 4

----

## Version 0.5.2 (2019-09-15)

### Issues Closed

* [Issue 132](https://github.com/spyder-ide/spyder-kernels/issues/132) - tests use removed pandas.Panel ([PR 135](https://github.com/spyder-ide/spyder-kernels/pull/135))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 149](https://github.com/spyder-ide/spyder-kernels/pull/149) - PR: Add xarray to our test deps in setup.py
* [PR 135](https://github.com/spyder-ide/spyder-kernels/pull/135) - PR: Replace usage of Pandas Panel for Xarray Dataset in our tests ([132](https://github.com/spyder-ide/spyder-kernels/issues/132))

In this release 2 pull requests were closed.

----

## Version 0.5.1 (2019-07-11)

### Issues Closed

* [Issue 121](https://github.com/spyder-ide/spyder-kernels/issues/121) - Add test requirements to setup.py ([PR 122](https://github.com/spyder-ide/spyder-kernels/pull/122))
* [Issue 120](https://github.com/spyder-ide/spyder-kernels/issues/120) - Backport CI configuration from master to 0.x ([PR 123](https://github.com/spyder-ide/spyder-kernels/pull/123))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 125](https://github.com/spyder-ide/spyder-kernels/pull/125) - PR: Fix not including tests in tarballs and wheels
* [PR 123](https://github.com/spyder-ide/spyder-kernels/pull/123) - PR: Backport CI configuration from master to 0.x ([120](https://github.com/spyder-ide/spyder-kernels/issues/120))
* [PR 122](https://github.com/spyder-ide/spyder-kernels/pull/122) - PR: Add tests requirements to setup.py ([121](https://github.com/spyder-ide/spyder-kernels/issues/121))

In this release 3 pull requests were closed.

----

## Version 0.5.0 (2019-06-23)

### New features

* Set Matplotlib backend to inline for kernels started in a terminal.
* Handle option sent from Spyder to show/hide cmd windows generated
  by the subprocess module.

### Issues Closed

* [Issue 108](https://github.com/spyder-ide/spyder-kernels/issues/108) - Set matplotlib backend to inline by default on starting a new kernel ([PR 110](https://github.com/spyder-ide/spyder-kernels/pull/110))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 110](https://github.com/spyder-ide/spyder-kernels/pull/110) - PR: Set Matplotlib backend to inline for kernels started outside Spyder ([108](https://github.com/spyder-ide/spyder-kernels/issues/108))
* [PR 107](https://github.com/spyder-ide/spyder-kernels/pull/107) - PR: Use Readme.md for long description in PyPi
* [PR 104](https://github.com/spyder-ide/spyder-kernels/pull/104) - PR: Handle option to show/hide cmd windows generated by the subprocess module

In this release 3 pull requests were closed.

----

## Version 0.4.4 (2019-04-08)

### Issues Closed

* [Issue 102](https://github.com/spyder-ide/spyder-kernels/issues/102) - Tkinter is now required for version 0.4.3 after patching the turtle code ([PR 103](https://github.com/spyder-ide/spyder-kernels/pull/103))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 106](https://github.com/spyder-ide/spyder-kernels/pull/106) - PR: Skip test_turtle_launch if Tk is not installed
* [PR 103](https://github.com/spyder-ide/spyder-kernels/pull/103) - PR: Enclose turtle customizations in a try/except to avoid a dependency on Tk ([102](https://github.com/spyder-ide/spyder-kernels/issues/102))

In this release 2 pull requests were closed.

----

## Version 0.4.3 (2019-03-31)

### Issues Closed

* [Issue 91](https://github.com/spyder-ide/spyder-kernels/issues/91) - KeyError when running "%reset -f" programmatically ([PR 96](https://github.com/spyder-ide/spyder-kernels/pull/96))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 96](https://github.com/spyder-ide/spyder-kernels/pull/96) - PR:  Avoid error when trying to pop __file__ out of the current namespace ([91](https://github.com/spyder-ide/spyder-kernels/issues/91))
* [PR 92](https://github.com/spyder-ide/spyder-kernels/pull/92) - PR: Include user site-packages directory in the list of excluded paths by the UMR ([8776](https://github.com/spyder-ide/spyder/issues/8776))
* [PR 90](https://github.com/spyder-ide/spyder-kernels/pull/90) - PR: Patch turtle.bye to make it work with multiple runnings of the same code ([6278](https://github.com/spyder-ide/spyder/issues/6278))

In this release 3 pull requests were closed.

----

## Version 0.4.2 (2019-02-07)

### Issues Closed

* [Issue 85](https://github.com/spyder-ide/spyder-kernels/issues/85) - NameError: name 'modpath' is not defined ([PR 86](https://github.com/spyder-ide/spyder-kernels/pull/86))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 88](https://github.com/spyder-ide/spyder-kernels/pull/88) - PR: Improve Cython activation
* [PR 87](https://github.com/spyder-ide/spyder-kernels/pull/87) - PR: Fix running Cython files
* [PR 86](https://github.com/spyder-ide/spyder-kernels/pull/86) - PR: Fix problems with UMR's run method ([85](https://github.com/spyder-ide/spyder-kernels/issues/85))

In this release 3 pull requests were closed.

----

## Version 0.4.1 (2019-02-03)

### Pull Requests Merged

* [PR 84](https://github.com/spyder-ide/spyder-kernels/pull/84) - PR: Better way to skip standard library and site-packages modules from UMR
* [PR 83](https://github.com/spyder-ide/spyder-kernels/pull/83) - PR: Blacklist tensorflow from the UMR ([8697](https://github.com/spyder-ide/spyder/issues/8697))

In this release 2 pull requests were closed.

----

## Version 0.4 (2019-02-02)

### New features
* This release fixes several important issues that prevented
  saving the current namespace to work as expected.

### Issues Closed

* [Issue 75](https://github.com/spyder-ide/spyder-kernels/issues/75) - Namespace serialization silently fails if any object is unserializable, e.g. a Python module ([PR 81](https://github.com/spyder-ide/spyder-kernels/pull/81))
* [Issue 9](https://github.com/spyder-ide/spyder-kernels/issues/9) - Spydata files won't import if the original filename is changed ([PR 80](https://github.com/spyder-ide/spyder-kernels/pull/80))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 82](https://github.com/spyder-ide/spyder-kernels/pull/82) - PR: Enclose calls to load wurlitzer and autoreload in try/except's ([8668](https://github.com/spyder-ide/spyder/issues/8668))
* [PR 81](https://github.com/spyder-ide/spyder-kernels/pull/81) - PR: Fix and improve saving of Spyder namespace with many types of objects ([75](https://github.com/spyder-ide/spyder-kernels/issues/75))
* [PR 80](https://github.com/spyder-ide/spyder-kernels/pull/80) - PR: Fix loading Spydata file with changed filename and other edge-cases in load_dict ([9](https://github.com/spyder-ide/spyder-kernels/issues/9))

In this release 3 pull requests were closed.

----

## Version 0.3 (2018-11-23)

### New features
* Add Wurlitzer as a new dependency on Posix systems.
* Add tests for the console kernel.

### Issues Closed

* [Issue 62](https://github.com/spyder-ide/spyder-kernels/issues/62) - Add support for AppVeyor ([PR 63](https://github.com/spyder-ide/spyder-kernels/pull/63))
* [Issue 60](https://github.com/spyder-ide/spyder-kernels/issues/60) - Only load Wurlitzer in Posix systems ([PR 64](https://github.com/spyder-ide/spyder-kernels/pull/64))
* [Issue 23](https://github.com/spyder-ide/spyder-kernels/issues/23) - Add tests for the console kernel ([PR 37](https://github.com/spyder-ide/spyder-kernels/pull/37))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 64](https://github.com/spyder-ide/spyder-kernels/pull/64) - PR: Don't load Wurlitzer extension on Windows because it has no effect there ([60](https://github.com/spyder-ide/spyder-kernels/issues/60))
* [PR 63](https://github.com/spyder-ide/spyder-kernels/pull/63) - PR: Test on Windows with Appveyor ([62](https://github.com/spyder-ide/spyder-kernels/issues/62))
* [PR 61](https://github.com/spyder-ide/spyder-kernels/pull/61) - PR: Patch multiprocessing to make it work when all variables are removed ([8128](https://github.com/spyder-ide/spyder/issues/8128))
* [PR 59](https://github.com/spyder-ide/spyder-kernels/pull/59) - PR: Filter deprecation warnings in ipykernel ([8103](https://github.com/spyder-ide/spyder/issues/8103))
* [PR 56](https://github.com/spyder-ide/spyder-kernels/pull/56) - PR: Add Wurlitzer to Readme
* [PR 55](https://github.com/spyder-ide/spyder-kernels/pull/55) - PR: Exclude all tests from our tarballs
* [PR 54](https://github.com/spyder-ide/spyder-kernels/pull/54) - PR: Add the Wurlitzer package to capture stdout/stderr from C libraries ([3777](https://github.com/spyder-ide/spyder/issues/3777))
* [PR 53](https://github.com/spyder-ide/spyder-kernels/pull/53) - PR: Remove current working directory from sys.path before starting the console kernel ([8007](https://github.com/spyder-ide/spyder/issues/8007))
* [PR 37](https://github.com/spyder-ide/spyder-kernels/pull/37) - PR: Initial tests for the console kernel ([23](https://github.com/spyder-ide/spyder-kernels/issues/23))
* [PR 36](https://github.com/spyder-ide/spyder-kernels/pull/36) - PR: Make tests to really fail in CircleCI
* [PR 21](https://github.com/spyder-ide/spyder-kernels/pull/21) - PR: Add AUTHORS.txt in MANIFEST.in to include in package

In this release 11 pull requests were closed.

----

## Version 0.2.6 (2018-08-09)

### Pull Requests Merged

* [PR 20](https://github.com/spyder-ide/spyder-kernels/pull/20) - PR: Include license file again in tarball

In this release 1 pull request was closed.

----

## Version 0.2.5 (2018-08-09)

### Pull Requests Merged

* [PR 19](https://github.com/spyder-ide/spyder-kernels/pull/19) - PR: Fix inconsistent EOLs
* [PR 18](https://github.com/spyder-ide/spyder-kernels/pull/18) - PR: Fix legal texts and make them consistent across all files
* [PR 17](https://github.com/spyder-ide/spyder-kernels/pull/17) - PR: Add/update descriptions, links and metadata in setup.py
* [PR 16](https://github.com/spyder-ide/spyder-kernels/pull/16) - PR: Include test suite in manifest
* [PR 11](https://github.com/spyder-ide/spyder-kernels/pull/11) - PR: Add codecov support to see coverage
* [PR 10](https://github.com/spyder-ide/spyder-kernels/pull/10) - PR: Start testing with CircleCI
* [PR 8](https://github.com/spyder-ide/spyder-kernels/pull/8) - PR: Demand specific dependency versions needed by Spyder

In this release 7 pull requests were closed.

----

## Version 0.2.4 (2018-06-25)

### Pull Requests Merged

* [PR 6](https://github.com/spyder-ide/spyder-kernels/pull/6) - PR: Handle deprecated 'summary' method for Pandas

In this release 1 pull request was closed.

----

## Version 0.2.3 (2018-06-23)

### Pull Requests Merged

* [PR 5](https://github.com/spyder-ide/spyder-kernels/pull/5) - PR: Add __version__ to package's init

In this release 1 pull request was closed.

----

## Version 0.2.2 (2018-06-22)

### Pull Requests Merged

* [PR 4](https://github.com/spyder-ide/spyder-kernels/pull/4) - PR: Fix debugging in Python 2

In this release 1 pull request was closed.

----

## Version 0.2.1 (2018-06-22)

### Pull Requests Merged

* [PR 3](https://github.com/spyder-ide/spyder-kernels/pull/3) - PR: Fix debugging

In this release 1 pull request was closed.

----

## Version 0.2 (2018-06-20)

### Pull Requests Merged

* [PR 2](https://github.com/spyder-ide/spyder-kernels/pull/2) - PR: Import our customizations directly here
* [PR 1](https://github.com/spyder-ide/spyder-kernels/pull/1) - PR: Fix some errors in sitecustomize

In this release 2 pull requests were closed.

----

## Version 0.1 (2018-06-18)

Initial release
