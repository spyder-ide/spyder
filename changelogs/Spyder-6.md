# History of changes for Spyder 6

## Version 6.0.3 (2024/12/10)

### Important fixes

* Restore widget shortcuts to Preferences and allow to change them on the fly.
* Add support for IPython enhanced tracebacks and use the selected color scheme in the editor when showing them.
* Improve the way users can select the interface font in Preferences.
* Activate `Open last closed` shortcut and restore some missing context menu actions in the Editor.
* Fix several issues when getting selections to run them.
* Use the `INSTALLER_UNATTENDED` environment variable to not launch Spyder automatically if installing it in batch/silent mode from the standalone installers.

### API changes

* Add `plugin_name` kwarg to the `register_shortcut_for_widget` method of
  `SpyderShortcutsMixin`.
* The `add_configuration_observer` method was added to `SpyderConfigurationObserver`.
* Add `items_elide_mode` kwarg to the constructors of `SpyderComboBox` and
  `SpyderComboBoxWithIcons`.
* The `sig_item_in_popup_changed` and `sig_popup_is_hidden` signals were added
  to `SpyderComboBox`, `SpyderComboBoxWithIcons` and `SpyderFontComboBox`.

### Issues Closed

* [Issue 23203](https://github.com/spyder-ide/spyder/issues/23203) - Menuinst error related with the reset shortcut
* [Issue 23196](https://github.com/spyder-ide/spyder/issues/23196) - Internal console completions are very difficult to read in dark mode ([PR 23217](https://github.com/spyder-ide/spyder/pull/23217) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23151](https://github.com/spyder-ide/spyder/issues/23151) - Shortcuts don't work for new files in the Editor ([PR 23161](https://github.com/spyder-ide/spyder/pull/23161) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23072](https://github.com/spyder-ide/spyder/issues/23072) - Custom shortcut `Alt+Shift+Return` doesn't work ([PR 23024](https://github.com/spyder-ide/spyder/pull/23024) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23062](https://github.com/spyder-ide/spyder/issues/23062) - `REQUIRED.app` is installed by Spyder macOS installer
* [Issue 23042](https://github.com/spyder-ide/spyder/issues/23042) - Delete folded block erases text on following line ([PR 23044](https://github.com/spyder-ide/spyder/pull/23044) by [@athompson673](https://github.com/athompson673))
* [Issue 22929](https://github.com/spyder-ide/spyder/issues/22929) - RuntimeError when trying to compute the console banner ([PR 22958](https://github.com/spyder-ide/spyder/pull/22958) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22912](https://github.com/spyder-ide/spyder/issues/22912) - Open last closed shortcut (Ctrl+Shift+T) does not work ([PR 22914](https://github.com/spyder-ide/spyder/pull/22914) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 22827](https://github.com/spyder-ide/spyder/issues/22827) - Attempt to add path in `Anaconda3/pkgs` to Pythonpath manager leads to an error ([PR 22850](https://github.com/spyder-ide/spyder/pull/22850) by [@mrclary](https://github.com/mrclary))
* [Issue 22794](https://github.com/spyder-ide/spyder/issues/22794) - Move from using `jupyter-desktop-server` to `jupyter-remote-desktop-proxy` for binder setup ([PR 22881](https://github.com/spyder-ide/spyder/pull/22881) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22741](https://github.com/spyder-ide/spyder/issues/22741) - Spyder restart required after changing some shortcuts in Preferences ([PR 23024](https://github.com/spyder-ide/spyder/pull/23024) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22730](https://github.com/spyder-ide/spyder/issues/22730) - Silent install automatically starts the application in Spyder 6 ([PR 22876](https://github.com/spyder-ide/spyder/pull/22876) by [@mrclary](https://github.com/mrclary))
* [Issue 22683](https://github.com/spyder-ide/spyder/issues/22683) - Restore content of font selection pull-down menu in preferences back to version 5 quality ([PR 22927](https://github.com/spyder-ide/spyder/pull/22927) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22661](https://github.com/spyder-ide/spyder/issues/22661) - Spyder 6 stuck when computing `xHeight` of monospace font ([PR 22826](https://github.com/spyder-ide/spyder/pull/22826) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22649](https://github.com/spyder-ide/spyder/issues/22649) - Global Run preset default values reappear after restart
* [Issue 22637](https://github.com/spyder-ide/spyder/issues/22637) - Run selection is missing from the Editor's context menu in Sypder 6.0 ([PR 22796](https://github.com/spyder-ide/spyder/pull/22796) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22635](https://github.com/spyder-ide/spyder/issues/22635) - AttributeError in tour when Help plugin is not available ([PR 23177](https://github.com/spyder-ide/spyder/pull/23177) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22630](https://github.com/spyder-ide/spyder/issues/22630) - F9 (run selection) fails from .md file ([PR 22820](https://github.com/spyder-ide/spyder/pull/22820) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22607](https://github.com/spyder-ide/spyder/issues/22607) - KeyError problem when running files ([PR 22819](https://github.com/spyder-ide/spyder/pull/22819) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22516](https://github.com/spyder-ide/spyder/issues/22516) - Many shortcuts not showing in Preferences ([PR 23024](https://github.com/spyder-ide/spyder/pull/23024) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22492](https://github.com/spyder-ide/spyder/issues/22492) - Color Scheme Error: `configparser.NoOptionError: No option 'custom-0/normal' in section: 'appearance'` ([PR 23022](https://github.com/spyder-ide/spyder/pull/23022) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22453](https://github.com/spyder-ide/spyder/issues/22453) - Search -> Find text only works for Editor ([PR 23145](https://github.com/spyder-ide/spyder/pull/23145) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22412](https://github.com/spyder-ide/spyder/issues/22412) - Traceback color handling and definition need improvements ([PR 22965](https://github.com/spyder-ide/spyder/pull/22965) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22060](https://github.com/spyder-ide/spyder/issues/22060) - Code highlight removed after run selected or current line ([PR 22940](https://github.com/spyder-ide/spyder/pull/22940) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 1052](https://github.com/spyder-ide/spyder/issues/1052) - Add support for IPython enhanced tracebacks ([PR 22965](https://github.com/spyder-ide/spyder/pull/22965) by [@dalthviz](https://github.com/dalthviz))

In this release 25 issues were closed.

### Pull Requests Merged

* [PR 23235](https://github.com/spyder-ide/spyder/pull/23235) - PR: Minor improvements to `RELEASE.md` release candidate section, by [@dalthviz](https://github.com/dalthviz)
* [PR 23233](https://github.com/spyder-ide/spyder/pull/23233) - PR: Fix error when inserting items in DataFrameEditor (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23217](https://github.com/spyder-ide/spyder/pull/23217) - PR: A couple of fixes for the Internal console, by [@ccordoba12](https://github.com/ccordoba12) ([23196](https://github.com/spyder-ide/spyder/issues/23196))
* [PR 23213](https://github.com/spyder-ide/spyder/pull/23213) - PR: Add constraint for `pyqt5-sip` on Python 3.8 (Dependencies), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23211](https://github.com/spyder-ide/spyder/pull/23211) - PR: Enable/disable the `Configuration per file` action according to the current file run configuration (Run), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23201](https://github.com/spyder-ide/spyder/pull/23201) - PR: Update `spyder-kernels` to 3.0.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 23178](https://github.com/spyder-ide/spyder/pull/23178) - PR: Add release instructions on how to update the Conda-forge `rc` feedstock channel (Installers), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23177](https://github.com/spyder-ide/spyder/pull/23177) - PR: Remove from intro tour steps for unavailable plugins (Tours), by [@ccordoba12](https://github.com/ccordoba12) ([22635](https://github.com/spyder-ide/spyder/issues/22635))
* [PR 23165](https://github.com/spyder-ide/spyder/pull/23165) - PR: UI fixes for the Appearance config page and find/replace widget on Mac , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23161](https://github.com/spyder-ide/spyder/pull/23161) - PR: Register shortcuts for widgets directly (API), by [@ccordoba12](https://github.com/ccordoba12) ([23151](https://github.com/spyder-ide/spyder/issues/23151))
* [PR 23145](https://github.com/spyder-ide/spyder/pull/23145) - PR: Don't register shortcuts for find/replace related actions that go in the Search menu (Editor), by [@dalthviz](https://github.com/dalthviz) ([22453](https://github.com/spyder-ide/spyder/issues/22453))
* [PR 23144](https://github.com/spyder-ide/spyder/pull/23144) - PR: Fix `DeprecationWarning: module 'sre_constants' is deprecated`, by [@athompson673](https://github.com/athompson673)
* [PR 23121](https://github.com/spyder-ide/spyder/pull/23121) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 23120](https://github.com/spyder-ide/spyder/pull/23120) - PR: Update translations for 6.0.3, by [@dalthviz](https://github.com/dalthviz)
* [PR 23069](https://github.com/spyder-ide/spyder/pull/23069) - PR: Fix small error in `get_spyder_conda_channel` (Utils), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23055](https://github.com/spyder-ide/spyder/pull/23055) - PR: Choose Qt binding to install from `SPYDER_QT_BINDING` environment variable, by [@dpizetta](https://github.com/dpizetta)
* [PR 23044](https://github.com/spyder-ide/spyder/pull/23044) - PR: Fix `FoldingPanel._expand_selection` to not select text an extra line below a folded region (Editor), by [@athompson673](https://github.com/athompson673) ([23042](https://github.com/spyder-ide/spyder/issues/23042))
* [PR 23029](https://github.com/spyder-ide/spyder/pull/23029) - PR: Pin Jedi to 0.19.1 for now on Linux (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23024](https://github.com/spyder-ide/spyder/pull/23024) - PR: Restore widget shortcuts to Preferences and allow to change them on the fly (Shortcuts), by [@ccordoba12](https://github.com/ccordoba12) ([23072](https://github.com/spyder-ide/spyder/issues/23072), [22741](https://github.com/spyder-ide/spyder/issues/22741), [22516](https://github.com/spyder-ide/spyder/issues/22516))
* [PR 23022](https://github.com/spyder-ide/spyder/pull/23022) - PR: Handle error when trying to get invalid/unavailable custom syntax highlighting themes (Appearance), by [@dalthviz](https://github.com/dalthviz) ([22492](https://github.com/spyder-ide/spyder/issues/22492))
* [PR 22965](https://github.com/spyder-ide/spyder/pull/22965) - PR: Initial traceback setup to use selected syntax style (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([22412](https://github.com/spyder-ide/spyder/issues/22412), [1052](https://github.com/spyder-ide/spyder/issues/1052))
* [PR 22958](https://github.com/spyder-ide/spyder/pull/22958) - PR: Catch error when trying to compute the console banner (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22929](https://github.com/spyder-ide/spyder/issues/22929))
* [PR 22940](https://github.com/spyder-ide/spyder/pull/22940) - PR: Fix several issues when getting selections to run them (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22060](https://github.com/spyder-ide/spyder/issues/22060))
* [PR 22927](https://github.com/spyder-ide/spyder/pull/22927) - PR: Improve the way users can select the interface font in Preferences (Appearance), by [@ccordoba12](https://github.com/ccordoba12) ([22683](https://github.com/spyder-ide/spyder/issues/22683))
* [PR 22914](https://github.com/spyder-ide/spyder/pull/22914) - PR: Activate `Open last closed` shortcut in `EditorStack` (Editor), by [@jitseniesen](https://github.com/jitseniesen) ([22912](https://github.com/spyder-ide/spyder/issues/22912))
* [PR 22881](https://github.com/spyder-ide/spyder/pull/22881) - PR: Use `jupyter-remote-desktop-proxy` for binder setup (Binder), by [@dalthviz](https://github.com/dalthviz) ([22794](https://github.com/spyder-ide/spyder/issues/22794))
* [PR 22876](https://github.com/spyder-ide/spyder/pull/22876) - PR: Do not launch Spyder if installing in CI or batch/silent mode (Installers), by [@mrclary](https://github.com/mrclary) ([22730](https://github.com/spyder-ide/spyder/issues/22730))
* [PR 22861](https://github.com/spyder-ide/spyder/pull/22861) - PR: Add `overflow: hidden` to body and container in in-app appeal page (Application), by [@conradolandia](https://github.com/conradolandia)
* [PR 22860](https://github.com/spyder-ide/spyder/pull/22860) - PR: Check `spyder-remote-services` version compatibility (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 22850](https://github.com/spyder-ide/spyder/pull/22850) - PR: Fix `UnboundLocalError` when removing and adding paths to Pythonpath Manager, by [@mrclary](https://github.com/mrclary) ([22827](https://github.com/spyder-ide/spyder/issues/22827))
* [PR 22826](https://github.com/spyder-ide/spyder/pull/22826) - PR: Try to set the monospace font size up to six times in `SpyderApplication` (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([22661](https://github.com/spyder-ide/spyder/issues/22661))
* [PR 22820](https://github.com/spyder-ide/spyder/pull/22820) - PR: Register run metadata on renames for supported file extensions (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22630](https://github.com/spyder-ide/spyder/issues/22630))
* [PR 22819](https://github.com/spyder-ide/spyder/pull/22819) - PR: Fix enabled state of Run plugin actions when a file type doesn't have an associated configuration, by [@ccordoba12](https://github.com/ccordoba12) ([22607](https://github.com/spyder-ide/spyder/issues/22607))
* [PR 22796](https://github.com/spyder-ide/spyder/pull/22796) - PR: Restore run actions to the context menu of `CodeEditor` (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22637](https://github.com/spyder-ide/spyder/issues/22637))
* [PR 22791](https://github.com/spyder-ide/spyder/pull/22791) - PR: Run installer build workflow on both master and 6.x weekly (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22696](https://github.com/spyder-ide/spyder/pull/22696) - PR: Update workflows to accommodate GitHub deprecation of macos-12 runners (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22541](https://github.com/spyder-ide/spyder/pull/22541) - PR: Update Python versions used for testing on Windows and Mac (CI), by [@ccordoba12](https://github.com/ccordoba12)

In this release 37 pull requests were closed.

----

## Version 6.0.2 (2024/10/31)

### Important fixes

* Fix plots not being generated with the Matplotlib inline backend.
* Restore missing debugger buttons to the main toolbar.
* Several fixes and improvements to the update detection mechanism.
* Fix SSH tunneling info handling for remote kernels connection and add remote client tests.
* Handle kernel fault file not being available.
* Update QtConsole constraint to 5.6.1 to support ANSI codes that move the cursor.

### API changes

* The `sig_is_rendered` signal was added to `SpyderToolbar`.
* The `add_toolbar` kwarg of the `create_run_button` and `create_run_in_executor_button`
  methods of the Run plugin can now accept a dictionary.

### Issues Closed

* [Issue 22732](https://github.com/spyder-ide/spyder/issues/22732) - return in finally swallows exceptions ([PR 22745](https://github.com/spyder-ide/spyder/pull/22745) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22685](https://github.com/spyder-ide/spyder/issues/22685) - Check update process for 6.0.2 with a rc (6.0.2rc1)
* [Issue 22593](https://github.com/spyder-ide/spyder/issues/22593) - Banner not shown when there are many files open in the Editor at startup ([PR 22594](https://github.com/spyder-ide/spyder/pull/22594) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22584](https://github.com/spyder-ide/spyder/issues/22584) - RuntimeError when setting a layout and the IPython console is undocked ([PR 22595](https://github.com/spyder-ide/spyder/pull/22595) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22574](https://github.com/spyder-ide/spyder/issues/22574) - `SpyderCodeRunner._debugger_exec` error when starting the debugger from Spyder 6.0.1 ([PR 22633](https://github.com/spyder-ide/spyder/pull/22633) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22572](https://github.com/spyder-ide/spyder/issues/22572) - Spyder  encounters an internal problem after declining update to 6.0.1 ([PR 22598](https://github.com/spyder-ide/spyder/pull/22598) by [@mrclary](https://github.com/mrclary))
* [Issue 22566](https://github.com/spyder-ide/spyder/issues/22566) - Standalone installer shows 404 error on spyder-conda-lock.zip ([PR 22598](https://github.com/spyder-ide/spyder/pull/22598) by [@mrclary](https://github.com/mrclary))
* [Issue 22555](https://github.com/spyder-ide/spyder/issues/22555) - Remote spyder kernel not connecting  ([PR 22691](https://github.com/spyder-ide/spyder/pull/22691) by [@hlouzada](https://github.com/hlouzada))
* [Issue 22551](https://github.com/spyder-ide/spyder/issues/22551) - Error message "the system cannot find the path specified" upon trying to start the kernel ([PR 22575](https://github.com/spyder-ide/spyder/pull/22575) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22546](https://github.com/spyder-ide/spyder/issues/22546) - UnicodeDecodeError when changing files with an open project ([PR 22656](https://github.com/spyder-ide/spyder/pull/22656) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22448](https://github.com/spyder-ide/spyder/issues/22448) - TypeError on connecting to spyder-notebook kernel ([PR 22628](https://github.com/spyder-ide/spyder/pull/22628) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22434](https://github.com/spyder-ide/spyder/issues/22434) - Spyder 6: Debugging buttons missing from the main toolbar ([PR 22702](https://github.com/spyder-ide/spyder/pull/22702) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22420](https://github.com/spyder-ide/spyder/issues/22420) - Plots not showing in Spyder 6 using external Python interpreter  ([PR 22664](https://github.com/spyder-ide/spyder/pull/22664) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22407](https://github.com/spyder-ide/spyder/issues/22407) - Update mechanism not working for Spyder 6.0 installed from Fedora distro package ([PR 22631](https://github.com/spyder-ide/spyder/pull/22631) by [@mrclary](https://github.com/mrclary))
* [Issue 6172](https://github.com/spyder-ide/spyder/issues/6172) - TQDM progress bar is not displayed correctly in the console ([PR 22718](https://github.com/spyder-ide/spyder/pull/22718) by [@dalthviz](https://github.com/dalthviz))

In this release 15 issues were closed.

### Pull Requests Merged

* [PR 22785](https://github.com/spyder-ide/spyder/pull/22785) - PR: Improve version update instructions on `RELEASE.md`, by [@dalthviz](https://github.com/dalthviz)
* [PR 22771](https://github.com/spyder-ide/spyder/pull/22771) - PR: Update dev version from alpha to rc, by [@dalthviz](https://github.com/dalthviz)
* [PR 22760](https://github.com/spyder-ide/spyder/pull/22760) - PR: Update core dependencies for 6.0.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 22759](https://github.com/spyder-ide/spyder/pull/22759) - PR: Update `spyder-kernels` to 3.0.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 22757](https://github.com/spyder-ide/spyder/pull/22757) - PR: Mention that we need to publish release candidates for bugfix versions in release instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22753](https://github.com/spyder-ide/spyder/pull/22753) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 22752](https://github.com/spyder-ide/spyder/pull/22752) - PR: Update translations for 6.0.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 22745](https://github.com/spyder-ide/spyder/pull/22745) - PR: Remove unnecessary `return` in a `try/finally` statement (Files), by [@ccordoba12](https://github.com/ccordoba12) ([22732](https://github.com/spyder-ide/spyder/issues/22732))
* [PR 22718](https://github.com/spyder-ide/spyder/pull/22718) - PR: Update QtConsole subrepo to take into account changes to support cursor move actions, by [@dalthviz](https://github.com/dalthviz) ([6172](https://github.com/spyder-ide/spyder/issues/6172))
* [PR 22709](https://github.com/spyder-ide/spyder/pull/22709) - PR: Update installing developer repos to accommodate dist-info, by [@mrclary](https://github.com/mrclary)
* [PR 22702](https://github.com/spyder-ide/spyder/pull/22702) - PR: Restore buttons that control the debugger to the main toolbar, by [@ccordoba12](https://github.com/ccordoba12) ([22434](https://github.com/spyder-ide/spyder/issues/22434))
* [PR 22699](https://github.com/spyder-ide/spyder/pull/22699) - PR: Add `Help Spyder` entry to the Help menu (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22692](https://github.com/spyder-ide/spyder/pull/22692) - PR: Configure `spyder-remote-services` as an external dependency for the remote client tests, by [@hlouzada](https://github.com/hlouzada)
* [PR 22691](https://github.com/spyder-ide/spyder/pull/22691) - PR: Provide username, host and port from hostname info in ssh tunnels, by [@hlouzada](https://github.com/hlouzada) ([22555](https://github.com/spyder-ide/spyder/issues/22555))
* [PR 22668](https://github.com/spyder-ide/spyder/pull/22668) - PR: Don't use hard-coded path to Python in script shebang used to launch Spyder, by [@Flamefire](https://github.com/Flamefire)
* [PR 22664](https://github.com/spyder-ide/spyder/pull/22664) - PR: Manually register the Matplotlib inline backend in case it hasn't, by [@ccordoba12](https://github.com/ccordoba12) ([22420](https://github.com/spyder-ide/spyder/issues/22420))
* [PR 22656](https://github.com/spyder-ide/spyder/pull/22656) - PR: Always use `utf-8` when handling QByteArray data in `ProcessWorker` (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([22546](https://github.com/spyder-ide/spyder/issues/22546))
* [PR 22654](https://github.com/spyder-ide/spyder/pull/22654) - PR: Some small fixes to the Maintenance instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22636](https://github.com/spyder-ide/spyder/pull/22636) - PR: Simplify min/max required versions of spyder-kernels in the stable branch (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22633](https://github.com/spyder-ide/spyder/pull/22633) - PR: Fix debug file and cell buttons in Debugger toolbar, by [@ccordoba12](https://github.com/ccordoba12) ([22574](https://github.com/spyder-ide/spyder/issues/22574))
* [PR 22631](https://github.com/spyder-ide/spyder/pull/22631) - PR: Do not check for updates if Spyder is in a system or managed environment, by [@mrclary](https://github.com/mrclary) ([22407](https://github.com/spyder-ide/spyder/issues/22407))
* [PR 22628](https://github.com/spyder-ide/spyder/pull/22628) - PR: Handle case when kernel fault file doesn't exist and show error with info explaining that no connection was possible (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([22448](https://github.com/spyder-ide/spyder/issues/22448))
* [PR 22621](https://github.com/spyder-ide/spyder/pull/22621) - PR: Fix setting of working directory in Profiler plugin, by [@rear1019](https://github.com/rear1019)
* [PR 22618](https://github.com/spyder-ide/spyder/pull/22618) - PR: Fix `test_copy_paste_autoindent` forcing text over the clipboard to work (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 22598](https://github.com/spyder-ide/spyder/pull/22598) - PR: Check for asset availability when checking for updates, by [@mrclary](https://github.com/mrclary) ([22572](https://github.com/spyder-ide/spyder/issues/22572), [22566](https://github.com/spyder-ide/spyder/issues/22566))
* [PR 22597](https://github.com/spyder-ide/spyder/pull/22597) - PR: Minor updates to the installer, by [@mrclary](https://github.com/mrclary)
* [PR 22595](https://github.com/spyder-ide/spyder/pull/22595) - PR: Dock all undocked plugins before applying a layout, by [@ccordoba12](https://github.com/ccordoba12) ([22584](https://github.com/spyder-ide/spyder/issues/22584))
* [PR 22594](https://github.com/spyder-ide/spyder/pull/22594) - PR: Set shell banner attribute to be the one computed by us (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22593](https://github.com/spyder-ide/spyder/issues/22593))
* [PR 22577](https://github.com/spyder-ide/spyder/pull/22577) - PR: Pin micromamba to the last version before 2.0 to prevent hangs (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22575](https://github.com/spyder-ide/spyder/pull/22575) - PR: Add harmless OpenCL warning to bening errors (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22551](https://github.com/spyder-ide/spyder/issues/22551))
* [PR 22527](https://github.com/spyder-ide/spyder/pull/22527) - PR: Add initial tests for the Remote client plugin, by [@hlouzada](https://github.com/hlouzada)

In this release 31 pull requests were closed.

----

## Version 6.0.1 (2024/09/23)

### Important fixes

* Fix Spyder hanging at startup on Linux when started in a terminal in background mode.
* Fix appeal/sponsor Spyder message being shown at every startup.
* Fix error that prevented mouse clicks in Spyder to work on the Windows Subsystem for Linux.
* Avoid crashes at startup from faulty/outdated external plugins.
* Fix Spyder installer not being able to finish installation due to Start Menu entry error in some Conda installations.
* Fix Spyder installer not installing the right Spyder version (`6.0.0` vs `6.0.0rc2`)
* Fix Binder instance with example workshop project from being non-responsive.
* Fix errors related to unmaximazing panes and layout changes.

### Issues Closed

* [Issue 22514](https://github.com/spyder-ide/spyder/issues/22514) - AttributeError when unmaximizing plugin ([PR 22534](https://github.com/spyder-ide/spyder/pull/22534) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22494](https://github.com/spyder-ide/spyder/issues/22494) - Error while changing the layout and a plugin was closed while undocked ([PR 22502](https://github.com/spyder-ide/spyder/pull/22502) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22466](https://github.com/spyder-ide/spyder/issues/22466) - ndarray of text does not display correctly in variable explorer ([PR 22484](https://github.com/spyder-ide/spyder/pull/22484) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 22457](https://github.com/spyder-ide/spyder/issues/22457) - Help Spyder dialog is shown at every startup ([PR 22476](https://github.com/spyder-ide/spyder/pull/22476) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22454](https://github.com/spyder-ide/spyder/issues/22454) - Support Spyder dialog does not get focus on startup ([PR 22476](https://github.com/spyder-ide/spyder/pull/22476) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22440](https://github.com/spyder-ide/spyder/issues/22440) - IPython console not showing initial banner in Spyder 6 ([PR 22501](https://github.com/spyder-ide/spyder/pull/22501) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22433](https://github.com/spyder-ide/spyder/issues/22433) - Spyder 6 - `%autoreload` magic not loaded by default on Windows ([PR 22438](https://github.com/spyder-ide/spyder/pull/22438) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22432](https://github.com/spyder-ide/spyder/issues/22432) - AttributeError message at start up ([PR 22437](https://github.com/spyder-ide/spyder/pull/22437) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22428](https://github.com/spyder-ide/spyder/issues/22428) - Spyder 6.0 fails to install when creating Start Menu entry
* [Issue 22416](https://github.com/spyder-ide/spyder/issues/22416) - Installers for 6.0.0 release come with 6.0.0rc2 ([PR 22424](https://github.com/spyder-ide/spyder/pull/22424) by [@mrclary](https://github.com/mrclary))
* [Issue 22415](https://github.com/spyder-ide/spyder/issues/22415) - Spyder 6.0 hangs at startup on Linux (proc.communicate never times out) ([PR 22504](https://github.com/spyder-ide/spyder/pull/22504) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22124](https://github.com/spyder-ide/spyder/issues/22124) - Spyder on Binder is non-responsive ([PR 22509](https://github.com/spyder-ide/spyder/pull/22509) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21563](https://github.com/spyder-ide/spyder/issues/21563) - Error while closing project just after Spyder starts ([PR 22490](https://github.com/spyder-ide/spyder/pull/22490) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20851](https://github.com/spyder-ide/spyder/issues/20851) - Spyder under WSL2 loss of mouse click ability (corruption of transient.ini file??) ([PR 22549](https://github.com/spyder-ide/spyder/pull/22549) by [@ccordoba12](https://github.com/ccordoba12))

In this release 14 issues were closed.

### Pull Requests Merged

* [PR 22550](https://github.com/spyder-ide/spyder/pull/22550) - PR: Avoid crashes at startup due to faulty/outdated external plugins, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22549](https://github.com/spyder-ide/spyder/pull/22549) - PR: Prevent storing a negative position when saving the main window settings (Layout), by [@ccordoba12](https://github.com/ccordoba12) ([20851](https://github.com/spyder-ide/spyder/issues/20851))
* [PR 22539](https://github.com/spyder-ide/spyder/pull/22539) - PR: Add step to `RELEASE.md` to update metadata files (`org.spyder_ide.spyder.appdata.xml`), by [@dalthviz](https://github.com/dalthviz)
* [PR 22538](https://github.com/spyder-ide/spyder/pull/22538) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 22534](https://github.com/spyder-ide/spyder/pull/22534) - PR: Prevent error when unmaximizing plugins (Main window), by [@ccordoba12](https://github.com/ccordoba12) ([22514](https://github.com/spyder-ide/spyder/issues/22514))
* [PR 22530](https://github.com/spyder-ide/spyder/pull/22530) - PR: Update translations for 6.0.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 22509](https://github.com/spyder-ide/spyder/pull/22509) - PR: Don't kill kernel process tree when running in Binder (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22124](https://github.com/spyder-ide/spyder/issues/22124))
* [PR 22504](https://github.com/spyder-ide/spyder/pull/22504) - PR: Don't use script to get env vars if Spyder is launched from a terminal (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([22415](https://github.com/spyder-ide/spyder/issues/22415))
* [PR 22502](https://github.com/spyder-ide/spyder/pull/22502) - PR: Reset `undocked before hiding` state of all plugins before applying layout, by [@ccordoba12](https://github.com/ccordoba12) ([22494](https://github.com/spyder-ide/spyder/issues/22494))
* [PR 22501](https://github.com/spyder-ide/spyder/pull/22501) - PR: Show banner when the kernel is ready (IPython console) , by [@ccordoba12](https://github.com/ccordoba12) ([22440](https://github.com/spyder-ide/spyder/issues/22440))
* [PR 22490](https://github.com/spyder-ide/spyder/pull/22490) - PR: Prevent error when updating `sys.path` in consoles (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([21563](https://github.com/spyder-ide/spyder/issues/21563))
* [PR 22484](https://github.com/spyder-ide/spyder/pull/22484) - PR: Change default format in array editor to `''`, by [@jitseniesen](https://github.com/jitseniesen) ([22466](https://github.com/spyder-ide/spyder/issues/22466))
* [PR 22476](https://github.com/spyder-ide/spyder/pull/22476) - PR: Fix issues showing the in-app appeal message, by [@ccordoba12](https://github.com/ccordoba12) ([22457](https://github.com/spyder-ide/spyder/issues/22457), [22454](https://github.com/spyder-ide/spyder/issues/22454))
* [PR 22474](https://github.com/spyder-ide/spyder/pull/22474) - PR: Update org.spyder_ide.spyder.appdata.xml, by [@kevinsmia1939](https://github.com/kevinsmia1939)
* [PR 22468](https://github.com/spyder-ide/spyder/pull/22468) - PR: Fix development version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22459](https://github.com/spyder-ide/spyder/pull/22459) - PR: Update workflows to run in the `6.x` branch (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22442](https://github.com/spyder-ide/spyder/pull/22442) - PR: Update contributing, release and maintenance instructions for backporting, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22438](https://github.com/spyder-ide/spyder/pull/22438) - PR: Enable `autoreload` magic on all operating systems (Config), by [@ccordoba12](https://github.com/ccordoba12) ([22433](https://github.com/spyder-ide/spyder/issues/22433))
* [PR 22437](https://github.com/spyder-ide/spyder/pull/22437) - PR: Fix bug when calling `update_edit_menu` at startup (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22432](https://github.com/spyder-ide/spyder/issues/22432))
* [PR 22424](https://github.com/spyder-ide/spyder/pull/22424) - PR: Prioritize conda-forge channel so that stable releases are pulled above unstable ones (Installers), by [@mrclary](https://github.com/mrclary) ([22416](https://github.com/spyder-ide/spyder/issues/22416))

In this release 20 pull requests were closed.

----

## Version 6.0.0 (2024-09-03)

### New features

* New installers for Windows, Linux and macOS based on Conda and Conda-forge.
  They come up with a more robust update process and are based on Python 3.11.
* Add a Debugger pane to explore the stack frame of the current debugging
  session.
* Add a button to the Debugger pane to pause the current code execution and
  enter the debugger afterwards.
* Add submenu to the `Consoles` menu to start a new console for a specific
  Conda or Pyenv environment.
* Add ability to refresh the open Variable Explorer viewers to reflect the current
  variable value.
* Add initial support to automatically connect to remote servers through SSH
  and run code in them. This functionality can be found in the menu
  `Consoles > New console in remote server`.
* Show plots generated in the Variable Explorer or its viewers in the Plots pane.
* Show Matplotlib backend and Python environment information in the status bar.
* Make kernel restarts be much faster for the current interpreter.
* Add experimental support for Qt 6 and increase minimal required version to
  Qt 5.15.
* Turn `runfile`, `debugfile`, `runcell` and related commands into IPython magics.

### Important fixes

* Environment variables declared in `~/.bashrc` or `~/.zhrc` are detected and
  passed to the IPython console.
* Support all real number dtypes in the dataframe viewer.
* Respect Matplotlib user settings configured outside Spyder.
* Increase DPI of Matplotlib plots so they look better in high resolution screens.
* Allow to copy the absolute and relative paths of the current file to the tabs'
  context menu of the Editor.
* Restore ability to load Hdf5 and Dicom files through the Variable Explorer
  (this was working in Spyder 4 and before).
* Add ability to disable external plugins in `Preferences > Plugins`.
* Use a simpler filesystem watcher in Projects to improve performance.

### UX/UI improvements

* Make Spyder accept Chinese, Korean or Japanese input on Linux by adding
  `fcitx-qt5` as a new dependency (in conda environments only).
* The file switcher can browse and open files present in the current project
  (in conda environments or if the `fzf` package is installed).
* Improve how options are displayed and handled in several Variable Explorer
  viewers.
* The interface font used by the entire application can be configured in
  `Preferences > Appearance`.
* Files can be opened in the editor by pasting their path in the Working
  Directory toolbar.
* Add a new button to the Variable Explorer to indicate when variables are being
  filtered.
* Show intro message for panes that don't display content at startup.

### New, updated and removed plugins

* Add a Switcher plugin for the files and symbols switcher.
* Add a Debugger plugin to centralize all functionality related to debugging.
* Add an External Terminal plugin to execute Python and Bash/Batch/PS1 files on
  a system terminal.
* Generalize the Run plugin to support generic inputs and executors. This allows
  plugins to declare what kind of inputs (i.e. file, cell or selection) they
  can execute and how they will display the result.
* Declare a proper API for the Projects plugin.
* The Editor now uses the API introduced in Spyder 5. That was the last built-in
  plugin that needed to be migrated to it.
* The Breakpoints plugin was removed and its functionality moved to the Debugger
  one.

### New API features

* `SpyderPluginV2.get_description` must be a static method and
  `SpyderPluginV2.get_icon` a class or static method. This is necessary to
  display the list of available plugins in Preferences in a more user-friendly
  way (see PR [PR 21101](https://github.com/spyder-ide/spyder/pull/21101) for
  the details).
* `SpyderPlugin` and `SpyderPluginWidget` are no longer exposed in the public
  API. They will be removed in Spyder 6.1.
* All comboboxes must inherit from `SpyderComboBox` or related subclasses in
  `spyder.api.widgets.comboboxes`. Comboboxes that inherit directly from
  `QComboBox` won't follow Spyder's graphical style.
* All menus must inherit from `SpyderMenu` in `spyder.api.widgets.menus`.
* All dialog button boxes must inherit from `SpyderDialogButtonBox` in
  `spyder.api.widgets.dialogs`.
* Helper classes were added to `spyder.api.fonts` to get and set the fonts used
  in Spyder in different widgets.
* Helper classes were added to `spyder.api.shortcuts` to get and set keyboard
  shortcuts.
* `AsyncDispatcher` was added to `spyder.api.asyncdispatcher` to run asyncio
  code in Spyder. Only Qt signals can be attached to asyncio
  `future.add_done_callback` calls to avoid segfaults.
* `ShellConnectStatusBarWidget` was added to `spyder.api.shellconnect.status`
  to create status bar widgets connected to the current console.

### Issues Closed

* [Issue 22378](https://github.com/spyder-ide/spyder/issues/22378) - Spyder 6.0.0 release ([PR 22401](https://github.com/spyder-ide/spyder/pull/22401) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22374](https://github.com/spyder-ide/spyder/issues/22374) - Check reason why Sphinx upper constraint is needed to make the splash screen work on Windows ([PR 22404](https://github.com/spyder-ide/spyder/pull/22404) by [@mrclary](https://github.com/mrclary))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 22404](https://github.com/spyder-ide/spyder/pull/22404) - PR: Resolve issue where splash screen was incorrectly rendered if conda environment is not activated (Installers), by [@mrclary](https://github.com/mrclary) ([22374](https://github.com/spyder-ide/spyder/issues/22374))
* [PR 22403](https://github.com/spyder-ide/spyder/pull/22403) - PR: Minor fixes to Spyder 6 Changelog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22401](https://github.com/spyder-ide/spyder/pull/22401) - PR: Update core dependencies for 6.0.0, by [@dalthviz](https://github.com/dalthviz) ([22378](https://github.com/spyder-ide/spyder/issues/22378))
* [PR 22399](https://github.com/spyder-ide/spyder/pull/22399) - PR: Fix issue where single-instance mode was not enforced (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22397](https://github.com/spyder-ide/spyder/pull/22397) - PR: Update user-facing Changelog for Spyder 6.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22395](https://github.com/spyder-ide/spyder/pull/22395) - PR: Some last minute fixes before releasing Spyder 6, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22394](https://github.com/spyder-ide/spyder/pull/22394) - PR: Restore `TMPDIR` in the kernel if it's available in the system, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22387](https://github.com/spyder-ide/spyder/pull/22387) - PR: Add in-app appeal message for donations (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22382](https://github.com/spyder-ide/spyder/pull/22382) - PR: Pass `TMPDIR` env var to kernels (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22380](https://github.com/spyder-ide/spyder/pull/22380) - PR: Fix listing envs in the Consoles' environment menu (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22379](https://github.com/spyder-ide/spyder/pull/22379) - PR: Update Qtconsole subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22377](https://github.com/spyder-ide/spyder/pull/22377) - PR: Don't expose `SpyderPlugin` and `SpyderPluginWidget` as part of the public API, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22334](https://github.com/spyder-ide/spyder/pull/22334) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)

In this release 13 pull requests were closed.

----

## Version 6.0rc2 (2024-08-22)

### Issues Closed

* [Issue 22363](https://github.com/spyder-ide/spyder/issues/22363) - Unable to connect via new remote development feature: poetry: command not found ([PR 22368](https://github.com/spyder-ide/spyder/pull/22368) by [@hlouzada](https://github.com/hlouzada))
* [Issue 22353](https://github.com/spyder-ide/spyder/issues/22353) - Splash screen when running from installer shows partially (at least on Windows) ([PR 22370](https://github.com/spyder-ide/spyder/pull/22370) by [@mrclary](https://github.com/mrclary))
* [Issue 22352](https://github.com/spyder-ide/spyder/issues/22352) - Spyder 6.0 rc2 release
* [Issue 22309](https://github.com/spyder-ide/spyder/issues/22309) - Status bar does not show Python version ([PR 22350](https://github.com/spyder-ide/spyder/pull/22350) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22266](https://github.com/spyder-ide/spyder/issues/22266) - Panes options menus not rendering correctly on first trigger  ([PR 22355](https://github.com/spyder-ide/spyder/pull/22355) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22240](https://github.com/spyder-ide/spyder/issues/22240) - Spyder 6.0.0b2 consoles fail to start with micromamba ([PR 22360](https://github.com/spyder-ide/spyder/pull/22360) by [@mrclary](https://github.com/mrclary))
* [Issue 21652](https://github.com/spyder-ide/spyder/issues/21652) - Warnings in the console with the Brain2 library ([PR 22350](https://github.com/spyder-ide/spyder/pull/22350) by [@ccordoba12](https://github.com/ccordoba12))

In this release 7 issues were closed.

### Pull Requests Merged

* [PR 22371](https://github.com/spyder-ide/spyder/pull/22371) - PR: Fix starting kernels for old Conda versions (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22370](https://github.com/spyder-ide/spyder/pull/22370) - PR: Limit sphinx version to `<7.4.0` to prevent bug with splash screen on Windows, by [@mrclary](https://github.com/mrclary) ([22353](https://github.com/spyder-ide/spyder/issues/22353))
* [PR 22368](https://github.com/spyder-ide/spyder/pull/22368) - PR: Update `spyder-remote-services` installation script (Remote client), by [@hlouzada](https://github.com/hlouzada) ([22363](https://github.com/spyder-ide/spyder/issues/22363))
* [PR 22367](https://github.com/spyder-ide/spyder/pull/22367) - PR: Update core dependencies for 6.0.0rc2, by [@dalthviz](https://github.com/dalthviz)
* [PR 22364](https://github.com/spyder-ide/spyder/pull/22364) - PR: Sync the IPython console current env with the one used in the Editor for completions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22362](https://github.com/spyder-ide/spyder/pull/22362) - PR: Update menuinst version for file-type association (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22361](https://github.com/spyder-ide/spyder/pull/22361) - PR: Fix buttons style of the start tour dialog (Tours), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22360](https://github.com/spyder-ide/spyder/pull/22360) - PR: Fix redirection flag for micromamba (IPython console), by [@mrclary](https://github.com/mrclary) ([22240](https://github.com/spyder-ide/spyder/issues/22240))
* [PR 22355](https://github.com/spyder-ide/spyder/pull/22355) - PR: Prevent first time render glitch by calling position logic via a timer in `showEvent` (Menus), by [@dalthviz](https://github.com/dalthviz) ([22266](https://github.com/spyder-ide/spyder/issues/22266))
* [PR 22350](https://github.com/spyder-ide/spyder/pull/22350) - PR: Add statusbar widget to display the env info associated to the current console (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22309](https://github.com/spyder-ide/spyder/issues/22309), [21652](https://github.com/spyder-ide/spyder/issues/21652))
* [PR 22339](https://github.com/spyder-ide/spyder/pull/22339) - PR: Recreate Spyder runtime environment on minor updates (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22338](https://github.com/spyder-ide/spyder/pull/22338) - PR: Ensure "Update Assets" job runs when "Build Subrepos" is skipped, by [@mrclary](https://github.com/mrclary)
* [PR 22303](https://github.com/spyder-ide/spyder/pull/22303) - PR: Update connections dialog size constants, title and icon (Remote Client), by [@dalthviz](https://github.com/dalthviz)

In this release 13 pull requests were closed.

----

## Version 6.0rc1 (2024-08-08)

### Issues Closed

* [Issue 22317](https://github.com/spyder-ide/spyder/issues/22317) - Spyder 6.0 rc1 release ([PR 22336](https://github.com/spyder-ide/spyder/pull/22336) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22181](https://github.com/spyder-ide/spyder/issues/22181) - Warning message on the first console that is open ([PR 22302](https://github.com/spyder-ide/spyder/pull/22302) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22180](https://github.com/spyder-ide/spyder/issues/22180) - Text being cut in the `About` dialog ([PR 22286](https://github.com/spyder-ide/spyder/pull/22286) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22112](https://github.com/spyder-ide/spyder/issues/22112) - `ModuleNotFoundError: No module named 'win32gui'` on the Windows installer
* [Issue 22033](https://github.com/spyder-ide/spyder/issues/22033) - Closing last unfocused document tab causes IndexError ([PR 22292](https://github.com/spyder-ide/spyder/pull/22292) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21959](https://github.com/spyder-ide/spyder/issues/21959) - Do not translate `Commit` in context menu of Files/Projects ([PR 22320](https://github.com/spyder-ide/spyder/pull/22320) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21824](https://github.com/spyder-ide/spyder/issues/21824) - It's not clear what some actions in the new Options menus of Variable Explorer editors do ([PR 22061](https://github.com/spyder-ide/spyder/pull/22061) by [@jitseniesen](https://github.com/jitseniesen))

In this release 7 issues were closed.

### Pull Requests Merged

* [PR 22336](https://github.com/spyder-ide/spyder/pull/22336) - PR: Update core dependencies for 6.0.0 rc1, by [@dalthviz](https://github.com/dalthviz) ([22317](https://github.com/spyder-ide/spyder/issues/22317))
* [PR 22333](https://github.com/spyder-ide/spyder/pull/22333) - PR: Update translations for 6.0.0 (extra strings), by [@dalthviz](https://github.com/dalthviz)
* [PR 22328](https://github.com/spyder-ide/spyder/pull/22328) - PR: Add a widget to show connection logs to `ConnectionDialog` (Remote client), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22327](https://github.com/spyder-ide/spyder/pull/22327) - PR: Fix typo in shebang line in `user-env.sh`, by [@mrclary](https://github.com/mrclary)
* [PR 22320](https://github.com/spyder-ide/spyder/pull/22320) - PR: Improve text of several strings for translation (Files/Projects), by [@ccordoba12](https://github.com/ccordoba12) ([21959](https://github.com/spyder-ide/spyder/issues/21959))
* [PR 22308](https://github.com/spyder-ide/spyder/pull/22308) - PR: Enable showing calltip widget even with signatures without parameters (Editor/Completion), by [@dalthviz](https://github.com/dalthviz)
* [PR 22304](https://github.com/spyder-ide/spyder/pull/22304) - PR: Disable shortcuts for actions in the `View > Panes` menu when not visible (Layout), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22302](https://github.com/spyder-ide/spyder/pull/22302) - PR: Filter unnecessary stream messages in the kernel (IPython console), by [@dalthviz](https://github.com/dalthviz) ([22181](https://github.com/spyder-ide/spyder/issues/22181))
* [PR 22300](https://github.com/spyder-ide/spyder/pull/22300) - PR: Update Spyder installer base environment with conda-lock file, by [@mrclary](https://github.com/mrclary)
* [PR 22293](https://github.com/spyder-ide/spyder/pull/22293) - PR: Fix resetting layout options (Layout), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22292](https://github.com/spyder-ide/spyder/pull/22292) - PR: Update custom button tab index when removing intermediate tabs without changing current selected tab (Widgets), by [@dalthviz](https://github.com/dalthviz) ([22033](https://github.com/spyder-ide/spyder/issues/22033))
* [PR 22291](https://github.com/spyder-ide/spyder/pull/22291) - PR: Revert PR 22269 (Disable signing Mac app), by [@mrclary](https://github.com/mrclary)
* [PR 22290](https://github.com/spyder-ide/spyder/pull/22290) - PR: Always create the local conda channel on CI, even for releases, by [@mrclary](https://github.com/mrclary)
* [PR 22286](https://github.com/spyder-ide/spyder/pull/22286) - PR: Increase about dialog width to prevent cutting text on Windows (Application), by [@dalthviz](https://github.com/dalthviz) ([22180](https://github.com/spyder-ide/spyder/issues/22180))
* [PR 22285](https://github.com/spyder-ide/spyder/pull/22285) - PR: Handle remote connection lost (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 22276](https://github.com/spyder-ide/spyder/pull/22276) - PR: Improve UI of status bar widgets (API/Completions), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22061](https://github.com/spyder-ide/spyder/pull/22061) - PR: New menu item for view options in array and dataframe editors, by [@jitseniesen](https://github.com/jitseniesen) ([21824](https://github.com/spyder-ide/spyder/issues/21824))

In this release 17 pull requests were closed.

----

## Version 6.0beta3 (2024-07-18)

### Issues Closed

* [Issue 22262](https://github.com/spyder-ide/spyder/issues/22262) - Spyder 6.0 beta3 release
* [Issue 22201](https://github.com/spyder-ide/spyder/issues/22201) - Build string in conda package url for Spyder in the conda-lock file release asset does not match conda-forge ([PR 22204](https://github.com/spyder-ide/spyder/pull/22204) by [@mrclary](https://github.com/mrclary))
* [Issue 22194](https://github.com/spyder-ide/spyder/issues/22194) - CommError upon opening existing console ([PR 22231](https://github.com/spyder-ide/spyder/pull/22231) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22179](https://github.com/spyder-ide/spyder/issues/22179) - Kernel is dead message when starting Spyder ([PR 22231](https://github.com/spyder-ide/spyder/pull/22231) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22178](https://github.com/spyder-ide/spyder/issues/22178) - Traceback related to run parameters over CI ([PR 22232](https://github.com/spyder-ide/spyder/pull/22232) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21596](https://github.com/spyder-ide/spyder/issues/21596) - Left pane size changes when starting Spyder ([PR 22232](https://github.com/spyder-ide/spyder/pull/22232) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21590](https://github.com/spyder-ide/spyder/issues/21590) - Profiler pane not showing results ([PR 21713](https://github.com/spyder-ide/spyder/pull/21713) by [@rear1019](https://github.com/rear1019))
* [Issue 21129](https://github.com/spyder-ide/spyder/issues/21129) - Spyder 6.0.0a1 - New line (ctrl-enter) in console runs cell instead ([PR 22230](https://github.com/spyder-ide/spyder/pull/22230) by [@ccordoba12](https://github.com/ccordoba12))

In this release 8 issues were closed.

### Pull Requests Merged

* [PR 22269](https://github.com/spyder-ide/spyder/pull/22269) - PR: Temporarily suspend notarizing the macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 22253](https://github.com/spyder-ide/spyder/pull/22253) - PR: Update conda-lock for change in release workflow, by [@mrclary](https://github.com/mrclary)
* [PR 22243](https://github.com/spyder-ide/spyder/pull/22243) - PR: Add missing space over masked label text (Variable Explorer - `ArrayEditor`), by [@dalthviz](https://github.com/dalthviz)
* [PR 22234](https://github.com/spyder-ide/spyder/pull/22234) - PR: Improve Switcher UI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22232](https://github.com/spyder-ide/spyder/pull/22232) - PR: Tabify Outline next to Projects in default layout and other layout improvements and fixes, by [@ccordoba12](https://github.com/ccordoba12) ([22178](https://github.com/spyder-ide/spyder/issues/22178), [21596](https://github.com/spyder-ide/spyder/issues/21596))
* [PR 22231](https://github.com/spyder-ide/spyder/pull/22231) - PR: Fix errors when getting Matplotlib backend in the kernel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22194](https://github.com/spyder-ide/spyder/issues/22194), [22179](https://github.com/spyder-ide/spyder/issues/22179))
* [PR 22230](https://github.com/spyder-ide/spyder/pull/22230) - PR: Fix shortcuts for several Run and Debugger actions, by [@ccordoba12](https://github.com/ccordoba12) ([21129](https://github.com/spyder-ide/spyder/issues/21129))
* [PR 22228](https://github.com/spyder-ide/spyder/pull/22228) - PR: Minor UI improvements to the Run entry in Preferences, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22223](https://github.com/spyder-ide/spyder/pull/22223) - PR: Fix Windows tunneling error when connecting to kernels (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 22204](https://github.com/spyder-ide/spyder/pull/22204) - PR: Fix issues with installers discovered after 6.0.0b2 was released, by [@mrclary](https://github.com/mrclary) ([22201](https://github.com/spyder-ide/spyder/issues/22201))
* [PR 22202](https://github.com/spyder-ide/spyder/pull/22202) - PR: Fix issue where macOS installer update fails to launch Spyder, by [@mrclary](https://github.com/mrclary)
* [PR 22200](https://github.com/spyder-ide/spyder/pull/22200) - PR: Improve implementation and UI of console envs menu (IPython console/Main interpreter) , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22197](https://github.com/spyder-ide/spyder/pull/22197) - PR: Address small PySide2 compatibility issues, by [@hmaarrfk](https://github.com/hmaarrfk)
* [PR 22196](https://github.com/spyder-ide/spyder/pull/22196) - PR: Make QtWebEngine optional, by [@hmaarrfk](https://github.com/hmaarrfk)
* [PR 22185](https://github.com/spyder-ide/spyder/pull/22185) - PR: Update translations for 6.0.0 , by [@dalthviz](https://github.com/dalthviz)
* [PR 22183](https://github.com/spyder-ide/spyder/pull/22183) - PR: Update `README`, `RELEASE` and `Announcements` files, by [@dalthviz](https://github.com/dalthviz)
* [PR 21713](https://github.com/spyder-ide/spyder/pull/21713) - PR: Fix profiling results being hidden (Profiler), by [@rear1019](https://github.com/rear1019) ([21590](https://github.com/spyder-ide/spyder/issues/21590))

In this release 17 pull requests were closed.

----

## Version 6.0beta2 (2024-06-19)

### Issues Closed

* [Issue 22176](https://github.com/spyder-ide/spyder/issues/22176) - Spyder 6.0 beta2 release  ([PR 22177](https://github.com/spyder-ide/spyder/pull/22177) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22070](https://github.com/spyder-ide/spyder/issues/22070) - Snapping Spyder 6 while `Show breakpoints` is active is broken ([PR 22163](https://github.com/spyder-ide/spyder/pull/22163) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22034](https://github.com/spyder-ide/spyder/issues/22034) - IPython console Matplotlib rc parameters are inconsistent when switching backends ([PR 22088](https://github.com/spyder-ide/spyder/pull/22088) by [@mrclary](https://github.com/mrclary))
* [Issue 22030](https://github.com/spyder-ide/spyder/issues/22030) - Issue reporter submit to Github results in 403 error ([PR 22108](https://github.com/spyder-ide/spyder/pull/22108) by [@mrclary](https://github.com/mrclary))
* [Issue 21878](https://github.com/spyder-ide/spyder/issues/21878) - KeyError when changing run options in 6.0.0a4 ([PR 22141](https://github.com/spyder-ide/spyder/pull/22141) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21771](https://github.com/spyder-ide/spyder/issues/21771) - Adding "User environment variables in Windows registry" ([PR 22075](https://github.com/spyder-ide/spyder/pull/22075) by [@mrclary](https://github.com/mrclary))
* [Issue 20700](https://github.com/spyder-ide/spyder/issues/20700) - Run settings can not be changed in master ([PR 22141](https://github.com/spyder-ide/spyder/pull/22141) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20569](https://github.com/spyder-ide/spyder/issues/20569) - Run after closing  all files ([PR 22141](https://github.com/spyder-ide/spyder/pull/22141) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16265](https://github.com/spyder-ide/spyder/issues/16265) - Outline pane is automatically shown when editor is maximized ([PR 19784](https://github.com/spyder-ide/spyder/pull/19784) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 10932](https://github.com/spyder-ide/spyder/issues/10932) - Spyder is ignoring matplotlib user settings ([PR 22088](https://github.com/spyder-ide/spyder/pull/22088) by [@mrclary](https://github.com/mrclary))

In this release 10 issues were closed.

### Pull Requests Merged

* [PR 22177](https://github.com/spyder-ide/spyder/pull/22177) - PR: Update core dependencies for 6.0.0 beta2, by [@dalthviz](https://github.com/dalthviz) ([22176](https://github.com/spyder-ide/spyder/issues/22176))
* [PR 22163](https://github.com/spyder-ide/spyder/pull/22163) - PR: Improve UI/UX of the Debugger pane, by [@ccordoba12](https://github.com/ccordoba12) ([22070](https://github.com/spyder-ide/spyder/issues/22070))
* [PR 22155](https://github.com/spyder-ide/spyder/pull/22155) - PR: Use `jupyter_server` instead of `jupyterhub` for remote client plugin, by [@hlouzada](https://github.com/hlouzada)
* [PR 22143](https://github.com/spyder-ide/spyder/pull/22143) - PR: Add new icons to be used in the Debugger toolbar, by [@conradolandia](https://github.com/conradolandia)
* [PR 22141](https://github.com/spyder-ide/spyder/pull/22141) - PR: Improve UI/UX of the Run plugin configuration widgets, by [@ccordoba12](https://github.com/ccordoba12) ([21878](https://github.com/spyder-ide/spyder/issues/21878), [20700](https://github.com/spyder-ide/spyder/issues/20700), [20569](https://github.com/spyder-ide/spyder/issues/20569))
* [PR 22137](https://github.com/spyder-ide/spyder/pull/22137) - PR: Fix conflict between AsyncDispatcher and `run_sync` function of `jupyter_core`, by [@hlouzada](https://github.com/hlouzada)
* [PR 22120](https://github.com/spyder-ide/spyder/pull/22120) - PR: Enable comms to work across different Python versions (IPython console), by [@impact27](https://github.com/impact27)
* [PR 22118](https://github.com/spyder-ide/spyder/pull/22118) - PR: Use `GITHUB_TOKEN` to make authorized user requests against GitHub (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22110](https://github.com/spyder-ide/spyder/pull/22110) - PR: Adjust emblems for Projects menu icons, by [@conradolandia](https://github.com/conradolandia)
* [PR 22108](https://github.com/spyder-ide/spyder/pull/22108) - PR: Replace `github.py` with `pygithub` package, by [@mrclary](https://github.com/mrclary) ([22030](https://github.com/spyder-ide/spyder/issues/22030))
* [PR 22103](https://github.com/spyder-ide/spyder/pull/22103) - PR: Update macOS from 11 to 12 in installer workflow, by [@mrclary](https://github.com/mrclary)
* [PR 22089](https://github.com/spyder-ide/spyder/pull/22089) - PR: Fix workflow glob (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22088](https://github.com/spyder-ide/spyder/pull/22088) - PR: Fix issue where Spyder's inline graphics preferences were not applied, by [@mrclary](https://github.com/mrclary) ([22034](https://github.com/spyder-ide/spyder/issues/22034), [10932](https://github.com/spyder-ide/spyder/issues/10932))
* [PR 22077](https://github.com/spyder-ide/spyder/pull/22077) - PR: Try to decrease timeouts when running tests and check general tests robustness and speed (CI/Testing), by [@dalthviz](https://github.com/dalthviz)
* [PR 22075](https://github.com/spyder-ide/spyder/pull/22075) - PR: Fix setting user environment variables on Windows, by [@mrclary](https://github.com/mrclary) ([21771](https://github.com/spyder-ide/spyder/issues/21771))
* [PR 19784](https://github.com/spyder-ide/spyder/pull/19784) - PR: Remember undocked state of plugins when closed and allow to close Outline when the Editor is maximized or in an Editor window, by [@ccordoba12](https://github.com/ccordoba12) ([16265](https://github.com/spyder-ide/spyder/issues/16265))

In this release 16 pull requests were closed.

----

## Version 6.0beta1 (2024-05-16)

### Issues Closed

* [Issue 22084](https://github.com/spyder-ide/spyder/issues/22084) - Error when restarting kernel ([PR 22085](https://github.com/spyder-ide/spyder/pull/22085) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22076](https://github.com/spyder-ide/spyder/issues/22076) - Spyder 6.0 beta1 release ([PR 22083](https://github.com/spyder-ide/spyder/pull/22083) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22068](https://github.com/spyder-ide/spyder/issues/22068) - Use Python 3.11 in the Spyder 6 installers ([PR 22072](https://github.com/spyder-ide/spyder/pull/22072) by [@mrclary](https://github.com/mrclary))
* [Issue 22049](https://github.com/spyder-ide/spyder/issues/22049) - Editor tab no longer called "Editor" ([PR 22050](https://github.com/spyder-ide/spyder/pull/22050) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22012](https://github.com/spyder-ide/spyder/issues/22012) - QThread destroyed when still running error in tests with main_window fixture ([PR 22053](https://github.com/spyder-ide/spyder/pull/22053) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21899](https://github.com/spyder-ide/spyder/issues/21899) - Feature Request: Be able to double click plots so they blow up into a larger screen ([PR 22029](https://github.com/spyder-ide/spyder/pull/22029) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21743](https://github.com/spyder-ide/spyder/issues/21743) - Enhancement proposal: create a plot button in variable explorer to visualize numerical data ([PR 21969](https://github.com/spyder-ide/spyder/pull/21969) by [@dpturibio](https://github.com/dpturibio))
* [Issue 17468](https://github.com/spyder-ide/spyder/issues/17468) - Editor migration tracker ([PR 22005](https://github.com/spyder-ide/spyder/pull/22005) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12158](https://github.com/spyder-ide/spyder/issues/12158) - Move plots in Plots pane ([PR 22029](https://github.com/spyder-ide/spyder/pull/22029) by [@ccordoba12](https://github.com/ccordoba12))

In this release 9 issues were closed.

### Pull Requests Merged

* [PR 22085](https://github.com/spyder-ide/spyder/pull/22085) - PR: Fix callable associated to `restart_action` (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22084](https://github.com/spyder-ide/spyder/issues/22084))
* [PR 22083](https://github.com/spyder-ide/spyder/pull/22083) - PR: Update core dependencies for 6.0.0 beta1, by [@dalthviz](https://github.com/dalthviz) ([22076](https://github.com/spyder-ide/spyder/issues/22076))
* [PR 22079](https://github.com/spyder-ide/spyder/pull/22079) - PR: Add UI for the `Remote client` plugin, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22072](https://github.com/spyder-ide/spyder/pull/22072) - PR: Use Python 3.11 for our installers, by [@mrclary](https://github.com/mrclary) ([22068](https://github.com/spyder-ide/spyder/issues/22068))
* [PR 22059](https://github.com/spyder-ide/spyder/pull/22059) - PR: Use conda-lock files to incrementally update conda-based installers, by [@mrclary](https://github.com/mrclary)
* [PR 22057](https://github.com/spyder-ide/spyder/pull/22057) - PR: Make Matplotlib status bar widget show the right backend and fix some errors related to kernel restarts for options that require them, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22053](https://github.com/spyder-ide/spyder/pull/22053) - PR: Fix introspection testing (CI), by [@dalthviz](https://github.com/dalthviz) ([22012](https://github.com/spyder-ide/spyder/issues/22012))
* [PR 22050](https://github.com/spyder-ide/spyder/pull/22050) - PR: Show `Editor` as title when the Editor is tabbed (Editor), by [@dalthviz](https://github.com/dalthviz) ([22049](https://github.com/spyder-ide/spyder/issues/22049))
* [PR 22029](https://github.com/spyder-ide/spyder/pull/22029) - PR: Improve UX of the Plots plugin, by [@ccordoba12](https://github.com/ccordoba12) ([21899](https://github.com/spyder-ide/spyder/issues/21899), [12158](https://github.com/spyder-ide/spyder/issues/12158))
* [PR 22025](https://github.com/spyder-ide/spyder/pull/22025) - PR: Improve drag & drop out of file explorer plugin, by [@rear1019](https://github.com/rear1019)
* [PR 22005](https://github.com/spyder-ide/spyder/pull/22005) - PR: Editor migration missing TODOs (Editor), by [@dalthviz](https://github.com/dalthviz) ([17468](https://github.com/spyder-ide/spyder/issues/17468))
* [PR 21969](https://github.com/spyder-ide/spyder/pull/21969) - PR: Add ability to show plots for dataframes (Variable Explorer), by [@dpturibio](https://github.com/dpturibio) ([21743](https://github.com/spyder-ide/spyder/issues/21743))
* [PR 21757](https://github.com/spyder-ide/spyder/pull/21757) - PR: Add backend for a new `Remote client` plugin, by [@hlouzada](https://github.com/hlouzada)

In this release 13 pull requests were closed.

----

## Version 6.0alpha5 (2024-04-23)

### Issues Closed

* [Issue 22008](https://github.com/spyder-ide/spyder/issues/22008) - Spyder 6.0 alpha5 release ([PR 22017](https://github.com/spyder-ide/spyder/pull/22017) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21900](https://github.com/spyder-ide/spyder/issues/21900) - IPython Console does not start if `debugpy` is not available (6.0 alpha4) ([PR 21926](https://github.com/spyder-ide/spyder/pull/21926) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21882](https://github.com/spyder-ide/spyder/issues/21882) - Connect errors without specific handling triggered while doing a check for updates to our error report dialog ([PR 21836](https://github.com/spyder-ide/spyder/pull/21836) by [@mrclary](https://github.com/mrclary))
* [Issue 21876](https://github.com/spyder-ide/spyder/issues/21876) - `%runcell` can not edit locals ([PR 21875](https://github.com/spyder-ide/spyder/pull/21875) by [@impact27](https://github.com/impact27))
* [Issue 21855](https://github.com/spyder-ide/spyder/issues/21855) - `menuinst` `Exception: Nothing to do:` traceback when installing Spyder 6.0.0a4 in a new conda env
* [Issue 21849](https://github.com/spyder-ide/spyder/issues/21849) - Message without translation in the tour ([PR 21880](https://github.com/spyder-ide/spyder/pull/21880) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21776](https://github.com/spyder-ide/spyder/issues/21776) - Standalone installers for 6.0 alpha4 are incorrectly named and Mac installer failed to build ([PR 21782](https://github.com/spyder-ide/spyder/pull/21782) by [@mrclary](https://github.com/mrclary))
* [Issue 21627](https://github.com/spyder-ide/spyder/issues/21627) - Larger dataframes with columns on the far right doesnt display max values when clicking on their column names twice + Other bugs ([PR 21913](https://github.com/spyder-ide/spyder/pull/21913) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21556](https://github.com/spyder-ide/spyder/issues/21556) - Follow up to work that added refresh buttons to editors from the Variable Explorer ([PR 21666](https://github.com/spyder-ide/spyder/pull/21666) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21468](https://github.com/spyder-ide/spyder/issues/21468) - Editor error while closing a project ([PR 21918](https://github.com/spyder-ide/spyder/pull/21918) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17807](https://github.com/spyder-ide/spyder/issues/17807) - Spyder not conform PEP3120 ([PR 21804](https://github.com/spyder-ide/spyder/pull/21804) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 12193](https://github.com/spyder-ide/spyder/issues/12193) - Move Editor plugin to use new API ([PR 21353](https://github.com/spyder-ide/spyder/pull/21353) by [@dalthviz](https://github.com/dalthviz))
* [Issue 9148](https://github.com/spyder-ide/spyder/issues/9148) - Low quality matplotlib inline plots on hidpi display ([PR 21812](https://github.com/spyder-ide/spyder/pull/21812) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 7609](https://github.com/spyder-ide/spyder/issues/7609) - Add a shortcut to create a new cell

In this release 14 issues were closed.

### Pull Requests Merged

* [PR 22017](https://github.com/spyder-ide/spyder/pull/22017) - PR: Update core dependencies for 6.0.0 alpha5, by [@dalthviz](https://github.com/dalthviz) ([22008](https://github.com/spyder-ide/spyder/issues/22008))
* [PR 22006](https://github.com/spyder-ide/spyder/pull/22006) - PR: Fix adding corner widgets in dockable plugins (API), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21948](https://github.com/spyder-ide/spyder/pull/21948) - PR: Fix getting IPython version for external conda environments (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21945](https://github.com/spyder-ide/spyder/pull/21945) - PR: Remove icons from standard buttons in dialogs (UI/UX), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21934](https://github.com/spyder-ide/spyder/pull/21934) - PR: Correct icon colors for remote connection dialog following WCAG 2 guidelines, by [@conradolandia](https://github.com/conradolandia)
* [PR 21926](https://github.com/spyder-ide/spyder/pull/21926) - PR: Add benign error when `debugpy` is not available (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([21900](https://github.com/spyder-ide/spyder/issues/21900))
* [PR 21918](https://github.com/spyder-ide/spyder/pull/21918) - PR: Add validation for `editor.sideareas_color` over debugger panel, by [@dalthviz](https://github.com/dalthviz) ([21468](https://github.com/spyder-ide/spyder/issues/21468))
* [PR 21913](https://github.com/spyder-ide/spyder/pull/21913) - PR: Fix issues with scrolling in dataframe editor (Variable Explorer), by [@jitseniesen](https://github.com/jitseniesen) ([21627](https://github.com/spyder-ide/spyder/issues/21627))
* [PR 21883](https://github.com/spyder-ide/spyder/pull/21883) - PR: Add icon to represent clearing the console (IPython console), by [@conradolandia](https://github.com/conradolandia)
* [PR 21880](https://github.com/spyder-ide/spyder/pull/21880) - PR: Add missing string for translation (Tours), by [@ccordoba12](https://github.com/ccordoba12) ([21849](https://github.com/spyder-ide/spyder/issues/21849))
* [PR 21875](https://github.com/spyder-ide/spyder/pull/21875) - PR: Allow magic to edit locals while debugging, by [@impact27](https://github.com/impact27) ([21876](https://github.com/spyder-ide/spyder/issues/21876))
* [PR 21871](https://github.com/spyder-ide/spyder/pull/21871) - PR: Fix issue where Spyder started automatically before conda-based installer exited, by [@mrclary](https://github.com/mrclary)
* [PR 21857](https://github.com/spyder-ide/spyder/pull/21857) - PR: UI improvements to configuration pages and other widgets, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21852](https://github.com/spyder-ide/spyder/pull/21852) - PR: Update to `codecov/action@v4` (CI), by [@mrclary](https://github.com/mrclary)
* [PR 21848](https://github.com/spyder-ide/spyder/pull/21848) - PR: Add icons for the remote connection dialog, by [@conradolandia](https://github.com/conradolandia)
* [PR 21844](https://github.com/spyder-ide/spyder/pull/21844) - PR: Make `SpyderPalette` inherit from QDarkStyle palettes and remove `QStylePalette`, by [@conradolandia](https://github.com/conradolandia)
* [PR 21836](https://github.com/spyder-ide/spyder/pull/21836) - PR: Only show UpdateManager statusbar widget while updating and when updates are available, by [@mrclary](https://github.com/mrclary) ([21882](https://github.com/spyder-ide/spyder/issues/21882))
* [PR 21813](https://github.com/spyder-ide/spyder/pull/21813) - PR: Additional UI/UX improvements for Files and Projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21812](https://github.com/spyder-ide/spyder/pull/21812) - PR: Change default resolution of plots to 144 dpi, by [@jitseniesen](https://github.com/jitseniesen) ([9148](https://github.com/spyder-ide/spyder/issues/9148))
* [PR 21804](https://github.com/spyder-ide/spyder/pull/21804) - PR: Use UTF-8 by default for Python files per PEP3120, by [@jitseniesen](https://github.com/jitseniesen) ([17807](https://github.com/spyder-ide/spyder/issues/17807))
* [PR 21788](https://github.com/spyder-ide/spyder/pull/21788) - PR: Avoid `conda run` capturing output in env activation (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21785](https://github.com/spyder-ide/spyder/pull/21785) - PR: Do not use version in artifact name (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21782](https://github.com/spyder-ide/spyder/pull/21782) - PR: Fix release build issues, by [@mrclary](https://github.com/mrclary) ([21776](https://github.com/spyder-ide/spyder/issues/21776))
* [PR 21666](https://github.com/spyder-ide/spyder/pull/21666) - PR: Unify UI of editors in Variable Explorer and simplify code, by [@jitseniesen](https://github.com/jitseniesen) ([21556](https://github.com/spyder-ide/spyder/issues/21556))
* [PR 21392](https://github.com/spyder-ide/spyder/pull/21392) - PR: Add macOS-arm64 target platform using M1 runner (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21353](https://github.com/spyder-ide/spyder/pull/21353) - PR: Initial Editor migration to the new API, by [@dalthviz](https://github.com/dalthviz) ([12193](https://github.com/spyder-ide/spyder/issues/12193))

In this release 26 pull requests were closed.

----

## Version 6.0alpha4 (2024-02-08)

### Issues Closed

* [Issue 21675](https://github.com/spyder-ide/spyder/issues/21675) - Icons for "Remove plots" and "Remove all plots" inconsistent ([PR 21715](https://github.com/spyder-ide/spyder/pull/21715) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21640](https://github.com/spyder-ide/spyder/issues/21640) - Minor update to standalone, conda-based installation via conda breaks the application ([PR 21647](https://github.com/spyder-ide/spyder/pull/21647) by [@mrclary](https://github.com/mrclary))
* [Issue 21538](https://github.com/spyder-ide/spyder/issues/21538) - TypeError after clicking "Find in files" action ([PR 21622](https://github.com/spyder-ide/spyder/pull/21622) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21482](https://github.com/spyder-ide/spyder/issues/21482) - When closing a modified file, the text on the popup's buttons could be clarified ([PR 21631](https://github.com/spyder-ide/spyder/pull/21631) by [@mrclary](https://github.com/mrclary))
* [Issue 21046](https://github.com/spyder-ide/spyder/issues/21046) - Improve highlighting of current plot ([PR 21598](https://github.com/spyder-ide/spyder/pull/21598) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 20114](https://github.com/spyder-ide/spyder/issues/20114) - Runfile raising syntax error when a dictionary is passed as an argument
* [Issue 19672](https://github.com/spyder-ide/spyder/issues/19672) - Missing options to control inline plots look ([PR 21566](https://github.com/spyder-ide/spyder/pull/21566) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 15264](https://github.com/spyder-ide/spyder/issues/15264) - Move calltip to not crop code written in the console ([PR 21710](https://github.com/spyder-ide/spyder/pull/21710) by [@ccordoba12](https://github.com/ccordoba12))

In this release 8 issues were closed.

### Pull Requests Merged

* [PR 21774](https://github.com/spyder-ide/spyder/pull/21774) - PR: Update core dependencies for 6.0.0 alpha4, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21762](https://github.com/spyder-ide/spyder/pull/21762) - PR: Improve performance of workspace watcher (Projects), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21740](https://github.com/spyder-ide/spyder/pull/21740) - PR: Remove old `python-lsp-black` related code, by [@remisalmon](https://github.com/remisalmon)
* [PR 21734](https://github.com/spyder-ide/spyder/pull/21734) - PR: Create a base class for sidebar dialogs (Widgets), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21715](https://github.com/spyder-ide/spyder/pull/21715) - PR: Change icon for "Remove all plots", by [@jitseniesen](https://github.com/jitseniesen) ([21675](https://github.com/spyder-ide/spyder/issues/21675))
* [PR 21710](https://github.com/spyder-ide/spyder/pull/21710) - PR: Improve hovers, completion hints and calltips, by [@ccordoba12](https://github.com/ccordoba12) ([15264](https://github.com/spyder-ide/spyder/issues/15264))
* [PR 21707](https://github.com/spyder-ide/spyder/pull/21707) - PR: Fix several UI regressions and errors, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21685](https://github.com/spyder-ide/spyder/pull/21685) - PR: More fixes for Qt 6 compatibility and a PySide2 fix, by [@rear1019](https://github.com/rear1019)
* [PR 21669](https://github.com/spyder-ide/spyder/pull/21669) - PR: Fix folding and make some performance improvements (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21667](https://github.com/spyder-ide/spyder/pull/21667) - PR: Fix errors when displaying the Symbols switcher, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21657](https://github.com/spyder-ide/spyder/pull/21657) - PR: Add icons for project actions, by [@conradolandia](https://github.com/conradolandia)
* [PR 21647](https://github.com/spyder-ide/spyder/pull/21647) - PR: Update for new menuinst and friends and new Spyder feedstock (Installers), by [@mrclary](https://github.com/mrclary) ([21640](https://github.com/spyder-ide/spyder/issues/21640))
* [PR 21641](https://github.com/spyder-ide/spyder/pull/21641) - PR: Additional UI improvements to the `About Spyder` dialog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21631](https://github.com/spyder-ide/spyder/pull/21631) - PR: Update button text for editor changed files message box, by [@mrclary](https://github.com/mrclary) ([21482](https://github.com/spyder-ide/spyder/issues/21482))
* [PR 21622](https://github.com/spyder-ide/spyder/pull/21622) - PR: Make some UI/UX improvements to the Find pane, by [@ccordoba12](https://github.com/ccordoba12) ([21538](https://github.com/spyder-ide/spyder/issues/21538))
* [PR 21598](https://github.com/spyder-ide/spyder/pull/21598) - PR: Change style of border around thumbnail of current plot, by [@jitseniesen](https://github.com/jitseniesen) ([21046](https://github.com/spyder-ide/spyder/issues/21046))
* [PR 21566](https://github.com/spyder-ide/spyder/pull/21566) - PR: Add new options for font size and bottom edge for inline plot, by [@jitseniesen](https://github.com/jitseniesen) ([19672](https://github.com/spyder-ide/spyder/issues/19672))

In this release 17 pull requests were closed.

----

## Version 6.0alpha3 (2023-12-19)

### Issues Closed

* [Issue 21591](https://github.com/spyder-ide/spyder/issues/21591) - Spyder 6.0 alpha3 release ([PR 21628](https://github.com/spyder-ide/spyder/pull/21628) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21527](https://github.com/spyder-ide/spyder/issues/21527) - Generate docstring not working if there are comments on the function definition lines ([PR 21536](https://github.com/spyder-ide/spyder/pull/21536) by [@rhkarls](https://github.com/rhkarls))
* [Issue 21520](https://github.com/spyder-ide/spyder/issues/21520) - Error when opening Preferences ([PR 21530](https://github.com/spyder-ide/spyder/pull/21530) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21499](https://github.com/spyder-ide/spyder/issues/21499) - Wrong Sphinx version detection for jsmath ([PR 21518](https://github.com/spyder-ide/spyder/pull/21518) by [@Mte90](https://github.com/Mte90))
* [Issue 21404](https://github.com/spyder-ide/spyder/issues/21404) - Spyder 6.0.0a2 splash screen text says version 5 ([PR 21535](https://github.com/spyder-ide/spyder/pull/21535) by [@conradolandia](https://github.com/conradolandia))
* [Issue 21326](https://github.com/spyder-ide/spyder/issues/21326) - Menu bar entries are too close to each other ([PR 21511](https://github.com/spyder-ide/spyder/pull/21511) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21322](https://github.com/spyder-ide/spyder/issues/21322) - Tests seems to be passing but fail ([PR 21102](https://github.com/spyder-ide/spyder/pull/21102) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21315](https://github.com/spyder-ide/spyder/issues/21315) - Array editor should have a toolbar ([PR 21317](https://github.com/spyder-ide/spyder/pull/21317) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21302](https://github.com/spyder-ide/spyder/issues/21302) - Codesign hangs on macOS installer ([PR 21334](https://github.com/spyder-ide/spyder/pull/21334) by [@mrclary](https://github.com/mrclary))
* [Issue 20831](https://github.com/spyder-ide/spyder/issues/20831) - Migrate existing update mechanism to new conda-based installers ([PR 21483](https://github.com/spyder-ide/spyder/pull/21483) by [@mrclary](https://github.com/mrclary))
* [Issue 20791](https://github.com/spyder-ide/spyder/issues/20791) - Two Spyder icons on Windows taskbar
* [Issue 20129](https://github.com/spyder-ide/spyder/issues/20129) - Check that paths are added in the expected order and to expected position in `sys.path` by the Pythonpath manager ([PR 21574](https://github.com/spyder-ide/spyder/pull/21574) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19182](https://github.com/spyder-ide/spyder/issues/19182) - Folders will disappear from the Pythonpath manager when they are deleted, but remain in `sys.path` ([PR 21574](https://github.com/spyder-ide/spyder/pull/21574) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15659](https://github.com/spyder-ide/spyder/issues/15659) - Shortcuts and icons not appearing in context menus of plugins on macOS ([PR 21511](https://github.com/spyder-ide/spyder/pull/21511) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15073](https://github.com/spyder-ide/spyder/issues/15073) - Switch order of entries in preferences ([PR 21233](https://github.com/spyder-ide/spyder/pull/21233) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14326](https://github.com/spyder-ide/spyder/issues/14326) - Uncommenting adds an extra whitespace in some cases ([PR 14768](https://github.com/spyder-ide/spyder/pull/14768) by [@remisalmon](https://github.com/remisalmon))
* [Issue 6325](https://github.com/spyder-ide/spyder/issues/6325) - Add ability to refresh/update existing Variable Explorer windows to reflect current variable state ([PR 21312](https://github.com/spyder-ide/spyder/pull/21312) by [@jitseniesen](https://github.com/jitseniesen))

In this release 17 issues were closed.

### Pull Requests Merged

* [PR 21628](https://github.com/spyder-ide/spyder/pull/21628) - PR: Update core dependencies for 6.0.0.alpha3, by [@dalthviz](https://github.com/dalthviz) ([21591](https://github.com/spyder-ide/spyder/issues/21591))
* [PR 21616](https://github.com/spyder-ide/spyder/pull/21616) - PR: Start spinner in dependencies dialog only when it's visible and make some improvements to the dialog's UI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21574](https://github.com/spyder-ide/spyder/pull/21574) - PR: Some improvements to the Pythonpath plugin, by [@ccordoba12](https://github.com/ccordoba12) ([20129](https://github.com/spyder-ide/spyder/issues/20129), [19182](https://github.com/spyder-ide/spyder/issues/19182))
* [PR 21573](https://github.com/spyder-ide/spyder/pull/21573) - PR: Increase minimal required version of PyQt to 5.15, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21572](https://github.com/spyder-ide/spyder/pull/21572) - PR: Initial fixes to make Spyder work with Qt 6, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21555](https://github.com/spyder-ide/spyder/pull/21555) - PR: Add new combobox widgets (API), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21540](https://github.com/spyder-ide/spyder/pull/21540) - PR: Remove double message on restart after kernel dies (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21536](https://github.com/spyder-ide/spyder/pull/21536) - PR: Remove comments from the function definition lines before generating docstrings, by [@rhkarls](https://github.com/rhkarls) ([21527](https://github.com/spyder-ide/spyder/issues/21527))
* [PR 21535](https://github.com/spyder-ide/spyder/pull/21535) - PR: Update Spyder splash screen text to read 'version 6', by [@conradolandia](https://github.com/conradolandia) ([21404](https://github.com/spyder-ide/spyder/issues/21404))
* [PR 21530](https://github.com/spyder-ide/spyder/pull/21530) - PR: Cast to `int` parameters used inside `ItemDelegate.sizeHint` return value (Widgets), by [@dalthviz](https://github.com/dalthviz) ([21520](https://github.com/spyder-ide/spyder/issues/21520))
* [PR 21524](https://github.com/spyder-ide/spyder/pull/21524) - PR: Fix syntax error over the completion plugin API (`SpyderCompletionProvider` class) (Completion), by [@dalthviz](https://github.com/dalthviz)
* [PR 21518](https://github.com/spyder-ide/spyder/pull/21518) - PR: Fix not displaying math equations in the Help pane, by [@Mte90](https://github.com/Mte90) ([21499](https://github.com/spyder-ide/spyder/issues/21499))
* [PR 21517](https://github.com/spyder-ide/spyder/pull/21517) - PR: Install QDarkstyle 3.2.0 on Linux pip slots (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21511](https://github.com/spyder-ide/spyder/pull/21511) - PR: Improve how menus are rendered and fix graphical errors related to them (UI), by [@ccordoba12](https://github.com/ccordoba12) ([21326](https://github.com/spyder-ide/spyder/issues/21326), [15659](https://github.com/spyder-ide/spyder/issues/15659))
* [PR 21510](https://github.com/spyder-ide/spyder/pull/21510) - PR: Fix deprecated top-level `developer_name` in AppData XML (Linux), by [@musicinmybrain](https://github.com/musicinmybrain)
* [PR 21483](https://github.com/spyder-ide/spyder/pull/21483) - PR: Create `UpdateManager` plugin to handle updates for the conda-based installers, by [@mrclary](https://github.com/mrclary) ([20831](https://github.com/spyder-ide/spyder/issues/20831))
* [PR 21451](https://github.com/spyder-ide/spyder/pull/21451) - PR: Fix interface language auto-configuration, by [@sthibaul](https://github.com/sthibaul)
* [PR 21391](https://github.com/spyder-ide/spyder/pull/21391) - PR: Temporarily use Apple Developer ID Application Certificate for signing Windows installer, by [@mrclary](https://github.com/mrclary)
* [PR 21352](https://github.com/spyder-ide/spyder/pull/21352) - PR: Add an empty message to the Debugger pane, by [@conradolandia](https://github.com/conradolandia)
* [PR 21343](https://github.com/spyder-ide/spyder/pull/21343) - PR: Fix Installer workflow on schedule and add badge to Readme, by [@mrclary](https://github.com/mrclary)
* [PR 21334](https://github.com/spyder-ide/spyder/pull/21334) - PR: Fix Codesigning for the Installers and Run Workflow on Schedule, by [@mrclary](https://github.com/mrclary) ([21302](https://github.com/spyder-ide/spyder/issues/21302))
* [PR 21333](https://github.com/spyder-ide/spyder/pull/21333) - PR: Fix syntax in `test_namespacebrowser.py` for Python 3.8 and 3.9, by [@jitseniesen](https://github.com/jitseniesen)
* [PR 21323](https://github.com/spyder-ide/spyder/pull/21323) - PR: Fix some failing tests, by [@impact27](https://github.com/impact27)
* [PR 21320](https://github.com/spyder-ide/spyder/pull/21320) - PR: Group kernel config calls (IPython console), by [@impact27](https://github.com/impact27)
* [PR 21317](https://github.com/spyder-ide/spyder/pull/21317) - PR: Add toolbar to array editor (Variable Explorer), by [@jitseniesen](https://github.com/jitseniesen) ([21315](https://github.com/spyder-ide/spyder/issues/21315))
* [PR 21312](https://github.com/spyder-ide/spyder/pull/21312) - PR: Add Refresh button to editors from Variable Explorer, by [@jitseniesen](https://github.com/jitseniesen) ([6325](https://github.com/spyder-ide/spyder/issues/6325))
* [PR 21294](https://github.com/spyder-ide/spyder/pull/21294) - PR: Rename `External Console` plugin to `External Terminal`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21276](https://github.com/spyder-ide/spyder/pull/21276) - PR: More UI fixes in several places, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21271](https://github.com/spyder-ide/spyder/pull/21271) - PR: Create loading screen for the Dependencies widget, and added new icons for dependencies, debug, console-off and console-remote-off, by [@conradolandia](https://github.com/conradolandia)
* [PR 21249](https://github.com/spyder-ide/spyder/pull/21249) - PR: Remove Kite completion provider code, by [@jsbautista](https://github.com/jsbautista)
* [PR 21233](https://github.com/spyder-ide/spyder/pull/21233) - PR: Improve style of the Preferences dialog (UI), by [@ccordoba12](https://github.com/ccordoba12) ([15073](https://github.com/spyder-ide/spyder/issues/15073))
* [PR 21102](https://github.com/spyder-ide/spyder/pull/21102) - PR: Fix error when running main window tests and failing tests, by [@ccordoba12](https://github.com/ccordoba12) ([21322](https://github.com/spyder-ide/spyder/issues/21322))
* [PR 20546](https://github.com/spyder-ide/spyder/pull/20546) - PR: Add edition menu and toolbar to dataframe viewer, by [@dpturibio](https://github.com/dpturibio) ([76](https://github.com/spyder-ide/ux-improvements/issues/76))
* [PR 14768](https://github.com/spyder-ide/spyder/pull/14768) - PR: Fix commenting/uncommenting to not change leading whitespaces, by [@remisalmon](https://github.com/remisalmon) ([14326](https://github.com/spyder-ide/spyder/issues/14326))

In this release 34 pull requests were closed.

----

## Version 6.0alpha2 (2023-09-05)

### Issues Closed

* [Issue 21257](https://github.com/spyder-ide/spyder/issues/21257) - Spyder 6.0 alpha2 release ([PR 21298](https://github.com/spyder-ide/spyder/pull/21298) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21222](https://github.com/spyder-ide/spyder/issues/21222) - DataFrame Editor background coloring does not support `pandas.Int*Dtype` dtypes ([PR 21295](https://github.com/spyder-ide/spyder/pull/21295) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21206](https://github.com/spyder-ide/spyder/issues/21206) - Config page for Shortcuts always shows shortcuts in black regardless of interface theme ([PR 21215](https://github.com/spyder-ide/spyder/pull/21215) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21191](https://github.com/spyder-ide/spyder/issues/21191) - TypeError when hovering over value in dictionary editor ([PR 21193](https://github.com/spyder-ide/spyder/pull/21193) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21173](https://github.com/spyder-ide/spyder/issues/21173) - Error with the Rich library in the Mac app
* [Issue 21157](https://github.com/spyder-ide/spyder/issues/21157) - Use caching for conda builds of subrepos in the installers-conda workflow ([PR 21182](https://github.com/spyder-ide/spyder/pull/21182) by [@mrclary](https://github.com/mrclary))
* [Issue 21149](https://github.com/spyder-ide/spyder/issues/21149) - Spyder 6.0a1 - Pandas error crashes console ([PR 21184](https://github.com/spyder-ide/spyder/pull/21184) by [@impact27](https://github.com/impact27))
* [Issue 21145](https://github.com/spyder-ide/spyder/issues/21145) - Plots from collection editor don't appear in Plots pane ([PR 21235](https://github.com/spyder-ide/spyder/pull/21235) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 20960](https://github.com/spyder-ide/spyder/issues/20960) - My font size in the variable explore is weird ([PR 20933](https://github.com/spyder-ide/spyder/pull/20933) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20940](https://github.com/spyder-ide/spyder/issues/20940) - Enhancements to Projects file switcher ([PR 21275](https://github.com/spyder-ide/spyder/pull/21275) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20715](https://github.com/spyder-ide/spyder/issues/20715) - Can not run IPython files in master ([PR 20762](https://github.com/spyder-ide/spyder/pull/20762) by [@impact27](https://github.com/impact27))
* [Issue 20701](https://github.com/spyder-ide/spyder/issues/20701) - Can not run renamed file in master ([PR 20762](https://github.com/spyder-ide/spyder/pull/20762) by [@impact27](https://github.com/impact27))
* [Issue 20571](https://github.com/spyder-ide/spyder/issues/20571) - Everything runs slowly after debugger is called ([PR 21107](https://github.com/spyder-ide/spyder/pull/21107) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17464](https://github.com/spyder-ide/spyder/issues/17464) - It is not possible to disable external plugins ([PR 21101](https://github.com/spyder-ide/spyder/pull/21101) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15254](https://github.com/spyder-ide/spyder/issues/15254) - Feature request: Pasting a file in the working directory doesn't work. ([PR 14092](https://github.com/spyder-ide/spyder/pull/14092) by [@impact27](https://github.com/impact27))
* [Issue 12851](https://github.com/spyder-ide/spyder/issues/12851) - Filenames are lowercased in debug mode ([PR 20493](https://github.com/spyder-ide/spyder/pull/20493) by [@impact27](https://github.com/impact27))
* [Issue 10968](https://github.com/spyder-ide/spyder/issues/10968) - Feature request: scroll line up/down using keyboard shortcut ([PR 10990](https://github.com/spyder-ide/spyder/pull/10990) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 10815](https://github.com/spyder-ide/spyder/issues/10815) - Add "Copy absolute/relative path" actions to the editor ([PR 21205](https://github.com/spyder-ide/spyder/pull/21205) by [@dalthviz](https://github.com/dalthviz))
* [Issue 5942](https://github.com/spyder-ide/spyder/issues/5942) - Is there any way to change the font for the entire application? ([PR 20933](https://github.com/spyder-ide/spyder/pull/20933) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 4120](https://github.com/spyder-ide/spyder/issues/4120) - Spyder cannot accept Chinese input ([PR 21260](https://github.com/spyder-ide/spyder/pull/21260) by [@dalthviz](https://github.com/dalthviz))
* [Issue 3860](https://github.com/spyder-ide/spyder/issues/3860) - File Switcher should search all project files and not only the open ones ([PR 20895](https://github.com/spyder-ide/spyder/pull/20895) by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez))

In this release 21 issues were closed.

### Pull Requests Merged

* [PR 21306](https://github.com/spyder-ide/spyder/pull/21306) - PR: Update `RELEASE.md` instructions and bump `spyder-kernels` version used in the IPython Console validations, by [@dalthviz](https://github.com/dalthviz)
* [PR 21305](https://github.com/spyder-ide/spyder/pull/21305) - PR: Do not sign or notarize macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 21300](https://github.com/spyder-ide/spyder/pull/21300) - PR: Remove installers workflow step validation for spyder conda package build to be done only on PRs (CI), by [@dalthviz](https://github.com/dalthviz)
* [PR 21298](https://github.com/spyder-ide/spyder/pull/21298) - PR: Update core dependencies for 6.0.0.alpha2, by [@dalthviz](https://github.com/dalthviz) ([21257](https://github.com/spyder-ide/spyder/issues/21257))
* [PR 21295](https://github.com/spyder-ide/spyder/pull/21295) - PR: Support all real number dtypes in dataframe editor, by [@jitseniesen](https://github.com/jitseniesen) ([21222](https://github.com/spyder-ide/spyder/issues/21222))
* [PR 21275](https://github.com/spyder-ide/spyder/pull/21275) - PR: Compute Projects switcher results in a worker to avoid freezes, by [@ccordoba12](https://github.com/ccordoba12) ([20940](https://github.com/spyder-ide/spyder/issues/20940))
* [PR 21262](https://github.com/spyder-ide/spyder/pull/21262) - PR: Handle decode errors in threads used for standard streams (IPython console), by [@impact27](https://github.com/impact27)
* [PR 21260](https://github.com/spyder-ide/spyder/pull/21260) - PR: Add `fzf` and `fcitx-qt5` as conda requirements, by [@dalthviz](https://github.com/dalthviz) ([4120](https://github.com/spyder-ide/spyder/issues/4120))
* [PR 21236](https://github.com/spyder-ide/spyder/pull/21236) - PR: Fix error after changes to Plugins page (Preferences), by [@rear1019](https://github.com/rear1019)
* [PR 21235](https://github.com/spyder-ide/spyder/pull/21235) - PR: Display plots from collections editor in the Plots pane, by [@jitseniesen](https://github.com/jitseniesen) ([21145](https://github.com/spyder-ide/spyder/issues/21145))
* [PR 21226](https://github.com/spyder-ide/spyder/pull/21226) - PR: Fixes to improve compatibility with PySide2, by [@rear1019](https://github.com/rear1019)
* [PR 21224](https://github.com/spyder-ide/spyder/pull/21224) - PR: Fix `TypeError` in breakpoints table (Debugger), by [@rear1019](https://github.com/rear1019)
* [PR 21215](https://github.com/spyder-ide/spyder/pull/21215) - PR: Fix showing text in the dark theme for keyboard sequences in the Shortcurts page (Preferences), by [@ccordoba12](https://github.com/ccordoba12) ([21206](https://github.com/spyder-ide/spyder/issues/21206))
* [PR 21213](https://github.com/spyder-ide/spyder/pull/21213) - PR: Update installer workflow to only restore cache of subrepo builds (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21212](https://github.com/spyder-ide/spyder/pull/21212) - PR: Build subrepo caches on master (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21210](https://github.com/spyder-ide/spyder/pull/21210) - PR: Move Editor API inside the plugin (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 21205](https://github.com/spyder-ide/spyder/pull/21205) - PR: Add copy absolute and relative paths to file context menu (Editor), by [@dalthviz](https://github.com/dalthviz) ([10815](https://github.com/spyder-ide/spyder/issues/10815))
* [PR 21194](https://github.com/spyder-ide/spyder/pull/21194) - PR: Move classes in `editor.py` to their own modules (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 21193](https://github.com/spyder-ide/spyder/pull/21193) - PR: Fix `ReadOnlyCollectionsModel` tooltip logic (Widgets/Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([21191](https://github.com/spyder-ide/spyder/issues/21191))
* [PR 21185](https://github.com/spyder-ide/spyder/pull/21185) - PR: Fix config page radiobutton reference (Main interpreter), by [@dalthviz](https://github.com/dalthviz)
* [PR 21184](https://github.com/spyder-ide/spyder/pull/21184) - PR: Remove locals inspection from the kernel (IPython console), by [@impact27](https://github.com/impact27) ([21149](https://github.com/spyder-ide/spyder/issues/21149))
* [PR 21182](https://github.com/spyder-ide/spyder/pull/21182) - PR: Cache subrepo conda builds for installers, by [@mrclary](https://github.com/mrclary) ([21157](https://github.com/spyder-ide/spyder/issues/21157))
* [PR 21156](https://github.com/spyder-ide/spyder/pull/21156) - PR: Some fixes for the report error dialog (UI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21134](https://github.com/spyder-ide/spyder/pull/21134) - PR: Improve UI of `PaneEmptyWidget`, show message on panes connected to dead consoles and improve About dialog UI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21133](https://github.com/spyder-ide/spyder/pull/21133) - PR: Improve style of dockwidget tabbars (UI), by [@ccordoba12](https://github.com/ccordoba12) ([4](https://github.com/spyder-ide/ux-improvements/issues/4))
* [PR 21132](https://github.com/spyder-ide/spyder/pull/21132) - PR: Don't write to shell history file when getting user environment variables, by [@mrclary](https://github.com/mrclary)
* [PR 21131](https://github.com/spyder-ide/spyder/pull/21131) - PR: Reinstate notarization of conda-based macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 21125](https://github.com/spyder-ide/spyder/pull/21125) - PR: Update to `napari/label/bundle_tools_3` (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21107](https://github.com/spyder-ide/spyder/pull/21107) - PR: Add `exitdb` command and some speed optimizations to the debugger, by [@ccordoba12](https://github.com/ccordoba12) ([20571](https://github.com/spyder-ide/spyder/issues/20571))
* [PR 21101](https://github.com/spyder-ide/spyder/pull/21101) - PR: Improve UI of Plugins page in Preferences, by [@ccordoba12](https://github.com/ccordoba12) ([17464](https://github.com/spyder-ide/spyder/issues/17464))
* [PR 21092](https://github.com/spyder-ide/spyder/pull/21092) - PR: Remove setting font for update status bar widget (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21084](https://github.com/spyder-ide/spyder/pull/21084) - PR: Automatically launch Spyder after installation (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21083](https://github.com/spyder-ide/spyder/pull/21083) - PR: Fix issue where bootstrap incorrectly determines git branch, by [@mrclary](https://github.com/mrclary)
* [PR 21075](https://github.com/spyder-ide/spyder/pull/21075) - PR: Update installers to use Python 3.10, by [@mrclary](https://github.com/mrclary)
* [PR 21065](https://github.com/spyder-ide/spyder/pull/21065) - PR: Fix issue getting user environment variables on Posix systems and pass them to the IPython console, by [@mrclary](https://github.com/mrclary)
* [PR 21062](https://github.com/spyder-ide/spyder/pull/21062) - PR: Fix issue where cmd.exe window flashes on Spyder startup on Windows (installer), by [@mrclary](https://github.com/mrclary)
* [PR 21057](https://github.com/spyder-ide/spyder/pull/21057) - PR: Remove Spyder 5 changelog from tarball, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21053](https://github.com/spyder-ide/spyder/pull/21053) - PR: Fix issues for all-user install in post-install script (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21050](https://github.com/spyder-ide/spyder/pull/21050) - PR: Small fixes to release files after 6.0a1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20997](https://github.com/spyder-ide/spyder/pull/20997) - PR: Remove Spyder 2 icon set because it's incomplete, by [@jsbautista](https://github.com/jsbautista) ([43](https://github.com/spyder-ide/ux-improvements/issues/43))
* [PR 20933](https://github.com/spyder-ide/spyder/pull/20933) - PR: Make the font used by the application configurable and other UI fixes, by [@ccordoba12](https://github.com/ccordoba12) ([5942](https://github.com/spyder-ide/spyder/issues/5942), [20960](https://github.com/spyder-ide/spyder/issues/20960))
* [PR 20926](https://github.com/spyder-ide/spyder/pull/20926) - PR: Add help info widget to show tooltips in Preferences (UX/UI), by [@jsbautista](https://github.com/jsbautista)
* [PR 20895](https://github.com/spyder-ide/spyder/pull/20895) - PR: Add switcher integration to projects, by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez) ([3860](https://github.com/spyder-ide/spyder/issues/3860))
* [PR 20868](https://github.com/spyder-ide/spyder/pull/20868) - PR: Improve Variable Explorer UX, by [@jsbautista](https://github.com/jsbautista) ([17](https://github.com/spyder-ide/ux-improvements/issues/17))
* [PR 20767](https://github.com/spyder-ide/spyder/pull/20767) - PR: Add clarifying message to several empty panes, by [@jsbautista](https://github.com/jsbautista) ([11](https://github.com/spyder-ide/ux-improvements/issues/11))
* [PR 20762](https://github.com/spyder-ide/spyder/pull/20762) - PR: Enable running renamed and IPython files again, by [@impact27](https://github.com/impact27) ([20715](https://github.com/spyder-ide/spyder/issues/20715), [20701](https://github.com/spyder-ide/spyder/issues/20701))
* [PR 20493](https://github.com/spyder-ide/spyder/pull/20493) - PR: Fix capitalization on Windows when opening a file in debug mode, by [@impact27](https://github.com/impact27) ([12851](https://github.com/spyder-ide/spyder/issues/12851))
* [PR 19492](https://github.com/spyder-ide/spyder/pull/19492) - PR: Merge Breakpoints and Debugger plugins, by [@impact27](https://github.com/impact27)
* [PR 19350](https://github.com/spyder-ide/spyder/pull/19350) - PR: Improve debugging for IPython kernels, by [@impact27](https://github.com/impact27)
* [PR 14092](https://github.com/spyder-ide/spyder/pull/14092) - PR: Open file pasted into working directory toolbar, by [@impact27](https://github.com/impact27) ([15254](https://github.com/spyder-ide/spyder/issues/15254))
* [PR 10990](https://github.com/spyder-ide/spyder/pull/10990) - PR: Add scroll line up/down keyboard shortcuts (Editor), by [@jnsebgosselin](https://github.com/jnsebgosselin) ([10968](https://github.com/spyder-ide/spyder/issues/10968))

In this release 51 pull requests were closed.

----

## Version 6.0alpha1 (2023-06-19)

### Issues Closed

* [Issue 20885](https://github.com/spyder-ide/spyder/issues/20885) - Error when opening files due to a corrupted config file ([PR 20886](https://github.com/spyder-ide/spyder/pull/20886) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20776](https://github.com/spyder-ide/spyder/issues/20776) - Loading of old third-party plugins in Spyder 6 ([PR 20789](https://github.com/spyder-ide/spyder/pull/20789) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20630](https://github.com/spyder-ide/spyder/issues/20630) - Proposition: Turn runfile / runcell to IPython magics ([PR 20633](https://github.com/spyder-ide/spyder/pull/20633) by [@impact27](https://github.com/impact27))
* [Issue 20572](https://github.com/spyder-ide/spyder/issues/20572) - Graphical way to pause at current point and drop to debugger ([PR 18514](https://github.com/spyder-ide/spyder/pull/18514) by [@impact27](https://github.com/impact27))
* [Issue 20561](https://github.com/spyder-ide/spyder/issues/20561) - Spyder crashes at shutdown ([PR 20562](https://github.com/spyder-ide/spyder/pull/20562) by [@impact27](https://github.com/impact27))
* [Issue 20536](https://github.com/spyder-ide/spyder/issues/20536) - Attach sha256sum for installers ([PR 20587](https://github.com/spyder-ide/spyder/pull/20587) by [@mrclary](https://github.com/mrclary))
* [Issue 20474](https://github.com/spyder-ide/spyder/issues/20474) - Generating new plots always overrides currently selected plot ([PR 20475](https://github.com/spyder-ide/spyder/pull/20475) by [@impact27](https://github.com/impact27))
* [Issue 20403](https://github.com/spyder-ide/spyder/issues/20403) - Find and replace "Replace all occurences" ignores "Only search for whole words" ([PR 20497](https://github.com/spyder-ide/spyder/pull/20497) by [@mrclary](https://github.com/mrclary))
* [Issue 19920](https://github.com/spyder-ide/spyder/issues/19920) - Debug toolbar is enabled for non-Python files (e.g.:  .trp)
* [Issue 19502](https://github.com/spyder-ide/spyder/issues/19502) - Update Python version on Windows installer to 3.10 to not flag `match` as an error
* [Issue 18855](https://github.com/spyder-ide/spyder/issues/18855) - `test_leaks` is failing on master ([PR 18857](https://github.com/spyder-ide/spyder/pull/18857) by [@impact27](https://github.com/impact27))
* [Issue 17888](https://github.com/spyder-ide/spyder/issues/17888) - Add Debug line functionality to Debug menu and toolbar ([PR 19306](https://github.com/spyder-ide/spyder/pull/19306) by [@impact27](https://github.com/impact27))
* [Issue 16662](https://github.com/spyder-ide/spyder/issues/16662) - Add a way to test the Windows installer ([PR 20601](https://github.com/spyder-ide/spyder/pull/20601) by [@mrclary](https://github.com/mrclary))
* [Issue 16013](https://github.com/spyder-ide/spyder/issues/16013) - Feature request: Expose pdb "u" and "d" commands to user ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))
* [Issue 14894](https://github.com/spyder-ide/spyder/issues/14894) - Variable explorer doesn't show variables on remote kernel when using localhost forwarded ports ([PR 16890](https://github.com/spyder-ide/spyder/pull/16890) by [@impact27](https://github.com/impact27))
* [Issue 14518](https://github.com/spyder-ide/spyder/issues/14518) - How to view numbers in a dataframe with thousands separator in spyder variable explorer? ([PR 20473](https://github.com/spyder-ide/spyder/pull/20473) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 13336](https://github.com/spyder-ide/spyder/issues/13336) - Kernel not restarting sometimes ([PR 19411](https://github.com/spyder-ide/spyder/pull/19411) by [@impact27](https://github.com/impact27))
* [Issue 11177](https://github.com/spyder-ide/spyder/issues/11177) - Visualize what line of code the editor is running  ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))
* [Issue 5205](https://github.com/spyder-ide/spyder/issues/5205) - Improvement: add a shortcut to enter the debugger after an error occurs ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))
* [Issue 1613](https://github.com/spyder-ide/spyder/issues/1613) - Visual debug call stack window - enhacement request ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))

In this release 20 issues were closed.

### Pull Requests Merged

* [PR 21041](https://github.com/spyder-ide/spyder/pull/21041) - PR: Skip notarization of our Mac app (Installers), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21036](https://github.com/spyder-ide/spyder/pull/21036) - PR: Add `spyder_kernels_rc` conda-forge label (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21030](https://github.com/spyder-ide/spyder/pull/21030) - PR: Update core dependencies for 6.0 alpha1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20972](https://github.com/spyder-ide/spyder/pull/20972) - PR: Add new icons for replace next, all and selection buttons, by [@conradolandia](https://github.com/conradolandia)
* [PR 20965](https://github.com/spyder-ide/spyder/pull/20965) - PR: Fix typo in Announcements.md, by [@habibmy](https://github.com/habibmy)
* [PR 20952](https://github.com/spyder-ide/spyder/pull/20952) - PR: Add support for the future `python-lsp-black` 2.0 version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20905](https://github.com/spyder-ide/spyder/pull/20905) - PR: Fix typo in kernel error message (IPython console), by [@jitseniesen](https://github.com/jitseniesen)
* [PR 20893](https://github.com/spyder-ide/spyder/pull/20893) - PR: Move LSP related code from the `CodeEditor` class definition to a new mixin and `CodeEditor` related elements to a `codeeditor` module (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20886](https://github.com/spyder-ide/spyder/pull/20886) - PR: Prevent saving `None` value as Editor bookmarks, by [@dalthviz](https://github.com/dalthviz) ([20885](https://github.com/spyder-ide/spyder/issues/20885))
* [PR 20884](https://github.com/spyder-ide/spyder/pull/20884) - PR: Cleanup Environments for Conda-based Installers, by [@mrclary](https://github.com/mrclary)
* [PR 20874](https://github.com/spyder-ide/spyder/pull/20874) - PR: Improve versions of debug icons, add new cell icon and optimize svg icons, by [@conradolandia](https://github.com/conradolandia)
* [PR 20837](https://github.com/spyder-ide/spyder/pull/20837) - PR: Define Switcher Plugin public API + fix switcher position bug, by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez)
* [PR 20833](https://github.com/spyder-ide/spyder/pull/20833) - PR: Skip a test that started to fail on Linux and Mac, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20827](https://github.com/spyder-ide/spyder/pull/20827) - PR: Change logic to detect conda-based installers and micromamba on them, by [@mrclary](https://github.com/mrclary)
* [PR 20825](https://github.com/spyder-ide/spyder/pull/20825) - PR: Move CONF usage for bookmarks logic and use `SpyderConfiguratorAccessor` class in Editor widgets (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20824](https://github.com/spyder-ide/spyder/pull/20824) - PR: Declare a clear API for Projects and move implementation code to its main widget, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20810](https://github.com/spyder-ide/spyder/pull/20810) - PR: Remove some unused methods from MainWindow and fix Code Analysis and Profiler actions in menus position, by [@dalthviz](https://github.com/dalthviz)
* [PR 20789](https://github.com/spyder-ide/spyder/pull/20789) - PR: Remove code that tried to load old third-party plugins and move IO plugins to Spyder-kernels, by [@ccordoba12](https://github.com/ccordoba12) ([20776](https://github.com/spyder-ide/spyder/issues/20776))
* [PR 20773](https://github.com/spyder-ide/spyder/pull/20773) - PR: Fix `test_collectionseditor` after merge (Widgets), by [@dalthviz](https://github.com/dalthviz)
* [PR 20733](https://github.com/spyder-ide/spyder/pull/20733) - PR: Fix `test_clickable_ipython_tracebacks`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20726](https://github.com/spyder-ide/spyder/pull/20726) - PR: Improve and refactor the way we run and debug code in the IPython console, by [@impact27](https://github.com/impact27)
* [PR 20714](https://github.com/spyder-ide/spyder/pull/20714) - PR: Make the switcher a plugin, by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez)
* [PR 20689](https://github.com/spyder-ide/spyder/pull/20689) - PR: Fix `Source` menu order (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20653](https://github.com/spyder-ide/spyder/pull/20653) - PR: Fix debugger tests with the latest version of IPykernel, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20633](https://github.com/spyder-ide/spyder/pull/20633) - PR: Create magics for run|debug file|cell (IPython console), by [@impact27](https://github.com/impact27) ([20630](https://github.com/spyder-ide/spyder/issues/20630))
* [PR 20620](https://github.com/spyder-ide/spyder/pull/20620) - PR: Initial code changes for old menu actions to use the `Mainmenu` plugin (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20601](https://github.com/spyder-ide/spyder/pull/20601) - PR: Add installer tests for Linux and Windows, by [@mrclary](https://github.com/mrclary) ([16662](https://github.com/spyder-ide/spyder/issues/16662))
* [PR 20587](https://github.com/spyder-ide/spyder/pull/20587) - PR: Add sha256sum to release assets, by [@mrclary](https://github.com/mrclary) ([20536](https://github.com/spyder-ide/spyder/issues/20536))
* [PR 20575](https://github.com/spyder-ide/spyder/pull/20575) - PR: Fix conda script selection for custom interpreter env activation on Windows, by [@dalthviz](https://github.com/dalthviz)
* [PR 20574](https://github.com/spyder-ide/spyder/pull/20574) - PR: Remove API method that's no longer necessary (Run), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20568](https://github.com/spyder-ide/spyder/pull/20568) - PR: Add public API method to set custom interpreter (Main interpreter), by [@dalthviz](https://github.com/dalthviz)
* [PR 20562](https://github.com/spyder-ide/spyder/pull/20562) - PR: Wait on all shutdown threads (IPython console), by [@impact27](https://github.com/impact27) ([20561](https://github.com/spyder-ide/spyder/issues/20561))
* [PR 20557](https://github.com/spyder-ide/spyder/pull/20557) - PR: Transition Debugger plugin actions to the new Run architecture and cleanup Editor plugin, by [@impact27](https://github.com/impact27)
* [PR 20548](https://github.com/spyder-ide/spyder/pull/20548) - PR: Fix test_shell_execution for macOS, by [@mrclary](https://github.com/mrclary)
* [PR 20509](https://github.com/spyder-ide/spyder/pull/20509) - PR: Improve cells support in the Editor, by [@jsbautista](https://github.com/jsbautista)
* [PR 20497](https://github.com/spyder-ide/spyder/pull/20497) - PR: Fix issue where replace all did not respect whole words filter, by [@mrclary](https://github.com/mrclary) ([20403](https://github.com/spyder-ide/spyder/issues/20403))
* [PR 20475](https://github.com/spyder-ide/spyder/pull/20475) - PR: Stop automatic scrolling when a plot is selected (Plots), by [@impact27](https://github.com/impact27) ([20474](https://github.com/spyder-ide/spyder/issues/20474))
* [PR 20473](https://github.com/spyder-ide/spyder/pull/20473) - PR: Use .format() to format floats in array and dataframe editors, by [@jitseniesen](https://github.com/jitseniesen) ([14518](https://github.com/spyder-ide/spyder/issues/14518))
* [PR 20471](https://github.com/spyder-ide/spyder/pull/20471) - PR: Update conda-based installers, by [@mrclary](https://github.com/mrclary)
* [PR 20460](https://github.com/spyder-ide/spyder/pull/20460) - PR: Fix failure installing Spyder-kernels from master on Windows and other minor fixes on CIS, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20449](https://github.com/spyder-ide/spyder/pull/20449) - PR: Replace mamba command with micromamba in CI install script (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20421](https://github.com/spyder-ide/spyder/pull/20421) - PR: Add menu to use specific environment interpreter for a new console instance, by [@jsbautista](https://github.com/jsbautista)
* [PR 20411](https://github.com/spyder-ide/spyder/pull/20411) - PR: Pin PyZMQ to version 24 to prevent hangs in our CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20368](https://github.com/spyder-ide/spyder/pull/20368) - PR: Remove original installers in favor of conda-based ones, by [@mrclary](https://github.com/mrclary)
* [PR 20306](https://github.com/spyder-ide/spyder/pull/20306) - PR: Skip a test that started to fail on Windows, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20238](https://github.com/spyder-ide/spyder/pull/20238) - PR: Fix a small kernel restart issue (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19842](https://github.com/spyder-ide/spyder/pull/19842) - PR: Update Variable Explorer from the kernel, by [@impact27](https://github.com/impact27)
* [PR 19411](https://github.com/spyder-ide/spyder/pull/19411) - PR: Use pipes for stdout and stderr and improve comm connection (IPython console), by [@impact27](https://github.com/impact27) ([13336](https://github.com/spyder-ide/spyder/issues/13336))
* [PR 19343](https://github.com/spyder-ide/spyder/pull/19343) - PR: Use new API to handle creation and removal of debug toolbar and menu, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19306](https://github.com/spyder-ide/spyder/pull/19306) - PR: Add a debug current line or selection button, by [@impact27](https://github.com/impact27) ([17888](https://github.com/spyder-ide/spyder/issues/17888))
* [PR 19305](https://github.com/spyder-ide/spyder/pull/19305) - PR: Add button to debugger plugin to go to editor, by [@impact27](https://github.com/impact27)
* [PR 19265](https://github.com/spyder-ide/spyder/pull/19265) - PR: Move debug functions from IPython plugin to debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 19208](https://github.com/spyder-ide/spyder/pull/19208) - PR: Move breakpoints logic from editor plugin to debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 19181](https://github.com/spyder-ide/spyder/pull/19181) - PR: Move debug cell / file / config to Debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 19092](https://github.com/spyder-ide/spyder/pull/19092) - PR: Use cached kernel for faster kernel restart (IPython console), by [@impact27](https://github.com/impact27)
* [PR 19074](https://github.com/spyder-ide/spyder/pull/19074) - PR: Improve validation for the right Spyder-kernels version, by [@impact27](https://github.com/impact27)
* [PR 19062](https://github.com/spyder-ide/spyder/pull/19062) - PR: Refactor the way clients are created (IPython console), by [@impact27](https://github.com/impact27)
* [PR 19005](https://github.com/spyder-ide/spyder/pull/19005) - PR: Unmaximize debugger plugin when clicking on debug toolbar buttons, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18877](https://github.com/spyder-ide/spyder/pull/18877) - PR: Add debug cell icon to the debug toolbar, by [@stevetracvc](https://github.com/stevetracvc)
* [PR 18864](https://github.com/spyder-ide/spyder/pull/18864) - PR: Fix `test_leaks` on master, by [@impact27](https://github.com/impact27)
* [PR 18857](https://github.com/spyder-ide/spyder/pull/18857) - PR: Close memory leak in master, by [@impact27](https://github.com/impact27) ([18855](https://github.com/spyder-ide/spyder/issues/18855))
* [PR 18853](https://github.com/spyder-ide/spyder/pull/18853) - PR: Move debug buttons to the Debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 18852](https://github.com/spyder-ide/spyder/pull/18852) - PR: Rename FramesExplorer plugin to Debugger, by [@impact27](https://github.com/impact27)
* [PR 18837](https://github.com/spyder-ide/spyder/pull/18837) - PR: Make the debugger work faster, by [@impact27](https://github.com/impact27)
* [PR 18514](https://github.com/spyder-ide/spyder/pull/18514) - PR: Add ability to interrupt the current execution and enter the debugger after that, by [@impact27](https://github.com/impact27) ([20572](https://github.com/spyder-ide/spyder/issues/20572))
* [PR 18476](https://github.com/spyder-ide/spyder/pull/18476) - PR: Do not reset the frames explorer while debugging, by [@impact27](https://github.com/impact27)
* [PR 18463](https://github.com/spyder-ide/spyder/pull/18463) - PR: Refactor to separate ShellWidget from VariableExplorerWidget and FigureBrowser, by [@impact27](https://github.com/impact27)
* [PR 17656](https://github.com/spyder-ide/spyder/pull/17656) - PR: Ignore `REVIEW.md` from `check-manifest` and fix `setup.py` patch for Windows installers on PRs, by [@dalthviz](https://github.com/dalthviz)
* [PR 17467](https://github.com/spyder-ide/spyder/pull/17467) - PR: Generalize Run plugin to support generic inputs and executors, by [@andfoy](https://github.com/andfoy)
* [PR 17335](https://github.com/spyder-ide/spyder/pull/17335) - PR: Skip Spyder-kernels check for now (Dependencies), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16890](https://github.com/spyder-ide/spyder/pull/16890) - PR: Use control channel for comms, by [@impact27](https://github.com/impact27) ([14894](https://github.com/spyder-ide/spyder/issues/14894))
* [PR 16789](https://github.com/spyder-ide/spyder/pull/16789) - PR: Create Reviewer Guidelines, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 16661](https://github.com/spyder-ide/spyder/pull/16661) - PR: Add a finder widget to reuse a similar widget used in the Variable Explorer, by [@impact27](https://github.com/impact27)
* [PR 14199](https://github.com/spyder-ide/spyder/pull/14199) - PR: Show Matplotlib backend state in status bar, by [@impact27](https://github.com/impact27)
* [PR 11186](https://github.com/spyder-ide/spyder/pull/11186) - PR: Add a new plugin to explore frames while debugging, by [@impact27](https://github.com/impact27) ([5205](https://github.com/spyder-ide/spyder/issues/5205), [1613](https://github.com/spyder-ide/spyder/issues/1613), [16013](https://github.com/spyder-ide/spyder/issues/16013), [11177](https://github.com/spyder-ide/spyder/issues/11177))

In this release 75 pull requests were closed.
