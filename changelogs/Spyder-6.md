# History of changes for Spyder 6

## Version 6.0.0 (unreleased)

### New features

* New installers for Windows, Linux and macOS based on Conda and Conda-forge.
* Add a Debugger pane to explore the stack frame of the current debugging
  session.
* Add a button to the Debugger pane to pause the current code execution and
  enter the debugger afterwards.
* Add submenu to the `Consoles` menu to start a new console for a specific
  Conda or Pyenv environment.
* Add ability to refresh the open Variable Explorer viewers to reflect the current
  variable state.
* Show plots generated in the Variable Explorer or its viewers in the Plots pane.
* Show Matplotlib backend state in status bar.
* Make kernel restarts be much faster for the current interpreter.
* Turn `runfile`, `debugfile`, `runcell` and related commands into IPython magics.

### Important fixes

* Environment variables declared in `~/.bashrc` or `~/.zhrc` are detected and
  passed to the IPython console.
* Support all real number dtypes in the dataframe viewer.
* Restore ability to load Hdf5 and Dicom files through the Variable Explorer
  (this was working in Spyder 4 and before).

### UX/UI improvements

* Make Spyder accept Chinese, Korean or Japanese input on Linux by adding
  `fcitx-qt5` as a new dependency (in conda environments only).
* The file switcher can browse and open files present in the current project (
  only if the `fzf` package is installed).
* The interface font used by the entire application can be configured in
  `Preferences > Appearance`
* Files can be opened in the editor by pasting their path in the Working
  Directory toolbar.
* Add a new button to the Variable Explorer to indicate when variables are being
  filtered.

### New API features

* `SpyderPluginV2.get_description` must be a static method now and
  `SpyderPluginV2.get_icon` a class or static method. This is necessary to
  display the list of available plugins in Preferences in a more user-friendly
  way (see PR spyder-ide/spyder#21101).
* Generalize the Run plugin to support generic inputs and executors. This allows
  plugins to declare what kind of inputs (i.e. file, cell or selection) they
  can execute and how they will display the result.
* Add a new plugin called Switcher for the files and symbols switcher.
* Declare a proper API for the Projects plugin.
* Remove the Breakpoints plugin and add its functionality to the Debugger one.

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
