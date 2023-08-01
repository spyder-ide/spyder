# History of changes for Spyder 5

## Version 5.4.4 (2023-07-17)

### New features

* Add new shortcuts to switch Editor tabs for macOS (`Cmd + 8` and `Cmd + 9`)
* Add syntax highlighting for Python 3.10 missing statements (`match` and `case`)
* Improve compatibility with PySide2
* Improve Editor scrollflags painting (find matches flags painted above errors and warnings flags)

### Important fixes

* Fix crash when plugins fail their compatibility checks
* Fix LSP status bar error when cliking it
* Fix IPython console font size setting
* Prevent IPython console `This version of python seems to be incorrectly compiled` warning message in Python 3.11
* Skip some IPython versions with somes bugs and add some error catching for the IPython console
* Fix Editor found results rehighlighting when switching between files
* Fix Editor class/function dropdown widget when using splited editors
* Fix Editor line numbers and autoformat cursor position when the wrap lines option is enabled
* Fix Editor error when removing unsaved files from Projects/Files explorer while open in the Editor
* Prevent Editor `QTextCursor::setPosition: Position '-1' out of range` warning message
* Fix Find functionality for a single file
* Fix PYTHONPATH manager focus issues after adding a path
* Fix Online Help issues when searching for `numpy` or `pandas`
* Fix Windows installer being launched with admin rights after installation/autoupdate
* Fix Windows installer conda environments activation logic when there are spaces in the installation path
* Fix macOS standalone installer workflow and notarization process with new certificate

### Issues Closed

