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
* Show Matplotlib backend state in status bar.
* Make kernel restarts be much faster for the current interpreter.
* Turn `runfile`, `debugfile`, `runcell` and related commands to IPython magics.

### Important fixes

* Environment variables declared in `~/.bashrc` or `~/.zhrc` are detected and
  passed to the IPython console.
* Restore ability to load Hdf5 and Dicom files through the Variable Explorer
  (this was working in Spyder 4 and before).

### UX/UI improvements

* The file switcher can open files present in the current project.
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