* [Issue 21127](https://github.com/spyder-ide/spyder/issues/21127) - LSP status crashes after reset, code logic error ([PR 21128](https://github.com/spyder-ide/spyder/pull/21128) by [@dpizetta](https://github.com/dpizetta))
* [Issue 21074](https://github.com/spyder-ide/spyder/issues/21074) - Spyder crashes when launching after Windows standalone installation ([PR 21082](https://github.com/spyder-ide/spyder/pull/21082) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21063](https://github.com/spyder-ide/spyder/issues/21063) - Spyder 5.4.4 release ([PR 21155](https://github.com/spyder-ide/spyder/pull/21155) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21028](https://github.com/spyder-ide/spyder/issues/21028) - Minor bug with empty files: `QTextCursor::setPosition: Position '-1' out of range` ([PR 21031](https://github.com/spyder-ide/spyder/pull/21031) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21017](https://github.com/spyder-ide/spyder/issues/21017) - Invoking `warnings.simplefilter` in the console results in an exception ([PR 21056](https://github.com/spyder-ide/spyder/pull/21056) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21012](https://github.com/spyder-ide/spyder/issues/21012) - `psutil.NoSuchProcess` is raised when killing kernel ([PR 21020](https://github.com/spyder-ide/spyder/pull/21020) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20998](https://github.com/spyder-ide/spyder/issues/20998) - Error when deleting several unsaved files from project while open in editor ([PR 21003](https://github.com/spyder-ide/spyder/pull/21003) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20964](https://github.com/spyder-ide/spyder/issues/20964) - Find in files gives error when searching in just one file ([PR 20971](https://github.com/spyder-ide/spyder/pull/20971) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20963](https://github.com/spyder-ide/spyder/issues/20963) - Syntax highlight new Python 3.10 statements is missing ([PR 21042](https://github.com/spyder-ide/spyder/pull/21042) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20907](https://github.com/spyder-ide/spyder/issues/20907) - App association error ([PR 20948](https://github.com/spyder-ide/spyder/pull/20948) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20871](https://github.com/spyder-ide/spyder/issues/20871) - Autocomplete fails at second level (IPython console) ([PR 21019](https://github.com/spyder-ide/spyder/pull/21019) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20866](https://github.com/spyder-ide/spyder/issues/20866) - Error when searching numpy and pandas in Online Help widget ([PR 20870](https://github.com/spyder-ide/spyder/pull/20870) by [@mrclary](https://github.com/mrclary))
* [Issue 20852](https://github.com/spyder-ide/spyder/issues/20852) - Auto-format sometimes jumps to a different position if Editor > Display > Wrap lines is set ([PR 21038](https://github.com/spyder-ide/spyder/pull/21038) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20834](https://github.com/spyder-ide/spyder/issues/20834) - Spyder standalone bundle workflow fails ([PR 20835](https://github.com/spyder-ide/spyder/pull/20835) by [@mrclary](https://github.com/mrclary))
* [Issue 20816](https://github.com/spyder-ide/spyder/issues/20816) - `ValueError: The truth value of a DataFrame is ambiguous` when working with Dataframes ([PR 21019](https://github.com/spyder-ide/spyder/pull/21019) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20808](https://github.com/spyder-ide/spyder/issues/20808) - PYTHONPATH manager just closes after upgrade to 5.4.3 in the Mac app ([PR 20812](https://github.com/spyder-ide/spyder/pull/20812) by [@mrclary](https://github.com/mrclary))
* [Issue 20802](https://github.com/spyder-ide/spyder/issues/20802) - Incorrect line numbers displayed after line wrapping in the source code editor ([PR 21037](https://github.com/spyder-ide/spyder/pull/21037) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20800](https://github.com/spyder-ide/spyder/issues/20800) - `This version of python seems to be incorrectly compiled` message with Python 3.11 from Anaconda ([PR 20947](https://github.com/spyder-ide/spyder/pull/20947) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20798](https://github.com/spyder-ide/spyder/issues/20798) - Some errors that occur when using the Find plugin
* [Issue 20774](https://github.com/spyder-ide/spyder/issues/20774) - Spyder 5.4.3 launched with administrative rights through auto-updater
* [Issue 20716](https://github.com/spyder-ide/spyder/issues/20716) - The text size in the IPython console changes depending on the code run on it ([PR 21059](https://github.com/spyder-ide/spyder/pull/21059) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20639](https://github.com/spyder-ide/spyder/issues/20639) - Error debugging Plotly code in Spyder 5.4.1 ([PR 21018](https://github.com/spyder-ide/spyder/pull/21018) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20602](https://github.com/spyder-ide/spyder/issues/20602) - Code analysis doesn't work if there are multiple symlinks to python directory in lib folder ([PR 21034](https://github.com/spyder-ide/spyder/pull/21034) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16562](https://github.com/spyder-ide/spyder/issues/16562) - Cannot activate conda env when created in a path ([PR 20758](https://github.com/spyder-ide/spyder/pull/20758) by [@dalthviz](https://github.com/dalthviz))
* [Issue 1741](https://github.com/spyder-ide/spyder/issues/1741) - Provide better keyboard shortcuts to switch editor tabs on Mac ([PR 21111](https://github.com/spyder-ide/spyder/pull/21111) by [@ryohei22](https://github.com/ryohei22))

In this release 25 issues were closed.

### Pull Requests Merged

* [PR 21155](https://github.com/spyder-ide/spyder/pull/21155) - PR: Update core dependencies for 5.4.4, by [@dalthviz](https://github.com/dalthviz) ([21063](https://github.com/spyder-ide/spyder/issues/21063))
* [PR 21154](https://github.com/spyder-ide/spyder/pull/21154) - PR: Fix notarizing for 5.x branch, by [@mrclary](https://github.com/mrclary)
* [PR 21140](https://github.com/spyder-ide/spyder/pull/21140) - PR: Prevent failures when Codecov action fails and switch to `setup-micromamba` (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21128](https://github.com/spyder-ide/spyder/pull/21128) - PR: Fix LSP status widget logic when it is `None` using early return, by [@dpizetta](https://github.com/dpizetta) ([21127](https://github.com/spyder-ide/spyder/issues/21127))
* [PR 21111](https://github.com/spyder-ide/spyder/pull/21111) - PR: Add better shortcuts to switch editor tabs for macOS, by [@ryohei22](https://github.com/ryohei22) ([1741](https://github.com/spyder-ide/spyder/issues/1741))
* [PR 21085](https://github.com/spyder-ide/spyder/pull/21085) - PR: Rehighlight found results in the editor when switching between files, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21082](https://github.com/spyder-ide/spyder/pull/21082) - PR: Fix crash at startup when plugins fail their compatibility checks, by [@ccordoba12](https://github.com/ccordoba12) ([21074](https://github.com/spyder-ide/spyder/issues/21074))
* [PR 21061](https://github.com/spyder-ide/spyder/pull/21061) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 21060](https://github.com/spyder-ide/spyder/pull/21060) - PR: Update translations for 5.4.4, by [@dalthviz](https://github.com/dalthviz)
* [PR 21059](https://github.com/spyder-ide/spyder/pull/21059) - PR: Save fonts with delta in our font cache (Config), by [@ccordoba12](https://github.com/ccordoba12) ([20716](https://github.com/spyder-ide/spyder/issues/20716))
* [PR 21056](https://github.com/spyder-ide/spyder/pull/21056) - PR: Fix showing a PyZMQ warning when filtering warnings, by [@ccordoba12](https://github.com/ccordoba12) ([21017](https://github.com/spyder-ide/spyder/issues/21017))
* [PR 21042](https://github.com/spyder-ide/spyder/pull/21042) - PR: Make `match` and `case` be highlighted as Python keywords (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20963](https://github.com/spyder-ide/spyder/issues/20963))
* [PR 21038](https://github.com/spyder-ide/spyder/pull/21038) - PR: Use cursor `position` instead of `blockNumber` when restoring cursor after format (Editor), by [@dalthviz](https://github.com/dalthviz) ([20852](https://github.com/spyder-ide/spyder/issues/20852))
* [PR 21037](https://github.com/spyder-ide/spyder/pull/21037) - PR: Fix line number painting when wrap text option is active (Editor), by [@dalthviz](https://github.com/dalthviz) ([20802](https://github.com/spyder-ide/spyder/issues/20802))
* [PR 21034](https://github.com/spyder-ide/spyder/pull/21034) - PR: Increase minimal required version of pylint-venv (Code analysis), by [@ccordoba12](https://github.com/ccordoba12) ([20602](https://github.com/spyder-ide/spyder/issues/20602))
* [PR 21031](https://github.com/spyder-ide/spyder/pull/21031) - PR: Prevent setting cursor in a negative position (Editor), by [@dalthviz](https://github.com/dalthviz) ([21028](https://github.com/spyder-ide/spyder/issues/21028))
* [PR 21020](https://github.com/spyder-ide/spyder/pull/21020) - PR: Catch an error when trying to kill the kernel children processes (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([21012](https://github.com/spyder-ide/spyder/issues/21012))
* [PR 21019](https://github.com/spyder-ide/spyder/pull/21019) - PR: Skip more buggy IPython versions, by [@ccordoba12](https://github.com/ccordoba12) ([20871](https://github.com/spyder-ide/spyder/issues/20871), [20816](https://github.com/spyder-ide/spyder/issues/20816))
* [PR 21018](https://github.com/spyder-ide/spyder/pull/21018) - PR: Disable IPython's debugger skip functionality by default (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([20639](https://github.com/spyder-ide/spyder/issues/20639))
* [PR 21003](https://github.com/spyder-ide/spyder/pull/21003) - PR: Prevent error when removing several unsaved files from Projects or Files (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20998](https://github.com/spyder-ide/spyder/issues/20998))
* [PR 20971](https://github.com/spyder-ide/spyder/pull/20971) - PR: Fix searching in a single file (Find), by [@ccordoba12](https://github.com/ccordoba12) ([20964](https://github.com/spyder-ide/spyder/issues/20964))
* [PR 20970](https://github.com/spyder-ide/spyder/pull/20970) - PR: Paint find matches above errors and warnings in scrollflags, by [@athompson673](https://github.com/athompson673)
* [PR 20961](https://github.com/spyder-ide/spyder/pull/20961) - PR: Fix class/function selector for split editors (Editor), by [@rear1019](https://github.com/rear1019)
* [PR 20954](https://github.com/spyder-ide/spyder/pull/20954) - PR: Backport PR 20952 (Add support for the future `python-lsp-black` 2.0 version), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20948](https://github.com/spyder-ide/spyder/pull/20948) - PR: Catch `PermissionsError` when trying to get applications executables (Files), by [@dalthviz](https://github.com/dalthviz) ([20907](https://github.com/spyder-ide/spyder/issues/20907))
* [PR 20947](https://github.com/spyder-ide/spyder/pull/20947) - PR: Add `-Xfrozen_modules` flag to prevent Python incorrectly compiled message (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([20800](https://github.com/spyder-ide/spyder/issues/20800))
* [PR 20870](https://github.com/spyder-ide/spyder/pull/20870) - PR: Fix errors with OnlineHelp plugin regarding readonly properties and ModuleScanner errors, by [@mrclary](https://github.com/mrclary) ([20866](https://github.com/spyder-ide/spyder/issues/20866))
* [PR 20838](https://github.com/spyder-ide/spyder/pull/20838) - PR: Remove installer option to initialize the conda environment and misc improvements, by [@mrclary](https://github.com/mrclary)
* [PR 20835](https://github.com/spyder-ide/spyder/pull/20835) - PR: Install wheel in macOS build environment, by [@mrclary](https://github.com/mrclary) ([20834](https://github.com/spyder-ide/spyder/issues/20834))
* [PR 20830](https://github.com/spyder-ide/spyder/pull/20830) - PR: Don't treat warnings as errors when installing Spyder and subrepos (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20823](https://github.com/spyder-ide/spyder/pull/20823) - PR: Change reporting of macOS system from Darwin to macOS and include machine type, by [@mrclary](https://github.com/mrclary)
* [PR 20817](https://github.com/spyder-ide/spyder/pull/20817) - PR: Update codecov coverage upload to use GitHub Action (CI), by [@dalthviz](https://github.com/dalthviz)
* [PR 20812](https://github.com/spyder-ide/spyder/pull/20812) - PR: Ensure Pythonpath Manager widget is in front and has focus after adding path on macOS, by [@mrclary](https://github.com/mrclary) ([20808](https://github.com/spyder-ide/spyder/issues/20808))
* [PR 20811](https://github.com/spyder-ide/spyder/pull/20811) - PR: Keep `PYTHONHOME` in `get_user_environment_variables` for macOS standalone app, by [@mrclary](https://github.com/mrclary)
* [PR 20781](https://github.com/spyder-ide/spyder/pull/20781) - PR: Update `RELEASE.md` following 5.4.3 release experience, by [@dalthviz](https://github.com/dalthviz)
* [PR 20764](https://github.com/spyder-ide/spyder/pull/20764) - PR: Various fixes to improve compatibility with PySide2. , by [@rear1019](https://github.com/rear1019)
* [PR 20758](https://github.com/spyder-ide/spyder/pull/20758) - PR: Remove quotes from `conda-activate.bat` params and fix `micromamba.exe` detection (Installers), by [@dalthviz](https://github.com/dalthviz) ([16562](https://github.com/spyder-ide/spyder/issues/16562))

In this release 37 pull requests were closed.


----


## Version 5.4.3 (2023-04-05)

### New features

* Add support for QDarkstyle 3.1
* Add support for Jupyter-client 8
* Add mambaforge and miniforge when searching for conda environments

### Important fixes

* Fix IPython Console completions, traceback handling and other issues to better support IPython 8.x
* Fix compatibility issues with PyZMQ 25.x
* Add warning message before loading spydata files 
* Fix web based widgets display by adding the `--no-sandbox` argument for `QtApplication`
* Fix copy and paste shortcuts for the Files and Projects explorer panes
* Fix Windows standalone installer restart mechanism
* Fix keyring backends for the Mac standalone installer
* Fix Editor issues related with handling LSP server failed starts
* Fix Editor issues related with restoring previous session and file changes outside Spyder
* Fix PYTHONPATH manager showing extra paths and other related errors
* Fix update available notification with pip based installations
* Fix some UX/UI issues for the find replace widget when the Editor has a small width
* Removal of Python 2 related code

### Issues Closed

* [Issue 20742](https://github.com/spyder-ide/spyder/issues/20742) - Release Spyder 5.4.3 ([PR 20772](https://github.com/spyder-ide/spyder/pull/20772) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20681](https://github.com/spyder-ide/spyder/issues/20681) - ModuleNotFoundError when clicking on "Connect to an existing kernel" in the Mac app ([PR 20686](https://github.com/spyder-ide/spyder/pull/20686) by [@mrclary](https://github.com/mrclary))
* [Issue 20679](https://github.com/spyder-ide/spyder/issues/20679) - TypeError when saving file with a different name in the editor and the LSP server failed to start ([PR 20685](https://github.com/spyder-ide/spyder/pull/20685) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20670](https://github.com/spyder-ide/spyder/issues/20670) - TimeoutError and crash at startup when restoring files in the editor if OneDrive is not started ([PR 20674](https://github.com/spyder-ide/spyder/pull/20674) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20643](https://github.com/spyder-ide/spyder/issues/20643) - AttributeError after closing all files in a new editor window ([PR 20664](https://github.com/spyder-ide/spyder/pull/20664) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20637](https://github.com/spyder-ide/spyder/issues/20637) - Extra path shown in Pythonpath manager when using the Mac app ([PR 20106](https://github.com/spyder-ide/spyder/pull/20106) by [@mrclary](https://github.com/mrclary))
* [Issue 20619](https://github.com/spyder-ide/spyder/issues/20619) - Mambaforge environment not automatically detected ([PR 20498](https://github.com/spyder-ide/spyder/pull/20498) by [@mrclary](https://github.com/mrclary))
* [Issue 20599](https://github.com/spyder-ide/spyder/issues/20599) - Profiler process needs to remove `PYTHONEXECUTABLE` to run in conda env ([PR 20612](https://github.com/spyder-ide/spyder/pull/20612) by [@battaglia01](https://github.com/battaglia01))
* [Issue 20597](https://github.com/spyder-ide/spyder/issues/20597) - Crash with seaborn objects (version 0.12.2) Python 3.10 and QtConsole 5.4.0 ([PR 20644](https://github.com/spyder-ide/spyder/pull/20644) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20539](https://github.com/spyder-ide/spyder/issues/20539) - TypeError when trying to update environments in status bar widget ([PR 20690](https://github.com/spyder-ide/spyder/pull/20690) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20506](https://github.com/spyder-ide/spyder/issues/20506) - Error when trying to add directories in PythonPath Manager ([PR 20541](https://github.com/spyder-ide/spyder/pull/20541) by [@rear1019](https://github.com/rear1019))
* [Issue 20504](https://github.com/spyder-ide/spyder/issues/20504) - Pane tabs in macOS are center-aligned rather than left-aligned ([PR 20515](https://github.com/spyder-ide/spyder/pull/20515) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20496](https://github.com/spyder-ide/spyder/issues/20496) - Viewer of dataframes uses `iteritems` but shouldn't for Pandas >= 1.5.0 ([PR 20650](https://github.com/spyder-ide/spyder/pull/20650) by [@dan123456-eng](https://github.com/dan123456-eng))
* [Issue 20476](https://github.com/spyder-ide/spyder/issues/20476) - Buttons in find and replace widget jump around for small editor widths ([PR 20593](https://github.com/spyder-ide/spyder/pull/20593) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20462](https://github.com/spyder-ide/spyder/issues/20462) - ndarray subclasses with a member called 'dtype' crashes Spyder if dtype.name doesn't exist ([PR 20464](https://github.com/spyder-ide/spyder/pull/20464) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20430](https://github.com/spyder-ide/spyder/issues/20430) - `spyder-line-profiler` fails silently with latest 5.x due to missing import in `py3compat` ([PR 20450](https://github.com/spyder-ide/spyder/pull/20450) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20417](https://github.com/spyder-ide/spyder/issues/20417) - Small inconsistency in license file ([PR 20420](https://github.com/spyder-ide/spyder/pull/20420) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20407](https://github.com/spyder-ide/spyder/issues/20407) - IPython console does not link to the file and row that caused the error anymore ([PR 20725](https://github.com/spyder-ide/spyder/pull/20725) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20406](https://github.com/spyder-ide/spyder/issues/20406) - Error when checking for updates finishes with pip installations ([PR 20492](https://github.com/spyder-ide/spyder/pull/20492) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20398](https://github.com/spyder-ide/spyder/issues/20398) - TypeError when running files in external terminal ([PR 20405](https://github.com/spyder-ide/spyder/pull/20405) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20393](https://github.com/spyder-ide/spyder/issues/20393) - Pressing `Tab` key for code completion repeats previous text with IPython 8.8+ ([PR 20656](https://github.com/spyder-ide/spyder/pull/20656) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20392](https://github.com/spyder-ide/spyder/issues/20392) - Remove QDarkstyle subrepo ([PR 20442](https://github.com/spyder-ide/spyder/pull/20442) by [@mrclary](https://github.com/mrclary))
* [Issue 20390](https://github.com/spyder-ide/spyder/issues/20390) - Online Help Crash ([PR 20596](https://github.com/spyder-ide/spyder/pull/20596) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20381](https://github.com/spyder-ide/spyder/issues/20381) - ZMQError when running code in the console ([PR 20735](https://github.com/spyder-ide/spyder/pull/20735) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20358](https://github.com/spyder-ide/spyder/issues/20358) - Help pane doesn't show anything in rich text mode ([PR 20482](https://github.com/spyder-ide/spyder/pull/20482) by [@tlunet](https://github.com/tlunet))
* [Issue 20242](https://github.com/spyder-ide/spyder/issues/20242) - Error when running Numpy, Scipy, Pandas code with Windows installer ([PR 20106](https://github.com/spyder-ide/spyder/pull/20106) by [@mrclary](https://github.com/mrclary))
* [Issue 20068](https://github.com/spyder-ide/spyder/issues/20068) - Copy and paste shortcuts for Files and Projects don't work in 5.3.3 ([PR 20707](https://github.com/spyder-ide/spyder/pull/20707) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18838](https://github.com/spyder-ide/spyder/issues/18838) - Crash after switching git branch that removes open files ([PR 20586](https://github.com/spyder-ide/spyder/pull/20586) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11754](https://github.com/spyder-ide/spyder/issues/11754) - Unable to load .spydata files containing numpy object arrays 

In this release 29 issues were closed.

### Pull Requests Merged

* [PR 20772](https://github.com/spyder-ide/spyder/pull/20772) - PR: Update core dependencies for 5.4.3, by [@dalthviz](https://github.com/dalthviz) ([20742](https://github.com/spyder-ide/spyder/issues/20742))
* [PR 20766](https://github.com/spyder-ide/spyder/pull/20766) - PR: Add support for QDarkstyle 3.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20763](https://github.com/spyder-ide/spyder/pull/20763) - PR: Sync latest changes in PyLSP, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20751](https://github.com/spyder-ide/spyder/pull/20751) - PR: Remove constraint for PyZMQ < 25 (Installers), by [@dalthviz](https://github.com/dalthviz)
* [PR 20749](https://github.com/spyder-ide/spyder/pull/20749) - PR: Check if the `iopub` channel is not closed before flushing it (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20735](https://github.com/spyder-ide/spyder/pull/20735) - PR: Add support for Jupyter-client 8, by [@ccordoba12](https://github.com/ccordoba12) ([20381](https://github.com/spyder-ide/spyder/issues/20381))
* [PR 20729](https://github.com/spyder-ide/spyder/pull/20729) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 20727](https://github.com/spyder-ide/spyder/pull/20727) - PR: Update translations for 5.4.3, by [@dalthviz](https://github.com/dalthviz)
* [PR 20725](https://github.com/spyder-ide/spyder/pull/20725) - PR: Fix clicking on file names in tracebacks for IPython 8 and minor fixes for messages shown in the console, by [@ccordoba12](https://github.com/ccordoba12) ([20407](https://github.com/spyder-ide/spyder/issues/20407))
* [PR 20707](https://github.com/spyder-ide/spyder/pull/20707) - PR: Fix copy/paste shortcuts in Files and Projects, by [@ccordoba12](https://github.com/ccordoba12) ([20068](https://github.com/spyder-ide/spyder/issues/20068))
* [PR 20699](https://github.com/spyder-ide/spyder/pull/20699) - PR: Fix restart mechanism for the Windows standalone installer (Installers), by [@dalthviz](https://github.com/dalthviz)
* [PR 20690](https://github.com/spyder-ide/spyder/pull/20690) - PR: Avoid error when updating environments (Main interpreter), by [@ccordoba12](https://github.com/ccordoba12) ([20539](https://github.com/spyder-ide/spyder/issues/20539))
* [PR 20686](https://github.com/spyder-ide/spyder/pull/20686) - PR: Fix issue where keyring backends are not found in macOS standalone app, by [@mrclary](https://github.com/mrclary) ([20681](https://github.com/spyder-ide/spyder/issues/20681))
* [PR 20685](https://github.com/spyder-ide/spyder/pull/20685) - PR: Fix error in `document_did_open` when the LSP failed to start (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20679](https://github.com/spyder-ide/spyder/issues/20679))
* [PR 20674](https://github.com/spyder-ide/spyder/pull/20674) - PR: Avoid crash at startup when trying to restore the previous session (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20670](https://github.com/spyder-ide/spyder/issues/20670))
* [PR 20664](https://github.com/spyder-ide/spyder/pull/20664) - PR: Add validations before doing operations with the current editor (Editor), by [@dalthviz](https://github.com/dalthviz) ([20643](https://github.com/spyder-ide/spyder/issues/20643))
* [PR 20656](https://github.com/spyder-ide/spyder/pull/20656) - PR: Skip IPython versions that give buggy code completions and other fixes for dependencies, by [@ccordoba12](https://github.com/ccordoba12) ([20393](https://github.com/spyder-ide/spyder/issues/20393))
* [PR 20650](https://github.com/spyder-ide/spyder/pull/20650) - PR: Change usage of `iteritems` for `items` in dataframe editor (Variable Explorer), by [@dan123456-eng](https://github.com/dan123456-eng) ([20496](https://github.com/spyder-ide/spyder/issues/20496))
* [PR 20644](https://github.com/spyder-ide/spyder/pull/20644) - PR: Fix displaying images that have float width or height (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([20597](https://github.com/spyder-ide/spyder/issues/20597))
* [PR 20612](https://github.com/spyder-ide/spyder/pull/20612) - PR: Remove `PYTHONEXECUTABLE` for process that runs the profiler, by [@battaglia01](https://github.com/battaglia01) ([20599](https://github.com/spyder-ide/spyder/issues/20599))
* [PR 20596](https://github.com/spyder-ide/spyder/pull/20596) - PR: Set `PYDEVD_DISABLE_FILE_VALIDATION` to prevent errors when searching for numpy docs (Online Help), by [@dalthviz](https://github.com/dalthviz) ([20390](https://github.com/spyder-ide/spyder/issues/20390))
* [PR 20593](https://github.com/spyder-ide/spyder/pull/20593) - PR: Show icon instead of text for small widths and clear found results correctly in Find/Replace widget, by [@ccordoba12](https://github.com/ccordoba12) ([20476](https://github.com/spyder-ide/spyder/issues/20476))
* [PR 20588](https://github.com/spyder-ide/spyder/pull/20588) - PR: Remove macOS and Windows conda-based installers from 5.x branch, by [@mrclary](https://github.com/mrclary)
* [PR 20586](https://github.com/spyder-ide/spyder/pull/20586) - PR: Fix segfault when closing files removed outside Spyder (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([18838](https://github.com/spyder-ide/spyder/issues/18838))
* [PR 20582](https://github.com/spyder-ide/spyder/pull/20582) - PR: Make translation object a singleton, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 20558](https://github.com/spyder-ide/spyder/pull/20558) - PR: Drop bytes encodings for translations, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 20543](https://github.com/spyder-ide/spyder/pull/20543) - PR: Fix “Last edit location” for unsaved files, by [@rear1019](https://github.com/rear1019)
* [PR 20542](https://github.com/spyder-ide/spyder/pull/20542) - PR: Fix error in public API of Python Path Manager, by [@rear1019](https://github.com/rear1019)
* [PR 20541](https://github.com/spyder-ide/spyder/pull/20541) - PR: Fix error when Python Path Manager is reopened, by [@rear1019](https://github.com/rear1019) ([20506](https://github.com/spyder-ide/spyder/issues/20506))
* [PR 20538](https://github.com/spyder-ide/spyder/pull/20538) - PR: Fix reinstalling Spyder in editable mode when switching from 5.x to master and viceversa (Development), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20515](https://github.com/spyder-ide/spyder/pull/20515) - PR: Make pane tabs to be left aligned on macOS again, by [@ccordoba12](https://github.com/ccordoba12) ([20504](https://github.com/spyder-ide/spyder/issues/20504))
* [PR 20498](https://github.com/spyder-ide/spyder/pull/20498) - PR: Update conda search paths to include mambaforge and miniforge, by [@mrclary](https://github.com/mrclary) ([20619](https://github.com/spyder-ide/spyder/issues/20619))
* [PR 20492](https://github.com/spyder-ide/spyder/pull/20492) - PR: Initialize `content` variable for update available message (Application), by [@dalthviz](https://github.com/dalthviz) ([20406](https://github.com/spyder-ide/spyder/issues/20406))
* [PR 20482](https://github.com/spyder-ide/spyder/pull/20482) - PR: Add `--no-sandbox` argument for QtApplication, by [@tlunet](https://github.com/tlunet) ([20358](https://github.com/spyder-ide/spyder/issues/20358))
* [PR 20466](https://github.com/spyder-ide/spyder/pull/20466) - PR: Fix installer triggers, by [@mrclary](https://github.com/mrclary)
* [PR 20464](https://github.com/spyder-ide/spyder/pull/20464) - PR: Prevent error when trying to show arrays without an actual `dtype` (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([20462](https://github.com/spyder-ide/spyder/issues/20462))
* [PR 20456](https://github.com/spyder-ide/spyder/pull/20456) - PR: Skip `test_tk_backend` on Windows with IPykernel 6.21.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20452](https://github.com/spyder-ide/spyder/pull/20452) - PR: Update GitHub actions, by [@mrclary](https://github.com/mrclary)
* [PR 20450](https://github.com/spyder-ide/spyder/pull/20450) - PR: Restore `pickle` import in `py3compat.py` and some fixes to the main window tests, by [@ccordoba12](https://github.com/ccordoba12) ([20430](https://github.com/spyder-ide/spyder/issues/20430))
* [PR 20442](https://github.com/spyder-ide/spyder/pull/20442) - PR: Remove qdarkstyle subrepo, by [@mrclary](https://github.com/mrclary) ([20392](https://github.com/spyder-ide/spyder/issues/20392))
* [PR 20425](https://github.com/spyder-ide/spyder/pull/20425) - PR: Better split test suite between slow and fast slots in CIs and other improvements for CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20420](https://github.com/spyder-ide/spyder/pull/20420) - PR: Make Readme and License files to match, by [@ccordoba12](https://github.com/ccordoba12) ([20417](https://github.com/spyder-ide/spyder/issues/20417))
* [PR 20405](https://github.com/spyder-ide/spyder/pull/20405) - PR: Fix check for UNC working directory path when running code in external terminals, by [@ccordoba12](https://github.com/ccordoba12) ([20398](https://github.com/spyder-ide/spyder/issues/20398))
* [PR 20396](https://github.com/spyder-ide/spyder/pull/20396) - PR: Add workflow triggers for release candidates and fix tag normalization, by [@mrclary](https://github.com/mrclary)
* [PR 20366](https://github.com/spyder-ide/spyder/pull/20366) - PR: Remove Python 2 support (part I), by [@oscargus](https://github.com/oscargus)
* [PR 20272](https://github.com/spyder-ide/spyder/pull/20272) - PR: Display warning message before loading spydata files, by [@nkleinbaer](https://github.com/nkleinbaer) ([11754](https://github.com/[/issues/11754))
* [PR 20106](https://github.com/spyder-ide/spyder/pull/20106) - PR: Fix issue where user environment variables with line endings were not parsed correctly on Unix platforms, by [@mrclary](https://github.com/mrclary) ([20637](https://github.com/spyder-ide/spyder/issues/20637), [20242](https://github.com/spyder-ide/spyder/issues/20242), [20097](https://github.com/spyder-ide/spyder/issues/20097))

In this release 47 pull requests were closed.


----


## Version 5.4.2 (2023-01-18)

### New features

* Improvements to the experimental conda-based Linux installer (shortcut icon, improvements to execute the installer script)

### Important fixes

* Fix issues detected with PyZMQ 25
* Fix dot completions and improve support for files and directories completions
* Fix getting current user enviroment variables
* Fix cursor position restauration after autoformat when saving files
* Fix error when reverting unexisting files
* Improvements to the workflows to build conda-based installers
* Fix some issues related with Python 3.11 compatibility

### Issues Closed

* [Issue 20363](https://github.com/spyder-ide/spyder/issues/20363) - Release Spyder 5.4.2 ([PR 20395](https://github.com/spyder-ide/spyder/pull/20395) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20359](https://github.com/spyder-ide/spyder/issues/20359) - TypeError: object list can't be used in 'await' expression with PyZMQ 25 ([PR 20391](https://github.com/spyder-ide/spyder/pull/20391) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20331](https://github.com/spyder-ide/spyder/issues/20331) - Fix on dot completion leads to dot replacement ([PR 20350](https://github.com/spyder-ide/spyder/pull/20350) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20309](https://github.com/spyder-ide/spyder/issues/20309) - UnicodeDecodeError when trying to get environment variables in 5.4.1 ([PR 20329](https://github.com/spyder-ide/spyder/pull/20329) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20296](https://github.com/spyder-ide/spyder/issues/20296) - Failed to render rich text help in Python 3.11 ([PR 20324](https://github.com/spyder-ide/spyder/pull/20324) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20291](https://github.com/spyder-ide/spyder/issues/20291) - Mac installer for 5.4.1 failed to build ([PR 20297](https://github.com/spyder-ide/spyder/pull/20297) by [@mrclary](https://github.com/mrclary))
* [Issue 20286](https://github.com/spyder-ide/spyder/issues/20286) - Annoying log message shown when autosave fails to work ([PR 20287](https://github.com/spyder-ide/spyder/pull/20287) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20285](https://github.com/spyder-ide/spyder/issues/20285) - Spyder 5.4.1 does not show completions when only a dot is written next to a module ([PR 20298](https://github.com/spyder-ide/spyder/pull/20298) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20284](https://github.com/spyder-ide/spyder/issues/20284) - FileNotFoundError when reverting non-existing file in the editor ([PR 20288](https://github.com/spyder-ide/spyder/pull/20288) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20282](https://github.com/spyder-ide/spyder/issues/20282) - Spyder 5.4.1 is closing alone when saving files and auto-formatting on save is enabled ([PR 20317](https://github.com/spyder-ide/spyder/pull/20317) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20176](https://github.com/spyder-ide/spyder/issues/20176) - Improvements to the Linux installer ([PR 20319](https://github.com/spyder-ide/spyder/pull/20319) by [@mrclary](https://github.com/mrclary))
* [Issue 20097](https://github.com/spyder-ide/spyder/issues/20097) - ValueError when trying to get environment variables on Linux ([PR 20297](https://github.com/spyder-ide/spyder/pull/20297) by [@mrclary](https://github.com/mrclary))

In this release 12 issues were closed.

### Pull Requests Merged

* [PR 20395](https://github.com/spyder-ide/spyder/pull/20395) - PR: Update core dependencies for 5.4.2, by [@dalthviz](https://github.com/dalthviz) ([20363](https://github.com/spyder-ide/spyder/issues/20363))
* [PR 20391](https://github.com/spyder-ide/spyder/pull/20391) - PR: Rely on `jupyter-client` 7.4.9+ because it's compatible with PyZMQ 25 (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([20359](https://github.com/spyder-ide/spyder/issues/20359))
* [PR 20376](https://github.com/spyder-ide/spyder/pull/20376) - PR: Fix patch for conda-based installers, by [@mrclary](https://github.com/mrclary)
* [PR 20350](https://github.com/spyder-ide/spyder/pull/20350) - PR: Introduce completions correctly for autocompletion characters and improve file completions (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20331](https://github.com/spyder-ide/spyder/issues/20331))
* [PR 20335](https://github.com/spyder-ide/spyder/pull/20335) - PR: Move ipyconsole fixture to conftest (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20329](https://github.com/spyder-ide/spyder/pull/20329) - PR: Catch any possible error when trying to get the user environment variables (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([20309](https://github.com/spyder-ide/spyder/issues/20309))
* [PR 20324](https://github.com/spyder-ide/spyder/pull/20324) - PR: Fix getting object signature from kernel in Python 3.11 (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([20296](https://github.com/spyder-ide/spyder/issues/20296))
* [PR 20319](https://github.com/spyder-ide/spyder/pull/20319) - PR: Improvements to Conda-based Linux installer, by [@mrclary](https://github.com/mrclary) ([20176](https://github.com/spyder-ide/spyder/issues/20176))
* [PR 20317](https://github.com/spyder-ide/spyder/pull/20317) - PR: Fix restoring current cursor line after autoformat takes place (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20282](https://github.com/spyder-ide/spyder/issues/20282))
* [PR 20315](https://github.com/spyder-ide/spyder/pull/20315) - PR: Update installer workflows to run as release on push of `pre` tag, by [@mrclary](https://github.com/mrclary)
* [PR 20303](https://github.com/spyder-ide/spyder/pull/20303) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 20301](https://github.com/spyder-ide/spyder/pull/20301) - PR: Fix pydocstyle linting, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20298](https://github.com/spyder-ide/spyder/pull/20298) - PR: Fix automatic completions after a dot is written next to a module, by [@ccordoba12](https://github.com/ccordoba12) ([20285](https://github.com/spyder-ide/spyder/issues/20285))
* [PR 20297](https://github.com/spyder-ide/spyder/pull/20297) - PR: Fix installer issues and bug when getting environment variables, by [@mrclary](https://github.com/mrclary) ([20291](https://github.com/spyder-ide/spyder/issues/20291), [20097](https://github.com/spyder-ide/spyder/issues/20097))
* [PR 20288](https://github.com/spyder-ide/spyder/pull/20288) - PR: Catch error when trying to revert unexisting files (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20284](https://github.com/spyder-ide/spyder/issues/20284))
* [PR 20287](https://github.com/spyder-ide/spyder/pull/20287) - PR: Avoid showing a `logger.error` message when auto-saving (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20286](https://github.com/spyder-ide/spyder/issues/20286))

In this release 16 pull requests were closed.


----


## Version 5.4.1 (2022-12-29)

### New features

* Support for IPython 8
* Improvements for code completion and help offered for scientific modules (Numpy, Pandas, Matplotlib and Scipy)
* Improvements to the UX/UI of the FindReplace widget (find and replace functionality)
* New PYTHONPATH manager plugin

### Important fixes

* Improve/fix errors regarding the `New Window` and `Split window` Editor funtionality and general `RuntimeError`s on the Editor
* Improvements when syncing symbols and folding code functionality for the Editor
* Fix PYTHONPATH handling for the IPython console
* Some fixes for code completion and code style linting functionality 
* Some fixes/improvements regarding UX/UI for the IPython console pane, menu and context menu generation
* Some improvements regarding UX/UI for the current working directory toolbar

### New API features

* Improvements to the way Spyder handles menus sections additions

### Issues Closed

* [Issue 20263](https://github.com/spyder-ide/spyder/issues/20263) - Release Spyder 5.4.1 ([PR 20277](https://github.com/spyder-ide/spyder/pull/20277) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20255](https://github.com/spyder-ide/spyder/issues/20255) - Consider a different icon for "no matches" in Find/Replace ([PR 20268](https://github.com/spyder-ide/spyder/pull/20268) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20212](https://github.com/spyder-ide/spyder/issues/20212) - RuntimeError when trying to interrupt a dead kernel ([PR 20224](https://github.com/spyder-ide/spyder/pull/20224) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20156](https://github.com/spyder-ide/spyder/issues/20156) - Autocomplete does not work properly if the file starts with a number ([PR 20226](https://github.com/spyder-ide/spyder/pull/20226) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20144](https://github.com/spyder-ide/spyder/issues/20144) - RuntimeError after closing Editor window renders Editor unusable ([PR 20221](https://github.com/spyder-ide/spyder/pull/20221) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20105](https://github.com/spyder-ide/spyder/issues/20105) - Exception if List contains array with only one element ([PR 20225](https://github.com/spyder-ide/spyder/pull/20225) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20101](https://github.com/spyder-ide/spyder/issues/20101) - KeyError when updating contents in the Outline, which prevents opening new Editor windows ([PR 20221](https://github.com/spyder-ide/spyder/pull/20221) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20079](https://github.com/spyder-ide/spyder/issues/20079) - Spyder crashes at startup because it's unable to ready `pylintrc` file ([PR 20080](https://github.com/spyder-ide/spyder/pull/20080) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20071](https://github.com/spyder-ide/spyder/issues/20071) - RuntimeError when closing file in the editor ([PR 20082](https://github.com/spyder-ide/spyder/pull/20082) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20055](https://github.com/spyder-ide/spyder/issues/20055) - RuntimeError when opening a file ([PR 20082](https://github.com/spyder-ide/spyder/pull/20082) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20035](https://github.com/spyder-ide/spyder/issues/20035) - Error in "Check for updates" ([PR 20036](https://github.com/spyder-ide/spyder/pull/20036) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20033](https://github.com/spyder-ide/spyder/issues/20033) - Black line when opening a file at the last line ([PR 20161](https://github.com/spyder-ide/spyder/pull/20161) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20023](https://github.com/spyder-ide/spyder/issues/20023) - Spyder-kernels message not shown on Windows after restarting kernels ([PR 20233](https://github.com/spyder-ide/spyder/pull/20233) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20003](https://github.com/spyder-ide/spyder/issues/20003) - Windows: Can't execute new python file on network drive ([PR 20050](https://github.com/spyder-ide/spyder/pull/20050) by [@athompson673](https://github.com/athompson673))
* [Issue 19991](https://github.com/spyder-ide/spyder/issues/19991) - Right click next to console tab does not work any longer ([PR 20000](https://github.com/spyder-ide/spyder/pull/20000) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19989](https://github.com/spyder-ide/spyder/issues/19989) - Unreasonably irritating autocomplete behavior ([PR 20157](https://github.com/spyder-ide/spyder/pull/20157) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19983](https://github.com/spyder-ide/spyder/issues/19983) - Execute in dedicated console without clearing variables ([PR 20012](https://github.com/spyder-ide/spyder/pull/20012) by [@bcolsen](https://github.com/bcolsen))
* [Issue 19966](https://github.com/spyder-ide/spyder/issues/19966) - Current Spyder demo via MyBinder doesn't have Web browser working in easy to launch way ([PR 20004](https://github.com/spyder-ide/spyder/pull/20004) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19958](https://github.com/spyder-ide/spyder/issues/19958) - Editor jumps to the end of file when saving with autoformat-on-save switched on ([PR 20167](https://github.com/spyder-ide/spyder/pull/20167) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19724](https://github.com/spyder-ide/spyder/issues/19724) - PYTHONPATH not seen by Spyder after updating to 5.3.3? ([PR 19937](https://github.com/spyder-ide/spyder/pull/19937) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19633](https://github.com/spyder-ide/spyder/issues/19633) - Bug: FileDialog: Profiler Save/Load does not make File-Extension (.Result) clear ([PR 20064](https://github.com/spyder-ide/spyder/pull/20064) by [@maurerle](https://github.com/maurerle))
* [Issue 19610](https://github.com/spyder-ide/spyder/issues/19610) - Spyder crashes when the IPython console is disabled ([PR 20183](https://github.com/spyder-ide/spyder/pull/20183) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19565](https://github.com/spyder-ide/spyder/issues/19565) - Wrong E275 warning if keyword is at the end of a line ([PR 20264](https://github.com/spyder-ide/spyder/pull/20264) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18117](https://github.com/spyder-ide/spyder/issues/18117) - Please support IPython 8 ([PR 20271](https://github.com/spyder-ide/spyder/pull/20271) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16342](https://github.com/spyder-ide/spyder/issues/16342) - Slow time to display completions ([PR 18871](https://github.com/spyder-ide/spyder/pull/18871) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16161](https://github.com/spyder-ide/spyder/issues/16161) - Spyder 5.1 crash in Ubuntu's Unity ([PR 20183](https://github.com/spyder-ide/spyder/pull/20183) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12693](https://github.com/spyder-ide/spyder/issues/12693) - Go to line dialog finds an internal problem ([PR 20070](https://github.com/spyder-ide/spyder/pull/20070) by [@maurerle](https://github.com/maurerle))
* [Issue 7247](https://github.com/spyder-ide/spyder/issues/7247) - Find and Replace stops highlighting any matches if any change is made in the Editor ([PR 20049](https://github.com/spyder-ide/spyder/pull/20049) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 6444](https://github.com/spyder-ide/spyder/issues/6444) - Pressing "Clear comparison" in Profiler while its running stops it and raises a TypeError ([PR 20064](https://github.com/spyder-ide/spyder/pull/20064) by [@maurerle](https://github.com/maurerle))

In this release 29 issues were closed.

### Pull Requests Merged

* [PR 20277](https://github.com/spyder-ide/spyder/pull/20277) - PR: Update core dependencies for 5.4.1, by [@dalthviz](https://github.com/dalthviz) ([20263](https://github.com/spyder-ide/spyder/issues/20263))
* [PR 20276](https://github.com/spyder-ide/spyder/pull/20276) - PR: Update missing translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 20274](https://github.com/spyder-ide/spyder/pull/20274) - PR: Improve completions for scientific modules (Code completion), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20271](https://github.com/spyder-ide/spyder/pull/20271) - PR: Add support for IPython 8, by [@ccordoba12](https://github.com/ccordoba12) ([18117](https://github.com/spyder-ide/spyder/issues/18117))
* [PR 20269](https://github.com/spyder-ide/spyder/pull/20269) - PR: Require py2app 0.28.4 for the Mac installer, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20268](https://github.com/spyder-ide/spyder/pull/20268) - PR: Use a better icon when no matches are found (Find/Replace widget), by [@ccordoba12](https://github.com/ccordoba12) ([20255](https://github.com/spyder-ide/spyder/issues/20255))
* [PR 20264](https://github.com/spyder-ide/spyder/pull/20264) - PR: Fix Pycodestyle linting with line endings other than LF (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([19565](https://github.com/spyder-ide/spyder/issues/19565))
* [PR 20259](https://github.com/spyder-ide/spyder/pull/20259) - PR: Fix concurrency for installers-conda workflow, by [@mrclary](https://github.com/mrclary)
* [PR 20254](https://github.com/spyder-ide/spyder/pull/20254) - PR: Cancel runs in progress when pushing new commits (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20252](https://github.com/spyder-ide/spyder/pull/20252) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 20251](https://github.com/spyder-ide/spyder/pull/20251) - PR: Update translations for 5.4.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 20233](https://github.com/spyder-ide/spyder/pull/20233) - PR: Fix showing Spyder-kernels message on kernel restarts (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([20023](https://github.com/spyder-ide/spyder/issues/20023))
* [PR 20226](https://github.com/spyder-ide/spyder/pull/20226) - PR: Prevent Python variable validation to get current word and position when doing completions, by [@dalthviz](https://github.com/dalthviz) ([20156](https://github.com/spyder-ide/spyder/issues/20156))
* [PR 20225](https://github.com/spyder-ide/spyder/pull/20225) - PR: Add validation to prevent errors when getting array-like variables (Widgets - collectionseditor), by [@dalthviz](https://github.com/dalthviz) ([20105](https://github.com/spyder-ide/spyder/issues/20105))
* [PR 20224](https://github.com/spyder-ide/spyder/pull/20224) - PR: Inform users when kernel can't be interrupted (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([20212](https://github.com/spyder-ide/spyder/issues/20212))
* [PR 20221](https://github.com/spyder-ide/spyder/pull/20221) - PR: Several fixes for new Editor windows, by [@ccordoba12](https://github.com/ccordoba12) ([20144](https://github.com/spyder-ide/spyder/issues/20144), [20101](https://github.com/spyder-ide/spyder/issues/20101))
* [PR 20218](https://github.com/spyder-ide/spyder/pull/20218) - PR: Improve syncing symbols and folding (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20183](https://github.com/spyder-ide/spyder/pull/20183) - PR: Simplify the way we add sections to menus (API), by [@ccordoba12](https://github.com/ccordoba12) ([19610](https://github.com/spyder-ide/spyder/issues/19610), [16161](https://github.com/spyder-ide/spyder/issues/16161))
* [PR 20167](https://github.com/spyder-ide/spyder/pull/20167) - PR: Restore cursor position after inserting auto-formatted text (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([19958](https://github.com/spyder-ide/spyder/issues/19958))
* [PR 20161](https://github.com/spyder-ide/spyder/pull/20161) - PR: Fix a visual glitch when opening files in the light theme (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20033](https://github.com/spyder-ide/spyder/issues/20033))
* [PR 20157](https://github.com/spyder-ide/spyder/pull/20157) - PR: Pass Home/End key events from Completion to CodeEditor widget (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([19989](https://github.com/spyder-ide/spyder/issues/19989))
* [PR 20146](https://github.com/spyder-ide/spyder/pull/20146) - PR: Add default value for `IconLineEdit` helper widget constructor params (Widgets), by [@dalthviz](https://github.com/dalthviz)
* [PR 20122](https://github.com/spyder-ide/spyder/pull/20122) - PR: Remove white dots on IPython console tabbar for Windows, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20113](https://github.com/spyder-ide/spyder/pull/20113) - PR: Fix random rare error in completion plugin, by [@rear1019](https://github.com/rear1019)
* [PR 20092](https://github.com/spyder-ide/spyder/pull/20092) - PR: Fix Pytest catching up tests using Spyder-unittest or VSCode, by [@maurerle](https://github.com/maurerle)
* [PR 20091](https://github.com/spyder-ide/spyder/pull/20091) - PR: Remove check_path to allow running in debugger, by [@maurerle](https://github.com/maurerle)
* [PR 20082](https://github.com/spyder-ide/spyder/pull/20082) - PR: Catch a couple of reported RuntimeError's (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([20071](https://github.com/spyder-ide/spyder/issues/20071), [20055](https://github.com/spyder-ide/spyder/issues/20055))
* [PR 20080](https://github.com/spyder-ide/spyder/pull/20080) - PR: Prevent crash at startup if importing `pylint.config` fails (Code Analysis), by [@ccordoba12](https://github.com/ccordoba12) ([20079](https://github.com/spyder-ide/spyder/issues/20079))
* [PR 20070](https://github.com/spyder-ide/spyder/pull/20070) - PR: Fix QIntValidator to handle '+' sign, by [@maurerle](https://github.com/maurerle) ([12693](https://github.com/spyder-ide/spyder/issues/12693))
* [PR 20064](https://github.com/spyder-ide/spyder/pull/20064) - PR: Fixes profiler extension and buttons, by [@maurerle](https://github.com/maurerle) ([6444](https://github.com/spyder-ide/spyder/issues/6444), [19633](https://github.com/spyder-ide/spyder/issues/19633))
* [PR 20056](https://github.com/spyder-ide/spyder/pull/20056) - PR: Update conda-based installers, by [@mrclary](https://github.com/mrclary)
* [PR 20050](https://github.com/spyder-ide/spyder/pull/20050) - PR: Add "UNC wdir not supported by cmd.exe" warning when trying to run file in external console, by [@athompson673](https://github.com/athompson673) ([20003](https://github.com/spyder-ide/spyder/issues/20003))
* [PR 20049](https://github.com/spyder-ide/spyder/pull/20049) - PR: Improve UX/UI of the `FindReplace` widget, by [@ccordoba12](https://github.com/ccordoba12) ([7247](https://github.com/spyder-ide/spyder/issues/7247))
* [PR 20047](https://github.com/spyder-ide/spyder/pull/20047) - PR: Fix some LSP issues, by [@rear1019](https://github.com/rear1019)
* [PR 20036](https://github.com/spyder-ide/spyder/pull/20036) - PR: Add validation to prevent calling uninitialized `application_update_status` widget on conda installations (Application), by [@dalthviz](https://github.com/dalthviz) ([20035](https://github.com/spyder-ide/spyder/issues/20035))
* [PR 20012](https://github.com/spyder-ide/spyder/pull/20012) - PR: Correctly handle the option to run in a dedicated console without clearing variables, by [@bcolsen](https://github.com/bcolsen) ([19983](https://github.com/spyder-ide/spyder/issues/19983))
* [PR 20005](https://github.com/spyder-ide/spyder/pull/20005) - PR: Add left spacer to Working directory toolbar, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20004](https://github.com/spyder-ide/spyder/pull/20004) - PR: Add binder badges for Spyder latest release, 5.x and master versions (Docs), by [@dalthviz](https://github.com/dalthviz) ([19966](https://github.com/spyder-ide/spyder/issues/19966))
* [PR 20002](https://github.com/spyder-ide/spyder/pull/20002) - PR: Update remote when syncing subrepos, by [@mrclary](https://github.com/mrclary)
* [PR 20000](https://github.com/spyder-ide/spyder/pull/20000) - PR: Restore context menu on tabs (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19991](https://github.com/spyder-ide/spyder/issues/19991))
* [PR 19992](https://github.com/spyder-ide/spyder/pull/19992) - PR: Update python-lsp-server subrepo and change CI Python versions, by [@dalthviz](https://github.com/dalthviz)
* [PR 19937](https://github.com/spyder-ide/spyder/pull/19937) - PR: Add a new plugin for the Pythonpath manager, by [@ccordoba12](https://github.com/ccordoba12) ([19724](https://github.com/spyder-ide/spyder/issues/19724))
* [PR 19885](https://github.com/spyder-ide/spyder/pull/19885) - PR: Fix `test_kernel_crash` to work with IPython 8+, by [@eendebakpt](https://github.com/eendebakpt)
* [PR 18871](https://github.com/spyder-ide/spyder/pull/18871) - PR: Make automatic completions more responsive (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16342](https://github.com/spyder-ide/spyder/issues/16342))

In this release 44 pull requests were closed.


----


## Version 5.4.0 (2022-11-04)

### New features

* New UI/UX elements to update standalone installers with options to download and install a new version if available.
* New experimental conda-based standalone installers for MacOS and Linux (available on the GitHub release page with the `EXPERIMENTAL-` prefix)
* Now the Code Analysis/Pylint plugin uses the current custom interpreter/environment if set
* Option to show user environment variables extended to all operative systems (previously available only for Windows)

### Important fixes

* Improve Outline Explorer plugin performance and fix updating process when it becomes visible
* Improvements to colors on the dependencies dialog and IPython console
* Fix IPython console issues on the Matplotlib TkInter backend with debugging and an increase of CPU and memory usage while in an idle state
* Fix IPython console memory leak when using the Matplotlib Qt ackend
* Fix IPython console `input()` issue on MacOS
* Fix IPython console kernel error regarding environment path as unexpected argument
* Fix Spyder 3 icon theme load on Windows with untrusted fonts security restrictions
* Fix the `Autoformat files on save` functionality to not hang with non-Python files
* Some fixes for cell execution on Python 3.11
* Some fixes to shortcuts (Switch to Editor, Find Next, Find Previous)
* Some fixes to improve compatibility with PySide2
* Some fixes to prevent blurry SVG icons

### Issues Closed

* [Issue 19902](https://github.com/spyder-ide/spyder/issues/19902) - Quick improvements and fixes to run Spyder on Binder ([PR 19936](https://github.com/spyder-ide/spyder/pull/19936) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19893](https://github.com/spyder-ide/spyder/issues/19893) - Release Spyder 5.4.0 ([PR 19978](https://github.com/spyder-ide/spyder/pull/19978) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19888](https://github.com/spyder-ide/spyder/issues/19888) - Spyder 5.3.3 IPython-console not properly doing `input()` on Mac ([PR 19947](https://github.com/spyder-ide/spyder/pull/19947) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19874](https://github.com/spyder-ide/spyder/issues/19874) - Spyder using  increasingly more CPU & memory while idling when using the Tkinter backend ([PR 19957](https://github.com/spyder-ide/spyder/pull/19957) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19868](https://github.com/spyder-ide/spyder/issues/19868) - Feedback about auto-update mechanism for installers ([PR 19871](https://github.com/spyder-ide/spyder/pull/19871) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19865](https://github.com/spyder-ide/spyder/issues/19865) - Unable to launch Spyder from `bootstrap.py` on Windows ([PR 19867](https://github.com/spyder-ide/spyder/pull/19867) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19862](https://github.com/spyder-ide/spyder/issues/19862) - Execution of code cells fails for Spyder on python 3.11 ([PR 19891](https://github.com/spyder-ide/spyder/pull/19891) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19850](https://github.com/spyder-ide/spyder/issues/19850) - IndexError when reading Internal console history file ([PR 19856](https://github.com/spyder-ide/spyder/pull/19856) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19832](https://github.com/spyder-ide/spyder/issues/19832) - Spyder doesn't open on MyBinder ([PR 19838](https://github.com/spyder-ide/spyder/pull/19838) by [@mrclary](https://github.com/mrclary))
* [Issue 19818](https://github.com/spyder-ide/spyder/issues/19818) - AttributeError on Online help pane whe Spyder is installed on msys2-mingw64 ([PR 19830](https://github.com/spyder-ide/spyder/pull/19830) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19743](https://github.com/spyder-ide/spyder/issues/19743) - macOS standalone installer failing due to black 22.10.0 ([PR 19744](https://github.com/spyder-ide/spyder/pull/19744) by [@mrclary](https://github.com/mrclary))
* [Issue 19735](https://github.com/spyder-ide/spyder/issues/19735) - AttributeError: 'WriteWrapper' object has no attribute '_thread_id' in kernel ([PR 19864](https://github.com/spyder-ide/spyder/pull/19864) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19728](https://github.com/spyder-ide/spyder/issues/19728) - Traceback from Editor/Debugger plugin when using same environment to launch different Spyder branches (master vs 5.x) ([PR 19742](https://github.com/spyder-ide/spyder/pull/19742) by [@mrclary](https://github.com/mrclary))
* [Issue 19712](https://github.com/spyder-ide/spyder/issues/19712) - Bootstrap incorrectly detects pylsp's install status ([PR 19847](https://github.com/spyder-ide/spyder/pull/19847) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19618](https://github.com/spyder-ide/spyder/issues/19618) - MacOS standalone installer PR build failing ([PR 19620](https://github.com/spyder-ide/spyder/pull/19620) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19602](https://github.com/spyder-ide/spyder/issues/19602) - `test_no_empty_file_items` not working on some CI setups ([PR 19617](https://github.com/spyder-ide/spyder/pull/19617) by [@stevetracvc](https://github.com/stevetracvc))
* [Issue 19520](https://github.com/spyder-ide/spyder/issues/19520) - SVG icons are blurry after update to 5.3 ([PR 19526](https://github.com/spyder-ide/spyder/pull/19526) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19516](https://github.com/spyder-ide/spyder/issues/19516) - Error when importing Django settings in the IPython console ([PR 19686](https://github.com/spyder-ide/spyder/pull/19686) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19514](https://github.com/spyder-ide/spyder/issues/19514) - AttributeError when updating folding ([PR 19680](https://github.com/spyder-ide/spyder/pull/19680) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19393](https://github.com/spyder-ide/spyder/issues/19393) - RuntimeError: wrapped C/C++ object of type EditorStack has been deleted ([PR 19471](https://github.com/spyder-ide/spyder/pull/19471) by [@impact27](https://github.com/impact27))
* [Issue 19385](https://github.com/spyder-ide/spyder/issues/19385) - Code analysis fails with `No module named pylint` on pip based installation ([PR 19477](https://github.com/spyder-ide/spyder/pull/19477) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19374](https://github.com/spyder-ide/spyder/issues/19374) - Switch to Editor hotkey broken (5.3.3) ([PR 19703](https://github.com/spyder-ide/spyder/pull/19703) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19372](https://github.com/spyder-ide/spyder/issues/19372) - Alt key pressed moves focus to the scrollbar (the left one) when focused on auto complete ([PR 19855](https://github.com/spyder-ide/spyder/pull/19855) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19355](https://github.com/spyder-ide/spyder/issues/19355) - `flush_std` is spamming Spyder-kernels ([PR 19510](https://github.com/spyder-ide/spyder/pull/19510) by [@impact27](https://github.com/impact27))
* [Issue 19344](https://github.com/spyder-ide/spyder/issues/19344) - Spyder hangs when trying to save a new Cython file if "Autoformat files on save" is selected ([PR 19380](https://github.com/spyder-ide/spyder/pull/19380) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19298](https://github.com/spyder-ide/spyder/issues/19298) - Error when starting kernel: "The following argument was not expected: /path/to/environment/" ([PR 19836](https://github.com/spyder-ide/spyder/pull/19836) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19283](https://github.com/spyder-ide/spyder/issues/19283) - KeyError when removing autosave files ([PR 19286](https://github.com/spyder-ide/spyder/pull/19286) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19248](https://github.com/spyder-ide/spyder/issues/19248) - Spyder hangs when saving .rst files ([PR 19380](https://github.com/spyder-ide/spyder/pull/19380) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19236](https://github.com/spyder-ide/spyder/issues/19236) - MacOS standalone not working due to pygments error ([PR 19240](https://github.com/spyder-ide/spyder/pull/19240) by [@mrclary](https://github.com/mrclary))
* [Issue 19232](https://github.com/spyder-ide/spyder/issues/19232) - "Scroll past the end" is not translated correctly in French (Editor)
* [Issue 19205](https://github.com/spyder-ide/spyder/issues/19205) - Project's folder is not added to sys.path when creating/loading a project with Spyder 5.3.2 ([PR 19253](https://github.com/spyder-ide/spyder/pull/19253) by [@mrclary](https://github.com/mrclary))
* [Issue 19145](https://github.com/spyder-ide/spyder/issues/19145) - AttributeError in the kernel when modifying `locals` ([PR 19686](https://github.com/spyder-ide/spyder/pull/19686) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19126](https://github.com/spyder-ide/spyder/issues/19126) - Error when trying to load Python files in the Variable Explorer ([PR 19702](https://github.com/spyder-ide/spyder/pull/19702) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19112](https://github.com/spyder-ide/spyder/issues/19112) - New update status bar default message, visibility behavior and update process for the Windows standalone installer ([PR 19793](https://github.com/spyder-ide/spyder/pull/19793) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19091](https://github.com/spyder-ide/spyder/issues/19091) - Spyder becomes sluggish if too much content is printed in the console ([PR 19866](https://github.com/spyder-ide/spyder/pull/19866) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19026](https://github.com/spyder-ide/spyder/issues/19026) - Memory leak with Matplotlib Qt/Automatic backend ([PR 19686](https://github.com/spyder-ide/spyder/pull/19686) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18870](https://github.com/spyder-ide/spyder/issues/18870) - Create conda-based standalone application ([PR 19461](https://github.com/spyder-ide/spyder/pull/19461) by [@mrclary](https://github.com/mrclary))
* [Issue 18642](https://github.com/spyder-ide/spyder/issues/18642) - Spyder unable to load Spyder 3 icon theme ([PR 19922](https://github.com/spyder-ide/spyder/pull/19922) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17577](https://github.com/spyder-ide/spyder/issues/17577) - Can't save an html file in Spyder ([PR 19380](https://github.com/spyder-ide/spyder/pull/19380) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17523](https://github.com/spyder-ide/spyder/issues/17523) - Console blocks when debugging if using the Tkinter graphics backend on Windows ([PR 19538](https://github.com/spyder-ide/spyder/pull/19538) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16634](https://github.com/spyder-ide/spyder/issues/16634) - Undocked Outline doesn't update ([PR 19448](https://github.com/spyder-ide/spyder/pull/19448) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16406](https://github.com/spyder-ide/spyder/issues/16406) - Outline not showing functions or erroneously showing imports as functions ([PR 19332](https://github.com/spyder-ide/spyder/pull/19332) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16352](https://github.com/spyder-ide/spyder/issues/16352) - Outline explorer seeing imported symbols from relative import with tuple syntax ([PR 19332](https://github.com/spyder-ide/spyder/pull/19332) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16166](https://github.com/spyder-ide/spyder/issues/16166) - New Pyx file fails to save with "Code Formatting" enabled ([PR 19380](https://github.com/spyder-ide/spyder/pull/19380) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15709](https://github.com/spyder-ide/spyder/issues/15709) - Pylint uses startup Python interpreter/enviroment even if costum interpreter/enviroment is set ([PR 15761](https://github.com/spyder-ide/spyder/pull/15761) by [@mwawra](https://github.com/mwawra))
* [Issue 15517](https://github.com/spyder-ide/spyder/issues/15517) - Outline pane navigates to the wrong file ([PR 19360](https://github.com/spyder-ide/spyder/pull/19360) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15437](https://github.com/spyder-ide/spyder/issues/15437) - Keyboard shortcut for Find not working in Mac ([PR 19795](https://github.com/spyder-ide/spyder/pull/19795) by [@mrclary](https://github.com/mrclary))
* [Issue 13090](https://github.com/spyder-ide/spyder/issues/13090) - Red text in Dependency dialog window is hard to read ([PR 19314](https://github.com/spyder-ide/spyder/pull/19314) by [@jitseniesen](https://github.com/jitseniesen))

In this release 48 issues were closed.

### Pull Requests Merged

* [PR 19978](https://github.com/spyder-ide/spyder/pull/19978) - PR: Update core dependencies for 5.4.0, by [@dalthviz](https://github.com/dalthviz) ([19893](https://github.com/spyder-ide/spyder/issues/19893))
* [PR 19969](https://github.com/spyder-ide/spyder/pull/19969) - PR: Some fixes to make Spyder work with the latest changes in PyLSP, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19957](https://github.com/spyder-ide/spyder/pull/19957) - PR: Update `spyder-kernels` subrepo to include constraint and fixes for `ipykernel` 6.16.1, by [@dalthviz](https://github.com/dalthviz) ([19874](https://github.com/spyder-ide/spyder/issues/19874))
* [PR 19947](https://github.com/spyder-ide/spyder/pull/19947) - PR: Fix out-of-order insertion of mixed stdin and stdout streams on macOS (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19888](https://github.com/spyder-ide/spyder/issues/19888))
* [PR 19936](https://github.com/spyder-ide/spyder/pull/19936) - PR: Update binder link and add instructions when releasing new versions to keep it updated, by [@dalthviz](https://github.com/dalthviz) ([19902](https://github.com/spyder-ide/spyder/issues/19902))
* [PR 19922](https://github.com/spyder-ide/spyder/pull/19922) - PR: Update `QtAwesome` constraint to >=1.2.1 (Dependencies), by [@dalthviz](https://github.com/dalthviz) ([18642](https://github.com/spyder-ide/spyder/issues/18642))
* [PR 19918](https://github.com/spyder-ide/spyder/pull/19918) - PR: Do not build experimental installer for win-64 on release, by [@mrclary](https://github.com/mrclary)
* [PR 19894](https://github.com/spyder-ide/spyder/pull/19894) - PR: Update download installer update cancel button size (Application), by [@dalthviz](https://github.com/dalthviz)
* [PR 19891](https://github.com/spyder-ide/spyder/pull/19891) - PR: Fix cell execution on Python 3.11 (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19862](https://github.com/spyder-ide/spyder/issues/19862))
* [PR 19880](https://github.com/spyder-ide/spyder/pull/19880) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 19875](https://github.com/spyder-ide/spyder/pull/19875) - PR: Fix handle current filename, by [@impact27](https://github.com/impact27)
* [PR 19871](https://github.com/spyder-ide/spyder/pull/19871) - PR: Only create the application update status bar for standalone installers, increase timer interval to start checking for updates and change cancel download button shape (Application), by [@dalthviz](https://github.com/dalthviz) ([19868](https://github.com/spyder-ide/spyder/issues/19868))
* [PR 19870](https://github.com/spyder-ide/spyder/pull/19870) - PR: Update translations for 5.4.0, by [@dalthviz](https://github.com/dalthviz)
* [PR 19867](https://github.com/spyder-ide/spyder/pull/19867) - PR: Fix `bootstrap.py` git subprocess call on Windows, by [@dalthviz](https://github.com/dalthviz) ([19865](https://github.com/spyder-ide/spyder/issues/19865))
* [PR 19866](https://github.com/spyder-ide/spyder/pull/19866) - PR: Set a much lower max value for buffer size (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19091](https://github.com/spyder-ide/spyder/issues/19091))
* [PR 19864](https://github.com/spyder-ide/spyder/pull/19864) - PR: Prevent error when multiple threads try to write messages from comm handlers (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19735](https://github.com/spyder-ide/spyder/issues/19735))
* [PR 19856](https://github.com/spyder-ide/spyder/pull/19856) - PR: Catch any error while reading Internal Console history file, by [@ccordoba12](https://github.com/ccordoba12) ([19850](https://github.com/spyder-ide/spyder/issues/19850))
* [PR 19855](https://github.com/spyder-ide/spyder/pull/19855) - PR: Improve how to save a file when the completion widget is visible (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([19372](https://github.com/spyder-ide/spyder/issues/19372))
* [PR 19847](https://github.com/spyder-ide/spyder/pull/19847) - PR: Fix detecting that python-lsp-server is installed in editable mode (Development), by [@ccordoba12](https://github.com/ccordoba12) ([19712](https://github.com/spyder-ide/spyder/issues/19712))
* [PR 19838](https://github.com/spyder-ide/spyder/pull/19838) - PR: Do not import spyder before install_repo in bootstrap.py, by [@mrclary](https://github.com/mrclary) ([19832](https://github.com/spyder-ide/spyder/issues/19832))
* [PR 19836](https://github.com/spyder-ide/spyder/pull/19836) - PR: Add benign error 'The following argument was not expected' (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([19298](https://github.com/spyder-ide/spyder/issues/19298))
* [PR 19830](https://github.com/spyder-ide/spyder/pull/19830) - PR: Catch an error when loading pages in `WebView` widgets, by [@ccordoba12](https://github.com/ccordoba12) ([19818](https://github.com/spyder-ide/spyder/issues/19818))
* [PR 19795](https://github.com/spyder-ide/spyder/pull/19795) - PR: Conform "find next" and "find previous" shortcuts to macOS standards, by [@mrclary](https://github.com/mrclary) ([15437](https://github.com/spyder-ide/spyder/issues/15437))
* [PR 19793](https://github.com/spyder-ide/spyder/pull/19793) - PR: Show installer download percentage progress in the status bar (Application), by [@dalthviz](https://github.com/dalthviz) ([19112](https://github.com/spyder-ide/spyder/issues/19112))
* [PR 19750](https://github.com/spyder-ide/spyder/pull/19750) - PR: Increase minimal required version of Qstylizer to 0.2.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19744](https://github.com/spyder-ide/spyder/pull/19744) - PR: Pin black to 22.8.0 (Mac app), by [@mrclary](https://github.com/mrclary) ([19743](https://github.com/spyder-ide/spyder/issues/19743))
* [PR 19742](https://github.com/spyder-ide/spyder/pull/19742) - PR: Reinstall spyder in editable mode in bootstrap if branch changed to/from master, by [@mrclary](https://github.com/mrclary) ([19728](https://github.com/spyder-ide/spyder/issues/19728))
* [PR 19703](https://github.com/spyder-ide/spyder/pull/19703) - PR: Fix keyboard shortcut to switch to the Editor, by [@ccordoba12](https://github.com/ccordoba12) ([19374](https://github.com/spyder-ide/spyder/issues/19374))
* [PR 19702](https://github.com/spyder-ide/spyder/pull/19702) - PR: Catch error when trying to load unsupported data files (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19126](https://github.com/spyder-ide/spyder/issues/19126))
* [PR 19700](https://github.com/spyder-ide/spyder/pull/19700) - PR: Add dialog to confirm downloaded installer installation and update related code organization (Application), by [@dalthviz](https://github.com/dalthviz)
* [PR 19690](https://github.com/spyder-ide/spyder/pull/19690) - PR: Simplify `test_no_empty_file_items` to only check filenames and total number of results, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 19686](https://github.com/spyder-ide/spyder/pull/19686) - PR: Fix some errors when computing the namespace view and a memory leak with the Matplotlib Qt backend (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19516](https://github.com/spyder-ide/spyder/issues/19516), [19145](https://github.com/spyder-ide/spyder/issues/19145), [19026](https://github.com/spyder-ide/spyder/issues/19026))
* [PR 19680](https://github.com/spyder-ide/spyder/pull/19680) - PR: Prevent error when trying to update folding info (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([19514](https://github.com/spyder-ide/spyder/issues/19514))
* [PR 19646](https://github.com/spyder-ide/spyder/pull/19646) - PR: Show Spyder-kernels message on restarts (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19620](https://github.com/spyder-ide/spyder/pull/19620) - PR: Pin Sphinx to version 5.1.1 to prevent errors on MacOS installer build, by [@dalthviz](https://github.com/dalthviz) ([19618](https://github.com/spyder-ide/spyder/issues/19618))
* [PR 19617](https://github.com/spyder-ide/spyder/pull/19617) - PR: Temporary fix for function `test_no_empty_file_items`, by [@stevetracvc](https://github.com/stevetracvc) ([19602](https://github.com/spyder-ide/spyder/issues/19602))
* [PR 19564](https://github.com/spyder-ide/spyder/pull/19564) - PR: Update `test_no_empty_file_items` to work with all possible OS results (Find in Files), by [@dalthviz](https://github.com/dalthviz)
* [PR 19553](https://github.com/spyder-ide/spyder/pull/19553) - PR: Fixes to improve compatibility with PySide2, by [@rear1019](https://github.com/rear1019)
* [PR 19549](https://github.com/spyder-ide/spyder/pull/19549) - PR: Fix errors when Projects plugin is disabled, by [@rear1019](https://github.com/rear1019)
* [PR 19538](https://github.com/spyder-ide/spyder/pull/19538) - PR: Update Tkinter assets copy logic for the Windows installer and fix Tkinter backend handling when debugging, by [@dalthviz](https://github.com/dalthviz) ([17523](https://github.com/spyder-ide/spyder/issues/17523))
* [PR 19526](https://github.com/spyder-ide/spyder/pull/19526) - PR: Fix showing pixelated SVG icons on high dpi screens, by [@ccordoba12](https://github.com/ccordoba12) ([19520](https://github.com/spyder-ide/spyder/issues/19520))
* [PR 19510](https://github.com/spyder-ide/spyder/pull/19510) - PR: Remove polling std streams, by [@impact27](https://github.com/impact27) ([19355](https://github.com/spyder-ide/spyder/issues/19355))
* [PR 19485](https://github.com/spyder-ide/spyder/pull/19485) - PR: Use a more recent Python version for our Mac app, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19477](https://github.com/spyder-ide/spyder/pull/19477) - PR: Add `APPDATA` environment variable to Pylint process (Pylint), by [@dalthviz](https://github.com/dalthviz) ([19385](https://github.com/spyder-ide/spyder/issues/19385))
* [PR 19471](https://github.com/spyder-ide/spyder/pull/19471) - PR: Remove lambdas in Qt slots, by [@impact27](https://github.com/impact27) ([19393](https://github.com/spyder-ide/spyder/issues/19393))
* [PR 19461](https://github.com/spyder-ide/spyder/pull/19461) - PR: Create conda-based application installer for macOS and Linux, by [@mrclary](https://github.com/mrclary) ([18870](https://github.com/spyder-ide/spyder/issues/18870))
* [PR 19448](https://github.com/spyder-ide/spyder/pull/19448) - PR: Greatly improve Outline performance and update it correctly when it becomes visible, by [@ccordoba12](https://github.com/ccordoba12) ([16634](https://github.com/spyder-ide/spyder/issues/16634))
* [PR 19380](https://github.com/spyder-ide/spyder/pull/19380) - PR: Only autoformat on save if the file is a Python file (Editor), by [@dalthviz](https://github.com/dalthviz) ([19344](https://github.com/spyder-ide/spyder/issues/19344), [19248](https://github.com/spyder-ide/spyder/issues/19248), [17577](https://github.com/spyder-ide/spyder/issues/17577), [16166](https://github.com/spyder-ide/spyder/issues/16166))
* [PR 19360](https://github.com/spyder-ide/spyder/pull/19360) - PR: Reload symbols when saving a file through the `Save as` menu entry (Outline), by [@ccordoba12](https://github.com/ccordoba12) ([15517](https://github.com/spyder-ide/spyder/issues/15517))
* [PR 19332](https://github.com/spyder-ide/spyder/pull/19332) - PR: Show symbols for namespace packages in the Outline, by [@ccordoba12](https://github.com/ccordoba12) ([16406](https://github.com/spyder-ide/spyder/issues/16406), [16352](https://github.com/spyder-ide/spyder/issues/16352))
* [PR 19314](https://github.com/spyder-ide/spyder/pull/19314) - PR: Change colours in Dependencies dialog window, by [@jitseniesen](https://github.com/jitseniesen) ([13090](https://github.com/spyder-ide/spyder/issues/13090))
* [PR 19297](https://github.com/spyder-ide/spyder/pull/19297) - PR: Improve style of the IPython console a bit, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19287](https://github.com/spyder-ide/spyder/pull/19287) - PR: Remove `main_toolbar` and `main_toolbar_actions` attributes (Main Window), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19286](https://github.com/spyder-ide/spyder/pull/19286) - PR: Catch error when removing autosave files (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([19283](https://github.com/spyder-ide/spyder/issues/19283))
* [PR 19253](https://github.com/spyder-ide/spyder/pull/19253) - PR: Ensure that project path is added to `spyder_pythonpath`, by [@mrclary](https://github.com/mrclary) ([19205](https://github.com/spyder-ide/spyder/issues/19205))
* [PR 19240](https://github.com/spyder-ide/spyder/pull/19240) - PR: Add Pygments to the list of packages placed out of the zipped library (Mac app), by [@mrclary](https://github.com/mrclary) ([19236](https://github.com/spyder-ide/spyder/issues/19236))
* [PR 18619](https://github.com/spyder-ide/spyder/pull/18619) - PR: Improve update UX and automatically download latest installers, by [@jsbautista](https://github.com/jsbautista)
* [PR 18397](https://github.com/spyder-ide/spyder/pull/18397) - PR: Show environment variables for all operating systems and modernize `spyder.utils.environ` module, by [@mrclary](https://github.com/mrclary)
* [PR 15761](https://github.com/spyder-ide/spyder/pull/15761) - PR: Add environment of custom interpreter to Pylint plugin, by [@mwawra](https://github.com/mwawra) ([15709](https://github.com/spyder-ide/spyder/issues/15709))

In this release 59 pull requests were closed.


----


## Version 5.3.3 (2022-08-29)

### New features

* Printing files now uses a light syntax highlighting theme to prevent printing files with dark backgrounds.
* MacOS standalone installer now are being build using MacOS 11 instead of MacOS 10.15

### Important fixes

* Fix several bugs related with the Layout plugin (save visible plugins to restore their visiility and tabify behavior for external plugins).
* Fix several bugs related with the focus management between the Editor and other panes.
* Improve Find and Replace speed on the Editor.
* Fixes to the MacOS standalone application to support being code signed.

### Issues Closed

* [Issue 19176](https://github.com/spyder-ide/spyder/issues/19176) - Release Spyder 5.3.3 ([PR 19224](https://github.com/spyder-ide/spyder/pull/19224) by [@dalthviz](https://github.com/dalthviz))
* [Issue 19172](https://github.com/spyder-ide/spyder/issues/19172) - AttributeError when closing main window ([PR 19177](https://github.com/spyder-ide/spyder/pull/19177) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19109](https://github.com/spyder-ide/spyder/issues/19109) - RuntimeError when opening a new editor window ([PR 19114](https://github.com/spyder-ide/spyder/pull/19114) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19087](https://github.com/spyder-ide/spyder/issues/19087) - ValueError when trying to update Completios status bar widget ([PR 19096](https://github.com/spyder-ide/spyder/pull/19096) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19084](https://github.com/spyder-ide/spyder/issues/19084) - Layout is broken sometimes when many consoles are open ([PR 19085](https://github.com/spyder-ide/spyder/pull/19085) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19042](https://github.com/spyder-ide/spyder/issues/19042) - Console looses focus while typing debugging commands on it ([PR 19043](https://github.com/spyder-ide/spyder/pull/19043) by [@impact27](https://github.com/impact27))
* [Issue 19003](https://github.com/spyder-ide/spyder/issues/19003) - IPython ignore "Open IPython console here" ([PR 19068](https://github.com/spyder-ide/spyder/pull/19068) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19000](https://github.com/spyder-ide/spyder/issues/19000) - Extra info displayed about Python interpreter in status bar ([PR 19082](https://github.com/spyder-ide/spyder/pull/19082) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18929](https://github.com/spyder-ide/spyder/issues/18929) - Error when opening Preferences ([PR 19027](https://github.com/spyder-ide/spyder/pull/19027) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18908](https://github.com/spyder-ide/spyder/issues/18908) - PYDEVD kernel error when starting Spyder ([PR 18981](https://github.com/spyder-ide/spyder/pull/18981) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18901](https://github.com/spyder-ide/spyder/issues/18901) - Windows standalone version crashes on launch with an AttributeError ([PR 18910](https://github.com/spyder-ide/spyder/pull/18910) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18887](https://github.com/spyder-ide/spyder/issues/18887) - Mistranslation in Japanese locale
* [Issue 18856](https://github.com/spyder-ide/spyder/issues/18856) - Error when trying to plot local variables in variable explorer when using Spyder 5.3.2 ([PR 18894](https://github.com/spyder-ide/spyder/pull/18894) by [@impact27](https://github.com/impact27))
* [Issue 18817](https://github.com/spyder-ide/spyder/issues/18817) - Editor tabs min. width too small when many tabs ([PR 19037](https://github.com/spyder-ide/spyder/pull/19037) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18776](https://github.com/spyder-ide/spyder/issues/18776) - Help pane unable to render rich text on macOS app ([PR 18789](https://github.com/spyder-ide/spyder/pull/18789) by [@mrclary](https://github.com/mrclary))
* [Issue 18764](https://github.com/spyder-ide/spyder/issues/18764) - Memory leak when closing editor or console tabs ([PR 18781](https://github.com/spyder-ide/spyder/pull/18781) by [@impact27](https://github.com/impact27))
* [Issue 18690](https://github.com/spyder-ide/spyder/issues/18690) - Spyder code contains CRLF line endings in several files ([PR 18691](https://github.com/spyder-ide/spyder/pull/18691) by [@impact27](https://github.com/impact27))
* [Issue 18661](https://github.com/spyder-ide/spyder/issues/18661) - Code signature breaks micromamba in macOS application ([PR 18685](https://github.com/spyder-ide/spyder/pull/18685) by [@mrclary](https://github.com/mrclary))
* [Issue 18520](https://github.com/spyder-ide/spyder/issues/18520) - Segmentation fault crash from the Editor ([PR 18686](https://github.com/spyder-ide/spyder/pull/18686) by [@impact27](https://github.com/impact27))
* [Issue 18434](https://github.com/spyder-ide/spyder/issues/18434) - Already executed Dask tasks get re-executed in Spyder ([PR 18941](https://github.com/spyder-ide/spyder/pull/18941) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18283](https://github.com/spyder-ide/spyder/issues/18283) - Blurry Spyder icon on Windows taskbar ([PR 18992](https://github.com/spyder-ide/spyder/pull/18992) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17907](https://github.com/spyder-ide/spyder/issues/17907) - DuplicateOptionError when reading workspace.ini project file ([PR 19123](https://github.com/spyder-ide/spyder/pull/19123) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17710](https://github.com/spyder-ide/spyder/issues/17710) - Randomly broken input function ([PR 18439](https://github.com/spyder-ide/spyder/pull/18439) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17443](https://github.com/spyder-ide/spyder/issues/17443) - IndexError in Find pane ([PR 19124](https://github.com/spyder-ide/spyder/pull/19124) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16975](https://github.com/spyder-ide/spyder/issues/16975) - Replace all is not efficient ([PR 16988](https://github.com/spyder-ide/spyder/pull/16988) by [@impact27](https://github.com/impact27))
* [Issue 16256](https://github.com/spyder-ide/spyder/issues/16256) - Files shown without hits when maximum number of results reached ([PR 19124](https://github.com/spyder-ide/spyder/pull/19124) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15471](https://github.com/spyder-ide/spyder/issues/15471) - Lag in the editor, replace all hangs Spyder indefinitely ([PR 16988](https://github.com/spyder-ide/spyder/pull/16988) by [@impact27](https://github.com/impact27))
* [Issue 15405](https://github.com/spyder-ide/spyder/issues/15405) - TypeError: 'method' object is not connected when running from the Files pane ([PR 19160](https://github.com/spyder-ide/spyder/pull/19160) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14176](https://github.com/spyder-ide/spyder/issues/14176) - Spyder crashes when replacing text ([PR 16988](https://github.com/spyder-ide/spyder/pull/16988) by [@impact27](https://github.com/impact27))
* [Issue 12104](https://github.com/spyder-ide/spyder/issues/12104) - Save list of visible panes before closing Spyder and restore them on the next session ([PR 18962](https://github.com/spyder-ide/spyder/pull/18962) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 7196](https://github.com/spyder-ide/spyder/issues/7196) - Unable to save workspace on Linux ([PR 17790](https://github.com/spyder-ide/spyder/pull/17790) by [@maurerle](https://github.com/maurerle))
* [Issue 3221](https://github.com/spyder-ide/spyder/issues/3221) - Editor loses cursor focus after running cell when IPython console is detached ([PR 18928](https://github.com/spyder-ide/spyder/pull/18928) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 2521](https://github.com/spyder-ide/spyder/issues/2521) - Printing from the editor shows dark background or blank text ([PR 18808](https://github.com/spyder-ide/spyder/pull/18808) by [@ccordoba12](https://github.com/ccordoba12))

In this release 33 issues were closed.

### Pull Requests Merged

* [PR 19224](https://github.com/spyder-ide/spyder/pull/19224) - PR: Update core dependencies for 5.3.3, by [@dalthviz](https://github.com/dalthviz) ([19176](https://github.com/spyder-ide/spyder/issues/19176))
* [PR 19177](https://github.com/spyder-ide/spyder/pull/19177) - PR: Validate that Layout plugin exists in `moveEvent` method (Main Window), by [@ccordoba12](https://github.com/ccordoba12) ([19172](https://github.com/spyder-ide/spyder/issues/19172))
* [PR 19163](https://github.com/spyder-ide/spyder/pull/19163) - PR: Several fixes related to the tabify plugins functionality, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19160](https://github.com/spyder-ide/spyder/pull/19160) - PR: Ensure correct client and shellwidget are used to execute code in new consoles when multiple scripts are run at the same time (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([15405](https://github.com/spyder-ide/spyder/issues/15405))
* [PR 19143](https://github.com/spyder-ide/spyder/pull/19143) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 19142](https://github.com/spyder-ide/spyder/pull/19142) - PR: Update translations for 5.3.3, by [@dalthviz](https://github.com/dalthviz)
* [PR 19124](https://github.com/spyder-ide/spyder/pull/19124) - PR: Fix a couple of bugs in the Find plugin, by [@ccordoba12](https://github.com/ccordoba12) ([17443](https://github.com/spyder-ide/spyder/issues/17443), [16256](https://github.com/spyder-ide/spyder/issues/16256))
* [PR 19123](https://github.com/spyder-ide/spyder/pull/19123) - PR: Recreate config in case of errors while reading it (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([17907](https://github.com/spyder-ide/spyder/issues/17907))
* [PR 19114](https://github.com/spyder-ide/spyder/pull/19114) - PR: Catch an error when creating new editor windows, by [@ccordoba12](https://github.com/ccordoba12) ([19109](https://github.com/spyder-ide/spyder/issues/19109))
* [PR 19096](https://github.com/spyder-ide/spyder/pull/19096) - PR: Avoid a ValueError when splitting a string (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([19087](https://github.com/spyder-ide/spyder/issues/19087))
* [PR 19085](https://github.com/spyder-ide/spyder/pull/19085) - PR: Restore the previous way of closing all clients (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([19084](https://github.com/spyder-ide/spyder/issues/19084))
* [PR 19083](https://github.com/spyder-ide/spyder/pull/19083) - PR: Handle default Win installer pythonw interpreter to get Python version (Status), by [@dalthviz](https://github.com/dalthviz)
* [PR 19082](https://github.com/spyder-ide/spyder/pull/19082) - PR: Add regex check for interpreter info output (Programs), by [@dalthviz](https://github.com/dalthviz) ([19000](https://github.com/spyder-ide/spyder/issues/19000))
* [PR 19068](https://github.com/spyder-ide/spyder/pull/19068) - PR: Fix syncing IPython console cwd with the Working directory toolbar, by [@ccordoba12](https://github.com/ccordoba12) ([19003](https://github.com/spyder-ide/spyder/issues/19003))
* [PR 19066](https://github.com/spyder-ide/spyder/pull/19066) - PR: Fix focus when debugging cells, by [@impact27](https://github.com/impact27)
* [PR 19043](https://github.com/spyder-ide/spyder/pull/19043) - PR: Keep focus in shellwidget while debugging, by [@impact27](https://github.com/impact27) ([19042](https://github.com/spyder-ide/spyder/issues/19042))
* [PR 19037](https://github.com/spyder-ide/spyder/pull/19037) - PR: Set elide mode to prevent tabs text eliding on MacOS (Tabs), by [@dalthviz](https://github.com/dalthviz) ([18817](https://github.com/spyder-ide/spyder/issues/18817))
* [PR 19027](https://github.com/spyder-ide/spyder/pull/19027) - PR: Add cast for custom syntax highlighting themes names to string (Appereance), by [@dalthviz](https://github.com/dalthviz) ([18929](https://github.com/spyder-ide/spyder/issues/18929))
* [PR 19025](https://github.com/spyder-ide/spyder/pull/19025) - PR: Allow plugins/widgets to ask for app restarts by emitting a signal, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19008](https://github.com/spyder-ide/spyder/pull/19008) - PR: Add the ability to request unmaximizing plugins from widgets and remove redeclared signals/connections in widgets, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18992](https://github.com/spyder-ide/spyder/pull/18992) - PR: Pass resample kwarg when getting .ico icon for Windows, by [@dalthviz](https://github.com/dalthviz) ([18283](https://github.com/spyder-ide/spyder/issues/18283))
* [PR 18981](https://github.com/spyder-ide/spyder/pull/18981) - PR: Add PYDEVD debug warning message to benign errors (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([18908](https://github.com/spyder-ide/spyder/issues/18908))
* [PR 18962](https://github.com/spyder-ide/spyder/pull/18962) - PR: Restore plugins that were visible during the previous session, by [@ccordoba12](https://github.com/ccordoba12) ([12104](https://github.com/spyder-ide/spyder/issues/12104))
* [PR 18941](https://github.com/spyder-ide/spyder/pull/18941) - PR: Prevent triggering Dask tasks when getting variables properties (IPython console), by [@dalthviz](https://github.com/dalthviz) ([18434](https://github.com/spyder-ide/spyder/issues/18434))
* [PR 18928](https://github.com/spyder-ide/spyder/pull/18928) - PR: Improve `Maintain focus in the editor` option and unmaximize plugins when running/debugging code, by [@ccordoba12](https://github.com/ccordoba12) ([3221](https://github.com/spyder-ide/spyder/issues/3221))
* [PR 18911](https://github.com/spyder-ide/spyder/pull/18911) - PR: Add methods to simplify access to our config system to `MainWindow`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18910](https://github.com/spyder-ide/spyder/pull/18910) - PR: Fix call to show compatibility message for plugins (Mainwindow), by [@dalthviz](https://github.com/dalthviz) ([18901](https://github.com/spyder-ide/spyder/issues/18901))
* [PR 18894](https://github.com/spyder-ide/spyder/pull/18894) - PR: Add a test for plotting from the Variable Explorer while debugging, by [@impact27](https://github.com/impact27) ([18856](https://github.com/spyder-ide/spyder/issues/18856))
* [PR 18869](https://github.com/spyder-ide/spyder/pull/18869) - PR: Make style of "Print preview" dialog follow the rest of Spyder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18863](https://github.com/spyder-ide/spyder/pull/18863) - PR: Fix EOL for missed files, by [@mrclary](https://github.com/mrclary)
* [PR 18851](https://github.com/spyder-ide/spyder/pull/18851) - PR: Use Mac 12 to run tests on CIs and Mac 11 for the standalone app, by [@impact27](https://github.com/impact27)
* [PR 18831](https://github.com/spyder-ide/spyder/pull/18831) - PR: Don't apply color schemes that require a restart and fix other issues about them, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18808](https://github.com/spyder-ide/spyder/pull/18808) - PR: Use an instance of SimpleCodeEditor to print files (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([2521](https://github.com/spyder-ide/spyder/issues/2521))
* [PR 18802](https://github.com/spyder-ide/spyder/pull/18802) - PR: Run all tests, not stopping on first failure (Testing), by [@juliangilbey](https://github.com/juliangilbey)
* [PR 18789](https://github.com/spyder-ide/spyder/pull/18789) - PR: Fix issue where QtWebEngineProcess was not working properly in signed macOS app, by [@mrclary](https://github.com/mrclary) ([18776](https://github.com/spyder-ide/spyder/issues/18776))
* [PR 18781](https://github.com/spyder-ide/spyder/pull/18781) - PR: Close memory leaks of CodeEditor and ShellWidget, by [@impact27](https://github.com/impact27) ([18764](https://github.com/spyder-ide/spyder/issues/18764))
* [PR 18768](https://github.com/spyder-ide/spyder/pull/18768) - PR: Prefer a run-slow skip reason over an already passed one (Testing), by [@juliangilbey](https://github.com/juliangilbey)
* [PR 18767](https://github.com/spyder-ide/spyder/pull/18767) - PR: Catch all passed tests, including parametrized tests with spaces in parameters, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 18765](https://github.com/spyder-ide/spyder/pull/18765) - PR: Remove remaining call to `update_extra_selections` (Editor), by [@impact27](https://github.com/impact27)
* [PR 18762](https://github.com/spyder-ide/spyder/pull/18762) - PR: Use run_tests script to run tests on Windows (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18691](https://github.com/spyder-ide/spyder/pull/18691) - PR: Enforce LF line endings in Spyder code, by [@impact27](https://github.com/impact27) ([18690](https://github.com/spyder-ide/spyder/issues/18690))
* [PR 18686](https://github.com/spyder-ide/spyder/pull/18686) - PR: Prevent segfault when modifying the editor content, by [@impact27](https://github.com/impact27) ([18520](https://github.com/spyder-ide/spyder/issues/18520))
* [PR 18685](https://github.com/spyder-ide/spyder/pull/18685) - PR: Patch rpath in micromamba so that code signing doesn't break it, by [@mrclary](https://github.com/mrclary) ([18661](https://github.com/spyder-ide/spyder/issues/18661))
* [PR 18682](https://github.com/spyder-ide/spyder/pull/18682) - PR: Fix a few typos, by [@timgates42](https://github.com/timgates42)
* [PR 18681](https://github.com/spyder-ide/spyder/pull/18681) - PR: Minor fix to improve compatibility with PySide2, by [@rear1019](https://github.com/rear1019)
* [PR 18439](https://github.com/spyder-ide/spyder/pull/18439) - PR: Increase minimal required version of Qtconsole to 5.3.2, by [@ccordoba12](https://github.com/ccordoba12) ([17710](https://github.com/spyder-ide/spyder/issues/17710))
* [PR 17790](https://github.com/spyder-ide/spyder/pull/17790) - PR: Fix saving variables as .spydata if no file extension is given, by [@maurerle](https://github.com/maurerle) ([7196](https://github.com/spyder-ide/spyder/issues/7196))
* [PR 16988](https://github.com/spyder-ide/spyder/pull/16988) - PR: Fix slow find in large files (Editor), by [@impact27](https://github.com/impact27) ([16975](https://github.com/spyder-ide/spyder/issues/16975), [15471](https://github.com/spyder-ide/spyder/issues/15471), [14176](https://github.com/spyder-ide/spyder/issues/14176))

In this release 48 pull requests were closed.


----


## Version 5.3.2 (2022-07-13)

### New features

* Add code signing to the standalone macOS installer.
* Add `openpyxml` and `defusedxml` to the packages bundled with the standalone Windows and macOS installers.
* New entry from the Editor context menu to `Show help for current object`.
* Improve UX/UI for the repositioning panes functionality.

### Important fixes

* Fix several bugs related to the debugging functionality (remote kernels usage and Pdb history).
* Fix incompatibility with Pylint 2.14.0+.
* Fix Windows Python environment activation script with micromamba.
* Fix several bugs related with the Plots pane.

### New API features

* Add `create_client_for_kernel` and `rename_client_tab` to the Ipython Console plugin so that other plugins can access to console creation like [Spyder-notebook](https://github.com/spyder-ide/spyder-notebook/pull/369).

### Issues Closed

* [Issue 18624](https://github.com/spyder-ide/spyder/issues/18624) - Asking to save modified file twice ([PR 18625](https://github.com/spyder-ide/spyder/pull/18625) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18599](https://github.com/spyder-ide/spyder/issues/18599) - Issue reporter raises AttributeError upon dismissing ([PR 18613](https://github.com/spyder-ide/spyder/pull/18613) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18597](https://github.com/spyder-ide/spyder/issues/18597) - Opening preferences results in UnboundLocalError in macOS app ([PR 18598](https://github.com/spyder-ide/spyder/pull/18598) by [@mrclary](https://github.com/mrclary))
* [Issue 18531](https://github.com/spyder-ide/spyder/issues/18531) - Error when creating Pdb history file ([PR 18533](https://github.com/spyder-ide/spyder/pull/18533) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18479](https://github.com/spyder-ide/spyder/issues/18479) - Release Spyder 5.3.2 ([PR 18655](https://github.com/spyder-ide/spyder/pull/18655) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18407](https://github.com/spyder-ide/spyder/issues/18407) - Numpy 1.23.0 breaks autocompletion and makes the tests fail ([PR 18413](https://github.com/spyder-ide/spyder/pull/18413) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18330](https://github.com/spyder-ide/spyder/issues/18330) - Errors when debugging with remote kernel ([PR 18512](https://github.com/spyder-ide/spyder/pull/18512) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18290](https://github.com/spyder-ide/spyder/issues/18290) - Error when enabling `Underline errors and warnings` linting option ([PR 18303](https://github.com/spyder-ide/spyder/pull/18303) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18262](https://github.com/spyder-ide/spyder/issues/18262) - OSError when trying to start files server ([PR 18437](https://github.com/spyder-ide/spyder/pull/18437) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18175](https://github.com/spyder-ide/spyder/issues/18175) - Pylint 2.14.0 code analysis won't work on miniconda conda-forge install on Windows ([PR 18106](https://github.com/spyder-ide/spyder/pull/18106) by [@dalthviz](https://github.com/dalthviz))
* [Issue 18071](https://github.com/spyder-ide/spyder/issues/18071) - Missing Pandas optional dependency `openpyxl` to read excel files on installers
* [Issue 18010](https://github.com/spyder-ide/spyder/issues/18010) - Fatal Python error when running profiler in macOS app with external environment ([PR 18031](https://github.com/spyder-ide/spyder/pull/18031) by [@mrclary](https://github.com/mrclary))
* [Issue 18005](https://github.com/spyder-ide/spyder/issues/18005) - TypeError when getting background color - DataFrameEditor ([PR 18007](https://github.com/spyder-ide/spyder/pull/18007) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 18003](https://github.com/spyder-ide/spyder/issues/18003) - Matplotlib not installed or didn't load correctly in Spyder 5.3.1 ([PR 18387](https://github.com/spyder-ide/spyder/pull/18387) by [@mrclary](https://github.com/mrclary))
* [Issue 17945](https://github.com/spyder-ide/spyder/issues/17945) - IPython console widget size changes on startup if vertical panes are combined ([PR 18332](https://github.com/spyder-ide/spyder/pull/18332) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17915](https://github.com/spyder-ide/spyder/issues/17915) - Startup run code of IPython is not working when using projects ([PR 17997](https://github.com/spyder-ide/spyder/pull/17997) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17872](https://github.com/spyder-ide/spyder/issues/17872) - Python interpreter file browser resolves symlinks ([PR 17874](https://github.com/spyder-ide/spyder/pull/17874) by [@mrclary](https://github.com/mrclary))
* [Issue 17835](https://github.com/spyder-ide/spyder/issues/17835) - Problems with Spyder on Mac with Conda-forge and `applaunchservices` ([PR 18530](https://github.com/spyder-ide/spyder/pull/18530) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17815](https://github.com/spyder-ide/spyder/issues/17815) - Check usage of `pytest-timeout` to prevent some tests from hanging the CI  ([PR 17990](https://github.com/spyder-ide/spyder/pull/17990) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17753](https://github.com/spyder-ide/spyder/issues/17753) - Another ZeroDivisionError in the Plots pane ([PR 18504](https://github.com/spyder-ide/spyder/pull/18504) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17701](https://github.com/spyder-ide/spyder/issues/17701) - Disable pyls-flake8 in PyLSP configuration ([PR 18438](https://github.com/spyder-ide/spyder/pull/18438) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17511](https://github.com/spyder-ide/spyder/issues/17511) - Inconsistent use of system PYTHONPATH in completions and IPython Console ([PR 17512](https://github.com/spyder-ide/spyder/pull/17512) by [@mrclary](https://github.com/mrclary))
* [Issue 17425](https://github.com/spyder-ide/spyder/issues/17425) - Small bugs in kernel update error screen ([PR 18471](https://github.com/spyder-ide/spyder/pull/18471) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17406](https://github.com/spyder-ide/spyder/issues/17406) - Questions about development environment ([PR 17408](https://github.com/spyder-ide/spyder/pull/17408) by [@mrclary](https://github.com/mrclary))
* [Issue 16414](https://github.com/spyder-ide/spyder/issues/16414) - Add code signing to macOS installer ([PR 16490](https://github.com/spyder-ide/spyder/pull/16490) by [@mrclary](https://github.com/mrclary))
* [Issue 15223](https://github.com/spyder-ide/spyder/issues/15223) - ZeroDivisionError when generating thumbnail in Plots ([PR 18504](https://github.com/spyder-ide/spyder/pull/18504) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15074](https://github.com/spyder-ide/spyder/issues/15074) - Screen flickering the first time I open Spyder (MacOS) ([PR 18332](https://github.com/spyder-ide/spyder/pull/18332) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14883](https://github.com/spyder-ide/spyder/issues/14883) - `A monitor scale changed was detected` message blocks the window ([PR 18323](https://github.com/spyder-ide/spyder/pull/18323) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14806](https://github.com/spyder-ide/spyder/issues/14806) - CTRL-S does not save file, if pop-up menu is open ([PR 18414](https://github.com/spyder-ide/spyder/pull/18414) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13812](https://github.com/spyder-ide/spyder/issues/13812) - Error in tutorial ([PR 18194](https://github.com/spyder-ide/spyder/pull/18194) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13043](https://github.com/spyder-ide/spyder/issues/13043) - Beginners Tutorial is wrong ([PR 18194](https://github.com/spyder-ide/spyder/pull/18194) by [@dalthviz](https://github.com/dalthviz))
* [Issue 10603](https://github.com/spyder-ide/spyder/issues/10603) - Segmentation fault when accesing void object of numpy module ([PR 10617](https://github.com/spyder-ide/spyder/pull/10617) by [@impact27](https://github.com/impact27))
* [Issue 978](https://github.com/spyder-ide/spyder/issues/978) - Add "Show help for current object" option to Editor context menu ([PR 18180](https://github.com/spyder-ide/spyder/pull/18180) by [@jsbautista](https://github.com/jsbautista))

In this release 33 issues were closed.

### Pull Requests Merged

* [PR 18655](https://github.com/spyder-ide/spyder/pull/18655) - PR: Update core dependencies for 5.3.2, by [@dalthviz](https://github.com/dalthviz) ([18479](https://github.com/spyder-ide/spyder/issues/18479))
* [PR 18625](https://github.com/spyder-ide/spyder/pull/18625) - PR: Don't double validate if plugins can be deleted/closed (Registry), by [@dalthviz](https://github.com/dalthviz) ([18624](https://github.com/spyder-ide/spyder/issues/18624))
* [PR 18613](https://github.com/spyder-ide/spyder/pull/18613) - PR: Fix error when closing error dialog (Console), by [@ccordoba12](https://github.com/ccordoba12) ([18599](https://github.com/spyder-ide/spyder/issues/18599))
* [PR 18598](https://github.com/spyder-ide/spyder/pull/18598) - PR: Fix issue where macOS_group was referenced before assignment (Preferences), by [@mrclary](https://github.com/mrclary) ([18597](https://github.com/spyder-ide/spyder/issues/18597))
* [PR 18573](https://github.com/spyder-ide/spyder/pull/18573) - PR: Update minimal required version for PyLSP to 1.5.0 and its subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18548](https://github.com/spyder-ide/spyder/pull/18548) - PR: Change default installers assets download URL (Windows), by [@dalthviz](https://github.com/dalthviz)
* [PR 18544](https://github.com/spyder-ide/spyder/pull/18544) - PR: Add new API methods to the IPython console, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18533](https://github.com/spyder-ide/spyder/pull/18533) - PR: Catch errors when creating or accessing Pdb history (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([18531](https://github.com/spyder-ide/spyder/issues/18531))
* [PR 18530](https://github.com/spyder-ide/spyder/pull/18530) - PR: Require `applaunchservices` 0.3.0+, by [@ccordoba12](https://github.com/ccordoba12) ([17835](https://github.com/spyder-ide/spyder/issues/17835))
* [PR 18519](https://github.com/spyder-ide/spyder/pull/18519) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 18518](https://github.com/spyder-ide/spyder/pull/18518) - PR: Update translations for 5.3.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 18513](https://github.com/spyder-ide/spyder/pull/18513) - PR: Add tests for running namespace, by [@impact27](https://github.com/impact27)
* [PR 18512](https://github.com/spyder-ide/spyder/pull/18512) - PR: Fix filenames used for remote kernels while debugging, by [@ccordoba12](https://github.com/ccordoba12) ([18330](https://github.com/spyder-ide/spyder/issues/18330))
* [PR 18506](https://github.com/spyder-ide/spyder/pull/18506) - PR: Restrict unnecessary workflows when only installer files are changed., by [@mrclary](https://github.com/mrclary)
* [PR 18504](https://github.com/spyder-ide/spyder/pull/18504) - PR: Prevent ZeroDivisionError when calculating plots scales and sizes (Plots), by [@dalthviz](https://github.com/dalthviz) ([17753](https://github.com/spyder-ide/spyder/issues/17753), [15223](https://github.com/spyder-ide/spyder/issues/15223))
* [PR 18485](https://github.com/spyder-ide/spyder/pull/18485) - PR: Remove `applaunchservices` dependency for macOS app, by [@mrclary](https://github.com/mrclary)
* [PR 18481](https://github.com/spyder-ide/spyder/pull/18481) - PR: Copy all NSIS plugins into discoverable path for the Windows installer build, by [@jsbautista](https://github.com/jsbautista)
* [PR 18471](https://github.com/spyder-ide/spyder/pull/18471) - PR: Escape hyphen from update instructions for spyder-kernels (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([17425](https://github.com/spyder-ide/spyder/issues/17425))
* [PR 18438](https://github.com/spyder-ide/spyder/pull/18438) - PR: Disable pyls-flake8 plugin (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([17701](https://github.com/spyder-ide/spyder/issues/17701))
* [PR 18437](https://github.com/spyder-ide/spyder/pull/18437) - PR: Catch error when it's not possible to bind a port to `open_files_server` (Main Window), by [@ccordoba12](https://github.com/ccordoba12) ([18262](https://github.com/spyder-ide/spyder/issues/18262))
* [PR 18414](https://github.com/spyder-ide/spyder/pull/18414) - PR: Hide completion widget when keypress has modifiers (Editor), by [@dalthviz](https://github.com/dalthviz) ([14806](https://github.com/spyder-ide/spyder/issues/14806))
* [PR 18413](https://github.com/spyder-ide/spyder/pull/18413) - PR: Use Numpy 1.22 because 1.23 is not giving completions, by [@ccordoba12](https://github.com/ccordoba12) ([18407](https://github.com/spyder-ide/spyder/issues/18407))
* [PR 18387](https://github.com/spyder-ide/spyder/pull/18387) - PR: Fix issue where micromamba activation script was not properly executed., by [@mrclary](https://github.com/mrclary) ([18003](https://github.com/spyder-ide/spyder/issues/18003))
* [PR 18377](https://github.com/spyder-ide/spyder/pull/18377) - PR: Don't connect Qt signals to the `emit` method of others to avoid segfaults, by [@impact27](https://github.com/impact27)
* [PR 18332](https://github.com/spyder-ide/spyder/pull/18332) - PR: Ensure setting up last dockwidgets size distributions (Layout and Registry), by [@dalthviz](https://github.com/dalthviz) ([17945](https://github.com/spyder-ide/spyder/issues/17945), [15074](https://github.com/spyder-ide/spyder/issues/15074))
* [PR 18323](https://github.com/spyder-ide/spyder/pull/18323) - PR: Prevent showing monitor scale change message if auto high DPI is selected and some other fixes, by [@dalthviz](https://github.com/dalthviz) ([14883](https://github.com/spyder-ide/spyder/issues/14883))
* [PR 18310](https://github.com/spyder-ide/spyder/pull/18310) - PR: Make validation of blocks with Outline explorer data faster, by [@impact27](https://github.com/impact27)
* [PR 18306](https://github.com/spyder-ide/spyder/pull/18306) - PR: Improve the test suite reliability on CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18304](https://github.com/spyder-ide/spyder/pull/18304) - PR: Fix syntax issues in macOS installer workflow file, by [@mrclary](https://github.com/mrclary)
* [PR 18303](https://github.com/spyder-ide/spyder/pull/18303) - PR: Fix error when enabling `Underline errors and warnings` in Preferences (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([18290](https://github.com/spyder-ide/spyder/issues/18290))
* [PR 18297](https://github.com/spyder-ide/spyder/pull/18297) - PR: Cache validation of local Kite installation on Mac, by [@impact27](https://github.com/impact27)
* [PR 18278](https://github.com/spyder-ide/spyder/pull/18278) - PR: Fix issue where nbconvert was not importable in macOS application, by [@mrclary](https://github.com/mrclary)
* [PR 18275](https://github.com/spyder-ide/spyder/pull/18275) - PR: Add flag to prevent downloading assets for the Windows installer script, by [@dalthviz](https://github.com/dalthviz)
* [PR 18233](https://github.com/spyder-ide/spyder/pull/18233) - PR: Update instructions to build the Windows installer, by [@jsbautista](https://github.com/jsbautista)
* [PR 18194](https://github.com/spyder-ide/spyder/pull/18194) - PR: Update Spyder tutorial (Help), by [@dalthviz](https://github.com/dalthviz) ([13812](https://github.com/spyder-ide/spyder/issues/13812), [13043](https://github.com/spyder-ide/spyder/issues/13043))
* [PR 18180](https://github.com/spyder-ide/spyder/pull/18180) - PR: Add `Show help for current object` option to Editor context menu, by [@jsbautista](https://github.com/jsbautista) ([978](https://github.com/spyder-ide/spyder/issues/978))
* [PR 18172](https://github.com/spyder-ide/spyder/pull/18172) - PR: Change all strings displayed to the user from `Python script` to `Python file`, by [@jsbautista](https://github.com/jsbautista) ([29](https://github.com/spyder-ide/ux-improvements/issues/29))
* [PR 18121](https://github.com/spyder-ide/spyder/pull/18121) - PR: Really add `defusedxml` and `openpyxl` to the Mac app build, by [@mrclary](https://github.com/mrclary)
* [PR 18120](https://github.com/spyder-ide/spyder/pull/18120) - PR: Only build Full macOS app on pull requests, by [@mrclary](https://github.com/mrclary)
* [PR 18108](https://github.com/spyder-ide/spyder/pull/18108) - PR: `test_sympy_client` xpasses with sympy version 1.10.1, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 18107](https://github.com/spyder-ide/spyder/pull/18107) - PR: Add openpyxl and defusedxml packages to full macOS app version, by [@mrclary](https://github.com/mrclary)
* [PR 18106](https://github.com/spyder-ide/spyder/pull/18106) - PR: Fix tests due to Pylint 2.14.0 and some test stalling the CI or falling due to leak validations, by [@dalthviz](https://github.com/dalthviz) ([18175](https://github.com/spyder-ide/spyder/issues/18175))
* [PR 18105](https://github.com/spyder-ide/spyder/pull/18105) - PR: Add `openpyxl` and `defusedxml` to the full version Windows installers, by [@dalthviz](https://github.com/dalthviz)
* [PR 18074](https://github.com/spyder-ide/spyder/pull/18074) - PR: Add installer and environment info to issue reporter, by [@mrclary](https://github.com/mrclary)
* [PR 18031](https://github.com/spyder-ide/spyder/pull/18031) - PR: Remove PYTHONHOME from QProcess.processEnvironment in profiler, by [@mrclary](https://github.com/mrclary) ([18010](https://github.com/spyder-ide/spyder/issues/18010))
* [PR 18007](https://github.com/spyder-ide/spyder/pull/18007) - PR: Catch error when computing the background color of a dataframe column (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([18005](https://github.com/spyder-ide/spyder/issues/18005))
* [PR 17997](https://github.com/spyder-ide/spyder/pull/17997) - PR: Don't use cached kernel for a full console restart, by [@dalthviz](https://github.com/dalthviz) ([17915](https://github.com/spyder-ide/spyder/issues/17915))
* [PR 17990](https://github.com/spyder-ide/spyder/pull/17990) - PR: Use `pytest-timeout` and set timeout to 120 secs, by [@dalthviz](https://github.com/dalthviz) ([17815](https://github.com/spyder-ide/spyder/issues/17815))
* [PR 17874](https://github.com/spyder-ide/spyder/pull/17874) - PR: Do not resolve symlink on Python interpreter file selection, by [@mrclary](https://github.com/mrclary) ([17872](https://github.com/spyder-ide/spyder/issues/17872))
* [PR 17813](https://github.com/spyder-ide/spyder/pull/17813) - PR: Improve UI/UX of how repositioning panes work, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17512](https://github.com/spyder-ide/spyder/pull/17512) - PR: Consistently handle PYTHONPATH and add Import feature to PYTHONPATH Manager, by [@mrclary](https://github.com/mrclary) ([17511](https://github.com/spyder-ide/spyder/issues/17511))
* [PR 17408](https://github.com/spyder-ide/spyder/pull/17408) - PR: Modernize bootstrap script, by [@mrclary](https://github.com/mrclary) ([17406](https://github.com/spyder-ide/spyder/issues/17406))
* [PR 16490](https://github.com/spyder-ide/spyder/pull/16490) - PR: Code sign macOS app, by [@mrclary](https://github.com/mrclary) ([16414](https://github.com/spyder-ide/spyder/issues/16414))
* [PR 10617](https://github.com/spyder-ide/spyder/pull/10617) - PR: Don't edit Numpy void objects in the Variable Explorer, by [@impact27](https://github.com/impact27) ([10603](https://github.com/spyder-ide/spyder/issues/10603))

In this release 54 pull requests were closed.


----


## Version 5.3.1 (2022-05-23)

### New features

* Add a toolbar to the Variable Explorer viewer for dictionaries, lists and sets to easily access the
  functionality available through its context menu.
* Add navigation with extra buttons in the editor for mouses that support them.
* Add `--no-web-widgets` command line option to disable plugins/widgets that use Qt Webengine widgets.

### Important fixes

* Fix several important bugs related to the `Autoformat on save` functionality.
* Fix options related to the `Working directory` entry in Preferences.
* Make code completion widget entries accessible to screen readers.

### New API features

* Add `get_command_line_options` to `SpyderPluginV2` so that plugins can access the command line options
  passed to Spyder.
* The current interpreter used by all Spyder plugins can be accessed now through the `executable` option
  of the Main interpreter plugin.

### Issues Closed

* [Issue 17889](https://github.com/spyder-ide/spyder/issues/17889) - ImportError when trying to display QMessageBox about corrupted configuration files ([PR 17912](https://github.com/spyder-ide/spyder/pull/17912) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17861](https://github.com/spyder-ide/spyder/issues/17861) - Python interpreter path overwritten in console w/external interpreter on the MacOS standalone version if the `Spyder.app` name is changed  ([PR 17868](https://github.com/spyder-ide/spyder/pull/17868) by [@mrclary](https://github.com/mrclary))
* [Issue 17836](https://github.com/spyder-ide/spyder/issues/17836) - Autoformat file on save prevents saving files ([PR 17854](https://github.com/spyder-ide/spyder/pull/17854) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17814](https://github.com/spyder-ide/spyder/issues/17814) - Release Spyder 5.3.1 ([PR 17972](https://github.com/spyder-ide/spyder/pull/17972) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17803](https://github.com/spyder-ide/spyder/issues/17803) - Editor "New Window" no longer independent of main window ([PR 17826](https://github.com/spyder-ide/spyder/pull/17826) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17784](https://github.com/spyder-ide/spyder/issues/17784) - Spyder fails to quit if Preferences dialog is open ([PR 17824](https://github.com/spyder-ide/spyder/pull/17824) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17778](https://github.com/spyder-ide/spyder/issues/17778) - TypeError when processing completion signatures ([PR 17833](https://github.com/spyder-ide/spyder/pull/17833) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17776](https://github.com/spyder-ide/spyder/issues/17776) - jupyter_client 7.3.0 error in `__del__` ([PR 17844](https://github.com/spyder-ide/spyder/pull/17844) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17737](https://github.com/spyder-ide/spyder/issues/17737) - The working directory is not properly set when Spyder is launched ([PR 17760](https://github.com/spyder-ide/spyder/pull/17760) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17731](https://github.com/spyder-ide/spyder/issues/17731) - Spyder fails to restart after selecting Restart from the macOS standalone application menu bar ([PR 17740](https://github.com/spyder-ide/spyder/pull/17740) by [@mrclary](https://github.com/mrclary))
* [Issue 17729](https://github.com/spyder-ide/spyder/issues/17729) - Python processes linger after quitting Spyder macOS standalone application ([PR 17732](https://github.com/spyder-ide/spyder/pull/17732) by [@mrclary](https://github.com/mrclary))
* [Issue 17726](https://github.com/spyder-ide/spyder/issues/17726) - Canceling closing Spyder with unsaved changes closes editor and all files ([PR 17735](https://github.com/spyder-ide/spyder/pull/17735) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17725](https://github.com/spyder-ide/spyder/issues/17725) - What are the install arguments for the Windows installer? ([PR 17728](https://github.com/spyder-ide/spyder/pull/17728) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17716](https://github.com/spyder-ide/spyder/issues/17716) - Files not autoformatted on save when other options that work on save are set ([PR 17828](https://github.com/spyder-ide/spyder/pull/17828) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17685](https://github.com/spyder-ide/spyder/issues/17685) - Unavailable shared folder causes Spyder to crash on startup ([PR 17686](https://github.com/spyder-ide/spyder/pull/17686) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17677](https://github.com/spyder-ide/spyder/issues/17677) - TypeError when showing DPI message in Python 3.10 ([PR 17678](https://github.com/spyder-ide/spyder/pull/17678) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17665](https://github.com/spyder-ide/spyder/issues/17665) - IPython console does not work with Micromamba environments ([PR 17692](https://github.com/spyder-ide/spyder/pull/17692) by [@mrclary](https://github.com/mrclary))
* [Issue 17661](https://github.com/spyder-ide/spyder/issues/17661) - Spyder can't start pylsp on pip installations ([PR 17717](https://github.com/spyder-ide/spyder/pull/17717) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17621](https://github.com/spyder-ide/spyder/issues/17621) - Error when trying to open a project and reading config file ([PR 17630](https://github.com/spyder-ide/spyder/pull/17630) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17609](https://github.com/spyder-ide/spyder/issues/17609) - Language server fails to load pylsp_black plugin in macOS app ([PR 17612](https://github.com/spyder-ide/spyder/pull/17612) by [@mrclary](https://github.com/mrclary))
* [Issue 17598](https://github.com/spyder-ide/spyder/issues/17598) - Changelog too large to render on Github ([PR 17605](https://github.com/spyder-ide/spyder/pull/17605) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17595](https://github.com/spyder-ide/spyder/issues/17595) - Can't run files with space in path via external terminal ([PR 17635](https://github.com/spyder-ide/spyder/pull/17635) by [@mrclary](https://github.com/mrclary))
* [Issue 17589](https://github.com/spyder-ide/spyder/issues/17589) - Using `spyder -w` does not open in the correct working directory ([PR 17657](https://github.com/spyder-ide/spyder/pull/17657) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17580](https://github.com/spyder-ide/spyder/issues/17580) - Check CI robustness in merge commits ([PR 17622](https://github.com/spyder-ide/spyder/pull/17622) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17551](https://github.com/spyder-ide/spyder/issues/17551) - setuptools 61.0.0 breaks macOS installer ([PR 17612](https://github.com/spyder-ide/spyder/pull/17612) by [@mrclary](https://github.com/mrclary))
* [Issue 17499](https://github.com/spyder-ide/spyder/issues/17499) - Remove tests that don't apply due to the new debugger ([PR 17622](https://github.com/spyder-ide/spyder/pull/17622) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17498](https://github.com/spyder-ide/spyder/issues/17498) - Check code update due to QTextEdit bug solved on PyQt 5.15 ([PR 17622](https://github.com/spyder-ide/spyder/pull/17622) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17475](https://github.com/spyder-ide/spyder/issues/17475) - Find pane does not set focus in text field ([PR 17658](https://github.com/spyder-ide/spyder/pull/17658) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17047](https://github.com/spyder-ide/spyder/issues/17047) - Accessibility: Autocomplete suggestions are surrounded by HTML markup for screen reader users ([PR 17706](https://github.com/spyder-ide/spyder/pull/17706) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16930](https://github.com/spyder-ide/spyder/issues/16930) - Disabled toolbars get enabled when restarting Spyder ([PR 17768](https://github.com/spyder-ide/spyder/pull/17768) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16297](https://github.com/spyder-ide/spyder/issues/16297) - Plots DPI Scaling setting keeps reversing ([PR 17767](https://github.com/spyder-ide/spyder/pull/17767) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16061](https://github.com/spyder-ide/spyder/issues/16061) - The shortcuts for file switcher and symbol finder are not working ([PR 17849](https://github.com/spyder-ide/spyder/pull/17849) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15948](https://github.com/spyder-ide/spyder/issues/15948) - [Enhancement] Support XButton1 and XButton2 ([PR 17786](https://github.com/spyder-ide/spyder/pull/17786) by [@maurerle](https://github.com/maurerle))
* [Issue 15460](https://github.com/spyder-ide/spyder/issues/15460) - File associations applications are added more than one time in context  menu ([PR 17687](https://github.com/spyder-ide/spyder/pull/17687) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14646](https://github.com/spyder-ide/spyder/issues/14646) - Outline duplicates files when Editor is split ([PR 17700](https://github.com/spyder-ide/spyder/pull/17700) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14639](https://github.com/spyder-ide/spyder/issues/14639) - IndexError when saving file and auto-formatting is on ([PR 17757](https://github.com/spyder-ide/spyder/pull/17757) by [@dalthviz](https://github.com/dalthviz))
* [Issue 1884](https://github.com/spyder-ide/spyder/issues/1884) - Profiler plugin does not use non-default python interpreter ([PR 17788](https://github.com/spyder-ide/spyder/pull/17788) by [@maurerle](https://github.com/maurerle))

In this release 37 issues were closed.

### Pull Requests Merged

* [PR 17972](https://github.com/spyder-ide/spyder/pull/17972) - PR: Update core dependencies for 5.3.1, by [@ccordoba12](https://github.com/ccordoba12) ([17814](https://github.com/spyder-ide/spyder/issues/17814))
* [PR 17934](https://github.com/spyder-ide/spyder/pull/17934) - PR: Improve updating Main Interpreter status bar widget when the current one is removed, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17912](https://github.com/spyder-ide/spyder/pull/17912) - PR: Don't use create_application when showing message about not being able to load CONF, by [@ccordoba12](https://github.com/ccordoba12) ([17889](https://github.com/spyder-ide/spyder/issues/17889))
* [PR 17868](https://github.com/spyder-ide/spyder/pull/17868) - PR: Remove dependence on fixed macOS application bundle name, by [@mrclary](https://github.com/mrclary) ([17861](https://github.com/spyder-ide/spyder/issues/17861))
* [PR 17860](https://github.com/spyder-ide/spyder/pull/17860) - PR: Add missing `PyQtWebEngine` dependency for conda-forge based CI and fix tests, by [@dalthviz](https://github.com/dalthviz)
* [PR 17856](https://github.com/spyder-ide/spyder/pull/17856) - PR: Add micromamba executable to the Windows installer, by [@dalthviz](https://github.com/dalthviz)
* [PR 17854](https://github.com/spyder-ide/spyder/pull/17854) - PR: Wait for autoformat before returning on 'save' method (Editor), by [@dalthviz](https://github.com/dalthviz) ([17836](https://github.com/spyder-ide/spyder/issues/17836))
* [PR 17850](https://github.com/spyder-ide/spyder/pull/17850) - PR: Fix an option name used in config page (Working directory), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17849](https://github.com/spyder-ide/spyder/pull/17849) - PR: Pre-render menus in all operating systems (Main menu), by [@ccordoba12](https://github.com/ccordoba12) ([16061](https://github.com/spyder-ide/spyder/issues/16061))
* [PR 17847](https://github.com/spyder-ide/spyder/pull/17847) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 17846](https://github.com/spyder-ide/spyder/pull/17846) - PR: Update translations for 5.3.1 with config page fix, by [@dalthviz](https://github.com/dalthviz)
* [PR 17844](https://github.com/spyder-ide/spyder/pull/17844) - PR: Increase minimal required version of jupyter_client in spyder-kernels , by [@ccordoba12](https://github.com/ccordoba12) ([17776](https://github.com/spyder-ide/spyder/issues/17776))
* [PR 17838](https://github.com/spyder-ide/spyder/pull/17838) - PR: Update translations for 5.3.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 17833](https://github.com/spyder-ide/spyder/pull/17833) - PR: Check that signature response is not empty before processing it (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([17778](https://github.com/spyder-ide/spyder/issues/17778))
* [PR 17832](https://github.com/spyder-ide/spyder/pull/17832) - PR: Fix “Source → Show warning/error list” action (Pyside2), by [@rear1019](https://github.com/rear1019)
* [PR 17828](https://github.com/spyder-ide/spyder/pull/17828) - PR: Fix collision between `format_on_save` and other Editor formatting options, by [@dalthviz](https://github.com/dalthviz) ([17716](https://github.com/spyder-ide/spyder/issues/17716))
* [PR 17826](https://github.com/spyder-ide/spyder/pull/17826) - PR: Fix Editor new window to be indenpendent of the main window, by [@dalthviz](https://github.com/dalthviz) ([17803](https://github.com/spyder-ide/spyder/issues/17803))
* [PR 17824](https://github.com/spyder-ide/spyder/pull/17824) - PR: Close Preferences when closing Spyder, by [@ccordoba12](https://github.com/ccordoba12) ([17784](https://github.com/spyder-ide/spyder/issues/17784))
* [PR 17820](https://github.com/spyder-ide/spyder/pull/17820) - PR: Don’t emit `sig_shellwidget_created` before shell widget is initialized, by [@rear1019](https://github.com/rear1019)
* [PR 17817](https://github.com/spyder-ide/spyder/pull/17817) - PR: Fix saving of external plugin config in on_close(), by [@rear1019](https://github.com/rear1019)
* [PR 17811](https://github.com/spyder-ide/spyder/pull/17811) - PR: Improve style and UX of new toolbar in collections viewer (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17788](https://github.com/spyder-ide/spyder/pull/17788) - PR: Unify access to current active interpreter, by [@maurerle](https://github.com/maurerle) ([1884](https://github.com/spyder-ide/spyder/issues/1884))
* [PR 17786](https://github.com/spyder-ide/spyder/pull/17786) - PR: Implement mouse XButton navigation in the editor, by [@maurerle](https://github.com/maurerle) ([15948](https://github.com/spyder-ide/spyder/issues/15948))
* [PR 17774](https://github.com/spyder-ide/spyder/pull/17774) - PR: Improve compatibility with PySide2, by [@rear1019](https://github.com/rear1019)
* [PR 17768](https://github.com/spyder-ide/spyder/pull/17768) - PR: Fix state handling for toolbars visibility (Toolbar), by [@dalthviz](https://github.com/dalthviz) ([16930](https://github.com/spyder-ide/spyder/issues/16930))
* [PR 17767](https://github.com/spyder-ide/spyder/pull/17767) - PR: Subscribe to configs for Matplotlib inline backend (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([16297](https://github.com/spyder-ide/spyder/issues/16297))
* [PR 17760](https://github.com/spyder-ide/spyder/pull/17760) - PR: Fix setting working directory at startup and for new IPython consoles, by [@ccordoba12](https://github.com/ccordoba12) ([17737](https://github.com/spyder-ide/spyder/issues/17737))
* [PR 17757](https://github.com/spyder-ide/spyder/pull/17757) - PR: Calculate index when autoformating on save from the Editor, by [@dalthviz](https://github.com/dalthviz) ([14639](https://github.com/spyder-ide/spyder/issues/14639))
* [PR 17743](https://github.com/spyder-ide/spyder/pull/17743) - PR: Remove possibility of passing separate configuration object for testing, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17740](https://github.com/spyder-ide/spyder/pull/17740) - PR: Change restart script for macOS app, by [@mrclary](https://github.com/mrclary) ([17731](https://github.com/spyder-ide/spyder/issues/17731))
* [PR 17735](https://github.com/spyder-ide/spyder/pull/17735) - PR: Move deleteLater calls to be done after validating plugin can be closed, by [@dalthviz](https://github.com/dalthviz) ([17726](https://github.com/spyder-ide/spyder/issues/17726))
* [PR 17732](https://github.com/spyder-ide/spyder/pull/17732) - PR: Remove macOS app flow fork in closing Spyder, by [@mrclary](https://github.com/mrclary) ([17729](https://github.com/spyder-ide/spyder/issues/17729))
* [PR 17728](https://github.com/spyder-ide/spyder/pull/17728) - PR: Add some info regarding command line arguments for the Windows installer, by [@dalthviz](https://github.com/dalthviz) ([17725](https://github.com/spyder-ide/spyder/issues/17725))
* [PR 17717](https://github.com/spyder-ide/spyder/pull/17717) - PR: Pass `APPDATA` env var to the process that starts the PyLSP server (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([17661](https://github.com/spyder-ide/spyder/issues/17661))
* [PR 17706](https://github.com/spyder-ide/spyder/pull/17706) - PR: Add `Qt.AccessibleTextRole` data to completion widget items, by [@dalthviz](https://github.com/dalthviz) ([17047](https://github.com/spyder-ide/spyder/issues/17047))
* [PR 17700](https://github.com/spyder-ide/spyder/pull/17700) - PR: Remove duplicates when sorting in the outline explorer, by [@dalthviz](https://github.com/dalthviz) ([14646](https://github.com/spyder-ide/spyder/issues/14646))
* [PR 17692](https://github.com/spyder-ide/spyder/pull/17692) - PR: Allow micromamba activation of external environments, by [@mrclary](https://github.com/mrclary) ([17665](https://github.com/spyder-ide/spyder/issues/17665))
* [PR 17687](https://github.com/spyder-ide/spyder/pull/17687) - PR: Fix clear for `Open with` menu in the Files pane, by [@dalthviz](https://github.com/dalthviz) ([15460](https://github.com/spyder-ide/spyder/issues/15460))
* [PR 17686](https://github.com/spyder-ide/spyder/pull/17686) - PR: Catch OSError when trying to open a not available file (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([17685](https://github.com/spyder-ide/spyder/issues/17685))
* [PR 17678](https://github.com/spyder-ide/spyder/pull/17678) - PR: Convert coordinates to position DPI message to int (Application), by [@ccordoba12](https://github.com/ccordoba12) ([17677](https://github.com/spyder-ide/spyder/issues/17677))
* [PR 17658](https://github.com/spyder-ide/spyder/pull/17658) - PR: Give focus to Find search text widget when switching to it, by [@ccordoba12](https://github.com/ccordoba12) ([17475](https://github.com/spyder-ide/spyder/issues/17475))
* [PR 17657](https://github.com/spyder-ide/spyder/pull/17657) - PR: Improve the way command line options are handled by plugins, by [@ccordoba12](https://github.com/ccordoba12) ([17589](https://github.com/spyder-ide/spyder/issues/17589))
* [PR 17646](https://github.com/spyder-ide/spyder/pull/17646) - PR: Ensure `QFont.setPointSize` receives an int argument (Shortcuts), by [@juliangilbey](https://github.com/juliangilbey)
* [PR 17641](https://github.com/spyder-ide/spyder/pull/17641) - PR: Skip Changelog files from manifest, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17635](https://github.com/spyder-ide/spyder/pull/17635) - PR: Revise run_python_script_in_terminal, by [@mrclary](https://github.com/mrclary) ([17595](https://github.com/spyder-ide/spyder/issues/17595))
* [PR 17630](https://github.com/spyder-ide/spyder/pull/17630) - PR: Catch any error when reading workspace config file (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([17621](https://github.com/spyder-ide/spyder/issues/17621))
* [PR 17622](https://github.com/spyder-ide/spyder/pull/17622) - PR: Check tests robustness, number of concurrent jobs and try to decrease segfault failures on CI, by [@dalthviz](https://github.com/dalthviz) ([17580](https://github.com/spyder-ide/spyder/issues/17580), [17499](https://github.com/spyder-ide/spyder/issues/17499), [17498](https://github.com/spyder-ide/spyder/issues/17498))
* [PR 17612](https://github.com/spyder-ide/spyder/pull/17612) - PR: Update py2app to 0.28 (Mac app), by [@mrclary](https://github.com/mrclary) ([17609](https://github.com/spyder-ide/spyder/issues/17609), [17551](https://github.com/spyder-ide/spyder/issues/17551))
* [PR 17607](https://github.com/spyder-ide/spyder/pull/17607) - PR: Remove the cls parameter from generated docstring (Editor), by [@trollodel](https://github.com/trollodel)
* [PR 17605](https://github.com/spyder-ide/spyder/pull/17605) - PR: Break Changelog in multiple files per major version, by [@ccordoba12](https://github.com/ccordoba12) ([17598](https://github.com/spyder-ide/spyder/issues/17598))
* [PR 17473](https://github.com/spyder-ide/spyder/pull/17473) - PR: Add context menu entries for collections to a toolbar (Variable Explorer), by [@dpturibio](https://github.com/dpturibio) ([67](https://github.com/spyder-ide/ux-improvements/issues/67))
* [PR 16518](https://github.com/spyder-ide/spyder/pull/16518) - PR: Allow users to disable web widgets with a command line option, by [@dmageeLANL](https://github.com/dmageeLANL)

In this release 52 pull requests were closed.


----


## Version 5.3.0 (2022-03-30)

### New features

* New `Run to current line` and `Run from current line` actions in the Editor
* New option to reset per-file run configurations
* Now the spyder-terminal plugin comes bundled with the standalone installers (MacOS and Windows)
* Now the standalone Windows installers come with Python 3.8.10
* Drop support for Python 3.6
* Update PyQt requirement to 5.15

### Important fixes

* Fix the restart logic in the IPython Console to set Matplotlib interactive backends
* Fix some issues related to Black formatting configuration and usage
* Improve Editor performance by decreasing the amount of requests (didChange request) made to the pylsp server
* Disable Kite provider for completions
* Require IPython => 7.31.1 due to CVE-2022-21699
* Several fixes for type errors with Python 3.10

### New API features

* New `on_close` method for the `PluginMainWidget` class that its called on `closeEvent`

### Issues Closed

* [Issue 17563](https://github.com/spyder-ide/spyder/issues/17563) - New dependencies for Spyder 5.3.0 ([PR 17578](https://github.com/spyder-ide/spyder/pull/17578) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17552](https://github.com/spyder-ide/spyder/issues/17552) - IPython kernel error with debugpy 1.6.0 ([PR 17553](https://github.com/spyder-ide/spyder/pull/17553) by [@mrclary](https://github.com/mrclary))
* [Issue 17546](https://github.com/spyder-ide/spyder/issues/17546) - pkg_resources does not find entry points in macOS app ([PR 17547](https://github.com/spyder-ide/spyder/pull/17547) by [@mrclary](https://github.com/mrclary))
* [Issue 17521](https://github.com/spyder-ide/spyder/issues/17521) - IndexError when copy/paste from file explorer ([PR 17524](https://github.com/spyder-ide/spyder/pull/17524) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17500](https://github.com/spyder-ide/spyder/issues/17500) - On closing a message from the spyder-terminal appears on the Windows installer ([PR 17533](https://github.com/spyder-ide/spyder/pull/17533) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17486](https://github.com/spyder-ide/spyder/issues/17486) - Error when undocking code window, after opening then closing a new window ([PR 17489](https://github.com/spyder-ide/spyder/pull/17489) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17472](https://github.com/spyder-ide/spyder/issues/17472) - Walrus operator incorrectly shows error on Windows app ([PR 17293](https://github.com/spyder-ide/spyder/pull/17293) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17361](https://github.com/spyder-ide/spyder/issues/17361) - TypeError when opening a pandas DataFrame in variable explorer ([PR 17367](https://github.com/spyder-ide/spyder/pull/17367) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17360](https://github.com/spyder-ide/spyder/issues/17360) - Turning off Project plugin stops LSP server from starting ([PR 17370](https://github.com/spyder-ide/spyder/pull/17370) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17319](https://github.com/spyder-ide/spyder/issues/17319) - The linenumber is not displayed properly ([PR 17321](https://github.com/spyder-ide/spyder/pull/17321) by [@impact27](https://github.com/impact27))
* [Issue 17289](https://github.com/spyder-ide/spyder/issues/17289) - Spyder on Windows 10, remote kernel on RPi Zero, Python script not found ([PR 17404](https://github.com/spyder-ide/spyder/pull/17404) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17262](https://github.com/spyder-ide/spyder/issues/17262) - TypeError when disabling completion providers ([PR 17490](https://github.com/spyder-ide/spyder/pull/17490) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17253](https://github.com/spyder-ide/spyder/issues/17253) - Variable explorer does not work with pandas 1.4 and Spyder Windows installer ([PR 17293](https://github.com/spyder-ide/spyder/pull/17293) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17252](https://github.com/spyder-ide/spyder/issues/17252) - Can't restart kernel due to content in stderr file ([PR 17274](https://github.com/spyder-ide/spyder/pull/17274) by [@impact27](https://github.com/impact27))
* [Issue 17232](https://github.com/spyder-ide/spyder/issues/17232) - Require IPython >= 7.31.1 due to CVE-2022-21699 ? ([PR 17399](https://github.com/spyder-ide/spyder/pull/17399) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17221](https://github.com/spyder-ide/spyder/issues/17221) - File name not updating when closing last open file ([PR 17273](https://github.com/spyder-ide/spyder/pull/17273) by [@Ajax-Light](https://github.com/Ajax-Light))
* [Issue 17217](https://github.com/spyder-ide/spyder/issues/17217) - Files or directories including ".git" in their path are ignored in project pane ([PR 17491](https://github.com/spyder-ide/spyder/pull/17491) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17213](https://github.com/spyder-ide/spyder/issues/17213) - Crash on bad IPython config ([PR 17205](https://github.com/spyder-ide/spyder/pull/17205) by [@impact27](https://github.com/impact27))
* [Issue 17202](https://github.com/spyder-ide/spyder/issues/17202) - Add spyder-terminal plugin to macOS and Windows installers ([PR 17212](https://github.com/spyder-ide/spyder/pull/17212) by [@mrclary](https://github.com/mrclary))
* [Issue 17197](https://github.com/spyder-ide/spyder/issues/17197) - No wheels available for Python 3.10 and PyQt 5.12 ([PR 16409](https://github.com/spyder-ide/spyder/pull/16409) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17172](https://github.com/spyder-ide/spyder/issues/17172) - Matplotlib no longer supports qt4 nor gtk backends ([PR 17419](https://github.com/spyder-ide/spyder/pull/17419) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17153](https://github.com/spyder-ide/spyder/issues/17153) - TypeError when flushing pending streams
* [Issue 17143](https://github.com/spyder-ide/spyder/issues/17143) - Black in Spyder 5 does not behave as standard Black ([PR 17555](https://github.com/spyder-ide/spyder/pull/17555) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17139](https://github.com/spyder-ide/spyder/issues/17139) - PySide2 error when viewing dataframes in Python 3.10 ([PR 17329](https://github.com/spyder-ide/spyder/pull/17329) by [@fumitoh](https://github.com/fumitoh))
* [Issue 17130](https://github.com/spyder-ide/spyder/issues/17130) - TypeError when writing "np.sin(" in console ([PR 17256](https://github.com/spyder-ide/spyder/pull/17256) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17108](https://github.com/spyder-ide/spyder/issues/17108) - How to remove Kite from Spyder completely ([PR 17465](https://github.com/spyder-ide/spyder/pull/17465) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17085](https://github.com/spyder-ide/spyder/issues/17085) - Lots of "XIO:  fatal IO error 0 (Success)" errors when running tests under Xvfb ([PR 16409](https://github.com/spyder-ide/spyder/pull/16409) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17083](https://github.com/spyder-ide/spyder/issues/17083) - test_profiler_config_dialog.py inconsistently throws a fatal error: segfault ([PR 16409](https://github.com/spyder-ide/spyder/pull/16409) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17060](https://github.com/spyder-ide/spyder/issues/17060) - test_qtbug35861 fails with Qt 5.15.2 ([PR 16409](https://github.com/spyder-ide/spyder/pull/16409) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16971](https://github.com/spyder-ide/spyder/issues/16971) - Drop support for Python 3.6 ([PR 17331](https://github.com/spyder-ide/spyder/pull/17331) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16844](https://github.com/spyder-ide/spyder/issues/16844) - Running the size of a dask dataframe file ([PR 17463](https://github.com/spyder-ide/spyder/pull/17463) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16747](https://github.com/spyder-ide/spyder/issues/16747) - Error when loading configuration file ([PR 17526](https://github.com/spyder-ide/spyder/pull/17526) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16595](https://github.com/spyder-ide/spyder/issues/16595) - Installing Kite takes forever ([PR 17465](https://github.com/spyder-ide/spyder/pull/17465) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16504](https://github.com/spyder-ide/spyder/issues/16504) - The input function inserts a new line ([PR 17559](https://github.com/spyder-ide/spyder/pull/17559) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16431](https://github.com/spyder-ide/spyder/issues/16431) - Feature request: "Run to line" and "Run from line" ([PR 16509](https://github.com/spyder-ide/spyder/pull/16509) by [@rhkarls](https://github.com/rhkarls))
* [Issue 16417](https://github.com/spyder-ide/spyder/issues/16417) - %debug magic does not work repeatably for untitled files ([PR 17191](https://github.com/spyder-ide/spyder/pull/17191) by [@impact27](https://github.com/impact27))
* [Issue 16402](https://github.com/spyder-ide/spyder/issues/16402) - Deactivate by default `Exclude all upper-case variables` option in Variable Explorer ([PR 17565](https://github.com/spyder-ide/spyder/pull/17565) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16207](https://github.com/spyder-ide/spyder/issues/16207) - Add option to reset per-file run configurations ([PR 16209](https://github.com/spyder-ide/spyder/pull/16209) by [@mrclary](https://github.com/mrclary))
* [Issue 14895](https://github.com/spyder-ide/spyder/issues/14895) - Latex rendering with dark theme is broken ([PR 16957](https://github.com/spyder-ide/spyder/pull/16957) by [@bnavigator](https://github.com/bnavigator))
* [Issue 14843](https://github.com/spyder-ide/spyder/issues/14843) - Ability to use PYTHONPATH from user bash_profile in macOS application ([PR 17502](https://github.com/spyder-ide/spyder/pull/17502) by [@mrclary](https://github.com/mrclary))
* [Issue 14809](https://github.com/spyder-ide/spyder/issues/14809) - PYTHONPATH Manager opens multiple windows ([PR 17503](https://github.com/spyder-ide/spyder/pull/17503) by [@mrclary](https://github.com/mrclary))
* [Issue 14575](https://github.com/spyder-ide/spyder/issues/14575) - Can't use pythonw as interpreter when needed on Mac  ([PR 17516](https://github.com/spyder-ide/spyder/pull/17516) by [@mrclary](https://github.com/mrclary))
* [Issue 14558](https://github.com/spyder-ide/spyder/issues/14558) - Black maximum allowed line length is not working. ([PR 17567](https://github.com/spyder-ide/spyder/pull/17567) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12829](https://github.com/spyder-ide/spyder/issues/12829) - Make Spyder work with PyQt 5.15 ([PR 16409](https://github.com/spyder-ide/spyder/pull/16409) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 3394](https://github.com/spyder-ide/spyder/issues/3394) - %edit magic can't create a new file ([PR 17181](https://github.com/spyder-ide/spyder/pull/17181) by [@impact27](https://github.com/impact27))

In this release 45 issues were closed.

### Pull Requests Merged

* [PR 17579](https://github.com/spyder-ide/spyder/pull/17579) - PR: Fix layout issue when closing with unsaved files, by [@dalthviz](https://github.com/dalthviz)
* [PR 17578](https://github.com/spyder-ide/spyder/pull/17578) - PR: Update core dependencies for 5.3.0, by [@dalthviz](https://github.com/dalthviz) ([17563](https://github.com/spyder-ide/spyder/issues/17563))
* [PR 17573](https://github.com/spyder-ide/spyder/pull/17573) - PR: Fix usage of `os._exit` to save Editor and Projects plugins state, by [@dalthviz](https://github.com/dalthviz)
* [PR 17567](https://github.com/spyder-ide/spyder/pull/17567) - PR: Fix setting max line length for Black (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([14558](https://github.com/spyder-ide/spyder/issues/14558))
* [PR 17565](https://github.com/spyder-ide/spyder/pull/17565) - PR: Disable option that excludes uppercase variables (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([16402](https://github.com/spyder-ide/spyder/issues/16402))
* [PR 17559](https://github.com/spyder-ide/spyder/pull/17559) - PR: Remove extra blank lines when running statements with `input()` (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([16504](https://github.com/spyder-ide/spyder/issues/16504))
* [PR 17558](https://github.com/spyder-ide/spyder/pull/17558) - PR: Loose requirement on QDarkstyle, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17555](https://github.com/spyder-ide/spyder/pull/17555) - PR: Preserve EOL characters when formatting text (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([17143](https://github.com/spyder-ide/spyder/issues/17143))
* [PR 17554](https://github.com/spyder-ide/spyder/pull/17554) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 17553](https://github.com/spyder-ide/spyder/pull/17553) - PR: Pass new environment variable to the kernel and remove some benign errors thanks to debugpy 1.6.0 (IPython console), by [@mrclary](https://github.com/mrclary) ([17552](https://github.com/spyder-ide/spyder/issues/17552))
* [PR 17547](https://github.com/spyder-ide/spyder/pull/17547) - PR: Fix zip archive in macOS app bundle so that pkg_resources will find entry points, by [@mrclary](https://github.com/mrclary) ([17546](https://github.com/spyder-ide/spyder/issues/17546))
* [PR 17533](https://github.com/spyder-ide/spyder/pull/17533) - PR: Change validation to force clean application close, by [@dalthviz](https://github.com/dalthviz) ([17500](https://github.com/spyder-ide/spyder/issues/17500))
* [PR 17528](https://github.com/spyder-ide/spyder/pull/17528) - PR: Make entries of `Convert end-of-line characters` menu match the ones in Preferences, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17526](https://github.com/spyder-ide/spyder/pull/17526) - PR: Prompt user to reset Spyder config files in case `CONF` instance initialization fails, by [@dalthviz](https://github.com/dalthviz) ([16747](https://github.com/spyder-ide/spyder/issues/16747))
* [PR 17524](https://github.com/spyder-ide/spyder/pull/17524) - PR: Avoid error when getting urls content from clipboard's mime data (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([17521](https://github.com/spyder-ide/spyder/issues/17521))
* [PR 17522](https://github.com/spyder-ide/spyder/pull/17522) - PR: Update translations for 5.3.0, by [@dalthviz](https://github.com/dalthviz)
* [PR 17516](https://github.com/spyder-ide/spyder/pull/17516) - PR: Fix issue where pythonw could not be used in macOS application, by [@mrclary](https://github.com/mrclary) ([14575](https://github.com/spyder-ide/spyder/issues/14575))
* [PR 17510](https://github.com/spyder-ide/spyder/pull/17510) - PR: Make context run cell icons match run menu icons, by [@rhkarls](https://github.com/rhkarls)
* [PR 17503](https://github.com/spyder-ide/spyder/pull/17503) - PR: Ensure only one instance of PYTHONPATH Manager, by [@mrclary](https://github.com/mrclary) ([14809](https://github.com/spyder-ide/spyder/issues/14809))
* [PR 17502](https://github.com/spyder-ide/spyder/pull/17502) - PR: Update macOS app to import user environment variables, by [@mrclary](https://github.com/mrclary) ([14843](https://github.com/spyder-ide/spyder/issues/14843))
* [PR 17491](https://github.com/spyder-ide/spyder/pull/17491) - PR: Use only paths last element for filtering in the project explorer, by [@dalthviz](https://github.com/dalthviz) ([17217](https://github.com/spyder-ide/spyder/issues/17217))
* [PR 17490](https://github.com/spyder-ide/spyder/pull/17490) - PR: Fix validations to add/remove completion status widgets, by [@dalthviz](https://github.com/dalthviz) ([17262](https://github.com/spyder-ide/spyder/issues/17262))
* [PR 17489](https://github.com/spyder-ide/spyder/pull/17489) - PR: Catch error when undocking/docking the editor, by [@ccordoba12](https://github.com/ccordoba12) ([17486](https://github.com/spyder-ide/spyder/issues/17486))
* [PR 17488](https://github.com/spyder-ide/spyder/pull/17488) - PR: Fix restart for interactive backends, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17485](https://github.com/spyder-ide/spyder/pull/17485) - PR: Avoid external plugins to be disabled, by [@steff456](https://github.com/steff456)
* [PR 17465](https://github.com/spyder-ide/spyder/pull/17465) - PR: Completely disable Kite provider (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([17108](https://github.com/spyder-ide/spyder/issues/17108), [16595](https://github.com/spyder-ide/spyder/issues/16595))
* [PR 17463](https://github.com/spyder-ide/spyder/pull/17463) - PR: Fix error when getting size of dask dataframe objects (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([16844](https://github.com/spyder-ide/spyder/issues/16844))
* [PR 17419](https://github.com/spyder-ide/spyder/pull/17419) - PR: Remove support for outdated and unused Matplotlib backends (IPython Console), by [@ccordoba12](https://github.com/ccordoba12) ([17172](https://github.com/spyder-ide/spyder/issues/17172))
* [PR 17404](https://github.com/spyder-ide/spyder/pull/17404) - PR: Prevent error when the kernel tries to get file code from the frontend, by [@ccordoba12](https://github.com/ccordoba12) ([17289](https://github.com/spyder-ide/spyder/issues/17289))
* [PR 17403](https://github.com/spyder-ide/spyder/pull/17403) - PR: Fix for arguments to be converted to string format, by [@dan123456-eng](https://github.com/dan123456-eng)
* [PR 17402](https://github.com/spyder-ide/spyder/pull/17402) - PR: Fix check for PyQt/PySide requirement, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17399](https://github.com/spyder-ide/spyder/pull/17399) - PR: Increase minimal required IPython version to 7.31.1, by [@ccordoba12](https://github.com/ccordoba12) ([17232](https://github.com/spyder-ide/spyder/issues/17232))
* [PR 17396](https://github.com/spyder-ide/spyder/pull/17396) - PR: Don't try to sync symbols and folding after a file is closed (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17370](https://github.com/spyder-ide/spyder/pull/17370) - PR: Load previous session if Projects is disabled, by [@ccordoba12](https://github.com/ccordoba12) ([17360](https://github.com/spyder-ide/spyder/issues/17360))
* [PR 17367](https://github.com/spyder-ide/spyder/pull/17367) - PR: Fix bug when viewing Dataframes in Python 3.10 (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([17361](https://github.com/spyder-ide/spyder/issues/17361))
* [PR 17347](https://github.com/spyder-ide/spyder/pull/17347) - PR: Stop copying black dist-info when building Windows installers and update constraints for numpy and black, by [@dalthviz](https://github.com/dalthviz)
* [PR 17331](https://github.com/spyder-ide/spyder/pull/17331) - PR: Increase required versions for Python and PyQt/Pyside, by [@ccordoba12](https://github.com/ccordoba12) ([16971](https://github.com/spyder-ide/spyder/issues/16971))
* [PR 17329](https://github.com/spyder-ide/spyder/pull/17329) - PR: Fix DataFrameView error with PySide2, by [@fumitoh](https://github.com/fumitoh) ([17139](https://github.com/spyder-ide/spyder/issues/17139))
* [PR 17321](https://github.com/spyder-ide/spyder/pull/17321) - PR: Fix painting of line numbers for some fonts (Editor), by [@impact27](https://github.com/impact27) ([17319](https://github.com/spyder-ide/spyder/issues/17319))
* [PR 17293](https://github.com/spyder-ide/spyder/pull/17293) - PR: Bump Windows installer Python version to 3.8.10, by [@dalthviz](https://github.com/dalthviz) ([17472](https://github.com/spyder-ide/spyder/issues/17472), [17253](https://github.com/spyder-ide/spyder/issues/17253))
* [PR 17288](https://github.com/spyder-ide/spyder/pull/17288) - PR: Skip more IPython console tests because they started to hang, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17283](https://github.com/spyder-ide/spyder/pull/17283) - PR: Increase Pytest required version to 6+, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17274](https://github.com/spyder-ide/spyder/pull/17274) - PR: Fix restart when something is present in kernel's stderr file (IPython console), by [@impact27](https://github.com/impact27) ([17252](https://github.com/spyder-ide/spyder/issues/17252))
* [PR 17273](https://github.com/spyder-ide/spyder/pull/17273) - PR: Fix label update when creating an untitled file after no other file is open, by [@Ajax-Light](https://github.com/Ajax-Light) ([17221](https://github.com/spyder-ide/spyder/issues/17221))
* [PR 17265](https://github.com/spyder-ide/spyder/pull/17265) - PR: Skip a test on Mac because it started to hang, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17256](https://github.com/spyder-ide/spyder/pull/17256) - PR: Fix more type errors in Python 3.10 and also tests, by [@ccordoba12](https://github.com/ccordoba12) ([17130](https://github.com/spyder-ide/spyder/issues/17130))
* [PR 17247](https://github.com/spyder-ide/spyder/pull/17247) - PR: Add spyder-terminal to the Windows installers, by [@dalthviz](https://github.com/dalthviz) ([17202](https://github.com/spyder-ide/spyder/issues/17202))
* [PR 17240](https://github.com/spyder-ide/spyder/pull/17240) - PR: Update RELEASE.md info regarding spyder-kernels version updates, by [@dalthviz](https://github.com/dalthviz)
* [PR 17238](https://github.com/spyder-ide/spyder/pull/17238) - PR: Avoid looping on all thumbnails (Plots), by [@impact27](https://github.com/impact27)
* [PR 17234](https://github.com/spyder-ide/spyder/pull/17234) - PR: Do not test for leaks on Windows to avoid tests stall, by [@impact27](https://github.com/impact27)
* [PR 17231](https://github.com/spyder-ide/spyder/pull/17231) - PR: Test that the debugger handles the namespace of a comprehension, by [@impact27](https://github.com/impact27)
* [PR 17212](https://github.com/spyder-ide/spyder/pull/17212) - PR: Add spyder-terminal plugin to macOS installer, by [@mrclary](https://github.com/mrclary) ([17202](https://github.com/spyder-ide/spyder/issues/17202))
* [PR 17205](https://github.com/spyder-ide/spyder/pull/17205) - PR: Catch leaks in the test suite, by [@impact27](https://github.com/impact27) ([17213](https://github.com/spyder-ide/spyder/issues/17213))
* [PR 17191](https://github.com/spyder-ide/spyder/pull/17191) - PR: Fix debugging unsaved files, by [@impact27](https://github.com/impact27) ([16417](https://github.com/spyder-ide/spyder/issues/16417))
* [PR 17181](https://github.com/spyder-ide/spyder/pull/17181) - PR: Create new file with %edit magic (IPython console), by [@impact27](https://github.com/impact27) ([3394](https://github.com/spyder-ide/spyder/issues/3394))
* [PR 17176](https://github.com/spyder-ide/spyder/pull/17176) - PR: Show tooltip with full path name in Files and Projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17133](https://github.com/spyder-ide/spyder/pull/17133) - PR: Use static text for line numbers (Editor), by [@impact27](https://github.com/impact27)
* [PR 17089](https://github.com/spyder-ide/spyder/pull/17089) - PR: Print last line of Pdb code, by [@impact27](https://github.com/impact27)
* [PR 16957](https://github.com/spyder-ide/spyder/pull/16957) - PR: Override RichJupyterWidget._get_color() because we use a custom style (IPython console), by [@bnavigator](https://github.com/bnavigator) ([14895](https://github.com/spyder-ide/spyder/issues/14895))
* [PR 16914](https://github.com/spyder-ide/spyder/pull/16914) - PR: Cache previous kernel attributes to speed up kernel launch (IPython console), by [@impact27](https://github.com/impact27)
* [PR 16911](https://github.com/spyder-ide/spyder/pull/16911) - PR: Decrease the amount of didChange requests (Editor), by [@impact27](https://github.com/impact27)
* [PR 16651](https://github.com/spyder-ide/spyder/pull/16651) - PR: Update py2app to 0.27 (Mac app), by [@mrclary](https://github.com/mrclary)
* [PR 16509](https://github.com/spyder-ide/spyder/pull/16509) - PR: Add functionality run to and from current line to editor, by [@rhkarls](https://github.com/rhkarls) ([16431](https://github.com/spyder-ide/spyder/issues/16431))
* [PR 16409](https://github.com/spyder-ide/spyder/pull/16409) - PR: Update PyQt requirement to 5.15, by [@ccordoba12](https://github.com/ccordoba12) ([17197](https://github.com/spyder-ide/spyder/issues/17197), [17085](https://github.com/spyder-ide/spyder/issues/17085), [17083](https://github.com/spyder-ide/spyder/issues/17083), [17060](https://github.com/spyder-ide/spyder/issues/17060), [12829](https://github.com/spyder-ide/spyder/issues/12829))
* [PR 16209](https://github.com/spyder-ide/spyder/pull/16209) - PR: Add option to per-file run configuration to use default run configuration, by [@mrclary](https://github.com/mrclary) ([16207](https://github.com/spyder-ide/spyder/issues/16207))
* [PR 15407](https://github.com/spyder-ide/spyder/pull/15407) - PR: Create Completions Plugin Statusbar Widget, by [@mrclary](https://github.com/mrclary) ([38](https://github.com/spyder-ide/ux-improvements/issues/38))

In this release 66 pull requests were closed.


----


## Version 5.2.2 (2022-01-21)

### Important fixes

* Fix using Tk backend on Windows with the IPython Console
* Fix several issues regarding the IPython Console kernel restart, shutdown and bening errors handling

### Issues Closed

* [Issue 17184](https://github.com/spyder-ide/spyder/issues/17184) - In Spyder 5.2.1, History pane is not being updated after entering commands in the IPython console ([PR 17218](https://github.com/spyder-ide/spyder/pull/17218) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17159](https://github.com/spyder-ide/spyder/issues/17159) - TypeError when displaying indent guides in Python 3.10 ([PR 17169](https://github.com/spyder-ide/spyder/pull/17169) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17145](https://github.com/spyder-ide/spyder/issues/17145) - TypeError when computing max of a dataframe column ([PR 17147](https://github.com/spyder-ide/spyder/pull/17147) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17144](https://github.com/spyder-ide/spyder/issues/17144) - The ( bracket does not always appear from input in IPython console ([PR 17175](https://github.com/spyder-ide/spyder/pull/17175) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17129](https://github.com/spyder-ide/spyder/issues/17129) - Error while renaming directory in Files pane ([PR 17132](https://github.com/spyder-ide/spyder/pull/17132) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17120](https://github.com/spyder-ide/spyder/issues/17120) - TypeError in calltip widget ([PR 17121](https://github.com/spyder-ide/spyder/pull/17121) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17102](https://github.com/spyder-ide/spyder/issues/17102) - spyder/app/tests/test_mainwindow.py::test_varexp_magic_dbg fails with Python 3.10 ([PR 17106](https://github.com/spyder-ide/spyder/pull/17106) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17101](https://github.com/spyder-ide/spyder/issues/17101) - Some test failures in spyder/plugins/editor/widgets/tests/test_warnings.py for Python 3.10 ([PR 17106](https://github.com/spyder-ide/spyder/pull/17106) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17100](https://github.com/spyder-ide/spyder/issues/17100) - autopep8 formatting tests failing ([PR 17106](https://github.com/spyder-ide/spyder/pull/17106) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17097](https://github.com/spyder-ide/spyder/issues/17097) - `KeyError: 'workspace'` when opening a project ([PR 17098](https://github.com/spyder-ide/spyder/pull/17098) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17090](https://github.com/spyder-ide/spyder/issues/17090) - test_handle_exception sometimes fails ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17084](https://github.com/spyder-ide/spyder/issues/17084) - test_arrayeditor.py::test_object_arrays_display consistently segfaults ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17080](https://github.com/spyder-ide/spyder/issues/17080) - test_workingdirectory.py tests segfault ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17071](https://github.com/spyder-ide/spyder/issues/17071) - test_pylint.py has lots of failures because qtawesome says 'Invalid font prefix "mdi"' ([PR 17074](https://github.com/spyder-ide/spyder/pull/17074) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17069](https://github.com/spyder-ide/spyder/issues/17069) - test_attribute_errors raises a numpy DeprecationWarning ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17068](https://github.com/spyder-ide/spyder/issues/17068) - test_objectexplorer_collection_types gives lots of errors ([PR 17075](https://github.com/spyder-ide/spyder/pull/17075) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17067](https://github.com/spyder-ide/spyder/issues/17067) - test_load_time fails ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17059](https://github.com/spyder-ide/spyder/issues/17059) - test_range_indicator_visible_on_hover_only fails ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17058](https://github.com/spyder-ide/spyder/issues/17058) - test_pydocgui.py has a timeout failure on test_get_pydoc ([PR 17092](https://github.com/spyder-ide/spyder/pull/17092) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17045](https://github.com/spyder-ide/spyder/issues/17045) - Wrong EOL characters written to file when saving ([PR 17048](https://github.com/spyder-ide/spyder/pull/17048) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17042](https://github.com/spyder-ide/spyder/issues/17042) - Unable to restart kernel with the default interpreter with the standalone Windows installer  ([PR 17158](https://github.com/spyder-ide/spyder/pull/17158) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17028](https://github.com/spyder-ide/spyder/issues/17028) - "Maintain focus in the editor" option has no effect when running cells ([PR 17094](https://github.com/spyder-ide/spyder/pull/17094) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17027](https://github.com/spyder-ide/spyder/issues/17027) - "An error ocurred while starting the kernel" about wrong version of spyder-kernels is displayed despite being installed ([PR 17033](https://github.com/spyder-ide/spyder/pull/17033) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17026](https://github.com/spyder-ide/spyder/issues/17026) - IPython Console shows error message on the Windows installer ([PR 17050](https://github.com/spyder-ide/spyder/pull/17050) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17025](https://github.com/spyder-ide/spyder/issues/17025) - Code Analysis error in the Windows installer when overwriting installation with a new installer version ([PR 17209](https://github.com/spyder-ide/spyder/pull/17209) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17024](https://github.com/spyder-ide/spyder/issues/17024) - Spyder 5.2.1 stuck connecting to kernel when using the Tk backend on Windows ([PR 17156](https://github.com/spyder-ide/spyder/pull/17156) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17011](https://github.com/spyder-ide/spyder/issues/17011) - Kernel process lingers after closing tab when running different interpreter and Qt5 backend ([PR 17035](https://github.com/spyder-ide/spyder/pull/17035) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16997](https://github.com/spyder-ide/spyder/issues/16997) - Error while checking/unchecking completion providers preferences ([PR 17056](https://github.com/spyder-ide/spyder/pull/17056) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16696](https://github.com/spyder-ide/spyder/issues/16696) - multiprocessing failing when function contains a class on the same file ([PR 17170](https://github.com/spyder-ide/spyder/pull/17170) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16676](https://github.com/spyder-ide/spyder/issues/16676) - An extra window running on Windows 11 ([PR 17182](https://github.com/spyder-ide/spyder/pull/17182) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16423](https://github.com/spyder-ide/spyder/issues/16423) - Make Variable Explorer column headers movable ([PR 17127](https://github.com/spyder-ide/spyder/pull/17127) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15331](https://github.com/spyder-ide/spyder/issues/15331) - Help pane cannot be toggled persistently in Spyder 5 ([PR 17222](https://github.com/spyder-ide/spyder/pull/17222) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14928](https://github.com/spyder-ide/spyder/issues/14928) - Get long message in Spyder when I use SymPy consoles ([PR 17051](https://github.com/spyder-ide/spyder/pull/17051) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14739](https://github.com/spyder-ide/spyder/issues/14739) - ZMQError: Address already in use when restarting the kernel ([PR 17035](https://github.com/spyder-ide/spyder/pull/17035) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14534](https://github.com/spyder-ide/spyder/issues/14534) - DeprecationWarning: ShellWidget._syntax_style_changed is deprecated in traitlets 4.1: use @observe and @unobserve instead ([PR 17076](https://github.com/spyder-ide/spyder/pull/17076) by [@juliangilbey](https://github.com/juliangilbey))

In this release 35 issues were closed.

### Pull Requests Merged

* [PR 17226](https://github.com/spyder-ide/spyder/pull/17226) - PR: Update core dependencies for 5.2.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 17222](https://github.com/spyder-ide/spyder/pull/17222) - PR: Raise Help and IPython console to be visible only the first time Spyder starts, by [@ccordoba12](https://github.com/ccordoba12) ([15331](https://github.com/spyder-ide/spyder/issues/15331))
* [PR 17218](https://github.com/spyder-ide/spyder/pull/17218) - PR: Restore connection between the IPython console and History, by [@ccordoba12](https://github.com/ccordoba12) ([17184](https://github.com/spyder-ide/spyder/issues/17184))
* [PR 17209](https://github.com/spyder-ide/spyder/pull/17209) - PR: Update Windows installer assets URL to add previous installation validation, by [@dalthviz](https://github.com/dalthviz) ([17025](https://github.com/spyder-ide/spyder/issues/17025))
* [PR 17193](https://github.com/spyder-ide/spyder/pull/17193) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 17192](https://github.com/spyder-ide/spyder/pull/17192) - PR: Update translations for 5.2.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 17190](https://github.com/spyder-ide/spyder/pull/17190) - PR: Spelling correction in the Kite progress installation dialog, by [@samiam2013](https://github.com/samiam2013)
* [PR 17182](https://github.com/spyder-ide/spyder/pull/17182) - PR: Add missing parent param to QObjects/QWidgets on the status bar base classes, by [@dalthviz](https://github.com/dalthviz) ([16676](https://github.com/spyder-ide/spyder/issues/16676))
* [PR 17175](https://github.com/spyder-ide/spyder/pull/17175) - PR: Prevent an error when inserting left brackets in the IPython console, by [@ccordoba12](https://github.com/ccordoba12) ([17144](https://github.com/spyder-ide/spyder/issues/17144))
* [PR 17170](https://github.com/spyder-ide/spyder/pull/17170) - PR: Fix error with multiprocessing when code contains classes (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([16696](https://github.com/spyder-ide/spyder/issues/16696))
* [PR 17169](https://github.com/spyder-ide/spyder/pull/17169) - PR: Convert to int variable used to paint indent guides (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([17159](https://github.com/spyder-ide/spyder/issues/17159))
* [PR 17158](https://github.com/spyder-ide/spyder/pull/17158) - PR: Fix kernel restart for the Windows app (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([17042](https://github.com/spyder-ide/spyder/issues/17042))
* [PR 17157](https://github.com/spyder-ide/spyder/pull/17157) - PR: Fix error with PyNaCl (Windows installer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17156](https://github.com/spyder-ide/spyder/pull/17156) - PR: Fix hang when setting the Tk backend on Windows (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([17024](https://github.com/spyder-ide/spyder/issues/17024))
* [PR 17147](https://github.com/spyder-ide/spyder/pull/17147) - PR: Catch error when computing the max of a dataframe column (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([17145](https://github.com/spyder-ide/spyder/issues/17145))
* [PR 17137](https://github.com/spyder-ide/spyder/pull/17137) - PR: Skip a test on Windows because it hangs sometimes, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17132](https://github.com/spyder-ide/spyder/pull/17132) - PR: Fix renaming files in the editor after the folder that contains them was renamed in Files, by [@ccordoba12](https://github.com/ccordoba12) ([17129](https://github.com/spyder-ide/spyder/issues/17129))
* [PR 17127](https://github.com/spyder-ide/spyder/pull/17127) - PR: Make Variable Explorer column headers movable, by [@ccordoba12](https://github.com/ccordoba12) ([16423](https://github.com/spyder-ide/spyder/issues/16423))
* [PR 17121](https://github.com/spyder-ide/spyder/pull/17121) - PR: Fix an implicit float to int conversion, by [@ccordoba12](https://github.com/ccordoba12) ([17120](https://github.com/spyder-ide/spyder/issues/17120))
* [PR 17118](https://github.com/spyder-ide/spyder/pull/17118) - PR: Add pyz file extension to be syntax-highlighted as markdown, by [@contactzen](https://github.com/contactzen)
* [PR 17106](https://github.com/spyder-ide/spyder/pull/17106) - PR: Fix autopep8 formatting and more failing tests, by [@ccordoba12](https://github.com/ccordoba12) ([17102](https://github.com/spyder-ide/spyder/issues/17102), [17101](https://github.com/spyder-ide/spyder/issues/17101), [17100](https://github.com/spyder-ide/spyder/issues/17100))
* [PR 17105](https://github.com/spyder-ide/spyder/pull/17105) - PR: Skip another conda test if this tool is not present, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 17098](https://github.com/spyder-ide/spyder/pull/17098) - PR: Catch error when trying to detect project type (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([17097](https://github.com/spyder-ide/spyder/issues/17097))
* [PR 17095](https://github.com/spyder-ide/spyder/pull/17095) - PR: Skip conda and pyenv tests if these tools are not present, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 17094](https://github.com/spyder-ide/spyder/pull/17094) - PR: Fix a couple of focus issues with the IPython console, by [@ccordoba12](https://github.com/ccordoba12) ([17028](https://github.com/spyder-ide/spyder/issues/17028))
* [PR 17092](https://github.com/spyder-ide/spyder/pull/17092) - PR: Fix several small issues in our test suite, by [@ccordoba12](https://github.com/ccordoba12) ([17090](https://github.com/spyder-ide/spyder/issues/17090), [17084](https://github.com/spyder-ide/spyder/issues/17084), [17080](https://github.com/spyder-ide/spyder/issues/17080), [17069](https://github.com/spyder-ide/spyder/issues/17069), [17067](https://github.com/spyder-ide/spyder/issues/17067), [17059](https://github.com/spyder-ide/spyder/issues/17059), [17058](https://github.com/spyder-ide/spyder/issues/17058))
* [PR 17087](https://github.com/spyder-ide/spyder/pull/17087) - PR: Make Pylint config page test run independently from the rest in our test suite, by [@juliangilbey](https://github.com/juliangilbey) ([17071](https://github.com/spyder-ide/spyder/issues/17071))
* [PR 17079](https://github.com/spyder-ide/spyder/pull/17079) - PR: Fix FileNotFoundError in Find plugin, by [@impact27](https://github.com/impact27)
* [PR 17076](https://github.com/spyder-ide/spyder/pull/17076) - PR: Fix traitlets deprecation warning, by [@juliangilbey](https://github.com/juliangilbey) ([14534](https://github.com/spyder-ide/spyder/issues/14534))
* [PR 17075](https://github.com/spyder-ide/spyder/pull/17075) - PR: Fix test_objectexplorer_collection_types for Python 3.9+, by [@ccordoba12](https://github.com/ccordoba12) ([17068](https://github.com/spyder-ide/spyder/issues/17068))
* [PR 17074](https://github.com/spyder-ide/spyder/pull/17074) - PR: Make Pylint plugin tests run independently from the rest in our test suite, by [@ccordoba12](https://github.com/ccordoba12) ([17071](https://github.com/spyder-ide/spyder/issues/17071))
* [PR 17064](https://github.com/spyder-ide/spyder/pull/17064) - PR: Fix "Show in external file explorer" for non-existing file (Windows), by [@rear1019](https://github.com/rear1019)
* [PR 17063](https://github.com/spyder-ide/spyder/pull/17063) - PR: Small fixes to improve compatibility with PySide, by [@rear1019](https://github.com/rear1019)
* [PR 17056](https://github.com/spyder-ide/spyder/pull/17056) - PR: Add validation for registration/unregistration of completion provider status bar widgets, by [@dalthviz](https://github.com/dalthviz) ([16997](https://github.com/spyder-ide/spyder/issues/16997))
* [PR 17052](https://github.com/spyder-ide/spyder/pull/17052) - PR: Reconfigure client before a kernel restart (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17051](https://github.com/spyder-ide/spyder/pull/17051) - PR: Don't print DeprecationWarning's that come from comm handlers (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([14928](https://github.com/spyder-ide/spyder/issues/14928))
* [PR 17050](https://github.com/spyder-ide/spyder/pull/17050) - PR: Avoid showing bening kernel errors in console banner (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([17026](https://github.com/spyder-ide/spyder/issues/17026))
* [PR 17048](https://github.com/spyder-ide/spyder/pull/17048) - PR: Fix setting EOL characters when the user decides their preferred ones in Preferences, by [@ccordoba12](https://github.com/ccordoba12) ([17045](https://github.com/spyder-ide/spyder/issues/17045))
* [PR 17035](https://github.com/spyder-ide/spyder/pull/17035) - PR: Fix shutdown kernels associated to conda envs (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([17011](https://github.com/spyder-ide/spyder/issues/17011), [14739](https://github.com/spyder-ide/spyder/issues/14739))
* [PR 17033](https://github.com/spyder-ide/spyder/pull/17033) - PR: Improve message about missing spyder-kernels (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([17027](https://github.com/spyder-ide/spyder/issues/17027))
* [PR 17020](https://github.com/spyder-ide/spyder/pull/17020) - PR: Clean Announcements.md and update RELEASE.md, by [@dalthviz](https://github.com/dalthviz)
* [PR 17019](https://github.com/spyder-ide/spyder/pull/17019) - PR: Fix cell highlighting (Editor), by [@impact27](https://github.com/impact27)
* [PR 17003](https://github.com/spyder-ide/spyder/pull/17003) - PR: Many updates to third party file lists in NOTICE.txt, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 16974](https://github.com/spyder-ide/spyder/pull/16974) - PR: Limit the number of flags in the editor, by [@impact27](https://github.com/impact27)
* [PR 16921](https://github.com/spyder-ide/spyder/pull/16921) - PR: Improve cursor position history (Editor), by [@impact27](https://github.com/impact27)

In this release 45 pull requests were closed.


----


## Version 5.2.1 (2021-12-14)

### Important fixes

* Prevent Spyder from crashing when selecting an interpreter with an incorrect `spyder-kernels` version
* Optimize several operations in the Editor and IPython Console

### Issues Closed

* [Issue 17005](https://github.com/spyder-ide/spyder/issues/17005) - Bump/remove outdated `spyder-kernerls` `requirements.py` version validation and Spyder crashing ([PR 17009](https://github.com/spyder-ide/spyder/pull/17009) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16995](https://github.com/spyder-ide/spyder/issues/16995) - Some SVG images have unnecessary executable permissions ([PR 17000](https://github.com/spyder-ide/spyder/pull/17000) by [@juliangilbey](https://github.com/juliangilbey))
* [Issue 16964](https://github.com/spyder-ide/spyder/issues/16964) - No possibility to select yapf as auto-formatter in preferences ([PR 16972](https://github.com/spyder-ide/spyder/pull/16972) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16960](https://github.com/spyder-ide/spyder/issues/16960) - TypeError when pressing Ctrl+Shift+Tab in the Editor ([PR 16973](https://github.com/spyder-ide/spyder/pull/16973) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16948](https://github.com/spyder-ide/spyder/issues/16948) - Clearing Find textbox in Editor does not trigger update to clear highlighted matches until Editor text changed ([PR 16950](https://github.com/spyder-ide/spyder/pull/16950) by [@impact27](https://github.com/impact27))
* [Issue 16935](https://github.com/spyder-ide/spyder/issues/16935) - Missing mandatory packages does not raise error ([PR 16943](https://github.com/spyder-ide/spyder/pull/16943) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16931](https://github.com/spyder-ide/spyder/issues/16931) - Disabling the Projects pluging crashes spyder ([PR 16945](https://github.com/spyder-ide/spyder/pull/16945) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16927](https://github.com/spyder-ide/spyder/issues/16927) - Debugger message bug gets printed in the IPython Console ([PR 16928](https://github.com/spyder-ide/spyder/pull/16928) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16910](https://github.com/spyder-ide/spyder/issues/16910) - Spyder Mac app laggy in 5.2.0 ([PR 16933](https://github.com/spyder-ide/spyder/pull/16933) by [@mrclary](https://github.com/mrclary))
* [Issue 16898](https://github.com/spyder-ide/spyder/issues/16898) - Mac app crashes when openning Spyder version 5.2.0 ([PR 16895](https://github.com/spyder-ide/spyder/pull/16895) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16896](https://github.com/spyder-ide/spyder/issues/16896) - Spyder 5.2 Windows installer crashes during launch ([PR 16895](https://github.com/spyder-ide/spyder/pull/16895) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16865](https://github.com/spyder-ide/spyder/issues/16865) - Spyder freezes when zooming in and out in a large file ([PR 16864](https://github.com/spyder-ide/spyder/pull/16864) by [@impact27](https://github.com/impact27))
* [Issue 16744](https://github.com/spyder-ide/spyder/issues/16744) - Remove Kite startup splash screen when Spyder starts ([PR 17013](https://github.com/spyder-ide/spyder/pull/17013) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16439](https://github.com/spyder-ide/spyder/issues/16439) - Internal problem when toggling max allowed line length ([PR 16906](https://github.com/spyder-ide/spyder/pull/16906) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16390](https://github.com/spyder-ide/spyder/issues/16390) - Modal dialog post resolution rescale locks up Spyder ([PR 16941](https://github.com/spyder-ide/spyder/pull/16941) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14521](https://github.com/spyder-ide/spyder/issues/14521) - Line break before type hint breaks docstring generation ([PR 14567](https://github.com/spyder-ide/spyder/pull/14567) by [@Richardk2n](https://github.com/Richardk2n))
* [Issue 14520](https://github.com/spyder-ide/spyder/issues/14520) - Docstring generation not working if the return type is an Annotated containing a function call ([PR 14567](https://github.com/spyder-ide/spyder/pull/14567) by [@Richardk2n](https://github.com/Richardk2n))
* [Issue 14188](https://github.com/spyder-ide/spyder/issues/14188) - Show vertical line at maximum allowed line length does not respect max allowed line length at startup ([PR 16906](https://github.com/spyder-ide/spyder/pull/16906) by [@ccordoba12](https://github.com/ccordoba12))

In this release 18 issues were closed.

### Pull Requests Merged

* [PR 17015](https://github.com/spyder-ide/spyder/pull/17015) - PR: Update CI workflows to use macOS 10.15, by [@dalthviz](https://github.com/dalthviz)
* [PR 17013](https://github.com/spyder-ide/spyder/pull/17013) - PR: Don't show Kite dialog the third time Spyder starts, by [@ccordoba12](https://github.com/ccordoba12) ([16744](https://github.com/spyder-ide/spyder/issues/16744))
* [PR 17012](https://github.com/spyder-ide/spyder/pull/17012) - PR: Update Quansight logo in Readme, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 17010](https://github.com/spyder-ide/spyder/pull/17010) - PR: Update core dependencies for 5.2.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 17009](https://github.com/spyder-ide/spyder/pull/17009) - PR: Remove `check_spyder_kernels`, by [@dalthviz](https://github.com/dalthviz) ([17005](https://github.com/spyder-ide/spyder/issues/17005))
* [PR 17000](https://github.com/spyder-ide/spyder/pull/17000) - PR: Remove execute bit permissions from images and data files, by [@juliangilbey](https://github.com/juliangilbey) ([16995](https://github.com/spyder-ide/spyder/issues/16995), [16995](https://github.com/spyder-ide/spyder/issues/16995))
* [PR 16991](https://github.com/spyder-ide/spyder/pull/16991) - PR: Fix changing color scheme and UI theme (Appearance), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16984](https://github.com/spyder-ide/spyder/pull/16984) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 16983](https://github.com/spyder-ide/spyder/pull/16983) - PR: Update translations for 5.2.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 16977](https://github.com/spyder-ide/spyder/pull/16977) - PR: Fix option to maintain focus on editor after running cells or selections, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16973](https://github.com/spyder-ide/spyder/pull/16973) - PR: Cast floats to ints in tab switcher (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16960](https://github.com/spyder-ide/spyder/issues/16960))
* [PR 16972](https://github.com/spyder-ide/spyder/pull/16972) - PR: Remove mention to Yapf in style and formatting preferences tab (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([16964](https://github.com/spyder-ide/spyder/issues/16964))
* [PR 16970](https://github.com/spyder-ide/spyder/pull/16970) - PR: Clean tests for CodeEditor, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16968](https://github.com/spyder-ide/spyder/pull/16968) - PR: Fix get_text_with_eol for files with CRLF line endings, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16950](https://github.com/spyder-ide/spyder/pull/16950) - PR: Clear highlighted matches after clearing text in find widget (Editor), by [@impact27](https://github.com/impact27) ([16948](https://github.com/spyder-ide/spyder/issues/16948))
* [PR 16945](https://github.com/spyder-ide/spyder/pull/16945) - PR: Fix errors when other plugins are not available (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16931](https://github.com/spyder-ide/spyder/issues/16931))
* [PR 16943](https://github.com/spyder-ide/spyder/pull/16943) - PR: Fix detection of non-installed modules (Dependencies), by [@ccordoba12](https://github.com/ccordoba12) ([16935](https://github.com/spyder-ide/spyder/issues/16935))
* [PR 16941](https://github.com/spyder-ide/spyder/pull/16941) - PR: Move DPI change message dialog to the primaryScreen center, by [@dalthviz](https://github.com/dalthviz) ([16390](https://github.com/spyder-ide/spyder/issues/16390))
* [PR 16933](https://github.com/spyder-ide/spyder/pull/16933) - PR: Ensure jellyfish is packaged with macOS installer, by [@mrclary](https://github.com/mrclary) ([16910](https://github.com/spyder-ide/spyder/issues/16910))
* [PR 16928](https://github.com/spyder-ide/spyder/pull/16928) - PR: Add validation to filter "Python bug https://bugs.python.org/issue1180193" message, by [@dalthviz](https://github.com/dalthviz) ([16927](https://github.com/spyder-ide/spyder/issues/16927))
* [PR 16925](https://github.com/spyder-ide/spyder/pull/16925) - PR: Do not check for change on every keystroke, by [@impact27](https://github.com/impact27)
* [PR 16915](https://github.com/spyder-ide/spyder/pull/16915) - PR: Fix error when updating the plugin checkboxes state, by [@steff456](https://github.com/steff456)
* [PR 16907](https://github.com/spyder-ide/spyder/pull/16907) - PR: Some improvements to the docstring extension (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16906](https://github.com/spyder-ide/spyder/pull/16906) - PR: Fix applying configuration options to the editor, by [@ccordoba12](https://github.com/ccordoba12) ([16439](https://github.com/spyder-ide/spyder/issues/16439), [14188](https://github.com/spyder-ide/spyder/issues/14188))
* [PR 16899](https://github.com/spyder-ide/spyder/pull/16899) - PR: Fix some issues with dependencies, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16895](https://github.com/spyder-ide/spyder/pull/16895) - PR: Update RELEASE and MAINTENANCE files and fix some IPython Console issues, by [@dalthviz](https://github.com/dalthviz) ([16898](https://github.com/spyder-ide/spyder/issues/16898), [16896](https://github.com/spyder-ide/spyder/issues/16896))
* [PR 16864](https://github.com/spyder-ide/spyder/pull/16864) - PR: Optimize several operations in the editor and IPython console, by [@impact27](https://github.com/impact27) ([16865](https://github.com/spyder-ide/spyder/issues/16865))
* [PR 14567](https://github.com/spyder-ide/spyder/pull/14567) - PR: Fix issues with docstring generation, by [@Richardk2n](https://github.com/Richardk2n) ([14521](https://github.com/spyder-ide/spyder/issues/14521), [14520](https://github.com/spyder-ide/spyder/issues/14520))

In this release 28 pull requests were closed.


----


## Version 5.2.0 (2021-11-24)

### New features

* Add new entry in preferences to turn off plugins
* Add experimental support for PySide2

### Important fixes

* Show standard streams when running code in the IPython Console
* Speed up search in the Find plugin

### New API features

* Migrate the IPython Console to the new API
* Add new mechanism for plugin teardowm
* Add a way to create stacked widgets connected to the IPython Console
  like Plots and the Variable explorer

### Issues Closed

* [Issue 16863](https://github.com/spyder-ide/spyder/issues/16863) - Kernel error trigerred by an asyncio conflict with SpyderKernelApp ([PR 16872](https://github.com/spyder-ide/spyder/pull/16872) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16828](https://github.com/spyder-ide/spyder/issues/16828) - Python seems to be incorrectly compiled for macOS installer ([PR 16849](https://github.com/spyder-ide/spyder/pull/16849) by [@mrclary](https://github.com/mrclary))
* [Issue 16790](https://github.com/spyder-ide/spyder/issues/16790) - Inconsistent debugger behavior ([PR 16820](https://github.com/spyder-ide/spyder/pull/16820) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16780](https://github.com/spyder-ide/spyder/issues/16780) - AttributeError: 'EvalEnv' object has no attribute 'get' ([PR 16815](https://github.com/spyder-ide/spyder/pull/16815) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16778](https://github.com/spyder-ide/spyder/issues/16778) - Readme is outdated  ([PR 16783](https://github.com/spyder-ide/spyder/pull/16783) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16763](https://github.com/spyder-ide/spyder/issues/16763) - app/tests/test_mainwindow.py::test_runcell_pdb is failing
* [Issue 16762](https://github.com/spyder-ide/spyder/issues/16762) - _kill_kernel changed in jupyter_clients 7.0.6 ([PR 16644](https://github.com/spyder-ide/spyder/pull/16644) by [@bnavigator](https://github.com/bnavigator))
* [Issue 16749](https://github.com/spyder-ide/spyder/issues/16749) - has_been_modified method has two arguments but only one is passed in Preferences ([PR 16787](https://github.com/spyder-ide/spyder/pull/16787) by [@steff456](https://github.com/steff456))
* [Issue 16748](https://github.com/spyder-ide/spyder/issues/16748) - Startup run code of IPython is not working when using projects ([PR 16753](https://github.com/spyder-ide/spyder/pull/16753) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16745](https://github.com/spyder-ide/spyder/issues/16745) - "Create new project" dialog box button focus is "Cancel" not "Create"  ([PR 16847](https://github.com/spyder-ide/spyder/pull/16847) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16731](https://github.com/spyder-ide/spyder/issues/16731) - Opening Image RGB object in the variable explorer ([PR 16738](https://github.com/spyder-ide/spyder/pull/16738) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16703](https://github.com/spyder-ide/spyder/issues/16703) - AttributeError when searching for help ([PR 16705](https://github.com/spyder-ide/spyder/pull/16705) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16649](https://github.com/spyder-ide/spyder/issues/16649) - Mac installers are failing to build ([PR 16652](https://github.com/spyder-ide/spyder/pull/16652) by [@mrclary](https://github.com/mrclary))
* [Issue 16598](https://github.com/spyder-ide/spyder/issues/16598) - AttributeError when opening numpy array from OS file explorer ([PR 16605](https://github.com/spyder-ide/spyder/pull/16605) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16571](https://github.com/spyder-ide/spyder/issues/16571) - TypeError in Tour with Python 3.10 ([PR 16574](https://github.com/spyder-ide/spyder/pull/16574) by [@rear1019](https://github.com/rear1019))
* [Issue 16537](https://github.com/spyder-ide/spyder/issues/16537) - Installer-based Spyder does not start on Windows ([PR 16559](https://github.com/spyder-ide/spyder/pull/16559) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16477](https://github.com/spyder-ide/spyder/issues/16477) - Drag & drop error in the Help pane ([PR 16483](https://github.com/spyder-ide/spyder/pull/16483) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16444](https://github.com/spyder-ide/spyder/issues/16444) - Regression: Spyder 5.1.5 doesn't enter on debug mode on breakpoint() command ([PR 16496](https://github.com/spyder-ide/spyder/pull/16496) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16348](https://github.com/spyder-ide/spyder/issues/16348) - ModuleNotFoundError with PyTorch and setting a custom interpreter ([PR 16815](https://github.com/spyder-ide/spyder/pull/16815) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16280](https://github.com/spyder-ide/spyder/issues/16280) - Autoformat files on save when running them causes lines addition to code ([PR 16539](https://github.com/spyder-ide/spyder/pull/16539) by [@impact27](https://github.com/impact27))
* [Issue 16216](https://github.com/spyder-ide/spyder/issues/16216) - Permanently undock some panes? ([PR 16889](https://github.com/spyder-ide/spyder/pull/16889) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15921](https://github.com/spyder-ide/spyder/issues/15921) - Consoles connected to external ipykernels break Plots and the Variable Explorer ([PR 15922](https://github.com/spyder-ide/spyder/pull/15922) by [@impact27](https://github.com/impact27))
* [Issue 15875](https://github.com/spyder-ide/spyder/issues/15875) - CommError: The comm is not connected when changing Matplotlib backend ([PR 16370](https://github.com/spyder-ide/spyder/pull/16370) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15654](https://github.com/spyder-ide/spyder/issues/15654) - `Alt Gr + F` triggering Find in files plugin instead of square brackets (`[`) on QWERTZ (Hungarian) keyboard layout ([PR 16782](https://github.com/spyder-ide/spyder/pull/16782) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15594](https://github.com/spyder-ide/spyder/issues/15594) - Completion & Linting settings missing from the preferences menu ([PR 16012](https://github.com/spyder-ide/spyder/pull/16012) by [@andfoy](https://github.com/andfoy))
* [Issue 15340](https://github.com/spyder-ide/spyder/issues/15340) - UnicodeDecodeError when opening a project ([PR 16522](https://github.com/spyder-ide/spyder/pull/16522) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14823](https://github.com/spyder-ide/spyder/issues/14823) - Typing latency in the editor due to folding ([PR 16446](https://github.com/spyder-ide/spyder/pull/16446) by [@mrclary](https://github.com/mrclary))
* [Issue 14138](https://github.com/spyder-ide/spyder/issues/14138) - Run Tests on macOS Application ([PR 16339](https://github.com/spyder-ide/spyder/pull/16339) by [@mrclary](https://github.com/mrclary))
* [Issue 13991](https://github.com/spyder-ide/spyder/issues/13991) - 'cerr' output multiplied with multiple clicks of 'Run'. ([PR 14025](https://github.com/spyder-ide/spyder/pull/14025) by [@impact27](https://github.com/impact27))
* [Issue 12194](https://github.com/spyder-ide/spyder/issues/12194) - Move IPython console to use the new API ([PR 16324](https://github.com/spyder-ide/spyder/pull/16324) by [@dalthviz](https://github.com/dalthviz))
* [Issue 10649](https://github.com/spyder-ide/spyder/issues/10649) - Layout of undocked windows not saved on Spyder 4 ([PR 16889](https://github.com/spyder-ide/spyder/pull/16889) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 9759](https://github.com/spyder-ide/spyder/issues/9759) - Output from C++ library not shown on IPython console ([PR 14025](https://github.com/spyder-ide/spyder/pull/14025) by [@impact27](https://github.com/impact27))
* [Issue 6894](https://github.com/spyder-ide/spyder/issues/6894) - PySide2 support ([PR 16322](https://github.com/spyder-ide/spyder/pull/16322) by [@rear1019](https://github.com/rear1019))
* [Issue 1922](https://github.com/spyder-ide/spyder/issues/1922) - (IPython) Some exceptions are only shown in the kernel's console ([PR 14025](https://github.com/spyder-ide/spyder/pull/14025) by [@impact27](https://github.com/impact27))

In this release 34 issues were closed.

### Pull Requests Merged

* [PR 16892](https://github.com/spyder-ide/spyder/pull/16892) - PR: Update core deps for 5.2.0, by [@dalthviz](https://github.com/dalthviz)
* [PR 16889](https://github.com/spyder-ide/spyder/pull/16889) - PR: Save and restore geometry of undocked plugins, by [@ccordoba12](https://github.com/ccordoba12) ([16216](https://github.com/spyder-ide/spyder/issues/16216), [10649](https://github.com/spyder-ide/spyder/issues/10649))
* [PR 16872](https://github.com/spyder-ide/spyder/pull/16872) - PR: Run asyncio and normal handlers in the kernel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([16863](https://github.com/spyder-ide/spyder/issues/16863))
* [PR 16857](https://github.com/spyder-ide/spyder/pull/16857) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 16856](https://github.com/spyder-ide/spyder/pull/16856) - PR: Don't use Matplotlib in a test to prevent hangs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16855](https://github.com/spyder-ide/spyder/pull/16855) - PR: Update missing translation strings for next release, by [@dalthviz](https://github.com/dalthviz)
* [PR 16850](https://github.com/spyder-ide/spyder/pull/16850) - PR: Print std stream messages in the console while starting, by [@impact27](https://github.com/impact27)
* [PR 16849](https://github.com/spyder-ide/spyder/pull/16849) - PR: Filter 'This version of python seems to be incorrectly compiled...' pydev_log.critical message, by [@mrclary](https://github.com/mrclary) ([16828](https://github.com/spyder-ide/spyder/issues/16828))
* [PR 16848](https://github.com/spyder-ide/spyder/pull/16848) - PR: Prevent some plugins from being disabled, by [@steff456](https://github.com/steff456)
* [PR 16847](https://github.com/spyder-ide/spyder/pull/16847) - PR: Improve the "Create new project" dialog (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([16745](https://github.com/spyder-ide/spyder/issues/16745))
* [PR 16845](https://github.com/spyder-ide/spyder/pull/16845) - PR: Skip a test in our pip slots because it's hanging, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16831](https://github.com/spyder-ide/spyder/pull/16831) - PR: Fix some issues after the IPython Console migration, by [@dalthviz](https://github.com/dalthviz)
* [PR 16829](https://github.com/spyder-ide/spyder/pull/16829) - PR: Constrain IPython to be less than 7.28.0 for macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 16824](https://github.com/spyder-ide/spyder/pull/16824) - PR: Fix crashes when certain plugins are not available, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16820](https://github.com/spyder-ide/spyder/pull/16820) - PR: Fix inconsistent behavior when running comprehensions in the debugger, by [@ccordoba12](https://github.com/ccordoba12) ([16790](https://github.com/spyder-ide/spyder/issues/16790))
* [PR 16819](https://github.com/spyder-ide/spyder/pull/16819) - PR: Skip a test that became too flaky on Mac, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16815](https://github.com/spyder-ide/spyder/pull/16815) - PR: Fix a couple of issues when running Pytorch code (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([16780](https://github.com/spyder-ide/spyder/issues/16780), [16348](https://github.com/spyder-ide/spyder/issues/16348))
* [PR 16801](https://github.com/spyder-ide/spyder/pull/16801) - PR: Update RELEASE.md and CONTRIBUTING.md, by [@dalthviz](https://github.com/dalthviz)
* [PR 16787](https://github.com/spyder-ide/spyder/pull/16787) - PR: Add missing argument to shortcut preferences, by [@steff456](https://github.com/steff456) ([16749](https://github.com/spyder-ide/spyder/issues/16749))
* [PR 16783](https://github.com/spyder-ide/spyder/pull/16783) - PR: Remove paragraph about Spyder 4 (Readme), by [@ccordoba12](https://github.com/ccordoba12) ([16778](https://github.com/spyder-ide/spyder/issues/16778))
* [PR 16782](https://github.com/spyder-ide/spyder/pull/16782) - PR: Change keyboard shortcut for "Find in files" action in the Search menu, by [@ccordoba12](https://github.com/ccordoba12) ([15654](https://github.com/spyder-ide/spyder/issues/15654))
* [PR 16772](https://github.com/spyder-ide/spyder/pull/16772) - PR: Update translations for 5.2.0, by [@dalthviz](https://github.com/dalthviz)
* [PR 16766](https://github.com/spyder-ide/spyder/pull/16766) - PR: Fix kernel shutdown (IPython console), by [@impact27](https://github.com/impact27)
* [PR 16764](https://github.com/spyder-ide/spyder/pull/16764) - PR: Update Spyder for qtconsole 5.2.0, by [@impact27](https://github.com/impact27)
* [PR 16753](https://github.com/spyder-ide/spyder/pull/16753) - PR: Allow console restart when reopening projects at startup, by [@dalthviz](https://github.com/dalthviz) ([16748](https://github.com/spyder-ide/spyder/issues/16748))
* [PR 16738](https://github.com/spyder-ide/spyder/pull/16738) - PR: Reimport ArrayEditor when displaying PIL images to avoid error (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([16731](https://github.com/spyder-ide/spyder/issues/16731))
* [PR 16722](https://github.com/spyder-ide/spyder/pull/16722) - PR: PySide - Do not pass `None` to QTreeView.setExpanded() (prevents a TypeError), by [@rear1019](https://github.com/rear1019)
* [PR 16711](https://github.com/spyder-ide/spyder/pull/16711) - PR: UX improvements to panes that inherit from OneColumnTree widget, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16705](https://github.com/spyder-ide/spyder/pull/16705) - PR: Catch error when trying to install event filter in WebView widget, by [@ccordoba12](https://github.com/ccordoba12) ([16703](https://github.com/spyder-ide/spyder/issues/16703))
* [PR 16686](https://github.com/spyder-ide/spyder/pull/16686) - PR: Try to fix bug when setting cursor shape for single click to open (Files/Projects), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16678](https://github.com/spyder-ide/spyder/pull/16678) - PR: Check tests with new snippets cache (Completions), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16652](https://github.com/spyder-ide/spyder/pull/16652) - PR: Limit jupyter-core to be less than 4.9 for macOS Installer, by [@mrclary](https://github.com/mrclary) ([16649](https://github.com/spyder-ide/spyder/issues/16649))
* [PR 16644](https://github.com/spyder-ide/spyder/pull/16644) - PR: Add support for Jupyter-client >= 7, by [@bnavigator](https://github.com/bnavigator) ([16762](https://github.com/spyder-ide/spyder/issues/16762))
* [PR 16605](https://github.com/spyder-ide/spyder/pull/16605) - PR: Fix error when opening files that the Variable Explorer can handle (Main window), by [@ccordoba12](https://github.com/ccordoba12) ([16598](https://github.com/spyder-ide/spyder/issues/16598))
* [PR 16602](https://github.com/spyder-ide/spyder/pull/16602) - PR: Only run pyenv tests on Linux (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16601](https://github.com/spyder-ide/spyder/pull/16601) - PR: Fix `__init__` of widgets that inherit from SpyderWidgetMixin for PyQt5 , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16599](https://github.com/spyder-ide/spyder/pull/16599) - PR: Help pip solver to pull dependencies faster (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16585](https://github.com/spyder-ide/spyder/pull/16585) - PR: Fix QProcess error messages in Completions plugin, by [@rear1019](https://github.com/rear1019)
* [PR 16574](https://github.com/spyder-ide/spyder/pull/16574) - PR: Fix QImage.scaled() with PyQt5 >= 5.15 (Tours), by [@rear1019](https://github.com/rear1019) ([16571](https://github.com/spyder-ide/spyder/issues/16571))
* [PR 16565](https://github.com/spyder-ide/spyder/pull/16565) - PR: Remove top constraint on Pylint, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16559](https://github.com/spyder-ide/spyder/pull/16559) - PR: Fix fallback to Spyder 2 icon theme to handle QtAwesome FontError, by [@dalthviz](https://github.com/dalthviz) ([16537](https://github.com/spyder-ide/spyder/issues/16537))
* [PR 16540](https://github.com/spyder-ide/spyder/pull/16540) - PR: Fix link to Spyder docs in connect to external kernel dialog, by [@CAM-Gerlach](https://github.com/CAM-Gerlach)
* [PR 16539](https://github.com/spyder-ide/spyder/pull/16539) - PR: Avoid calling auto-formatting when such an operation is taking place, by [@impact27](https://github.com/impact27) ([16280](https://github.com/spyder-ide/spyder/issues/16280))
* [PR 16532](https://github.com/spyder-ide/spyder/pull/16532) - PR: Sync subrepo with spyder-kernels#327, by [@impact27](https://github.com/impact27)
* [PR 16522](https://github.com/spyder-ide/spyder/pull/16522) - PR: Read project config file using UTF-8 (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([15340](https://github.com/spyder-ide/spyder/issues/15340))
* [PR 16507](https://github.com/spyder-ide/spyder/pull/16507) - PR: Fix swapped icons for Indent/Unindent actions (Editor), by [@rear1019](https://github.com/rear1019)
* [PR 16496](https://github.com/spyder-ide/spyder/pull/16496) - PR: Add a test to check that the breakpoint builtin is working, by [@ccordoba12](https://github.com/ccordoba12) ([16444](https://github.com/spyder-ide/spyder/issues/16444))
* [PR 16492](https://github.com/spyder-ide/spyder/pull/16492) - PR: Use conda-forge and mamba for testing, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16484](https://github.com/spyder-ide/spyder/pull/16484) - PR: Break `widgets.py` module into a package (Find), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16483](https://github.com/spyder-ide/spyder/pull/16483) - PR: Fix error when loading urls (Help), by [@ccordoba12](https://github.com/ccordoba12) ([16477](https://github.com/spyder-ide/spyder/issues/16477))
* [PR 16457](https://github.com/spyder-ide/spyder/pull/16457) - PR: Change cursor to pointing hand when single click option is on in Files and Projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16446](https://github.com/spyder-ide/spyder/pull/16446) - PR: Improve performance of code folding and indent guides, by [@mrclary](https://github.com/mrclary) ([14823](https://github.com/spyder-ide/spyder/issues/14823))
* [PR 16441](https://github.com/spyder-ide/spyder/pull/16441) - PR: Use a different icon for text completions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16370](https://github.com/spyder-ide/spyder/pull/16370) - PR: Add a test for the Tkinter backend (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([15875](https://github.com/spyder-ide/spyder/issues/15875))
* [PR 16339](https://github.com/spyder-ide/spyder/pull/16339) - PR: Add automatic tests for the macOS installer, by [@mrclary](https://github.com/mrclary) ([14138](https://github.com/spyder-ide/spyder/issues/14138))
* [PR 16324](https://github.com/spyder-ide/spyder/pull/16324) - PR: Migrate the IPython Console to the new API, by [@dalthviz](https://github.com/dalthviz) ([12194](https://github.com/spyder-ide/spyder/issues/12194))
* [PR 16322](https://github.com/spyder-ide/spyder/pull/16322) - PR: Make Spyder compatible (for the most part) with PySide2, by [@rear1019](https://github.com/rear1019) ([6894](https://github.com/spyder-ide/spyder/issues/6894))
* [PR 16229](https://github.com/spyder-ide/spyder/pull/16229) - PR: Several improvements to Find, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16012](https://github.com/spyder-ide/spyder/pull/16012) - PR: Add plugin teardown operations to the plugin registry, by [@andfoy](https://github.com/andfoy) ([15594](https://github.com/spyder-ide/spyder/issues/15594))
* [PR 15922](https://github.com/spyder-ide/spyder/pull/15922) - PR: Add a way to create plugins like Plots and the Variable explorer to the API, by [@impact27](https://github.com/impact27) ([15921](https://github.com/spyder-ide/spyder/issues/15921))
* [PR 14025](https://github.com/spyder-ide/spyder/pull/14025) - PR: Fix handling of kernel stderr, and capture stdout and segfaults too (IPython console), by [@impact27](https://github.com/impact27) ([9759](https://github.com/spyder-ide/spyder/issues/9759), [1922](https://github.com/spyder-ide/spyder/issues/1922), [13991](https://github.com/spyder-ide/spyder/issues/13991))

In this release 61 pull requests were closed.


----


## Version 5.1.5 (2021-09-16)

### Important fixes
* Fix docking of external plugins.

### Issues Closed

* [Issue 16419](https://github.com/spyder-ide/spyder/issues/16419) - Plugins not appearing in tabs in 5.2.0dev ([PR 16416](https://github.com/spyder-ide/spyder/pull/16416) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 16428](https://github.com/spyder-ide/spyder/pull/16428) - PR: Catch error when starting watcher (Projects), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16416](https://github.com/spyder-ide/spyder/pull/16416) - PR: Fix some issues with external plugins, by [@ccordoba12](https://github.com/ccordoba12) ([16419](https://github.com/spyder-ide/spyder/issues/16419))
* [PR 16375](https://github.com/spyder-ide/spyder/pull/16375) - PR: Improve appearance of toolbar extension button, by [@ccordoba12](https://github.com/ccordoba12)

In this release 3 pull requests were closed.


----


## Version 5.1.4 (2021-09-12)

### Important fixes
* Fix serious memory leaks and improve performance when typing in the editor.

### Issues Closed

* [Issue 16401](https://github.com/spyder-ide/spyder/issues/16401) - `Trim all newlines after the final one` when saving a file causes Spyder to freeze when saving a blank file ([PR 16405](https://github.com/spyder-ide/spyder/pull/16405) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16384](https://github.com/spyder-ide/spyder/issues/16384) - Editor becomes sluggish when displaying errors ([PR 16396](https://github.com/spyder-ide/spyder/pull/16396) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16343](https://github.com/spyder-ide/spyder/issues/16343) - No handler for workspace/executeCommand request ([PR 16344](https://github.com/spyder-ide/spyder/pull/16344) by [@hlouzada](https://github.com/hlouzada))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 16405](https://github.com/spyder-ide/spyder/pull/16405) - PR: Don't try to trim new lines for files with a single line (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16401](https://github.com/spyder-ide/spyder/issues/16401))
* [PR 16396](https://github.com/spyder-ide/spyder/pull/16396) - PR: Improve linting and folding performance (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16384](https://github.com/spyder-ide/spyder/issues/16384))
* [PR 16389](https://github.com/spyder-ide/spyder/pull/16389) - PR: Add constraint for jupyter_client version on conda based test, by [@dalthviz](https://github.com/dalthviz)
* [PR 16371](https://github.com/spyder-ide/spyder/pull/16371) - PR: Restore a couple of completion options lost during the migration (Completions), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16351](https://github.com/spyder-ide/spyder/pull/16351) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 16344](https://github.com/spyder-ide/spyder/pull/16344) - PR: Handle execute command response (LSP), by [@hlouzada](https://github.com/hlouzada) ([16343](https://github.com/spyder-ide/spyder/issues/16343))

In this release 6 pull requests were closed.


----


## Version 5.1.3 (2021-09-05)

### Important fixes
* Fix error when starting kernels in macOS application.

### Issues Closed

* [Issue 16358](https://github.com/spyder-ide/spyder/issues/16358) - RTreeError with snippets ([PR 16364](https://github.com/spyder-ide/spyder/pull/16364) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16346](https://github.com/spyder-ide/spyder/issues/16346) - TypeError with snippets ([PR 16364](https://github.com/spyder-ide/spyder/pull/16364) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16336](https://github.com/spyder-ide/spyder/issues/16336) - 5.1.2 Mac installer broken? ([PR 16337](https://github.com/spyder-ide/spyder/pull/16337) by [@mrclary](https://github.com/mrclary))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 16366](https://github.com/spyder-ide/spyder/pull/16366) - PR: Set minimum and recommended sizes for the Working directory combobox , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16365](https://github.com/spyder-ide/spyder/pull/16365) - PR: Remove indicator of popup menus in main toolbar, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16364](https://github.com/spyder-ide/spyder/pull/16364) - PR: Catch a couple of errors generated by Kite (Snippets), by [@ccordoba12](https://github.com/ccordoba12) ([16358](https://github.com/spyder-ide/spyder/issues/16358), [16346](https://github.com/spyder-ide/spyder/issues/16346))
* [PR 16337](https://github.com/spyder-ide/spyder/pull/16337) - PR: debugpy is not zip compatible (macOS app), by [@mrclary](https://github.com/mrclary) ([16336](https://github.com/spyder-ide/spyder/issues/16336))

In this release 4 pull requests were closed.


----


## Version 5.1.2 (2021-09-02)

### New features
* Add an entry called `Restart in debug mode` to the File menu. That will allow
  users to inspect the log files generated by Spyder by going to the menu
  `Tools > Debug logs` after the restart.
* Add a new command line option called `--conf-dir` to set a custom
  configuration directory for Spyder.
* Show hidden directories in Projects by default.

### New API features
* Use toolbar ids and widget/action ids when adding an item to a toolbar.
* Use menu and item ids to add items to the Main Menu plugin.

### Important fixes
* Fix several performance issues in the Editor.
* Fix slow browsing of variables in the Variable Explorer when Numpy and Pandas
  are not installed.
* Discard symbols imported from other libraries in the Outline pane.

### Issues Closed

* [Issue 16316](https://github.com/spyder-ide/spyder/issues/16316) - TypeError: runfile() got an unexpected keyword argument 'current_namespace' when trying to debug ([PR 16323](https://github.com/spyder-ide/spyder/pull/16323) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16292](https://github.com/spyder-ide/spyder/issues/16292) - ModuleNotFoundError: No module named 'platformdirs.macos' on macOS App ([PR 16293](https://github.com/spyder-ide/spyder/pull/16293) by [@mrclary](https://github.com/mrclary))
* [Issue 16287](https://github.com/spyder-ide/spyder/issues/16287) - Error when clicking Tools menu ([PR 16303](https://github.com/spyder-ide/spyder/pull/16303) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16269](https://github.com/spyder-ide/spyder/issues/16269) - Multiple IPython documentation help menus ([PR 16284](https://github.com/spyder-ide/spyder/pull/16284) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16248](https://github.com/spyder-ide/spyder/issues/16248) - Maximum character line slightly wrong ([PR 16277](https://github.com/spyder-ide/spyder/pull/16277) by [@rhkarls](https://github.com/rhkarls))
* [Issue 16247](https://github.com/spyder-ide/spyder/issues/16247) - Variable explorer is very slow ([PR 16276](https://github.com/spyder-ide/spyder/pull/16276) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16236](https://github.com/spyder-ide/spyder/issues/16236) - New Splash Screen misbehaves on dark backgrounds ([PR 16233](https://github.com/spyder-ide/spyder/pull/16233) by [@isabela-pf](https://github.com/isabela-pf))
* [Issue 16185](https://github.com/spyder-ide/spyder/issues/16185) - Mac OS - Execute in external system terminal not working ([PR 16200](https://github.com/spyder-ide/spyder/pull/16200) by [@mrclary](https://github.com/mrclary))
* [Issue 16180](https://github.com/spyder-ide/spyder/issues/16180) - "Format file or selection with Autopep8" cause the code to be misplaced ([PR 16223](https://github.com/spyder-ide/spyder/pull/16223) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16159](https://github.com/spyder-ide/spyder/issues/16159) - 5.1.1 : omitted indentation when pasting with the editor ([PR 16164](https://github.com/spyder-ide/spyder/pull/16164) by [@impact27](https://github.com/impact27))
* [Issue 15631](https://github.com/spyder-ide/spyder/issues/15631) - Slow response when editing files (after some time) ([PR 16206](https://github.com/spyder-ide/spyder/pull/16206) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15551](https://github.com/spyder-ide/spyder/issues/15551) - Feature Request: Specify a config directory on the command line ([PR 16179](https://github.com/spyder-ide/spyder/pull/16179) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14479](https://github.com/spyder-ide/spyder/issues/14479) - Disabling monitor scale change warning when using two screens ([PR 16317](https://github.com/spyder-ide/spyder/pull/16317) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14268](https://github.com/spyder-ide/spyder/issues/14268) - Highlight instances not shown when scrolling ([PR 16260](https://github.com/spyder-ide/spyder/pull/16260) by [@ccordoba12](https://github.com/ccordoba12))

In this release 14 issues were closed.

### Pull Requests Merged

* [PR 16331](https://github.com/spyder-ide/spyder/pull/16331) - PR: Fix performing app restart when LSP goes down, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16330](https://github.com/spyder-ide/spyder/pull/16330) - PR: Update dependencies for 5.1.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16323](https://github.com/spyder-ide/spyder/pull/16323) - PR: Fix error in runfile/debugfile with IPykernel 6.3.0, by [@ccordoba12](https://github.com/ccordoba12) ([16316](https://github.com/spyder-ide/spyder/issues/16316))
* [PR 16317](https://github.com/spyder-ide/spyder/pull/16317) - PR: Allow to not show again message about DPI screen changes, by [@ccordoba12](https://github.com/ccordoba12) ([14479](https://github.com/spyder-ide/spyder/issues/14479))
* [PR 16311](https://github.com/spyder-ide/spyder/pull/16311) - PR: Avoid overwrite of existing project type, by [@steff456](https://github.com/steff456)
* [PR 16303](https://github.com/spyder-ide/spyder/pull/16303) - PR: Fix error when rendering the Tools menu and Kite is not available, by [@ccordoba12](https://github.com/ccordoba12) ([16287](https://github.com/spyder-ide/spyder/issues/16287))
* [PR 16293](https://github.com/spyder-ide/spyder/pull/16293) - PR: Include platformdirs.macos in macOS app, by [@mrclary](https://github.com/mrclary) ([16292](https://github.com/spyder-ide/spyder/issues/16292))
* [PR 16284](https://github.com/spyder-ide/spyder/pull/16284) - PR: Prevent IPython console actions to be added multiple times to main menus, by [@ccordoba12](https://github.com/ccordoba12) ([16269](https://github.com/spyder-ide/spyder/issues/16269))
* [PR 16277](https://github.com/spyder-ide/spyder/pull/16277) - PR: Shift maximum character edge line to match editor characters, by [@rhkarls](https://github.com/rhkarls) ([16248](https://github.com/spyder-ide/spyder/issues/16248))
* [PR 16276](https://github.com/spyder-ide/spyder/pull/16276) - PR: Prevent slowdowns in the Variable Explorer when Numpy and Pandas are not installed, by [@ccordoba12](https://github.com/ccordoba12) ([16247](https://github.com/spyder-ide/spyder/issues/16247))
* [PR 16264](https://github.com/spyder-ide/spyder/pull/16264) - PR: Center cursor when searching for text (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16263](https://github.com/spyder-ide/spyder/pull/16263) - PR: Avoid freezes when updating symbols and folding, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16261](https://github.com/spyder-ide/spyder/pull/16261) - PR: Create main_widget module for the Outline plugin, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16260](https://github.com/spyder-ide/spyder/pull/16260) - PR: Update decorations whether there are or not underline errors, by [@ccordoba12](https://github.com/ccordoba12) ([14268](https://github.com/spyder-ide/spyder/issues/14268))
* [PR 16255](https://github.com/spyder-ide/spyder/pull/16255) - PR: Improve skipping imported symbols (Outline), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16241](https://github.com/spyder-ide/spyder/pull/16241) - PR: Fix splash screen when restarting Spyder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16240](https://github.com/spyder-ide/spyder/pull/16240) - PR: Use toolbar ids and widget/action ids when adding an item to a toolbar, by [@andfoy](https://github.com/andfoy)
* [PR 16233](https://github.com/spyder-ide/spyder/pull/16233) - PR: Improve splash screen blurriness and add high resolution Windows ico file, by [@isabela-pf](https://github.com/isabela-pf) ([16236](https://github.com/spyder-ide/spyder/issues/16236))
* [PR 16223](https://github.com/spyder-ide/spyder/pull/16223) - PR: Use toPlainText to get the file's text when applying formatting (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16180](https://github.com/spyder-ide/spyder/issues/16180))
* [PR 16214](https://github.com/spyder-ide/spyder/pull/16214) - PR: Solve pasting of one line + newline into the editor, by [@sphh](https://github.com/sphh)
* [PR 16213](https://github.com/spyder-ide/spyder/pull/16213) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 16210](https://github.com/spyder-ide/spyder/pull/16210) - PR:  Change entry name for file completions to 'file' (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16206](https://github.com/spyder-ide/spyder/pull/16206) - PR: Clear code_analysis_underline extra selections before painting new ones (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([15631](https://github.com/spyder-ide/spyder/issues/15631))
* [PR 16205](https://github.com/spyder-ide/spyder/pull/16205) - PR: Use menu and item identifiers to add items to the main menu plugin, by [@andfoy](https://github.com/andfoy)
* [PR 16200](https://github.com/spyder-ide/spyder/pull/16200) - PR: Add PYTHONHOME to shell environment when executing in external terminal from macOS app, by [@mrclary](https://github.com/mrclary) ([16185](https://github.com/spyder-ide/spyder/issues/16185))
* [PR 16195](https://github.com/spyder-ide/spyder/pull/16195) - PR: Simplify updating enabled state of code analysis actions (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16184](https://github.com/spyder-ide/spyder/pull/16184) - PR: Fix double clicks when single-click mode is active, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16182](https://github.com/spyder-ide/spyder/pull/16182) - PR: Some improvements to Projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16179](https://github.com/spyder-ide/spyder/pull/16179) - PR: Allow to set a custom configuration directory through the command line, by [@ccordoba12](https://github.com/ccordoba12) ([15551](https://github.com/spyder-ide/spyder/issues/15551))
* [PR 16176](https://github.com/spyder-ide/spyder/pull/16176) - PR: Skip a flaky test on Linux and mark others as flaky, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16173](https://github.com/spyder-ide/spyder/pull/16173) - PR: Improve running time of slow tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16170](https://github.com/spyder-ide/spyder/pull/16170) - PR: Add tests for external plugins using spyder-boilerplate, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16167](https://github.com/spyder-ide/spyder/pull/16167) - PR: Remove code related to the old way of detecting internal plugins, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16164](https://github.com/spyder-ide/spyder/pull/16164) - PR: Fix pasting code in the Editor, by [@impact27](https://github.com/impact27) ([16159](https://github.com/spyder-ide/spyder/issues/16159))
* [PR 16162](https://github.com/spyder-ide/spyder/pull/16162) - PR: Really fix pasting with tabs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16151](https://github.com/spyder-ide/spyder/pull/16151) - PR: Use running_in_ci instead of checking for the 'CI' env var directly, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15629](https://github.com/spyder-ide/spyder/pull/15629) - PR: Improve how to start Spyder in debug mode and show log in Tools menu, by [@mrclary](https://github.com/mrclary)

In this release 37 pull requests were closed.


----


## Version 5.1.1 (2021-08-04)

### Important fixes
* Fix loading internal plugins, which prevents a crash at startup in Python
  3.8+ and issues with completion and linting in other versions.
* Make functionality related to Jedi work in our Windows installer again.

### Issues Closed

* [Issue 16137](https://github.com/spyder-ide/spyder/issues/16137) - Ctrl+V causes a crash ([PR 16146](https://github.com/spyder-ide/spyder/pull/16146) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16136](https://github.com/spyder-ide/spyder/issues/16136) - Editor and IPythonConsole object has no attribute 'get_description'
 ([PR 16130](https://github.com/spyder-ide/spyder/pull/16130) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16125](https://github.com/spyder-ide/spyder/issues/16125) - Exception while writing pyqt code ([PR 16145](https://github.com/spyder-ide/spyder/pull/16145) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16123](https://github.com/spyder-ide/spyder/issues/16123) - 5.1.0: `black` formatter duplicates part of the last line and breaks any code it formats ([PR 16142](https://github.com/spyder-ide/spyder/pull/16142) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16118](https://github.com/spyder-ide/spyder/issues/16118) - 5.1.0: Outline Pane not loading on Windows installer ([PR 16142](https://github.com/spyder-ide/spyder/pull/16142) by [@dalthviz](https://github.com/dalthviz))
* [Issue 16117](https://github.com/spyder-ide/spyder/issues/16117) - 5.1.0 crashes with KeyError 'preferences' ([PR 16130](https://github.com/spyder-ide/spyder/pull/16130) by [@ccordoba12](https://github.com/ccordoba12))

In this release 6 issues were closed.

### Pull Requests Merged

* [PR 16150](https://github.com/spyder-ide/spyder/pull/16150) - PR: Update dependencies for 5.1.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16146](https://github.com/spyder-ide/spyder/pull/16146) - PR: Solve error when using tabs and pasting code (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16137](https://github.com/spyder-ide/spyder/issues/16137))
* [PR 16145](https://github.com/spyder-ide/spyder/pull/16145) - PR: Improve how we handle responses of completion item resolution (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16125](https://github.com/spyder-ide/spyder/issues/16125))
* [PR 16142](https://github.com/spyder-ide/spyder/pull/16142) - PR: Bump Windows installer assets version, by [@dalthviz](https://github.com/dalthviz) ([16123](https://github.com/spyder-ide/spyder/issues/16123), [16118](https://github.com/spyder-ide/spyder/issues/16118))
* [PR 16130](https://github.com/spyder-ide/spyder/pull/16130) - PR: Fix loading internal plugins and run tests as if the package were installed in our CIs, by [@ccordoba12](https://github.com/ccordoba12) ([16136](https://github.com/spyder-ide/spyder/issues/16136), [16117](https://github.com/spyder-ide/spyder/issues/16117))
* [PR 16121](https://github.com/spyder-ide/spyder/pull/16121) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)

In this release 6 pull requests were closed.


---


## Version 5.1.0 (2021-08-02)

### New features
* New logo, splash screen and design for the "About Spyder" dialog.
* Support Rich and Colorama in the IPython console.
* Pasting code in the Editor and IPython console preserves indentation.

### New API features
* Add a new registration mechanism for plugins that allow bidirectional
  dependencies among them. See
  [this page](https://github.com/spyder-ide/spyder/wiki/New-mechanism-to-register-plugins-in-Spyder-5.1.0)
  for instructions on how to migrate to it.

### Important fixes
* Fix several critical bugs in the Outline pane.
* Restore ability to ignore linting messages with inline comments in the
  Editor. Supported comments include `# noqa` and `# analysis:ignore`.
* Improve code completion performance in the Editor.
* Fix Code analysis pane in the Windows and macOS installers.
* Decrease startup time.
* Support Jedi 0.18 and Parso 0.8

### Issues Closed

* [Issue 16105](https://github.com/spyder-ide/spyder/issues/16105) - Error when copying and pasting into SimpleImputer.fit_transform() ([PR 16112](https://github.com/spyder-ide/spyder/pull/16112) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16079](https://github.com/spyder-ide/spyder/issues/16079) - Don't display hovers on strings, comments or objects without docstrings ([PR 16084](https://github.com/spyder-ide/spyder/pull/16084) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16064](https://github.com/spyder-ide/spyder/issues/16064) - Spyder 5.0.5 hangs when trying to establish a connection to kite.com ([PR 16109](https://github.com/spyder-ide/spyder/pull/16109) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16006](https://github.com/spyder-ide/spyder/issues/16006) - Splash screen can take a lot of space in low resolution screens ([PR 16020](https://github.com/spyder-ide/spyder/pull/16020) by [@juanis2112](https://github.com/juanis2112))
* [Issue 15962](https://github.com/spyder-ide/spyder/issues/15962) - Allow more recent Parso versions ([PR 15878](https://github.com/spyder-ide/spyder/pull/15878) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15960](https://github.com/spyder-ide/spyder/issues/15960) - AttributeError in snippets extension ([PR 16009](https://github.com/spyder-ide/spyder/pull/16009) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15904](https://github.com/spyder-ide/spyder/issues/15904) - Switching to light/dark themes is not working as expected ([PR 15983](https://github.com/spyder-ide/spyder/pull/15983) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15900](https://github.com/spyder-ide/spyder/issues/15900) - Response of LSP Requests results in wrong position in editor ([PR 15903](https://github.com/spyder-ide/spyder/pull/15903) by [@hlouzada](https://github.com/hlouzada))
* [Issue 15885](https://github.com/spyder-ide/spyder/issues/15885) - Pylint package not found with the Syder 5.0.4 Mac installer ([PR 15905](https://github.com/spyder-ide/spyder/pull/15905) by [@mrclary](https://github.com/mrclary))
* [Issue 15847](https://github.com/spyder-ide/spyder/issues/15847) - FileNotFoundError in Online help ([PR 15864](https://github.com/spyder-ide/spyder/pull/15864) by [@Virinas-code](https://github.com/Virinas-code))
* [Issue 15839](https://github.com/spyder-ide/spyder/issues/15839) - Pop-up window "New Spyder version" blocks loading the main window ([PR 15988](https://github.com/spyder-ide/spyder/pull/15988) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15780](https://github.com/spyder-ide/spyder/issues/15780) - %run -d [filename] doesn't stop on breakpoints ([PR 15947](https://github.com/spyder-ide/spyder/pull/15947) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15705](https://github.com/spyder-ide/spyder/issues/15705) - Spyder switches to plot tab when debugging in console ([PR 16052](https://github.com/spyder-ide/spyder/pull/16052) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15698](https://github.com/spyder-ide/spyder/issues/15698) - Fix buttons layout in Numpy and dataframe viewers ([PR 16091](https://github.com/spyder-ide/spyder/pull/16091) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15667](https://github.com/spyder-ide/spyder/issues/15667) - Improve message for "available update" dialog to include link with installers ([PR 16106](https://github.com/spyder-ide/spyder/pull/16106) by [@juanis2112](https://github.com/juanis2112))
* [Issue 15648](https://github.com/spyder-ide/spyder/issues/15648) - Selector for classes and functions not working when file is part of a project ([PR 16111](https://github.com/spyder-ide/spyder/pull/16111) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15638](https://github.com/spyder-ide/spyder/issues/15638) - Error when deleting UTF character ([PR 15805](https://github.com/spyder-ide/spyder/pull/15805) by [@impact27](https://github.com/impact27))
* [Issue 15618](https://github.com/spyder-ide/spyder/issues/15618) - Double pydocstyle errors ([PR 15926](https://github.com/spyder-ide/spyder/pull/15926) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15459](https://github.com/spyder-ide/spyder/issues/15459) - Filter settings are empty by default ([PR 16103](https://github.com/spyder-ide/spyder/pull/16103) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15458](https://github.com/spyder-ide/spyder/issues/15458) - Commit from files pane is not working. ([PR 15895](https://github.com/spyder-ide/spyder/pull/15895) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15452](https://github.com/spyder-ide/spyder/issues/15452) - ModuleNotFoundError when running code analysis on Windows installer ([PR 16053](https://github.com/spyder-ide/spyder/pull/16053) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15400](https://github.com/spyder-ide/spyder/issues/15400) - Help pane not connected to Editor for local packages ([PR 16099](https://github.com/spyder-ide/spyder/pull/16099) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15320](https://github.com/spyder-ide/spyder/issues/15320) - Dataframe viewer cannot show "_" in column names ([PR 16091](https://github.com/spyder-ide/spyder/pull/16091) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15042](https://github.com/spyder-ide/spyder/issues/15042) - Completions extremely slow ([PR 16057](https://github.com/spyder-ide/spyder/pull/16057) by [@andfoy](https://github.com/andfoy))
* [Issue 14917](https://github.com/spyder-ide/spyder/issues/14917) - Buggy Menubar Behavior on macOS ([PR 16114](https://github.com/spyder-ide/spyder/pull/16114) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14871](https://github.com/spyder-ide/spyder/issues/14871) - Outline GUI not working in `__init__.py` of a module ([PR 16111](https://github.com/spyder-ide/spyder/pull/16111) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14787](https://github.com/spyder-ide/spyder/issues/14787) - Editor extraneously reloads files when switching projects ([PR 15681](https://github.com/spyder-ide/spyder/pull/15681) by [@mrclary](https://github.com/mrclary))
* [Issue 13358](https://github.com/spyder-ide/spyder/issues/13358) - Go to definition not working on local packages ([PR 16099](https://github.com/spyder-ide/spyder/pull/16099) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13181](https://github.com/spyder-ide/spyder/issues/13181) - Improve Spyder logo for Spyder 5 ([PR 15829](https://github.com/spyder-ide/spyder/pull/15829) by [@isabela-pf](https://github.com/isabela-pf))
* [Issue 11701](https://github.com/spyder-ide/spyder/issues/11701) - Align indented lines after pasting ([PR 14467](https://github.com/spyder-ide/spyder/pull/14467) by [@impact27](https://github.com/impact27))
* [Issue 11033](https://github.com/spyder-ide/spyder/issues/11033) - How to suppress errors found by pyflakes in Spyder 4 ([PR 15927](https://github.com/spyder-ide/spyder/pull/15927) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 1917](https://github.com/spyder-ide/spyder/issues/1917) - Make Colorama and Rich work in Spyder's console ([PR 16095](https://github.com/spyder-ide/spyder/pull/16095) by [@ccordoba12](https://github.com/ccordoba12))

In this release 32 issues were closed.

### Pull Requests Merged

* [PR 16114](https://github.com/spyder-ide/spyder/pull/16114) - PR: Pre-render menus when main window is visible on macOS, by [@ccordoba12](https://github.com/ccordoba12) ([14917](https://github.com/spyder-ide/spyder/issues/14917))
* [PR 16113](https://github.com/spyder-ide/spyder/pull/16113) - PR: Update dependencies for 5.1.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16112](https://github.com/spyder-ide/spyder/pull/16112) - PR: Catch another error with snippets (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16105](https://github.com/spyder-ide/spyder/issues/16105))
* [PR 16111](https://github.com/spyder-ide/spyder/pull/16111) - PR: Fix several issues with the Outline, by [@ccordoba12](https://github.com/ccordoba12) ([15648](https://github.com/spyder-ide/spyder/issues/15648), [14871](https://github.com/spyder-ide/spyder/issues/14871))
* [PR 16109](https://github.com/spyder-ide/spyder/pull/16109) - PR: Add a timeout when doing a request to Kite url installers, by [@ccordoba12](https://github.com/ccordoba12) ([16064](https://github.com/spyder-ide/spyder/issues/16064))
* [PR 16108](https://github.com/spyder-ide/spyder/pull/16108) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 16107](https://github.com/spyder-ide/spyder/pull/16107) - PR: Update translation strings for 5.1.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16106](https://github.com/spyder-ide/spyder/pull/16106) - PR: Add link to download new installer update in dialog, by [@juanis2112](https://github.com/juanis2112) ([15667](https://github.com/spyder-ide/spyder/issues/15667))
* [PR 16103](https://github.com/spyder-ide/spyder/pull/16103) - PR: Fix setting filters in Files, by [@ccordoba12](https://github.com/ccordoba12) ([15459](https://github.com/spyder-ide/spyder/issues/15459))
* [PR 16102](https://github.com/spyder-ide/spyder/pull/16102) - PR: Make plugins.py a package (API), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16101](https://github.com/spyder-ide/spyder/pull/16101) - PR: Revert changes that avoided to compute stylesheets when importing the stylesheet module, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16099](https://github.com/spyder-ide/spyder/pull/16099) - PR: Make go-to-defintion and hover work for files when no project is active or outside of it (Completions), by [@ccordoba12](https://github.com/ccordoba12) ([15400](https://github.com/spyder-ide/spyder/issues/15400), [13358](https://github.com/spyder-ide/spyder/issues/13358))
* [PR 16095](https://github.com/spyder-ide/spyder/pull/16095) - PR: Support Rich and Colorama in the IPython console, by [@ccordoba12](https://github.com/ccordoba12) ([1917](https://github.com/spyder-ide/spyder/issues/1917))
* [PR 16091](https://github.com/spyder-ide/spyder/pull/16091) - PR: Improve style of editors (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([15698](https://github.com/spyder-ide/spyder/issues/15698), [15320](https://github.com/spyder-ide/spyder/issues/15320))
* [PR 16084](https://github.com/spyder-ide/spyder/pull/16084) - PR: Don't try to display hovers when there's no content to display (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([16079](https://github.com/spyder-ide/spyder/issues/16079))
* [PR 16078](https://github.com/spyder-ide/spyder/pull/16078) - PR: Exclude files in branding from check-manifest, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16066](https://github.com/spyder-ide/spyder/pull/16066) - PR: Fix layout and missing entries in main menus, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16057](https://github.com/spyder-ide/spyder/pull/16057) - PR: Use completionItem/resolve to improve completion performance, by [@andfoy](https://github.com/andfoy) ([15042](https://github.com/spyder-ide/spyder/issues/15042))
* [PR 16054](https://github.com/spyder-ide/spyder/pull/16054) - PR: Fix small error in Parso required version (Dependencies), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16053](https://github.com/spyder-ide/spyder/pull/16053) - PR: Add modified Pylint init file to prevent modifications to sys.path (Windows installers), by [@dalthviz](https://github.com/dalthviz) ([15452](https://github.com/spyder-ide/spyder/issues/15452))
* [PR 16052](https://github.com/spyder-ide/spyder/pull/16052) - PR: Only switch to Plots plugin once per session, by [@ccordoba12](https://github.com/ccordoba12) ([15705](https://github.com/spyder-ide/spyder/issues/15705))
* [PR 16041](https://github.com/spyder-ide/spyder/pull/16041) - PR: Move create_application and create_window to utils (Main window), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16040](https://github.com/spyder-ide/spyder/pull/16040) - PR: Fix getting text with end-of-lines (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16026](https://github.com/spyder-ide/spyder/pull/16026) - PR: Fix failures when building macOS installers, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16020](https://github.com/spyder-ide/spyder/pull/16020) - PR: Change size of splash screen, by [@juanis2112](https://github.com/juanis2112) ([16006](https://github.com/spyder-ide/spyder/issues/16006))
* [PR 16014](https://github.com/spyder-ide/spyder/pull/16014) - PR: Fix resetting variables after clicking on the reset button (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16011](https://github.com/spyder-ide/spyder/pull/16011) - PR: Fix compatibility with pytest-qt >= 4, by [@bnavigator](https://github.com/bnavigator)
* [PR 16009](https://github.com/spyder-ide/spyder/pull/16009) - PR: Catch error in snippets extension (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([15960](https://github.com/spyder-ide/spyder/issues/15960))
* [PR 16007](https://github.com/spyder-ide/spyder/pull/16007) - PR: Fix updated Spyder logos, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 15988](https://github.com/spyder-ide/spyder/pull/15988) - PR: Move check for possible updates after the main window is visible (Application), by [@ccordoba12](https://github.com/ccordoba12) ([15839](https://github.com/spyder-ide/spyder/issues/15839))
* [PR 15983](https://github.com/spyder-ide/spyder/pull/15983) - PR: Fix asking for restart when changing interface theme options (Appearance), by [@ccordoba12](https://github.com/ccordoba12) ([15904](https://github.com/spyder-ide/spyder/issues/15904))
* [PR 15980](https://github.com/spyder-ide/spyder/pull/15980) - PR: Add logos and guidelines outside the application, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 15964](https://github.com/spyder-ide/spyder/pull/15964) - PR: Adjust icon colors for increased contrast, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 15958](https://github.com/spyder-ide/spyder/pull/15958) - PR: Fix tests for IPykernel 6, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15956](https://github.com/spyder-ide/spyder/pull/15956) - PR: Update splash screen with new logo, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 15947](https://github.com/spyder-ide/spyder/pull/15947) - PR: Fix %debug magic, by [@ccordoba12](https://github.com/ccordoba12) ([15780](https://github.com/spyder-ide/spyder/issues/15780))
* [PR 15927](https://github.com/spyder-ide/spyder/pull/15927) - PR: Restore ability to ignore linting messages with inline comments (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([11033](https://github.com/spyder-ide/spyder/issues/11033))
* [PR 15926](https://github.com/spyder-ide/spyder/pull/15926) - PR: Don't add linting messages to block data for cloned editors (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([15618](https://github.com/spyder-ide/spyder/issues/15618))
* [PR 15905](https://github.com/spyder-ide/spyder/pull/15905) - PR: Add pylint to packages option for py2app (macOS installer), by [@mrclary](https://github.com/mrclary) ([15885](https://github.com/spyder-ide/spyder/issues/15885))
* [PR 15903](https://github.com/spyder-ide/spyder/pull/15903) - PR: Fix wrong EOL in LSP requests text, by [@hlouzada](https://github.com/hlouzada) ([15900](https://github.com/spyder-ide/spyder/issues/15900))
* [PR 15895](https://github.com/spyder-ide/spyder/pull/15895) - PR: Fix VCS browse and commit functionality (Files), by [@ccordoba12](https://github.com/ccordoba12) ([15458](https://github.com/spyder-ide/spyder/issues/15458))
* [PR 15887](https://github.com/spyder-ide/spyder/pull/15887) - PR: Make IPython Console widgets and other elements to use the SpyderConfigurationAccessor, by [@dalthviz](https://github.com/dalthviz)
* [PR 15886](https://github.com/spyder-ide/spyder/pull/15886) - PR: Bump minimum setuptools version to 49.6.0 , by [@dalthviz](https://github.com/dalthviz)
* [PR 15880](https://github.com/spyder-ide/spyder/pull/15880) - PR: Bump CONF_VERSION after move to pylsp server (Completions), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15878](https://github.com/spyder-ide/spyder/pull/15878) - PR: Update Jedi and Parso requirements, by [@ccordoba12](https://github.com/ccordoba12) ([15962](https://github.com/spyder-ide/spyder/issues/15962))
* [PR 15864](https://github.com/spyder-ide/spyder/pull/15864) - PR: Fix error in link to css files (Online Help), by [@Virinas-code](https://github.com/Virinas-code) ([15847](https://github.com/spyder-ide/spyder/issues/15847))
* [PR 15857](https://github.com/spyder-ide/spyder/pull/15857) - PR: Improve startup time in several ways, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15829](https://github.com/spyder-ide/spyder/pull/15829) - PR: Update Spyder's logo, by [@isabela-pf](https://github.com/isabela-pf) ([13181](https://github.com/spyder-ide/spyder/issues/13181))
* [PR 15805](https://github.com/spyder-ide/spyder/pull/15805) - PR: Find next character correctly (Editor), by [@impact27](https://github.com/impact27) ([15638](https://github.com/spyder-ide/spyder/issues/15638))
* [PR 15762](https://github.com/spyder-ide/spyder/pull/15762) - PR: Change design of about dialog, by [@juanis2112](https://github.com/juanis2112) ([40](https://github.com/spyder-ide/ux-improvements/issues/40))
* [PR 15760](https://github.com/spyder-ide/spyder/pull/15760) - PR: Initial signal names standardization (IPython Console), by [@dalthviz](https://github.com/dalthviz)
* [PR 15681](https://github.com/spyder-ide/spyder/pull/15681) - PR: Fix extraneous reloading documents on project switching, by [@mrclary](https://github.com/mrclary) ([14787](https://github.com/spyder-ide/spyder/issues/14787))
* [PR 15657](https://github.com/spyder-ide/spyder/pull/15657) - PR: Use community-based python-lsp-server instead of Palantir's python-language-server, by [@andfoy](https://github.com/andfoy)
* [PR 15582](https://github.com/spyder-ide/spyder/pull/15582) - PR: Use a notification-based manager to load and manage plugins during startup, by [@andfoy](https://github.com/andfoy)
* [PR 15488](https://github.com/spyder-ide/spyder/pull/15488) - PR: Make tour a plugin in the new API, by [@juanis2112](https://github.com/juanis2112)
* [PR 15000](https://github.com/spyder-ide/spyder/pull/15000) - PR: Migrate projects to the new API, by [@steff456](https://github.com/steff456)
* [PR 14467](https://github.com/spyder-ide/spyder/pull/14467) - PR: Fix indentation on paste, by [@impact27](https://github.com/impact27) ([11701](https://github.com/spyder-ide/spyder/issues/11701))

In this release 57 pull requests were closed.


----


## Version 5.0.5 (2021-06-23)

### Important fixes
* Catch any error when trying to detect if Kite installers are available.

### Issues Closed

* [Issue 15876](https://github.com/spyder-ide/spyder/issues/15876) - Spyder 5.0.4 crashes with proxy error to kite.com ([PR 15889](https://github.com/spyder-ide/spyder/pull/15889) by [@andfoy](https://github.com/andfoy))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 15916](https://github.com/spyder-ide/spyder/pull/15916) - PR: Add border around WebView widgets, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15889](https://github.com/spyder-ide/spyder/pull/15889) - PR: Prevent connection errors when trying to verify Kite installers, by [@andfoy](https://github.com/andfoy) ([15876](https://github.com/spyder-ide/spyder/issues/15876))

In this release 2 pull requests were closed.


----


## Version 5.0.4 (2021-06-11)

### New API features
* Programmatic addition of new layouts

### Important fixes
* Fix debugger for IPython 7.24.0
* Fix loading complex third-party plugins
* Fix errors when restarting kernels

### Issues Closed

* [Issue 15788](https://github.com/spyder-ide/spyder/issues/15788) - "import sys" doesn't seem to work at console startup ([PR 15801](https://github.com/spyder-ide/spyder/pull/15801) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15768](https://github.com/spyder-ide/spyder/issues/15768) - Logging error after kernel died or is restarted or a log entry is created form the IPython Console ([PR 15777](https://github.com/spyder-ide/spyder/pull/15777) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15738](https://github.com/spyder-ide/spyder/issues/15738) - Debugger broken with IPython 7.24.0 ([PR 15735](https://github.com/spyder-ide/spyder/pull/15735) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15714](https://github.com/spyder-ide/spyder/issues/15714) - Spyder crashes due to uncaught FileNotFoundError on startup ([PR 15715](https://github.com/spyder-ide/spyder/pull/15715) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15712](https://github.com/spyder-ide/spyder/issues/15712) - Crashed while pressing backspace ([PR 15716](https://github.com/spyder-ide/spyder/pull/15716) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15692](https://github.com/spyder-ide/spyder/issues/15692) - PYTHONPATH manager does not work with unicode characters in path  ([PR 15702](https://github.com/spyder-ide/spyder/pull/15702) by [@rhkarls](https://github.com/rhkarls))
* [Issue 15689](https://github.com/spyder-ide/spyder/issues/15689) - Titlebar doesn't use dark mode on macOS ([PR 15690](https://github.com/spyder-ide/spyder/pull/15690) by [@mrclary](https://github.com/mrclary))
* [Issue 15645](https://github.com/spyder-ide/spyder/issues/15645) - AttributeError when closing console ([PR 15680](https://github.com/spyder-ide/spyder/pull/15680) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15498](https://github.com/spyder-ide/spyder/issues/15498) - "Warning, no such comm" shown when restarting the kernel ([PR 15719](https://github.com/spyder-ide/spyder/pull/15719) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15417](https://github.com/spyder-ide/spyder/issues/15417) - UMR message is still printed for the Windows installer ([PR 15766](https://github.com/spyder-ide/spyder/pull/15766) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15313](https://github.com/spyder-ide/spyder/issues/15313) - Right click on editor tabs selects the wrong tab ([PR 15490](https://github.com/spyder-ide/spyder/pull/15490) by [@impact27](https://github.com/impact27))
* [Issue 15163](https://github.com/spyder-ide/spyder/issues/15163) - No QcoreApplication Found - Spyder 5 installation problem  ([PR 15777](https://github.com/spyder-ide/spyder/pull/15777) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14803](https://github.com/spyder-ide/spyder/issues/14803) - RuntimeError when switching projects with watchdog>=2.0.0 ([PR 15676](https://github.com/spyder-ide/spyder/pull/15676) by [@mrclary](https://github.com/mrclary))

In this release 13 issues were closed.

### Pull Requests Merged

* [PR 15837](https://github.com/spyder-ide/spyder/pull/15837) - PR: Update dependencies for 5.0.4, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15828](https://github.com/spyder-ide/spyder/pull/15828) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 15827](https://github.com/spyder-ide/spyder/pull/15827) - PR: Update translation strings, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15809](https://github.com/spyder-ide/spyder/pull/15809) - PR: Display message to explain how to use modules that don't come with our installers, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15801](https://github.com/spyder-ide/spyder/pull/15801) - PR: Sync subrepo with spyder-kernels#299, by [@ccordoba12](https://github.com/ccordoba12) ([15788](https://github.com/spyder-ide/spyder/issues/15788))
* [PR 15782](https://github.com/spyder-ide/spyder/pull/15782) - PR: Add restriction to pytest-qt to be < 4.0, by [@dalthviz](https://github.com/dalthviz)
* [PR 15778](https://github.com/spyder-ide/spyder/pull/15778) - PR: Disable Kite call-to-action and dialog if installers are not available, by [@andfoy](https://github.com/andfoy)
* [PR 15777](https://github.com/spyder-ide/spyder/pull/15777) - PR: Fix some issues with the logging module, by [@ccordoba12](https://github.com/ccordoba12) ([15768](https://github.com/spyder-ide/spyder/issues/15768), [15163](https://github.com/spyder-ide/spyder/issues/15163))
* [PR 15766](https://github.com/spyder-ide/spyder/pull/15766) - PR: Sync subrepo with spyder-kernels#298, by [@ccordoba12](https://github.com/ccordoba12) ([15417](https://github.com/spyder-ide/spyder/issues/15417))
* [PR 15749](https://github.com/spyder-ide/spyder/pull/15749) - PR: Fix unregistering plugins in new API, by [@dalthviz](https://github.com/dalthviz)
* [PR 15739](https://github.com/spyder-ide/spyder/pull/15739) - PR: Install IPython 7.23 until debugger issues are solved (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15735](https://github.com/spyder-ide/spyder/pull/15735) - PR: Sync subrepo with spyder-kernels#297, by [@ccordoba12](https://github.com/ccordoba12) ([15738](https://github.com/spyder-ide/spyder/issues/15738))
* [PR 15719](https://github.com/spyder-ide/spyder/pull/15719) - PR: Avoid showing "No such comm" warning when restarting the kernel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([15498](https://github.com/spyder-ide/spyder/issues/15498))
* [PR 15718](https://github.com/spyder-ide/spyder/pull/15718) - PR: Remove remaining code from the mainwindow (IPython Console), by [@dalthviz](https://github.com/dalthviz)
* [PR 15716](https://github.com/spyder-ide/spyder/pull/15716) - PR: Catch another KeyError when trying to highlight a folding block (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([15712](https://github.com/spyder-ide/spyder/issues/15712))
* [PR 15715](https://github.com/spyder-ide/spyder/pull/15715) - PR: Catch an error when restoring files on Windows (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([15714](https://github.com/spyder-ide/spyder/issues/15714))
* [PR 15702](https://github.com/spyder-ide/spyder/pull/15702) - PR: Force reading of path stored in Spyder configuration folder as utf-8, by [@rhkarls](https://github.com/rhkarls) ([15692](https://github.com/spyder-ide/spyder/issues/15692))
* [PR 15690](https://github.com/spyder-ide/spyder/pull/15690) - PR: Fix dark mode compliance in macOS app, by [@mrclary](https://github.com/mrclary) ([15689](https://github.com/spyder-ide/spyder/issues/15689))
* [PR 15687](https://github.com/spyder-ide/spyder/pull/15687) - PR: Initial reorganizations of IPython Console actions for the mainmenu, by [@dalthviz](https://github.com/dalthviz)
* [PR 15680](https://github.com/spyder-ide/spyder/pull/15680) - PR: Catch an error when shutting down the comm channel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([15645](https://github.com/spyder-ide/spyder/issues/15645))
* [PR 15676](https://github.com/spyder-ide/spyder/pull/15676) - PR: Revert the constraint on Watchdog 2.0, by [@mrclary](https://github.com/mrclary) ([14803](https://github.com/spyder-ide/spyder/issues/14803))
* [PR 15523](https://github.com/spyder-ide/spyder/pull/15523) - PR: Fix loading complex third party plugins, by [@steff456](https://github.com/steff456)
* [PR 15490](https://github.com/spyder-ide/spyder/pull/15490) - PR: Fixes the selected tab when right clicking, by [@impact27](https://github.com/impact27) ([15313](https://github.com/spyder-ide/spyder/issues/15313))
* [PR 15288](https://github.com/spyder-ide/spyder/pull/15288) - PR: Programmatic addition of new layouts and layouts config update, by [@dalthviz](https://github.com/dalthviz)

In this release 24 pull requests were closed.


----


## Version 5.0.3 (2021-05-17)

### Important fixes
* Fix Help pane in the macOS installer.
* Add rtree as a dependency for our pip packages.

### Issues Closed

* [Issue 15609](https://github.com/spyder-ide/spyder/issues/15609) - Error when trying to use help pane on Spyder.dmg 5.0.2  ([PR 15622](https://github.com/spyder-ide/spyder/pull/15622) by [@mrclary](https://github.com/mrclary))
* [Issue 15546](https://github.com/spyder-ide/spyder/issues/15546) - Debugger raises encoding error ([PR 15604](https://github.com/spyder-ide/spyder/pull/15604) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15195](https://github.com/spyder-ide/spyder/issues/15195) - Ctrl+I produces warning with Sphinx 4 ([PR 15622](https://github.com/spyder-ide/spyder/pull/15622) by [@mrclary](https://github.com/mrclary))
* [Issue 14748](https://github.com/spyder-ide/spyder/issues/14748) - Add rtree to our setup.py dependencies ([PR 14496](https://github.com/spyder-ide/spyder/pull/14496) by [@mrclary](https://github.com/mrclary))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 15636](https://github.com/spyder-ide/spyder/pull/15636) - PR: Update dependencies for 5.0.3, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15635](https://github.com/spyder-ide/spyder/pull/15635) - PR: Scroll pager content with keys (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15627](https://github.com/spyder-ide/spyder/pull/15627) - PR: Update Windows assets url, by [@dalthviz](https://github.com/dalthviz)
* [PR 15622](https://github.com/spyder-ide/spyder/pull/15622) - PR: Fix issues related to sphinx >= 4.0 and docutils >= 0.17 in Mac installer, by [@mrclary](https://github.com/mrclary) ([15609](https://github.com/spyder-ide/spyder/issues/15609), [15195](https://github.com/spyder-ide/spyder/issues/15195))
* [PR 15614](https://github.com/spyder-ide/spyder/pull/15614) - PR: Remove rtree wheel from Windows installer extra packages, by [@dalthviz](https://github.com/dalthviz)
* [PR 15604](https://github.com/spyder-ide/spyder/pull/15604) - PR: Sync subrepo with spyder-kernels#291, by [@ccordoba12](https://github.com/ccordoba12) ([15546](https://github.com/spyder-ide/spyder/issues/15546))
* [PR 15595](https://github.com/spyder-ide/spyder/pull/15595) - PR: Move css_path to Appearance config section (IPython Console), by [@dalthviz](https://github.com/dalthviz)
* [PR 14496](https://github.com/spyder-ide/spyder/pull/14496) - PR: Add Rtree to setup.py and update handling it in macOS installer, by [@mrclary](https://github.com/mrclary) ([14748](https://github.com/spyder-ide/spyder/issues/14748))

In this release 8 pull requests were closed.


----


## Version 5.0.2 (2021-05-10)

### Important fixes
* Fix error when restarting kernels.
* Fix outline, folding and go-to-defintion when Kite is installed.
* Make Plots pane show again separate plots generated in different consoles.
* Fix preferences error when following Kite's tutorial.

### Issues Closed

* [Issue 15467](https://github.com/spyder-ide/spyder/issues/15467) - Plots pane keeps coming back ([PR 15483](https://github.com/spyder-ide/spyder/pull/15483) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15420](https://github.com/spyder-ide/spyder/issues/15420) - Improve spyder-kernels installation message ([PR 15379](https://github.com/spyder-ide/spyder/pull/15379) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15411](https://github.com/spyder-ide/spyder/issues/15411) - Figures from different Consoles are not shown ([PR 15431](https://github.com/spyder-ide/spyder/pull/15431) by [@impact27](https://github.com/impact27))
* [Issue 15398](https://github.com/spyder-ide/spyder/issues/15398) - Minor visual glitch when hovering tabs of the Editor. ([PR 15451](https://github.com/spyder-ide/spyder/pull/15451) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 15394](https://github.com/spyder-ide/spyder/issues/15394) - Missing actions in the Edit menu ([PR 15406](https://github.com/spyder-ide/spyder/pull/15406) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15388](https://github.com/spyder-ide/spyder/issues/15388) - Freeze when connecting to remote kernel via SSH with protected key file ([PR 15390](https://github.com/spyder-ide/spyder/pull/15390) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15356](https://github.com/spyder-ide/spyder/issues/15356) - KeyError when restarting kernel on Windows ([PR 15462](https://github.com/spyder-ide/spyder/pull/15462) by [@impact27](https://github.com/impact27))
* [Issue 15350](https://github.com/spyder-ide/spyder/issues/15350) - Set maximum number of entries in Find is not working ([PR 15419](https://github.com/spyder-ide/spyder/pull/15419) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15348](https://github.com/spyder-ide/spyder/issues/15348) - Troubleshoting Guide from issue reporter not working ([PR 15355](https://github.com/spyder-ide/spyder/pull/15355) by [@steff456](https://github.com/steff456))
* [Issue 15345](https://github.com/spyder-ide/spyder/issues/15345) - Exclude patterns in Find are not saved ([PR 15419](https://github.com/spyder-ide/spyder/pull/15419) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15324](https://github.com/spyder-ide/spyder/issues/15324) - TypeError when using kite_tutorial ([PR 15447](https://github.com/spyder-ide/spyder/pull/15447) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15322](https://github.com/spyder-ide/spyder/issues/15322) - Can't launch Spyder if Completions plugin is deactivated ([PR 15354](https://github.com/spyder-ide/spyder/pull/15354) by [@steff456](https://github.com/steff456))
* [Issue 15139](https://github.com/spyder-ide/spyder/issues/15139) - Outline doesn't show anything except the file.  ([PR 15448](https://github.com/spyder-ide/spyder/pull/15448) by [@andfoy](https://github.com/andfoy))
* [Issue 12553](https://github.com/spyder-ide/spyder/issues/12553) - Scrolling down in IPython Console isn't easy during code execution

In this release 14 issues were closed.

### Pull Requests Merged

* [PR 15487](https://github.com/spyder-ide/spyder/pull/15487) - PR: Update dependencies for 5.0.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15483](https://github.com/spyder-ide/spyder/pull/15483) - PR: Only switch to Plots when inline plotting is muted, by [@ccordoba12](https://github.com/ccordoba12) ([15467](https://github.com/spyder-ide/spyder/issues/15467))
* [PR 15468](https://github.com/spyder-ide/spyder/pull/15468) - PR: Pin pyls-spyder version whilst pyls-black is migrated to pylsp, by [@andfoy](https://github.com/andfoy)
* [PR 15462](https://github.com/spyder-ide/spyder/pull/15462) - PR: Fix close comm (IPython console), by [@impact27](https://github.com/impact27) ([15356](https://github.com/spyder-ide/spyder/issues/15356))
* [PR 15451](https://github.com/spyder-ide/spyder/pull/15451) - PR: Fix minor visual glitch when hovering tabs of the Editor, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([15398](https://github.com/spyder-ide/spyder/issues/15398))
* [PR 15448](https://github.com/spyder-ide/spyder/pull/15448) - PR: Fix issues with empty responses for non-aggregated completion requests, by [@andfoy](https://github.com/andfoy) ([15139](https://github.com/spyder-ide/spyder/issues/15139))
* [PR 15447](https://github.com/spyder-ide/spyder/pull/15447) - PR: Fix args/kwargs handling in the call_all_editorstacks signature to update completion related options for the Editor, by [@dalthviz](https://github.com/dalthviz) ([15324](https://github.com/spyder-ide/spyder/issues/15324))
* [PR 15431](https://github.com/spyder-ide/spyder/pull/15431) - PR: Fix showing plots for different consoles in Plots, by [@impact27](https://github.com/impact27) ([15411](https://github.com/spyder-ide/spyder/issues/15411))
* [PR 15426](https://github.com/spyder-ide/spyder/pull/15426) - PR: Put the sys.prefix in the config search path, by [@pelson](https://github.com/pelson)
* [PR 15419](https://github.com/spyder-ide/spyder/pull/15419) - PR: Fix a couple of bugs in Find, by [@ccordoba12](https://github.com/ccordoba12) ([15350](https://github.com/spyder-ide/spyder/issues/15350), [15345](https://github.com/spyder-ide/spyder/issues/15345))
* [PR 15406](https://github.com/spyder-ide/spyder/pull/15406) - PR: Add missing actions in the Edit menu, by [@dalthviz](https://github.com/dalthviz) ([15394](https://github.com/spyder-ide/spyder/issues/15394))
* [PR 15390](https://github.com/spyder-ide/spyder/pull/15390) - PR: Add passphrase to the text expected by ssh tunnels (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([15388](https://github.com/spyder-ide/spyder/issues/15388))
* [PR 15379](https://github.com/spyder-ide/spyder/pull/15379) - PR: Don't report warnings generated by the trailets package as errors, by [@ccordoba12](https://github.com/ccordoba12) ([15420](https://github.com/spyder-ide/spyder/issues/15420))
* [PR 15376](https://github.com/spyder-ide/spyder/pull/15376) - PR: Fix update of plots toggle view and show/hide toolbars actions, by [@dalthviz](https://github.com/dalthviz)
* [PR 15366](https://github.com/spyder-ide/spyder/pull/15366) - PR: Minor layout improvements to the cornet widget of the panes toolbar, by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 15355](https://github.com/spyder-ide/spyder/pull/15355) - PR: Fix broken trobleshooting url, by [@steff456](https://github.com/steff456) ([15348](https://github.com/spyder-ide/spyder/issues/15348))
* [PR 15354](https://github.com/spyder-ide/spyder/pull/15354) - PR: Fix a couple of bugs in the statusbar, by [@steff456](https://github.com/steff456) ([15322](https://github.com/spyder-ide/spyder/issues/15322))
* [PR 15321](https://github.com/spyder-ide/spyder/pull/15321) - PR: Change readme screenshot for Spyder 5, by [@juanis2112](https://github.com/juanis2112)
* [PR 14935](https://github.com/spyder-ide/spyder/pull/14935) - PR: Remove unmaintained pytest-ordering package, by [@bnavigator](https://github.com/bnavigator)

In this release 19 pull requests were closed.


----


## Version 5.0.1 (2021-04-16)

### Important fixes
* Avoid false warning about incorrect spyder-kernels version.
* Fix error when opening a new editor window.
* Fix error when saving layouts.
* Fix several style issues.
* Fix clicking on tracebacks in the IPython console.

### Issues Closed

* [Issue 15177](https://github.com/spyder-ide/spyder/issues/15177) - Spyder fails to launch if completions are disabled ([PR 15194](https://github.com/spyder-ide/spyder/pull/15194) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15176](https://github.com/spyder-ide/spyder/issues/15176) - Spyder 5 requires QtAwesome >1.0.0 ([PR 15178](https://github.com/spyder-ide/spyder/pull/15178) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15166](https://github.com/spyder-ide/spyder/issues/15166) - Can't click on tracebacks in the IPython console and go to the corresponding line in the editor ([PR 15238](https://github.com/spyder-ide/spyder/pull/15238) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15164](https://github.com/spyder-ide/spyder/issues/15164) - Shotcuts not working when pane is maximized ([PR 15172](https://github.com/spyder-ide/spyder/pull/15172) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15148](https://github.com/spyder-ide/spyder/issues/15148) - Hyperlinks need special style (color) to be read in dark theme ([PR 15183](https://github.com/spyder-ide/spyder/pull/15183) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15146](https://github.com/spyder-ide/spyder/issues/15146) - Menu of the Object Explorer window: check boxes are overlapping the text ([PR 15183](https://github.com/spyder-ide/spyder/pull/15183) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15129](https://github.com/spyder-ide/spyder/issues/15129) - Error after saving layouts ([PR 15144](https://github.com/spyder-ide/spyder/pull/15144) by [@dalthviz](https://github.com/dalthviz))
* [Issue 15116](https://github.com/spyder-ide/spyder/issues/15116) - Menu text covered by icon(s) ([PR 15127](https://github.com/spyder-ide/spyder/pull/15127) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15104](https://github.com/spyder-ide/spyder/issues/15104) - Can't open new editor window ([PR 15124](https://github.com/spyder-ide/spyder/pull/15124) by [@andfoy](https://github.com/andfoy))
* [Issue 15098](https://github.com/spyder-ide/spyder/issues/15098) - AttributeError when doing a right-click on a WebView widget ([PR 15120](https://github.com/spyder-ide/spyder/pull/15120) by [@steff456](https://github.com/steff456))
* [Issue 15093](https://github.com/spyder-ide/spyder/issues/15093) - Setuptools warning due to distutils being imported first ([PR 15252](https://github.com/spyder-ide/spyder/pull/15252) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15091](https://github.com/spyder-ide/spyder/issues/15091) - spyder-kernels problem with Spyder 5 ([PR 15100](https://github.com/spyder-ide/spyder/pull/15100) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15090](https://github.com/spyder-ide/spyder/issues/15090) - TypeError when setting Preferences ([PR 15149](https://github.com/spyder-ide/spyder/pull/15149) by [@andfoy](https://github.com/andfoy))

In this release 13 issues were closed.

### Pull Requests Merged

* [PR 15297](https://github.com/spyder-ide/spyder/pull/15297) - PR: Add base plugin actions to validation (to not disable them) - Plots, by [@dalthviz](https://github.com/dalthviz)
* [PR 15272](https://github.com/spyder-ide/spyder/pull/15272) - PR: Correctly update search action's icon in "Find" pane, by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 15261](https://github.com/spyder-ide/spyder/pull/15261) - PR: Update layout setup to discard areas where the base plugin doesn't exist, by [@dalthviz](https://github.com/dalthviz)
* [PR 15259](https://github.com/spyder-ide/spyder/pull/15259) - PR: Enhance statusbar API, by [@steff456](https://github.com/steff456)
* [PR 15252](https://github.com/spyder-ide/spyder/pull/15252) - PR: Remove usage of distutils, by [@ccordoba12](https://github.com/ccordoba12) ([15093](https://github.com/spyder-ide/spyder/issues/15093))
* [PR 15250](https://github.com/spyder-ide/spyder/pull/15250) - PR: Remove most small white dots around toolbuttons in tabwidgets, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15238](https://github.com/spyder-ide/spyder/pull/15238) - PR: Fix traceback links in the IPython console, by [@ccordoba12](https://github.com/ccordoba12) ([15166](https://github.com/spyder-ide/spyder/issues/15166))
* [PR 15237](https://github.com/spyder-ide/spyder/pull/15237) - PR: Fix style of the tabbar scroller buttons, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15194](https://github.com/spyder-ide/spyder/pull/15194) - PR: Handle disabling completions and improve pruning (Solver), by [@dalthviz](https://github.com/dalthviz) ([15177](https://github.com/spyder-ide/spyder/issues/15177))
* [PR 15183](https://github.com/spyder-ide/spyder/pull/15183) - PR: More style fixes, by [@ccordoba12](https://github.com/ccordoba12) ([15148](https://github.com/spyder-ide/spyder/issues/15148), [15146](https://github.com/spyder-ide/spyder/issues/15146))
* [PR 15178](https://github.com/spyder-ide/spyder/pull/15178) - PR: Update QtAwesome requirement, by [@ccordoba12](https://github.com/ccordoba12) ([15176](https://github.com/spyder-ide/spyder/issues/15176))
* [PR 15175](https://github.com/spyder-ide/spyder/pull/15175) - PR: Manage loading external SpyderPluginV2 plugins, by [@steff456](https://github.com/steff456)
* [PR 15172](https://github.com/spyder-ide/spyder/pull/15172) - PR: Add maximize_dockwidget method for old API compatibility (main window), by [@dalthviz](https://github.com/dalthviz) ([15164](https://github.com/spyder-ide/spyder/issues/15164))
* [PR 15150](https://github.com/spyder-ide/spyder/pull/15150) - PR: Use the right args order in get_conf/set_conf (Layout), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15149](https://github.com/spyder-ide/spyder/pull/15149) - PR: Fix some issues when applying Run/Help settings in the Preferences dialog, by [@andfoy](https://github.com/andfoy) ([15090](https://github.com/spyder-ide/spyder/issues/15090))
* [PR 15144](https://github.com/spyder-ide/spyder/pull/15144) - PR: Fix call to plugin method when saving a custom layout, by [@dalthviz](https://github.com/dalthviz) ([15129](https://github.com/spyder-ide/spyder/issues/15129))
* [PR 15131](https://github.com/spyder-ide/spyder/pull/15131) - PR: Fix a crash at startup when switching screens, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15130](https://github.com/spyder-ide/spyder/pull/15130) - PR: Improve the style of tabs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15127](https://github.com/spyder-ide/spyder/pull/15127) - PR: Increase padding in checkboxes for old PyQt versions, by [@ccordoba12](https://github.com/ccordoba12) ([15116](https://github.com/spyder-ide/spyder/issues/15116))
* [PR 15125](https://github.com/spyder-ide/spyder/pull/15125) - PR: Sync spyder-kernels subrepo with the 2.x branch, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15124](https://github.com/spyder-ide/spyder/pull/15124) - PR: Fix OutlineExplorerWidget creation on separate editor window, by [@andfoy](https://github.com/andfoy) ([15104](https://github.com/spyder-ide/spyder/issues/15104))
* [PR 15120](https://github.com/spyder-ide/spyder/pull/15120) - PR: Fix popup error in WebView, by [@steff456](https://github.com/steff456) ([15098](https://github.com/spyder-ide/spyder/issues/15098))
* [PR 15100](https://github.com/spyder-ide/spyder/pull/15100) - PR: Fix error when detecting spyder-kernels version, by [@ccordoba12](https://github.com/ccordoba12) ([15091](https://github.com/spyder-ide/spyder/issues/15091))

In this release 23 pull requests were closed.


----


## Version 5.0.0 (2021-04-02)

### New features
* Improved dark theme based on QDarkstyle 3.0.
* New light theme based on QDarkstyle 3.0.
* New look and feel for toolbars.
* New icon set based on Material Design.
* New API to extend core plugins, with the exception of the Editor, IPython
  console and Projects.
* New plugins to manage menus, toolbars, layouts, shortcuts, preferences and
  status bar.
* New architecture to access and write configuration options.
* New API to declare code completion providers.
* New registries to access actions, tool buttons, toolbars and menus by their
  identifiers.

### Issues Closed

* [Issue 15082](https://github.com/spyder-ide/spyder/issues/15082) - Project menu indicator overlapped by its text, missing icons ([PR 15081](https://github.com/spyder-ide/spyder/pull/15081) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15064](https://github.com/spyder-ide/spyder/issues/15064) - Project recent_files not respected in Spyder 5 ([PR 15065](https://github.com/spyder-ide/spyder/pull/15065) by [@mrclary](https://github.com/mrclary))
* [Issue 15053](https://github.com/spyder-ide/spyder/issues/15053) - qdarkstyle.colorsystem requirement missing ([PR 15054](https://github.com/spyder-ide/spyder/pull/15054) by [@mrclary](https://github.com/mrclary))
* [Issue 15010](https://github.com/spyder-ide/spyder/issues/15010) - Error report dialog pop ups when creating a new console ([PR 15032](https://github.com/spyder-ide/spyder/pull/15032) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14996](https://github.com/spyder-ide/spyder/issues/14996) - Tour Icon not showing ([PR 15052](https://github.com/spyder-ide/spyder/pull/15052) by [@steff456](https://github.com/steff456))
* [Issue 14888](https://github.com/spyder-ide/spyder/issues/14888) - Kite support migration issues ([PR 15012](https://github.com/spyder-ide/spyder/pull/15012) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13629](https://github.com/spyder-ide/spyder/issues/13629) - Layout broken in master branch when using 4.x settings ([PR 13479](https://github.com/spyder-ide/spyder/pull/13479) by [@goanpeca](https://github.com/goanpeca))

In this release 7 issues were closed.

### Pull Requests Merged

* [PR 15087](https://github.com/spyder-ide/spyder/pull/15087) - PR: Increase required spyder-kernels version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15083](https://github.com/spyder-ide/spyder/pull/15083) - PR: Update core dependencies for Spyder 5.0.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15081](https://github.com/spyder-ide/spyder/pull/15081) - PR: Some style fixes, by [@ccordoba12](https://github.com/ccordoba12) ([15082](https://github.com/spyder-ide/spyder/issues/15082))
* [PR 15076](https://github.com/spyder-ide/spyder/pull/15076) - PR: Use group colors for objects in the Variable Explorer, by [@ccordoba12](https://github.com/ccordoba12) ([7](https://github.com/spyder-ide/ux-improvements/issues/7))
* [PR 15072](https://github.com/spyder-ide/spyder/pull/15072) - PR: Add a new light theme for the interface, by [@juanis2112](https://github.com/juanis2112)
* [PR 15067](https://github.com/spyder-ide/spyder/pull/15067) - PR: Fix hover and pressed states of buttons in Tour and Kite dialog, by [@juanis2112](https://github.com/juanis2112)
* [PR 15065](https://github.com/spyder-ide/spyder/pull/15065) - PR: Check for recent_files in project's main configuration section, by [@mrclary](https://github.com/mrclary) ([15064](https://github.com/spyder-ide/spyder/issues/15064))
* [PR 15063](https://github.com/spyder-ide/spyder/pull/15063) - PR: Fix issue with the report dialog that prevented to click on the traceback error, by [@andfoy](https://github.com/andfoy)
* [PR 15062](https://github.com/spyder-ide/spyder/pull/15062) - PR: Prevent completion timeouts when a single slow provider is up, by [@andfoy](https://github.com/andfoy)
* [PR 15060](https://github.com/spyder-ide/spyder/pull/15060) - PR: Send snippets provider completion results to last, by [@andfoy](https://github.com/andfoy)
* [PR 15058](https://github.com/spyder-ide/spyder/pull/15058) - PR: Icon migration updates, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 15054](https://github.com/spyder-ide/spyder/pull/15054) - PR: Use qdarkstyle subrepo in macOS app, by [@mrclary](https://github.com/mrclary) ([15053](https://github.com/spyder-ide/spyder/issues/15053))
* [PR 15052](https://github.com/spyder-ide/spyder/pull/15052) - PR: Fix tour icons, by [@steff456](https://github.com/steff456) ([14996](https://github.com/spyder-ide/spyder/issues/14996))
* [PR 15051](https://github.com/spyder-ide/spyder/pull/15051) - PR: Add option to hide the date column from Projects, by [@steff456](https://github.com/steff456)
* [PR 15050](https://github.com/spyder-ide/spyder/pull/15050) - PR: Prevent setting negative sizes in the Plots pane, by [@steff456](https://github.com/steff456)
* [PR 15049](https://github.com/spyder-ide/spyder/pull/15049) - PR: Set right roles for some actions on macOS menu bar, by [@steff456](https://github.com/steff456)
* [PR 15048](https://github.com/spyder-ide/spyder/pull/15048) - PR: Sync QDarkstyle subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15043](https://github.com/spyder-ide/spyder/pull/15043) - PR: Fix icons in several places, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15040](https://github.com/spyder-ide/spyder/pull/15040) - PR: Remove extra mock package, by [@bnavigator](https://github.com/bnavigator)
* [PR 15038](https://github.com/spyder-ide/spyder/pull/15038) - PR: Move PluginMainContainer and PluginMainWidget to their own modules, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15037](https://github.com/spyder-ide/spyder/pull/15037) - PR: Fix icons for Pylint and Profiler actions in menus, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15036](https://github.com/spyder-ide/spyder/pull/15036) - PR: Fix a segfault with the intro tour, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15034](https://github.com/spyder-ide/spyder/pull/15034) - PR: Fix a segfault in the test suite, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 15032](https://github.com/spyder-ide/spyder/pull/15032) - PR: Fix for search/find close button error (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([15010](https://github.com/spyder-ide/spyder/issues/15010))
* [PR 15029](https://github.com/spyder-ide/spyder/pull/15029) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 15028](https://github.com/spyder-ide/spyder/pull/15028) - PR: Update translation strings, by [@steff456](https://github.com/steff456)
* [PR 15019](https://github.com/spyder-ide/spyder/pull/15019) - PR: Update Windows installer script to support new Spyder internal plugins entrypoints and qdarkstyle, by [@dalthviz](https://github.com/dalthviz)
* [PR 15012](https://github.com/spyder-ide/spyder/pull/15012) - PR: Fix Kite issues for Spyder 5, by [@dalthviz](https://github.com/dalthviz) ([14888](https://github.com/spyder-ide/spyder/issues/14888))
* [PR 15006](https://github.com/spyder-ide/spyder/pull/15006) - PR: Change all icons to Material Design Icons, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 15005](https://github.com/spyder-ide/spyder/pull/15005) - PR: Add a subrepo for QDarkStyle, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14998](https://github.com/spyder-ide/spyder/pull/14998) - PR: Migrate the Outline Explorer to the new API, by [@andfoy](https://github.com/andfoy)
* [PR 14963](https://github.com/spyder-ide/spyder/pull/14963) - PR: Remove "options" variable from some unused places, by [@novaya](https://github.com/novaya)
* [PR 14944](https://github.com/spyder-ide/spyder/pull/14944) - PR: Enhance icon manager, by [@steff456](https://github.com/steff456)
* [PR 14939](https://github.com/spyder-ide/spyder/pull/14939) - PR: Introduce a global action/menu/toolbar/toolbutton registry, by [@andfoy](https://github.com/andfoy)
* [PR 14933](https://github.com/spyder-ide/spyder/pull/14933) - PR: Change margins and sizes of buttons in toolbars, by [@juanis2112](https://github.com/juanis2112)
* [PR 14665](https://github.com/spyder-ide/spyder/pull/14665) - PR: Add palette files with color roles, by [@juanis2112](https://github.com/juanis2112) ([26](https://github.com/spyder-ide/ux-improvements/issues/26), [13](https://github.com/spyder-ide/ux-improvements/issues/13))
* [PR 13479](https://github.com/spyder-ide/spyder/pull/13479) - PR: Move layouts to the new API, by [@goanpeca](https://github.com/goanpeca) ([13629](https://github.com/spyder-ide/spyder/issues/13629))

In this release 37 pull requests were closed.


----


## Version 5.0alpha7 (2021-03-19)

### Important fixes
* This is exactly the same as 5.0alpha6 but avoids reporting an error with
  an incompatible version of spyder-kernels.


----


## Version 5.0alpha6 (2021-03-19)

### Issues Closed

* [Issue 14923](https://github.com/spyder-ide/spyder/issues/14923) - Language server does not start in macOS application (master) ([PR 14930](https://github.com/spyder-ide/spyder/pull/14930) by [@mrclary](https://github.com/mrclary))
* [Issue 12192](https://github.com/spyder-ide/spyder/issues/12192) - Move Completion plugin to use new API ([PR 14314](https://github.com/spyder-ide/spyder/pull/14314) by [@andfoy](https://github.com/andfoy))
* [Issue 12184](https://github.com/spyder-ide/spyder/issues/12184) - Move Variable Explorer plugin to use new API ([PR 14709](https://github.com/spyder-ide/spyder/pull/14709) by [@ccordoba12](https://github.com/ccordoba12))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 14955](https://github.com/spyder-ide/spyder/pull/14955) - PR: Move actions to open preferences and reset to defaults to the Preferences plugin, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14942](https://github.com/spyder-ide/spyder/pull/14942) - PR: Add missing "self" argument in a method, by [@novaya](https://github.com/novaya)
* [PR 14940](https://github.com/spyder-ide/spyder/pull/14940) - PR: Add missing recursive_notification argument to set_option calls in old API preference pages, by [@andfoy](https://github.com/andfoy)
* [PR 14930](https://github.com/spyder-ide/spyder/pull/14930) - PR: Add lsp to spyder.completions entry-points, by [@mrclary](https://github.com/mrclary) ([14923](https://github.com/spyder-ide/spyder/issues/14923))
* [PR 14874](https://github.com/spyder-ide/spyder/pull/14874) - PR: Add external panels API to the editor, by [@steff456](https://github.com/steff456)
* [PR 14872](https://github.com/spyder-ide/spyder/pull/14872) - PR: Add support for custom status bar widgets, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14852](https://github.com/spyder-ide/spyder/pull/14852) - PR: Refactor Spyder configuration system to use an observer pattern, by [@andfoy](https://github.com/andfoy)
* [PR 14831](https://github.com/spyder-ide/spyder/pull/14831) - PR: Fix location of newly created file and directory in Files, by [@novaya](https://github.com/novaya)
* [PR 14810](https://github.com/spyder-ide/spyder/pull/14810) - PR: Panels and extensions cleanup (Editor), by [@steff456](https://github.com/steff456)
* [PR 14709](https://github.com/spyder-ide/spyder/pull/14709) - PR: Migrate Variable Explorer to the new API, by [@ccordoba12](https://github.com/ccordoba12) ([12184](https://github.com/spyder-ide/spyder/issues/12184))
* [PR 14314](https://github.com/spyder-ide/spyder/pull/14314) - PR: Migrate completion plugin to the new API, by [@andfoy](https://github.com/andfoy) ([12192](https://github.com/spyder-ide/spyder/issues/12192))

In this release 11 pull requests were closed.


----


## Version 5.0alpha5 (2021-02-23)

### Pull Requests Merged

* [PR 14796](https://github.com/spyder-ide/spyder/pull/14796) - PR: Fix plugin dependencies solver, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14782](https://github.com/spyder-ide/spyder/pull/14782) - PR: Several fixes to load external plugins, by [@ccordoba12](https://github.com/ccordoba12)

In this release 2 pull requests were closed.


----


## Version 5.0alpha4 (2021-02-14)

### Issues Closed

* [Issue 14661](https://github.com/spyder-ide/spyder/issues/14661) - There's a blank space in the menus in the top in macOS ([PR 14682](https://github.com/spyder-ide/spyder/pull/14682) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14612](https://github.com/spyder-ide/spyder/issues/14612) - View and Help application menus are not being display in master. ([PR 14619](https://github.com/spyder-ide/spyder/pull/14619) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14537](https://github.com/spyder-ide/spyder/issues/14537) - Migrate Spyder preferences dialog to a separate plugin ([PR 14536](https://github.com/spyder-ide/spyder/pull/14536) by [@andfoy](https://github.com/andfoy))
* [Issue 12195](https://github.com/spyder-ide/spyder/issues/12195) - Move Explorer/Projects plugin to use new API ([PR 14596](https://github.com/spyder-ide/spyder/pull/14596) by [@steff456](https://github.com/steff456))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 14737](https://github.com/spyder-ide/spyder/pull/14737) - PR: Update code of conduct with version 2.0 of Contributor Covenant's one, by [@juanis2112](https://github.com/juanis2112)
* [PR 14721](https://github.com/spyder-ide/spyder/pull/14721) - PR: Minor editor refactoring, by [@steff456](https://github.com/steff456)
* [PR 14690](https://github.com/spyder-ide/spyder/pull/14690) - PR: Update the date of copyright notice, by [@storm-sergey](https://github.com/storm-sergey)
* [PR 14682](https://github.com/spyder-ide/spyder/pull/14682) - PR: Add flag to prevent adding initial empty QAction on Mac for non-migrated menus, by [@dalthviz](https://github.com/dalthviz) ([14661](https://github.com/spyder-ide/spyder/issues/14661))
* [PR 14628](https://github.com/spyder-ide/spyder/pull/14628) - PR: Add button to show and hide replace widget from find widget, by [@juanis2112](https://github.com/juanis2112) ([25](https://github.com/spyder-ide/ux-improvements/issues/25))
* [PR 14619](https://github.com/spyder-ide/spyder/pull/14619) - PR: Support dynamic menus on Mac, by [@dalthviz](https://github.com/dalthviz) ([14612](https://github.com/spyder-ide/spyder/issues/14612))
* [PR 14614](https://github.com/spyder-ide/spyder/pull/14614) - PR: Remove secondary toolbars from toolbars in view menu, by [@juanis2112](https://github.com/juanis2112)
* [PR 14596](https://github.com/spyder-ide/spyder/pull/14596) - PR: Migrate Files to the new API, by [@steff456](https://github.com/steff456) ([12195](https://github.com/spyder-ide/spyder/issues/12195))
* [PR 14592](https://github.com/spyder-ide/spyder/pull/14592) - PR: Fix wrong spelled words, by [@freddii](https://github.com/freddii)
* [PR 14586](https://github.com/spyder-ide/spyder/pull/14586) - PR: Add a new Application plugin, by [@dalthviz](https://github.com/dalthviz)
* [PR 14584](https://github.com/spyder-ide/spyder/pull/14584) - PR: Fix spelling mistakes in comments and docstrings, by [@freddii](https://github.com/freddii)
* [PR 14576](https://github.com/spyder-ide/spyder/pull/14576) - PR: Add STIL to the list of supported languages, by [@andfoy](https://github.com/andfoy)
* [PR 14562](https://github.com/spyder-ide/spyder/pull/14562) - PR: Add color system file for new scale of colors in Spyder 5, by [@juanis2112](https://github.com/juanis2112)
* [PR 14536](https://github.com/spyder-ide/spyder/pull/14536) - PR: Migrate Spyder preference dialog to a plugin of the new API, by [@andfoy](https://github.com/andfoy) ([14537](https://github.com/spyder-ide/spyder/issues/14537))
* [PR 14320](https://github.com/spyder-ide/spyder/pull/14320) - PR: Create status bar plugin (New API), by [@ccordoba12](https://github.com/ccordoba12)

In this release 15 pull requests were closed.


----


## Version 5.0alpha3 (2021-01-08)

### Issues Closed

* [Issue 13698](https://github.com/spyder-ide/spyder/issues/13698) - Profiler pane issues and details ([PR 13711](https://github.com/spyder-ide/spyder/pull/13711) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13657](https://github.com/spyder-ide/spyder/issues/13657) - Find pane issues and details ([PR 13675](https://github.com/spyder-ide/spyder/pull/13675) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13103](https://github.com/spyder-ide/spyder/issues/13103) - Move Main Interpreter preferences to new Plugin API ([PR 13104](https://github.com/spyder-ide/spyder/pull/13104) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12183](https://github.com/spyder-ide/spyder/issues/12183) - Move Pylint plugin to use new API ([PR 12160](https://github.com/spyder-ide/spyder/pull/12160) by [@goanpeca](https://github.com/goanpeca))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 14498](https://github.com/spyder-ide/spyder/pull/14498) - PR: Fix two typos in Contributing guide, by [@real-yfprojects](https://github.com/real-yfprojects)
* [PR 14449](https://github.com/spyder-ide/spyder/pull/14449) - PR: Fix wrong import (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14388](https://github.com/spyder-ide/spyder/pull/14388) - PR: Fix changing directory when opening and closing projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14370](https://github.com/spyder-ide/spyder/pull/14370) - PR: Fix some real and some potential bugs, by [@novaya](https://github.com/novaya)
* [PR 14319](https://github.com/spyder-ide/spyder/pull/14319) - PR: Fix typo in variable name, by [@novaya](https://github.com/novaya)
* [PR 14283](https://github.com/spyder-ide/spyder/pull/14283) - PR: Fix wrong import (Code analysis), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13711](https://github.com/spyder-ide/spyder/pull/13711) - PR: Fix some issues with the profiler, by [@goanpeca](https://github.com/goanpeca) ([13698](https://github.com/spyder-ide/spyder/issues/13698))
* [PR 13675](https://github.com/spyder-ide/spyder/pull/13675) - PR: Fix some issues with the Find in files plugin, by [@goanpeca](https://github.com/goanpeca) ([13657](https://github.com/spyder-ide/spyder/issues/13657))
* [PR 13547](https://github.com/spyder-ide/spyder/pull/13547) - PR: Add new toolbar plugin, by [@goanpeca](https://github.com/goanpeca)
* [PR 13542](https://github.com/spyder-ide/spyder/pull/13542) - PR: Create new MainMenu plugin, by [@goanpeca](https://github.com/goanpeca)
* [PR 13104](https://github.com/spyder-ide/spyder/pull/13104) - PR: Migrate Main interpreter to new plugin API, by [@goanpeca](https://github.com/goanpeca) ([13103](https://github.com/spyder-ide/spyder/issues/13103))
* [PR 12160](https://github.com/spyder-ide/spyder/pull/12160) - PR: Move Pylint plugin to new API, by [@goanpeca](https://github.com/goanpeca) ([12183](https://github.com/spyder-ide/spyder/issues/12183))

In this release 12 pull requests were closed.


----


## Version 5.0alpha2 (2020-11-12)

### Issues Closed

* [Issue 13947](https://github.com/spyder-ide/spyder/issues/13947) - Fix import in test_mainwindow after merge of #13828 ([PR 13948](https://github.com/spyder-ide/spyder/pull/13948) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13695](https://github.com/spyder-ide/spyder/issues/13695) - [API] Support adding icons to menus ([PR 13709](https://github.com/spyder-ide/spyder/pull/13709) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13684](https://github.com/spyder-ide/spyder/issues/13684) - Differences in online help pane toolbar ([PR 13686](https://github.com/spyder-ide/spyder/pull/13686) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13683](https://github.com/spyder-ide/spyder/issues/13683) - The icon of internal console settings disappeared  ([PR 13689](https://github.com/spyder-ide/spyder/pull/13689) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13670](https://github.com/spyder-ide/spyder/issues/13670) - Breakpoint's hamburger menu has duplicated options than in context menu ([PR 13672](https://github.com/spyder-ide/spyder/pull/13672) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13665](https://github.com/spyder-ide/spyder/issues/13665) - Spyder crashes with `select all` + `copy all` in the help pane ([PR 13676](https://github.com/spyder-ide/spyder/pull/13676) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13659](https://github.com/spyder-ide/spyder/issues/13659) - Plots pane issues and details ([PR 13677](https://github.com/spyder-ide/spyder/pull/13677) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13524](https://github.com/spyder-ide/spyder/issues/13524) - "Run in current namespace" missing in Spyder 5.0.0a1 ([PR 13528](https://github.com/spyder-ide/spyder/pull/13528) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13422](https://github.com/spyder-ide/spyder/issues/13422) - After new Spyder IDE installation, clicked on popup to read "tutorial" ([PR 13529](https://github.com/spyder-ide/spyder/pull/13529) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13096](https://github.com/spyder-ide/spyder/issues/13096) - Move shortcut standalone preferences page to new plugin with new API ([PR 13097](https://github.com/spyder-ide/spyder/pull/13097) by [@goanpeca](https://github.com/goanpeca))
* [Issue 10722](https://github.com/spyder-ide/spyder/issues/10722) - Move creation of actions and shortcuts to the plugin API ([PR 13097](https://github.com/spyder-ide/spyder/pull/13097) by [@goanpeca](https://github.com/goanpeca))

In this release 11 issues were closed.

### Pull Requests Merged

* [PR 14018](https://github.com/spyder-ide/spyder/pull/14018) - PR: Update script installer to handle python-slugify package, by [@dalthviz](https://github.com/dalthviz)
* [PR 14015](https://github.com/spyder-ide/spyder/pull/14015) - PR: Use our convention for os.path to fix import error (Breakpoints), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13948](https://github.com/spyder-ide/spyder/pull/13948) - PR: Fix EmptyProject test fixture. Remove notify_project_open call, by [@dalthviz](https://github.com/dalthviz) ([13947](https://github.com/spyder-ide/spyder/issues/13947))
* [PR 13904](https://github.com/spyder-ide/spyder/pull/13904) - PR: Add missing instruction to Maintenance guide, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13886](https://github.com/spyder-ide/spyder/pull/13886) - PR: Update duplicate messages after the release of 4.1.5, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13874](https://github.com/spyder-ide/spyder/pull/13874) - PR: Fix loading of external (non dockable) plugins and other fixes, by [@goanpeca](https://github.com/goanpeca)
* [PR 13871](https://github.com/spyder-ide/spyder/pull/13871) - PR: Add some instructions for maintainers, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13709](https://github.com/spyder-ide/spyder/pull/13709) - PR: Add icon to menu creation mixin, by [@goanpeca](https://github.com/goanpeca) ([13695](https://github.com/spyder-ide/spyder/issues/13695))
* [PR 13689](https://github.com/spyder-ide/spyder/pull/13689) - PR: Restore submenu icon on internal console settings, by [@goanpeca](https://github.com/goanpeca) ([13683](https://github.com/spyder-ide/spyder/issues/13683))
* [PR 13686](https://github.com/spyder-ide/spyder/pull/13686) - PR: Update placeholder text in Online Help plugin, by [@goanpeca](https://github.com/goanpeca) ([13684](https://github.com/spyder-ide/spyder/issues/13684))
* [PR 13677](https://github.com/spyder-ide/spyder/pull/13677) - PR: Fix several issues with the plots pane from API migration, by [@goanpeca](https://github.com/goanpeca) ([13659](https://github.com/spyder-ide/spyder/issues/13659))
* [PR 13676](https://github.com/spyder-ide/spyder/pull/13676) - PR: Rename original browser copy action, by [@goanpeca](https://github.com/goanpeca) ([13665](https://github.com/spyder-ide/spyder/issues/13665))
* [PR 13672](https://github.com/spyder-ide/spyder/pull/13672) - PR: Remove actions from breakpoints options menu, by [@goanpeca](https://github.com/goanpeca) ([13670](https://github.com/spyder-ide/spyder/issues/13670))
* [PR 13600](https://github.com/spyder-ide/spyder/pull/13600) - PR:  Refactor the toolbar handling on main widgets, by [@goanpeca](https://github.com/goanpeca)
* [PR 13529](https://github.com/spyder-ide/spyder/pull/13529) - PR: Fix error when showing context menu on Help plugin, by [@goanpeca](https://github.com/goanpeca) ([13422](https://github.com/spyder-ide/spyder/issues/13422))
* [PR 13528](https://github.com/spyder-ide/spyder/pull/13528) - PR: Fix missing Run section on Preferences, by [@goanpeca](https://github.com/goanpeca) ([13524](https://github.com/spyder-ide/spyder/issues/13524))
* [PR 13440](https://github.com/spyder-ide/spyder/pull/13440) - PR: Create a simple code editor and use that for other plugins, by [@goanpeca](https://github.com/goanpeca)
* [PR 13097](https://github.com/spyder-ide/spyder/pull/13097) - PR: Move shortcuts to new API, by [@goanpeca](https://github.com/goanpeca) ([13096](https://github.com/spyder-ide/spyder/issues/13096), [10722](https://github.com/spyder-ide/spyder/issues/10722))

In this release 18 pull requests were closed.


----


## Version 5.0alpha1 (2020-08-04)

### Issues Closed

* [Issue 13471](https://github.com/spyder-ide/spyder/issues/13471) - Recursing problem with new plugin API on master ([PR 13472](https://github.com/spyder-ide/spyder/pull/13472) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13378](https://github.com/spyder-ide/spyder/issues/13378) - Some problems with the Find plugin in master ([PR 13398](https://github.com/spyder-ide/spyder/pull/13398) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13310](https://github.com/spyder-ide/spyder/issues/13310) - Traceback from the Files pane (AttributeError: 'FindInFilesWidget' object has no attribute 'extras_toolbar') ([PR 13316](https://github.com/spyder-ide/spyder/pull/13316) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13142](https://github.com/spyder-ide/spyder/issues/13142) - Spyder prints "code True" in internal console ([PR 13208](https://github.com/spyder-ide/spyder/pull/13208) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13127](https://github.com/spyder-ide/spyder/issues/13127) - All plugins in the new API are shown after startup ([PR 13208](https://github.com/spyder-ide/spyder/pull/13208) by [@goanpeca](https://github.com/goanpeca))
* [Issue 13099](https://github.com/spyder-ide/spyder/issues/13099) - Migrate RunConfig to Plugin with new API ([PR 13100](https://github.com/spyder-ide/spyder/pull/13100) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12938](https://github.com/spyder-ide/spyder/issues/12938) - Add cookicutter handling and UI generation ([PR 12924](https://github.com/spyder-ide/spyder/pull/12924) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12798](https://github.com/spyder-ide/spyder/issues/12798) - Create new Appearance Plugin using new API ([PR 12793](https://github.com/spyder-ide/spyder/pull/12793) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12760](https://github.com/spyder-ide/spyder/issues/12760) - Move Working Directory to new API ([PR 12756](https://github.com/spyder-ide/spyder/pull/12756) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12727](https://github.com/spyder-ide/spyder/issues/12727) - Move Internal Console plugin to new API ([PR 12438](https://github.com/spyder-ide/spyder/pull/12438) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12725](https://github.com/spyder-ide/spyder/issues/12725) - Move collections editor out of Variable Explorer into widgets ([PR 12726](https://github.com/spyder-ide/spyder/pull/12726) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12488](https://github.com/spyder-ide/spyder/issues/12488) - An idea to improve the visual of the 'Lock panes and toolbars' action in the View menu ([PR 12527](https://github.com/spyder-ide/spyder/pull/12527) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 12325](https://github.com/spyder-ide/spyder/issues/12325) - Move Breakpoints plugin to use new API ([PR 12324](https://github.com/spyder-ide/spyder/pull/12324) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12191](https://github.com/spyder-ide/spyder/issues/12191) - Move Profiler plugin to use new API ([PR 12377](https://github.com/spyder-ide/spyder/pull/12377) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12190](https://github.com/spyder-ide/spyder/issues/12190) - Move History plugin to use new API ([PR 12490](https://github.com/spyder-ide/spyder/pull/12490) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12189](https://github.com/spyder-ide/spyder/issues/12189) - Move Find in files plugin to use new API ([PR 12382](https://github.com/spyder-ide/spyder/pull/12382) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12187](https://github.com/spyder-ide/spyder/issues/12187) - Move Online Help plugin to use new API  ([PR 12330](https://github.com/spyder-ide/spyder/pull/12330) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12186](https://github.com/spyder-ide/spyder/issues/12186) - Move Help plugin to use new API ([PR 12338](https://github.com/spyder-ide/spyder/pull/12338) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12182](https://github.com/spyder-ide/spyder/issues/12182) - Move Plots plugin to use new API ([PR 12196](https://github.com/spyder-ide/spyder/pull/12196) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12180](https://github.com/spyder-ide/spyder/issues/12180) - Modernize global plugin API ([PR 11741](https://github.com/spyder-ide/spyder/pull/11741) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12130](https://github.com/spyder-ide/spyder/issues/12130) - Update plots plugin to python 3 ([PR 12131](https://github.com/spyder-ide/spyder/pull/12131) by [@steff456](https://github.com/steff456))
* [Issue 12002](https://github.com/spyder-ide/spyder/issues/12002) - spyder-kernels dependency not correctly detected for dev version ([PR 12017](https://github.com/spyder-ide/spyder/pull/12017) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11839](https://github.com/spyder-ide/spyder/issues/11839) - Move find in files plugin to python3 ([PR 11840](https://github.com/spyder-ide/spyder/pull/11840) by [@steff456](https://github.com/steff456))
* [Issue 11725](https://github.com/spyder-ide/spyder/issues/11725) - Move PyLint plugin to Python 3 ([PR 11816](https://github.com/spyder-ide/spyder/pull/11816) by [@steff456](https://github.com/steff456))
* [Issue 11616](https://github.com/spyder-ide/spyder/issues/11616) - Move breakpoints plugin to python3 only ([PR 11815](https://github.com/spyder-ide/spyder/pull/11815) by [@steff456](https://github.com/steff456))

In this release 25 issues were closed.

### Pull Requests Merged

* [PR 13472](https://github.com/spyder-ide/spyder/pull/13472) - PR: Fix parent of project type, by [@goanpeca](https://github.com/goanpeca) ([13471](https://github.com/spyder-ide/spyder/issues/13471))
* [PR 13460](https://github.com/spyder-ide/spyder/pull/13460) - PR: Use Binder images from our binder-environments repo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13414](https://github.com/spyder-ide/spyder/pull/13414) - PR: Remove duplicate preferences pages, by [@goanpeca](https://github.com/goanpeca)
* [PR 13403](https://github.com/spyder-ide/spyder/pull/13403) - PR: Move completion plugin files to manager plugin and create a completions.manager.api file, by [@goanpeca](https://github.com/goanpeca)
* [PR 13400](https://github.com/spyder-ide/spyder/pull/13400) - PR: Find internal plugins in plugin module for Spyder installs, by [@goanpeca](https://github.com/goanpeca)
* [PR 13398](https://github.com/spyder-ide/spyder/pull/13398) - PR: Add option to disable tooltip on toolbars when creating actions, by [@goanpeca](https://github.com/goanpeca) ([13378](https://github.com/spyder-ide/spyder/issues/13378))
* [PR 13375](https://github.com/spyder-ide/spyder/pull/13375) - PR: Generalize error reporting via signal and simplify widget, by [@goanpeca](https://github.com/goanpeca)
* [PR 13367](https://github.com/spyder-ide/spyder/pull/13367) - PR: Add file hover-go-to relative to project root, by [@goanpeca](https://github.com/goanpeca)
* [PR 13317](https://github.com/spyder-ide/spyder/pull/13317) - PR: Add name validation and status of project methods, by [@goanpeca](https://github.com/goanpeca)
* [PR 13316](https://github.com/spyder-ide/spyder/pull/13316) - PR: Add check for extras_toolbar existence, by [@goanpeca](https://github.com/goanpeca) ([13310](https://github.com/spyder-ide/spyder/issues/13310))
* [PR 13299](https://github.com/spyder-ide/spyder/pull/13299) - PR: Fix project logic to allow for extra dialogs, by [@goanpeca](https://github.com/goanpeca)
* [PR 13290](https://github.com/spyder-ide/spyder/pull/13290) - PR: Display external plugins in the dependencies dialog, by [@goanpeca](https://github.com/goanpeca)
* [PR 13280](https://github.com/spyder-ide/spyder/pull/13280) - PR: Add intermediate Project API while new API migration is finished, by [@goanpeca](https://github.com/goanpeca)
* [PR 13278](https://github.com/spyder-ide/spyder/pull/13278) - PR: Fix toolbar title and tabify of external plugins, by [@goanpeca](https://github.com/goanpeca)
* [PR 13208](https://github.com/spyder-ide/spyder/pull/13208) - PR: Fix visible plugins on restart and online server start, by [@goanpeca](https://github.com/goanpeca) ([13142](https://github.com/spyder-ide/spyder/issues/13142), [13127](https://github.com/spyder-ide/spyder/issues/13127))
* [PR 13186](https://github.com/spyder-ide/spyder/pull/13186) - PR: Fix a wrong import in our tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13151](https://github.com/spyder-ide/spyder/pull/13151) - PR: Fix test_lsp_config_dialog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13143](https://github.com/spyder-ide/spyder/pull/13143) - PR: Fix showing internal errors, by [@impact27](https://github.com/impact27)
* [PR 13122](https://github.com/spyder-ide/spyder/pull/13122) - PR: Fix spelling error in tutorial (Help), by [@scottwedge](https://github.com/scottwedge)
* [PR 13116](https://github.com/spyder-ide/spyder/pull/13116) - PR: Fix rename of CodeEditor kwarg (History), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13100](https://github.com/spyder-ide/spyder/pull/13100) - PR: Migrate RunConfig to Plugin with new API, by [@goanpeca](https://github.com/goanpeca) ([13099](https://github.com/spyder-ide/spyder/issues/13099))
* [PR 13070](https://github.com/spyder-ide/spyder/pull/13070) - WIP: Add ability to hot start some plugins., by [@goanpeca](https://github.com/goanpeca) ([13067](https://github.com/spyder-ide/spyder/issues/13067))
* [PR 12965](https://github.com/spyder-ide/spyder/pull/12965) - PR: Fix reporting internal PyLS errors and generalize reporting error mechanism, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12961](https://github.com/spyder-ide/spyder/pull/12961) - PR: Add job to build docs, by [@goanpeca](https://github.com/goanpeca)
* [PR 12924](https://github.com/spyder-ide/spyder/pull/12924) - PR: Add cookiecutter widget, by [@goanpeca](https://github.com/goanpeca) ([12938](https://github.com/spyder-ide/spyder/issues/12938))
* [PR 12893](https://github.com/spyder-ide/spyder/pull/12893) - PR: Add entry point plugin discovery and add plugin deps solver, by [@goanpeca](https://github.com/goanpeca)
* [PR 12793](https://github.com/spyder-ide/spyder/pull/12793) - PR: Create a new Appearance plugin, by [@goanpeca](https://github.com/goanpeca) ([12798](https://github.com/spyder-ide/spyder/issues/12798))
* [PR 12756](https://github.com/spyder-ide/spyder/pull/12756) - PR: Migrate Working Directory plugin to the new API, by [@goanpeca](https://github.com/goanpeca) ([12760](https://github.com/spyder-ide/spyder/issues/12760))
* [PR 12726](https://github.com/spyder-ide/spyder/pull/12726) - PR: Move collections editor out of the Variable Explorer and into the widgets module, by [@goanpeca](https://github.com/goanpeca) ([12725](https://github.com/spyder-ide/spyder/issues/12725))
* [PR 12669](https://github.com/spyder-ide/spyder/pull/12669) - PR: Update duplicates.yml, by [@goanpeca](https://github.com/goanpeca)
* [PR 12527](https://github.com/spyder-ide/spyder/pull/12527) - PR: Change icon and text of 'Lock Interface Action' when clicked, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([12488](https://github.com/spyder-ide/spyder/issues/12488))
* [PR 12490](https://github.com/spyder-ide/spyder/pull/12490) - PR: Migrate History Plugin to new API, by [@goanpeca](https://github.com/goanpeca) ([12190](https://github.com/spyder-ide/spyder/issues/12190))
* [PR 12438](https://github.com/spyder-ide/spyder/pull/12438) - PR: Migrate Console Plugin to the new API, by [@goanpeca](https://github.com/goanpeca) ([12727](https://github.com/spyder-ide/spyder/issues/12727))
* [PR 12382](https://github.com/spyder-ide/spyder/pull/12382) - PR: Migrate Find in files plugin to new API, by [@goanpeca](https://github.com/goanpeca) ([12189](https://github.com/spyder-ide/spyder/issues/12189))
* [PR 12377](https://github.com/spyder-ide/spyder/pull/12377) - PR: Migrate Profiler to new API, by [@goanpeca](https://github.com/goanpeca) ([12191](https://github.com/spyder-ide/spyder/issues/12191))
* [PR 12338](https://github.com/spyder-ide/spyder/pull/12338) - PR: Migrate Help plugin to new API, by [@goanpeca](https://github.com/goanpeca) ([12186](https://github.com/spyder-ide/spyder/issues/12186))
* [PR 12330](https://github.com/spyder-ide/spyder/pull/12330) - PR: Move Online help to new API , by [@goanpeca](https://github.com/goanpeca) ([12187](https://github.com/spyder-ide/spyder/issues/12187))
* [PR 12324](https://github.com/spyder-ide/spyder/pull/12324) - PR: Move Breakpoints Plugin to new API, by [@goanpeca](https://github.com/goanpeca) ([12325](https://github.com/spyder-ide/spyder/issues/12325))
* [PR 12196](https://github.com/spyder-ide/spyder/pull/12196) - PR: Move Plots to use new Plugin API, by [@goanpeca](https://github.com/goanpeca) ([12182](https://github.com/spyder-ide/spyder/issues/12182))
* [PR 12131](https://github.com/spyder-ide/spyder/pull/12131) - PR: Update plots plugin to Python 3, by [@steff456](https://github.com/steff456) ([12130](https://github.com/spyder-ide/spyder/issues/12130))
* [PR 12017](https://github.com/spyder-ide/spyder/pull/12017) - PR: Update spyder-kernels requirement for Spyder 5, by [@ccordoba12](https://github.com/ccordoba12) ([12002](https://github.com/spyder-ide/spyder/issues/12002))
* [PR 11935](https://github.com/spyder-ide/spyder/pull/11935) - PR: Spelling correction, by [@michelwoo](https://github.com/michelwoo)
* [PR 11840](https://github.com/spyder-ide/spyder/pull/11840) - PR: Update Find plugin to Python 3, by [@steff456](https://github.com/steff456) ([11839](https://github.com/spyder-ide/spyder/issues/11839))
* [PR 11816](https://github.com/spyder-ide/spyder/pull/11816) - PR: Update Pylint plugin to Python 3, by [@steff456](https://github.com/steff456) ([11725](https://github.com/spyder-ide/spyder/issues/11725))
* [PR 11815](https://github.com/spyder-ide/spyder/pull/11815) - PR: Update Breakpoints plugin to Python 3, by [@steff456](https://github.com/steff456) ([11616](https://github.com/spyder-ide/spyder/issues/11616))
* [PR 11741](https://github.com/spyder-ide/spyder/pull/11741) - PR: Create new API for plugins and widgets, by [@goanpeca](https://github.com/goanpeca) ([12180](https://github.com/spyder-ide/spyder/issues/12180))
* [PR 10963](https://github.com/spyder-ide/spyder/pull/10963) - PR: Remove Python 2 and 3.5 from our CIs, by [@ccordoba12](https://github.com/ccordoba12)

In this release 47 pull requests were closed.
