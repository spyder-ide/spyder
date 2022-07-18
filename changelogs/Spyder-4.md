# History of changes for Spyder 4

## Version 4.2.5 (2021-03-25)

### Important fixes
* Fix restoring window properties at startup.
* Fix a segfault when restarting kernels.
* Fix a segfault when processing linting results.

### Issues Closed

* [Issue 15002](https://github.com/spyder-ide/spyder/issues/15002) - Segfault when restarting the kernel while restarting ([PR 15001](https://github.com/spyder-ide/spyder/pull/15001) by [@impact27](https://github.com/impact27))
* [Issue 14962](https://github.com/spyder-ide/spyder/issues/14962) - Spyder 4.2.4 Regression - Custom Layouts Broken ([PR 14970](https://github.com/spyder-ide/spyder/pull/14970) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14798](https://github.com/spyder-ide/spyder/issues/14798) - Spyder crashes without warning ([PR 14985](https://github.com/spyder-ide/spyder/pull/14985) by [@impact27](https://github.com/impact27))

In this release 3 issues were closed.

* [PR 15001](https://github.com/spyder-ide/spyder/pull/15001) - PR: Avoid segfault when restarting kernel, by [@impact27](https://github.com/impact27) ([15002](https://github.com/spyder-ide/spyder/issues/15002))
* [PR 14985](https://github.com/spyder-ide/spyder/pull/14985) - PR: Avoid segfault when processing code analysis results, by [@impact27](https://github.com/impact27) ([14798](https://github.com/spyder-ide/spyder/issues/14798))
* [PR 14970](https://github.com/spyder-ide/spyder/pull/14970) - PR: Pass version kwarg in every call to saveState/restoreState (Main Window), by [@ccordoba12](https://github.com/ccordoba12) ([14962](https://github.com/spyder-ide/spyder/issues/14962))

In this release 3 pull requests were closed.


----


## Version 4.2.4 (2021-03-19)

### Important fixes
* Fix an important error when restarting kernels.
* Add compatibility with the future Spyder 5.

### Issues Closed

* [Issue 14901](https://github.com/spyder-ide/spyder/issues/14901) - AttributeError: no attribute 'refresh_formatter_name' when opening Spyder ([PR 14943](https://github.com/spyder-ide/spyder/pull/14943) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14886](https://github.com/spyder-ide/spyder/issues/14886) - KeyError after failed import in debugger
* [Issue 14701](https://github.com/spyder-ide/spyder/issues/14701) - Spyder.ttf font has print and preview only restrictions ([PR 14904](https://github.com/spyder-ide/spyder/pull/14904) by [@juliangilbey](https://github.com/juliangilbey))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 14957](https://github.com/spyder-ide/spyder/pull/14957) - PR: Use version arg explicitly in saveState/restoreState (Main Window), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14956](https://github.com/spyder-ide/spyder/pull/14956) - PR: Update hexstate handling to fallback to default layout when moving from Spyder 5 to Spyder 4, by [@dalthviz](https://github.com/dalthviz)
* [PR 14950](https://github.com/spyder-ide/spyder/pull/14950) - PR: Use QtAwesome 1.0.1 for the file tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14943](https://github.com/spyder-ide/spyder/pull/14943) - PR: Catch an error when updating the Source menu at startup, by [@ccordoba12](https://github.com/ccordoba12) ([14901](https://github.com/spyder-ide/spyder/issues/14901))
* [PR 14941](https://github.com/spyder-ide/spyder/pull/14941) - PR: Update required versions on qtconsole and qdarkstyle, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14904](https://github.com/spyder-ide/spyder/pull/14904) - PR: Mark spyder.ttf as an unrestricted font, by [@juliangilbey](https://github.com/juliangilbey) ([14701](https://github.com/spyder-ide/spyder/issues/14701))
* [PR 14903](https://github.com/spyder-ide/spyder/pull/14903) - PR: Add TypeError as a Picklingerror (Variable Explorer), by [@impact27](https://github.com/impact27)
* [PR 14884](https://github.com/spyder-ide/spyder/pull/14884) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)

In this release 8 pull requests were closed.


----


## Version 4.2.3 (2021-03-04)

### Important fixes
* Fix a very visible bug with Kite installation.
* Make Find pane to correctly highlight results in the editor.
* Don't show "Mo such comm" message when restaring kernels.

### Issues Closed

* [Issue 14835](https://github.com/spyder-ide/spyder/issues/14835) - Editing in 4.2.2 causes issue popup ([PR 14842](https://github.com/spyder-ide/spyder/pull/14842) by [@andfoy](https://github.com/andfoy))
* [Issue 14801](https://github.com/spyder-ide/spyder/issues/14801) - Kite installation error ([PR 14816](https://github.com/spyder-ide/spyder/pull/14816) by [@steff456](https://github.com/steff456))
* [Issue 14755](https://github.com/spyder-ide/spyder/issues/14755) - Find in files plugin does not forward results to editor properly ([PR 14770](https://github.com/spyder-ide/spyder/pull/14770) by [@impact27](https://github.com/impact27))
* [Issue 14713](https://github.com/spyder-ide/spyder/issues/14713) - python "help" command failed in iPython console ([PR 14804](https://github.com/spyder-ide/spyder/pull/14804) by [@mrclary](https://github.com/mrclary))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 14842](https://github.com/spyder-ide/spyder/pull/14842) - PR: Prevent IndexError when updating folding, by [@andfoy](https://github.com/andfoy) ([14835](https://github.com/spyder-ide/spyder/issues/14835))
* [PR 14840](https://github.com/spyder-ide/spyder/pull/14840) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 14816](https://github.com/spyder-ide/spyder/pull/14816) - PR: Remove unexpected argument in Kite installation dialog, by [@steff456](https://github.com/steff456) ([14801](https://github.com/spyder-ide/spyder/issues/14801))
* [PR 14805](https://github.com/spyder-ide/spyder/pull/14805) - PR: Remove "No such comm" warning, by [@impact27](https://github.com/impact27)
* [PR 14804](https://github.com/spyder-ide/spyder/pull/14804) - PR: Patch py2app site.py template for IPython help(), by [@mrclary](https://github.com/mrclary) ([14713](https://github.com/spyder-ide/spyder/issues/14713))
* [PR 14770](https://github.com/spyder-ide/spyder/pull/14770) - PR: Fix match in Find plugin, by [@impact27](https://github.com/impact27) ([14755](https://github.com/spyder-ide/spyder/issues/14755))

In this release 6 pull requests were closed.


----


## Version 4.2.2 (2021-02-22)

### Important fixes
* Improve performance when typing in the editor.
* Make variable explorer work for kernels started in remote servers.
* Fix using TKinter in the Windows and macOS installers.

### Issues Closed

* [Issue 14779](https://github.com/spyder-ide/spyder/issues/14779) - SystemError when switching projects ([PR 14791](https://github.com/spyder-ide/spyder/pull/14791) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14730](https://github.com/spyder-ide/spyder/issues/14730) - Bug at code folding of code cells
* [Issue 14656](https://github.com/spyder-ide/spyder/issues/14656) - Tk graphics backend is giving error on Big Sur with DMG installer
* [Issue 14653](https://github.com/spyder-ide/spyder/issues/14653) - Possible Black Autoformat Bug ([PR 14759](https://github.com/spyder-ide/spyder/pull/14759) by [@andfoy](https://github.com/andfoy))
* [Issue 14570](https://github.com/spyder-ide/spyder/issues/14570) - Lags appear when typing in large files in the editor ([PR 14574](https://github.com/spyder-ide/spyder/pull/14574) by [@andfoy](https://github.com/andfoy))
* [Issue 14551](https://github.com/spyder-ide/spyder/issues/14551) - functools.cached_property doesn't behave as expected in the spyder console ([PR 14715](https://github.com/spyder-ide/spyder/pull/14715) by [@impact27](https://github.com/impact27))
* [Issue 14542](https://github.com/spyder-ide/spyder/issues/14542) - Opening Dataframe in Variable Explorer not working with packaged 4.2.1 dmg version of Spyder ([PR 14545](https://github.com/spyder-ide/spyder/pull/14545) by [@mrclary](https://github.com/mrclary))
* [Issue 14535](https://github.com/spyder-ide/spyder/issues/14535) - DeprecationWarning: implicit conversion to integers in spyder/widgets/colors.py:78 ([PR 14543](https://github.com/spyder-ide/spyder/pull/14543) by [@juliangilbey](https://github.com/juliangilbey))
* [Issue 14527](https://github.com/spyder-ide/spyder/issues/14527) - Variable explorer sorting by Size ([PR 14761](https://github.com/spyder-ide/spyder/pull/14761) by [@steff456](https://github.com/steff456))
* [Issue 14499](https://github.com/spyder-ide/spyder/issues/14499) - outline view display variables and attributes
* [Issue 14483](https://github.com/spyder-ide/spyder/issues/14483) - Launch Issues with 4.2.1 and macOS ([PR 14564](https://github.com/spyder-ide/spyder/pull/14564) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14477](https://github.com/spyder-ide/spyder/issues/14477) - Debugger ignores some tuple assignments ([PR 14484](https://github.com/spyder-ide/spyder/pull/14484) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14476](https://github.com/spyder-ide/spyder/issues/14476) - Make Pdb continuation prompt consistent ([PR 14478](https://github.com/spyder-ide/spyder/pull/14478) by [@impact27](https://github.com/impact27))
* [Issue 14472](https://github.com/spyder-ide/spyder/issues/14472) - Hitting debug twice makes it unable to continue ([PR 14711](https://github.com/spyder-ide/spyder/pull/14711) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14413](https://github.com/spyder-ide/spyder/issues/14413) - TypeError in Outline explorer ([PR 14757](https://github.com/spyder-ide/spyder/pull/14757) by [@andfoy](https://github.com/andfoy))
* [Issue 14385](https://github.com/spyder-ide/spyder/issues/14385) - Tkinter failed to import ([PR 14727](https://github.com/spyder-ide/spyder/pull/14727) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14380](https://github.com/spyder-ide/spyder/issues/14380) - Debug mode not working on win10 for any code ([PR 14382](https://github.com/spyder-ide/spyder/pull/14382) by [@impact27](https://github.com/impact27))
* [Issue 14374](https://github.com/spyder-ide/spyder/issues/14374) - Matching bracket highlighting index error ([PR 14376](https://github.com/spyder-ide/spyder/pull/14376) by [@hengin](https://github.com/hengin))
* [Issue 14273](https://github.com/spyder-ide/spyder/issues/14273) - Spyder crashes after Monitor Scale change ([PR 14696](https://github.com/spyder-ide/spyder/pull/14696) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13252](https://github.com/spyder-ide/spyder/issues/13252) - Can't set custom interpreters in Preferences on macOS ([PR 14565](https://github.com/spyder-ide/spyder/pull/14565) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12663](https://github.com/spyder-ide/spyder/issues/12663) - Cursor moves position after deleting a character and changing line ([PR 14559](https://github.com/spyder-ide/spyder/pull/14559) by [@hengin](https://github.com/hengin))
* [Issue 11538](https://github.com/spyder-ide/spyder/issues/11538) - Variable explorer doesn't show variables on remote kernel ([PR 14447](https://github.com/spyder-ide/spyder/pull/14447) by [@impact27](https://github.com/impact27))
* [Issue 9179](https://github.com/spyder-ide/spyder/issues/9179) - brace matching confused by strings with braces ([PR 14376](https://github.com/spyder-ide/spyder/pull/14376) by [@hengin](https://github.com/hengin))
* [Issue 5401](https://github.com/spyder-ide/spyder/issues/5401) - Ctrl+C not working when using input on Windows ([PR 14557](https://github.com/spyder-ide/spyder/pull/14557) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 2965](https://github.com/spyder-ide/spyder/issues/2965) - Parenthesis highlight in the Editor is inconsistent ([PR 14376](https://github.com/spyder-ide/spyder/pull/14376) by [@hengin](https://github.com/hengin))
* [Issue 1354](https://github.com/spyder-ide/spyder/issues/1354) - The editor adds ":" when type in multiply lines list comprehension ([PR 14376](https://github.com/spyder-ide/spyder/pull/14376) by [@hengin](https://github.com/hengin))

In this release 26 issues were closed.

### Pull Requests Merged

* [PR 14794](https://github.com/spyder-ide/spyder/pull/14794) - PR: Update core dependencies for 4.2.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14791](https://github.com/spyder-ide/spyder/pull/14791) - PR: Constrain Watchdog to be less than 2.0.0, by [@ccordoba12](https://github.com/ccordoba12) ([14779](https://github.com/spyder-ide/spyder/issues/14779))
* [PR 14790](https://github.com/spyder-ide/spyder/pull/14790) - PR: Simplify how we enter debugging mode in IPython console tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14763](https://github.com/spyder-ide/spyder/pull/14763) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 14762](https://github.com/spyder-ide/spyder/pull/14762) - PR: Update translations for 4.2.2, by [@steff456](https://github.com/steff456)
* [PR 14761](https://github.com/spyder-ide/spyder/pull/14761) - PR: Catch type error when sorting by size in variable explorer, by [@steff456](https://github.com/steff456) ([14527](https://github.com/spyder-ide/spyder/issues/14527))
* [PR 14759](https://github.com/spyder-ide/spyder/pull/14759) - PR: Prevent double saving when running a file, by [@andfoy](https://github.com/andfoy) ([14653](https://github.com/spyder-ide/spyder/issues/14653))
* [PR 14757](https://github.com/spyder-ide/spyder/pull/14757) - PR: Prevent None items in Outline Explorer, by [@andfoy](https://github.com/andfoy) ([14413](https://github.com/spyder-ide/spyder/issues/14413))
* [PR 14727](https://github.com/spyder-ide/spyder/pull/14727) - PR: Add assets for Tkinter (Windows installer), by [@dalthviz](https://github.com/dalthviz) ([14385](https://github.com/spyder-ide/spyder/issues/14385))
* [PR 14719](https://github.com/spyder-ide/spyder/pull/14719) - PR: Improve design of Kite dialog, by [@juanis2112](https://github.com/juanis2112) ([32](https://github.com/spyder-ide/ux-improvements/issues/32))
* [PR 14715](https://github.com/spyder-ide/spyder/pull/14715) - PR: Test for spyder-kernels#278, by [@impact27](https://github.com/impact27) ([14551](https://github.com/spyder-ide/spyder/issues/14551))
* [PR 14711](https://github.com/spyder-ide/spyder/pull/14711) - PR: Sync subrepo with spyder-kernels#271, by [@ccordoba12](https://github.com/ccordoba12) ([14472](https://github.com/spyder-ide/spyder/issues/14472))
* [PR 14696](https://github.com/spyder-ide/spyder/pull/14696) - PR: Improve DPI change detection , by [@dalthviz](https://github.com/dalthviz) ([14273](https://github.com/spyder-ide/spyder/issues/14273))
* [PR 14667](https://github.com/spyder-ide/spyder/pull/14667) - PR: Move IPython out of zipped libraries in macOS application, by [@mrclary](https://github.com/mrclary)
* [PR 14655](https://github.com/spyder-ide/spyder/pull/14655) - PR: Update metainfo file and install it, by [@ximion](https://github.com/ximion)
* [PR 14624](https://github.com/spyder-ide/spyder/pull/14624) - PR: Fix IPython console for internal environment on macOS app, by [@mrclary](https://github.com/mrclary)
* [PR 14607](https://github.com/spyder-ide/spyder/pull/14607) - PR: Don't terminate folding thread before running new update (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14600](https://github.com/spyder-ide/spyder/pull/14600) - PR: Compute extended ranges for folding out of its thread (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14574](https://github.com/spyder-ide/spyder/pull/14574) - PR: Move folding update to a thread, by [@andfoy](https://github.com/andfoy) ([14570](https://github.com/spyder-ide/spyder/issues/14570))
* [PR 14565](https://github.com/spyder-ide/spyder/pull/14565) - PR: Remove PYTHONEXECUTABLE from env vars passed to the kernel, by [@ccordoba12](https://github.com/ccordoba12) ([13252](https://github.com/spyder-ide/spyder/issues/13252))
* [PR 14564](https://github.com/spyder-ide/spyder/pull/14564) - PR: Don't open script that starts Spyder at startup on macOS, by [@ccordoba12](https://github.com/ccordoba12) ([14483](https://github.com/spyder-ide/spyder/issues/14483))
* [PR 14559](https://github.com/spyder-ide/spyder/pull/14559) - PR: Workaround for Qt-bug where cursor moves unintuitively after text deletion, by [@hengin](https://github.com/hengin) ([12663](https://github.com/spyder-ide/spyder/issues/12663))
* [PR 14557](https://github.com/spyder-ide/spyder/pull/14557) - PR: Sync subrepo with spyder-kernels#277, by [@ccordoba12](https://github.com/ccordoba12) ([5401](https://github.com/spyder-ide/spyder/issues/5401))
* [PR 14552](https://github.com/spyder-ide/spyder/pull/14552) - PR: Update release instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14545](https://github.com/spyder-ide/spyder/pull/14545) - PR: Fix Variable Explorer pandas KeyError in macOS App, by [@mrclary](https://github.com/mrclary) ([14542](https://github.com/spyder-ide/spyder/issues/14542))
* [PR 14543](https://github.com/spyder-ide/spyder/pull/14543) - Fix DeprecationWarning: explicitly cast to an integer, by [@juliangilbey](https://github.com/juliangilbey) ([14535](https://github.com/spyder-ide/spyder/issues/14535))
* [PR 14514](https://github.com/spyder-ide/spyder/pull/14514) - PR: Fix test compatibility with Pandas 1.2.0, by [@dalthviz](https://github.com/dalthviz)
* [PR 14484](https://github.com/spyder-ide/spyder/pull/14484) - PR: Update subrepo with spyder-kernels#272, by [@ccordoba12](https://github.com/ccordoba12) ([14477](https://github.com/spyder-ide/spyder/issues/14477))
* [PR 14482](https://github.com/spyder-ide/spyder/pull/14482) - PR: Save prompt number while recursive debugging, by [@impact27](https://github.com/impact27)
* [PR 14478](https://github.com/spyder-ide/spyder/pull/14478) - PR: Update continuation prompt, by [@impact27](https://github.com/impact27) ([14476](https://github.com/spyder-ide/spyder/issues/14476))
* [PR 14447](https://github.com/spyder-ide/spyder/pull/14447) - PR: Tunnel comm port to make all features that depend on comms work for remote kernels, by [@impact27](https://github.com/impact27) ([11538](https://github.com/spyder-ide/spyder/issues/11538))
* [PR 14382](https://github.com/spyder-ide/spyder/pull/14382) - PR: Make Pdb work better without comms, by [@impact27](https://github.com/impact27) ([14380](https://github.com/spyder-ide/spyder/issues/14380))
* [PR 14376](https://github.com/spyder-ide/spyder/pull/14376) - PR: Bracket matching fixes (affects highlighting and autocompletion), by [@hengin](https://github.com/hengin) ([9179](https://github.com/spyder-ide/spyder/issues/9179), [2965](https://github.com/spyder-ide/spyder/issues/2965), [14374](https://github.com/spyder-ide/spyder/issues/14374), [1354](https://github.com/spyder-ide/spyder/issues/1354))
* [PR 13864](https://github.com/spyder-ide/spyder/pull/13864) - PR: Synchronize symbols and folding after a timeout (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13541](https://github.com/spyder-ide/spyder/pull/13541) - PR: Don't add manics conda channel to Binder's environment.yml, by [@yuvipanda](https://github.com/yuvipanda)

In this release 35 pull requests were closed.


----


## Version 4.2.1 (2020-12-18)

### New features

* Code folding for cells.

### Important fixes

* Search in the editor works as expected for folded regions.
* IPython Console preferences are applied on the fly.
* IPython files (`*.ipy`) are better supported in the editor.
* Reduce time to show Preferences dialog.
* Support for macOS Big Sur.

### Issues Closed

* [Issue 14440](https://github.com/spyder-ide/spyder/issues/14440) - Missing "magic" key for custom color schemes ([PR 14450](https://github.com/spyder-ide/spyder/pull/14450) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14404](https://github.com/spyder-ide/spyder/issues/14404) - Apply asyncio patch for Tornado < 6.1 ([PR 14414](https://github.com/spyder-ide/spyder/pull/14414) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14377](https://github.com/spyder-ide/spyder/issues/14377) - Kernel running well on Python 3.9 for Spyder 4.2 but the title of app still showing 3.7? ([PR 14396](https://github.com/spyder-ide/spyder/pull/14396) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14348](https://github.com/spyder-ide/spyder/issues/14348) - Not working working directory (-w) of project (-p) from command line ([PR 14227](https://github.com/spyder-ide/spyder/pull/14227) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14330](https://github.com/spyder-ide/spyder/issues/14330) - Spyder freezes for a long period every time preferences is open due to checking conda envs ([PR 14332](https://github.com/spyder-ide/spyder/pull/14332) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14329](https://github.com/spyder-ide/spyder/issues/14329) - Consider changing the tooltip in the Files pane filter toggle to be less confusing and match the others ([PR 14359](https://github.com/spyder-ide/spyder/pull/14359) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14328](https://github.com/spyder-ide/spyder/issues/14328) - Changing the filename filters doesn't update files shown if filters are enabled until the button is toggled off and back on ([PR 14337](https://github.com/spyder-ide/spyder/pull/14337) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14309](https://github.com/spyder-ide/spyder/issues/14309) - New way to update folding regions (PR #13783) freezes Spyder ([PR 14315](https://github.com/spyder-ide/spyder/pull/14315) by [@andfoy](https://github.com/andfoy))
* [Issue 14282](https://github.com/spyder-ide/spyder/issues/14282) - The extra selection is not sometimes displayed. ([PR 14295](https://github.com/spyder-ide/spyder/pull/14295) by [@ok97465](https://github.com/ok97465))
* [Issue 14263](https://github.com/spyder-ide/spyder/issues/14263) - Flags logic is broken for small files ([PR 14266](https://github.com/spyder-ide/spyder/pull/14266) by [@impact27](https://github.com/impact27))
* [Issue 14262](https://github.com/spyder-ide/spyder/issues/14262) - Code Analysis not working in packaged 4.2 MacOS app ([PR 14269](https://github.com/spyder-ide/spyder/pull/14269) by [@mrclary](https://github.com/mrclary))
* [Issue 14243](https://github.com/spyder-ide/spyder/issues/14243) - Add wheel for rtree to Mac installer ([PR 14410](https://github.com/spyder-ide/spyder/pull/14410) by [@mrclary](https://github.com/mrclary))
* [Issue 14222](https://github.com/spyder-ide/spyder/issues/14222) - Cannot launch Spyder after updating to macOS 11 Big Sur, please help. ([PR 14256](https://github.com/spyder-ide/spyder/pull/14256) by [@impact27](https://github.com/impact27))
* [Issue 14221](https://github.com/spyder-ide/spyder/issues/14221) - Move symbol switcher to use LSP symbols ([PR 14244](https://github.com/spyder-ide/spyder/pull/14244) by [@andfoy](https://github.com/andfoy))
* [Issue 14220](https://github.com/spyder-ide/spyder/issues/14220) - Improvements to the Windows installer ([PR 14279](https://github.com/spyder-ide/spyder/pull/14279) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14218](https://github.com/spyder-ide/spyder/issues/14218) - High typing latency in MacOS Big Sur ([PR 14256](https://github.com/spyder-ide/spyder/pull/14256) by [@impact27](https://github.com/impact27))
* [Issue 14203](https://github.com/spyder-ide/spyder/issues/14203) - Spyder 4.2 tour dialog box not respecting light theme from previous spyder ([PR 14420](https://github.com/spyder-ide/spyder/pull/14420) by [@juanis2112](https://github.com/juanis2112))
* [Issue 14192](https://github.com/spyder-ide/spyder/issues/14192) - Pager when getting help blocks IPython console ([PR 14418](https://github.com/spyder-ide/spyder/pull/14418) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14183](https://github.com/spyder-ide/spyder/issues/14183) - TypeError when getting text snippets ([PR 14186](https://github.com/spyder-ide/spyder/pull/14186) by [@andfoy](https://github.com/andfoy))
* [Issue 14175](https://github.com/spyder-ide/spyder/issues/14175) - Allow setting line length, when setting `black` as autoformatter ([PR 14187](https://github.com/spyder-ide/spyder/pull/14187) by [@steff456](https://github.com/steff456))
* [Issue 14155](https://github.com/spyder-ide/spyder/issues/14155) - Dictionary has keys and values mixed up ([PR 14333](https://github.com/spyder-ide/spyder/pull/14333) by [@hengin](https://github.com/hengin))
* [Issue 14152](https://github.com/spyder-ide/spyder/issues/14152) - Items are collapsed in the outline explorer after a change was made in the editor when the option "Follow cursor position" is unchecked. ([PR 14238](https://github.com/spyder-ide/spyder/pull/14238) by [@andfoy](https://github.com/andfoy))
* [Issue 14112](https://github.com/spyder-ide/spyder/issues/14112) - Execute permission bits are set to 1 for newly created files ([PR 14246](https://github.com/spyder-ide/spyder/pull/14246) by [@dalthviz](https://github.com/dalthviz))
* [Issue 14100](https://github.com/spyder-ide/spyder/issues/14100) - PermissionError when trying to change current working directory ([PR 14278](https://github.com/spyder-ide/spyder/pull/14278) by [@steff456](https://github.com/steff456))
* [Issue 13779](https://github.com/spyder-ide/spyder/issues/13779) - Crash while folding code block/function ([PR 13783](https://github.com/spyder-ide/spyder/pull/13783) by [@andfoy](https://github.com/andfoy))
* [Issue 13544](https://github.com/spyder-ide/spyder/issues/13544) - Pandas Series index wrong in Variable Explorer ([PR 14259](https://github.com/spyder-ide/spyder/pull/14259) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13535](https://github.com/spyder-ide/spyder/issues/13535) - Code Analysis output button and path handling on Windows ([PR 14305](https://github.com/spyder-ide/spyder/pull/14305) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13288](https://github.com/spyder-ide/spyder/issues/13288) - TimeoutError: Timeout while waiting for comm port. ([PR 14228](https://github.com/spyder-ide/spyder/pull/14228) by [@impact27](https://github.com/impact27))
* [Issue 13248](https://github.com/spyder-ide/spyder/issues/13248) - RuntimeError when trying to detect if completion widget is visible after closing editor window ([PR 14344](https://github.com/spyder-ide/spyder/pull/14344) by [@steff456](https://github.com/steff456))
* [Issue 12877](https://github.com/spyder-ide/spyder/issues/12877) - ValueError when opening array within array ([PR 14352](https://github.com/spyder-ide/spyder/pull/14352) by [@hengin](https://github.com/hengin))
* [Issue 12485](https://github.com/spyder-ide/spyder/issues/12485) - Collapsed code search bug ([PR 14398](https://github.com/spyder-ide/spyder/pull/14398) by [@andfoy](https://github.com/andfoy))
* [Issue 11360](https://github.com/spyder-ide/spyder/issues/11360) - Code Folding Occasionally Breaks ([PR 13783](https://github.com/spyder-ide/spyder/pull/13783) by [@andfoy](https://github.com/andfoy))
* [Issue 11357](https://github.com/spyder-ide/spyder/issues/11357) - IPython Console: Improvements for preferences application ([PR 12834](https://github.com/spyder-ide/spyder/pull/12834) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11090](https://github.com/spyder-ide/spyder/issues/11090) - Magics are marked as invalid syntax in ipy files ([PR 11101](https://github.com/spyder-ide/spyder/pull/11101) by [@impact27](https://github.com/impact27))
* [Issue 7846](https://github.com/spyder-ide/spyder/issues/7846) - Code folding cells
* [Issue 1983](https://github.com/spyder-ide/spyder/issues/1983) - Windows taskbar icon appears twice, if the Spyder icon is pinned ([PR 14219](https://github.com/spyder-ide/spyder/pull/14219) by [@dalthviz](https://github.com/dalthviz))

In this release 36 issues were closed.

### Pull Requests Merged

* [PR 14456](https://github.com/spyder-ide/spyder/pull/14456) - PR: Update core deps, by [@dalthviz](https://github.com/dalthviz)
* [PR 14453](https://github.com/spyder-ide/spyder/pull/14453) - PR: Set color of pager label (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14452](https://github.com/spyder-ide/spyder/pull/14452) - PR: Preserve custom interpreters introduced manually (Main interpreter), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14451](https://github.com/spyder-ide/spyder/pull/14451) - PR: Show Kite's on-boarding dialog the third time Spyder is started, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14450](https://github.com/spyder-ide/spyder/pull/14450) - PR: Add default values for color schemes, by [@dalthviz](https://github.com/dalthviz) ([14440](https://github.com/spyder-ide/spyder/issues/14440))
* [PR 14444](https://github.com/spyder-ide/spyder/pull/14444) - PR: Add .pyt and .pyi as extensions recognized as Python files (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14443](https://github.com/spyder-ide/spyder/pull/14443) - PR: Remove option to set max number of lines (History), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14430](https://github.com/spyder-ide/spyder/pull/14430) - PR: Fix validation for incorrectly uninstalled packages in is_module_installed, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14420](https://github.com/spyder-ide/spyder/pull/14420) - PR: Change colors for tour dialog in light mode, by [@juanis2112](https://github.com/juanis2112) ([14203](https://github.com/spyder-ide/spyder/issues/14203))
* [PR 14418](https://github.com/spyder-ide/spyder/pull/14418) - PR: Show a warning telling people how to get out of the pager (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([14192](https://github.com/spyder-ide/spyder/issues/14192))
* [PR 14415](https://github.com/spyder-ide/spyder/pull/14415) - PR: Update minimal required versions of python-language-server and pyls-spyder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14414](https://github.com/spyder-ide/spyder/pull/14414) - PR: Don't apply asyncio patch for Tornado 6.1+ (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([14404](https://github.com/spyder-ide/spyder/issues/14404))
* [PR 14410](https://github.com/spyder-ide/spyder/pull/14410) - PR: Add Rtree and other fixes for the macOS app, by [@mrclary](https://github.com/mrclary) ([14243](https://github.com/spyder-ide/spyder/issues/14243))
* [PR 14408](https://github.com/spyder-ide/spyder/pull/14408) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 14407](https://github.com/spyder-ide/spyder/pull/14407) - PR: Update translations, by [@andfoy](https://github.com/andfoy)
* [PR 14398](https://github.com/spyder-ide/spyder/pull/14398) - PR: Improve unfold_if_colapsed logic to consider nested blocks, by [@andfoy](https://github.com/andfoy) ([12485](https://github.com/spyder-ide/spyder/issues/12485))
* [PR 14396](https://github.com/spyder-ide/spyder/pull/14396) - PR: Don't show Python version on window title for our Mac and Windows apps, by [@ccordoba12](https://github.com/ccordoba12) ([14377](https://github.com/spyder-ide/spyder/issues/14377))
* [PR 14390](https://github.com/spyder-ide/spyder/pull/14390) - PR: Pin cryptography to 3.2.1 to avoid issues with lack of wheels for version 3.3 (Windows installer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14389](https://github.com/spyder-ide/spyder/pull/14389) - PR: Change colors for tour dialog in light mode, by [@juanis2112](https://github.com/juanis2112)
* [PR 14387](https://github.com/spyder-ide/spyder/pull/14387) - PR: Add python_requires to setup.py, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14367](https://github.com/spyder-ide/spyder/pull/14367) - PR: Change application of options that require direct code execution (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14366](https://github.com/spyder-ide/spyder/pull/14366) - PR: Sync spyder-kernels subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14359](https://github.com/spyder-ide/spyder/pull/14359) - PR: Use a single tooltip for the Files filter button, by [@ccordoba12](https://github.com/ccordoba12) ([14329](https://github.com/spyder-ide/spyder/issues/14329))
* [PR 14352](https://github.com/spyder-ide/spyder/pull/14352) - PR: Fix error when opening array of boolean arrays in Variable Explorer, by [@hengin](https://github.com/hengin) ([12877](https://github.com/spyder-ide/spyder/issues/12877))
* [PR 14350](https://github.com/spyder-ide/spyder/pull/14350) - PR: Use Pyzmq 19 on Windows (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14344](https://github.com/spyder-ide/spyder/pull/14344) - PR: Catch RuntimeError in the editor, by [@steff456](https://github.com/steff456) ([13248](https://github.com/spyder-ide/spyder/issues/13248))
* [PR 14342](https://github.com/spyder-ide/spyder/pull/14342) - PR: Increase IPython version to 7.6.0+, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14337](https://github.com/spyder-ide/spyder/pull/14337) - PR: Update view after applying filters if filters are on (Files), by [@ccordoba12](https://github.com/ccordoba12) ([14328](https://github.com/spyder-ide/spyder/issues/14328))
* [PR 14333](https://github.com/spyder-ide/spyder/pull/14333) - PR: Fix variable explorer sort by size bug, by [@hengin](https://github.com/hengin) ([14155](https://github.com/spyder-ide/spyder/issues/14155))
* [PR 14332](https://github.com/spyder-ide/spyder/pull/14332) - PR: Improve detection of conda and pyenv environments, by [@ccordoba12](https://github.com/ccordoba12) ([14330](https://github.com/spyder-ide/spyder/issues/14330))
* [PR 14318](https://github.com/spyder-ide/spyder/pull/14318) - PR: Fix issues with external kernels runfile and shutdown, by [@impact27](https://github.com/impact27)
* [PR 14315](https://github.com/spyder-ide/spyder/pull/14315) - PR: Replace Jaro-Wrinkler distance by normalized Jaccard index (Folding), by [@andfoy](https://github.com/andfoy) ([14309](https://github.com/spyder-ide/spyder/issues/14309))
* [PR 14308](https://github.com/spyder-ide/spyder/pull/14308) - PR: Prevent comms from crashing Spyder, by [@impact27](https://github.com/impact27)
* [PR 14305](https://github.com/spyder-ide/spyder/pull/14305) - PR: Normalize file paths for correct handling of filenames for static code analysis, by [@dalthviz](https://github.com/dalthviz) ([13535](https://github.com/spyder-ide/spyder/issues/13535))
* [PR 14295](https://github.com/spyder-ide/spyder/pull/14295) - PR: Check for initial selection before updating decorations, by [@ok97465](https://github.com/ok97465) ([14282](https://github.com/spyder-ide/spyder/issues/14282))
* [PR 14284](https://github.com/spyder-ide/spyder/pull/14284) - PR: Increase max Pytest version (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14279](https://github.com/spyder-ide/spyder/pull/14279) - PR: Add Rtree wheel to the Windows installer, by [@dalthviz](https://github.com/dalthviz) ([14220](https://github.com/spyder-ide/spyder/issues/14220))
* [PR 14278](https://github.com/spyder-ide/spyder/pull/14278) - PR: Catch IOError and OSError in spyder-kernels get_cwd, by [@steff456](https://github.com/steff456) ([14100](https://github.com/spyder-ide/spyder/issues/14100))
* [PR 14269](https://github.com/spyder-ide/spyder/pull/14269) - PR: Fix Code Analysis in macOS Application, by [@mrclary](https://github.com/mrclary) ([14262](https://github.com/spyder-ide/spyder/issues/14262))
* [PR 14266](https://github.com/spyder-ide/spyder/pull/14266) - PR: Align flags if not enough lines to create a scrollbar, by [@impact27](https://github.com/impact27) ([14263](https://github.com/spyder-ide/spyder/issues/14263))
* [PR 14259](https://github.com/spyder-ide/spyder/pull/14259) - PR: Recalculate index when sorting (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([13544](https://github.com/spyder-ide/spyder/issues/13544))
* [PR 14256](https://github.com/spyder-ide/spyder/pull/14256) - PR: Set QT_MAC_WANTS_LAYER env var to solve problems in Big Sur, by [@impact27](https://github.com/impact27) ([14222](https://github.com/spyder-ide/spyder/issues/14222), [14218](https://github.com/spyder-ide/spyder/issues/14218))
* [PR 14246](https://github.com/spyder-ide/spyder/pull/14246) - PR: Set base permission to 0o666 minus umask for files when saving, by [@dalthviz](https://github.com/dalthviz) ([14112](https://github.com/spyder-ide/spyder/issues/14112))
* [PR 14244](https://github.com/spyder-ide/spyder/pull/14244) - PR: Migrate the symbol switcher to use the LSP information, by [@andfoy](https://github.com/andfoy) ([14221](https://github.com/spyder-ide/spyder/issues/14221))
* [PR 14239](https://github.com/spyder-ide/spyder/pull/14239) - PR: Disable set-env usage on GitHub Actions and update conda action, by [@andfoy](https://github.com/andfoy)
* [PR 14238](https://github.com/spyder-ide/spyder/pull/14238) - PR: Fix issues with expanded symbols when cursor is not being followed up, by [@andfoy](https://github.com/andfoy) ([14152](https://github.com/spyder-ide/spyder/issues/14152))
* [PR 14231](https://github.com/spyder-ide/spyder/pull/14231) - PR: Improve startup time a bit, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14229](https://github.com/spyder-ide/spyder/pull/14229) - PR: Simplify creation of main application and splash screen, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14228](https://github.com/spyder-ide/spyder/pull/14228) - PR: Don't wait for disconnected comm (IPython console), by [@impact27](https://github.com/impact27) ([13288](https://github.com/spyder-ide/spyder/issues/13288))
* [PR 14227](https://github.com/spyder-ide/spyder/pull/14227) - PR: Fix opening projects from the command line, by [@ccordoba12](https://github.com/ccordoba12) ([14348](https://github.com/spyder-ide/spyder/issues/14348))
* [PR 14219](https://github.com/spyder-ide/spyder/pull/14219) - PR: Context menu entry to open files with Spyder and taskbar pinned icon (Windows installer), by [@dalthviz](https://github.com/dalthviz) ([1983](https://github.com/spyder-ide/spyder/issues/1983))
* [PR 14195](https://github.com/spyder-ide/spyder/pull/14195) - PR: Pin NumPy version to prevent RuntimeError - sanity check on Windows installer (Windows 10), by [@dalthviz](https://github.com/dalthviz)
* [PR 14187](https://github.com/spyder-ide/spyder/pull/14187) - PR: Fix bug in preferences with max line length, by [@steff456](https://github.com/steff456) ([14175](https://github.com/spyder-ide/spyder/issues/14175))
* [PR 14186](https://github.com/spyder-ide/spyder/pull/14186) - PR: Prevent indexing prefix tree with None values, by [@andfoy](https://github.com/andfoy) ([14183](https://github.com/spyder-ide/spyder/issues/14183))
* [PR 14185](https://github.com/spyder-ide/spyder/pull/14185) - PR: Don't use len to check for empty sequences (Snippets), by [@ElieGouzien](https://github.com/ElieGouzien)
* [PR 14181](https://github.com/spyder-ide/spyder/pull/14181) - PR: Improve release instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14180](https://github.com/spyder-ide/spyder/pull/14180) - PR: Update our subrepos after releasing 4.2.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14178](https://github.com/spyder-ide/spyder/pull/14178) - PR: Fix conda environment list on Windows application, by [@mrclary](https://github.com/mrclary)
* [PR 14071](https://github.com/spyder-ide/spyder/pull/14071) - PR: Replace deprecated imp with importlib, by [@oscargus](https://github.com/oscargus)
* [PR 13783](https://github.com/spyder-ide/spyder/pull/13783) - PR: Improve folding updates and line displacement on the editor, by [@andfoy](https://github.com/andfoy) ([13779](https://github.com/spyder-ide/spyder/issues/13779), [11360](https://github.com/spyder-ide/spyder/issues/11360))
* [PR 12834](https://github.com/spyder-ide/spyder/pull/12834) - PR: Improve handling of IPython Console preferences, by [@dalthviz](https://github.com/dalthviz) ([11357](https://github.com/spyder-ide/spyder/issues/11357))
* [PR 11101](https://github.com/spyder-ide/spyder/pull/11101) - PR: Support IPython files, by [@impact27](https://github.com/impact27) ([11090](https://github.com/spyder-ide/spyder/issues/11090))

In this release 62 pull requests were closed.


----


## Version 4.2.0 (2020-11-08)

### New features

* New, self-contained installers for Windows and macOS.
* Add support for inline and interactive Matplotlib plots in the debugger.
* Automatic detection of conda and pyenv environments in
  `Preferences > Python interpreter`.
* Add functionality to do auto-formatting in the Editor. It can be triggered in
  the menu `Source > Format file or selection` or with the shorcut
  `Ctrl+Alt+I` (`Cmd+Alt+I` in macOS).
* Add support for text snippets in the Editor. The list of available snippets
  is shown in `Preferences > Completion and linting > Snippets`.
* Support caching cells sent in succession to the IPython console. This will
  run one cell after the previous one finished.
* Make variables take precedence over Pdb commands in the debugger. In case a
  variable clashes with a command, you'll have to prefix the command with `!`.
* Show a message to take a tour of Spyder features the first time 4.2.0 is
  launched.
* Drop support for Python 2.7 and 3.5.

### Important fixes

* Improve performance in the Editor when painting indent guides and showing
  linting messages.
* Prevent the creation of temporary files in Dropbox directories after saving
  in the Editor.
* Prevent the Outline to degrade performance in the Editor when visible. This
  was achieved by moving this pane to use the LSP architecture.
* Support Jedi 0.17.2

### Issues Closed

* [Issue 14163](https://github.com/spyder-ide/spyder/issues/14163) - NameError: name 'DistributionNotFound' is not defined ([PR 14164](https://github.com/spyder-ide/spyder/pull/14164) by [@impact27](https://github.com/impact27))
* [Issue 14140](https://github.com/spyder-ide/spyder/issues/14140) - LSP Server Does Not Startup on macOS Application ([PR 14142](https://github.com/spyder-ide/spyder/pull/14142) by [@mrclary](https://github.com/mrclary))
* [Issue 14136](https://github.com/spyder-ide/spyder/issues/14136) - Conda Environment Status Shows Full Path ([PR 14123](https://github.com/spyder-ide/spyder/pull/14123) by [@mrclary](https://github.com/mrclary))
* [Issue 14125](https://github.com/spyder-ide/spyder/issues/14125) - TypeError when inserting text in code snippet ([PR 14157](https://github.com/spyder-ide/spyder/pull/14157) by [@andfoy](https://github.com/andfoy))
* [Issue 14117](https://github.com/spyder-ide/spyder/issues/14117) - Update translations for 4.2.0 ([PR 14159](https://github.com/spyder-ide/spyder/pull/14159) by [@spyder-bot](https://github.com/spyder-bot))
* [Issue 14113](https://github.com/spyder-ide/spyder/issues/14113) - Error when inserting text in code snippet ([PR 14114](https://github.com/spyder-ide/spyder/pull/14114) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14107](https://github.com/spyder-ide/spyder/issues/14107) - RuntimeError when closing project ([PR 14109](https://github.com/spyder-ide/spyder/pull/14109) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14082](https://github.com/spyder-ide/spyder/issues/14082) - Set column width automatically after changing autoformatter ([PR 14147](https://github.com/spyder-ide/spyder/pull/14147) by [@steff456](https://github.com/steff456))
* [Issue 14040](https://github.com/spyder-ide/spyder/issues/14040) - Pager is broken in IPython console ([PR 14056](https://github.com/spyder-ide/spyder/pull/14056) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14001](https://github.com/spyder-ide/spyder/issues/14001) - Cannot save if remove_trailing_spaces is enabled ([PR 14016](https://github.com/spyder-ide/spyder/pull/14016) by [@andfoy](https://github.com/andfoy))
* [Issue 13999](https://github.com/spyder-ide/spyder/issues/13999) - Error while restarting the kernel ([PR 14057](https://github.com/spyder-ide/spyder/pull/14057) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13985](https://github.com/spyder-ide/spyder/issues/13985) - Bug: Code style linting is ignored after Spyder restart ([PR 14043](https://github.com/spyder-ide/spyder/pull/14043) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13978](https://github.com/spyder-ide/spyder/issues/13978) - Migrate mac-application repo to spyder repo ([PR 13992](https://github.com/spyder-ide/spyder/pull/13992) by [@mrclary](https://github.com/mrclary))
* [Issue 13977](https://github.com/spyder-ide/spyder/issues/13977) - TypeError: 'bool' object is not callable at Spyder startup ([PR 14007](https://github.com/spyder-ide/spyder/pull/14007) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13964](https://github.com/spyder-ide/spyder/issues/13964) - PYTHONPATH not set when running profiler ([PR 14022](https://github.com/spyder-ide/spyder/pull/14022) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13957](https://github.com/spyder-ide/spyder/issues/13957) - Replace with | replace/find next | replace in selection | replace all ([PR 14054](https://github.com/spyder-ide/spyder/pull/14054) by [@TediaN97](https://github.com/TediaN97))
* [Issue 13928](https://github.com/spyder-ide/spyder/issues/13928) - The ouline explorer doesn't populate for some files with latest 4.x ([PR 14119](https://github.com/spyder-ide/spyder/pull/14119) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13918](https://github.com/spyder-ide/spyder/issues/13918) - Debugger panel is not updated correctly in latest 4.x ([PR 13919](https://github.com/spyder-ide/spyder/pull/13919) by [@impact27](https://github.com/impact27))
* [Issue 13909](https://github.com/spyder-ide/spyder/issues/13909) - Variables not defined error while in debug mode when running a list comprehension ([PR 13920](https://github.com/spyder-ide/spyder/pull/13920) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13908](https://github.com/spyder-ide/spyder/issues/13908) - Turning "Highlight current line" off breaks parenthesis matching highlighting ([PR 13281](https://github.com/spyder-ide/spyder/pull/13281) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13903](https://github.com/spyder-ide/spyder/issues/13903) - Add option to list available environments as main interpreter in Preferences ([PR 13950](https://github.com/spyder-ide/spyder/pull/13950) by [@steff456](https://github.com/steff456))
* [Issue 13897](https://github.com/spyder-ide/spyder/issues/13897) - Outline explorer only populate its content after a file is changed on latest 4.x ([PR 13981](https://github.com/spyder-ide/spyder/pull/13981) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13896](https://github.com/spyder-ide/spyder/issues/13896) - Outline exporer items auto expands to follow cursor position in latest 4.x ([PR 13885](https://github.com/spyder-ide/spyder/pull/13885) by [@andfoy](https://github.com/andfoy))
* [Issue 13892](https://github.com/spyder-ide/spyder/issues/13892) - Debugging __init__ impossible ([PR 13902](https://github.com/spyder-ide/spyder/pull/13902) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13891](https://github.com/spyder-ide/spyder/issues/13891) - Creating a pint Quantity in the console fails ([PR 13902](https://github.com/spyder-ide/spyder/pull/13902) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13882](https://github.com/spyder-ide/spyder/issues/13882) - Saving layout doesn't store the right sizes. ([PR 14078](https://github.com/spyder-ide/spyder/pull/14078) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13877](https://github.com/spyder-ide/spyder/issues/13877) - Variable names are displayed in the Outline pane ([PR 13885](https://github.com/spyder-ide/spyder/pull/13885) by [@andfoy](https://github.com/andfoy))
* [Issue 13872](https://github.com/spyder-ide/spyder/issues/13872) - Spinner is shown constantly in Outline explorer for files without a language server ([PR 13885](https://github.com/spyder-ide/spyder/pull/13885) by [@andfoy](https://github.com/andfoy))
* [Issue 13832](https://github.com/spyder-ide/spyder/issues/13832) - Replace kite dialog when opening spyder the first time for the tour dialog. ([PR 13953](https://github.com/spyder-ide/spyder/pull/13953) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13807](https://github.com/spyder-ide/spyder/issues/13807) - "Go to definition" causes error in Python 3.6 ([PR 13839](https://github.com/spyder-ide/spyder/pull/13839) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13806](https://github.com/spyder-ide/spyder/issues/13806) - object.[tab] causes internal error in IPython console ([PR 13830](https://github.com/spyder-ide/spyder/pull/13830) by [@steff456](https://github.com/steff456))
* [Issue 13786](https://github.com/spyder-ide/spyder/issues/13786) - A generic icon is shown in gnome-shell in a Wayland session ([PR 13787](https://github.com/spyder-ide/spyder/pull/13787) by [@musicinmybrain](https://github.com/musicinmybrain))
* [Issue 13762](https://github.com/spyder-ide/spyder/issues/13762) - Highlighting word when there is only one occurence ([PR 13834](https://github.com/spyder-ide/spyder/pull/13834) by [@steff456](https://github.com/steff456))
* [Issue 13754](https://github.com/spyder-ide/spyder/issues/13754) - Change colors for IPython console error message ([PR 13963](https://github.com/spyder-ide/spyder/pull/13963) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13741](https://github.com/spyder-ide/spyder/issues/13741) - Fix PYTHONPATH manager tooltip to match the title of the dialog window it triggers ([PR 13817](https://github.com/spyder-ide/spyder/pull/13817) by [@juanitagomezr](https://github.com/juanitagomezr))
* [Issue 13733](https://github.com/spyder-ide/spyder/issues/13733) - Variable type and size are out of order ([PR 13791](https://github.com/spyder-ide/spyder/pull/13791) by [@skjerns](https://github.com/skjerns))
* [Issue 13722](https://github.com/spyder-ide/spyder/issues/13722) - Spyder doesn't create a new folder in project explorer ([PR 13740](https://github.com/spyder-ide/spyder/pull/13740) by [@akwasigroch](https://github.com/akwasigroch))
* [Issue 13719](https://github.com/spyder-ide/spyder/issues/13719) - IPython.core.inputtransformer2 is only present in IPython >= 7.0 ([PR 13721](https://github.com/spyder-ide/spyder/pull/13721) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13668](https://github.com/spyder-ide/spyder/issues/13668) - Internal console inserts unwanted red highlighting on background ([PR 13281](https://github.com/spyder-ide/spyder/pull/13281) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13666](https://github.com/spyder-ide/spyder/issues/13666) - Internal console inserts unwanted background highlighting on left parenthesis ([PR 13281](https://github.com/spyder-ide/spyder/pull/13281) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13632](https://github.com/spyder-ide/spyder/issues/13632) - Cannot use imported modules with joblib ([PR 13818](https://github.com/spyder-ide/spyder/pull/13818) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13623](https://github.com/spyder-ide/spyder/issues/13623) - Unnecessary error when restarting the kernel ([PR 13634](https://github.com/spyder-ide/spyder/pull/13634) by [@impact27](https://github.com/impact27))
* [Issue 13620](https://github.com/spyder-ide/spyder/issues/13620) - RecursionError when opening a dataframe with Pandas 1.1.0 in the kernel and 1.0.5 in Spyder ([PR 13843](https://github.com/spyder-ide/spyder/pull/13843) by [@steff456](https://github.com/steff456))
* [Issue 13585](https://github.com/spyder-ide/spyder/issues/13585) - Plain text in help pane has a bug ([PR 13598](https://github.com/spyder-ide/spyder/pull/13598) by [@steff456](https://github.com/steff456))
* [Issue 13557](https://github.com/spyder-ide/spyder/issues/13557) - Date object not editable in variable explorer ([PR 13876](https://github.com/spyder-ide/spyder/pull/13876) by [@steff456](https://github.com/steff456))
* [Issue 13531](https://github.com/spyder-ide/spyder/issues/13531) - Run configuration per file dialog doesn't display complete ([PR 13590](https://github.com/spyder-ide/spyder/pull/13590) by [@steff456](https://github.com/steff456))
* [Issue 13519](https://github.com/spyder-ide/spyder/issues/13519) - Builtins can still be shadowed, causing kernel startup to fail, when a project is open ([PR 14017](https://github.com/spyder-ide/spyder/pull/14017) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13507](https://github.com/spyder-ide/spyder/issues/13507) - No xdg-open on VM instance ([PR 13971](https://github.com/spyder-ide/spyder/pull/13971) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13465](https://github.com/spyder-ide/spyder/issues/13465) - Fix some further issues with the Files pane UX ([PR 13833](https://github.com/spyder-ide/spyder/pull/13833) by [@steff456](https://github.com/steff456))
* [Issue 13439](https://github.com/spyder-ide/spyder/issues/13439) - Code analysis and profiler don't have shortcuts assigned ([PR 13970](https://github.com/spyder-ide/spyder/pull/13970) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13371](https://github.com/spyder-ide/spyder/issues/13371) - Add "Insert above/below" options for lists in variable explorer ([PR 13380](https://github.com/spyder-ide/spyder/pull/13380) by [@dpturibio](https://github.com/dpturibio))
* [Issue 13351](https://github.com/spyder-ide/spyder/issues/13351) - Some issues with Spyder projects and the workspace functionality in the PyLS ([PR 13828](https://github.com/spyder-ide/spyder/pull/13828) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13347](https://github.com/spyder-ide/spyder/issues/13347) - Clicking an item in Analyze pane does nothing but return to post-scan initial state ([PR 14090](https://github.com/spyder-ide/spyder/pull/14090) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13342](https://github.com/spyder-ide/spyder/issues/13342) - IndexError in Code Analysis prevents Spyder from getting launched ([PR 13753](https://github.com/spyder-ide/spyder/pull/13753) by [@steff456](https://github.com/steff456))
* [Issue 13283](https://github.com/spyder-ide/spyder/issues/13283) - Can't terminate debugging session ([PR 13379](https://github.com/spyder-ide/spyder/pull/13379) by [@impact27](https://github.com/impact27))
* [Issue 13241](https://github.com/spyder-ide/spyder/issues/13241) - Improvements to the help pane ([PR 13750](https://github.com/spyder-ide/spyder/pull/13750) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13240](https://github.com/spyder-ide/spyder/issues/13240) - Fix Introduction tour ([PR 13717](https://github.com/spyder-ide/spyder/pull/13717) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13239](https://github.com/spyder-ide/spyder/issues/13239) - Add Tutorial Videos item to Spyder Help menu ([PR 13895](https://github.com/spyder-ide/spyder/pull/13895) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13145](https://github.com/spyder-ide/spyder/issues/13145) - Create our own installer for Windows ([PR 13269](https://github.com/spyder-ide/spyder/pull/13269) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13121](https://github.com/spyder-ide/spyder/issues/13121) - TypeError: KiteClient.sig_response_ready in Kite's client ([PR 13884](https://github.com/spyder-ide/spyder/pull/13884) by [@andfoy](https://github.com/andfoy))
* [Issue 13041](https://github.com/spyder-ide/spyder/issues/13041) - Atomic writes generate temp files in Dropbox ([PR 13915](https://github.com/spyder-ide/spyder/pull/13915) by [@skjerns](https://github.com/skjerns))
* [Issue 13020](https://github.com/spyder-ide/spyder/issues/13020) - Editor sluggish on document diagnostics update ([PR 13281](https://github.com/spyder-ide/spyder/pull/13281) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12677](https://github.com/spyder-ide/spyder/issues/12677) - Add instructions about using "conda update anaconda" to the update dialog ([PR 14091](https://github.com/spyder-ide/spyder/pull/14091) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12651](https://github.com/spyder-ide/spyder/issues/12651) - Indentation handling when running code cells (IndentationError: unexpected indent) ([PR 13852](https://github.com/spyder-ide/spyder/pull/13852) by [@impact27](https://github.com/impact27))
* [Issue 12631](https://github.com/spyder-ide/spyder/issues/12631) - Feature Request: --safe-mode in spyder main cli options ([PR 12926](https://github.com/spyder-ide/spyder/pull/12926) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12564](https://github.com/spyder-ide/spyder/issues/12564) - Intended behaviour of add_pathlist_to_PYTHONPATH not clear ([PR 14022](https://github.com/spyder-ide/spyder/pull/14022) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12259](https://github.com/spyder-ide/spyder/issues/12259) - MacApp: Jedi Completion Not Entirely Working from Non-conda environment ([PR 13839](https://github.com/spyder-ide/spyder/pull/13839) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12200](https://github.com/spyder-ide/spyder/issues/12200) - Feature Request: Upgrade Spyder's Environment Handling ([PR 13950](https://github.com/spyder-ide/spyder/pull/13950) by [@steff456](https://github.com/steff456))
* [Issue 12045](https://github.com/spyder-ide/spyder/issues/12045) - Spyder prompts to install command line tools in macOS  ([PR 14105](https://github.com/spyder-ide/spyder/pull/14105) by [@juanis2112](https://github.com/juanis2112))
* [Issue 11396](https://github.com/spyder-ide/spyder/issues/11396) - Integration of automatic formatting tools: autopep8, yapf and black ([PR 13295](https://github.com/spyder-ide/spyder/pull/13295) by [@andfoy](https://github.com/andfoy))
* [Issue 11118](https://github.com/spyder-ide/spyder/issues/11118) - Problem in autocompletion of class attributes in Spyder 4 editor  ([PR 14058](https://github.com/spyder-ide/spyder/pull/14058) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 9725](https://github.com/spyder-ide/spyder/issues/9725) - Shift-Enter to run a cell is not cached ([PR 10873](https://github.com/spyder-ide/spyder/pull/10873) by [@impact27](https://github.com/impact27))
* [Issue 8864](https://github.com/spyder-ide/spyder/issues/8864) - Indent guides makes the Editor extremely slow on large files ([PR 13867](https://github.com/spyder-ide/spyder/pull/13867) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 3161](https://github.com/spyder-ide/spyder/issues/3161) - Check : Profiler unable to find modules ([PR 14022](https://github.com/spyder-ide/spyder/pull/14022) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 620](https://github.com/spyder-ide/spyder/issues/620) - Unable to see plots made with Matplotlib while debugging ([PR 13327](https://github.com/spyder-ide/spyder/pull/13327) by [@impact27](https://github.com/impact27))
* [Issue 588](https://github.com/spyder-ide/spyder/issues/588) - Add support for text snippets ([PR 14019](https://github.com/spyder-ide/spyder/pull/14019) by [@andfoy](https://github.com/andfoy))

In this release 76 issues were closed.

### Pull Requests Merged

* [PR 14170](https://github.com/spyder-ide/spyder/pull/14170) - PR: Update PyLS and spyder-kernels required versions for 4.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14168](https://github.com/spyder-ide/spyder/pull/14168) - PR: Fix logging to a file, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14167](https://github.com/spyder-ide/spyder/pull/14167) - PR: Update subrepo with spyder-kernels#255, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14164](https://github.com/spyder-ide/spyder/pull/14164) - PR: Fix get_package_version, by [@impact27](https://github.com/impact27) ([14163](https://github.com/spyder-ide/spyder/issues/14163))
* [PR 14160](https://github.com/spyder-ide/spyder/pull/14160) - PR: Fix detection of conda and pyenv environments on Windows, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14159](https://github.com/spyder-ide/spyder/pull/14159) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot) ([14117](https://github.com/spyder-ide/spyder/issues/14117))
* [PR 14157](https://github.com/spyder-ide/spyder/pull/14157) - PR: Prevent code snippet search from picking the root text node, by [@andfoy](https://github.com/andfoy) ([14125](https://github.com/spyder-ide/spyder/issues/14125))
* [PR 14154](https://github.com/spyder-ide/spyder/pull/14154) - PR: Fix some strings for translation, by [@juanis2112](https://github.com/juanis2112)
* [PR 14147](https://github.com/spyder-ide/spyder/pull/14147) - PR: Set column width automatically after changing autoformatter, by [@steff456](https://github.com/steff456) ([14082](https://github.com/spyder-ide/spyder/issues/14082))
* [PR 14146](https://github.com/spyder-ide/spyder/pull/14146) - PR: Change default auto-formatter to be Black (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14142](https://github.com/spyder-ide/spyder/pull/14142) - PR: Resolve LSP not starting in Mac app, by [@mrclary](https://github.com/mrclary) ([14140](https://github.com/spyder-ide/spyder/issues/14140))
* [PR 14137](https://github.com/spyder-ide/spyder/pull/14137) - PR: Fix project opening when starting Spyder in Mac app, by [@juanis2112](https://github.com/juanis2112)
* [PR 14135](https://github.com/spyder-ide/spyder/pull/14135) - PR: Update macOS app with new dependencies, by [@mrclary](https://github.com/mrclary)
* [PR 14123](https://github.com/spyder-ide/spyder/pull/14123) - PR: Add search paths to PATH in is_program_installed, by [@mrclary](https://github.com/mrclary) ([14136](https://github.com/spyder-ide/spyder/issues/14136))
* [PR 14119](https://github.com/spyder-ide/spyder/pull/14119) - PR: Check that we can get symbols in a file not part of a Python module, by [@ccordoba12](https://github.com/ccordoba12) ([13928](https://github.com/spyder-ide/spyder/issues/13928))
* [PR 14115](https://github.com/spyder-ide/spyder/pull/14115) - PR: Update translation files, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14114](https://github.com/spyder-ide/spyder/pull/14114) - PR: Add name and value to base node class (Snippets), by [@ccordoba12](https://github.com/ccordoba12) ([14113](https://github.com/spyder-ide/spyder/issues/14113))
* [PR 14109](https://github.com/spyder-ide/spyder/pull/14109) - PR: Catch an error when stopping watcher (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([14107](https://github.com/spyder-ide/spyder/issues/14107))
* [PR 14105](https://github.com/spyder-ide/spyder/pull/14105) - PR: Add find_git function to verify correctly if git is installed on macOS, by [@juanis2112](https://github.com/juanis2112) ([12045](https://github.com/spyder-ide/spyder/issues/12045))
* [PR 14104](https://github.com/spyder-ide/spyder/pull/14104) - PR: Customize tour dialog when starting Spyder, by [@juanis2112](https://github.com/juanis2112) ([22](https://github.com/spyder-ide/ux-improvements/issues/22))
* [PR 14091](https://github.com/spyder-ide/spyder/pull/14091) - PR: Improve message about new releases (Main Window), by [@ccordoba12](https://github.com/ccordoba12) ([12677](https://github.com/spyder-ide/spyder/issues/12677))
* [PR 14090](https://github.com/spyder-ide/spyder/pull/14090) - PR: Don't try to reload analysis for the currently displayed file (Code Analysis), by [@ccordoba12](https://github.com/ccordoba12) ([13347](https://github.com/spyder-ide/spyder/issues/13347))
* [PR 14078](https://github.com/spyder-ide/spyder/pull/14078) - PR: Use current size and position when saving window settings (Main Window), by [@ccordoba12](https://github.com/ccordoba12) ([13882](https://github.com/spyder-ide/spyder/issues/13882))
* [PR 14074](https://github.com/spyder-ide/spyder/pull/14074) - PR: Remove PyYAML deprecation warning, by [@oscargus](https://github.com/oscargus)
* [PR 14059](https://github.com/spyder-ide/spyder/pull/14059) - PR: Add build for Windows installer with extra packages, by [@dalthviz](https://github.com/dalthviz)
* [PR 14058](https://github.com/spyder-ide/spyder/pull/14058) - PR: Update subrepo with python-language-server#879, by [@ccordoba12](https://github.com/ccordoba12) ([11118](https://github.com/spyder-ide/spyder/issues/11118))
* [PR 14057](https://github.com/spyder-ide/spyder/pull/14057) - PR: Catch an error when trying to restart the kernel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([13999](https://github.com/spyder-ide/spyder/issues/13999))
* [PR 14056](https://github.com/spyder-ide/spyder/pull/14056) - PR: Remove option to use pager because it's broken (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([14040](https://github.com/spyder-ide/spyder/issues/14040))
* [PR 14054](https://github.com/spyder-ide/spyder/pull/14054) - PR: Change replace labels in find/replace widget, by [@TediaN97](https://github.com/TediaN97) ([13957](https://github.com/spyder-ide/spyder/issues/13957))
* [PR 14051](https://github.com/spyder-ide/spyder/pull/14051) - PR: Improvements to the About Spyder dialog, by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 14043](https://github.com/spyder-ide/spyder/pull/14043) - PR: Update subrepo with python-language-server#873, by [@ccordoba12](https://github.com/ccordoba12) ([13985](https://github.com/spyder-ide/spyder/issues/13985))
* [PR 14037](https://github.com/spyder-ide/spyder/pull/14037) - PR: Some improvements to the create project dialog., by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 14033](https://github.com/spyder-ide/spyder/pull/14033) - PR: Fix issue where external IPython consoles do not launch for macOS application, by [@mrclary](https://github.com/mrclary)
* [PR 14027](https://github.com/spyder-ide/spyder/pull/14027) - PR: Some improvements to the "Run > Configuration per file" dialog (2), by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 14022](https://github.com/spyder-ide/spyder/pull/14022) - PR: Simplify add_pathlist_to_PYTHONPATH, by [@ccordoba12](https://github.com/ccordoba12) ([3161](https://github.com/spyder-ide/spyder/issues/3161), [13964](https://github.com/spyder-ide/spyder/issues/13964), [12564](https://github.com/spyder-ide/spyder/issues/12564))
* [PR 14019](https://github.com/spyder-ide/spyder/pull/14019) - PR: Enable text snippets support in the editor, by [@andfoy](https://github.com/andfoy) ([588](https://github.com/spyder-ide/spyder/issues/588))
* [PR 14017](https://github.com/spyder-ide/spyder/pull/14017) - PR: Don't pass PYTHONPATH directly to the kernel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([13519](https://github.com/spyder-ide/spyder/issues/13519))
* [PR 14016](https://github.com/spyder-ide/spyder/pull/14016) - PR: Fix remove_trailing_spaces method and attribute clash, by [@andfoy](https://github.com/andfoy) ([14001](https://github.com/spyder-ide/spyder/issues/14001))
* [PR 14014](https://github.com/spyder-ide/spyder/pull/14014) - PR: Add get_package_version for more complete version list, by [@oscargus](https://github.com/oscargus)
* [PR 14008](https://github.com/spyder-ide/spyder/pull/14008) - PR: Improve how the options in Preferences/Appearance are applied, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 14007](https://github.com/spyder-ide/spyder/pull/14007) - PR: Catch TypeError when loading third-party plugins (Main Window), by [@ccordoba12](https://github.com/ccordoba12) ([13977](https://github.com/spyder-ide/spyder/issues/13977))
* [PR 13992](https://github.com/spyder-ide/spyder/pull/13992) - PR: Add scripts and files necessary to create a macOS installer, by [@mrclary](https://github.com/mrclary) ([13978](https://github.com/spyder-ide/spyder/issues/13978))
* [PR 13981](https://github.com/spyder-ide/spyder/pull/13981) - PR: Update Outline when opening or closing projects, by [@ccordoba12](https://github.com/ccordoba12) ([13897](https://github.com/spyder-ide/spyder/issues/13897))
* [PR 13979](https://github.com/spyder-ide/spyder/pull/13979) - PR: Some improvements to the "Run > Configuration per file" dialog, by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 13974](https://github.com/spyder-ide/spyder/pull/13974) - PR: Remove support for Python 2 and 3.5 in setup.py, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13972](https://github.com/spyder-ide/spyder/pull/13972) - PR: Use a better method to check the spinner is not shown in a couple of Outline tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13971](https://github.com/spyder-ide/spyder/pull/13971) - PR: Add warning for xdg-utils when trying to open a file in the editor in the external file explorer, by [@juanis2112](https://github.com/juanis2112) ([13507](https://github.com/spyder-ide/spyder/issues/13507))
* [PR 13970](https://github.com/spyder-ide/spyder/pull/13970) - PR: Add shortcuts to Profiler and Code Analysis panes, by [@juanis2112](https://github.com/juanis2112) ([13439](https://github.com/spyder-ide/spyder/issues/13439))
* [PR 13963](https://github.com/spyder-ide/spyder/pull/13963) - PR: Change colors for kernel errors in IPython console, by [@juanis2112](https://github.com/juanis2112) ([13754](https://github.com/spyder-ide/spyder/issues/13754))
* [PR 13958](https://github.com/spyder-ide/spyder/pull/13958) - PR: Update, revise and copyedit existing tour steps, by [@CAM-Gerlach](https://github.com/CAM-Gerlach)
* [PR 13953](https://github.com/spyder-ide/spyder/pull/13953) - PR: Change Kite dialog to tour dialog when starting Spyder for first time, by [@juanis2112](https://github.com/juanis2112) ([13832](https://github.com/spyder-ide/spyder/issues/13832))
* [PR 13950](https://github.com/spyder-ide/spyder/pull/13950) - PR: Show conda and pyenv environments in Python interpreter (Preferences), by [@steff456](https://github.com/steff456) ([13903](https://github.com/spyder-ide/spyder/issues/13903), [12200](https://github.com/spyder-ide/spyder/issues/12200))
* [PR 13938](https://github.com/spyder-ide/spyder/pull/13938) - PR: Update outline for files in previous session after Spyder started, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13920](https://github.com/spyder-ide/spyder/pull/13920) - PR: Update subrepo with spyder-kernels#252, by [@ccordoba12](https://github.com/ccordoba12) ([13909](https://github.com/spyder-ide/spyder/issues/13909))
* [PR 13919](https://github.com/spyder-ide/spyder/pull/13919) - PR: Fix debugger panel not being updated, by [@impact27](https://github.com/impact27) ([13918](https://github.com/spyder-ide/spyder/issues/13918))
* [PR 13915](https://github.com/spyder-ide/spyder/pull/13915) - PR: Avoid atomic writes leaving trail of temporary files in Dropbox directories, by [@skjerns](https://github.com/skjerns) ([13041](https://github.com/spyder-ide/spyder/issues/13041))
* [PR 13902](https://github.com/spyder-ide/spyder/pull/13902) - PR: Update subrepo with spyder-kernels#251, by [@ccordoba12](https://github.com/ccordoba12) ([13892](https://github.com/spyder-ide/spyder/issues/13892), [13891](https://github.com/spyder-ide/spyder/issues/13891))
* [PR 13895](https://github.com/spyder-ide/spyder/pull/13895) - PR: Add tutorial videos to help menu, update link to troubleshooting in docs, by [@juanis2112](https://github.com/juanis2112) ([13239](https://github.com/spyder-ide/spyder/issues/13239))
* [PR 13894](https://github.com/spyder-ide/spyder/pull/13894) - PR: Disable toolbar fullscreen button for macOS, by [@juanis2112](https://github.com/juanis2112) ([5](https://github.com/spyder-ide/ux-improvements/issues/5))
* [PR 13885](https://github.com/spyder-ide/spyder/pull/13885) - PR: Restore code cells and block comments in the Outline pane and fix other issues, by [@andfoy](https://github.com/andfoy) ([13896](https://github.com/spyder-ide/spyder/issues/13896), [13877](https://github.com/spyder-ide/spyder/issues/13877), [13872](https://github.com/spyder-ide/spyder/issues/13872))
* [PR 13884](https://github.com/spyder-ide/spyder/pull/13884) - PR: Display an error message when Kite sends a non-dict response, by [@andfoy](https://github.com/andfoy) ([13121](https://github.com/spyder-ide/spyder/issues/13121))
* [PR 13881](https://github.com/spyder-ide/spyder/pull/13881) - PR: Test icons for naming changes in QtAwesome, by [@dalthviz](https://github.com/dalthviz)
* [PR 13876](https://github.com/spyder-ide/spyder/pull/13876) - PR: Make date objects editable in the object explorer, by [@steff456](https://github.com/steff456) ([13557](https://github.com/spyder-ide/spyder/issues/13557))
* [PR 13867](https://github.com/spyder-ide/spyder/pull/13867) - PR: Improve performance when painting indent guides, by [@ccordoba12](https://github.com/ccordoba12) ([8864](https://github.com/spyder-ide/spyder/issues/8864))
* [PR 13852](https://github.com/spyder-ide/spyder/pull/13852) - PR: Add test for spyder-kernels#243, by [@impact27](https://github.com/impact27) ([12651](https://github.com/spyder-ide/spyder/issues/12651))
* [PR 13843](https://github.com/spyder-ide/spyder/pull/13843) - PR: Update optional dependency on Pandas to 1.1.1, by [@steff456](https://github.com/steff456) ([13620](https://github.com/spyder-ide/spyder/issues/13620))
* [PR 13839](https://github.com/spyder-ide/spyder/pull/13839) - PR: Update Jedi requirement to 0.17.2, by [@ccordoba12](https://github.com/ccordoba12) ([13807](https://github.com/spyder-ide/spyder/issues/13807), [12259](https://github.com/spyder-ide/spyder/issues/12259))
* [PR 13834](https://github.com/spyder-ide/spyder/pull/13834) - PR: Only highlight multiple occurrences in the editor, by [@steff456](https://github.com/steff456) ([13762](https://github.com/spyder-ide/spyder/issues/13762))
* [PR 13833](https://github.com/spyder-ide/spyder/pull/13833) - PR: Fix some UX/UI issues in the Files pane, by [@steff456](https://github.com/steff456) ([13465](https://github.com/spyder-ide/spyder/issues/13465))
* [PR 13830](https://github.com/spyder-ide/spyder/pull/13830) - PR: Update version of qtconsole to 4.7.7, by [@steff456](https://github.com/steff456) ([13806](https://github.com/spyder-ide/spyder/issues/13806))
* [PR 13828](https://github.com/spyder-ide/spyder/pull/13828) - PR: Don't send requests to the PyLS until it's been properly initialized, by [@ccordoba12](https://github.com/ccordoba12) ([13351](https://github.com/spyder-ide/spyder/issues/13351))
* [PR 13818](https://github.com/spyder-ide/spyder/pull/13818) - PR: Update subrepo with spyder-kernels#244, by [@dalthviz](https://github.com/dalthviz) ([13632](https://github.com/spyder-ide/spyder/issues/13632))
* [PR 13817](https://github.com/spyder-ide/spyder/pull/13817) - PR: Change tooltip of PYTHONPATH manager to match title in dialog, by [@juanitagomezr](https://github.com/juanitagomezr) ([13741](https://github.com/spyder-ide/spyder/issues/13741))
* [PR 13814](https://github.com/spyder-ide/spyder/pull/13814) - PR: Press enter on completion test, by [@bnavigator](https://github.com/bnavigator)
* [PR 13796](https://github.com/spyder-ide/spyder/pull/13796) - PR: Remove repeated SymbolKind enum, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13791](https://github.com/spyder-ide/spyder/pull/13791) - PR: Restore sorting of types and natural sorting, by [@skjerns](https://github.com/skjerns) ([13733](https://github.com/spyder-ide/spyder/issues/13733))
* [PR 13789](https://github.com/spyder-ide/spyder/pull/13789) - PR: Update contributing guide to install main dependencies from the dev label in our channel, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13787](https://github.com/spyder-ide/spyder/pull/13787) - PR: Call QGuiApplication.setDesktopFileName to fix generic icon on GNOME/Wayland, by [@musicinmybrain](https://github.com/musicinmybrain) ([13786](https://github.com/spyder-ide/spyder/issues/13786))
* [PR 13765](https://github.com/spyder-ide/spyder/pull/13765) - PR: Remove pin for python-jsonrpc-server and update PyLS subrepo (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13756](https://github.com/spyder-ide/spyder/pull/13756) - PR: Pin python-jsonrpc-server to a working version in our CIs (for now), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13753](https://github.com/spyder-ide/spyder/pull/13753) - PR: Handle IndexError in Pylint history, by [@steff456](https://github.com/steff456) ([13342](https://github.com/spyder-ide/spyder/issues/13342))
* [PR 13750](https://github.com/spyder-ide/spyder/pull/13750) - PR: Fixes to Help plugin according to UX review, by [@juanis2112](https://github.com/juanis2112) ([13241](https://github.com/spyder-ide/spyder/issues/13241))
* [PR 13740](https://github.com/spyder-ide/spyder/pull/13740) - PR: Fix create folder in Projects, by [@akwasigroch](https://github.com/akwasigroch) ([13722](https://github.com/spyder-ide/spyder/issues/13722))
* [PR 13721](https://github.com/spyder-ide/spyder/pull/13721) - PR: Correctly import IPythonInputSplitter for IPython < 7.0, by [@ccordoba12](https://github.com/ccordoba12) ([13719](https://github.com/spyder-ide/spyder/issues/13719))
* [PR 13717](https://github.com/spyder-ide/spyder/pull/13717) - PR: Fix technical bugs on tour, by [@juanis2112](https://github.com/juanis2112) ([13240](https://github.com/spyder-ide/spyder/issues/13240))
* [PR 13634](https://github.com/spyder-ide/spyder/pull/13634) - PR: Skip error when getting values (IPython console), by [@impact27](https://github.com/impact27) ([13623](https://github.com/spyder-ide/spyder/issues/13623))
* [PR 13627](https://github.com/spyder-ide/spyder/pull/13627) - PR: Fix some issues with the PyLS subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13598](https://github.com/spyder-ide/spyder/pull/13598) - PR: Fix messages shown in plain text (Help), by [@steff456](https://github.com/steff456) ([13585](https://github.com/spyder-ide/spyder/issues/13585))
* [PR 13590](https://github.com/spyder-ide/spyder/pull/13590) - PR: Fix height of "Run > Configuration per file" dialog by adding a scrollbar to it, by [@steff456](https://github.com/steff456) ([13531](https://github.com/spyder-ide/spyder/issues/13531))
* [PR 13380](https://github.com/spyder-ide/spyder/pull/13380) - PR: Add option to insert elements above/below in lists (Variable Explorer), by [@dpturibio](https://github.com/dpturibio) ([13371](https://github.com/spyder-ide/spyder/issues/13371))
* [PR 13379](https://github.com/spyder-ide/spyder/pull/13379) - PR: Fix close button while debugging, by [@impact27](https://github.com/impact27) ([13283](https://github.com/spyder-ide/spyder/issues/13283))
* [PR 13327](https://github.com/spyder-ide/spyder/pull/13327) - PR: Improve Pdb input handling, by [@impact27](https://github.com/impact27) ([620](https://github.com/spyder-ide/spyder/issues/620))
* [PR 13295](https://github.com/spyder-ide/spyder/pull/13295) - PR: Enable LSP autoformatting support, by [@andfoy](https://github.com/andfoy) ([11396](https://github.com/spyder-ide/spyder/issues/11396))
* [PR 13281](https://github.com/spyder-ide/spyder/pull/13281) - PR: Improve performance when processing linting results and scrolling (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([13908](https://github.com/spyder-ide/spyder/issues/13908), [13668](https://github.com/spyder-ide/spyder/issues/13668), [13666](https://github.com/spyder-ide/spyder/issues/13666), [13020](https://github.com/spyder-ide/spyder/issues/13020))
* [PR 13269](https://github.com/spyder-ide/spyder/pull/13269) - PR: Windows Installer script, by [@dalthviz](https://github.com/dalthviz) ([13145](https://github.com/spyder-ide/spyder/issues/13145))
* [PR 13190](https://github.com/spyder-ide/spyder/pull/13190) - PR: Go to current position when using the Pdb `where` command, by [@impact27](https://github.com/impact27)
* [PR 13149](https://github.com/spyder-ide/spyder/pull/13149) - PR: Normcase breakpoints to avoid issues on Windows, by [@impact27](https://github.com/impact27)
* [PR 13109](https://github.com/spyder-ide/spyder/pull/13109) - PR: Migrate the Outline Explorer to use LSP information, by [@andfoy](https://github.com/andfoy)
* [PR 12926](https://github.com/spyder-ide/spyder/pull/12926) - PR: Add safe-mode option to Spyder in non dev mode, by [@juanis2112](https://github.com/juanis2112) ([12631](https://github.com/spyder-ide/spyder/issues/12631))
* [PR 12236](https://github.com/spyder-ide/spyder/pull/12236) - PR: Start kernels and Jedi envs with explicit environment (Mac app), by [@mrclary](https://github.com/mrclary)
* [PR 12235](https://github.com/spyder-ide/spyder/pull/12235) - PR: Use clean environment for Python version and module checks (Mac app), by [@mrclary](https://github.com/mrclary)
* [PR 12232](https://github.com/spyder-ide/spyder/pull/12232) - PR: Display interpreter status if Spyder not launched from conda envrionment (Mac app), by [@mrclary](https://github.com/mrclary) ([6](https://github.com/spyder-ide/mac-application/issues/6))
* [PR 12134](https://github.com/spyder-ide/spyder/pull/12134) - PR: Use '!' for Pdb commands and add other options to control the debugger (IPython console), by [@impact27](https://github.com/impact27)
* [PR 12011](https://github.com/spyder-ide/spyder/pull/12011) - PR: Initial changes to create again a macOS standalone app, by [@mrclary](https://github.com/mrclary)
* [PR 10873](https://github.com/spyder-ide/spyder/pull/10873) - PR: Add a cache to runcell, by [@impact27](https://github.com/impact27) ([9725](https://github.com/spyder-ide/spyder/issues/9725))

In this release 105 pull requests were closed.


----


## Version 4.1.6 (2020-11-08)

### Important fixes

* Fix support for Python 2

### Issues Closed

* [Issue 13962](https://github.com/spyder-ide/spyder/issues/13962) - Spyder within Python 2.7 Anaconda environment crashes ([PR 14169](https://github.com/spyder-ide/spyder/pull/14169) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 14169](https://github.com/spyder-ide/spyder/pull/14169) - PR: Fixes to release 4.1.6, by [@ccordoba12](https://github.com/ccordoba12) ([13962](https://github.com/spyder-ide/spyder/issues/13962))

In this release 1 pull request was closed.


----


## Version 4.1.5 (2020-09-01)

### New features

* Add natural sorting for variables in the Variable Explorer.
* Add shortcut to open files in the Editor in the operating system file
  explorer.
* Add an option to run lines of code when entering the debugger. This is
  present in `Preferences > IPython console > Startup`.

### Important fixes

* Fix error when opening projects.
* Fix error when hovering in the Editor caused by Kite.
* Don't save files when running cells.
* Several improvements to the user experience of Files.

### Issues Closed

* [Issue 13635](https://github.com/spyder-ide/spyder/issues/13635) - Update spyder-kernels subrepo ([PR 13202](https://github.com/spyder-ide/spyder/pull/13202) by [@impact27](https://github.com/impact27))
* [Issue 13490](https://github.com/spyder-ide/spyder/issues/13490) - Test `test_dbg_input` is failing in Linux fast CI ([PR 13499](https://github.com/spyder-ide/spyder/pull/13499) by [@impact27](https://github.com/impact27))
* [Issue 13481](https://github.com/spyder-ide/spyder/issues/13481) - Can't open Dict in variable explorer with mixed data types as keys. ([PR 13545](https://github.com/spyder-ide/spyder/pull/13545) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13444](https://github.com/spyder-ide/spyder/issues/13444) - Explorer "New" actions should depend on selected files ([PR 13482](https://github.com/spyder-ide/spyder/pull/13482) by [@steff456](https://github.com/steff456))
* [Issue 13417](https://github.com/spyder-ide/spyder/issues/13417) - Error in Spyder tutorial ([PR 13419](https://github.com/spyder-ide/spyder/pull/13419) by [@aznpooface](https://github.com/aznpooface))
* [Issue 13388](https://github.com/spyder-ide/spyder/issues/13388) - BrokenPipeError when trying to connect to the Pydoc server ([PR 13407](https://github.com/spyder-ide/spyder/pull/13407) by [@steff456](https://github.com/steff456))
* [Issue 13363](https://github.com/spyder-ide/spyder/issues/13363) - Profiler doesn't sort by time ([PR 13426](https://github.com/spyder-ide/spyder/pull/13426) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13346](https://github.com/spyder-ide/spyder/issues/13346) - TypeError when opening a project ([PR 13377](https://github.com/spyder-ide/spyder/pull/13377) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13297](https://github.com/spyder-ide/spyder/issues/13297) - TypeError when hovering in the editor ([PR 13575](https://github.com/spyder-ide/spyder/pull/13575) by [@andfoy](https://github.com/andfoy))
* [Issue 13254](https://github.com/spyder-ide/spyder/issues/13254) - Add (0) to first image stored when saving all images from IDE ([PR 13334](https://github.com/spyder-ide/spyder/pull/13334) by [@arteagac](https://github.com/arteagac))
* [Issue 13230](https://github.com/spyder-ide/spyder/issues/13230) - Another KeyError when folding regions ([PR 13279](https://github.com/spyder-ide/spyder/pull/13279) by [@steff456](https://github.com/steff456))
* [Issue 13197](https://github.com/spyder-ide/spyder/issues/13197) - Spyder saves files before running code cells (but should not) ([PR 13202](https://github.com/spyder-ide/spyder/pull/13202) by [@impact27](https://github.com/impact27))
* [Issue 13179](https://github.com/spyder-ide/spyder/issues/13179) - Some improvements for the Files plugin ([PR 13209](https://github.com/spyder-ide/spyder/pull/13209) by [@dalthviz](https://github.com/dalthviz))
* [Issue 13158](https://github.com/spyder-ide/spyder/issues/13158) - Feature request: keyboard shortcut for "Show in external file explorer"
* [Issue 13144](https://github.com/spyder-ide/spyder/issues/13144) - I'm not able to search by context in the shortcuts table ([PR 13294](https://github.com/spyder-ide/spyder/pull/13294) by [@steff456](https://github.com/steff456))
* [Issue 12795](https://github.com/spyder-ide/spyder/issues/12795) - Startup script for debugger ([PR 10542](https://github.com/spyder-ide/spyder/pull/10542) by [@impact27](https://github.com/impact27))
* [Issue 7844](https://github.com/spyder-ide/spyder/issues/7844) - Add a "Copy to clipboard" button to the "About Spyder" window ([PR 13268](https://github.com/spyder-ide/spyder/pull/13268) by [@davidxbuck](https://github.com/davidxbuck))

In this release 17 issues were closed.

### Pull Requests Merged

* [PR 13679](https://github.com/spyder-ide/spyder/pull/13679) - PR: Update required version of spyder-kernels for 4.1.5, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13621](https://github.com/spyder-ide/spyder/pull/13621) - PR: Install PyLS locally without modifying site-packages, by [@andfoy](https://github.com/andfoy)
* [PR 13575](https://github.com/spyder-ide/spyder/pull/13575) - PR: Prevent raising an exception when a hover request returns a list, by [@andfoy](https://github.com/andfoy) ([13297](https://github.com/spyder-ide/spyder/issues/13297))
* [PR 13559](https://github.com/spyder-ide/spyder/pull/13559) - PR: Fix using dir in the spyder module, by [@impact27](https://github.com/impact27)
* [PR 13558](https://github.com/spyder-ide/spyder/pull/13558) - PR: Add natural sorting for dicts (Variable Explorer), by [@skjerns](https://github.com/skjerns)
* [PR 13554](https://github.com/spyder-ide/spyder/pull/13554) - PR: Change About and Dependencies dialogs to non-modal, by [@juanis2112](https://github.com/juanis2112)
* [PR 13545](https://github.com/spyder-ide/spyder/pull/13545) - PR: Fix error when showing dicts with mixed type keys (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([13481](https://github.com/spyder-ide/spyder/issues/13481))
* [PR 13499](https://github.com/spyder-ide/spyder/pull/13499) - PR: Fix failing test for IPython 7.17, by [@impact27](https://github.com/impact27) ([13490](https://github.com/spyder-ide/spyder/issues/13490))
* [PR 13482](https://github.com/spyder-ide/spyder/pull/13482) - PR: Explorer "New" actions now depend on selected files, by [@steff456](https://github.com/steff456) ([13444](https://github.com/spyder-ide/spyder/issues/13444))
* [PR 13426](https://github.com/spyder-ide/spyder/pull/13426) - PR: Fix sorting of files in profiler by fixing parser, by [@juanis2112](https://github.com/juanis2112) ([13363](https://github.com/spyder-ide/spyder/issues/13363))
* [PR 13419](https://github.com/spyder-ide/spyder/pull/13419) - PR: Fix error in tutorial (Help), by [@aznpooface](https://github.com/aznpooface) ([13417](https://github.com/spyder-ide/spyder/issues/13417))
* [PR 13408](https://github.com/spyder-ide/spyder/pull/13408) - PR: Fix some failing tests, by [@goanpeca](https://github.com/goanpeca)
* [PR 13407](https://github.com/spyder-ide/spyder/pull/13407) - PR: Catch BrokenPipeError when trying to open a port (Online Help), by [@steff456](https://github.com/steff456) ([13388](https://github.com/spyder-ide/spyder/issues/13388))
* [PR 13396](https://github.com/spyder-ide/spyder/pull/13396) - PR: Improve Binder installation, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13395](https://github.com/spyder-ide/spyder/pull/13395) - PR: Remove Github action to add Binder badge on pull request creation, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13393](https://github.com/spyder-ide/spyder/pull/13393) - PR: Fix Binder actions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13392](https://github.com/spyder-ide/spyder/pull/13392) - PR: Add Github actions to display a Binder badge in our PRs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13377](https://github.com/spyder-ide/spyder/pull/13377) - PR: Verify path before notifying project was open, by [@dalthviz](https://github.com/dalthviz) ([13346](https://github.com/spyder-ide/spyder/issues/13346))
* [PR 13376](https://github.com/spyder-ide/spyder/pull/13376) - PR: Fix some issues with the Find and Code Analysis panes, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13359](https://github.com/spyder-ide/spyder/pull/13359) - PR: Add a "Show in external file browser" shortcut (Editor), by [@athompson673](https://github.com/athompson673)
* [PR 13334](https://github.com/spyder-ide/spyder/pull/13334) - PR: Fix for consistent numbering when saving multiple plots, by [@arteagac](https://github.com/arteagac) ([13254](https://github.com/spyder-ide/spyder/issues/13254))
* [PR 13311](https://github.com/spyder-ide/spyder/pull/13311) - PR: Remove Python 2 testing on Github Actions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13294](https://github.com/spyder-ide/spyder/pull/13294) - PR: Enable filtering in multiple columns in the shortcuts table (Preferences), by [@steff456](https://github.com/steff456) ([13144](https://github.com/spyder-ide/spyder/issues/13144))
* [PR 13293](https://github.com/spyder-ide/spyder/pull/13293) - PR: Fix linux container dependencies install, by [@goanpeca](https://github.com/goanpeca)
* [PR 13279](https://github.com/spyder-ide/spyder/pull/13279) - PR: Catch KeyError in codefolding when folding regions, by [@steff456](https://github.com/steff456) ([13230](https://github.com/spyder-ide/spyder/issues/13230))
* [PR 13268](https://github.com/spyder-ide/spyder/pull/13268) - PR: Add "Copy to clipboard" button to the "About Spyder" dialog, by [@davidxbuck](https://github.com/davidxbuck) ([7844](https://github.com/spyder-ide/spyder/issues/7844))
* [PR 13259](https://github.com/spyder-ide/spyder/pull/13259) - PR: Update Contributing guide to specify forking the Spyder repo, by [@CAM-Gerlach](https://github.com/CAM-Gerlach)
* [PR 13209](https://github.com/spyder-ide/spyder/pull/13209) - PR: Improve Files plugin UI, by [@dalthviz](https://github.com/dalthviz) ([13179](https://github.com/spyder-ide/spyder/issues/13179))
* [PR 13202](https://github.com/spyder-ide/spyder/pull/13202) - PR: Do not save file when runcell, by [@impact27](https://github.com/impact27) ([13635](https://github.com/spyder-ide/spyder/issues/13635), [13197](https://github.com/spyder-ide/spyder/issues/13197))
* [PR 10542](https://github.com/spyder-ide/spyder/pull/10542) - PR: Add startup lines to the debugger, by [@impact27](https://github.com/impact27) ([12795](https://github.com/spyder-ide/spyder/issues/12795))

In this release 30 pull requests were closed.


----


## Version 4.1.4 (2020-07-10)

### Important fixes

* Fix linter not being updated after changes on Windows.
* Correctly restart kernels after a crash while running code.
* Clear variable explorer after a kernel restart.
* Fix several errors when sorting variables in the variable explorer.
* Fix selection color in several syntax highlighting themes.
* Support Jedi 0.17.1, which fixes several issues with code completion in the
  editor.
* Fix errors when running Dask code in the IPython console.
* Show scrollflag in macOS with the dark theme.
* Only show folding arrows when the user hovers over them, which improves
  responsiveness in the editor
* Fix several problems with the integration between our projects and the
  Python language server.
* Handle NaT values in the Variable Explorer.

### Issues Closed

* [Issue 13205](https://github.com/spyder-ide/spyder/issues/13205) - Invalid interpreter causes crash over the LSP/pyls ([PR 13217](https://github.com/spyder-ide/spyder/pull/13217) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13191](https://github.com/spyder-ide/spyder/issues/13191) - Missing arrows to change tab on mac ([PR 13249](https://github.com/spyder-ide/spyder/pull/13249) by [@impact27](https://github.com/impact27))
* [Issue 13178](https://github.com/spyder-ide/spyder/issues/13178) - Some improvements to the Find pane ([PR 13215](https://github.com/spyder-ide/spyder/pull/13215) by [@steff456](https://github.com/steff456))
* [Issue 13172](https://github.com/spyder-ide/spyder/issues/13172) - Update translations for 4.1.4 ([PR 13170](https://github.com/spyder-ide/spyder/pull/13170) by [@spyder-bot](https://github.com/spyder-bot))
* [Issue 13164](https://github.com/spyder-ide/spyder/issues/13164) - Kernel fails to send config sometimes ([PR 13166](https://github.com/spyder-ide/spyder/pull/13166) by [@impact27](https://github.com/impact27))
* [Issue 13148](https://github.com/spyder-ide/spyder/issues/13148) - Segmentation fault when requesting context menu for a one file in project explorer ([PR 13226](https://github.com/spyder-ide/spyder/pull/13226) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 13119](https://github.com/spyder-ide/spyder/issues/13119) - Minor spelling error in Spyder tutorial
* [Issue 13110](https://github.com/spyder-ide/spyder/issues/13110) - Linting is not respecting pycodestyle.cfg ([PR 13146](https://github.com/spyder-ide/spyder/pull/13146) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13069](https://github.com/spyder-ide/spyder/issues/13069) - Debugger panel is not shown for pyw files ([PR 13085](https://github.com/spyder-ide/spyder/pull/13085) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13059](https://github.com/spyder-ide/spyder/issues/13059) - Fix abbreviations for seconds in profiler ([PR 13081](https://github.com/spyder-ide/spyder/pull/13081) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13048](https://github.com/spyder-ide/spyder/issues/13048) - Spyder claims to be "Connecting to kernel" while running a file ([PR 13056](https://github.com/spyder-ide/spyder/pull/13056) by [@impact27](https://github.com/impact27))
* [Issue 13018](https://github.com/spyder-ide/spyder/issues/13018) - Kernel is not restarted correctly when RecursiveError is thrown on Windows ([PR 12972](https://github.com/spyder-ide/spyder/pull/12972) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 13009](https://github.com/spyder-ide/spyder/issues/13009) - Missing fold marks in the Spyder 2 theme ([PR 13015](https://github.com/spyder-ide/spyder/pull/13015) by [@juanis2112](https://github.com/juanis2112))
* [Issue 13004](https://github.com/spyder-ide/spyder/issues/13004) - Right-clicking an empty folder doesn't show the context menu of the Files pane ([PR 13032](https://github.com/spyder-ide/spyder/pull/13032) by [@steff456](https://github.com/steff456))
* [Issue 12999](https://github.com/spyder-ide/spyder/issues/12999) - IPython console hangs after changing warning to errors ([PR 13007](https://github.com/spyder-ide/spyder/pull/13007) by [@impact27](https://github.com/impact27))
* [Issue 12992](https://github.com/spyder-ide/spyder/issues/12992) - Shift+return not working for run selection -  no solutions work ([PR 13047](https://github.com/spyder-ide/spyder/pull/13047) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12892](https://github.com/spyder-ide/spyder/issues/12892) - Open new file causes an error ([PR 13040](https://github.com/spyder-ide/spyder/pull/13040) by [@steff456](https://github.com/steff456))
* [Issue 12883](https://github.com/spyder-ide/spyder/issues/12883) - File names are repeated in Code analysis file combobox ([PR 12884](https://github.com/spyder-ide/spyder/pull/12884) by [@steff456](https://github.com/steff456))
* [Issue 12857](https://github.com/spyder-ide/spyder/issues/12857) - Selection color makes comments not visible ([PR 12981](https://github.com/spyder-ide/spyder/pull/12981) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12825](https://github.com/spyder-ide/spyder/issues/12825) - Variable inspector opens window out of focus ([PR 13033](https://github.com/spyder-ide/spyder/pull/13033) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12810](https://github.com/spyder-ide/spyder/issues/12810) - Can't close any editor tab when in debug mode ([PR 12985](https://github.com/spyder-ide/spyder/pull/12985) by [@steff456](https://github.com/steff456))
* [Issue 12801](https://github.com/spyder-ide/spyder/issues/12801) - Include first __main__ caller in post-mortem debugger stack trace
* [Issue 12799](https://github.com/spyder-ide/spyder/issues/12799) - Improve error message when loading spydata files ([PR 13052](https://github.com/spyder-ide/spyder/pull/13052) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12755](https://github.com/spyder-ide/spyder/issues/12755) - I closed an autosave file and Spyder said there is some error ([PR 12822](https://github.com/spyder-ide/spyder/pull/12822) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 12748](https://github.com/spyder-ide/spyder/issues/12748) - Update CI to include caching ([PR 12826](https://github.com/spyder-ide/spyder/pull/12826) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12740](https://github.com/spyder-ide/spyder/issues/12740) - Code Analysis customize history not working and actions unavailable when pane is undocked ([PR 12874](https://github.com/spyder-ide/spyder/pull/12874) by [@steff456](https://github.com/steff456))
* [Issue 12735](https://github.com/spyder-ide/spyder/issues/12735) - Change output of code analysis to show the full names of the pylint messages ([PR 12803](https://github.com/spyder-ide/spyder/pull/12803) by [@CAM-Gerlach](https://github.com/CAM-Gerlach))
* [Issue 12733](https://github.com/spyder-ide/spyder/issues/12733) - Change menu item to run code analysis ([PR 12734](https://github.com/spyder-ide/spyder/pull/12734) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12716](https://github.com/spyder-ide/spyder/issues/12716) - I never want to restart Spyder when the display dpi changes  ([PR 12881](https://github.com/spyder-ide/spyder/pull/12881) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12704](https://github.com/spyder-ide/spyder/issues/12704) - Deleting space before a word trigger meaningless completion ([PR 12710](https://github.com/spyder-ide/spyder/pull/12710) by [@steff456](https://github.com/steff456))
* [Issue 12689](https://github.com/spyder-ide/spyder/issues/12689) - Variables need to be deleted twice in the variable viewer ([PR 12695](https://github.com/spyder-ide/spyder/pull/12695) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12661](https://github.com/spyder-ide/spyder/issues/12661) - Change "Replace selection" to "Replace in selection" ([PR 12811](https://github.com/spyder-ide/spyder/pull/12811) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12659](https://github.com/spyder-ide/spyder/issues/12659) - 'Replace selection' reduces selected range ([PR 12745](https://github.com/spyder-ide/spyder/pull/12745) by [@steff456](https://github.com/steff456))
* [Issue 12657](https://github.com/spyder-ide/spyder/issues/12657) - Change text for collapse and expand selection, remove restore in Code Analysis pane ([PR 12653](https://github.com/spyder-ide/spyder/pull/12653) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12654](https://github.com/spyder-ide/spyder/issues/12654) - runtests.py attempts to collect tests from subrepos if extra arguments are given ([PR 12672](https://github.com/spyder-ide/spyder/pull/12672) by [@mrclary](https://github.com/mrclary))
* [Issue 12637](https://github.com/spyder-ide/spyder/issues/12637) - The scrollflag is missing in Spyder 4 on MacOS 10.15 ([PR 13071](https://github.com/spyder-ide/spyder/pull/13071) by [@steff456](https://github.com/steff456))
* [Issue 12620](https://github.com/spyder-ide/spyder/issues/12620) - Incorrect sorting with numbers in scientific notation ([PR 12901](https://github.com/spyder-ide/spyder/pull/12901) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12598](https://github.com/spyder-ide/spyder/issues/12598) - Connecting to external PyLS server is broken
* [Issue 12597](https://github.com/spyder-ide/spyder/issues/12597) - Code cells not properly executed from splitted editors or new window editors ([PR 12713](https://github.com/spyder-ide/spyder/pull/12713) by [@impact27](https://github.com/impact27))
* [Issue 12596](https://github.com/spyder-ide/spyder/issues/12596) - Additional empty line is added at the end of the template ([PR 12708](https://github.com/spyder-ide/spyder/pull/12708) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12575](https://github.com/spyder-ide/spyder/issues/12575) - Variable Explorer very slow with large dataframe ([PR 12697](https://github.com/spyder-ide/spyder/pull/12697) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12572](https://github.com/spyder-ide/spyder/issues/12572) - Support for jedi 0.17.0 ([PR 12792](https://github.com/spyder-ide/spyder/pull/12792) by [@andfoy](https://github.com/andfoy))
* [Issue 12563](https://github.com/spyder-ide/spyder/issues/12563) - Improve error message when trying to view a dataframe and Pandas is not installed next to Spyder ([PR 12902](https://github.com/spyder-ide/spyder/pull/12902) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12562](https://github.com/spyder-ide/spyder/issues/12562) - Colour Theme Editor UI Issue ([PR 12986](https://github.com/spyder-ide/spyder/pull/12986) by [@steff456](https://github.com/steff456))
* [Issue 12558](https://github.com/spyder-ide/spyder/issues/12558) - Middle mouse button click on editor tabs may close wrong tab ([PR 12617](https://github.com/spyder-ide/spyder/pull/12617) by [@steff456](https://github.com/steff456))
* [Issue 12491](https://github.com/spyder-ide/spyder/issues/12491) - Shortcut to go to Project pane is not working ([PR 12843](https://github.com/spyder-ide/spyder/pull/12843) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 12465](https://github.com/spyder-ide/spyder/issues/12465) - Spyder is interfering with Dask
* [Issue 12437](https://github.com/spyder-ide/spyder/issues/12437) - Minor issue with editor on macOS and the light theme ([PR 13060](https://github.com/spyder-ide/spyder/pull/13060) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12333](https://github.com/spyder-ide/spyder/issues/12333) - Tab-completion of keyword arguments makes paranthesis ([PR 12792](https://github.com/spyder-ide/spyder/pull/12792) by [@andfoy](https://github.com/andfoy))
* [Issue 12328](https://github.com/spyder-ide/spyder/issues/12328) - test_mainwindow.py opens too many file descriptors and sockets ([PR 12534](https://github.com/spyder-ide/spyder/pull/12534) by [@impact27](https://github.com/impact27))
* [Issue 12315](https://github.com/spyder-ide/spyder/issues/12315) - Restore code folding for large files ([PR 12937](https://github.com/spyder-ide/spyder/pull/12937) by [@andfoy](https://github.com/andfoy))
* [Issue 12266](https://github.com/spyder-ide/spyder/issues/12266) - Crash in fallback plugin when typing character ([PR 13038](https://github.com/spyder-ide/spyder/pull/13038) by [@andfoy](https://github.com/andfoy))
* [Issue 12225](https://github.com/spyder-ide/spyder/issues/12225) - LSP cycling : restarting ... ready ... restarting ... ([PR 12912](https://github.com/spyder-ide/spyder/pull/12912) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11933](https://github.com/spyder-ide/spyder/issues/11933) - Calltips not showing in editor for some functions with Jedi 0.15 ([PR 12792](https://github.com/spyder-ide/spyder/pull/12792) by [@andfoy](https://github.com/andfoy))
* [Issue 11889](https://github.com/spyder-ide/spyder/issues/11889) - TimeoutError when starting a kernel still poping out ([PR 12457](https://github.com/spyder-ide/spyder/pull/12457) by [@impact27](https://github.com/impact27))
* [Issue 11654](https://github.com/spyder-ide/spyder/issues/11654) - Fix request_params in send_workspace_folders_change ([PR 12812](https://github.com/spyder-ide/spyder/pull/12812) by [@andfoy](https://github.com/andfoy))
* [Issue 11506](https://github.com/spyder-ide/spyder/issues/11506) - Linter stays half-dead on Windows ([PR 12771](https://github.com/spyder-ide/spyder/pull/12771) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11154](https://github.com/spyder-ide/spyder/issues/11154) - Problem decoding source (pyflakes E) (Spyder 4) ([PR 12771](https://github.com/spyder-ide/spyder/pull/12771) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 10702](https://github.com/spyder-ide/spyder/issues/10702) - Variables disappear from Spyder 4.0 Variable Explorer  ([PR 10843](https://github.com/spyder-ide/spyder/pull/10843) by [@impact27](https://github.com/impact27))
* [Issue 10329](https://github.com/spyder-ide/spyder/issues/10329) - re.error when creating kernel
* [Issue 8329](https://github.com/spyder-ide/spyder/issues/8329) - Error when trying to inspect a 'NaT' in Variable Explorer ([PR 12700](https://github.com/spyder-ide/spyder/pull/12700) by [@dalthviz](https://github.com/dalthviz))
* [Issue 3291](https://github.com/spyder-ide/spyder/issues/3291) - Spyder open file dialog doesn't show special/hidden files on macOS  ([PR 12886](https://github.com/spyder-ide/spyder/pull/12886) by [@goanpeca](https://github.com/goanpeca))

In this release 62 issues were closed.

### Pull Requests Merged

* [PR 13251](https://github.com/spyder-ide/spyder/pull/13251) - PR: Add fonts-ubuntu to the list of deb packages installed on Binder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13249](https://github.com/spyder-ide/spyder/pull/13249) - PR: Remove arrows config in macOS stylesheet, by [@impact27](https://github.com/impact27) ([13191](https://github.com/spyder-ide/spyder/issues/13191))
* [PR 13242](https://github.com/spyder-ide/spyder/pull/13242) - PR: Update required versions of spyder-kernels and PyLS for 4.1.4, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13226](https://github.com/spyder-ide/spyder/pull/13226) - PR: Fix segfault when right-clicking any entry in the project explorer (2), by [@jnsebgosselin](https://github.com/jnsebgosselin) ([13148](https://github.com/spyder-ide/spyder/issues/13148))
* [PR 13217](https://github.com/spyder-ide/spyder/pull/13217) - PR: Validate Python interpreter when applying options (Main interpreter), by [@ccordoba12](https://github.com/ccordoba12) ([13205](https://github.com/spyder-ide/spyder/issues/13205))
* [PR 13215](https://github.com/spyder-ide/spyder/pull/13215) - PR: Some improvements for the Find pane, by [@steff456](https://github.com/steff456) ([13178](https://github.com/spyder-ide/spyder/issues/13178))
* [PR 13204](https://github.com/spyder-ide/spyder/pull/13204) - PR: Update spyder-kernels subrepo to fix an error with ipykernel 5.3.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13203](https://github.com/spyder-ide/spyder/pull/13203) - PR: Add scroll arrows fix for Qt 5.9 and 5.12, by [@goanpeca](https://github.com/goanpeca)
* [PR 13174](https://github.com/spyder-ide/spyder/pull/13174) - PR: Send comm config on every message to avoid TimeoutError's, by [@impact27](https://github.com/impact27)
* [PR 13170](https://github.com/spyder-ide/spyder/pull/13170) - PR: New translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot) ([13172](https://github.com/spyder-ide/spyder/issues/13172))
* [PR 13169](https://github.com/spyder-ide/spyder/pull/13169) - PR: Update translation files, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13166](https://github.com/spyder-ide/spyder/pull/13166) - PR: Ask config after configuration, by [@impact27](https://github.com/impact27) ([13164](https://github.com/spyder-ide/spyder/issues/13164))
* [PR 13146](https://github.com/spyder-ide/spyder/pull/13146) - PR: Some fixes to load project configuration files correctly, by [@ccordoba12](https://github.com/ccordoba12) ([13110](https://github.com/spyder-ide/spyder/issues/13110))
* [PR 13130](https://github.com/spyder-ide/spyder/pull/13130) - PR: Backport PR 13122, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13111](https://github.com/spyder-ide/spyder/pull/13111) - PR: Emit sig_project_closed when switching projects , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13108](https://github.com/spyder-ide/spyder/pull/13108) - PR: Update author_email in setup.py, by [@goanpeca](https://github.com/goanpeca)
* [PR 13095](https://github.com/spyder-ide/spyder/pull/13095) - PR: Update Jedi to 0.17.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 13085](https://github.com/spyder-ide/spyder/pull/13085) - PR: Make an in-depth audit of different LSP calls, by [@ccordoba12](https://github.com/ccordoba12) ([13069](https://github.com/spyder-ide/spyder/issues/13069))
* [PR 13081](https://github.com/spyder-ide/spyder/pull/13081) - PR: Change time units in Profiler to match the International System of Units, by [@juanis2112](https://github.com/juanis2112) ([13059](https://github.com/spyder-ide/spyder/issues/13059))
* [PR 13071](https://github.com/spyder-ide/spyder/pull/13071) - PR: Show the scrollflag in macOS, by [@steff456](https://github.com/steff456) ([12637](https://github.com/spyder-ide/spyder/issues/12637))
* [PR 13060](https://github.com/spyder-ide/spyder/pull/13060) - PR: Fix scroll arrows, add retina images for tab bar and adjust colors shape and size, by [@goanpeca](https://github.com/goanpeca) ([12437](https://github.com/spyder-ide/spyder/issues/12437))
* [PR 13056](https://github.com/spyder-ide/spyder/pull/13056) - PR: Show console when other execution happens, by [@impact27](https://github.com/impact27) ([13048](https://github.com/spyder-ide/spyder/issues/13048))
* [PR 13052](https://github.com/spyder-ide/spyder/pull/13052) - PR: Improve error message for loading spydata with missing dependencies, by [@juanis2112](https://github.com/juanis2112) ([12799](https://github.com/spyder-ide/spyder/issues/12799))
* [PR 13047](https://github.com/spyder-ide/spyder/pull/13047) - PR: Clear old set shortcuts if they are now empty (Shortcuts), by [@dalthviz](https://github.com/dalthviz) ([12992](https://github.com/spyder-ide/spyder/issues/12992))
* [PR 13040](https://github.com/spyder-ide/spyder/pull/13040) - PR: Fix ValueError when an untitled file is open in the editor, by [@steff456](https://github.com/steff456) ([12892](https://github.com/spyder-ide/spyder/issues/12892))
* [PR 13038](https://github.com/spyder-ide/spyder/pull/13038) - PR: Check when prefix size is less than zero or longer than the string size (Fallback completions), by [@andfoy](https://github.com/andfoy) ([12266](https://github.com/spyder-ide/spyder/issues/12266))
* [PR 13033](https://github.com/spyder-ide/spyder/pull/13033) - PR: Update window flags on text editor for macOS (Variable Explorer), by [@goanpeca](https://github.com/goanpeca) ([12825](https://github.com/spyder-ide/spyder/issues/12825))
* [PR 13032](https://github.com/spyder-ide/spyder/pull/13032) - PR: Show the context menu with disabled options in the file explorer when it is empty, by [@steff456](https://github.com/steff456) ([13004](https://github.com/spyder-ide/spyder/issues/13004))
* [PR 13015](https://github.com/spyder-ide/spyder/pull/13015) - PR: Add code folding arrow icons for Spyder 2 icon theme, by [@juanis2112](https://github.com/juanis2112) ([13009](https://github.com/spyder-ide/spyder/issues/13009))
* [PR 13007](https://github.com/spyder-ide/spyder/pull/13007) - PR: Print stderr messages to the console (IPython console), by [@impact27](https://github.com/impact27) ([12999](https://github.com/spyder-ide/spyder/issues/12999))
* [PR 13003](https://github.com/spyder-ide/spyder/pull/13003) - PR: Store the analyzed filenames of the Code Analysis plugin, by [@steff456](https://github.com/steff456)
* [PR 13000](https://github.com/spyder-ide/spyder/pull/13000) - PR: Minor fixes in Readme, by [@amish-d](https://github.com/amish-d)
* [PR 12987](https://github.com/spyder-ide/spyder/pull/12987) - PR: Add warning on console if file is not saved before running it, by [@impact27](https://github.com/impact27)
* [PR 12986](https://github.com/spyder-ide/spyder/pull/12986) - PR: Add minimum width for the color names in the edit appearance panel, by [@steff456](https://github.com/steff456) ([12562](https://github.com/spyder-ide/spyder/issues/12562))
* [PR 12985](https://github.com/spyder-ide/spyder/pull/12985) - PR: Add message when the debug mode is on and the file cannot be closed, by [@steff456](https://github.com/steff456) ([12810](https://github.com/spyder-ide/spyder/issues/12810))
* [PR 12981](https://github.com/spyder-ide/spyder/pull/12981) - PR: Change ocurrence color for various themes to make comments visible, by [@juanis2112](https://github.com/juanis2112) ([12857](https://github.com/spyder-ide/spyder/issues/12857))
* [PR 12972](https://github.com/spyder-ide/spyder/pull/12972) - PR: Fix several problems about kernel restarts, by [@ccordoba12](https://github.com/ccordoba12) ([13018](https://github.com/spyder-ide/spyder/issues/13018))
* [PR 12937](https://github.com/spyder-ide/spyder/pull/12937) - PR: Enable/disable folding guides when cursor enters/exits the left panel, by [@andfoy](https://github.com/andfoy) ([12315](https://github.com/spyder-ide/spyder/issues/12315))
* [PR 12912](https://github.com/spyder-ide/spyder/pull/12912) - PR: Use QProcess instead of subprocess for the LPS transport layer and server, by [@ccordoba12](https://github.com/ccordoba12) ([12225](https://github.com/spyder-ide/spyder/issues/12225))
* [PR 12902](https://github.com/spyder-ide/spyder/pull/12902) - PR: Improve messages for missing modules in Variable Explorer, by [@juanis2112](https://github.com/juanis2112) ([12563](https://github.com/spyder-ide/spyder/issues/12563))
* [PR 12901](https://github.com/spyder-ide/spyder/pull/12901) - PR: Use UserRole to sort columns by actual value and not display value (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([12620](https://github.com/spyder-ide/spyder/issues/12620))
* [PR 12886](https://github.com/spyder-ide/spyder/pull/12886) - PR: Use QFileDialog on OSX to open files, by [@goanpeca](https://github.com/goanpeca) ([3291](https://github.com/spyder-ide/spyder/issues/3291))
* [PR 12884](https://github.com/spyder-ide/spyder/pull/12884) - PR: Verify if file is already shown in the combobox to avoid duplicates (Code Analysis), by [@steff456](https://github.com/steff456) ([12883](https://github.com/spyder-ide/spyder/issues/12883))
* [PR 12881](https://github.com/spyder-ide/spyder/pull/12881) - PR: Improve detection of screen scale change by storing current dpi, by [@dalthviz](https://github.com/dalthviz) ([12716](https://github.com/spyder-ide/spyder/issues/12716))
* [PR 12874](https://github.com/spyder-ide/spyder/pull/12874) - PR: Fix customizing Code Analysis history, by [@steff456](https://github.com/steff456) ([12740](https://github.com/spyder-ide/spyder/issues/12740))
* [PR 12852](https://github.com/spyder-ide/spyder/pull/12852) - PR: Fix hiding completion on backspace when nothing before cursor, by [@ElieGouzien](https://github.com/ElieGouzien)
* [PR 12845](https://github.com/spyder-ide/spyder/pull/12845) - PR: Set the Python language server current working directory to an empty dir, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12843](https://github.com/spyder-ide/spyder/pull/12843) - PR: Unmaximize on new/open/close/delete project, by [@jitseniesen](https://github.com/jitseniesen) ([12491](https://github.com/spyder-ide/spyder/issues/12491))
* [PR 12835](https://github.com/spyder-ide/spyder/pull/12835) - PR: Test that a file with the same name of a standard library module doesn't break the console, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12831](https://github.com/spyder-ide/spyder/pull/12831) - PR: Remove some odd blanks introduced in review, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12826](https://github.com/spyder-ide/spyder/pull/12826) - PR: Enable conda package cache in Github actions, by [@goanpeca](https://github.com/goanpeca) ([12748](https://github.com/spyder-ide/spyder/issues/12748))
* [PR 12822](https://github.com/spyder-ide/spyder/pull/12822) - PR: Ensure autosave files don't overwrite existing files, by [@jitseniesen](https://github.com/jitseniesen) ([12755](https://github.com/spyder-ide/spyder/issues/12755))
* [PR 12812](https://github.com/spyder-ide/spyder/pull/12812) - PR: Implement workspace/didChangeWorkspaceFolders correctly and fix major issues with workspace-only servers, by [@andfoy](https://github.com/andfoy) ([11654](https://github.com/spyder-ide/spyder/issues/11654))
* [PR 12811](https://github.com/spyder-ide/spyder/pull/12811) - PR: Change text of "Replace selection" to "Replace in selection", by [@juanis2112](https://github.com/juanis2112) ([12661](https://github.com/spyder-ide/spyder/issues/12661))
* [PR 12803](https://github.com/spyder-ide/spyder/pull/12803) - PR: Add Pylint message name to code analysis pane and refine format, by [@CAM-Gerlach](https://github.com/CAM-Gerlach) ([12735](https://github.com/spyder-ide/spyder/issues/12735))
* [PR 12792](https://github.com/spyder-ide/spyder/pull/12792) - PR: Update Jedi requirement to 0.17 and Parso to 0.7, by [@andfoy](https://github.com/andfoy) ([12572](https://github.com/spyder-ide/spyder/issues/12572), [12333](https://github.com/spyder-ide/spyder/issues/12333), [11933](https://github.com/spyder-ide/spyder/issues/11933))
* [PR 12781](https://github.com/spyder-ide/spyder/pull/12781) - PR: Add tool tip to EOLStatus, by [@OverLordGoldDragon](https://github.com/OverLordGoldDragon)
* [PR 12777](https://github.com/spyder-ide/spyder/pull/12777) - PR: Don't load files twice at startup and remove multiple calls to document_did_open, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12771](https://github.com/spyder-ide/spyder/pull/12771) - PR: Set LSP server stdout to None on Windows, by [@ccordoba12](https://github.com/ccordoba12) ([11506](https://github.com/spyder-ide/spyder/issues/11506), [11154](https://github.com/spyder-ide/spyder/issues/11154))
* [PR 12770](https://github.com/spyder-ide/spyder/pull/12770) - PR: Improve completions provided by FileComboBox, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12769](https://github.com/spyder-ide/spyder/pull/12769) - PR: Allow the default interpreter to be selected as a custom one in our Preferences, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12746](https://github.com/spyder-ide/spyder/pull/12746) - PR: Fix a couple of failing tests , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12745](https://github.com/spyder-ide/spyder/pull/12745) - PR: Fix selected range after "Replace Selection", by [@steff456](https://github.com/steff456) ([12659](https://github.com/spyder-ide/spyder/issues/12659))
* [PR 12734](https://github.com/spyder-ide/spyder/pull/12734) - PR: Change menu item in Source menu from "Run static code analysis" to "Run code analysis", by [@juanis2112](https://github.com/juanis2112) ([12733](https://github.com/spyder-ide/spyder/issues/12733))
* [PR 12713](https://github.com/spyder-ide/spyder/pull/12713) - PR: Clone cell list to splitted editors, by [@impact27](https://github.com/impact27) ([12597](https://github.com/spyder-ide/spyder/issues/12597))
* [PR 12710](https://github.com/spyder-ide/spyder/pull/12710) - PR: Fix showing/hiding completions when backspace is pressed, by [@steff456](https://github.com/steff456) ([12704](https://github.com/spyder-ide/spyder/issues/12704))
* [PR 12708](https://github.com/spyder-ide/spyder/pull/12708) - PR: Remove additional empty line at the end of the template, by [@juanis2112](https://github.com/juanis2112) ([12596](https://github.com/spyder-ide/spyder/issues/12596))
* [PR 12700](https://github.com/spyder-ide/spyder/pull/12700) - PR: Handle NaT values (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([8329](https://github.com/spyder-ide/spyder/issues/8329))
* [PR 12697](https://github.com/spyder-ide/spyder/pull/12697) - PR: Store copy of the list representation of index and columns (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([12575](https://github.com/spyder-ide/spyder/issues/12575))
* [PR 12695](https://github.com/spyder-ide/spyder/pull/12695) - PR: Don't interrupt the kernel when resetting namespace, by [@ccordoba12](https://github.com/ccordoba12) ([12689](https://github.com/spyder-ide/spyder/issues/12689))
* [PR 12672](https://github.com/spyder-ide/spyder/pull/12672) - PR: Ignore external-deps directory in runtests.py, by [@mrclary](https://github.com/mrclary) ([12654](https://github.com/spyder-ide/spyder/issues/12654))
* [PR 12653](https://github.com/spyder-ide/spyder/pull/12653) - PR: Change text for collapse and expand selection and remove restore action in Code Analysis pane, by [@juanis2112](https://github.com/juanis2112) ([12657](https://github.com/spyder-ide/spyder/issues/12657))
* [PR 12639](https://github.com/spyder-ide/spyder/pull/12639) - PR: Add cron job for cancelling old builds, by [@goanpeca](https://github.com/goanpeca)
* [PR 12638](https://github.com/spyder-ide/spyder/pull/12638) - PR: Update release instructions to include localization updates, by [@goanpeca](https://github.com/goanpeca)
* [PR 12617](https://github.com/spyder-ide/spyder/pull/12617) - PR: Make middle mouse button click on editor tabs close the intended tab, by [@steff456](https://github.com/steff456) ([12558](https://github.com/spyder-ide/spyder/issues/12558))
* [PR 12534](https://github.com/spyder-ide/spyder/pull/12534) - PR: Close leaks without changing tests, by [@impact27](https://github.com/impact27) ([12328](https://github.com/spyder-ide/spyder/issues/12328))
* [PR 12480](https://github.com/spyder-ide/spyder/pull/12480) - PR: Add an option to filter logger messages when debugging, by [@andfoy](https://github.com/andfoy)
* [PR 12457](https://github.com/spyder-ide/spyder/pull/12457) - PR: Don't raise TimeoutError if the kernel is dead, by [@impact27](https://github.com/impact27) ([11889](https://github.com/spyder-ide/spyder/issues/11889))
* [PR 10843](https://github.com/spyder-ide/spyder/pull/10843) - PR: Fix sorting and loading data in the Variable Explorer, by [@impact27](https://github.com/impact27) ([10702](https://github.com/spyder-ide/spyder/issues/10702))

In this release 79 pull requests were closed.


----


## Version 4.1.3 (2020-05-08)

### New features

* New files are saved now as Utf-8 (instead of as Ascii).
* Make functionality to go to the previous/next cursor more intuitive.
* New dark and light themes for the Online Help pane.

### Important fixes

* Make Spyder work on Python 3.8 and Windows.
* Fix several startup crashes related to problems with Kite.
* Fix contrast issues present in several syntax highlighting themes.
* Fix "Directly enter debugging when errors appear" run option.
* Fix startup crash when Spyder is using the Brazilian Portuguese translation.
* Fix segfault on Unix systems when removing plots.
* Correctly position linting markers when code is folded in the editor.
* Correctly show variables while debugging in the Variable Explorer.

### Issues Closed

* [Issue 12510](https://github.com/spyder-ide/spyder/issues/12510) - Problem with Spyder's opening ([PR 12516](https://github.com/spyder-ide/spyder/pull/12516) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12477](https://github.com/spyder-ide/spyder/issues/12477) - Hovers don't hide when Spyder loses focus ([PR 12606](https://github.com/spyder-ide/spyder/pull/12606) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12459](https://github.com/spyder-ide/spyder/issues/12459) - Spyder quits when removing a plot and save plots dialog is wrong. ([PR 12518](https://github.com/spyder-ide/spyder/pull/12518) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12442](https://github.com/spyder-ide/spyder/issues/12442) - TimeoutError in the IPython console when moving or deleting startup script
* [Issue 12424](https://github.com/spyder-ide/spyder/issues/12424) - Improve Readme instructions on how to install Spyder from source ([PR 12432](https://github.com/spyder-ide/spyder/pull/12432) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12417](https://github.com/spyder-ide/spyder/issues/12417) - Inconsistencies with the completion widget ([PR 12453](https://github.com/spyder-ide/spyder/pull/12453) by [@steff456](https://github.com/steff456))
* [Issue 12416](https://github.com/spyder-ide/spyder/issues/12416) - Don't save files as ascii in the editor if there's no coding line ([PR 12467](https://github.com/spyder-ide/spyder/pull/12467) by [@andfoy](https://github.com/andfoy))
* [Issue 12415](https://github.com/spyder-ide/spyder/issues/12415) - Not all shortcuts are displayed in the preferences table ([PR 12514](https://github.com/spyder-ide/spyder/pull/12514) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12410](https://github.com/spyder-ide/spyder/issues/12410) - Check handling of str responses in Kite client signals ([PR 12435](https://github.com/spyder-ide/spyder/pull/12435) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12400](https://github.com/spyder-ide/spyder/issues/12400) - Console won't close ([PR 12448](https://github.com/spyder-ide/spyder/pull/12448) by [@steff456](https://github.com/steff456))
* [Issue 12396](https://github.com/spyder-ide/spyder/issues/12396) - KeyError when renaming file in the editor ([PR 12508](https://github.com/spyder-ide/spyder/pull/12508) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 12373](https://github.com/spyder-ide/spyder/issues/12373) - Code analysis not updated after Backspace ([PR 12374](https://github.com/spyder-ide/spyder/pull/12374) by [@andfoy](https://github.com/andfoy))
* [Issue 12357](https://github.com/spyder-ide/spyder/issues/12357) - Error with kite when using work vpn ([PR 12364](https://github.com/spyder-ide/spyder/pull/12364) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12321](https://github.com/spyder-ide/spyder/issues/12321) - Code analysis markers are not positioned correctly when code is folded ([PR 12452](https://github.com/spyder-ide/spyder/pull/12452) by [@steff456](https://github.com/steff456))
* [Issue 12313](https://github.com/spyder-ide/spyder/issues/12313) - Spyder is opening bootstrap.py when using "python bootstrap.py" ([PR 12314](https://github.com/spyder-ide/spyder/pull/12314) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12296](https://github.com/spyder-ide/spyder/issues/12296) - "TypeError: 'bool' object is not callable" in dataframe viewer ([PR 12342](https://github.com/spyder-ide/spyder/pull/12342) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12287](https://github.com/spyder-ide/spyder/issues/12287) - TypeError when switching to plain text mode in Help for an object with no help ([PR 12308](https://github.com/spyder-ide/spyder/pull/12308) by [@steff456](https://github.com/steff456))
* [Issue 12280](https://github.com/spyder-ide/spyder/issues/12280) - Error when clearing variables in the Variable Explorer ([PR 12363](https://github.com/spyder-ide/spyder/pull/12363) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12253](https://github.com/spyder-ide/spyder/issues/12253) - ZeroDivisionError when trying to show a plot ([PR 12455](https://github.com/spyder-ide/spyder/pull/12455) by [@steff456](https://github.com/steff456))
* [Issue 12244](https://github.com/spyder-ide/spyder/issues/12244) - Something broke recently with windows CI ([PR 11066](https://github.com/spyder-ide/spyder/pull/11066) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12215](https://github.com/spyder-ide/spyder/issues/12215) - View variable explorer supported objects in the object explorer ([PR 12260](https://github.com/spyder-ide/spyder/pull/12260) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12210](https://github.com/spyder-ide/spyder/issues/12210) - Save console output generates errors
* [Issue 12201](https://github.com/spyder-ide/spyder/issues/12201) - Problem when closing a project ([PR 12439](https://github.com/spyder-ide/spyder/pull/12439) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12179](https://github.com/spyder-ide/spyder/issues/12179) - Shortcuts table loads whatever is saved on the shortcuts section ([PR 12177](https://github.com/spyder-ide/spyder/pull/12177) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12168](https://github.com/spyder-ide/spyder/issues/12168) - Shortcuts on tips not adapted to platform ([PR 12169](https://github.com/spyder-ide/spyder/pull/12169) by [@goanpeca](https://github.com/goanpeca))
* [Issue 12154](https://github.com/spyder-ide/spyder/issues/12154) - White brackets in the Obsidian theme ([PR 12270](https://github.com/spyder-ide/spyder/pull/12270) by [@juanis2112](https://github.com/juanis2112))
* [Issue 12139](https://github.com/spyder-ide/spyder/issues/12139) - If main window is closed with undocked panes, those are not shown during the next session ([PR 12294](https://github.com/spyder-ide/spyder/pull/12294) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12102](https://github.com/spyder-ide/spyder/issues/12102) - Namespace is not set correctly while debugging ([PR 12117](https://github.com/spyder-ide/spyder/pull/12117) by [@impact27](https://github.com/impact27))
* [Issue 12034](https://github.com/spyder-ide/spyder/issues/12034) - NameError: free variable 'self' referenced before assignment in Variable Explorer ([PR 12109](https://github.com/spyder-ide/spyder/pull/12109) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11986](https://github.com/spyder-ide/spyder/issues/11986) - "Directly enter debugging when errors appear" is not working ([PR 12148](https://github.com/spyder-ide/spyder/pull/12148) by [@impact27](https://github.com/impact27))
* [Issue 11961](https://github.com/spyder-ide/spyder/issues/11961) - Duplicate line down has changed behavior with Duplicate line up
* [Issue 11953](https://github.com/spyder-ide/spyder/issues/11953) - "TypeError: not enough arguments for format string" when starting Spyder in Portuguese
* [Issue 11930](https://github.com/spyder-ide/spyder/issues/11930) - Tests are fragile ([PR 11066](https://github.com/spyder-ide/spyder/pull/11066) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11923](https://github.com/spyder-ide/spyder/issues/11923) - Run in console's namespace with existing kernel not working ([PR 12436](https://github.com/spyder-ide/spyder/pull/12436) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11919](https://github.com/spyder-ide/spyder/issues/11919) - An issue with the "File Association" example in the settings ([PR 12093](https://github.com/spyder-ide/spyder/pull/12093) by [@steff456](https://github.com/steff456))
* [Issue 11880](https://github.com/spyder-ide/spyder/issues/11880) - Spyder doesn't start in Python 3.8 ([PR 12178](https://github.com/spyder-ide/spyder/pull/12178) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11875](https://github.com/spyder-ide/spyder/issues/11875) - Profiler crash in Spyder 4.1.0 ([PR 12094](https://github.com/spyder-ide/spyder/pull/12094) by [@steff456](https://github.com/steff456))
* [Issue 11870](https://github.com/spyder-ide/spyder/issues/11870) - test_mainwindow incorrectly picks up pytest arguments ([PR 11704](https://github.com/spyder-ide/spyder/pull/11704) by [@CAM-Gerlach](https://github.com/CAM-Gerlach))
* [Issue 11790](https://github.com/spyder-ide/spyder/issues/11790) - ZeroDivisionError when viewing dataframes ([PR 12341](https://github.com/spyder-ide/spyder/pull/12341) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11698](https://github.com/spyder-ide/spyder/issues/11698) - Go to previous cursor position not working ([PR 12114](https://github.com/spyder-ide/spyder/pull/12114) by [@steff456](https://github.com/steff456))
* [Issue 11235](https://github.com/spyder-ide/spyder/issues/11235) - TypeError when starting Kite client ([PR 12364](https://github.com/spyder-ide/spyder/pull/12364) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11152](https://github.com/spyder-ide/spyder/issues/11152) - pyls-mypy messages are not displayed correctly in some cases ([PR 12519](https://github.com/spyder-ide/spyder/pull/12519) by [@steff456](https://github.com/steff456))
* [Issue 10148](https://github.com/spyder-ide/spyder/issues/10148) - Editor unindents when typing : ([PR 12055](https://github.com/spyder-ide/spyder/pull/12055) by [@remisalmon](https://github.com/remisalmon))
* [Issue 10124](https://github.com/spyder-ide/spyder/issues/10124) - Explain CodeEditor's parameters within the doctring ([PR 12290](https://github.com/spyder-ide/spyder/pull/12290) by [@Akashtyagi08](https://github.com/Akashtyagi08))
* [Issue 9696](https://github.com/spyder-ide/spyder/issues/9696) - Online Help pane doesn't support the dark theme ([PR 11893](https://github.com/spyder-ide/spyder/pull/11893) by [@dalthviz](https://github.com/dalthviz))
* [Issue 7831](https://github.com/spyder-ide/spyder/issues/7831) - Inconsistent behavior with creating/saving files with default names ([PR 12359](https://github.com/spyder-ide/spyder/pull/12359) by [@steff456](https://github.com/steff456))

In this release 46 issues were closed.

### Pull Requests Merged

* [PR 12632](https://github.com/spyder-ide/spyder/pull/12632) - PR: Update minimal required version of spyder-kernels to 1.9.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12629](https://github.com/spyder-ide/spyder/pull/12629) - PR: Update translations for 4.1.3, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 12618](https://github.com/spyder-ide/spyder/pull/12618) - PR: Update translation file strings, by [@goanpeca](https://github.com/goanpeca)
* [PR 12613](https://github.com/spyder-ide/spyder/pull/12613) - PR: Invert duplicate line down and up behaviour, by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 12606](https://github.com/spyder-ide/spyder/pull/12606) - PR: Hide tooltip and calltip widgets when window is not active, by [@ccordoba12](https://github.com/ccordoba12) ([12477](https://github.com/spyder-ide/spyder/issues/12477))
* [PR 12590](https://github.com/spyder-ide/spyder/pull/12590) - PR: Update check-manifest ignore rules to work with its 0.42 version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12580](https://github.com/spyder-ide/spyder/pull/12580) - PR: Install Pylint 2.4 in our CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12569](https://github.com/spyder-ide/spyder/pull/12569) - PR: Fix color constrast in Solarized themes, by [@grantcarthew](https://github.com/grantcarthew)
* [PR 12549](https://github.com/spyder-ide/spyder/pull/12549) - PR: More improvements to Online Help, by [@dalthviz](https://github.com/dalthviz)
* [PR 12526](https://github.com/spyder-ide/spyder/pull/12526) - PR: A couple of fixes for the python-language-server subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12519](https://github.com/spyder-ide/spyder/pull/12519) - PR: Correctly display messages from the pyls-mypy plugin, by [@steff456](https://github.com/steff456) ([11152](https://github.com/spyder-ide/spyder/issues/11152))
* [PR 12518](https://github.com/spyder-ide/spyder/pull/12518) - PR: Fix segfault on Unix systems when removing plots, by [@goanpeca](https://github.com/goanpeca) ([12459](https://github.com/spyder-ide/spyder/issues/12459))
* [PR 12516](https://github.com/spyder-ide/spyder/pull/12516) - PR: Handle error when checking if Kite is already running, by [@dalthviz](https://github.com/dalthviz) ([12510](https://github.com/spyder-ide/spyder/issues/12510))
* [PR 12514](https://github.com/spyder-ide/spyder/pull/12514) - PR: Fix missing shortcuts on Preferences, by [@goanpeca](https://github.com/goanpeca) ([12415](https://github.com/spyder-ide/spyder/issues/12415))
* [PR 12513](https://github.com/spyder-ide/spyder/pull/12513) - PR: Update test_run_static_code_analysis for the latest Pylint version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12508](https://github.com/spyder-ide/spyder/pull/12508) - PR: Handle KeyError when processing rename in autosave, by [@jitseniesen](https://github.com/jitseniesen) ([12396](https://github.com/spyder-ide/spyder/issues/12396))
* [PR 12467](https://github.com/spyder-ide/spyder/pull/12467) - PR: Encode and store UTF-8 files by default, by [@andfoy](https://github.com/andfoy) ([12416](https://github.com/spyder-ide/spyder/issues/12416))
* [PR 12458](https://github.com/spyder-ide/spyder/pull/12458) - PR: Change convention and refactor icons on the code analysis pane, by [@juanis2112](https://github.com/juanis2112)
* [PR 12455](https://github.com/spyder-ide/spyder/pull/12455) - PR: Add broken icon in the Plots pane if the figure is corrupted, by [@steff456](https://github.com/steff456) ([12253](https://github.com/spyder-ide/spyder/issues/12253))
* [PR 12453](https://github.com/spyder-ide/spyder/pull/12453) - PR: Fix unstable completions when using backspace, by [@steff456](https://github.com/steff456) ([12417](https://github.com/spyder-ide/spyder/issues/12417))
* [PR 12452](https://github.com/spyder-ide/spyder/pull/12452) - PR: Code analysis and debug markers correctly positioned when code is folded, by [@steff456](https://github.com/steff456) ([12321](https://github.com/spyder-ide/spyder/issues/12321))
* [PR 12448](https://github.com/spyder-ide/spyder/pull/12448) - PR: Catch AttributeError when closing a console, by [@steff456](https://github.com/steff456) ([12400](https://github.com/spyder-ide/spyder/issues/12400))
* [PR 12445](https://github.com/spyder-ide/spyder/pull/12445) - PR: Remove warning message when undocking panes, by [@goanpeca](https://github.com/goanpeca)
* [PR 12439](https://github.com/spyder-ide/spyder/pull/12439) - PR: Add validation for current line values when loading files (Editor), by [@dalthviz](https://github.com/dalthviz) ([12201](https://github.com/spyder-ide/spyder/issues/12201))
* [PR 12436](https://github.com/spyder-ide/spyder/pull/12436) - PR: Use runfile for external spyder-kernels, by [@dalthviz](https://github.com/dalthviz) ([11923](https://github.com/spyder-ide/spyder/issues/11923))
* [PR 12435](https://github.com/spyder-ide/spyder/pull/12435) - PR: Add support for a string response when getting Kite available languages, by [@dalthviz](https://github.com/dalthviz) ([12410](https://github.com/spyder-ide/spyder/issues/12410))
* [PR 12432](https://github.com/spyder-ide/spyder/pull/12432) - PR: Link the Contributing guide on our Readme to tell people how to run Spyder from a clone, by [@ccordoba12](https://github.com/ccordoba12) ([12424](https://github.com/spyder-ide/spyder/issues/12424))
* [PR 12389](https://github.com/spyder-ide/spyder/pull/12389) - PR: Add a git subrepo for the python-language-server, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12376](https://github.com/spyder-ide/spyder/pull/12376) - PR: Make test_get_git_refs work when merging against 4.x, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 12374](https://github.com/spyder-ide/spyder/pull/12374) - PR: Trigger documentDidChange on backspace, by [@andfoy](https://github.com/andfoy) ([12373](https://github.com/spyder-ide/spyder/issues/12373))
* [PR 12364](https://github.com/spyder-ide/spyder/pull/12364) - PR: Handle string status responses in Kite due to VPN errors, by [@dalthviz](https://github.com/dalthviz) ([12357](https://github.com/spyder-ide/spyder/issues/12357), [11235](https://github.com/spyder-ide/spyder/issues/11235))
* [PR 12363](https://github.com/spyder-ide/spyder/pull/12363) - PR: Make refresh namespacebrowser an interrupt call (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([12280](https://github.com/spyder-ide/spyder/issues/12280))
* [PR 12362](https://github.com/spyder-ide/spyder/pull/12362) - PR: Fix the same font in Preferences and update action icons (Online Help), by [@dalthviz](https://github.com/dalthviz)
* [PR 12359](https://github.com/spyder-ide/spyder/pull/12359) - PR: Fix inconsistent behavior when creating/saving files with default names, by [@steff456](https://github.com/steff456) ([7831](https://github.com/spyder-ide/spyder/issues/7831))
* [PR 12342](https://github.com/spyder-ide/spyder/pull/12342) - PR: Use def instead of lambda to define slots for data conversion (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([12296](https://github.com/spyder-ide/spyder/issues/12296))
* [PR 12341](https://github.com/spyder-ide/spyder/pull/12341) - PR: Validate column max/min difference (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([11790](https://github.com/spyder-ide/spyder/issues/11790))
* [PR 12314](https://github.com/spyder-ide/spyder/pull/12314) - PR: Don't pass sys.argv to get_options if not running tests, by [@ccordoba12](https://github.com/ccordoba12) ([12313](https://github.com/spyder-ide/spyder/issues/12313))
* [PR 12308](https://github.com/spyder-ide/spyder/pull/12308) - PR: Fix TypeError in the Help plugin in plain text mode, by [@steff456](https://github.com/steff456) ([12287](https://github.com/spyder-ide/spyder/issues/12287))
* [PR 12297](https://github.com/spyder-ide/spyder/pull/12297) - PR: Only cancel previous builds on pull_request events, by [@goanpeca](https://github.com/goanpeca)
* [PR 12294](https://github.com/spyder-ide/spyder/pull/12294) - PR: Save main window settings after plugin windows are closed, by [@ccordoba12](https://github.com/ccordoba12) ([12139](https://github.com/spyder-ide/spyder/issues/12139))
* [PR 12290](https://github.com/spyder-ide/spyder/pull/12290) - PR: Add docstring to explain CodeEditor parameters, by [@Akashtyagi08](https://github.com/Akashtyagi08) ([10124](https://github.com/spyder-ide/spyder/issues/10124))
* [PR 12286](https://github.com/spyder-ide/spyder/pull/12286) - PR: Emit sig_editor_shown for objects that can be edited inline in the Variable Explorer, by [@juanis2112](https://github.com/juanis2112)
* [PR 12283](https://github.com/spyder-ide/spyder/pull/12283) - PR: Update README build badges, by [@goanpeca](https://github.com/goanpeca)
* [PR 12281](https://github.com/spyder-ide/spyder/pull/12281) - PR: Add skip to builds plus check for skipping if PRs do not change Python files, by [@goanpeca](https://github.com/goanpeca)
* [PR 12270](https://github.com/spyder-ide/spyder/pull/12270) - PR: Change color of matched brackets in some of the dark highlighting themes, by [@juanis2112](https://github.com/juanis2112) ([12154](https://github.com/spyder-ide/spyder/issues/12154))
* [PR 12260](https://github.com/spyder-ide/spyder/pull/12260) - PR: Remove restriction to populate object attributes in the Object Explorer, by [@dalthviz](https://github.com/dalthviz) ([12215](https://github.com/spyder-ide/spyder/issues/12215))
* [PR 12256](https://github.com/spyder-ide/spyder/pull/12256) - PR: Enable status check for stdio LSP servers, by [@andfoy](https://github.com/andfoy)
* [PR 12234](https://github.com/spyder-ide/spyder/pull/12234) - PR: Fix file tests for shortcuts, by [@goanpeca](https://github.com/goanpeca)
* [PR 12227](https://github.com/spyder-ide/spyder/pull/12227) - PR: Fix running fast tests locally on macOS, by [@goanpeca](https://github.com/goanpeca)
* [PR 12181](https://github.com/spyder-ide/spyder/pull/12181) - PR: Move dock attributes from plugin to dockwidget, by [@goanpeca](https://github.com/goanpeca)
* [PR 12178](https://github.com/spyder-ide/spyder/pull/12178) - PR: Patch asyncio to start Spyder with Python 3.8 on Windows, by [@dalthviz](https://github.com/dalthviz) ([11880](https://github.com/spyder-ide/spyder/issues/11880))
* [PR 12177](https://github.com/spyder-ide/spyder/pull/12177) - PR: Register actions without shortcuts and only display registered actions, by [@goanpeca](https://github.com/goanpeca) ([12179](https://github.com/spyder-ide/spyder/issues/12179))
* [PR 12169](https://github.com/spyder-ide/spyder/pull/12169) - PR: Display correct shortcut string on tooltips, by [@goanpeca](https://github.com/goanpeca) ([12168](https://github.com/spyder-ide/spyder/issues/12168))
* [PR 12148](https://github.com/spyder-ide/spyder/pull/12148) - PR: Add a test for post mortem functionality in the console, by [@impact27](https://github.com/impact27) ([11986](https://github.com/spyder-ide/spyder/issues/11986))
* [PR 12140](https://github.com/spyder-ide/spyder/pull/12140) - PR: Fix completion hiding when within function or comprehension., by [@ElieGouzien](https://github.com/ElieGouzien)
* [PR 12119](https://github.com/spyder-ide/spyder/pull/12119) - PR: Fix links to PyQt5 docs, by [@StefRe](https://github.com/StefRe)
* [PR 12117](https://github.com/spyder-ide/spyder/pull/12117) - PR: Test that we set the namespace correctly while debugging, by [@impact27](https://github.com/impact27) ([12102](https://github.com/spyder-ide/spyder/issues/12102))
* [PR 12114](https://github.com/spyder-ide/spyder/pull/12114) - PR: Fix go to previous/next cursor position , by [@steff456](https://github.com/steff456) ([11698](https://github.com/spyder-ide/spyder/issues/11698))
* [PR 12109](https://github.com/spyder-ide/spyder/pull/12109) - PR: Catch NameError when trying to load more data in the dataframe and array viewers, by [@dalthviz](https://github.com/dalthviz) ([12034](https://github.com/spyder-ide/spyder/issues/12034))
* [PR 12094](https://github.com/spyder-ide/spyder/pull/12094) - PR: Remove size parameter in TextEditor constructor call, by [@steff456](https://github.com/steff456) ([11875](https://github.com/spyder-ide/spyder/issues/11875))
* [PR 12093](https://github.com/spyder-ide/spyder/pull/12093) - PR: Fix file association dialog example in settings, by [@steff456](https://github.com/steff456) ([11919](https://github.com/spyder-ide/spyder/issues/11919))
* [PR 12055](https://github.com/spyder-ide/spyder/pull/12055) - PR: Correctly unindent code for valid Python, by [@remisalmon](https://github.com/remisalmon) ([10148](https://github.com/spyder-ide/spyder/issues/10148))
* [PR 11893](https://github.com/spyder-ide/spyder/pull/11893) - PR: Use custom CSS when serving docs for the Online Help, by [@dalthviz](https://github.com/dalthviz) ([9696](https://github.com/spyder-ide/spyder/issues/9696))
* [PR 11704](https://github.com/spyder-ide/spyder/pull/11704) - PR: Fix issues parsing runtests.py args and passing them properly to Spyder and Pytest, by [@CAM-Gerlach](https://github.com/CAM-Gerlach) ([11870](https://github.com/spyder-ide/spyder/issues/11870))
* [PR 11066](https://github.com/spyder-ide/spyder/pull/11066) - PR: Use github actions to run all our tests, by [@goanpeca](https://github.com/goanpeca) ([12244](https://github.com/spyder-ide/spyder/issues/12244), [11930](https://github.com/spyder-ide/spyder/issues/11930))

In this release 65 pull requests were closed.


---


## Version 4.1.2 (2020-04-03)

### New features

* Add a new entry to the status bar to show the current state of the Python
  language server. This will allow users to know if completions, linting and
  folding are working as expected or have issues. Clicking on this entry will
  also show a menu from which is possible to restart the server manually.

### Important fixes

* Completely disable warning informing to restart Spyder when a screen
  resolution is detected on macOS.
* Show an error message when it's not possible to create a special console
  for Sympy, Cython or Pylab.
* Restore code folding for all files with less than 2000 lines.
* Fix showing help for dot objects (e.g. `np.sin`) in the IPython console.
* Fix showing kernel initialization error messages on Windows.

### Issues Closed

* [Issue 12091](https://github.com/spyder-ide/spyder/issues/12091) - Update translations for 4.1.2 ([PR 11825](https://github.com/spyder-ide/spyder/pull/11825) by [@spyder-bot](https://github.com/spyder-bot))
* [Issue 12052](https://github.com/spyder-ide/spyder/issues/12052) - TypeError when trying to view output of Code Analysis pane ([PR 12053](https://github.com/spyder-ide/spyder/pull/12053) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 12026](https://github.com/spyder-ide/spyder/issues/12026) - Segmentation fault while painting flags ([PR 12036](https://github.com/spyder-ide/spyder/pull/12036) by [@impact27](https://github.com/impact27))
* [Issue 12024](https://github.com/spyder-ide/spyder/issues/12024) - Unable to save file to mapped network drive on Windows 7 ([PR 12050](https://github.com/spyder-ide/spyder/pull/12050) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11997](https://github.com/spyder-ide/spyder/issues/11997) - RuntimeError when disconnecting monitors ([PR 12008](https://github.com/spyder-ide/spyder/pull/12008) by [@steff456](https://github.com/steff456))
* [Issue 11988](https://github.com/spyder-ide/spyder/issues/11988) - OSError when importing Numpy in Object Explorer  ([PR 12003](https://github.com/spyder-ide/spyder/pull/12003) by [@steff456](https://github.com/steff456))
* [Issue 11963](https://github.com/spyder-ide/spyder/issues/11963) - Error when trying to delete two or more variables ([PR 11968](https://github.com/spyder-ide/spyder/pull/11968) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11903](https://github.com/spyder-ide/spyder/issues/11903) - TypeError when changing monitors ([PR 11937](https://github.com/spyder-ide/spyder/pull/11937) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11885](https://github.com/spyder-ide/spyder/issues/11885) - test_arrayeditor.py::test_arrayeditor_with_inf_array fails because of deprecation warning (Py3.8) ([PR 11899](https://github.com/spyder-ide/spyder/pull/11899) by [@bnavigator](https://github.com/bnavigator))
* [Issue 11872](https://github.com/spyder-ide/spyder/issues/11872) - psutil.NoSuchProcess when restarting the kernel ([PR 11910](https://github.com/spyder-ide/spyder/pull/11910) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11869](https://github.com/spyder-ide/spyder/issues/11869) - Code folding disabled w/ <2000 lines (4.1.1) ([PR 11888](https://github.com/spyder-ide/spyder/pull/11888) by [@steff456](https://github.com/steff456))
* [Issue 11862](https://github.com/spyder-ide/spyder/issues/11862) - IndexError: string index out of range in fallback plugin ([PR 12077](https://github.com/spyder-ide/spyder/pull/12077) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11846](https://github.com/spyder-ide/spyder/issues/11846) - Popup "A monitor scale change was detected" every few minutes ([PR 11884](https://github.com/spyder-ide/spyder/pull/11884) by [@steff456](https://github.com/steff456))
* [Issue 11821](https://github.com/spyder-ide/spyder/issues/11821) - Completion doc widget and editor/console to help improvements ([PR 11826](https://github.com/spyder-ide/spyder/pull/11826) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11622](https://github.com/spyder-ide/spyder/issues/11622) - UI enhancements to the Variable Explorer ([PR 11814](https://github.com/spyder-ide/spyder/pull/11814) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11026](https://github.com/spyder-ide/spyder/issues/11026) - Code completion and linting stop working during the current session ([PR 12020](https://github.com/spyder-ide/spyder/pull/12020) by [@goanpeca](https://github.com/goanpeca))

In this release 16 issues were closed.

### Pull Requests Merged

* [PR 12083](https://github.com/spyder-ide/spyder/pull/12083) - PR: Update translation files, by [@goanpeca](https://github.com/goanpeca)
* [PR 12077](https://github.com/spyder-ide/spyder/pull/12077) - PR: Prevent error when checking if prefix is valid in fallback with utf-16 characters, by [@ccordoba12](https://github.com/ccordoba12) ([11862](https://github.com/spyder-ide/spyder/issues/11862))
* [PR 12053](https://github.com/spyder-ide/spyder/pull/12053) - PR: Fix error when showing Pylint output, by [@ccordoba12](https://github.com/ccordoba12) ([12052](https://github.com/spyder-ide/spyder/issues/12052))
* [PR 12050](https://github.com/spyder-ide/spyder/pull/12050) - PR: Add validation for path existence before writing to filename, by [@dalthviz](https://github.com/dalthviz) ([12024](https://github.com/spyder-ide/spyder/issues/12024))
* [PR 12043](https://github.com/spyder-ide/spyder/pull/12043) - PR: Fix typo in Windows executable filename extensions, by [@StefRe](https://github.com/StefRe)
* [PR 12036](https://github.com/spyder-ide/spyder/pull/12036) - PR: Avoid segfault when painting flags after removing lines, by [@impact27](https://github.com/impact27) ([12026](https://github.com/spyder-ide/spyder/issues/12026))
* [PR 12020](https://github.com/spyder-ide/spyder/pull/12020) - PR: Add autorestart mechanism for LSP servers and status widget with menu to restart them manually, by [@goanpeca](https://github.com/goanpeca) ([11026](https://github.com/spyder-ide/spyder/issues/11026))
* [PR 12008](https://github.com/spyder-ide/spyder/pull/12008) - PR: Catch RuntimeError to prevent errors when disconnecting monitors, by [@steff456](https://github.com/steff456) ([11997](https://github.com/spyder-ide/spyder/issues/11997))
* [PR 12003](https://github.com/spyder-ide/spyder/pull/12003) - PR: Fix OSError when importing Numpy in Object Explorer, by [@steff456](https://github.com/steff456) ([11988](https://github.com/spyder-ide/spyder/issues/11988))
* [PR 11991](https://github.com/spyder-ide/spyder/pull/11991) - PR: Check if block is valid before painting it in the scrollflag panel, by [@impact27](https://github.com/impact27)
* [PR 11982](https://github.com/spyder-ide/spyder/pull/11982) - PR: Make a string translatable, by [@bnavigator](https://github.com/bnavigator)
* [PR 11968](https://github.com/spyder-ide/spyder/pull/11968) - PR: Set data only one time after multiple removes, by [@dalthviz](https://github.com/dalthviz) ([11963](https://github.com/spyder-ide/spyder/issues/11963))
* [PR 11937](https://github.com/spyder-ide/spyder/pull/11937) - PR: Catch TypeError when handling screen change, by [@dalthviz](https://github.com/dalthviz) ([11903](https://github.com/spyder-ide/spyder/issues/11903))
* [PR 11910](https://github.com/spyder-ide/spyder/pull/11910) - PR: Fix error when restarting the kernel and restore showing kernel errors on Windows, by [@ccordoba12](https://github.com/ccordoba12) ([11872](https://github.com/spyder-ide/spyder/issues/11872))
* [PR 11899](https://github.com/spyder-ide/spyder/pull/11899) - PR: Fix deprecation warnings, by [@bnavigator](https://github.com/bnavigator) ([11885](https://github.com/spyder-ide/spyder/issues/11885))
* [PR 11888](https://github.com/spyder-ide/spyder/pull/11888) - PR: Activate code folding when the panel is not visible, by [@steff456](https://github.com/steff456) ([11869](https://github.com/spyder-ide/spyder/issues/11869))
* [PR 11886](https://github.com/spyder-ide/spyder/pull/11886) - PR: Fix tests in Azure/macOS, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11884](https://github.com/spyder-ide/spyder/pull/11884) - PR: Disable screen resolution change message in macOS and allow to hide it during the current session, by [@steff456](https://github.com/steff456) ([11846](https://github.com/spyder-ide/spyder/issues/11846))
* [PR 11826](https://github.com/spyder-ide/spyder/pull/11826) - PR: Fix getting help from the console for dot objects and remove redundant info from completion hints, by [@dalthviz](https://github.com/dalthviz) ([11821](https://github.com/spyder-ide/spyder/issues/11821))
* [PR 11825](https://github.com/spyder-ide/spyder/pull/11825) - PR: New translations for 4.1.2, by [@spyder-bot](https://github.com/spyder-bot) ([12091](https://github.com/spyder-ide/spyder/issues/12091))
* [PR 11824](https://github.com/spyder-ide/spyder/pull/11824) - PR: Correctly hide already complete word in completion widget, by [@ElieGouzien](https://github.com/ElieGouzien)
* [PR 11814](https://github.com/spyder-ide/spyder/pull/11814) - PR: Add loading indicator for the Variable Explorer, by [@dalthviz](https://github.com/dalthviz) ([11622](https://github.com/spyder-ide/spyder/issues/11622))
* [PR 11365](https://github.com/spyder-ide/spyder/pull/11365) - PR: Detect unavailable dependencies for special consoles, by [@dalthviz](https://github.com/dalthviz)

In this release 23 pull requests were closed.


----


## Version 4.1.1 (2020-03-18)

### New features

* Add file path completions to the Editor. This works by writing the
  beginning of a file path, either absolute or relative, inside a
  string and pressing `Tab` or `Ctrl+Space` to get completions for
  it.
* Add a new command line option called `--report-segfault` to be
  able to send segmentation fault reports to Github.

### Important fixes

* Fix a critical error when starting kernels on Windows.
* Update Jedi to 0.15.2.
* Add conda activation scripts for the kernel to the package.

### Issues Closed

* [Issue 11851](https://github.com/spyder-ide/spyder/issues/11851) - TimeoutError: Timeout while waiting for comm port ([PR 11853](https://github.com/spyder-ide/spyder/pull/11853) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11819](https://github.com/spyder-ide/spyder/issues/11819) - Activation of kernel env fails when using anaconda shortcut (FileNotFound error kernel start 4.1.0) ([PR 11838](https://github.com/spyder-ide/spyder/pull/11838) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11634](https://github.com/spyder-ide/spyder/issues/11634) - Error when importing CSV  file from  Variable tab  ([PR 11812](https://github.com/spyder-ide/spyder/pull/11812) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11150](https://github.com/spyder-ide/spyder/issues/11150) - Unable to load docstring into "Help" pane for functions with certain decorators ([PR 11809](https://github.com/spyder-ide/spyder/pull/11809) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 10536](https://github.com/spyder-ide/spyder/issues/10536) - Send segmentation fault reports to Github ([PR 10553](https://github.com/spyder-ide/spyder/pull/10553) by [@impact27](https://github.com/impact27))
* [Issue 5519](https://github.com/spyder-ide/spyder/issues/5519) - Add path autocompletion to the Editor

In this release 6 issues were closed.

### Pull Requests Merged

* [PR 11854](https://github.com/spyder-ide/spyder/pull/11854) - PR: Update minimal required version for the PyLS, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11853](https://github.com/spyder-ide/spyder/pull/11853) - PR: Increase time to detect if kernel is alive and to receive the comm config, by [@ccordoba12](https://github.com/ccordoba12) ([11851](https://github.com/spyder-ide/spyder/issues/11851))
* [PR 11841](https://github.com/spyder-ide/spyder/pull/11841) - PR: Install the right version of jupyter_client for Python 2 in our CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11838](https://github.com/spyder-ide/spyder/pull/11838) - PR: Add conda activation scripts to the package, by [@ccordoba12](https://github.com/ccordoba12) ([11819](https://github.com/spyder-ide/spyder/issues/11819))
* [PR 11812](https://github.com/spyder-ide/spyder/pull/11812) - PR: Fix validation for import as ndarray/array, by [@dalthviz](https://github.com/dalthviz) ([11634](https://github.com/spyder-ide/spyder/issues/11634))
* [PR 11809](https://github.com/spyder-ide/spyder/pull/11809) - PR: Update Jedi requirement to 0.15.2, by [@ccordoba12](https://github.com/ccordoba12) ([11150](https://github.com/spyder-ide/spyder/issues/11150))
* [PR 11807](https://github.com/spyder-ide/spyder/pull/11807) - PR: Restore rtree to the conda deps, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 10553](https://github.com/spyder-ide/spyder/pull/10553) - PR: Allow to report segmentation faults to Github, by [@impact27](https://github.com/impact27) ([10536](https://github.com/spyder-ide/spyder/issues/10536))

In this release 8 pull requests were closed.


----


## Version 4.1.0 (2020-03-15)

### New features

* Several improvements to the interface and user experience of the Plots pane.
* Show hidden files in Files and Project panes.
* Allow automatic introduction of docstrings in the Sphinx format.
* Implicitly create a project when Spyder is launched with a folder path as
  argument in the command line
* Activate conda environment prior to kernel start in the IPython console.
* Re-add the ability to run IPython magics inside of cells.
* Allow running PyQt applications multiple times.
* Make adjustable the maximum number of recent projects in the Projects
  menu.

### Important fixes

* Disable code folding and indent guides when files have more than 2000 lines
  for performance reasons.
* Critical performance improvements to the Editor and Files.
* Several fixes to the autosave mechanism.
* Preserve creation time when saving files.
* Don't corrupt symlinks when saving files associated to them.
* Improve the code completion experience in the Editor.
* Start kernels in a thread to avoid freezing the entire interface.
* Correctly update the debugging panel in the Editor when debugging in
  multiple consoles.
* Make the Code Analysis pane to read the nearest pylintrc file, according to
  the hierarchy defined by Pylint.

### Issues Closed

* [Issue 11765](https://github.com/spyder-ide/spyder/issues/11765) - Highlighting does not work for terminal-style completions in the iPython console ([PR 11766](https://github.com/spyder-ide/spyder/pull/11766) by [@keepiru](https://github.com/keepiru))
* [Issue 11731](https://github.com/spyder-ide/spyder/issues/11731) - Update translations for 4.1 ([PR 11772](https://github.com/spyder-ide/spyder/pull/11772) by [@spyder-bot](https://github.com/spyder-bot))
* [Issue 11718](https://github.com/spyder-ide/spyder/issues/11718) - Symbolic and hard links "broken" when saving files ([PR 11722](https://github.com/spyder-ide/spyder/pull/11722) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11692](https://github.com/spyder-ide/spyder/issues/11692) - Crowdin translations are outdated ([PR 11711](https://github.com/spyder-ide/spyder/pull/11711) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11671](https://github.com/spyder-ide/spyder/issues/11671) - No code folding at startup ([PR 11681](https://github.com/spyder-ide/spyder/pull/11681) by [@andfoy](https://github.com/andfoy))
* [Issue 11652](https://github.com/spyder-ide/spyder/issues/11652) - Facing error when trying to open spyder tutorial ([PR 11762](https://github.com/spyder-ide/spyder/pull/11762) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11630](https://github.com/spyder-ide/spyder/issues/11630) - Cell shortcut remap not sticking on macOS ([PR 11661](https://github.com/spyder-ide/spyder/pull/11661) by [@steff456](https://github.com/steff456))
* [Issue 11625](https://github.com/spyder-ide/spyder/issues/11625) - Code completion is added when indenting code ([PR 11650](https://github.com/spyder-ide/spyder/pull/11650) by [@andfoy](https://github.com/andfoy))
* [Issue 11609](https://github.com/spyder-ide/spyder/issues/11609) - UnicodeEncodeError in save_autosave_mapping ([PR 11619](https://github.com/spyder-ide/spyder/pull/11619) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 11600](https://github.com/spyder-ide/spyder/issues/11600) - Auto-completion should not complete already complete words ([PR 11732](https://github.com/spyder-ide/spyder/pull/11732) by [@steff456](https://github.com/steff456))
* [Issue 11597](https://github.com/spyder-ide/spyder/issues/11597) - Spyder not launching when Kite installation is faulty ([PR 11602](https://github.com/spyder-ide/spyder/pull/11602) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11596](https://github.com/spyder-ide/spyder/issues/11596) - Variable of npz file cannot be read if namespace has the same name ([PR 11628](https://github.com/spyder-ide/spyder/pull/11628) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11591](https://github.com/spyder-ide/spyder/issues/11591) - Options for different modes of documentation are not available when the Help Pane is undocked.  ([PR 11593](https://github.com/spyder-ide/spyder/pull/11593) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11586](https://github.com/spyder-ide/spyder/issues/11586) - spyder --defaults raises TypeError ([PR 11587](https://github.com/spyder-ide/spyder/pull/11587) by [@steff456](https://github.com/steff456))
* [Issue 11579](https://github.com/spyder-ide/spyder/issues/11579) - Help is not displaying single-line docstrings ([PR 11672](https://github.com/spyder-ide/spyder/pull/11672) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11546](https://github.com/spyder-ide/spyder/issues/11546) - test_goto_uri hangs when not run from git repository ([PR 11547](https://github.com/spyder-ide/spyder/pull/11547) by [@bnavigator](https://github.com/bnavigator))
* [Issue 11539](https://github.com/spyder-ide/spyder/issues/11539) - Unable to restart Spyder: FileNotFoundError - 'external-deps' ([PR 11541](https://github.com/spyder-ide/spyder/pull/11541) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11532](https://github.com/spyder-ide/spyder/issues/11532) - Crash when trying to run a Python file in a project from the explorer pane - Spyder 4.0.1 ([PR 11533](https://github.com/spyder-ide/spyder/pull/11533) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11526](https://github.com/spyder-ide/spyder/issues/11526) - Autocomplete dict error ([PR 11592](https://github.com/spyder-ide/spyder/pull/11592) by [@andfoy](https://github.com/andfoy))
* [Issue 11514](https://github.com/spyder-ide/spyder/issues/11514) - Error when changing the Python interpreter to Python 2 ([PR 11540](https://github.com/spyder-ide/spyder/pull/11540) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11503](https://github.com/spyder-ide/spyder/issues/11503) - "Maintain focus ..." option has no effect in Spyder4 ([PR 11554](https://github.com/spyder-ide/spyder/pull/11554) by [@steff456](https://github.com/steff456))
* [Issue 11502](https://github.com/spyder-ide/spyder/issues/11502) - Unintuitive behavior: Mouse wheel scrolling in editor steals keyboard focus ([PR 11530](https://github.com/spyder-ide/spyder/pull/11530) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11497](https://github.com/spyder-ide/spyder/issues/11497) - Spyder 4 cannot launch when Kite is installed ([PR 11517](https://github.com/spyder-ide/spyder/pull/11517) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11495](https://github.com/spyder-ide/spyder/issues/11495) - Flags are misaligned when scrolling if code is folded ([PR 11488](https://github.com/spyder-ide/spyder/pull/11488) by [@impact27](https://github.com/impact27))
* [Issue 11493](https://github.com/spyder-ide/spyder/issues/11493) - Make fallback completions respect prefix ([PR 11531](https://github.com/spyder-ide/spyder/pull/11531) by [@andfoy](https://github.com/andfoy))
* [Issue 11489](https://github.com/spyder-ide/spyder/issues/11489) - Copy file reference in variable explorer generates PicklingError ([PR 11574](https://github.com/spyder-ide/spyder/pull/11574) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11477](https://github.com/spyder-ide/spyder/issues/11477) - Imports hang after debugging (Spyder 4) ([PR 11479](https://github.com/spyder-ide/spyder/pull/11479) by [@impact27](https://github.com/impact27))
* [Issue 11471](https://github.com/spyder-ide/spyder/issues/11471) - Cannot open objects in variable explorer ([PR 11549](https://github.com/spyder-ide/spyder/pull/11549) by [@impact27](https://github.com/impact27))
* [Issue 11468](https://github.com/spyder-ide/spyder/issues/11468) - Another KeyError while autosaving ([PR 11647](https://github.com/spyder-ide/spyder/pull/11647) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 11464](https://github.com/spyder-ide/spyder/issues/11464) - Error when renaming file in the open files dialog  ([PR 11627](https://github.com/spyder-ide/spyder/pull/11627) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11455](https://github.com/spyder-ide/spyder/issues/11455) - Unable to delete multiple variables in Variable Explorer ([PR 11567](https://github.com/spyder-ide/spyder/pull/11567) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11435](https://github.com/spyder-ide/spyder/issues/11435) - Add sphinx/reStructuredText docstrings ([PR 11460](https://github.com/spyder-ide/spyder/pull/11460) by [@ok97465](https://github.com/ok97465))
* [Issue 11417](https://github.com/spyder-ide/spyder/issues/11417) - Signature calltip doesn't work without automatic bracket completion (Kite example) ([PR 11422](https://github.com/spyder-ide/spyder/pull/11422) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11412](https://github.com/spyder-ide/spyder/issues/11412) - Spyder 4.0.1 editing *really* laggy ([PR 11488](https://github.com/spyder-ide/spyder/pull/11488) by [@impact27](https://github.com/impact27))
* [Issue 11406](https://github.com/spyder-ide/spyder/issues/11406) - Kernel dies silently and doesn't restart properly. ([PR 11192](https://github.com/spyder-ide/spyder/pull/11192) by [@impact27](https://github.com/impact27))
* [Issue 11403](https://github.com/spyder-ide/spyder/issues/11403) - Spyder 4 is not preserving files creation time ([PR 11443](https://github.com/spyder-ide/spyder/pull/11443) by [@andfoy](https://github.com/andfoy))
* [Issue 11399](https://github.com/spyder-ide/spyder/issues/11399) - Snippets do not display when the text starts by underscore ([PR 11400](https://github.com/spyder-ide/spyder/pull/11400) by [@andfoy](https://github.com/andfoy))
* [Issue 11376](https://github.com/spyder-ide/spyder/issues/11376) - Infinite loop when "gl-N" (with a single digit) appears in multiline docstring ([PR 11378](https://github.com/spyder-ide/spyder/pull/11378) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11375](https://github.com/spyder-ide/spyder/issues/11375) - Corrupt autosave files don't get reset ([PR 11608](https://github.com/spyder-ide/spyder/pull/11608) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 11370](https://github.com/spyder-ide/spyder/issues/11370) - Issue reporter due to disconnected network drive after wakeup ([PR 11473](https://github.com/spyder-ide/spyder/pull/11473) by [@andfoy](https://github.com/andfoy))
* [Issue 11363](https://github.com/spyder-ide/spyder/issues/11363) - Implicitly create project when launched with a folder path as argument ([PR 11416](https://github.com/spyder-ide/spyder/pull/11416) by [@akdor1154](https://github.com/akdor1154))
* [Issue 11358](https://github.com/spyder-ide/spyder/issues/11358) - Don't restart automatically Spyder when a monitor scale change is detected ([PR 11359](https://github.com/spyder-ide/spyder/pull/11359) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11355](https://github.com/spyder-ide/spyder/issues/11355) - Editor: wrong tooltip position when undocking ([PR 11361](https://github.com/spyder-ide/spyder/pull/11361) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11351](https://github.com/spyder-ide/spyder/issues/11351) - Spyder showing Kite: unsupported on status bar ([PR 11449](https://github.com/spyder-ide/spyder/pull/11449) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11348](https://github.com/spyder-ide/spyder/issues/11348) - Renaming a python file in the file explorer causes an error ([PR 11505](https://github.com/spyder-ide/spyder/pull/11505) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 11346](https://github.com/spyder-ide/spyder/issues/11346) - Don't show "No documentation available" tooltip on hover ([PR 11377](https://github.com/spyder-ide/spyder/pull/11377) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11331](https://github.com/spyder-ide/spyder/issues/11331) - Numpy arrays not writable ([PR 11555](https://github.com/spyder-ide/spyder/pull/11555) by [@steff456](https://github.com/steff456))
* [Issue 11318](https://github.com/spyder-ide/spyder/issues/11318) - Add external plugins to dependencies ([PR 11364](https://github.com/spyder-ide/spyder/pull/11364) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11308](https://github.com/spyder-ide/spyder/issues/11308) - Spyder 4.0.1: Error when saving file to network drive (but saving worked) ([PR 11465](https://github.com/spyder-ide/spyder/pull/11465) by [@andfoy](https://github.com/andfoy))
* [Issue 11293](https://github.com/spyder-ide/spyder/issues/11293) - AltGr closes completion widget ([PR 11321](https://github.com/spyder-ide/spyder/pull/11321) by [@MaxGyver83](https://github.com/MaxGyver83))
* [Issue 11291](https://github.com/spyder-ide/spyder/issues/11291) - KeyError in folding when deleting a line ([PR 11310](https://github.com/spyder-ide/spyder/pull/11310) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11267](https://github.com/spyder-ide/spyder/issues/11267) - Improvements to the Help panel ([PR 11272](https://github.com/spyder-ide/spyder/pull/11272) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11258](https://github.com/spyder-ide/spyder/issues/11258) - Replace text is always enabled even for read-only plugins. ([PR 11259](https://github.com/spyder-ide/spyder/pull/11259) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 11247](https://github.com/spyder-ide/spyder/issues/11247) - Opening a folder with a lot of binary files freezes Spyder ([PR 11248](https://github.com/spyder-ide/spyder/pull/11248) by [@impact27](https://github.com/impact27))
* [Issue 11244](https://github.com/spyder-ide/spyder/issues/11244) - Tooltip doesn't disappear if generated on first line of editor ([PR 11271](https://github.com/spyder-ide/spyder/pull/11271) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11240](https://github.com/spyder-ide/spyder/issues/11240) - Spyder crashes at startup after setting custom high DPI scaling at less than 1.0 ([PR 11254](https://github.com/spyder-ide/spyder/pull/11254) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11237](https://github.com/spyder-ide/spyder/issues/11237) - code autocomplete inserts extra characters ([PR 11400](https://github.com/spyder-ide/spyder/pull/11400) by [@andfoy](https://github.com/andfoy))
* [Issue 11228](https://github.com/spyder-ide/spyder/issues/11228) - TypeError when disconnecting sig_display_object_info signal ([PR 11241](https://github.com/spyder-ide/spyder/pull/11241) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11227](https://github.com/spyder-ide/spyder/issues/11227) - set_options_opengl is called too late ([PR 11585](https://github.com/spyder-ide/spyder/pull/11585) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11226](https://github.com/spyder-ide/spyder/issues/11226) - AttributeError in dockwidgets tabbar ([PR 11239](https://github.com/spyder-ide/spyder/pull/11239) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11222](https://github.com/spyder-ide/spyder/issues/11222) - PyLS freezes spyder ([PR 11223](https://github.com/spyder-ide/spyder/pull/11223) by [@impact27](https://github.com/impact27))
* [Issue 11217](https://github.com/spyder-ide/spyder/issues/11217) - Extra closing parenthesis added after new line ([PR 11256](https://github.com/spyder-ide/spyder/pull/11256) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11216](https://github.com/spyder-ide/spyder/issues/11216) - Loadmat internal error in variable explorer ([PR 11238](https://github.com/spyder-ide/spyder/pull/11238) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11148](https://github.com/spyder-ide/spyder/issues/11148) - Commenting lines that include the first one in a file freezes Spyder ([PR 11212](https://github.com/spyder-ide/spyder/pull/11212) by [@impact27](https://github.com/impact27))
* [Issue 11137](https://github.com/spyder-ide/spyder/issues/11137) - TimeoutError when running cells after a kernel restart ([PR 11192](https://github.com/spyder-ide/spyder/pull/11192) by [@impact27](https://github.com/impact27))
* [Issue 11129](https://github.com/spyder-ide/spyder/issues/11129) - Variable explorer shows DatetimeIndex with numpy datetime64 format instead of timestamp ([PR 11210](https://github.com/spyder-ide/spyder/pull/11210) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11128](https://github.com/spyder-ide/spyder/issues/11128) - Indentation level is not reset when writing a comment after indent within a long instruction ([PR 11334](https://github.com/spyder-ide/spyder/pull/11334) by [@impact27](https://github.com/impact27))
* [Issue 11092](https://github.com/spyder-ide/spyder/issues/11092) - Copy line and duplicate line shortcuts are confusing ([PR 11122](https://github.com/spyder-ide/spyder/pull/11122) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 11082](https://github.com/spyder-ide/spyder/issues/11082) - Hitting esc requests code completions ([PR 11328](https://github.com/spyder-ide/spyder/pull/11328) by [@goanpeca](https://github.com/goanpeca))
* [Issue 11061](https://github.com/spyder-ide/spyder/issues/11061) - IPython magics no longer work in Spyder 4 ([PR 11103](https://github.com/spyder-ide/spyder/pull/11103) by [@impact27](https://github.com/impact27))
* [Issue 11024](https://github.com/spyder-ide/spyder/issues/11024) - Spyder 4.0.0 gives an error when restarting it in Python 2.7 ([PR 11219](https://github.com/spyder-ide/spyder/pull/11219) by [@dalthviz](https://github.com/dalthviz))
* [Issue 11023](https://github.com/spyder-ide/spyder/issues/11023) - Unexpected indent when running a single cell
* [Issue 11021](https://github.com/spyder-ide/spyder/issues/11021) - Autocomplete triggered by Ctrl + Enter ([PR 11745](https://github.com/spyder-ide/spyder/pull/11745) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 11001](https://github.com/spyder-ide/spyder/issues/11001) - KeyError when removing variables in the Variable Explorer ([PR 11567](https://github.com/spyder-ide/spyder/pull/11567) by [@dalthviz](https://github.com/dalthviz))
* [Issue 10971](https://github.com/spyder-ide/spyder/issues/10971) - Crashing in kite_tutorial.py ([PR 11287](https://github.com/spyder-ide/spyder/pull/11287) by [@dalthviz](https://github.com/dalthviz))
* [Issue 10911](https://github.com/spyder-ide/spyder/issues/10911) - Change theme settings in external plugins is not possible ([PR 11389](https://github.com/spyder-ide/spyder/pull/11389) by [@steff456](https://github.com/steff456))
* [Issue 10883](https://github.com/spyder-ide/spyder/issues/10883) - Show hidden files in the project explorer ([PR 11545](https://github.com/spyder-ide/spyder/pull/11545) by [@goanpeca](https://github.com/goanpeca))
* [Issue 10864](https://github.com/spyder-ide/spyder/issues/10864) - Date/time-based filename (when saving) for figures on Plots pane ([PR 11690](https://github.com/spyder-ide/spyder/pull/11690) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 10863](https://github.com/spyder-ide/spyder/issues/10863) - Plots should remember last saved path ([PR 11670](https://github.com/spyder-ide/spyder/pull/11670) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 10798](https://github.com/spyder-ide/spyder/issues/10798) - Completions sometimes insert extraneous text ([PR 11437](https://github.com/spyder-ide/spyder/pull/11437) by [@ok97465](https://github.com/ok97465))
* [Issue 10785](https://github.com/spyder-ide/spyder/issues/10785) - Can't change dir to network drive in console ([PR 11393](https://github.com/spyder-ide/spyder/pull/11393) by [@dalthviz](https://github.com/dalthviz))
* [Issue 10745](https://github.com/spyder-ide/spyder/issues/10745) - Variable explorer viewers too small on high DPI ([PR 10976](https://github.com/spyder-ide/spyder/pull/10976) by [@jsh9](https://github.com/jsh9))
* [Issue 10704](https://github.com/spyder-ide/spyder/issues/10704) - Segmentation fault when closing an undocked plugin ([PR 11472](https://github.com/spyder-ide/spyder/pull/11472) by [@impact27](https://github.com/impact27))
* [Issue 10657](https://github.com/spyder-ide/spyder/issues/10657) - Saving a protected file hangs Spyder ([PR 11764](https://github.com/spyder-ide/spyder/pull/11764) by [@steff456](https://github.com/steff456))
* [Issue 10640](https://github.com/spyder-ide/spyder/issues/10640) - Increase or make adjustable the maximum number of Recent Projects ([PR 10801](https://github.com/spyder-ide/spyder/pull/10801) by [@juanis2112](https://github.com/juanis2112))
* [Issue 10627](https://github.com/spyder-ide/spyder/issues/10627) - Variable explorer shortcuts not updated after configuration change ([PR 11441](https://github.com/spyder-ide/spyder/pull/11441) by [@dalthviz](https://github.com/dalthviz))
* [Issue 10538](https://github.com/spyder-ide/spyder/issues/10538) - Debugging improvements ([PR 10610](https://github.com/spyder-ide/spyder/pull/10610) by [@dalthviz](https://github.com/dalthviz))
* [Issue 9888](https://github.com/spyder-ide/spyder/issues/9888) - Missing space when rendering NumPy docstrings ([PR 11270](https://github.com/spyder-ide/spyder/pull/11270) by [@dalthviz](https://github.com/dalthviz))
* [Issue 9367](https://github.com/spyder-ide/spyder/issues/9367) - Some issues with the Plot viewer ([PR 11576](https://github.com/spyder-ide/spyder/pull/11576) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 9077](https://github.com/spyder-ide/spyder/issues/9077) - Compiled modules of non-default interpreters fail to import on Windows ([PR 11327](https://github.com/spyder-ide/spyder/pull/11327) by [@goanpeca](https://github.com/goanpeca))
* [Issue 7699](https://github.com/spyder-ide/spyder/issues/7699) - Unusual characters break help ([PR 11332](https://github.com/spyder-ide/spyder/pull/11332) by [@dalthviz](https://github.com/dalthviz))
* [Issue 6695](https://github.com/spyder-ide/spyder/issues/6695) - Cannot plot local varibles in variable explorer when debugging
* [Issue 6181](https://github.com/spyder-ide/spyder/issues/6181) - Code completion window too small on high resolution screens ([PR 11322](https://github.com/spyder-ide/spyder/pull/11322) by [@dalthviz](https://github.com/dalthviz))
* [Issue 5345](https://github.com/spyder-ide/spyder/issues/5345) - Static Code Analysis Not Reading .pylintrc file ([PR 11708](https://github.com/spyder-ide/spyder/pull/11708) by [@CAM-Gerlach](https://github.com/CAM-Gerlach))
* [Issue 2970](https://github.com/spyder-ide/spyder/issues/2970) - PyQt code cannot run twice
* [Issue 1918](https://github.com/spyder-ide/spyder/issues/1918) - `__file__` continues in namespace after runfile if ctrl-c

In this release 96 issues were closed.

### Pull Requests Merged

* [PR 11801](https://github.com/spyder-ide/spyder/pull/11801) - PR: Disable Polish translation, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11800](https://github.com/spyder-ide/spyder/pull/11800) - PR: Update version constraints for spyder-kernels, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11793](https://github.com/spyder-ide/spyder/pull/11793) - PR: Update spyder-kernels subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11772](https://github.com/spyder-ide/spyder/pull/11772) - PR: Update translations, by [@spyder-bot](https://github.com/spyder-bot) ([11731](https://github.com/spyder-ide/spyder/issues/11731))
* [PR 11770](https://github.com/spyder-ide/spyder/pull/11770) - PR: Remove line wrap from po files, by [@goanpeca](https://github.com/goanpeca)
* [PR 11766](https://github.com/spyder-ide/spyder/pull/11766) - PR: Fix broken completions highlighting in the IPython console, by [@keepiru](https://github.com/keepiru) ([11765](https://github.com/spyder-ide/spyder/issues/11765))
* [PR 11764](https://github.com/spyder-ide/spyder/pull/11764) - PR: Fix saving protected files on Windows by checking if they are read-only, by [@steff456](https://github.com/steff456) ([10657](https://github.com/spyder-ide/spyder/issues/10657))
* [PR 11762](https://github.com/spyder-ide/spyder/pull/11762) - PR: Use the same temp base dir for Sphinx config, src and build paths, by [@dalthviz](https://github.com/dalthviz) ([11652](https://github.com/spyder-ide/spyder/issues/11652))
* [PR 11755](https://github.com/spyder-ide/spyder/pull/11755) - PR: Some improvements to fallback completions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11746](https://github.com/spyder-ide/spyder/pull/11746) - PR: Fix highlighting based on Pygments, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11745](https://github.com/spyder-ide/spyder/pull/11745) - PR: Only ask for completions when text is generated after pressing a key in the Editor, by [@ccordoba12](https://github.com/ccordoba12) ([11021](https://github.com/spyder-ide/spyder/issues/11021))
* [PR 11739](https://github.com/spyder-ide/spyder/pull/11739) - PR: Add API entry for translation utilities, by [@goanpeca](https://github.com/goanpeca)
* [PR 11732](https://github.com/spyder-ide/spyder/pull/11732) - PR: Do not include complete words as part of completion suggestions, by [@steff456](https://github.com/steff456) ([11600](https://github.com/spyder-ide/spyder/issues/11600))
* [PR 11722](https://github.com/spyder-ide/spyder/pull/11722) - PR: Use resolved path (without symlinks) to save files, by [@dalthviz](https://github.com/dalthviz) ([11718](https://github.com/spyder-ide/spyder/issues/11718))
* [PR 11715](https://github.com/spyder-ide/spyder/pull/11715) - PR: Disable code folding when files are too long and add an option to disable code folding, by [@andfoy](https://github.com/andfoy)
* [PR 11714](https://github.com/spyder-ide/spyder/pull/11714) - PR: Fix issues with autocompletion characters and prevent whitespace from triggering completions, by [@andfoy](https://github.com/andfoy)
* [PR 11713](https://github.com/spyder-ide/spyder/pull/11713) - PR: Fix translations, by [@goanpeca](https://github.com/goanpeca)
* [PR 11711](https://github.com/spyder-ide/spyder/pull/11711) - PR: Update translation files, by [@goanpeca](https://github.com/goanpeca) ([11692](https://github.com/spyder-ide/spyder/issues/11692))
* [PR 11708](https://github.com/spyder-ide/spyder/pull/11708) - PR: Make pylint plugin find most local .pylintrc to given file and set cwd correctly, by [@CAM-Gerlach](https://github.com/CAM-Gerlach) ([5345](https://github.com/spyder-ide/spyder/issues/5345))
* [PR 11690](https://github.com/spyder-ide/spyder/pull/11690) - PR: Date/time-based filename (when saving) figures in Plots pane, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([10864](https://github.com/spyder-ide/spyder/issues/10864))
* [PR 11684](https://github.com/spyder-ide/spyder/pull/11684) - PR: Give focus to Plots pane when switching to it by shortcut if it's visible, by [@ok97465](https://github.com/ok97465)
* [PR 11681](https://github.com/spyder-ide/spyder/pull/11681) - PR: Prevent code folding from not being called on startup, by [@andfoy](https://github.com/andfoy) ([11671](https://github.com/spyder-ide/spyder/issues/11671))
* [PR 11672](https://github.com/spyder-ide/spyder/pull/11672) - PR: Fix hover endpoint for Kite on Windows and allow docs without signature in Help, by [@dalthviz](https://github.com/dalthviz) ([11579](https://github.com/spyder-ide/spyder/issues/11579))
* [PR 11670](https://github.com/spyder-ide/spyder/pull/11670) - PR: Remember last saved path in Plots pane, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([10863](https://github.com/spyder-ide/spyder/issues/10863))
* [PR 11664](https://github.com/spyder-ide/spyder/pull/11664) - PR: Remove highlight on key release event, by [@goanpeca](https://github.com/goanpeca)
* [PR 11661](https://github.com/spyder-ide/spyder/pull/11661) - PR: Use register_shortcut for a successful remap of cell shortcuts, by [@steff456](https://github.com/steff456) ([11630](https://github.com/spyder-ide/spyder/issues/11630))
* [PR 11656](https://github.com/spyder-ide/spyder/pull/11656) - PR: Fix test_conda_env_activation, by [@goanpeca](https://github.com/goanpeca)
* [PR 11650](https://github.com/spyder-ide/spyder/pull/11650) - PR: Prevent Tab/Backtab from triggering completions, by [@andfoy](https://github.com/andfoy) ([11625](https://github.com/spyder-ide/spyder/issues/11625))
* [PR 11647](https://github.com/spyder-ide/spyder/pull/11647) - PR: Fix KeyError on autosave, by [@jitseniesen](https://github.com/jitseniesen) ([11468](https://github.com/spyder-ide/spyder/issues/11468))
* [PR 11628](https://github.com/spyder-ide/spyder/pull/11628) - PR: Handle loading data from NpzFile instances and add an override flag to the load, by [@dalthviz](https://github.com/dalthviz) ([11596](https://github.com/spyder-ide/spyder/issues/11596))
* [PR 11627](https://github.com/spyder-ide/spyder/pull/11627) - PR: Validation for tab indexes when refreshing the Editor, by [@dalthviz](https://github.com/dalthviz) ([11464](https://github.com/spyder-ide/spyder/issues/11464))
* [PR 11626](https://github.com/spyder-ide/spyder/pull/11626) - PR: Skip some tests that are failing or timing out too much, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11619](https://github.com/spyder-ide/spyder/pull/11619) - PR: Convert autosave mapping to ASCII before saving, by [@jitseniesen](https://github.com/jitseniesen) ([11609](https://github.com/spyder-ide/spyder/issues/11609))
* [PR 11608](https://github.com/spyder-ide/spyder/pull/11608) - PR: Handle corrupted pid files in autosave component, by [@jitseniesen](https://github.com/jitseniesen) ([11375](https://github.com/spyder-ide/spyder/issues/11375))
* [PR 11602](https://github.com/spyder-ide/spyder/pull/11602) - PR: Add handling for faulty Kite installations, by [@dalthviz](https://github.com/dalthviz) ([11597](https://github.com/spyder-ide/spyder/issues/11597))
* [PR 11593](https://github.com/spyder-ide/spyder/pull/11593) - PR: Ensure Help pane actions are enabled after being undocked, by [@dalthviz](https://github.com/dalthviz) ([11591](https://github.com/spyder-ide/spyder/issues/11591))
* [PR 11592](https://github.com/spyder-ide/spyder/pull/11592) - PR: Handle TextEdit correctly when receiving completions, by [@andfoy](https://github.com/andfoy) ([11526](https://github.com/spyder-ide/spyder/issues/11526))
* [PR 11590](https://github.com/spyder-ide/spyder/pull/11590) - PR: Fix running tests locally from file, by [@jnsebgosselin](https://github.com/jnsebgosselin)
* [PR 11587](https://github.com/spyder-ide/spyder/pull/11587) - PR: Fix TypeError in `spyder --defaults`, by [@steff456](https://github.com/steff456) ([11586](https://github.com/spyder-ide/spyder/issues/11586))
* [PR 11585](https://github.com/spyder-ide/spyder/pull/11585) - PR: Set OpenGL backend before the QApplication is created, by [@ccordoba12](https://github.com/ccordoba12) ([11227](https://github.com/spyder-ide/spyder/issues/11227))
* [PR 11576](https://github.com/spyder-ide/spyder/pull/11576) - PR: UX and UI Improvements to the Plots pane, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([9367](https://github.com/spyder-ide/spyder/issues/9367))
* [PR 11574](https://github.com/spyder-ide/spyder/pull/11574) - PR: Add handling for PicklingError when getting values from the kernel, by [@dalthviz](https://github.com/dalthviz) ([11489](https://github.com/spyder-ide/spyder/issues/11489))
* [PR 11567](https://github.com/spyder-ide/spyder/pull/11567) - PR: Reset source model from parent after setting data (Variable explorer), by [@dalthviz](https://github.com/dalthviz) ([11455](https://github.com/spyder-ide/spyder/issues/11455), [11001](https://github.com/spyder-ide/spyder/issues/11001))
* [PR 11555](https://github.com/spyder-ide/spyder/pull/11555) - PR: Change variable explorer title for NumPy object arrays, by [@steff456](https://github.com/steff456) ([11331](https://github.com/spyder-ide/spyder/issues/11331))
* [PR 11554](https://github.com/spyder-ide/spyder/pull/11554) - PR: Fix focus to the editor given the focus_to_editor option, by [@steff456](https://github.com/steff456) ([11503](https://github.com/spyder-ide/spyder/issues/11503))
* [PR 11549](https://github.com/spyder-ide/spyder/pull/11549) - PR: Remove usage of load_exception in KernelComm and fix importing spyder-kernels subrepo, by [@impact27](https://github.com/impact27) ([11471](https://github.com/spyder-ide/spyder/issues/11471))
* [PR 11548](https://github.com/spyder-ide/spyder/pull/11548) - PR: Only run git tests when in a git repo, by [@bnavigator](https://github.com/bnavigator)
* [PR 11547](https://github.com/spyder-ide/spyder/pull/11547) - PR: Fix hanging test when not in git repository, by [@bnavigator](https://github.com/bnavigator) ([11546](https://github.com/spyder-ide/spyder/issues/11546))
* [PR 11545](https://github.com/spyder-ide/spyder/pull/11545) - PR: Show hidden files in explorer and project explorer, by [@goanpeca](https://github.com/goanpeca) ([10883](https://github.com/spyder-ide/spyder/issues/10883))
* [PR 11544](https://github.com/spyder-ide/spyder/pull/11544) - PR: Add debug calls for 3rd party plugin loading, by [@goanpeca](https://github.com/goanpeca)
* [PR 11541](https://github.com/spyder-ide/spyder/pull/11541) - PR: Fix restarting Spyder when it was started using bootstrap.py, by [@ccordoba12](https://github.com/ccordoba12) ([11539](https://github.com/spyder-ide/spyder/issues/11539))
* [PR 11540](https://github.com/spyder-ide/spyder/pull/11540) - PR: Update Chinese translation text to use the correct % character, by [@dalthviz](https://github.com/dalthviz) ([11514](https://github.com/spyder-ide/spyder/issues/11514))
* [PR 11533](https://github.com/spyder-ide/spyder/pull/11533) - PR: Add console_namespace positional arg (set to False) when calling Run in an Explorer widget, by [@dalthviz](https://github.com/dalthviz) ([11532](https://github.com/spyder-ide/spyder/issues/11532))
* [PR 11531](https://github.com/spyder-ide/spyder/pull/11531) - PR: Prevent fallback to output completions when the prefix is invalid, by [@andfoy](https://github.com/andfoy) ([11493](https://github.com/spyder-ide/spyder/issues/11493))
* [PR 11530](https://github.com/spyder-ide/spyder/pull/11530) - PR: Prevent editor stealing focus of other widgets while scrolling, by [@dalthviz](https://github.com/dalthviz) ([11502](https://github.com/spyder-ide/spyder/issues/11502))
* [PR 11517](https://github.com/spyder-ide/spyder/pull/11517) - PR: Update psutil dependency constraint and add checks for dependency integrity, by [@goanpeca](https://github.com/goanpeca) ([11497](https://github.com/spyder-ide/spyder/issues/11497))
* [PR 11505](https://github.com/spyder-ide/spyder/pull/11505) - PR: Handle file renamed in the explorer correctly in the editor, by [@jitseniesen](https://github.com/jitseniesen) ([11348](https://github.com/spyder-ide/spyder/issues/11348))
* [PR 11498](https://github.com/spyder-ide/spyder/pull/11498) - PR: Add Polish translation, by [@wojnilowicz](https://github.com/wojnilowicz)
* [PR 11488](https://github.com/spyder-ide/spyder/pull/11488) - PR: Optimise keyPressEvent in the editor, by [@impact27](https://github.com/impact27) ([11495](https://github.com/spyder-ide/spyder/issues/11495), [11412](https://github.com/spyder-ide/spyder/issues/11412))
* [PR 11479](https://github.com/spyder-ide/spyder/pull/11479) - PR: Fix errors when restarting the kernel while in debugging, by [@impact27](https://github.com/impact27) ([11477](https://github.com/spyder-ide/spyder/issues/11477))
* [PR 11478](https://github.com/spyder-ide/spyder/pull/11478) - PR: Improve formatting of Contributing guide, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11476](https://github.com/spyder-ide/spyder/pull/11476) - PR: Pin parso to 0.5.2 because version 0.6.0 is incompatible with Jedi 0.14, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11473](https://github.com/spyder-ide/spyder/pull/11473) - PR: Monkeypatch watchdog's main dispatcher to prevent network failures, by [@andfoy](https://github.com/andfoy) ([11370](https://github.com/spyder-ide/spyder/issues/11370))
* [PR 11472](https://github.com/spyder-ide/spyder/pull/11472) - PR: Avoid Python destroying Qt window and causing segfault, by [@impact27](https://github.com/impact27) ([10704](https://github.com/spyder-ide/spyder/issues/10704))
* [PR 11465](https://github.com/spyder-ide/spyder/pull/11465) - PR: Prevent operation not permitted errors when writing to samba shares, by [@andfoy](https://github.com/andfoy) ([11308](https://github.com/spyder-ide/spyder/issues/11308))
* [PR 11462](https://github.com/spyder-ide/spyder/pull/11462) - PR: Add debug logger calls for dragEnterEvent in the Editor, by [@dalthviz](https://github.com/dalthviz)
* [PR 11460](https://github.com/spyder-ide/spyder/pull/11460) - PR: Add automatic introduction of docstrings in Sphinx format, by [@ok97465](https://github.com/ok97465) ([11435](https://github.com/spyder-ide/spyder/issues/11435))
* [PR 11449](https://github.com/spyder-ide/spyder/pull/11449) - PR: Encode url parameters before sending requests to Kite, by [@dalthviz](https://github.com/dalthviz) ([11351](https://github.com/spyder-ide/spyder/issues/11351))
* [PR 11443](https://github.com/spyder-ide/spyder/pull/11443) - PR: Preserve creation time when performing an atomic_write, by [@andfoy](https://github.com/andfoy) ([11403](https://github.com/spyder-ide/spyder/issues/11403))
* [PR 11441](https://github.com/spyder-ide/spyder/pull/11441) - PR: Properly register shortcuts for some actions of the Variable Explorer, by [@dalthviz](https://github.com/dalthviz) ([10627](https://github.com/spyder-ide/spyder/issues/10627))
* [PR 11437](https://github.com/spyder-ide/spyder/pull/11437) - PR: Display the latest result of requested completions, by [@ok97465](https://github.com/ok97465) ([10798](https://github.com/spyder-ide/spyder/issues/10798))
* [PR 11422](https://github.com/spyder-ide/spyder/pull/11422) - PR: Enable signature request without automatic bracket completion, by [@dalthviz](https://github.com/dalthviz) ([11417](https://github.com/spyder-ide/spyder/issues/11417))
* [PR 11416](https://github.com/spyder-ide/spyder/pull/11416) - PR: Interpret -p project argument relative to the directory of invocation, by [@akdor1154](https://github.com/akdor1154) ([11363](https://github.com/spyder-ide/spyder/issues/11363))
* [PR 11415](https://github.com/spyder-ide/spyder/pull/11415) - PR: Fix some spelling errors, by [@hjung4](https://github.com/hjung4)
* [PR 11400](https://github.com/spyder-ide/spyder/pull/11400) - PR: Prevent underscore prefixed snippets to be omitted, by [@andfoy](https://github.com/andfoy) ([11399](https://github.com/spyder-ide/spyder/issues/11399), [11237](https://github.com/spyder-ide/spyder/issues/11237))
* [PR 11395](https://github.com/spyder-ide/spyder/pull/11395) - PR: Handle screen change to trigger restart and prevent display issues, by [@dalthviz](https://github.com/dalthviz)
* [PR 11393](https://github.com/spyder-ide/spyder/pull/11393) - PR: Use normpath to set network folders as cwd on Windows, by [@dalthviz](https://github.com/dalthviz) ([10785](https://github.com/spyder-ide/spyder/issues/10785))
* [PR 11389](https://github.com/spyder-ide/spyder/pull/11389) - PR: Add support for third party plugins to react to color scheme changes, by [@steff456](https://github.com/steff456) ([10911](https://github.com/spyder-ide/spyder/issues/10911))
* [PR 11378](https://github.com/spyder-ide/spyder/pull/11378) - PR: Fix infinite loop with issue shorthand within comments, by [@goanpeca](https://github.com/goanpeca) ([11376](https://github.com/spyder-ide/spyder/issues/11376))
* [PR 11377](https://github.com/spyder-ide/spyder/pull/11377) - PR: Add check to prevent hover with no docs, by [@goanpeca](https://github.com/goanpeca) ([11346](https://github.com/spyder-ide/spyder/issues/11346))
* [PR 11364](https://github.com/spyder-ide/spyder/pull/11364) - PR: Include plugins in dependencies dialog, by [@goanpeca](https://github.com/goanpeca) ([11318](https://github.com/spyder-ide/spyder/issues/11318))
* [PR 11361](https://github.com/spyder-ide/spyder/pull/11361) - PR: Fix tooltip position after the editor is undocked, by [@dalthviz](https://github.com/dalthviz) ([11355](https://github.com/spyder-ide/spyder/issues/11355))
* [PR 11359](https://github.com/spyder-ide/spyder/pull/11359) - PR: Make scale restart optional, by [@dalthviz](https://github.com/dalthviz) ([11358](https://github.com/spyder-ide/spyder/issues/11358))
* [PR 11350](https://github.com/spyder-ide/spyder/pull/11350) - PR: Add a git subrepo for spyder-kernels, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 11334](https://github.com/spyder-ide/spyder/pull/11334) - PR: Fix several indentation cases, by [@impact27](https://github.com/impact27) ([11128](https://github.com/spyder-ide/spyder/issues/11128))
* [PR 11332](https://github.com/spyder-ide/spyder/pull/11332) - PR: Get current word to inspect current object from the IPython console, by [@dalthviz](https://github.com/dalthviz) ([7699](https://github.com/spyder-ide/spyder/issues/7699))
* [PR 11329](https://github.com/spyder-ide/spyder/pull/11329) - PR: Remove "The send queue is full! Retrying..." when LSP is not initialised, by [@impact27](https://github.com/impact27)
* [PR 11328](https://github.com/spyder-ide/spyder/pull/11328) - PR: Add escape key to completion ignore keys, by [@goanpeca](https://github.com/goanpeca) ([11082](https://github.com/spyder-ide/spyder/issues/11082))
* [PR 11327](https://github.com/spyder-ide/spyder/pull/11327) - PR: Activate conda environment prior to kernel start, by [@goanpeca](https://github.com/goanpeca) ([9077](https://github.com/spyder-ide/spyder/issues/9077), [89](https://github.com/spyder-ide/spyder-kernels/issues/89))
* [PR 11322](https://github.com/spyder-ide/spyder/pull/11322) - PR: Add a restart message when a monitor scale change is detected, by [@dalthviz](https://github.com/dalthviz) ([6181](https://github.com/spyder-ide/spyder/issues/6181))
* [PR 11321](https://github.com/spyder-ide/spyder/pull/11321) - PR: Don't close autocompletion menu when AltGr is pressed, by [@MaxGyver83](https://github.com/MaxGyver83) ([11293](https://github.com/spyder-ide/spyder/issues/11293))
* [PR 11317](https://github.com/spyder-ide/spyder/pull/11317) - PR: Finalise kernel shutdown in a thread, by [@impact27](https://github.com/impact27) ([197](https://github.com/spyder-ide/spyder-kernels/issues/197))
* [PR 11310](https://github.com/spyder-ide/spyder/pull/11310) - PR: Catch KeyError when trying to highlight folding region, by [@ccordoba12](https://github.com/ccordoba12) ([11291](https://github.com/spyder-ide/spyder/issues/11291))
* [PR 11287](https://github.com/spyder-ide/spyder/pull/11287) - PR: Fix snippets completion with a single token in placeholder, by [@dalthviz](https://github.com/dalthviz) ([10971](https://github.com/spyder-ide/spyder/issues/10971))
* [PR 11272](https://github.com/spyder-ide/spyder/pull/11272) - PR: Improvements to the Help pane (style, loading page and some other issues), by [@dalthviz](https://github.com/dalthviz) ([11267](https://github.com/spyder-ide/spyder/issues/11267))
* [PR 11271](https://github.com/spyder-ide/spyder/pull/11271) - PR: Hide tooltip when the window is blocked, by [@dalthviz](https://github.com/dalthviz) ([11244](https://github.com/spyder-ide/spyder/issues/11244))
* [PR 11270](https://github.com/spyder-ide/spyder/pull/11270) - PR: Add css to style parameters in the Help pane when using Sphinx >=2, by [@dalthviz](https://github.com/dalthviz) ([9888](https://github.com/spyder-ide/spyder/issues/9888))
* [PR 11259](https://github.com/spyder-ide/spyder/pull/11259) - PR: Do not show replace widget when it is not enabled, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([11258](https://github.com/spyder-ide/spyder/issues/11258))
* [PR 11256](https://github.com/spyder-ide/spyder/pull/11256) - PR: Change unmatched brackets in line validation, by [@dalthviz](https://github.com/dalthviz) ([11217](https://github.com/spyder-ide/spyder/issues/11217))
* [PR 11254](https://github.com/spyder-ide/spyder/pull/11254) - PR: Validate custom scale factor not being below 1.0, by [@dalthviz](https://github.com/dalthviz) ([11240](https://github.com/spyder-ide/spyder/issues/11240))
* [PR 11248](https://github.com/spyder-ide/spyder/pull/11248) - PR: Cache call to get_icon_by_extension_or_type, by [@impact27](https://github.com/impact27) ([11247](https://github.com/spyder-ide/spyder/issues/11247))
* [PR 11241](https://github.com/spyder-ide/spyder/pull/11241) - PR: Handle error when disconnecting object info signal after idle, by [@dalthviz](https://github.com/dalthviz) ([11228](https://github.com/spyder-ide/spyder/issues/11228))
* [PR 11239](https://github.com/spyder-ide/spyder/pull/11239) - PR: Handle AttributeError when generating context menu on dockwidget tabs, by [@dalthviz](https://github.com/dalthviz) ([11226](https://github.com/spyder-ide/spyder/issues/11226))
* [PR 11238](https://github.com/spyder-ide/spyder/pull/11238) - PR: Handle AttributeError when creating an ArrayEditor, by [@dalthviz](https://github.com/dalthviz) ([11216](https://github.com/spyder-ide/spyder/issues/11216))
* [PR 11223](https://github.com/spyder-ide/spyder/pull/11223) - PR: Fix freeze when LSP client queue is full, by [@impact27](https://github.com/impact27) ([11222](https://github.com/spyder-ide/spyder/issues/11222))
* [PR 11219](https://github.com/spyder-ide/spyder/pull/11219) - PR: Handle encoding when restarting Spyder to fix an error with Python 2.7, by [@dalthviz](https://github.com/dalthviz) ([11024](https://github.com/spyder-ide/spyder/issues/11024))
* [PR 11212](https://github.com/spyder-ide/spyder/pull/11212) - PR: Fix infinite loop when commenting first block, by [@impact27](https://github.com/impact27) ([11148](https://github.com/spyder-ide/spyder/issues/11148))
* [PR 11210](https://github.com/spyder-ide/spyder/pull/11210) - PR: Use Pandas tolist to get formatted indexes and headers in the DataFrame editor, by [@dalthviz](https://github.com/dalthviz) ([11129](https://github.com/spyder-ide/spyder/issues/11129))
* [PR 11192](https://github.com/spyder-ide/spyder/pull/11192) - PR: Send comm config again if comm times out, by [@impact27](https://github.com/impact27) ([11406](https://github.com/spyder-ide/spyder/issues/11406), [11137](https://github.com/spyder-ide/spyder/issues/11137))
* [PR 11122](https://github.com/spyder-ide/spyder/pull/11122) - PR: Rename copy line and duplicate line shortcuts, by [@jnsebgosselin](https://github.com/jnsebgosselin) ([11092](https://github.com/spyder-ide/spyder/issues/11092))
* [PR 11103](https://github.com/spyder-ide/spyder/pull/11103) - PR: Add IPython magic runcell test, by [@impact27](https://github.com/impact27) ([11061](https://github.com/spyder-ide/spyder/issues/11061))
* [PR 10976](https://github.com/spyder-ide/spyder/pull/10976) - PR: Implement dynamic variable explorer window size, by [@jsh9](https://github.com/jsh9) ([10745](https://github.com/spyder-ide/spyder/issues/10745))
* [PR 10801](https://github.com/spyder-ide/spyder/pull/10801) - PR: Make adjustable the maximum number of recent projects, by [@juanis2112](https://github.com/juanis2112) ([10640](https://github.com/spyder-ide/spyder/issues/10640))
* [PR 10610](https://github.com/spyder-ide/spyder/pull/10610) - PR: Update debugging panel with current console pdb state, by [@dalthviz](https://github.com/dalthviz) ([10538](https://github.com/spyder-ide/spyder/issues/10538))
* [PR 9554](https://github.com/spyder-ide/spyder/pull/9554) - PR: Remove stylesheet workarounds for the options and browse button when under the dark theme, by [@jnsebgosselin](https://github.com/jnsebgosselin)

In this release 115 pull requests were closed.


----


## Version 4.0.1 (2020-01-02)

### Important fixes

* Remove password-based authentication to report errors on Github.
* Several performance improvements in the Editor.

### Issues Closed

* [Issue 11191](https://github.com/spyder-ide/spyder/issues/11191) - Travis fails with IPython 7.11 ([PR 11194](https://github.com/spyder-ide/spyder/pull/11194))
* [Issue 11140](https://github.com/spyder-ide/spyder/issues/11140) - Simple typo: witdh -> width ([PR 11141](https://github.com/spyder-ide/spyder/pull/11141))
* [Issue 11132](https://github.com/spyder-ide/spyder/issues/11132) - Duplicate keyboard shortcuts, restoring them to default crashes  ([PR 11197](https://github.com/spyder-ide/spyder/pull/11197))
* [Issue 11096](https://github.com/spyder-ide/spyder/issues/11096) - "Select All" in Variable Explorer for DataFrames ([PR 11100](https://github.com/spyder-ide/spyder/pull/11100))
* [Issue 11076](https://github.com/spyder-ide/spyder/issues/11076) - Kite pop-up doesn't show up if Editor pane undocked ([PR 11114](https://github.com/spyder-ide/spyder/pull/11114))
* [Issue 11074](https://github.com/spyder-ide/spyder/issues/11074) - AttributeError: 'QTextBlock' object has no attribute '_selection' ([PR 11075](https://github.com/spyder-ide/spyder/pull/11075))
* [Issue 11070](https://github.com/spyder-ide/spyder/issues/11070) - Copying or duplicating multiple selected lines deselects last line each time ([PR 11089](https://github.com/spyder-ide/spyder/pull/11089))
* [Issue 11060](https://github.com/spyder-ide/spyder/issues/11060) - Variable explorer slow to open in spyder 4 with large dataframes ([PR 11102](https://github.com/spyder-ide/spyder/pull/11102))
* [Issue 11059](https://github.com/spyder-ide/spyder/issues/11059) - Github warning when using Issue reporter ([PR 11209](https://github.com/spyder-ide/spyder/pull/11209))
* [Issue 11058](https://github.com/spyder-ide/spyder/issues/11058) - Exceptions when I cancelled saving an unsaved file ([PR 11077](https://github.com/spyder-ide/spyder/pull/11077))
* [Issue 11050](https://github.com/spyder-ide/spyder/issues/11050) - Feature request: add a minimum height for the slider range of the scrollflag panel ([PR 11057](https://github.com/spyder-ide/spyder/pull/11057))
* [Issue 11047](https://github.com/spyder-ide/spyder/issues/11047) - Error when getting completions with Jedi 0.15 ([PR 11087](https://github.com/spyder-ide/spyder/pull/11087))
* [Issue 11007](https://github.com/spyder-ide/spyder/issues/11007) - Status bar displays incorrect interpreter on Windows ([PR 11008](https://github.com/spyder-ide/spyder/pull/11008))
* [Issue 11006](https://github.com/spyder-ide/spyder/issues/11006) - Status bar does not update current interpreter ([PR 11008](https://github.com/spyder-ide/spyder/pull/11008))
* [Issue 11000](https://github.com/spyder-ide/spyder/issues/11000) - Spyder very slow when working on large python files ([PR 11011](https://github.com/spyder-ide/spyder/pull/11011))
* [Issue 10992](https://github.com/spyder-ide/spyder/issues/10992) - Spyder 4.0.0 unbearably slow when adding or removing lines ([PR 11010](https://github.com/spyder-ide/spyder/pull/11010))
* [Issue 10955](https://github.com/spyder-ide/spyder/issues/10955) - The object modified is too big to be sent back to the kernel ([PR 10987](https://github.com/spyder-ide/spyder/pull/10987))
* [Issue 10918](https://github.com/spyder-ide/spyder/issues/10918) - KeyError when drawing folding regions ([PR 11088](https://github.com/spyder-ide/spyder/pull/11088))
* [Issue 10912](https://github.com/spyder-ide/spyder/issues/10912) - When plotting new plot, plot pane does automatically scroll down to newest plot. ([PR 10914](https://github.com/spyder-ide/spyder/pull/10914))
* [Issue 10897](https://github.com/spyder-ide/spyder/issues/10897) - Blank line printed on console for each chart plotted ([PR 10909](https://github.com/spyder-ide/spyder/pull/10909))
* [Issue 10893](https://github.com/spyder-ide/spyder/issues/10893) - Spyder closes unexpectedly when trying to change plain text font ([PR 11172](https://github.com/spyder-ide/spyder/pull/11172))
* [Issue 10844](https://github.com/spyder-ide/spyder/issues/10844) - Can't open file with non unicode name by drag and drop ([PR 10846](https://github.com/spyder-ide/spyder/pull/10846))
* [Issue 10835](https://github.com/spyder-ide/spyder/issues/10835) - Hover tips interfere with editor text selection ([PR 10855](https://github.com/spyder-ide/spyder/pull/10855))
* [Issue 10786](https://github.com/spyder-ide/spyder/issues/10786) - Alt+Space shortcut cannot be set in Spyder 4 ([PR 10836](https://github.com/spyder-ide/spyder/pull/10836))
* [Issue 10221](https://github.com/spyder-ide/spyder/issues/10221) - Spyder stalls for 2 minutes on startup when starting a remote Xorg session ([PR 10837](https://github.com/spyder-ide/spyder/pull/10837))
* [Issue 8093](https://github.com/spyder-ide/spyder/issues/8093) - Variable Explorer crashes when viewing Numpy matrix with inf ([PR 10856](https://github.com/spyder-ide/spyder/pull/10856))
* [Issue 7998](https://github.com/spyder-ide/spyder/issues/7998) - "Show blank spaces" refuses to work on files without officially "supported" extensions ([PR 10887](https://github.com/spyder-ide/spyder/pull/10887))
* [Issue 7848](https://github.com/spyder-ide/spyder/issues/7848) - Variable editor problems on clicking ([PR 10866](https://github.com/spyder-ide/spyder/pull/10866))
* [Issue 7362](https://github.com/spyder-ide/spyder/issues/7362) - Cannot type further letters or symbols after : in symbol finder dialog ([PR 10865](https://github.com/spyder-ide/spyder/pull/10865))
* [Issue 6992](https://github.com/spyder-ide/spyder/issues/6992) - Default Help "Usage" screen always shows hardcoded default inspect shortcut, not actual one ([PR 10869](https://github.com/spyder-ide/spyder/pull/10869))
* [Issue 4833](https://github.com/spyder-ide/spyder/issues/4833) - Error when copying text from a Dataframe on Python 2 ([PR 11104](https://github.com/spyder-ide/spyder/pull/11104))
* [Issue 2675](https://github.com/spyder-ide/spyder/issues/2675) - Multiline search and replace doesn't replace ([PR 10872](https://github.com/spyder-ide/spyder/pull/10872))

In this release 32 issues were closed.

### Pull Requests Merged

* [PR 11209](https://github.com/spyder-ide/spyder/pull/11209) - PR: Remove password-based authentication from the Github login dialog ([11059](https://github.com/spyder-ide/spyder/issues/11059))
* [PR 11197](https://github.com/spyder-ide/spyder/pull/11197) - PR: Fix creation of config files for external plugins ([11132](https://github.com/spyder-ide/spyder/issues/11132))
* [PR 11194](https://github.com/spyder-ide/spyder/pull/11194) - PR: Skip some failing tests for the IPython console ([11191](https://github.com/spyder-ide/spyder/issues/11191))
* [PR 11184](https://github.com/spyder-ide/spyder/pull/11184) - PR: Fix shortcut reset error and add test
* [PR 11172](https://github.com/spyder-ide/spyder/pull/11172) - PR: Fix completions for the internal console and prevent hard crash ([10893](https://github.com/spyder-ide/spyder/issues/10893))
* [PR 11159](https://github.com/spyder-ide/spyder/pull/11159) - PR: Don't register keyring as a dependency on Linux and Python 2
* [PR 11141](https://github.com/spyder-ide/spyder/pull/11141) - PR: Fix simple typo in docstring ([11140](https://github.com/spyder-ide/spyder/issues/11140))
* [PR 11114](https://github.com/spyder-ide/spyder/pull/11114) - PR: Handle CompletionWidget position when undocking editor ([11076](https://github.com/spyder-ide/spyder/issues/11076))
* [PR 11104](https://github.com/spyder-ide/spyder/pull/11104) - PR: Handle encoding error when copying dataframes in Python 2 ([4833](https://github.com/spyder-ide/spyder/issues/4833))
* [PR 11102](https://github.com/spyder-ide/spyder/pull/11102) - PR: Set time limit to calculate columns size hint for Dataframe Editor ([11060](https://github.com/spyder-ide/spyder/issues/11060))
* [PR 11100](https://github.com/spyder-ide/spyder/pull/11100) - PR: Copy index and headers of dataframe ([11096](https://github.com/spyder-ide/spyder/issues/11096))
* [PR 11091](https://github.com/spyder-ide/spyder/pull/11091) - PR: Workaround to avoid a glitch when duplicating current line or text selection
* [PR 11089](https://github.com/spyder-ide/spyder/pull/11089) - PR: Fix copying or duplicating multiple selected lines ([11070](https://github.com/spyder-ide/spyder/issues/11070))
* [PR 11088](https://github.com/spyder-ide/spyder/pull/11088) - PR: Catch KeyError when trying to draw a folding region ([10918](https://github.com/spyder-ide/spyder/issues/10918))
* [PR 11087](https://github.com/spyder-ide/spyder/pull/11087) - PR: Add Jedi as a new dependency for users to be aware of its right version ([11047](https://github.com/spyder-ide/spyder/issues/11047))
* [PR 11077](https://github.com/spyder-ide/spyder/pull/11077) - PR: Keep finfo.newly_created state when cancelling save_as ([11058](https://github.com/spyder-ide/spyder/issues/11058))
* [PR 11075](https://github.com/spyder-ide/spyder/pull/11075) - PR: Call data instead of block to fix AttributeError in the editor ([11074](https://github.com/spyder-ide/spyder/issues/11074))
* [PR 11057](https://github.com/spyder-ide/spyder/pull/11057) - PR: Set a minimum value for the scrollflag's slider height ([11050](https://github.com/spyder-ide/spyder/issues/11050))
* [PR 11036](https://github.com/spyder-ide/spyder/pull/11036) - PR: Improve efficiency of __mark_occurences method
* [PR 11011](https://github.com/spyder-ide/spyder/pull/11011) - PR: Optimize editor scrollflag panel painting ([11000](https://github.com/spyder-ide/spyder/issues/11000))
* [PR 11010](https://github.com/spyder-ide/spyder/pull/11010) - PR: Change update_all to update_current on editor changes ([10992](https://github.com/spyder-ide/spyder/issues/10992))
* [PR 11008](https://github.com/spyder-ide/spyder/pull/11008) - PR: Correctly update Python interpreter on status bar when modified for Windows ([11007](https://github.com/spyder-ide/spyder/issues/11007), [11007](https://github.com/spyder-ide/spyder/issues/11007), [11006](https://github.com/spyder-ide/spyder/issues/11006), [11006](https://github.com/spyder-ide/spyder/issues/11006))
* [PR 11002](https://github.com/spyder-ide/spyder/pull/11002) - PR: Skip test_go_to_definition completely on macOS
* [PR 10987](https://github.com/spyder-ide/spyder/pull/10987) - PR: Remove serialized length limit when sending modified variables back to the kernel ([10955](https://github.com/spyder-ide/spyder/issues/10955))
* [PR 10967](https://github.com/spyder-ide/spyder/pull/10967) - PR: Create sections for project and build status in README.md
* [PR 10956](https://github.com/spyder-ide/spyder/pull/10956) - PR: Fix simple error in a test widget
* [PR 10954](https://github.com/spyder-ide/spyder/pull/10954) - PR: Add crowdin config
* [PR 10953](https://github.com/spyder-ide/spyder/pull/10953) - PR: Update readme to use the correct branch for binder
* [PR 10950](https://github.com/spyder-ide/spyder/pull/10950) - PR: Add link to try out current Spyder on mybinder.org
* [PR 10948](https://github.com/spyder-ide/spyder/pull/10948) - PR: Correctly show several missing deps in our dialog
* [PR 10914](https://github.com/spyder-ide/spyder/pull/10914) - PR: Automatically scroll down to newest plot in Plots pane ([10912](https://github.com/spyder-ide/spyder/issues/10912))
* [PR 10909](https://github.com/spyder-ide/spyder/pull/10909) - PR: Fix extra blank line added to qtconsole when plotting ([10897](https://github.com/spyder-ide/spyder/issues/10897))
* [PR 10887](https://github.com/spyder-ide/spyder/pull/10887) - PR: Fix showing spaces for generic files ([7998](https://github.com/spyder-ide/spyder/issues/7998))
* [PR 10872](https://github.com/spyder-ide/spyder/pull/10872) - PR: Fix find/replace widget for multiline regex ([2675](https://github.com/spyder-ide/spyder/issues/2675))
* [PR 10869](https://github.com/spyder-ide/spyder/pull/10869) - PR: Fix help intro message with correct shortcut and update if shortcut changes ([6992](https://github.com/spyder-ide/spyder/issues/6992))
* [PR 10866](https://github.com/spyder-ide/spyder/pull/10866) - PR: Fix updates with complex values on variable explorer ([7848](https://github.com/spyder-ide/spyder/issues/7848))
* [PR 10865](https://github.com/spyder-ide/spyder/pull/10865) - PR: Handle non-ascii text in the switcher ([7362](https://github.com/spyder-ide/spyder/issues/7362))
* [PR 10856](https://github.com/spyder-ide/spyder/pull/10856) - PR: Check if arrays have inf values and add test ([8093](https://github.com/spyder-ide/spyder/issues/8093))
* [PR 10855](https://github.com/spyder-ide/spyder/pull/10855) - PR: Hide tooltip widget with mouse click and keypress ([10835](https://github.com/spyder-ide/spyder/issues/10835))
* [PR 10846](https://github.com/spyder-ide/spyder/pull/10846) - PR: Unquote url properly for drag and drop ([10844](https://github.com/spyder-ide/spyder/issues/10844))
* [PR 10837](https://github.com/spyder-ide/spyder/pull/10837) - PR: Do not import keyring when running through SSH ([10221](https://github.com/spyder-ide/spyder/issues/10221))
* [PR 10836](https://github.com/spyder-ide/spyder/pull/10836) - PR: Fix the shortcut override in the ShortcutEditor. ([10786](https://github.com/spyder-ide/spyder/issues/10786))
* [PR 10804](https://github.com/spyder-ide/spyder/pull/10804) - PR: Implement a faster paint event for cells

In this release 43 pull requests were closed.


----


## Version 4.0.0 (2019-12-06)

### New features

#### Main Window

* Add a dark theme for the entire interface.
* Add a new `Plots` pane to browse all inline figures generated by the IPython console.
* Several plugins were renamed to have a simpler interface:
  - `Static code analysis` to `Code Analysis`
  - `File explorer` to `Files`
  - `Find in files` to `Find`
  - `History log` to `History`
  - `Project explorer` to `Project`
* Add a new action called `Undock` to the Options menu of every plugin. This action
  creates a separate window that only contains the plugin and can be moved to a
  different place of the screen or to a different monitor.
* Add a clock to the status bar, for those who like to work in full screen mode. It can
  be activated in
  `Preferences > General > Advanced settings > Status bar > Show clock`.
* Show current conda environment and git branch (if any) in the status bar.
* Add translation for Simplified Chinese.

#### Editor

* Add code folding functionality.
* Show code completions as you type.
* Add autosave functionality to be able to recover unsaved files after a crash.
* Add indentation guides. They can be activated under the `Source` menu.
* Add a panel to show the current class and method/function where the cursor is placed,
  inspired by similar functionality present in Microsoft Visual Studio. It can activated
  under the menu `Source > Show selector for classes and functions`.
* Allow setting multiple line length indicators under
  `Preferences > Editor > Display > Show vertical lines`.
* Add `Ctrl+Alt+Shift+,` and `Ctrl+Alt+Shift+.` shortcuts to go to the previous/next
  warning and error, respectively.
* Allow scrolling past the end of the file. This can activated in
  `Preferences > Editor > Display > Scroll past the end`.
* Add the ability to take into account code indentation and PEP 8 when adding and
  removing comments.
* Add an option to convert end-of-line characters on save.  This can activated in
  `Preferences > Editor > Advanced settings > End-of-line characters`
* Add `Ctrl+{` and `Ctrl+_` shortcuts to split panels vertically and horizontally,
  respectively.
* Add `Alt+Shift+W` shortcut to close the current split panel.
* After pressing a quote or brace the current selection gets enclosed on it.
* Add automatic docstring generation (parameters, return vals and exceptions raised) in
  Numpydoc and Googledoc formats.
* Add an option to its context menu to sort files alphabetically.
* Add the ability to reference issues on Gitlab (`gl`), Github (`gh`) and Bitbucket
  (`bb`) in comments or strings by using the convention `{gl/gh/bb}:my-org/my-repo#123`.
  You can also reference them by `{gl/gh/bb}-123`, if you've previously set up an
  `upstream` or `origin` remote in your repo.
* Use the Language Server Protocol for code completion and linting.

#### IPython console
* Files are now run in an empty namespace. This avoids picking up variables defined in
  the console while running a file. To get the previous behavior you need to go to the
  menu `Run > Configuration per file` and activate the option called
  `Run in console’s namespace instead of an empty one`.
* Add menu options to start consoles in Pylab, Sympy and Cython modes.
* Run cells through a function called `runcell` instead of pasting their contents
  directly to the console.
* Use Jupyter comms to handle communications between frontend and kernel.

#### Debugger

* Add code completion to it.
* Add the ability to execute multi-line statements on it.
* Add syntax highlighting to it and color `ipdb` prompts.
* Add permanent history to it, separate from the console history.
* `runfile` and `runcell` can now be called when the debugger is active.
* Add the ability to debug cells by pressing `Alt+Shift+Return` or by going to the menu
  `Debug > Debug cell`.
* Add an option to ignore installed Python libraries while debugging. It can be turned on
  in the menu `Debug > Ignore Python libraries while debugging`.
* Add the ability to see inline plots while debugging. For that you need to activate the
  option called `Process execute events while debugging`, present in in the `Debug` menu.
* Disambiguate file names in the Breakpoints pane.

#### Variable Explorer

* Add a new viewer to inspect any Python object in a tree-like way.
* Add the ability to search for variable names and types.
* Restore the ability to refresh it while code is being executed.
* Add support for Numpy object arrays.
* Add MultiIndex display support to the DataFrame viewer.
* Add support for all Pandas indexes.
* Add support for sets.
* Add a new option to exclude callables and modules.
* Add an option to its context menu (the one you get with a mouse right-click) to resize
  columns to its contents.

#### Files

* Add the possibility to associate different external applications to open specific file
  extensions (e.g. `.txt` files with Notepad++ or VSCode).
* Add a context menu action called `Open externally` to all files to open them with the
  operating system default program associated with the file type.
* Add multi-select functionality, i.e. using `Ctrl/Shift+click` to select multiple files.
* Add the ability to copy/paste files and their absolute or relative paths.
* Use special icons for different file types.
* Add an option to open files and directories with a single click.

#### Outline

* Show cells grouped in sections. Level 1 cells are defined by `#%%` (as before), level 2
  cells by `#%%%`, level 3 cells by `#%%%%` and so on. With this new syntax, all `n+1`
  cells will be conveniently grouped under n-level cells in the outline tree.
* Add an option to sort files alphabetically. By default files are shown in the same
  order as in the Editor.
* Add a default name for cells to encourage users to name them. This way cells can be
  more easily spotted in the outline tree.

#### Preferences:

* Spyder can now read default configuration options saved in `spyder.ini` files from
  system (e.g. `/etc/spyder`) and conda environment (e.g.
  `~/miniconda/envs/py36/etc/spyder`) directories. This can be used by sysadmins to turn
  on/off certain options by default for all users in an organization. To inspect the
  paths from which Spyder reads these files per operating system and the order in which
  it does that, you can use the new command line option `spyder --paths`.

#### API Changes

##### Major changes
* Create one module per plugin in `spyder.plugins` and move there all widgets and utility
  modules used by that plugin. For example, `spyder.widgets.sourcecode.codeeditor` is now
  at `spyder.plugins.editor.widgets.codeeditor`.
* Create the `spyder.api` module to expose a public API for external plugins. *Note*:
  This is still not stable. It'll be improved and stabilized for Spyder 5 (to be released
  in 2020).
* Add a `SpyderPlugin` class to be able to create plugins without an associated graphical
  pane.

##### Minor changes
* Remove the `SpyderPluginMixin` class. Its contents were added to `BasePluginMixin` and
  `BasePluginWidgetMixin` (in `plugins/base.py`).
* Move `SpyderDockWidget` to `widgets/dock.py`.
* Config pages of all plugins are now located in a separate module called
  `spyder/plugins/<plugin>/confpage.py`

#### Under the hood
* Drop support for Python 3.4.
* Increase minimal PyQt supported version to 5.6.
* Deprecate the usage of `debug_print` and use the `logging` module instead.

### Issues Closed

* [Issue 10917](https://github.com/spyder-ide/spyder/issues/10917) - No plotting available for some variables in Variable Explorer ([PR 10929](https://github.com/spyder-ide/spyder/pull/10929))
* [Issue 10900](https://github.com/spyder-ide/spyder/issues/10900) - Regression: Indent guides broken in any Editor split panel except the first ([PR 10910](https://github.com/spyder-ide/spyder/pull/10910))
* [Issue 10884](https://github.com/spyder-ide/spyder/issues/10884) - String "Run in console's namespace instead of an empty one" translated but still show English on UI ([PR 10886](https://github.com/spyder-ide/spyder/pull/10886))
* [Issue 10851](https://github.com/spyder-ide/spyder/issues/10851) - Pdb switch code editor tabs without reason ([PR 10850](https://github.com/spyder-ide/spyder/pull/10850))
* [Issue 10834](https://github.com/spyder-ide/spyder/issues/10834) - Keyboard events leak from console to editor while debugging ([PR 10847](https://github.com/spyder-ide/spyder/pull/10847))
* [Issue 10763](https://github.com/spyder-ide/spyder/issues/10763) - Fails to install Spyder4.0.0rc2 on Windows due to ujson dependency
* [Issue 10736](https://github.com/spyder-ide/spyder/issues/10736) - runfile changes the current tab in the editor ([PR 10839](https://github.com/spyder-ide/spyder/pull/10839))
* [Issue 10672](https://github.com/spyder-ide/spyder/issues/10672) - Update translations for 4.0.0 ([PR 10930](https://github.com/spyder-ide/spyder/pull/10930))

In this release 8 issues were closed.

### Pull Requests Merged

* [PR 10947](https://github.com/spyder-ide/spyder/pull/10947) - PR: Show PyLS errors only in debug or development modes
* [PR 10940](https://github.com/spyder-ide/spyder/pull/10940) - PR: Update versions of spyder-kernels and PyLS for the final release
* [PR 10935](https://github.com/spyder-ide/spyder/pull/10935) - PR: Some corrections to the French translation
* [PR 10930](https://github.com/spyder-ide/spyder/pull/10930) - PR: Disable Hungarian and Russian translations ([10810](https://github.com/spyder-ide/spyder/issues/10810), [10809](https://github.com/spyder-ide/spyder/issues/10809), [10672](https://github.com/spyder-ide/spyder/issues/10672))
* [PR 10929](https://github.com/spyder-ide/spyder/pull/10929) - PR: Use proxy_model when refreshing plot actions state ([10917](https://github.com/spyder-ide/spyder/issues/10917))
* [PR 10920](https://github.com/spyder-ide/spyder/pull/10920) - PR: Show autosave dialog on top of splash screen in macOS
* [PR 10910](https://github.com/spyder-ide/spyder/pull/10910) - PR: Show indent guides for splited editor panels ([10900](https://github.com/spyder-ide/spyder/issues/10900))
* [PR 10902](https://github.com/spyder-ide/spyder/pull/10902) - PR: Update Simplified Chinese translation
* [PR 10901](https://github.com/spyder-ide/spyder/pull/10901) - PR: Update Portuguese (Brazilian) translation for Spyder 4
* [PR 10899](https://github.com/spyder-ide/spyder/pull/10899) - PR: Fix restart when using an external interpreter in development mode
* [PR 10892](https://github.com/spyder-ide/spyder/pull/10892) - PR: Only assign icons to files and directories in Files
* [PR 10886](https://github.com/spyder-ide/spyder/pull/10886) - PR: Remove non-ascii character in a translation string ([10884](https://github.com/spyder-ide/spyder/issues/10884))
* [PR 10885](https://github.com/spyder-ide/spyder/pull/10885) - PR: Skip test_debug_unsaved_file in macOS and Python 3
* [PR 10882](https://github.com/spyder-ide/spyder/pull/10882) - PR: Update Simplified Chinese translations against RC3
* [PR 10868](https://github.com/spyder-ide/spyder/pull/10868) - PR: Add Simplified Chinese translation for Spyder 4
* [PR 10859](https://github.com/spyder-ide/spyder/pull/10859) - PR: Add a reviewed German translation
* [PR 10850](https://github.com/spyder-ide/spyder/pull/10850) - PR: Only go to line in editor when Pdb changes line ([10851](https://github.com/spyder-ide/spyder/issues/10851))
* [PR 10847](https://github.com/spyder-ide/spyder/pull/10847) - PR: Make sure processEvents is not called by Pdb ([10834](https://github.com/spyder-ide/spyder/issues/10834))
* [PR 10839](https://github.com/spyder-ide/spyder/pull/10839) - PR: Don't switch tabs in runfile or runcell ([10736](https://github.com/spyder-ide/spyder/issues/10736))
* [PR 10764](https://github.com/spyder-ide/spyder/pull/10764) - PR: Update Spanish translation for Spyder 4
* [PR 10720](https://github.com/spyder-ide/spyder/pull/10720) - PR: Add french translations
* [PR 10714](https://github.com/spyder-ide/spyder/pull/10714) - PR: Update Japanese translation for 4.0.0

In this release 22 pull requests were closed.


----


## Version 4.0rc3 (2019-11-27)

### Issues Closed

* [Issue 10842](https://github.com/spyder-ide/spyder/issues/10842) - Calltip has unbound local error ([PR 10848](https://github.com/spyder-ide/spyder/pull/10848))
* [Issue 10797](https://github.com/spyder-ide/spyder/issues/10797) - Autocompletions should not be triggered by backspace ([PR 10802](https://github.com/spyder-ide/spyder/pull/10802))
* [Issue 10783](https://github.com/spyder-ide/spyder/issues/10783) - Autocompletions should not be triggered when inserting a newline ([PR 10802](https://github.com/spyder-ide/spyder/pull/10802))
* [Issue 10777](https://github.com/spyder-ide/spyder/issues/10777) - KeyError when removing syntax error in editor ([PR 10782](https://github.com/spyder-ide/spyder/pull/10782))
* [Issue 10766](https://github.com/spyder-ide/spyder/issues/10766) - Enabling or disabling "Show blank spaces" causes Spyder to perma-hang ([PR 10767](https://github.com/spyder-ide/spyder/pull/10767))
* [Issue 10754](https://github.com/spyder-ide/spyder/issues/10754) - Make Spyder display a clear/user-friendly error when used with a too-old Spyder-Kernels version ([PR 10781](https://github.com/spyder-ide/spyder/pull/10781))
* [Issue 10752](https://github.com/spyder-ide/spyder/issues/10752) - Spyder encounters internal error on hover (TypeError / ValueError) ([PR 10757](https://github.com/spyder-ide/spyder/pull/10757))
* [Issue 10660](https://github.com/spyder-ide/spyder/issues/10660) - Adding applications to file associations is broken on Windows due to unescaped backslashes ([PR 10733](https://github.com/spyder-ide/spyder/pull/10733))
* [Issue 10647](https://github.com/spyder-ide/spyder/issues/10647) - Snippets corrupted after completion inserted over placeholder ([PR 10701](https://github.com/spyder-ide/spyder/pull/10701))
* [Issue 10624](https://github.com/spyder-ide/spyder/issues/10624) - Selector for classes and functions not working correctly. ([PR 10825](https://github.com/spyder-ide/spyder/pull/10825))
* [Issue 10528](https://github.com/spyder-ide/spyder/issues/10528) - Completions are not working for underscore variables ([PR 10730](https://github.com/spyder-ide/spyder/pull/10730))
* [Issue 10521](https://github.com/spyder-ide/spyder/issues/10521) - Segmentation fault in paintEvent ([PR 10771](https://github.com/spyder-ide/spyder/pull/10771))
* [Issue 10209](https://github.com/spyder-ide/spyder/issues/10209) - Spyder freezes when trying to connect to an LSP server ([PR 10481](https://github.com/spyder-ide/spyder/pull/10481))
* [Issue 9956](https://github.com/spyder-ide/spyder/issues/9956) - Code folding bug ([PR 10333](https://github.com/spyder-ide/spyder/pull/10333))
* [Issue 5533](https://github.com/spyder-ide/spyder/issues/5533) - Online help index contains invalid links ([PR 10755](https://github.com/spyder-ide/spyder/pull/10755))

In this release 15 issues were closed.

### Pull Requests Merged

* [PR 10848](https://github.com/spyder-ide/spyder/pull/10848) - PR: Fix show_calltip for the IPython console ([10842](https://github.com/spyder-ide/spyder/issues/10842))
* [PR 10838](https://github.com/spyder-ide/spyder/pull/10838) - PR: Update minimal PyLS version required by us
* [PR 10826](https://github.com/spyder-ide/spyder/pull/10826) - PR: Catch extra exception for external plugins
* [PR 10825](https://github.com/spyder-ide/spyder/pull/10825) - PR: Fix class/function selector by using the LSP ([10624](https://github.com/spyder-ide/spyder/issues/10624))
* [PR 10820](https://github.com/spyder-ide/spyder/pull/10820) - PR: Prevent calls to document/didChange whenever the cursor changes position
* [PR 10802](https://github.com/spyder-ide/spyder/pull/10802) - PR: Prevent automatic completions on backspace and return ([10797](https://github.com/spyder-ide/spyder/issues/10797), [10783](https://github.com/spyder-ide/spyder/issues/10783))
* [PR 10782](https://github.com/spyder-ide/spyder/pull/10782) - PR: Fix several issues with the new LSP folding ([10777](https://github.com/spyder-ide/spyder/issues/10777))
* [PR 10781](https://github.com/spyder-ide/spyder/pull/10781) - PR: Improve error message of spyder-kernels version in external interpreter ([10754](https://github.com/spyder-ide/spyder/issues/10754))
* [PR 10771](https://github.com/spyder-ide/spyder/pull/10771) - PR: Fix segfault in replace by calling setFocus outside of EditBlock ([10521](https://github.com/spyder-ide/spyder/issues/10521))
* [PR 10767](https://github.com/spyder-ide/spyder/pull/10767) - PR: Don't request folding when rehighlighting the whole document ([10766](https://github.com/spyder-ide/spyder/issues/10766))
* [PR 10765](https://github.com/spyder-ide/spyder/pull/10765) - PR: Fix opening files with spaces
* [PR 10757](https://github.com/spyder-ide/spyder/pull/10757) - PR: Fix hover regression and improve tests for it ([10752](https://github.com/spyder-ide/spyder/issues/10752))
* [PR 10755](https://github.com/spyder-ide/spyder/pull/10755) - PR: Fix link handling and pydoc numpy related import for Online Help ([5533](https://github.com/spyder-ide/spyder/issues/5533))
* [PR 10733](https://github.com/spyder-ide/spyder/pull/10733) - PR: Fix logic for removing extra quotes on windows path applications ([10660](https://github.com/spyder-ide/spyder/issues/10660))
* [PR 10730](https://github.com/spyder-ide/spyder/pull/10730) - PR: Fix underscore completions ([10528](https://github.com/spyder-ide/spyder/issues/10528))
* [PR 10701](https://github.com/spyder-ide/spyder/pull/10701) - PR: Fix snippet region computation for completion insertions over selections ([10647](https://github.com/spyder-ide/spyder/issues/10647))
* [PR 10481](https://github.com/spyder-ide/spyder/pull/10481) - PR: Don't block when transport layer is down ([10209](https://github.com/spyder-ide/spyder/issues/10209))
* [PR 10333](https://github.com/spyder-ide/spyder/pull/10333) - PR: Enable LSP folding support ([9956](https://github.com/spyder-ide/spyder/issues/9956))

In this release 18 pull requests were closed.


----


## Version 4.0rc2 (2019-11-18)

### Issues Closed

* [Issue 10735](https://github.com/spyder-ide/spyder/issues/10735) - Rename in (variable explorer) is not working properly ([PR 10739](https://github.com/spyder-ide/spyder/pull/10739))
* [Issue 10726](https://github.com/spyder-ide/spyder/issues/10726) - Toolbar tooltips are not updated correctly after a change is made to the shortcuts ([PR 10727](https://github.com/spyder-ide/spyder/pull/10727))
* [Issue 10712](https://github.com/spyder-ide/spyder/issues/10712) - Add a clock to the statusbar ([PR 10725](https://github.com/spyder-ide/spyder/pull/10725))
* [Issue 10709](https://github.com/spyder-ide/spyder/issues/10709) - Errors when removing variables in the Variable Explorer ([PR 10729](https://github.com/spyder-ide/spyder/pull/10729))
* [Issue 10696](https://github.com/spyder-ide/spyder/issues/10696) - Pdb and IPython completes are inconsistent  ([PR 10695](https://github.com/spyder-ide/spyder/pull/10695))
* [Issue 10692](https://github.com/spyder-ide/spyder/issues/10692) - Autocomplete in the console only displays file extensions
* [Issue 10686](https://github.com/spyder-ide/spyder/issues/10686) - Fix path manager synchronize on windows ([PR 10711](https://github.com/spyder-ide/spyder/pull/10711))
* [Issue 10684](https://github.com/spyder-ide/spyder/issues/10684) - EditorStack file and symbol switcher not working #2 ([PR 10685](https://github.com/spyder-ide/spyder/pull/10685))
* [Issue 10682](https://github.com/spyder-ide/spyder/issues/10682) - Some proposed improvements to the file switcher ([PR 10698](https://github.com/spyder-ide/spyder/pull/10698))
* [Issue 10674](https://github.com/spyder-ide/spyder/issues/10674) - Observing $0 / $1 vars in help topic name upon clicking a tooltip ([PR 10731](https://github.com/spyder-ide/spyder/pull/10731))
* [Issue 10653](https://github.com/spyder-ide/spyder/issues/10653) - Error when reporting inotify message ([PR 10662](https://github.com/spyder-ide/spyder/pull/10662))
* [Issue 10650](https://github.com/spyder-ide/spyder/issues/10650) - Error while getting completion of function/method definition ([PR 10688](https://github.com/spyder-ide/spyder/pull/10688))
* [Issue 10646](https://github.com/spyder-ide/spyder/issues/10646) - Go to definition in editor not working for files in user PYTHONPATH ([PR 10629](https://github.com/spyder-ide/spyder/pull/10629))
* [Issue 10634](https://github.com/spyder-ide/spyder/issues/10634) - 'Show completions on the fly' cannot be turned off ([PR 10732](https://github.com/spyder-ide/spyder/pull/10732))
* [Issue 10609](https://github.com/spyder-ide/spyder/issues/10609) - Kite tutorial keeps trying to reload tutorial file ([PR 10615](https://github.com/spyder-ide/spyder/pull/10615))
* [Issue 10593](https://github.com/spyder-ide/spyder/issues/10593) - Error in cv2 autocompletion ([PR 10605](https://github.com/spyder-ide/spyder/pull/10605))
* [Issue 10590](https://github.com/spyder-ide/spyder/issues/10590) - Crash when trying to run a Python file in a project ([PR 10607](https://github.com/spyder-ide/spyder/pull/10607))
* [Issue 10588](https://github.com/spyder-ide/spyder/issues/10588) - IndentationError in pdb breaks the console
* [Issue 10563](https://github.com/spyder-ide/spyder/issues/10563) - runcell is buggy ([PR 10565](https://github.com/spyder-ide/spyder/pull/10565))
* [Issue 10537](https://github.com/spyder-ide/spyder/issues/10537) - Object Explorer improvements ([PR 10546](https://github.com/spyder-ide/spyder/pull/10546))
* [Issue 10534](https://github.com/spyder-ide/spyder/issues/10534) - Completion hint is somtimes strange when using kite ([PR 10731](https://github.com/spyder-ide/spyder/pull/10731))
* [Issue 10449](https://github.com/spyder-ide/spyder/issues/10449) - Kernel times out when sending big variable (it worked in Spyder 3) ([PR 10450](https://github.com/spyder-ide/spyder/pull/10450))
* [Issue 10299](https://github.com/spyder-ide/spyder/issues/10299) - Add jedi env and sys path update to LSP ([PR 10629](https://github.com/spyder-ide/spyder/pull/10629))
* [Issue 10276](https://github.com/spyder-ide/spyder/issues/10276) - Autocomplete introduces code snippet in import statement
* [Issue 10275](https://github.com/spyder-ide/spyder/issues/10275) - Local code not shown in Kite completions ([PR 10638](https://github.com/spyder-ide/spyder/pull/10638))
* [Issue 10264](https://github.com/spyder-ide/spyder/issues/10264) - Find in files freezes spyder ([PR 10582](https://github.com/spyder-ide/spyder/pull/10582))
* [Issue 9865](https://github.com/spyder-ide/spyder/issues/9865) - Cancelling "Save as" leads to modified marker (that cannot be undone) ([PR 10635](https://github.com/spyder-ide/spyder/pull/10635))
* [Issue 9125](https://github.com/spyder-ide/spyder/issues/9125) - Autosave recovery dialog expands beyond screen instead of using scrollbars with too many items ([PR 10549](https://github.com/spyder-ide/spyder/pull/10549))
* [Issue 8715](https://github.com/spyder-ide/spyder/issues/8715) - Add filters to exclude modules and functions in Variable Explorer ([PR 10734](https://github.com/spyder-ide/spyder/pull/10734))
* [Issue 4398](https://github.com/spyder-ide/spyder/issues/4398) - Variable explorer is not updated during code execution ([PR 10567](https://github.com/spyder-ide/spyder/pull/10567))
* [Issue 3321](https://github.com/spyder-ide/spyder/issues/3321) - No shortcuts displayed for plugins ([PR 10560](https://github.com/spyder-ide/spyder/pull/10560))
* [Issue 3254](https://github.com/spyder-ide/spyder/issues/3254) - Shortcuts for external plugins can't be registered ([PR 10560](https://github.com/spyder-ide/spyder/pull/10560))
* [Issue 1004](https://github.com/spyder-ide/spyder/issues/1004) - Make the editor use the selected interpreter in Preferences for completions ([PR 10629](https://github.com/spyder-ide/spyder/pull/10629))

In this release 33 issues were closed.

### Pull Requests Merged

* [PR 10747](https://github.com/spyder-ide/spyder/pull/10747) - PR: Update versions of our dependencies required for rc2
* [PR 10739](https://github.com/spyder-ide/spyder/pull/10739) - PR: Map indexes from proxy model to source model for Variable Explorer actions ([10735](https://github.com/spyder-ide/spyder/issues/10735))
* [PR 10734](https://github.com/spyder-ide/spyder/pull/10734) - PR: Add option to exclude callables and modules in the Variable Explorer ([8715](https://github.com/spyder-ide/spyder/issues/8715))
* [PR 10732](https://github.com/spyder-ide/spyder/pull/10732) - PR: Add delay to dot completion logic ([10634](https://github.com/spyder-ide/spyder/issues/10634))
* [PR 10731](https://github.com/spyder-ide/spyder/pull/10731) - PR: Fix hint for completion and title of help on click ([10674](https://github.com/spyder-ide/spyder/issues/10674), [10534](https://github.com/spyder-ide/spyder/issues/10534))
* [PR 10729](https://github.com/spyder-ide/spyder/pull/10729) - PR: Map indexes from proxy model when removing variables ([10709](https://github.com/spyder-ide/spyder/issues/10709))
* [PR 10727](https://github.com/spyder-ide/spyder/pull/10727) - PR: Fix updating actions tooltips after a change is applied to the shortcuts ([10726](https://github.com/spyder-ide/spyder/issues/10726))
* [PR 10725](https://github.com/spyder-ide/spyder/pull/10725) - PR: Add a clock to the status bar ([10712](https://github.com/spyder-ide/spyder/issues/10712))
* [PR 10715](https://github.com/spyder-ide/spyder/pull/10715) - PR: Add restart option to PluginConfigPage
* [PR 10713](https://github.com/spyder-ide/spyder/pull/10713) - PR: Show the recovery dialog on top of the splash screen
* [PR 10711](https://github.com/spyder-ide/spyder/pull/10711) - PR: Reenable path manager sync on windows ([10686](https://github.com/spyder-ide/spyder/issues/10686))
* [PR 10708](https://github.com/spyder-ide/spyder/pull/10708) - PR: Minor improvements to the shortcut editor
* [PR 10698](https://github.com/spyder-ide/spyder/pull/10698) - PR: Sort items in Switcher in ascending order and move logic to filter items in the proxy model ([10682](https://github.com/spyder-ide/spyder/issues/10682))
* [PR 10695](https://github.com/spyder-ide/spyder/pull/10695) - PR: Use IPython completer for Pdb ([10696](https://github.com/spyder-ide/spyder/issues/10696))
* [PR 10688](https://github.com/spyder-ide/spyder/pull/10688) - PR: Fix completion of function/method definition in Kite ([10650](https://github.com/spyder-ide/spyder/issues/10650))
* [PR 10685](https://github.com/spyder-ide/spyder/pull/10685) - PR: Fix Fileswitcher for 'EditorStack' instances #2 ([10684](https://github.com/spyder-ide/spyder/issues/10684))
* [PR 10683](https://github.com/spyder-ide/spyder/pull/10683) - PR: Make the list view of the file switcher look active at all times.
* [PR 10677](https://github.com/spyder-ide/spyder/pull/10677) - PR: Make to HTMLDelegate drawControl
* [PR 10662](https://github.com/spyder-ide/spyder/pull/10662) - PR: Fix handling of inotify error ([10653](https://github.com/spyder-ide/spyder/issues/10653))
* [PR 10659](https://github.com/spyder-ide/spyder/pull/10659) - PR: Calculate switcher items height from content, padding and font size instead of hard-coded values
* [PR 10654](https://github.com/spyder-ide/spyder/pull/10654) - PR: Display file match items on one line in the find in files browser
* [PR 10648](https://github.com/spyder-ide/spyder/pull/10648) - PR: Send Kite completions requests correctly for selections
* [PR 10644](https://github.com/spyder-ide/spyder/pull/10644) - PR: Prevent status bar widget blinking during startup
* [PR 10638](https://github.com/spyder-ide/spyder/pull/10638) - PR: Trigger completions after braces ([10275](https://github.com/spyder-ide/spyder/issues/10275))
* [PR 10635](https://github.com/spyder-ide/spyder/pull/10635) - PR: Don't mark files as dirty if "Save as" operation is canceled ([9865](https://github.com/spyder-ide/spyder/issues/9865))
* [PR 10631](https://github.com/spyder-ide/spyder/pull/10631) - PR: Don't repeatedly request Kite onboarding file
* [PR 10630](https://github.com/spyder-ide/spyder/pull/10630) - PR: Fix completions bug in Kite introduced by PR 10605
* [PR 10629](https://github.com/spyder-ide/spyder/pull/10629) - PR: Add LSP support for handling jedi script extra paths and environment ([10646](https://github.com/spyder-ide/spyder/issues/10646), [10299](https://github.com/spyder-ide/spyder/issues/10299), [1004](https://github.com/spyder-ide/spyder/issues/1004))
* [PR 10623](https://github.com/spyder-ide/spyder/pull/10623) - PR: Improve path manager
* [PR 10615](https://github.com/spyder-ide/spyder/pull/10615) - PR: Prevent reload of kite onboarding file ([10609](https://github.com/spyder-ide/spyder/issues/10609))
* [PR 10607](https://github.com/spyder-ide/spyder/pull/10607) - PR: Fix 'run file' project explorer action and add test for it ([10590](https://github.com/spyder-ide/spyder/issues/10590))
* [PR 10605](https://github.com/spyder-ide/spyder/pull/10605) - PR: Filter completions with an empty value for the 'insertText' key ([10593](https://github.com/spyder-ide/spyder/issues/10593))
* [PR 10587](https://github.com/spyder-ide/spyder/pull/10587) - PR: Split slow and fast tests in different slots on Travis and Azure
* [PR 10582](https://github.com/spyder-ide/spyder/pull/10582) - PR: Add results in batches and limit results on Find pane to a maximum ([10264](https://github.com/spyder-ide/spyder/issues/10264))
* [PR 10567](https://github.com/spyder-ide/spyder/pull/10567) - PR: Add button and keyboard shortcut to refresh the variable explorer during execution ([4398](https://github.com/spyder-ide/spyder/issues/4398))
* [PR 10565](https://github.com/spyder-ide/spyder/pull/10565) - PR: Improve cell name detection and run cells with the right namespace while debugging ([10563](https://github.com/spyder-ide/spyder/issues/10563))
* [PR 10560](https://github.com/spyder-ide/spyder/pull/10560) - PR: Add methods to handle external plugins shortcuts ([3321](https://github.com/spyder-ide/spyder/issues/3321), [3254](https://github.com/spyder-ide/spyder/issues/3254))
* [PR 10549](https://github.com/spyder-ide/spyder/pull/10549) - PR: Add scrollbar to autosave dialog ([9125](https://github.com/spyder-ide/spyder/issues/9125))
* [PR 10546](https://github.com/spyder-ide/spyder/pull/10546) - PR: Improvements to the Object Explorer (font, resize, and actions over row) ([10537](https://github.com/spyder-ide/spyder/issues/10537))
* [PR 10527](https://github.com/spyder-ide/spyder/pull/10527) - PR: Add an option to execute IPython events while debugging
* [PR 10450](https://github.com/spyder-ide/spyder/pull/10450) - PR: Increase timeout for several calls to the kernel ([10449](https://github.com/spyder-ide/spyder/issues/10449))

In this release 41 pull requests were closed.


----


## Version 4.0rc1 (2019-11-03)

### Issues Closed

* [Issue 10571](https://github.com/spyder-ide/spyder/issues/10571) - Update Kite link in call-to-action ([PR 10579](https://github.com/spyder-ide/spyder/pull/10579))
* [Issue 10489](https://github.com/spyder-ide/spyder/issues/10489) - Cannot remove thumbnails on Plots pane ([PR 10508](https://github.com/spyder-ide/spyder/pull/10508))
* [Issue 10478](https://github.com/spyder-ide/spyder/issues/10478) - "OSError: inotify watch limit reached" with many files in a project ([PR 10480](https://github.com/spyder-ide/spyder/pull/10480))
* [Issue 10457](https://github.com/spyder-ide/spyder/issues/10457) - Decreasing automatic_completions_after_ms setting causes lag when typing ([PR 10502](https://github.com/spyder-ide/spyder/pull/10502))
* [Issue 10453](https://github.com/spyder-ide/spyder/issues/10453) - Completion before ")" causes internal problem. ([PR 10454](https://github.com/spyder-ide/spyder/pull/10454))
* [Issue 10448](https://github.com/spyder-ide/spyder/issues/10448) - Autocompletions not working inside function calls ([PR 10510](https://github.com/spyder-ide/spyder/pull/10510))
* [Issue 10447](https://github.com/spyder-ide/spyder/issues/10447) - Kite completions not being shown ([PR 10509](https://github.com/spyder-ide/spyder/pull/10509))
* [Issue 10442](https://github.com/spyder-ide/spyder/issues/10442) - The kite logo on the status bar is pixelated on retina display: ([PR 10483](https://github.com/spyder-ide/spyder/pull/10483))
* [Issue 10439](https://github.com/spyder-ide/spyder/issues/10439) - Another TypeError when going to definition ([PR 10479](https://github.com/spyder-ide/spyder/pull/10479))
* [Issue 10436](https://github.com/spyder-ide/spyder/issues/10436) - Spyder executable file opened on launch ([PR 10443](https://github.com/spyder-ide/spyder/pull/10443))
* [Issue 10430](https://github.com/spyder-ide/spyder/issues/10430) - UnicodeEncodeError for Kite engine ([PR 10433](https://github.com/spyder-ide/spyder/pull/10433))
* [Issue 10401](https://github.com/spyder-ide/spyder/issues/10401) - No completions returned from Kite after unicode emoji ([PR 10459](https://github.com/spyder-ide/spyder/pull/10459))
* [Issue 10349](https://github.com/spyder-ide/spyder/issues/10349) - Kite autosearch docs not working on mouse events ([PR 10541](https://github.com/spyder-ide/spyder/pull/10541))
* [Issue 10131](https://github.com/spyder-ide/spyder/issues/10131) - Can't click in tooltip because it disappears ([PR 10568](https://github.com/spyder-ide/spyder/pull/10568))
* [Issue 10045](https://github.com/spyder-ide/spyder/issues/10045) - ValueError when closing project on USB stick ([PR 10419](https://github.com/spyder-ide/spyder/pull/10419))
* [Issue 9900](https://github.com/spyder-ide/spyder/issues/9900) - Remove old defaults for spyder ([PR 10180](https://github.com/spyder-ide/spyder/pull/10180))
* [Issue 9805](https://github.com/spyder-ide/spyder/issues/9805) - Update configuration manager to handle site/system level configuration ([PR 10180](https://github.com/spyder-ide/spyder/pull/10180))
* [Issue 5970](https://github.com/spyder-ide/spyder/issues/5970) - When newly created, unsaved file open, running any file triggers the save as dialog ([PR 10115](https://github.com/spyder-ide/spyder/pull/10115))
* [Issue 3232](https://github.com/spyder-ide/spyder/issues/3232) - Add "step into my code" option to the debugger ([PR 10199](https://github.com/spyder-ide/spyder/pull/10199))
* [Issue 2902](https://github.com/spyder-ide/spyder/issues/2902) - Very slow line execution using IPython in macOS

In this release 20 issues were closed.

### Pull Requests Merged

* [PR 10586](https://github.com/spyder-ide/spyder/pull/10586) - PR: Update minimal required version of spyder-kernels
* [PR 10579](https://github.com/spyder-ide/spyder/pull/10579) - PR: Update Kite installer links & remove centering logic ([10571](https://github.com/spyder-ide/spyder/issues/10571))
* [PR 10568](https://github.com/spyder-ide/spyder/pull/10568) - PR: Fix tooltip for hints position ([10131](https://github.com/spyder-ide/spyder/issues/10131))
* [PR 10548](https://github.com/spyder-ide/spyder/pull/10548) - PR: Fix error in Azure when trying to update conda
* [PR 10544](https://github.com/spyder-ide/spyder/pull/10544) - PR: Move runcell test to a better place
* [PR 10541](https://github.com/spyder-ide/spyder/pull/10541) - PR: Retrieve Kite copilot documentation on click ([10349](https://github.com/spyder-ide/spyder/issues/10349))
* [PR 10539](https://github.com/spyder-ide/spyder/pull/10539) - PR: Replace usage of localhost for 127.0.0.1
* [PR 10533](https://github.com/spyder-ide/spyder/pull/10533) - PR: Handle case where a line is destroyed in outline explorer
* [PR 10529](https://github.com/spyder-ide/spyder/pull/10529) - PR: Fix errors when updating menus and the editor was not fully loaded
* [PR 10512](https://github.com/spyder-ide/spyder/pull/10512) - PR: Fix blocknumber segfault
* [PR 10510](https://github.com/spyder-ide/spyder/pull/10510) - PR: Fix on the fly completions inside braces ([10448](https://github.com/spyder-ide/spyder/issues/10448))
* [PR 10509](https://github.com/spyder-ide/spyder/pull/10509) - PR: Add a "wait_for" timeout for completions ([10447](https://github.com/spyder-ide/spyder/issues/10447))
* [PR 10508](https://github.com/spyder-ide/spyder/pull/10508) - PR: Remove thumbnails on plots pane successfully ([10489](https://github.com/spyder-ide/spyder/issues/10489))
* [PR 10504](https://github.com/spyder-ide/spyder/pull/10504) - PR: Correctly handle Kite replacement range, fixing dict completions
* [PR 10502](https://github.com/spyder-ide/spyder/pull/10502) - PR: Completions performance improvements ([10457](https://github.com/spyder-ide/spyder/issues/10457))
* [PR 10496](https://github.com/spyder-ide/spyder/pull/10496) - PR: Print info_page content in the IPython console tests
* [PR 10486](https://github.com/spyder-ide/spyder/pull/10486) - PR: Clear logs menu to avoid creating duplicates
* [PR 10483](https://github.com/spyder-ide/spyder/pull/10483) - PR: Fix kite logo for OSX ([10442](https://github.com/spyder-ide/spyder/issues/10442))
* [PR 10480](https://github.com/spyder-ide/spyder/pull/10480) - PR: Handle inotify error on Linux ([10478](https://github.com/spyder-ide/spyder/issues/10478))
* [PR 10479](https://github.com/spyder-ide/spyder/pull/10479) - PR: Make default responses of completion plugins to be None ([10439](https://github.com/spyder-ide/spyder/issues/10439))
* [PR 10476](https://github.com/spyder-ide/spyder/pull/10476) - PR: Remove deleteLater calls
* [PR 10468](https://github.com/spyder-ide/spyder/pull/10468) - PR: Cleanup test_mainwindow tests
* [PR 10466](https://github.com/spyder-ide/spyder/pull/10466) - PR: Use pytest-faulthandler to debug segmentation faults in our tests
* [PR 10465](https://github.com/spyder-ide/spyder/pull/10465) - PR: Update kite test
* [PR 10464](https://github.com/spyder-ide/spyder/pull/10464) - PR: Print shell content upon failure and try to correct segfaults in IPython console tests
* [PR 10459](https://github.com/spyder-ide/spyder/pull/10459) - PR: Send correct Unicode offset encoding to Kite ([10401](https://github.com/spyder-ide/spyder/issues/10401))
* [PR 10454](https://github.com/spyder-ide/spyder/pull/10454) - PR: Check length of parameters when trying to parse signatures ([10453](https://github.com/spyder-ide/spyder/issues/10453))
* [PR 10444](https://github.com/spyder-ide/spyder/pull/10444) - PR: Use a single main window instance to run all its tests
* [PR 10443](https://github.com/spyder-ide/spyder/pull/10443) - PR: Skip opening launch script in macOS application ([10436](https://github.com/spyder-ide/spyder/issues/10436))
* [PR 10438](https://github.com/spyder-ide/spyder/pull/10438) - PR: Use a new comm socket for comms
* [PR 10433](https://github.com/spyder-ide/spyder/pull/10433) - PR: Fix encoding issues when using Python 2 ([10430](https://github.com/spyder-ide/spyder/issues/10430))
* [PR 10419](https://github.com/spyder-ide/spyder/pull/10419) - PR: Handle paths for recent files on a different mount than the project root path ([10045](https://github.com/spyder-ide/spyder/issues/10045))
* [PR 10414](https://github.com/spyder-ide/spyder/pull/10414) - PR: Register Spyder with macOS launch services
* [PR 10260](https://github.com/spyder-ide/spyder/pull/10260) - PR: Show Kite onboarding file once after Kite was installed
* [PR 10199](https://github.com/spyder-ide/spyder/pull/10199) - PR: Add an option to ignore installed Python libraries while debugging ([3232](https://github.com/spyder-ide/spyder/issues/3232))
* [PR 10180](https://github.com/spyder-ide/spyder/pull/10180) - PR: Add global and environment configuration paths to load default options from them ([9900](https://github.com/spyder-ide/spyder/issues/9900), [9805](https://github.com/spyder-ide/spyder/issues/9805))
* [PR 10115](https://github.com/spyder-ide/spyder/pull/10115) - PR: Run and debug files without saving them ([5970](https://github.com/spyder-ide/spyder/issues/5970))
* [PR 10111](https://github.com/spyder-ide/spyder/pull/10111) - PR: Kill LSP transport layer if Spyder gets killed

In this release 38 pull requests were closed.


----


## Version 4.0beta7 (2019-10-17)

### Issues Closed

* [Issue 10424](https://github.com/spyder-ide/spyder/issues/10424) - Kite call-to-action consistently causes a Spyder hard crash ([PR 10432](https://github.com/spyder-ide/spyder/pull/10432))
* [Issue 10404](https://github.com/spyder-ide/spyder/issues/10404) - TypeError in go-to-definition ([PR 10399](https://github.com/spyder-ide/spyder/pull/10399))
* [Issue 10388](https://github.com/spyder-ide/spyder/issues/10388) - Big toolip when using kite ([PR 10405](https://github.com/spyder-ide/spyder/pull/10405))
* [Issue 10372](https://github.com/spyder-ide/spyder/issues/10372) - IndexError when autocompleting using Kite ([PR 10418](https://github.com/spyder-ide/spyder/pull/10418))
* [Issue 10351](https://github.com/spyder-ide/spyder/issues/10351) - Syntax coloring  incorrect with import as statements ([PR 10421](https://github.com/spyder-ide/spyder/pull/10421))
* [Issue 10335](https://github.com/spyder-ide/spyder/issues/10335) - Editor plugin not raised after selecting file in Switcher ([PR 10420](https://github.com/spyder-ide/spyder/pull/10420))
* [Issue 10290](https://github.com/spyder-ide/spyder/issues/10290) - Deleting line when breakpoint it set causes crash
* [Issue 9356](https://github.com/spyder-ide/spyder/issues/9356) - UnicodeEncodeError when pylint tries to print non-ascii character ([PR 9851](https://github.com/spyder-ide/spyder/pull/9851))
* [Issue 7787](https://github.com/spyder-ide/spyder/issues/7787) - Suppress ipdb output during debug ([PR 10207](https://github.com/spyder-ide/spyder/pull/10207))
* [Issue 7031](https://github.com/spyder-ide/spyder/issues/7031) - Profiler raises a UnicodeEncodeError when non-ASCII characters are printed by the source file ([PR 9851](https://github.com/spyder-ide/spyder/pull/9851))
* [Issue 1643](https://github.com/spyder-ide/spyder/issues/1643) - Spyder does not fully support IPython scripts (*.ipy)
* [Issue 1073](https://github.com/spyder-ide/spyder/issues/1073) - Debugging: Unable to run selection while debugging ([PR 10190](https://github.com/spyder-ide/spyder/pull/10190))
* [Issue 288](https://github.com/spyder-ide/spyder/issues/288) - Code completion doesn't work in the debugger

In this release 13 issues were closed.

### Pull Requests Merged

* [PR 10434](https://github.com/spyder-ide/spyder/pull/10434) - PR: Increase minimal required version of spyder-kernels to 1.6
* [PR 10432](https://github.com/spyder-ide/spyder/pull/10432) - PR: Add bloom files to our tarballs ([10424](https://github.com/spyder-ide/spyder/issues/10424))
* [PR 10421](https://github.com/spyder-ide/spyder/pull/10421) - PR: Update highlighter regex for 'as' keyword ([10351](https://github.com/spyder-ide/spyder/issues/10351))
* [PR 10420](https://github.com/spyder-ide/spyder/pull/10420) - PR: Editor plugin is raised after selecting file in the switcher ([10335](https://github.com/spyder-ide/spyder/issues/10335))
* [PR 10418](https://github.com/spyder-ide/spyder/pull/10418) - PR: Check length of parameters data vs active parameter index ([10372](https://github.com/spyder-ide/spyder/issues/10372))
* [PR 10413](https://github.com/spyder-ide/spyder/pull/10413) - PR: Don't use PyLS 0.29 for now in our tests
* [PR 10411](https://github.com/spyder-ide/spyder/pull/10411) - PR: Add validation for number of parameters in function calltip ([10408](https://github.com/spyder-ide/spyder/issues/10408))
* [PR 10405](https://github.com/spyder-ide/spyder/pull/10405) - PR: Add validation for completion signature processing ([10388](https://github.com/spyder-ide/spyder/issues/10388))
* [PR 10403](https://github.com/spyder-ide/spyder/pull/10403) - PR: Improve LSP support for MarkupString[] for hover requests
* [PR 10399](https://github.com/spyder-ide/spyder/pull/10399) - PR: Fix deadlock when going to a definition ([10404](https://github.com/spyder-ide/spyder/issues/10404))
* [PR 10327](https://github.com/spyder-ide/spyder/pull/10327) - PR: Try opening closed files in the frontend side
* [PR 10207](https://github.com/spyder-ide/spyder/pull/10207) - PR: Disable printing stack when using debug buttons ([7787](https://github.com/spyder-ide/spyder/issues/7787))
* [PR 10190](https://github.com/spyder-ide/spyder/pull/10190) - PR: Full multiline support and better history management for the debugger ([1073](https://github.com/spyder-ide/spyder/issues/1073))
* [PR 10153](https://github.com/spyder-ide/spyder/pull/10153) - PR: Add console handler to send file contents to the kernel during execution
* [PR 9940](https://github.com/spyder-ide/spyder/pull/9940) - PR: Add autocomplete to the debugger
* [PR 9851](https://github.com/spyder-ide/spyder/pull/9851) - PR: Set encoding to utf8 for Profiler and Pylint processes ([9356](https://github.com/spyder-ide/spyder/issues/9356), [7031](https://github.com/spyder-ide/spyder/issues/7031))

In this release 16 pull requests were closed.


----


## Version 4.0beta6 (2019-10-14)

### Issues Closed

* [Issue 10352](https://github.com/spyder-ide/spyder/issues/10352) - An error occurs when autocompleting 'subplots' using kite. ([PR 10365](https://github.com/spyder-ide/spyder/pull/10365))
* [Issue 10331](https://github.com/spyder-ide/spyder/issues/10331) - Automatic_completions* options not being set at startup ([PR 10348](https://github.com/spyder-ide/spyder/pull/10348))
* [Issue 10308](https://github.com/spyder-ide/spyder/issues/10308) - A file switcher test is failing on master ([PR 10309](https://github.com/spyder-ide/spyder/pull/10309))
* [Issue 10296](https://github.com/spyder-ide/spyder/issues/10296) - Portuguese (BRAZIL) minor error ([PR 10344](https://github.com/spyder-ide/spyder/pull/10344))
* [Issue 10289](https://github.com/spyder-ide/spyder/issues/10289) - crash in 4.0.0b5 related to non-ascii characters and tooltips ([PR 10256](https://github.com/spyder-ide/spyder/pull/10256))
* [Issue 10284](https://github.com/spyder-ide/spyder/issues/10284) - Can not change font ([PR 10306](https://github.com/spyder-ide/spyder/pull/10306))
* [Issue 10255](https://github.com/spyder-ide/spyder/issues/10255) - Selected figure thumbnail in Plots not highlighted in dark mode ([PR 10259](https://github.com/spyder-ide/spyder/pull/10259))
* [Issue 10248](https://github.com/spyder-ide/spyder/issues/10248) - Trailing spaces are being removed on line change even if the option is unset in preferences ([PR 10261](https://github.com/spyder-ide/spyder/pull/10261))
* [Issue 10235](https://github.com/spyder-ide/spyder/issues/10235) - Completions docs UI shows docs for wrong completion ([PR 10262](https://github.com/spyder-ide/spyder/pull/10262))
* [Issue 10230](https://github.com/spyder-ide/spyder/issues/10230) - Several errors with code snippets ([PR 10256](https://github.com/spyder-ide/spyder/pull/10256))
* [Issue 10227](https://github.com/spyder-ide/spyder/issues/10227) - Kite completions ordering is not respected ([PR 10301](https://github.com/spyder-ide/spyder/pull/10301))
* [Issue 10226](https://github.com/spyder-ide/spyder/issues/10226) - Kite (and LSP) completions frequently not displayed ([PR 10301](https://github.com/spyder-ide/spyder/pull/10301))
* [Issue 10214](https://github.com/spyder-ide/spyder/issues/10214) - Minimal pyxdg version not set in setup.py ([PR 10218](https://github.com/spyder-ide/spyder/pull/10218))
* [Issue 10208](https://github.com/spyder-ide/spyder/issues/10208) - OSError when saving files on Linux ([PR 10236](https://github.com/spyder-ide/spyder/pull/10236))
* [Issue 10203](https://github.com/spyder-ide/spyder/issues/10203) - IndexError in Kite completitons  ([PR 10216](https://github.com/spyder-ide/spyder/pull/10216))
* [Issue 10141](https://github.com/spyder-ide/spyder/issues/10141) - Ctrl+I doesn't work in editor when hovers are deactivated ([PR 10254](https://github.com/spyder-ide/spyder/pull/10254))
* [Issue 10134](https://github.com/spyder-ide/spyder/issues/10134) - On the fly code completion interferes with normal typing ([PR 10262](https://github.com/spyder-ide/spyder/pull/10262))
* [Issue 10118](https://github.com/spyder-ide/spyder/issues/10118) - Open Collective ([PR 10237](https://github.com/spyder-ide/spyder/pull/10237))
* [Issue 10071](https://github.com/spyder-ide/spyder/issues/10071) - Kite is always started ([PR 10354](https://github.com/spyder-ide/spyder/pull/10354))
* [Issue 9992](https://github.com/spyder-ide/spyder/issues/9992) - Completion stopped working after switching to "This is an external server" ([PR 10278](https://github.com/spyder-ide/spyder/pull/10278))
* [Issue 7008](https://github.com/spyder-ide/spyder/issues/7008) - Keyboard shortcut dialog unuseable / crash ([PR 10215](https://github.com/spyder-ide/spyder/pull/10215))

In this release 21 issues were closed.

### Pull Requests Merged

* [PR 10370](https://github.com/spyder-ide/spyder/pull/10370) - PR: Remove extraneous Kite config option
* [PR 10365](https://github.com/spyder-ide/spyder/pull/10365) - PR: Fix Kite error when args in signature is None ([10352](https://github.com/spyder-ide/spyder/issues/10352))
* [PR 10358](https://github.com/spyder-ide/spyder/pull/10358) - PR: Update test_c_and_n_pdb_commands test
* [PR 10354](https://github.com/spyder-ide/spyder/pull/10354) - PR: Enable better configuration of completions clients ([10071](https://github.com/spyder-ide/spyder/issues/10071))
* [PR 10348](https://github.com/spyder-ide/spyder/pull/10348) - PR: Apply autocompletion options at startup ([10331](https://github.com/spyder-ide/spyder/issues/10331))
* [PR 10344](https://github.com/spyder-ide/spyder/pull/10344) - PR: Fix error in Portuguese translation ([10296](https://github.com/spyder-ide/spyder/issues/10296))
* [PR 10338](https://github.com/spyder-ide/spyder/pull/10338) - PR: Add LSP log option when spyder is in debug mode
* [PR 10332](https://github.com/spyder-ide/spyder/pull/10332) - PR: Add a call-to-action for Kite
* [PR 10324](https://github.com/spyder-ide/spyder/pull/10324) - PR: Add branding for code snippet completions
* [PR 10321](https://github.com/spyder-ide/spyder/pull/10321) - PR: Show exact match completions
* [PR 10314](https://github.com/spyder-ide/spyder/pull/10314) - PR: Fix tests on Windows
* [PR 10309](https://github.com/spyder-ide/spyder/pull/10309) - PR: Fix test and path shortening for the switcher ([10308](https://github.com/spyder-ide/spyder/issues/10308))
* [PR 10306](https://github.com/spyder-ide/spyder/pull/10306) - PR: Fix regression for set_font method ([10284](https://github.com/spyder-ide/spyder/issues/10284))
* [PR 10301](https://github.com/spyder-ide/spyder/pull/10301) - PR: Fix completions prioritization and Kite completions behavior ([10227](https://github.com/spyder-ide/spyder/issues/10227), [10226](https://github.com/spyder-ide/spyder/issues/10226))
* [PR 10278](https://github.com/spyder-ide/spyder/pull/10278) - PR: Add several validations for external LSP servers ([9992](https://github.com/spyder-ide/spyder/issues/9992))
* [PR 10270](https://github.com/spyder-ide/spyder/pull/10270) - PR: Fix regression and add test for language selection on preferences
* [PR 10262](https://github.com/spyder-ide/spyder/pull/10262) - PR: Add delay and minimum chars to on the fly completions ([10235](https://github.com/spyder-ide/spyder/issues/10235), [10134](https://github.com/spyder-ide/spyder/issues/10134))
* [PR 10261](https://github.com/spyder-ide/spyder/pull/10261) - PR: Only remove trailing spaces when option is turned on in Preferences ([10248](https://github.com/spyder-ide/spyder/issues/10248))
* [PR 10259](https://github.com/spyder-ide/spyder/pull/10259) - PR: Better highlight selected figure in thumbnail. ([10255](https://github.com/spyder-ide/spyder/issues/10255))
* [PR 10256](https://github.com/spyder-ide/spyder/pull/10256) - PR: Fix several code snippets corner cases ([10289](https://github.com/spyder-ide/spyder/issues/10289), [10230](https://github.com/spyder-ide/spyder/issues/10230))
* [PR 10254](https://github.com/spyder-ide/spyder/pull/10254) - PR: Always enable hovers on the PyLS ([10141](https://github.com/spyder-ide/spyder/issues/10141))
* [PR 10253](https://github.com/spyder-ide/spyder/pull/10253) - PR: Move some options from editor to LSP Preferences page
* [PR 10252](https://github.com/spyder-ide/spyder/pull/10252) - PR: Add ability to modify other plugin options
* [PR 10251](https://github.com/spyder-ide/spyder/pull/10251) - PR: Add an installation UI for Kite
* [PR 10249](https://github.com/spyder-ide/spyder/pull/10249) - PR: Avoid stripping if the event comes from another editor
* [PR 10237](https://github.com/spyder-ide/spyder/pull/10237) - PR: Add open collective funding button ([10118](https://github.com/spyder-ide/spyder/issues/10118))
* [PR 10236](https://github.com/spyder-ide/spyder/pull/10236) - PR: Fix OSError when saving files on Linux ([10208](https://github.com/spyder-ide/spyder/issues/10208))
* [PR 10233](https://github.com/spyder-ide/spyder/pull/10233) - PR: Send current cursor position to Kite to enable autosearch in Kite Copilot
* [PR 10220](https://github.com/spyder-ide/spyder/pull/10220) - PR: Catch errors when sending messages to tcp sockets that reject a connection from our LSP client
* [PR 10219](https://github.com/spyder-ide/spyder/pull/10219) - PR: Create LSP logs for all active instances of Spyder
* [PR 10218](https://github.com/spyder-ide/spyder/pull/10218) - PR: Add minimal requirement for pyxdg to 0.26 ([10214](https://github.com/spyder-ide/spyder/issues/10214))
* [PR 10216](https://github.com/spyder-ide/spyder/pull/10216) - PR: Fix signature processing when no signature is retrieved with Kite ([10203](https://github.com/spyder-ide/spyder/issues/10203))
* [PR 10215](https://github.com/spyder-ide/spyder/pull/10215) - PR: Fix keyboard shortcut dialog crash ([7008](https://github.com/spyder-ide/spyder/issues/7008))
* [PR 10211](https://github.com/spyder-ide/spyder/pull/10211) - PR: Fix connection to an external LSP server
* [PR 10205](https://github.com/spyder-ide/spyder/pull/10205) - PR: Add checkbox to verify changes in advanced options of LSP preferences
* [PR 10179](https://github.com/spyder-ide/spyder/pull/10179) - PR: Implement Kite installation logic
* [PR 10166](https://github.com/spyder-ide/spyder/pull/10166) - PR: Add status bar widget for Kite

In this release 37 pull requests were closed.


----


## Version 4.0beta5 (2019-09-15)

### Issues Closed

* [Issue 10176](https://github.com/spyder-ide/spyder/issues/10176) - Handle connection errors when quitting Kite outside Spyder ([PR 10177](https://github.com/spyder-ide/spyder/pull/10177))
* [Issue 10159](https://github.com/spyder-ide/spyder/issues/10159) - TypeError in kite client ([PR 10173](https://github.com/spyder-ide/spyder/pull/10173))
* [Issue 10139](https://github.com/spyder-ide/spyder/issues/10139) - 'Enable docstring style linting' setting not saved in Preferences ([PR 10145](https://github.com/spyder-ide/spyder/pull/10145))
* [Issue 10138](https://github.com/spyder-ide/spyder/issues/10138) - Spyder hangs if you open the Issue reporter while Preferences is open ([PR 10142](https://github.com/spyder-ide/spyder/pull/10142))
* [Issue 10136](https://github.com/spyder-ide/spyder/issues/10136) - Issue reporter misbehaves if you delete characters of the header with the Delete key ([PR 10140](https://github.com/spyder-ide/spyder/pull/10140))
* [Issue 10135](https://github.com/spyder-ide/spyder/issues/10135) - Issue reporter dialog should not be modal ([PR 10143](https://github.com/spyder-ide/spyder/pull/10143))
* [Issue 10109](https://github.com/spyder-ide/spyder/issues/10109) - Incorrect Kite completions ordering ([PR 10110](https://github.com/spyder-ide/spyder/pull/10110))
* [Issue 10073](https://github.com/spyder-ide/spyder/issues/10073) - Outline links to editor wrong when code is folded ([PR 10074](https://github.com/spyder-ide/spyder/pull/10074))
* [Issue 10048](https://github.com/spyder-ide/spyder/issues/10048) - runfile breaks debugfile ([PR 10047](https://github.com/spyder-ide/spyder/pull/10047))
* [Issue 10039](https://github.com/spyder-ide/spyder/issues/10039) - Editor has several problems to handle emojis ([PR 10043](https://github.com/spyder-ide/spyder/pull/10043))
* [Issue 10038](https://github.com/spyder-ide/spyder/issues/10038) - KeyError when autosaving file ([PR 10100](https://github.com/spyder-ide/spyder/pull/10100))
* [Issue 10029](https://github.com/spyder-ide/spyder/issues/10029) - Ignore ConnectionError on Kite completions request ([PR 10076](https://github.com/spyder-ide/spyder/pull/10076))
* [Issue 10014](https://github.com/spyder-ide/spyder/issues/10014) - "Projects > Recent" always opens last project ([PR 10035](https://github.com/spyder-ide/spyder/pull/10035))
* [Issue 10011](https://github.com/spyder-ide/spyder/issues/10011) - re.error when getting signature in the editor ([PR 10016](https://github.com/spyder-ide/spyder/pull/10016))
* [Issue 10002](https://github.com/spyder-ide/spyder/issues/10002) - Remove "No match" entry in editor's code completion widget ([PR 10007](https://github.com/spyder-ide/spyder/pull/10007))
* [Issue 9996](https://github.com/spyder-ide/spyder/issues/9996) - Resize in dataframe viewer does not honor column name length ([PR 10017](https://github.com/spyder-ide/spyder/pull/10017))
* [Issue 9993](https://github.com/spyder-ide/spyder/issues/9993) - TypeError in Kite client ([PR 10076](https://github.com/spyder-ide/spyder/pull/10076))
* [Issue 9973](https://github.com/spyder-ide/spyder/issues/9973) - Sorting is not right when viewing a list in the Variable Explorer ([PR 9980](https://github.com/spyder-ide/spyder/pull/9980))
* [Issue 9963](https://github.com/spyder-ide/spyder/issues/9963) - Running an empty cell is broken ([PR 9014](https://github.com/spyder-ide/spyder/pull/9014))
* [Issue 9959](https://github.com/spyder-ide/spyder/issues/9959) -  TypeError in object explorer ([PR 9967](https://github.com/spyder-ide/spyder/pull/9967))
* [Issue 9950](https://github.com/spyder-ide/spyder/issues/9950) - Syntax Highlighter is supressing outlined QTextCharFormat style ([PR 10137](https://github.com/spyder-ide/spyder/pull/10137))
* [Issue 9933](https://github.com/spyder-ide/spyder/issues/9933) - PyLS settings are not being applied live ([PR 10164](https://github.com/spyder-ide/spyder/pull/10164))
* [Issue 9924](https://github.com/spyder-ide/spyder/issues/9924) - Warning/error on last row not in warning list ([PR 9943](https://github.com/spyder-ide/spyder/pull/9943))
* [Issue 9796](https://github.com/spyder-ide/spyder/issues/9796) - Centralize all dependencies in one place and declare all the ones present in setup.py ([PR 9975](https://github.com/spyder-ide/spyder/pull/9975))
* [Issue 9747](https://github.com/spyder-ide/spyder/issues/9747) - Separator on plots plugin acts more like a button than a resize area ([PR 9720](https://github.com/spyder-ide/spyder/pull/9720))
* [Issue 9568](https://github.com/spyder-ide/spyder/issues/9568) - Implement code snippets for completions ([PR 9850](https://github.com/spyder-ide/spyder/pull/9850))
* [Issue 9516](https://github.com/spyder-ide/spyder/issues/9516) - Variable Explorer bug when sorting by 'size' ([PR 9980](https://github.com/spyder-ide/spyder/pull/9980))
* [Issue 9420](https://github.com/spyder-ide/spyder/issues/9420) - FileNotFoundError when closing a file that's opened in several Spyder instances ([PR 10077](https://github.com/spyder-ide/spyder/pull/10077))
* [Issue 9361](https://github.com/spyder-ide/spyder/issues/9361) - Add a command to debug a single cell ([PR 9014](https://github.com/spyder-ide/spyder/pull/9014))
* [Issue 9342](https://github.com/spyder-ide/spyder/issues/9342) - File not saved when calling runfile from console ([PR 9966](https://github.com/spyder-ide/spyder/pull/9966))
* [Issue 9246](https://github.com/spyder-ide/spyder/issues/9246) - Set icons for other completion kind items ([PR 9897](https://github.com/spyder-ide/spyder/pull/9897))
* [Issue 9198](https://github.com/spyder-ide/spyder/issues/9198) - Make changing the working directory via the toolbar work with local external Spyder kernels ([PR 9999](https://github.com/spyder-ide/spyder/pull/9999))
* [Issue 9197](https://github.com/spyder-ide/spyder/issues/9197) - Plots plugin doesn't show plots generated in local, external Spyder kernels ([PR 10001](https://github.com/spyder-ide/spyder/pull/10001))
* [Issue 8580](https://github.com/spyder-ide/spyder/issues/8580) - Improvements to the File switcher ([PR 10060](https://github.com/spyder-ide/spyder/pull/10060))
* [Issue 7377](https://github.com/spyder-ide/spyder/issues/7377) - Indentation errors for fuction calls with `#` in a string ([PR 9566](https://github.com/spyder-ide/spyder/pull/9566))
* [Issue 5606](https://github.com/spyder-ide/spyder/issues/5606) - Editor sets incorrect indent when character immediately before the break is a paren ([PR 9566](https://github.com/spyder-ide/spyder/pull/9566))
* [Issue 4180](https://github.com/spyder-ide/spyder/issues/4180) - It should be possible to get the same behaviour with Spyder's Run button than with IPython's %run
* [Issue 3798](https://github.com/spyder-ide/spyder/issues/3798) - Invert colors for "Pretty-Printing" symbolic math in IPython's dark background ([PR 10114](https://github.com/spyder-ide/spyder/pull/10114))
* [Issue 3181](https://github.com/spyder-ide/spyder/issues/3181) - Show signature to the right of the completion widget ([PR 9897](https://github.com/spyder-ide/spyder/pull/9897))
* [Issue 2871](https://github.com/spyder-ide/spyder/issues/2871) - Hide completion widget when scrolling up and down ([PR 9897](https://github.com/spyder-ide/spyder/pull/9897))
* [Issue 887](https://github.com/spyder-ide/spyder/issues/887) - Fix issues with incorrect auto-indentation ([PR 9566](https://github.com/spyder-ide/spyder/pull/9566))

In this release 41 issues were closed.

### Pull Requests Merged

* [PR 10202](https://github.com/spyder-ide/spyder/pull/10202) - PR: Update spyder-kernels and PyLS minimal required versions
* [PR 10196](https://github.com/spyder-ide/spyder/pull/10196) - PR: Detect zombie process and add python as default Kite client available language
* [PR 10195](https://github.com/spyder-ide/spyder/pull/10195) - PR: Fix formatting of missing dependencies dialog
* [PR 10189](https://github.com/spyder-ide/spyder/pull/10189) - PR: Fix multiline support for pdb history
* [PR 10181](https://github.com/spyder-ide/spyder/pull/10181) - PR: Use multi config for project configuration
* [PR 10177](https://github.com/spyder-ide/spyder/pull/10177) - PR: Handle Kite client connection errors when quitting Kite outside Spyder ([10176](https://github.com/spyder-ide/spyder/issues/10176))
* [PR 10174](https://github.com/spyder-ide/spyder/pull/10174) - PR: Gather responses from other completion sources when LSP raises an error
* [PR 10173](https://github.com/spyder-ide/spyder/pull/10173) - PR: Fix error when response is None in Kite client ([10159](https://github.com/spyder-ide/spyder/issues/10159))
* [PR 10170](https://github.com/spyder-ide/spyder/pull/10170) - PR: Add class variables to set configuration options for plugins
* [PR 10164](https://github.com/spyder-ide/spyder/pull/10164) - PR: Fix PyLS options not being updated correctly when a previous server was running ([9933](https://github.com/spyder-ide/spyder/issues/9933))
* [PR 10162](https://github.com/spyder-ide/spyder/pull/10162) - PR: Remove adding second interpreter prompt after error
* [PR 10160](https://github.com/spyder-ide/spyder/pull/10160) - PR: Fix banners for the IPython console
* [PR 10158](https://github.com/spyder-ide/spyder/pull/10158) - PR: Don't call MainWindow's apply_settings method when no needed
* [PR 10150](https://github.com/spyder-ide/spyder/pull/10150) - PR: Avoid RuntimeError when handling completion responses
* [PR 10145](https://github.com/spyder-ide/spyder/pull/10145) - PR: Fix PyLS actions triggering in Preferences ([10139](https://github.com/spyder-ide/spyder/issues/10139))
* [PR 10143](https://github.com/spyder-ide/spyder/pull/10143) - PR: Set error dialog as non-modal ([10135](https://github.com/spyder-ide/spyder/issues/10135))
* [PR 10142](https://github.com/spyder-ide/spyder/pull/10142) - PR: Revert windows on top for config dialog ([10138](https://github.com/spyder-ide/spyder/issues/10138))
* [PR 10140](https://github.com/spyder-ide/spyder/pull/10140) - PR: Fix Del key on report error dialog ([10136](https://github.com/spyder-ide/spyder/issues/10136))
* [PR 10137](https://github.com/spyder-ide/spyder/pull/10137) - PR: Prevent background overrides to extra decorations ([9950](https://github.com/spyder-ide/spyder/issues/9950))
* [PR 10114](https://github.com/spyder-ide/spyder/pull/10114) - PR: Handle Sympy foreground color setting following a color scheme change ([3798](https://github.com/spyder-ide/spyder/issues/3798))
* [PR 10110](https://github.com/spyder-ide/spyder/pull/10110) - PR: Fix completion order for lower/upper case entries ([10109](https://github.com/spyder-ide/spyder/issues/10109))
* [PR 10104](https://github.com/spyder-ide/spyder/pull/10104) - PR: Hide tooltips if switching editor in stack
* [PR 10103](https://github.com/spyder-ide/spyder/pull/10103) - PR: Fix code editor freeze when searching for next/previous warnings
* [PR 10100](https://github.com/spyder-ide/spyder/pull/10100) - PR: Update autosave information after file is renamed ([10038](https://github.com/spyder-ide/spyder/issues/10038))
* [PR 10088](https://github.com/spyder-ide/spyder/pull/10088) - PR: Always enable Kite completions
* [PR 10087](https://github.com/spyder-ide/spyder/pull/10087) - PR: Separate pdb input from regular input
* [PR 10085](https://github.com/spyder-ide/spyder/pull/10085) - PR: Stop IPython console channels faster
* [PR 10082](https://github.com/spyder-ide/spyder/pull/10082) - PR: Change the current cell color of the Spyder Dark theme
* [PR 10077](https://github.com/spyder-ide/spyder/pull/10077) - PR: Store autosave information in separate files instead of the Spyder config ([9420](https://github.com/spyder-ide/spyder/issues/9420))
* [PR 10076](https://github.com/spyder-ide/spyder/pull/10076) - PR: Check if responses are not None in Kite plugin handlers ([9993](https://github.com/spyder-ide/spyder/issues/9993), [10029](https://github.com/spyder-ide/spyder/issues/10029))
* [PR 10074](https://github.com/spyder-ide/spyder/pull/10074) - PR: Fix getting blocks by numbers in the editor ([10073](https://github.com/spyder-ide/spyder/issues/10073))
* [PR 10072](https://github.com/spyder-ide/spyder/pull/10072) - PR: Hide size/type columns and add show/hide actions to header (right click) and plugin opts.
* [PR 10070](https://github.com/spyder-ide/spyder/pull/10070) - PR: Prevent Kite error at startup if Kite is closed on macOS
* [PR 10067](https://github.com/spyder-ide/spyder/pull/10067) - PR: Improve check to see if Spyder is running in a macOS app
* [PR 10066](https://github.com/spyder-ide/spyder/pull/10066) - PR: Speedup of console shutdown time
* [PR 10060](https://github.com/spyder-ide/spyder/pull/10060) - PR: Migrate FileSwitcher functionality to Switcher ([8580](https://github.com/spyder-ide/spyder/issues/8580))
* [PR 10049](https://github.com/spyder-ide/spyder/pull/10049) - PR: Avoid discarding file open event in macOS app
* [PR 10047](https://github.com/spyder-ide/spyder/pull/10047) - PR: Add new test for unnamed first cell and debugcell ([10048](https://github.com/spyder-ide/spyder/issues/10048))
* [PR 10044](https://github.com/spyder-ide/spyder/pull/10044) - PR: Fix a couple of main window debugging tests
* [PR 10043](https://github.com/spyder-ide/spyder/pull/10043) - PR: Solve some issues with QString compatibility with emojis ([10039](https://github.com/spyder-ide/spyder/issues/10039))
* [PR 10035](https://github.com/spyder-ide/spyder/pull/10035) - PR: Fix "Projects > Recent" menu entries ([10014](https://github.com/spyder-ide/spyder/issues/10014))
* [PR 10033](https://github.com/spyder-ide/spyder/pull/10033) - PR: Skip new switcher test in CircleCI because it gives a segfault
* [PR 10032](https://github.com/spyder-ide/spyder/pull/10032) - PR: Add an option to run a file in the console's current namespace
* [PR 10017](https://github.com/spyder-ide/spyder/pull/10017) - PR: Resize dataframeeditor header to contents ([9996](https://github.com/spyder-ide/spyder/issues/9996))
* [PR 10016](https://github.com/spyder-ide/spyder/pull/10016) - PR: Escape regex characters from parameters while processing a signature ([10011](https://github.com/spyder-ide/spyder/issues/10011))
* [PR 10010](https://github.com/spyder-ide/spyder/pull/10010) - PR: Add permanent history to the debugger
* [PR 10007](https://github.com/spyder-ide/spyder/pull/10007) - PR: Remove "No match" entry in editor's code completion widget ([10002](https://github.com/spyder-ide/spyder/issues/10002))
* [PR 10006](https://github.com/spyder-ide/spyder/pull/10006) - PR: Correct Pympler required version
* [PR 10001](https://github.com/spyder-ide/spyder/pull/10001) - PR: Connect Plots plugin to external Spyder kernels ([9197](https://github.com/spyder-ide/spyder/issues/9197))
* [PR 10000](https://github.com/spyder-ide/spyder/pull/10000) - PR: Drop support for Python 3.4
* [PR 9999](https://github.com/spyder-ide/spyder/pull/9999) - PR: Allow setting the cwd through our toolbar for local external Spyder kernels ([9198](https://github.com/spyder-ide/spyder/issues/9198))
* [PR 9995](https://github.com/spyder-ide/spyder/pull/9995) - PR: Fix tests in Travis
* [PR 9988](https://github.com/spyder-ide/spyder/pull/9988) - PR: Improve support for Kite on macOS
* [PR 9980](https://github.com/spyder-ide/spyder/pull/9980) - PR: Don't convert values to text strings and fix sorting issues in the Variable Explorer ([9973](https://github.com/spyder-ide/spyder/issues/9973), [9516](https://github.com/spyder-ide/spyder/issues/9516))
* [PR 9975](https://github.com/spyder-ide/spyder/pull/9975) - PR: Centralize dependencies and declare the missing ones ([9796](https://github.com/spyder-ide/spyder/issues/9796))
* [PR 9967](https://github.com/spyder-ide/spyder/pull/9967) - PR: Improve error handling while getting objects attributes ([9959](https://github.com/spyder-ide/spyder/issues/9959))
* [PR 9966](https://github.com/spyder-ide/spyder/pull/9966) - PR: Save files when calling runfile directly in the console ([9342](https://github.com/spyder-ide/spyder/issues/9342))
* [PR 9960](https://github.com/spyder-ide/spyder/pull/9960) - PR: Do not add empty messages to history
* [PR 9944](https://github.com/spyder-ide/spyder/pull/9944) - PR: Add syntax highlighting to the debugger
* [PR 9943](https://github.com/spyder-ide/spyder/pull/9943) - PR: Add last line warnings/errors to their menu list ([9924](https://github.com/spyder-ide/spyder/issues/9924))
* [PR 9913](https://github.com/spyder-ide/spyder/pull/9913) - PR: Add unambiguous file names to Breakpoints pane
* [PR 9897](https://github.com/spyder-ide/spyder/pull/9897) - PR: Improvements to the completion widget ([9246](https://github.com/spyder-ide/spyder/issues/9246), [3181](https://github.com/spyder-ide/spyder/issues/3181), [2871](https://github.com/spyder-ide/spyder/issues/2871))
* [PR 9879](https://github.com/spyder-ide/spyder/pull/9879) - PR: Modifications for easier compatibility with Python 3.8
* [PR 9850](https://github.com/spyder-ide/spyder/pull/9850) - PR: Implement code snippets for our completion clients ([9568](https://github.com/spyder-ide/spyder/issues/9568))
* [PR 9720](https://github.com/spyder-ide/spyder/pull/9720) - PR: Make the width of thumbnails scrollbar resizable ([9747](https://github.com/spyder-ide/spyder/issues/9747))
* [PR 9566](https://github.com/spyder-ide/spyder/pull/9566) - PR: Correct auto-indent behaving in unexpected ways ([887](https://github.com/spyder-ide/spyder/issues/887), [7377](https://github.com/spyder-ide/spyder/issues/7377), [5606](https://github.com/spyder-ide/spyder/issues/5606))
* [PR 9343](https://github.com/spyder-ide/spyder/pull/9343) - PR: Use Jupyter comms to communicate between frontend and kernel
* [PR 9133](https://github.com/spyder-ide/spyder/pull/9133) - PR: Create generic switcher
* [PR 9014](https://github.com/spyder-ide/spyder/pull/9014) - PR: Use cell name in runcell to run it from the console and add functionality to debug cells ([9963](https://github.com/spyder-ide/spyder/issues/9963), [9361](https://github.com/spyder-ide/spyder/issues/9361))

In this release 69 pull requests were merged.


----


## Version 4.0beta4 (2019-08-02)

### Issues Closed

* [Issue 9945](https://github.com/spyder-ide/spyder/issues/9945) - Unify behavior to trigger elements edition (Variable Explorer) ([PR 9948](https://github.com/spyder-ide/spyder/pull/9948))
* [Issue 9915](https://github.com/spyder-ide/spyder/issues/9915) - Settings not getting applied ([PR 9932](https://github.com/spyder-ide/spyder/pull/9932))
* [Issue 9914](https://github.com/spyder-ide/spyder/issues/9914) - Preferences do not fully reset (transient.ini) ([PR 9917](https://github.com/spyder-ide/spyder/pull/9917))
* [Issue 9911](https://github.com/spyder-ide/spyder/issues/9911) - IPython console crashes when using netCDF4 ([PR 9925](https://github.com/spyder-ide/spyder/pull/9925))
* [Issue 9908](https://github.com/spyder-ide/spyder/issues/9908) - KeyError: 'willSave' when splitting the editor ([PR 9887](https://github.com/spyder-ide/spyder/pull/9887))
* [Issue 9893](https://github.com/spyder-ide/spyder/issues/9893) - Variable explorer search button keeps pressed after hiding the search field with Esc ([PR 9894](https://github.com/spyder-ide/spyder/pull/9894))
* [Issue 9891](https://github.com/spyder-ide/spyder/issues/9891) - Improve shortcuts table UI ([PR 9921](https://github.com/spyder-ide/spyder/pull/9921))
* [Issue 9878](https://github.com/spyder-ide/spyder/issues/9878) - Windows layout does not work properly ([PR 9903](https://github.com/spyder-ide/spyder/pull/9903))
* [Issue 9871](https://github.com/spyder-ide/spyder/issues/9871) - New automatic completion makes it hard to work ([PR 9895](https://github.com/spyder-ide/spyder/pull/9895))
* [Issue 9849](https://github.com/spyder-ide/spyder/issues/9849) - Control-click URL in tutorial causes ValueError ([PR 9857](https://github.com/spyder-ide/spyder/pull/9857))
* [Issue 9835](https://github.com/spyder-ide/spyder/issues/9835) - Variable explorer: Sorting not working ([PR 9840](https://github.com/spyder-ide/spyder/pull/9840))
* [Issue 9826](https://github.com/spyder-ide/spyder/issues/9826) - Dark theme is not applied to context menu appearing on plots in ipython console
* [Issue 9802](https://github.com/spyder-ide/spyder/issues/9802) - Add capability of splitting the Configuration manager files to use ([PR 9820](https://github.com/spyder-ide/spyder/pull/9820))
* [Issue 9801](https://github.com/spyder-ide/spyder/issues/9801) - Add a configuration manager to handle global user preferences and projects preferences ([PR 9820](https://github.com/spyder-ide/spyder/pull/9820))
* [Issue 9794](https://github.com/spyder-ide/spyder/issues/9794) - Fail to Launch Spyder Tutorial ([PR 9831](https://github.com/spyder-ide/spyder/pull/9831))
* [Issue 9785](https://github.com/spyder-ide/spyder/issues/9785) - Equation is not displayed in Help pane on Windows ([PR 9793](https://github.com/spyder-ide/spyder/pull/9793))
* [Issue 9763](https://github.com/spyder-ide/spyder/issues/9763) - Align plugin tabs to the left and center dockwidget tabs for all OSes ([PR 9808](https://github.com/spyder-ide/spyder/pull/9808))
* [Issue 9755](https://github.com/spyder-ide/spyder/issues/9755) - KeyError textDocumentSync when opening Spyder with a project ([PR 9887](https://github.com/spyder-ide/spyder/pull/9887))
* [Issue 9749](https://github.com/spyder-ide/spyder/issues/9749) - No curly brackets on Spyder 4.0.0b3 on macOS with a French keyboard ([PR 9813](https://github.com/spyder-ide/spyder/pull/9813))
* [Issue 9746](https://github.com/spyder-ide/spyder/issues/9746) - Plots viewer arrows a bit too small ([PR 9745](https://github.com/spyder-ide/spyder/pull/9745))
* [Issue 9721](https://github.com/spyder-ide/spyder/issues/9721) - Prevent LSP client to listen to external hosts ([PR 9728](https://github.com/spyder-ide/spyder/pull/9728))
* [Issue 9714](https://github.com/spyder-ide/spyder/issues/9714) - Dependencies dialog should provide correct package name ([PR 9789](https://github.com/spyder-ide/spyder/pull/9789))
* [Issue 9713](https://github.com/spyder-ide/spyder/issues/9713) - Replace cannot ignore case when using regular expressions ([PR 9716](https://github.com/spyder-ide/spyder/pull/9716))
* [Issue 9688](https://github.com/spyder-ide/spyder/issues/9688) - Replace selection in wrong tab on startup ([PR 9710](https://github.com/spyder-ide/spyder/pull/9710))
* [Issue 9685](https://github.com/spyder-ide/spyder/issues/9685) - Selected text unselected after "Replace selection" ([PR 9687](https://github.com/spyder-ide/spyder/pull/9687))
* [Issue 9669](https://github.com/spyder-ide/spyder/issues/9669) - Cannot use viewer for collections, arrays, dataframes that are attributes of general objects ([PR 9806](https://github.com/spyder-ide/spyder/pull/9806))
* [Issue 9659](https://github.com/spyder-ide/spyder/issues/9659) - Add inf support to array builder! ([PR 9777](https://github.com/spyder-ide/spyder/pull/9777))
* [Issue 9644](https://github.com/spyder-ide/spyder/issues/9644) - Pylint output window is not inheriting the dark theme
* [Issue 9611](https://github.com/spyder-ide/spyder/issues/9611) - Minimize icon is out of center ([PR 9784](https://github.com/spyder-ide/spyder/pull/9784))
* [Issue 9604](https://github.com/spyder-ide/spyder/issues/9604) - Analyze Button of Code Pane doesn't respect save before analysis Preference ([PR 9864](https://github.com/spyder-ide/spyder/pull/9864))
* [Issue 9594](https://github.com/spyder-ide/spyder/issues/9594) - Completion widget of the IPython console is not showed correctly with the dark theme
* [Issue 9561](https://github.com/spyder-ide/spyder/issues/9561) - Selected working directory in Preferences is not preserved after a restart ([PR 9792](https://github.com/spyder-ide/spyder/pull/9792))
* [Issue 9451](https://github.com/spyder-ide/spyder/issues/9451) - Editing or viewing a datetime looses miliseconds part of the datetime timestamp ([PR 9848](https://github.com/spyder-ide/spyder/pull/9848))
* [Issue 9008](https://github.com/spyder-ide/spyder/issues/9008) - Add current conda environment as status widget ([PR 9778](https://github.com/spyder-ide/spyder/pull/9778))
* [Issue 8834](https://github.com/spyder-ide/spyder/issues/8834) - Hard crash when opening Numpy array in VarExp  with one or more np.object fields ([PR 5260](https://github.com/spyder-ide/spyder/pull/5260))
* [Issue 8767](https://github.com/spyder-ide/spyder/issues/8767) - Icons not displaying in Options menus in macOS ([PR 8923](https://github.com/spyder-ide/spyder/pull/8923))
* [Issue 7960](https://github.com/spyder-ide/spyder/issues/7960) - Search for "whole words" does not return the correct number of matches ([PR 9716](https://github.com/spyder-ide/spyder/pull/9716))
* [Issue 6416](https://github.com/spyder-ide/spyder/issues/6416) - Bug: Replace Selection changes double backslashes to single backslashes ([PR 9708](https://github.com/spyder-ide/spyder/pull/9708))
* [Issue 5734](https://github.com/spyder-ide/spyder/issues/5734) - Shift-Tab does not remove final indent level for non 4-multiple indents (e.g. continuations) ([PR 9869](https://github.com/spyder-ide/spyder/pull/9869))
* [Issue 5491](https://github.com/spyder-ide/spyder/issues/5491) - Relative paths in workspace.ini to make projects moveable ([PR 9672](https://github.com/spyder-ide/spyder/pull/9672))
* [Issue 5062](https://github.com/spyder-ide/spyder/issues/5062) - Run in external system terminal doesn't work in macOS ([PR 9673](https://github.com/spyder-ide/spyder/pull/9673))
* [Issue 4067](https://github.com/spyder-ide/spyder/issues/4067) - Add fuzzy search functionality to the Variable Explorer ([PR 9384](https://github.com/spyder-ide/spyder/pull/9384))
* [Issue 1914](https://github.com/spyder-ide/spyder/issues/1914) - Automatically show code completion widget ([PR 9839](https://github.com/spyder-ide/spyder/pull/9839))

In this release 43 issues were closed.

### Pull Requests Merged

* [PR 9948](https://github.com/spyder-ide/spyder/pull/9948) - PR: Enable edition only with double click (Variable Explorer) ([9945](https://github.com/spyder-ide/spyder/issues/9945))
* [PR 9941](https://github.com/spyder-ide/spyder/pull/9941) - PR: Fix running bash scripts in our CIs
* [PR 9936](https://github.com/spyder-ide/spyder/pull/9936) - PR: Fix loading from old defaults and removing deprecated options
* [PR 9932](https://github.com/spyder-ide/spyder/pull/9932) - PR: Fix preferences not being set ([9915](https://github.com/spyder-ide/spyder/issues/9915))
* [PR 9931](https://github.com/spyder-ide/spyder/pull/9931) - PR: Add error message when reporting PyLS internal errors
* [PR 9929](https://github.com/spyder-ide/spyder/pull/9929) - PR: Increase minimum required version of qtconsole to 4.5.2
* [PR 9926](https://github.com/spyder-ide/spyder/pull/9926) - PR: Install a working build of Python 3.6 in Azure to fix our tests
* [PR 9925](https://github.com/spyder-ide/spyder/pull/9925) - PR: Fix wrapping calltip text for elements without signature in the IPython console ([9911](https://github.com/spyder-ide/spyder/issues/9911))
* [PR 9921](https://github.com/spyder-ide/spyder/pull/9921) - PR: Improve shortcuts entry in Preferences ([9891](https://github.com/spyder-ide/spyder/issues/9891))
* [PR 9917](https://github.com/spyder-ide/spyder/pull/9917) - PR: Add new config files to reset ([9914](https://github.com/spyder-ide/spyder/issues/9914))
* [PR 9904](https://github.com/spyder-ide/spyder/pull/9904) - PR: Remove unused imports
* [PR 9903](https://github.com/spyder-ide/spyder/pull/9903) - PR: Rescale window layout parameters ([9878](https://github.com/spyder-ide/spyder/issues/9878))
* [PR 9902](https://github.com/spyder-ide/spyder/pull/9902) - PR: Skip most IPython console tests in macOS and Python 2.7
* [PR 9895](https://github.com/spyder-ide/spyder/pull/9895) - PR: Disable automatic completions when spacebar or backspace are pressed ([9871](https://github.com/spyder-ide/spyder/issues/9871))
* [PR 9894](https://github.com/spyder-ide/spyder/pull/9894) - PR: Change the way to show/hide the search widget in the Variable Explorer ([9893](https://github.com/spyder-ide/spyder/issues/9893))
* [PR 9887](https://github.com/spyder-ide/spyder/pull/9887) - PR: Prevent errors when LSP servers don't specify some settings ([9908](https://github.com/spyder-ide/spyder/issues/9908), [9755](https://github.com/spyder-ide/spyder/issues/9755))
* [PR 9877](https://github.com/spyder-ide/spyder/pull/9877) - PR: Inherit style in the output dialog from code analysis
* [PR 9870](https://github.com/spyder-ide/spyder/pull/9870) - PR: Remove several deprecation warnings
* [PR 9869](https://github.com/spyder-ide/spyder/pull/9869) - PR: Improve unindent behavior ([5734](https://github.com/spyder-ide/spyder/issues/5734))
* [PR 9866](https://github.com/spyder-ide/spyder/pull/9866) - PR: Reenable sorting of keyboard shortcuts table after clearing filter text
* [PR 9864](https://github.com/spyder-ide/spyder/pull/9864) - PR: Made Analyze button respect "save before" setting ([9604](https://github.com/spyder-ide/spyder/issues/9604))
* [PR 9857](https://github.com/spyder-ide/spyder/pull/9857) - PR: Fix control-click URL in tutorial ValueError ([9849](https://github.com/spyder-ide/spyder/issues/9849))
* [PR 9852](https://github.com/spyder-ide/spyder/pull/9852) - PR: Make LSP tests to be run independently
* [PR 9848](https://github.com/spyder-ide/spyder/pull/9848) - PR: Add millisecond editing capabilities to variable explorer ([9451](https://github.com/spyder-ide/spyder/issues/9451))
* [PR 9840](https://github.com/spyder-ide/spyder/pull/9840) - PR: Fix sorting by column in the Variable Explorer ([9835](https://github.com/spyder-ide/spyder/issues/9835))
* [PR 9839](https://github.com/spyder-ide/spyder/pull/9839) - PR: Perform code completions on the fly ([1914](https://github.com/spyder-ide/spyder/issues/1914))
* [PR 9831](https://github.com/spyder-ide/spyder/pull/9831) - PR: Add rst files again to our tarballs ([9794](https://github.com/spyder-ide/spyder/issues/9794))
* [PR 9820](https://github.com/spyder-ide/spyder/pull/9820) - PR: Update and modernize config system to support multiple types of configurations ([9802](https://github.com/spyder-ide/spyder/issues/9802), [9801](https://github.com/spyder-ide/spyder/issues/9801))
* [PR 9818](https://github.com/spyder-ide/spyder/pull/9818) - PR: Increase maximum Pytest supported version
* [PR 9814](https://github.com/spyder-ide/spyder/pull/9814) - PR: Use text instead of key in the editor close quotes extension
* [PR 9813](https://github.com/spyder-ide/spyder/pull/9813) - PR: Use text instead of key in the editor close bracket extension ([9749](https://github.com/spyder-ide/spyder/issues/9749))
* [PR 9808](https://github.com/spyder-ide/spyder/pull/9808) - PR: Align plugin tabs to the left and center dockwidget ones ([9763](https://github.com/spyder-ide/spyder/issues/9763))
* [PR 9806](https://github.com/spyder-ide/spyder/pull/9806) - PR: Add edition capabilities for object's attributes in the Object Explorer ([9669](https://github.com/spyder-ide/spyder/issues/9669))
* [PR 9798](https://github.com/spyder-ide/spyder/pull/9798) - PR: Improve robustness of LSP tests
* [PR 9793](https://github.com/spyder-ide/spyder/pull/9793) - PR: Improve rendering of equations with MathJax on Windows in the Help pane ([9785](https://github.com/spyder-ide/spyder/issues/9785))
* [PR 9792](https://github.com/spyder-ide/spyder/pull/9792) - PR: Preserve selected working directory in Preferences after a restart ([9561](https://github.com/spyder-ide/spyder/issues/9561))
* [PR 9789](https://github.com/spyder-ide/spyder/pull/9789) - PR: Add package name to dependencies ([9714](https://github.com/spyder-ide/spyder/issues/9714))
* [PR 9787](https://github.com/spyder-ide/spyder/pull/9787) - PR: Remove backslash of path for import_data on Windows
* [PR 9784](https://github.com/spyder-ide/spyder/pull/9784) - PR: Update collapse/expand icons ([9611](https://github.com/spyder-ide/spyder/issues/9611))
* [PR 9779](https://github.com/spyder-ide/spyder/pull/9779) - PR: Remove CONF calls on widgets for issue reporter
* [PR 9778](https://github.com/spyder-ide/spyder/pull/9778) - PR: Add conda environment status widget ([9008](https://github.com/spyder-ide/spyder/issues/9008))
* [PR 9777](https://github.com/spyder-ide/spyder/pull/9777) - PR: Fix inf handling and generalize array builder for initial support on other languages ([9659](https://github.com/spyder-ide/spyder/issues/9659))
* [PR 9753](https://github.com/spyder-ide/spyder/pull/9753) - PR: Implement a completion plugin for Kite
* [PR 9748](https://github.com/spyder-ide/spyder/pull/9748) - PR: Fix stripping on return for strings
* [PR 9745](https://github.com/spyder-ide/spyder/pull/9745) - PR: Fix height of thumbnail scrollbar arrow buttons in the Plots plugin ([9746](https://github.com/spyder-ide/spyder/issues/9746))
* [PR 9741](https://github.com/spyder-ide/spyder/pull/9741) - PR: Add basic config dlg tests for plugins
* [PR 9740](https://github.com/spyder-ide/spyder/pull/9740) - PR: Keep preferences on top and give focus if the shortcut is called
* [PR 9728](https://github.com/spyder-ide/spyder/pull/9728) - PR: Prevent LSP listen to external hosts ([9721](https://github.com/spyder-ide/spyder/issues/9721))
* [PR 9716](https://github.com/spyder-ide/spyder/pull/9716) - PR: Fix several find/replace bugs ([9713](https://github.com/spyder-ide/spyder/issues/9713), [7960](https://github.com/spyder-ide/spyder/issues/7960))
* [PR 9712](https://github.com/spyder-ide/spyder/pull/9712) - PR: Changed issue numbers in code to links
* [PR 9711](https://github.com/spyder-ide/spyder/pull/9711) - PR: Remove some redundant icons
* [PR 9710](https://github.com/spyder-ide/spyder/pull/9710) - PR: Replace in correct file after startup ([9688](https://github.com/spyder-ide/spyder/issues/9688))
* [PR 9709](https://github.com/spyder-ide/spyder/pull/9709) - PR: Add tooltips for find next/previous buttons
* [PR 9708](https://github.com/spyder-ide/spyder/pull/9708) - PR: Fix replace in selection with backslashes ([6416](https://github.com/spyder-ide/spyder/issues/6416))
* [PR 9704](https://github.com/spyder-ide/spyder/pull/9704) - PR: Refactor completion architecture to support multiple sources
* [PR 9687](https://github.com/spyder-ide/spyder/pull/9687) - PR: Restored selection after replaced in selection ([9685](https://github.com/spyder-ide/spyder/issues/9685))
* [PR 9682](https://github.com/spyder-ide/spyder/pull/9682) - PR: Fix QComboBox with newer Qt versions and qdarkstyle ([191](https://github.com/ColinDuquesnoy/QDarkStyleSheet/issues/191))
* [PR 9679](https://github.com/spyder-ide/spyder/pull/9679) - PR: Convert LSPManager into a proper SpyderPlugin
* [PR 9673](https://github.com/spyder-ide/spyder/pull/9673) - PR: Add support to run files in external system terminal for macOS ([5062](https://github.com/spyder-ide/spyder/issues/5062))
* [PR 9672](https://github.com/spyder-ide/spyder/pull/9672) - PR: Save project recent files as relative paths in workspace.ini ([5491](https://github.com/spyder-ide/spyder/issues/5491))
* [PR 9384](https://github.com/spyder-ide/spyder/pull/9384) - PR: Add fuzzy search to the Variable Explorer ([4067](https://github.com/spyder-ide/spyder/issues/4067))
* [PR 8923](https://github.com/spyder-ide/spyder/pull/8923) - PR: Show icons in Options menus for macOS ([8767](https://github.com/spyder-ide/spyder/issues/8767))
* [PR 5260](https://github.com/spyder-ide/spyder/pull/5260) - PR: Add support for object arrays in the Variable Explorer ([8834](https://github.com/spyder-ide/spyder/issues/8834))

In this release 63 pull requests were closed.


----


## Version 4.0beta3 (2019-06-29)

### Issues Closed

* [Issue 9691](https://github.com/spyder-ide/spyder/issues/9691) - Can't set other Python interpreter ([PR 9706](https://github.com/spyder-ide/spyder/pull/9706))
* [Issue 9668](https://github.com/spyder-ide/spyder/issues/9668) - Hovers and calltips broken in the Editor ([PR 9670](https://github.com/spyder-ide/spyder/pull/9670))
* [Issue 9635](https://github.com/spyder-ide/spyder/issues/9635) - Make highlighting of errors and warning synchronized with errors and warnings popup show and hide ([PR 9636](https://github.com/spyder-ide/spyder/pull/9636))
* [Issue 9631](https://github.com/spyder-ide/spyder/issues/9631) - Highlighting errors and warnings wipe underlining of errors and warning. ([PR 9636](https://github.com/spyder-ide/spyder/pull/9636))
* [Issue 9628](https://github.com/spyder-ide/spyder/issues/9628) - Python LSP codeeditor configurations are being replaced each time a new LSP server is available ([PR 9633](https://github.com/spyder-ide/spyder/pull/9633))
* [Issue 9627](https://github.com/spyder-ide/spyder/issues/9627) - Add an option to turn off the underlining of errors and warnings in the Editor. ([PR 9630](https://github.com/spyder-ide/spyder/pull/9630))
* [Issue 9616](https://github.com/spyder-ide/spyder/issues/9616) - Lowercase in text out of pattern ([PR 9677](https://github.com/spyder-ide/spyder/pull/9677))
* [Issue 9614](https://github.com/spyder-ide/spyder/issues/9614) - URL awereness is broken in latest master ([PR 9625](https://github.com/spyder-ide/spyder/pull/9625))
* [Issue 9596](https://github.com/spyder-ide/spyder/issues/9596) - Some completion trigger characters supported by LSP servers are not used ([PR 9605](https://github.com/spyder-ide/spyder/pull/9605))
* [Issue 9578](https://github.com/spyder-ide/spyder/issues/9578) - WaitSpinner color under the dark theme should be white and suggestion for improving the look of the spinner ([PR 9584](https://github.com/spyder-ide/spyder/pull/9584))
* [Issue 9577](https://github.com/spyder-ide/spyder/issues/9577) - Remember what was selected in the "Search in" combo box of the "Find"pluggin ([PR 9586](https://github.com/spyder-ide/spyder/pull/9586))
* [Issue 9570](https://github.com/spyder-ide/spyder/issues/9570) - Error for calltip with empty signature ([PR 9582](https://github.com/spyder-ide/spyder/pull/9582))
* [Issue 9557](https://github.com/spyder-ide/spyder/issues/9557) - Traceback on Spyder launch when auto-opens previous project
* [Issue 9549](https://github.com/spyder-ide/spyder/issues/9549) - Create preferences setting to allow file associations ([PR 9504](https://github.com/spyder-ide/spyder/pull/9504))
* [Issue 9543](https://github.com/spyder-ide/spyder/issues/9543) - Wrap text in warnings and hover tips ([PR 9585](https://github.com/spyder-ide/spyder/pull/9585))
* [Issue 9542](https://github.com/spyder-ide/spyder/issues/9542) - Text written in Help pane gets automatically selected after match ([PR 9552](https://github.com/spyder-ide/spyder/pull/9552))
* [Issue 9531](https://github.com/spyder-ide/spyder/issues/9531) - Crash when trying to autocomplete with fallback ([PR 9563](https://github.com/spyder-ide/spyder/pull/9563))
* [Issue 9529](https://github.com/spyder-ide/spyder/issues/9529) - Calltips in IPython console are empty but work in qtconsole ([PR 9533](https://github.com/spyder-ide/spyder/pull/9533))
* [Issue 9522](https://github.com/spyder-ide/spyder/issues/9522) - KeyError in PyLS when opening projects ([PR 9482](https://github.com/spyder-ide/spyder/pull/9482))
* [Issue 9515](https://github.com/spyder-ide/spyder/issues/9515) - Bug with default actions for Ctrl+Tab and Ctrl+Backtab in the Editor ([PR 9517](https://github.com/spyder-ide/spyder/pull/9517))
* [Issue 9513](https://github.com/spyder-ide/spyder/issues/9513) - Improvements to URL awareness ([PR 9572](https://github.com/spyder-ide/spyder/pull/9572))
* [Issue 9512](https://github.com/spyder-ide/spyder/issues/9512) - Toggle uppercase/lowercase menu icons ([PR 9518](https://github.com/spyder-ide/spyder/pull/9518))
* [Issue 9511](https://github.com/spyder-ide/spyder/issues/9511) - Toggling docstring style linting in preferences doesn't work in macOS ([PR 9637](https://github.com/spyder-ide/spyder/pull/9637))
* [Issue 9506](https://github.com/spyder-ide/spyder/issues/9506) - The vertical position of the tab switcher dialog window is wrong in Spyder 4 ([PR 9507](https://github.com/spyder-ide/spyder/pull/9507))
* [Issue 9505](https://github.com/spyder-ide/spyder/issues/9505) - Removing all variables on remote kernels fails ([PR 9548](https://github.com/spyder-ide/spyder/pull/9548))
* [Issue 9501](https://github.com/spyder-ide/spyder/issues/9501) - Cursor is not restore properly in the Editor ([PR 9502](https://github.com/spyder-ide/spyder/pull/9502))
* [Issue 9497](https://github.com/spyder-ide/spyder/issues/9497) - Moving tabs in the Editor is slow ([PR 9569](https://github.com/spyder-ide/spyder/pull/9569))
* [Issue 9474](https://github.com/spyder-ide/spyder/issues/9474) - Symbol switcher throws exception after Enter ([PR 9524](https://github.com/spyder-ide/spyder/pull/9524))
* [Issue 9472](https://github.com/spyder-ide/spyder/issues/9472) - Restore underlining errors and warnings in the Editor ([PR 9597](https://github.com/spyder-ide/spyder/pull/9597))
* [Issue 9469](https://github.com/spyder-ide/spyder/issues/9469) - EditorStack file and symbol switcher not working ([PR 9521](https://github.com/spyder-ide/spyder/pull/9521))
* [Issue 9463](https://github.com/spyder-ide/spyder/issues/9463) - Add simplified Github Issue/PR URL recognition ([PR 9473](https://github.com/spyder-ide/spyder/pull/9473))
* [Issue 9457](https://github.com/spyder-ide/spyder/issues/9457) - Not able to create a new breakpoint after a collapsed function ([PR 9555](https://github.com/spyder-ide/spyder/pull/9555))
* [Issue 9449](https://github.com/spyder-ide/spyder/issues/9449) - spyder 4 startup error ([PR 9467](https://github.com/spyder-ide/spyder/pull/9467))
* [Issue 9443](https://github.com/spyder-ide/spyder/issues/9443) - Code cells that fill the whole screen lose their background highlight ([PR 9444](https://github.com/spyder-ide/spyder/pull/9444))
* [Issue 9442](https://github.com/spyder-ide/spyder/issues/9442) - Information icon in File Switcher is not themed under the dark theme ([PR 9477](https://github.com/spyder-ide/spyder/pull/9477))
* [Issue 9439](https://github.com/spyder-ide/spyder/issues/9439) - Under the dark theme, the right warning display sidebar is not offset to match the scroll bar position ([PR 9450](https://github.com/spyder-ide/spyder/pull/9450))
* [Issue 9434](https://github.com/spyder-ide/spyder/issues/9434) - Code folding does not fold correctly when there are blank lines ([PR 9526](https://github.com/spyder-ide/spyder/pull/9526))
* [Issue 9425](https://github.com/spyder-ide/spyder/issues/9425) - Changing LSP-related settings when another Spyder instance is open stops LSP from working ([PR 9468](https://github.com/spyder-ide/spyder/pull/9468))
* [Issue 9405](https://github.com/spyder-ide/spyder/issues/9405) - Zoom buttons state and scaling percentage update when "Fits plot to window" is activated ([PR 9407](https://github.com/spyder-ide/spyder/pull/9407))
* [Issue 9395](https://github.com/spyder-ide/spyder/issues/9395) - using BeautifulSoup4 to webscrape wikipedia ([PR 9401](https://github.com/spyder-ide/spyder/pull/9401))
* [Issue 9393](https://github.com/spyder-ide/spyder/issues/9393) - Hover Tooltips make change focus off the spyder main window on Linux ([PR 9394](https://github.com/spyder-ide/spyder/pull/9394))
* [Issue 9390](https://github.com/spyder-ide/spyder/issues/9390) - Error when launching Preferences in Chinese ([PR 9571](https://github.com/spyder-ide/spyder/pull/9571))
* [Issue 9381](https://github.com/spyder-ide/spyder/issues/9381) - Overwritten file permissions on save ([PR 9550](https://github.com/spyder-ide/spyder/pull/9550))
* [Issue 9368](https://github.com/spyder-ide/spyder/issues/9368) - Resizing plot panes does not resize the content ([PR 9386](https://github.com/spyder-ide/spyder/pull/9386))
* [Issue 9357](https://github.com/spyder-ide/spyder/issues/9357) - Help Panel: LaTeX rendering is unreadable when using dark theme ([PR 9377](https://github.com/spyder-ide/spyder/pull/9377))
* [Issue 9303](https://github.com/spyder-ide/spyder/issues/9303) - Single click to open files doesn't work in project explorer ([PR 9402](https://github.com/spyder-ide/spyder/pull/9402))
* [Issue 9265](https://github.com/spyder-ide/spyder/issues/9265) - Autosaves are created for unmodified files and not removed on close with split Editor panes ([PR 9485](https://github.com/spyder-ide/spyder/pull/9485))
* [Issue 9247](https://github.com/spyder-ide/spyder/issues/9247) - Improve messages of code analysis tooltip ([PR 9422](https://github.com/spyder-ide/spyder/pull/9422))
* [Issue 9194](https://github.com/spyder-ide/spyder/issues/9194) - Pass language from console and editor on calltip call ([PR 9290](https://github.com/spyder-ide/spyder/pull/9290))
* [Issue 9085](https://github.com/spyder-ide/spyder/issues/9085) - Default code cell name  ([PR 9082](https://github.com/spyder-ide/spyder/pull/9082))
* [Issue 9007](https://github.com/spyder-ide/spyder/issues/9007) - Connect our LSP client to the workspace functionality provided by the PyLS. ([PR 9482](https://github.com/spyder-ide/spyder/pull/9482))
* [Issue 8564](https://github.com/spyder-ide/spyder/issues/8564) - New line creates whitespaces that conflict with PEP 8 ([PR 8734](https://github.com/spyder-ide/spyder/pull/8734))
* [Issue 8371](https://github.com/spyder-ide/spyder/issues/8371) - Support color scheme Sublime Text Monokai Extended (and more) ([PR 8381](https://github.com/spyder-ide/spyder/pull/8381))
* [Issue 8076](https://github.com/spyder-ide/spyder/issues/8076) - Incorrect custom shortcut displayed in menus for Run Cell command ([PR 9458](https://github.com/spyder-ide/spyder/pull/9458))
* [Issue 8068](https://github.com/spyder-ide/spyder/issues/8068) - Fully implement Spyder's new dark theme
* [Issue 8000](https://github.com/spyder-ide/spyder/issues/8000) - IndexError for some shortcuts in the Editor ([PR 9523](https://github.com/spyder-ide/spyder/pull/9523))
* [Issue 7976](https://github.com/spyder-ide/spyder/issues/7976) - Automatic Updates on Outline Explorer ([PR 9082](https://github.com/spyder-ide/spyder/pull/9082))
* [Issue 6055](https://github.com/spyder-ide/spyder/issues/6055) - Ctrl-Tab doesn't switch between Editor files in macOS ([PR 9400](https://github.com/spyder-ide/spyder/pull/9400))
* [Issue 1536](https://github.com/spyder-ide/spyder/issues/1536) - Pylint should follow the opened file ([PR 9430](https://github.com/spyder-ide/spyder/pull/9430))
* [Issue 885](https://github.com/spyder-ide/spyder/issues/885) - Outline Explorer: Highlight current class/method automatically ([PR 9219](https://github.com/spyder-ide/spyder/pull/9219))
* [Issue 558](https://github.com/spyder-ide/spyder/issues/558) - Add Object Explorer for exploring an object's properties ([PR 8852](https://github.com/spyder-ide/spyder/pull/8852))

In this release 61 issues were closed.

### Pull Requests Merged

* [PR 9706](https://github.com/spyder-ide/spyder/pull/9706) - PR: Fixes content type attribute error for global config dialog ([9691](https://github.com/spyder-ide/spyder/issues/9691))
* [PR 9677](https://github.com/spyder-ide/spyder/pull/9677) - PR: Fix texts out of pattern in Preferences ([9616](https://github.com/spyder-ide/spyder/issues/9616))
* [PR 9670](https://github.com/spyder-ide/spyder/pull/9670) - PR: Fix formating of text/documentation in tooltips and calltips ([9668](https://github.com/spyder-ide/spyder/issues/9668))
* [PR 9667](https://github.com/spyder-ide/spyder/pull/9667) - PR: Demand PyLS 0.27+ and disable Pylint linting
* [PR 9660](https://github.com/spyder-ide/spyder/pull/9660) - PR: Disable autosave if not running in single instance mode
* [PR 9657](https://github.com/spyder-ide/spyder/pull/9657) - PR: Update Contributing guide
* [PR 9646](https://github.com/spyder-ide/spyder/pull/9646) - PR: Avoid that code analysis tree collapses on selection
* [PR 9642](https://github.com/spyder-ide/spyder/pull/9642) - PR: Fix EditorPluginExample test
* [PR 9637](https://github.com/spyder-ide/spyder/pull/9637) - PR: Fix checkboxes loading from config file in macOS ([9511](https://github.com/spyder-ide/spyder/issues/9511))
* [PR 9636](https://github.com/spyder-ide/spyder/pull/9636) - PR: Fix and improvement to the highlighting and underlining of errors and warnings in the Editor ([9635](https://github.com/spyder-ide/spyder/issues/9635), [9631](https://github.com/spyder-ide/spyder/issues/9631))
* [PR 9634](https://github.com/spyder-ide/spyder/pull/9634) - PR: Downgrade Jedi in our CIs because the latest version broke the PyLS
* [PR 9633](https://github.com/spyder-ide/spyder/pull/9633) - PR: Fix project workspace startup ([9628](https://github.com/spyder-ide/spyder/issues/9628))
* [PR 9630](https://github.com/spyder-ide/spyder/pull/9630) - PR: Add an option to turn on/off the underlining of errors and warnings in the Editor.  ([9627](https://github.com/spyder-ide/spyder/issues/9627))
* [PR 9625](https://github.com/spyder-ide/spyder/pull/9625) - PR: Fix url awareness missing variable and add regression test ([9614](https://github.com/spyder-ide/spyder/issues/9614))
* [PR 9605](https://github.com/spyder-ide/spyder/pull/9605) - PR: Enable other LSP completion characters ([9596](https://github.com/spyder-ide/spyder/issues/9596))
* [PR 9597](https://github.com/spyder-ide/spyder/pull/9597) - PR: Restore underlining errors and warnings in the Editor ([9472](https://github.com/spyder-ide/spyder/issues/9472))
* [PR 9595](https://github.com/spyder-ide/spyder/pull/9595) - PR: Send fallback completions to the end of the completion widget
* [PR 9586](https://github.com/spyder-ide/spyder/pull/9586) - PR: Add and get "Search in" combo box index of the "Find" plugin from/to config ([9577](https://github.com/spyder-ide/spyder/issues/9577))
* [PR 9585](https://github.com/spyder-ide/spyder/pull/9585) - PR: Wrap text in tooltips, hints and calltips ([9543](https://github.com/spyder-ide/spyder/issues/9543))
* [PR 9584](https://github.com/spyder-ide/spyder/pull/9584) - PR: Style improvement to the wait spinner used in the Find plugin ([9578](https://github.com/spyder-ide/spyder/issues/9578))
* [PR 9582](https://github.com/spyder-ide/spyder/pull/9582) - PR: Add validation for empty signature while getting calltip in the IPython Console ([9570](https://github.com/spyder-ide/spyder/issues/9570))
* [PR 9572](https://github.com/spyder-ide/spyder/pull/9572) - PR: URL awareness improvements ([9513](https://github.com/spyder-ide/spyder/issues/9513))
* [PR 9571](https://github.com/spyder-ide/spyder/pull/9571) - PR: Fix error when launching Preferences in Chinese ([9390](https://github.com/spyder-ide/spyder/issues/9390))
* [PR 9569](https://github.com/spyder-ide/spyder/pull/9569) - PR: Add a worker to VCSStatus for getting Git active branch, state, branches (plus tags) ([9497](https://github.com/spyder-ide/spyder/issues/9497))
* [PR 9563](https://github.com/spyder-ide/spyder/pull/9563) - PR: Fix segfault when getting fallback completions ([9531](https://github.com/spyder-ide/spyder/issues/9531))
* [PR 9560](https://github.com/spyder-ide/spyder/pull/9560) - PR: Add desktop.ini file to .gitignore
* [PR 9556](https://github.com/spyder-ide/spyder/pull/9556) - PR: Remove extra padding around plots and variable explorer plugins
* [PR 9555](https://github.com/spyder-ide/spyder/pull/9555) - PR: Fix line count when code is collapsed ([9457](https://github.com/spyder-ide/spyder/issues/9457))
* [PR 9552](https://github.com/spyder-ide/spyder/pull/9552) - PR: Don't stay with selected text when it's found valid in the Help pane ([9542](https://github.com/spyder-ide/spyder/issues/9542))
* [PR 9550](https://github.com/spyder-ide/spyder/pull/9550) - PR: Preserve file permissions when saving in the editor ([9381](https://github.com/spyder-ide/spyder/issues/9381))
* [PR 9548](https://github.com/spyder-ide/spyder/pull/9548) - PR: Enclose kernel_env assignment in a try/except ([9505](https://github.com/spyder-ide/spyder/issues/9505))
* [PR 9541](https://github.com/spyder-ide/spyder/pull/9541) - PR: Watch a project file tree for changes
* [PR 9535](https://github.com/spyder-ide/spyder/pull/9535) - PR: Fix calltip size on linux
* [PR 9533](https://github.com/spyder-ide/spyder/pull/9533) - PR: Add documentation element to calltips in the IPython Console ([9529](https://github.com/spyder-ide/spyder/issues/9529))
* [PR 9526](https://github.com/spyder-ide/spyder/pull/9526) - PR: Correct indentation folding cases ([9434](https://github.com/spyder-ide/spyder/issues/9434))
* [PR 9524](https://github.com/spyder-ide/spyder/pull/9524) - PR: Add validation for Enter in the File Switcher ([9474](https://github.com/spyder-ide/spyder/issues/9474))
* [PR 9523](https://github.com/spyder-ide/spyder/pull/9523) - PR: Fix Prev/Next cursor position for unsaved files ([8000](https://github.com/spyder-ide/spyder/issues/8000))
* [PR 9521](https://github.com/spyder-ide/spyder/pull/9521) - PR: Fix Fileswitcher for 'EditorStack' instances ([9469](https://github.com/spyder-ide/spyder/issues/9469))
* [PR 9518](https://github.com/spyder-ide/spyder/pull/9518) - PR: Add icons to toggle uppercase/lowercase menu action ([9512](https://github.com/spyder-ide/spyder/issues/9512))
* [PR 9517](https://github.com/spyder-ide/spyder/pull/9517) - PR: Prevent indentation/unindentation in the CodeEditor when Ctrl+Tab or Ctrl+Shift+Tab is pressed ([9515](https://github.com/spyder-ide/spyder/issues/9515))
* [PR 9507](https://github.com/spyder-ide/spyder/pull/9507) - PR: Fix editor tab switcher vertical position ([9506](https://github.com/spyder-ide/spyder/issues/9506))
* [PR 9504](https://github.com/spyder-ide/spyder/pull/9504) - PR: Add support for configurable file extension associations ([9549](https://github.com/spyder-ide/spyder/issues/9549))
* [PR 9502](https://github.com/spyder-ide/spyder/pull/9502) - PR: Restore cursor properly in the Editor after a key release or a focus out event. ([9501](https://github.com/spyder-ide/spyder/issues/9501))
* [PR 9494](https://github.com/spyder-ide/spyder/pull/9494) - PR: Remove cell separator detection from syntax highlighting and use oedata instead ([9443](https://github.com/spyder-ide/spyder/issues/9443))
* [PR 9485](https://github.com/spyder-ide/spyder/pull/9485) - PR: Use file contents to decide when to autosave ([9265](https://github.com/spyder-ide/spyder/issues/9265))
* [PR 9482](https://github.com/spyder-ide/spyder/pull/9482) - PR: Add support for LSP workspace calls ([9522](https://github.com/spyder-ide/spyder/issues/9522), [9007](https://github.com/spyder-ide/spyder/issues/9007))
* [PR 9478](https://github.com/spyder-ide/spyder/pull/9478) - PR: Add icon for binary files
* [PR 9477](https://github.com/spyder-ide/spyder/pull/9477) - PR: Fix background color of information icon in File Switcher ([9442](https://github.com/spyder-ide/spyder/issues/9442))
* [PR 9473](https://github.com/spyder-ide/spyder/pull/9473) - PR: Add uri hover and click detection for shorthand github/bitbucket/gitlab issues ([9463](https://github.com/spyder-ide/spyder/issues/9463))
* [PR 9468](https://github.com/spyder-ide/spyder/pull/9468) - PR: Disable LSP services on CodeEditors before restarting LSP client ([9425](https://github.com/spyder-ide/spyder/issues/9425))
* [PR 9467](https://github.com/spyder-ide/spyder/pull/9467) - PR: Handle git not found error and add regression test ([9449](https://github.com/spyder-ide/spyder/issues/9449))
* [PR 9459](https://github.com/spyder-ide/spyder/pull/9459) - PR: Autocomplete only left part of selected word.
* [PR 9458](https://github.com/spyder-ide/spyder/pull/9458) - PR: Fix custom shortcut not displayed in menu entries for "Run cell" and "Run cell and advance"  ([8076](https://github.com/spyder-ide/spyder/issues/8076))
* [PR 9450](https://github.com/spyder-ide/spyder/pull/9450) - PR: Fix editor scrollflag area position and height under the dark theme ([9439](https://github.com/spyder-ide/spyder/issues/9439))
* [PR 9444](https://github.com/spyder-ide/spyder/pull/9444) - PR: Fix code cells that fill the whole screen lose their background highlight ([9443](https://github.com/spyder-ide/spyder/issues/9443))
* [PR 9437](https://github.com/spyder-ide/spyder/pull/9437) - PR: Try to reduce some flakiness in our tests
* [PR 9430](https://github.com/spyder-ide/spyder/pull/9430) - PR: Make Code Analysis pane follow the currently active file ([1536](https://github.com/spyder-ide/spyder/issues/1536))
* [PR 9422](https://github.com/spyder-ide/spyder/pull/9422) - PR: Enhance the display of warnings and errors  ([9247](https://github.com/spyder-ide/spyder/issues/9247))
* [PR 9417](https://github.com/spyder-ide/spyder/pull/9417) - PR: Reorganize global fixtures in conftest files
* [PR 9410](https://github.com/spyder-ide/spyder/pull/9410) - PR: Minor layout improvement to the "Appearance" preference panel.
* [PR 9407](https://github.com/spyder-ide/spyder/pull/9407) - PR: Disable zooming and update displayed scaling percent when "Fits plot to window" is checked ([9405](https://github.com/spyder-ide/spyder/issues/9405))
* [PR 9404](https://github.com/spyder-ide/spyder/pull/9404) - PR: Add a code of conduct
* [PR 9402](https://github.com/spyder-ide/spyder/pull/9402) - PR: Connect project explorer to file explorer when "Single click to open" option is updated ([9303](https://github.com/spyder-ide/spyder/issues/9303))
* [PR 9401](https://github.com/spyder-ide/spyder/pull/9401) - PR: Fix signature format for dict kwargs ([9395](https://github.com/spyder-ide/spyder/issues/9395))
* [PR 9400](https://github.com/spyder-ide/spyder/pull/9400) - PR: Fix Ctrl+Tab to cycle files on the editor ([6055](https://github.com/spyder-ide/spyder/issues/6055))
* [PR 9394](https://github.com/spyder-ide/spyder/pull/9394) - PR: Change calltip from tool to tooltip on linux ([9393](https://github.com/spyder-ide/spyder/issues/9393))
* [PR 9387](https://github.com/spyder-ide/spyder/pull/9387) - PR: Underline URIs in the Editor and enable opening them by Ctrl+click
* [PR 9386](https://github.com/spyder-ide/spyder/pull/9386) - PR: Resize plot when Plots pane is resized and "Fits plots to window" is checked. ([9368](https://github.com/spyder-ide/spyder/issues/9368))
* [PR 9385](https://github.com/spyder-ide/spyder/pull/9385) - PR: Improve LSP preferences UI
* [PR 9382](https://github.com/spyder-ide/spyder/pull/9382) - PR: Don't package our tests in our wheels and tarball
* [PR 9380](https://github.com/spyder-ide/spyder/pull/9380) - PR: Fix not selecting the right LSP language in "Other languages" tab
* [PR 9377](https://github.com/spyder-ide/spyder/pull/9377) - PR: Update MathJax to its latest version ([9357](https://github.com/spyder-ide/spyder/issues/9357))
* [PR 9371](https://github.com/spyder-ide/spyder/pull/9371) - PR: Fix test_get_git_refs when run by Travis on tags
* [PR 9364](https://github.com/spyder-ide/spyder/pull/9364) - PR: Move test_calltip to test_hints_and_calltips.py
* [PR 9363](https://github.com/spyder-ide/spyder/pull/9363) - PR: Refactor code in LSPManager to not imply that we're still passing signals around
* [PR 9362](https://github.com/spyder-ide/spyder/pull/9362) - PR: Show nicer close icons on macOS when hovering on tabs
* [PR 9320](https://github.com/spyder-ide/spyder/pull/9320) - PR: Reimplement fallback plugin for code completions
* [PR 9290](https://github.com/spyder-ide/spyder/pull/9290) - PR: Correctly handle programming language in calltips ([9194](https://github.com/spyder-ide/spyder/issues/9194))
* [PR 9274](https://github.com/spyder-ide/spyder/pull/9274) - PR: Shutdown running kernels more forcefully so they close faster
* [PR 9249](https://github.com/spyder-ide/spyder/pull/9249) - PR: Add stdio LSP transport client
* [PR 9226](https://github.com/spyder-ide/spyder/pull/9226) - PR: Add SpyderPlugin class to public API
* [PR 9219](https://github.com/spyder-ide/spyder/pull/9219) - PR: Highlight current entry in the Outline Explorer and update it on-the-fly ([885](https://github.com/spyder-ide/spyder/issues/885))
* [PR 9082](https://github.com/spyder-ide/spyder/pull/9082) - PR: Use blocks to identify lines and add unique cell names ([9085](https://github.com/spyder-ide/spyder/issues/9085), [7976](https://github.com/spyder-ide/spyder/issues/7976))
* [PR 8852](https://github.com/spyder-ide/spyder/pull/8852) - PR: Add an Object Explorer to the Variable Explorer ([558](https://github.com/spyder-ide/spyder/issues/558))
* [PR 8768](https://github.com/spyder-ide/spyder/pull/8768) - PR: Change IPython Console icon
* [PR 8734](https://github.com/spyder-ide/spyder/pull/8734) - PR: Remove blanks if no content is added in a line and Enter is pressed to create a new line ([8564](https://github.com/spyder-ide/spyder/issues/8564))
* [PR 8381](https://github.com/spyder-ide/spyder/pull/8381) - PR: Add some color schemes from Eclipse ([8371](https://github.com/spyder-ide/spyder/issues/8371))

In this release 87 pull requests were closed.


----


## Version 4.0beta2 (2019-05-19)

### Issues Closed

* [Issue 9341](https://github.com/spyder-ide/spyder/issues/9341) - RuntimeError after closing a split editor ([PR 9345](https://github.com/spyder-ide/spyder/pull/9345))
* [Issue 9332](https://github.com/spyder-ide/spyder/issues/9332) - Search is broken in file switcher and produces exception due to indentation error ([PR 9333](https://github.com/spyder-ide/spyder/pull/9333))
* [Issue 9323](https://github.com/spyder-ide/spyder/issues/9323) - Close brackets or close quotes doesn't update the LSP ([PR 9324](https://github.com/spyder-ide/spyder/pull/9324))
* [Issue 9311](https://github.com/spyder-ide/spyder/issues/9311) - Some issues with calltips and hovers ([PR 9322](https://github.com/spyder-ide/spyder/pull/9322))
* [Issue 9299](https://github.com/spyder-ide/spyder/issues/9299) - Code style warnings are not updated in the Editor after "Delete line" shortcut ([PR 9300](https://github.com/spyder-ide/spyder/pull/9300))
* [Issue 9298](https://github.com/spyder-ide/spyder/issues/9298) - About dialog on OSX is too big and bolded ([PR 9306](https://github.com/spyder-ide/spyder/pull/9306))
* [Issue 9294](https://github.com/spyder-ide/spyder/issues/9294) - Error when getting hover of "dict" ([PR 9301](https://github.com/spyder-ide/spyder/pull/9301))
* [Issue 9287](https://github.com/spyder-ide/spyder/issues/9287) - Hovers, tooltips and calltips are shown at the wrong position on Linux ([PR 9293](https://github.com/spyder-ide/spyder/pull/9293))
* [Issue 9281](https://github.com/spyder-ide/spyder/issues/9281) - Avoid the possibility of duplicate preferences dialogs ([PR 9280](https://github.com/spyder-ide/spyder/pull/9280))
* [Issue 9273](https://github.com/spyder-ide/spyder/issues/9273) - Autocomplete choice 1 option ([PR 9260](https://github.com/spyder-ide/spyder/pull/9260))
* [Issue 9269](https://github.com/spyder-ide/spyder/issues/9269) - Autocompletion doesn't update ([PR 9260](https://github.com/spyder-ide/spyder/pull/9260))
* [Issue 9268](https://github.com/spyder-ide/spyder/issues/9268) - Autocompletion appears right before return and change the text ([PR 9260](https://github.com/spyder-ide/spyder/pull/9260))
* [Issue 9267](https://github.com/spyder-ide/spyder/issues/9267) - Auto completion widget shows even after line return ([PR 9260](https://github.com/spyder-ide/spyder/pull/9260))
* [Issue 9257](https://github.com/spyder-ide/spyder/issues/9257) - Spyder steals my letters! ([PR 9260](https://github.com/spyder-ide/spyder/pull/9260))
* [Issue 9248](https://github.com/spyder-ide/spyder/issues/9248) - Appearance preferences for syntax highlighting with dark theme look weird ([PR 9348](https://github.com/spyder-ide/spyder/pull/9348))
* [Issue 9245](https://github.com/spyder-ide/spyder/issues/9245) - Improve dialog to start servers for other languages
* [Issue 9242](https://github.com/spyder-ide/spyder/issues/9242) - Remove unused Pyflakes and pep8 checks ([PR 9243](https://github.com/spyder-ide/spyder/pull/9243))
* [Issue 9236](https://github.com/spyder-ide/spyder/issues/9236) - Opening a new editor window results in an error ([PR 9282](https://github.com/spyder-ide/spyder/pull/9282))
* [Issue 9211](https://github.com/spyder-ide/spyder/issues/9211) - Show PyLS server errors in Spyder's error report dialog ([PR 9266](https://github.com/spyder-ide/spyder/pull/9266))
* [Issue 9209](https://github.com/spyder-ide/spyder/issues/9209) - Setting ignore rules for Pycodestyle is not working ([PR 9231](https://github.com/spyder-ide/spyder/pull/9231))
* [Issue 9208](https://github.com/spyder-ide/spyder/issues/9208) - Hide debugger panel for files that are not Python ones ([PR 9289](https://github.com/spyder-ide/spyder/pull/9289))
* [Issue 9207](https://github.com/spyder-ide/spyder/issues/9207) - Rename plugins for a simpler, less crowded interface ([PR 9237](https://github.com/spyder-ide/spyder/pull/9237))
* [Issue 9195](https://github.com/spyder-ide/spyder/issues/9195) - Cannot connect to an external PyLS server ([PR 9203](https://github.com/spyder-ide/spyder/pull/9203))
* [Issue 9187](https://github.com/spyder-ide/spyder/issues/9187) - Define Hint behavior ([PR 9191](https://github.com/spyder-ide/spyder/pull/9191))
* [Issue 9173](https://github.com/spyder-ide/spyder/issues/9173) - Error when closing a panel ([PR 9175](https://github.com/spyder-ide/spyder/pull/9175))
* [Issue 9151](https://github.com/spyder-ide/spyder/issues/9151) - Add icons for Latex file type ([PR 9228](https://github.com/spyder-ide/spyder/pull/9228))
* [Issue 9150](https://github.com/spyder-ide/spyder/issues/9150) - Improve the "Open recent" menu ([PR 9230](https://github.com/spyder-ide/spyder/pull/9230))
* [Issue 9120](https://github.com/spyder-ide/spyder/issues/9120) - QDarkStyle issue on Mac for status bar ([PR 9121](https://github.com/spyder-ide/spyder/pull/9121))
* [Issue 9044](https://github.com/spyder-ide/spyder/issues/9044) - Editor text is all shown in bold text ([PR 9046](https://github.com/spyder-ide/spyder/pull/9046))
* [Issue 9006](https://github.com/spyder-ide/spyder/issues/9006) - Shorten status bar widgets size ([PR 9010](https://github.com/spyder-ide/spyder/pull/9010))
* [Issue 8985](https://github.com/spyder-ide/spyder/issues/8985) - Reconnect warning menu with PyLS output ([PR 9011](https://github.com/spyder-ide/spyder/pull/9011))
* [Issue 8930](https://github.com/spyder-ide/spyder/issues/8930) - Single click to interact with items in Project Explorer, rather than double-click ([PR 9024](https://github.com/spyder-ide/spyder/pull/9024))
* [Issue 8865](https://github.com/spyder-ide/spyder/issues/8865) - LSP services don't work in any split Editor pane but the first (left/topmost) one ([PR 9075](https://github.com/spyder-ide/spyder/pull/9075))
* [Issue 8859](https://github.com/spyder-ide/spyder/issues/8859) - Completion popup menu isn't dismissed after typing a delimiter and causes unexpected behavior ([PR 9057](https://github.com/spyder-ide/spyder/pull/9057))
* [Issue 8846](https://github.com/spyder-ide/spyder/issues/8846) - Errors in the debugger panel and stuck indicator after ending the debugging ([PR 8854](https://github.com/spyder-ide/spyder/pull/8854))
* [Issue 8828](https://github.com/spyder-ide/spyder/issues/8828) - Tests are failing with PyLS 0.23+ ([PR 8972](https://github.com/spyder-ide/spyder/pull/8972))
* [Issue 8816](https://github.com/spyder-ide/spyder/issues/8816) - Deleting a server in the LSP preferences pane when only one is present raises exceptions ([PR 8647](https://github.com/spyder-ide/spyder/pull/8647))
* [Issue 8815](https://github.com/spyder-ide/spyder/issues/8815) - Error in code completion when case-sensitive completions are disabled ([PR 9104](https://github.com/spyder-ide/spyder/pull/9104))
* [Issue 8813](https://github.com/spyder-ide/spyder/issues/8813) - Errors triggered when saving "Saving as" a file in latest master ([PR 8932](https://github.com/spyder-ide/spyder/pull/8932))
* [Issue 8749](https://github.com/spyder-ide/spyder/issues/8749) - Closing moved files creates IndexError ([PR 8782](https://github.com/spyder-ide/spyder/pull/8782))
* [Issue 8727](https://github.com/spyder-ide/spyder/issues/8727) - autocomplete fails to select an option in the list ([PR 8724](https://github.com/spyder-ide/spyder/pull/8724))
* [Issue 8723](https://github.com/spyder-ide/spyder/issues/8723) - autocomplete fails when pressing tab too quickly ([PR 8724](https://github.com/spyder-ide/spyder/pull/8724))
* [Issue 8655](https://github.com/spyder-ide/spyder/issues/8655) - Autosave not removed when closing a changed file without saving ([PR 8733](https://github.com/spyder-ide/spyder/pull/8733))
* [Issue 8654](https://github.com/spyder-ide/spyder/issues/8654) - Text files are wrongly autosaved when opened without changing them ([PR 9205](https://github.com/spyder-ide/spyder/pull/9205))
* [Issue 8641](https://github.com/spyder-ide/spyder/issues/8641) - Assign a keyboard shortcut for "next figure" and "previous figure" of the Plots pane ([PR 8643](https://github.com/spyder-ide/spyder/pull/8643))
* [Issue 8640](https://github.com/spyder-ide/spyder/issues/8640) - Assign a keyboard shortcut to switch to the Plots pane ([PR 9036](https://github.com/spyder-ide/spyder/pull/9036))
* [Issue 8631](https://github.com/spyder-ide/spyder/issues/8631) - Cannot restore files between different drives in Windows ([PR 8650](https://github.com/spyder-ide/spyder/pull/8650))
* [Issue 8628](https://github.com/spyder-ide/spyder/issues/8628) - Autocomplete replace "import" keyword ([PR 8648](https://github.com/spyder-ide/spyder/pull/8648))
* [Issue 8626](https://github.com/spyder-ide/spyder/issues/8626) - Display warning about rendering of plots below the new IPython prompt ([PR 8627](https://github.com/spyder-ide/spyder/pull/8627))
* [Issue 8613](https://github.com/spyder-ide/spyder/issues/8613) - Use new functionality in Qt 5.6 to resize dockwidgets programatically ([PR 9155](https://github.com/spyder-ide/spyder/pull/9155))
* [Issue 8609](https://github.com/spyder-ide/spyder/issues/8609) - Disabling Automatic Code Completion makes completion, analysis and calltips stop working permanently ([PR 9104](https://github.com/spyder-ide/spyder/pull/9104))
* [Issue 8603](https://github.com/spyder-ide/spyder/issues/8603) - The command line does not appear in ipython console after the warning about rendering of plots is displayed. ([PR 8604](https://github.com/spyder-ide/spyder/pull/8604))
* [Issue 8579](https://github.com/spyder-ide/spyder/issues/8579) - Error when triggering completion in the Internal Console ([PR 8593](https://github.com/spyder-ide/spyder/pull/8593))
* [Issue 8567](https://github.com/spyder-ide/spyder/issues/8567) - Deleting a folder which contains a sub-folder(s) raises an error ([PR 8599](https://github.com/spyder-ide/spyder/pull/8599))
* [Issue 8566](https://github.com/spyder-ide/spyder/issues/8566) - File names pasted in editor when copied from OS file manager ([PR 8569](https://github.com/spyder-ide/spyder/pull/8569))
* [Issue 8565](https://github.com/spyder-ide/spyder/issues/8565) - Code analysis and completion often break when the "Automatic code completion" option is checked ([PR 8600](https://github.com/spyder-ide/spyder/pull/8600))
* [Issue 8560](https://github.com/spyder-ide/spyder/issues/8560) - Sometimes segmentation Fault when placing the mouse cursor over linenumbers ([PR 5283](https://github.com/spyder-ide/spyder/pull/5283))
* [Issue 8557](https://github.com/spyder-ide/spyder/issues/8557) - KeyError when closing dataframe editor ([PR 8559](https://github.com/spyder-ide/spyder/pull/8559))
* [Issue 8556](https://github.com/spyder-ide/spyder/issues/8556) - Outline Explorer does not properly handle async functions and methods ([PR 8821](https://github.com/spyder-ide/spyder/pull/8821))
* [Issue 8545](https://github.com/spyder-ide/spyder/issues/8545) - Full Screen in dual monitor enviroment (windows) ([PR 8546](https://github.com/spyder-ide/spyder/pull/8546))
* [Issue 8523](https://github.com/spyder-ide/spyder/issues/8523) - Plot plugin context menu wrong style and copy to clipboard action glitches ([PR 8524](https://github.com/spyder-ide/spyder/pull/8524))
* [Issue 8520](https://github.com/spyder-ide/spyder/issues/8520) - Enclose console warning about plots being rendered in the Plots plugin in horizontal bars ([PR 8584](https://github.com/spyder-ide/spyder/pull/8584))
* [Issue 8515](https://github.com/spyder-ide/spyder/issues/8515) - Error when deleting a project ([PR 8516](https://github.com/spyder-ide/spyder/pull/8516))
* [Issue 8511](https://github.com/spyder-ide/spyder/issues/8511) - Not working shortcut for copy figure in Plots Widget if there are multiple consoles. ([PR 8512](https://github.com/spyder-ide/spyder/pull/8512))
* [Issue 8510](https://github.com/spyder-ide/spyder/issues/8510) - Error when trying to go to cursor position in Outline ([PR 8517](https://github.com/spyder-ide/spyder/pull/8517))
* [Issue 8506](https://github.com/spyder-ide/spyder/issues/8506) - AttributeError: 'WebView' object has no attribute 'setBackgroundColor' ([PR 8508](https://github.com/spyder-ide/spyder/pull/8508))
* [Issue 8486](https://github.com/spyder-ide/spyder/issues/8486) - The editor menu has undock option after undock. ([PR 8489](https://github.com/spyder-ide/spyder/pull/8489))
* [Issue 8478](https://github.com/spyder-ide/spyder/issues/8478) - Improve IPython console Options menu ([PR 8578](https://github.com/spyder-ide/spyder/pull/8578))
* [Issue 8477](https://github.com/spyder-ide/spyder/issues/8477) - Set dark color for blank html template ([PR 8497](https://github.com/spyder-ide/spyder/pull/8497))
* [Issue 8468](https://github.com/spyder-ide/spyder/issues/8468) - Feature Request: copy figure of plot widget to clipboard ([PR 8470](https://github.com/spyder-ide/spyder/pull/8470))
* [Issue 8458](https://github.com/spyder-ide/spyder/issues/8458) - Spyder won't load previously open files from any project with a clean prefs file ([PR 8460](https://github.com/spyder-ide/spyder/pull/8460))
* [Issue 8455](https://github.com/spyder-ide/spyder/issues/8455) - Project Explorer is sometimes not set correctly when switching projects ([PR 8456](https://github.com/spyder-ide/spyder/pull/8456))
* [Issue 8450](https://github.com/spyder-ide/spyder/issues/8450) - Project switching with recent projects menu fails to open correct project ([PR 8452](https://github.com/spyder-ide/spyder/pull/8452))
* [Issue 8443](https://github.com/spyder-ide/spyder/issues/8443) - Backgroud color of Plotwidget in dark theme ([PR 8446](https://github.com/spyder-ide/spyder/pull/8446))
* [Issue 8388](https://github.com/spyder-ide/spyder/issues/8388) - Use language type icons present in Material design ([PR 8440](https://github.com/spyder-ide/spyder/pull/8440))
* [Issue 8386](https://github.com/spyder-ide/spyder/issues/8386) - Change function/class/method icons ([PR 8390](https://github.com/spyder-ide/spyder/pull/8390))
* [Issue 8375](https://github.com/spyder-ide/spyder/issues/8375) - Spyder editor does not open previously opened files in a project ([PR 8429](https://github.com/spyder-ide/spyder/pull/8429))
* [Issue 8344](https://github.com/spyder-ide/spyder/issues/8344) - Title field of error dialog is too small in macOS ([PR 8378](https://github.com/spyder-ide/spyder/pull/8378))
* [Issue 8330](https://github.com/spyder-ide/spyder/issues/8330) - qtawsome 0.5.0 requirements is not high enough for master ([PR 8340](https://github.com/spyder-ide/spyder/pull/8340))
* [Issue 8321](https://github.com/spyder-ide/spyder/issues/8321) - Make a copy of a files inside Project explorer ([PR 8606](https://github.com/spyder-ide/spyder/pull/8606))
* [Issue 8320](https://github.com/spyder-ide/spyder/issues/8320) - Some issues with the Plots plugin ([PR 8419](https://github.com/spyder-ide/spyder/pull/8419))
* [Issue 8309](https://github.com/spyder-ide/spyder/issues/8309) - A word write wrong in portuguese in the file pt_BR/LC_MESSAGES/spyder.po ([PR 8441](https://github.com/spyder-ide/spyder/pull/8441))
* [Issue 8297](https://github.com/spyder-ide/spyder/issues/8297) - Autocomplete doesn't replace text sometimes ([PR 8434](https://github.com/spyder-ide/spyder/pull/8434))
* [Issue 8293](https://github.com/spyder-ide/spyder/issues/8293) - More easily override conflicted shortcuts ([PR 9031](https://github.com/spyder-ide/spyder/pull/9031))
* [Issue 8291](https://github.com/spyder-ide/spyder/issues/8291) - Add QDarkstyle to the Dependencies list ([PR 8300](https://github.com/spyder-ide/spyder/pull/8300))
* [Issue 8284](https://github.com/spyder-ide/spyder/issues/8284) - Improve "Spyder Dark" syntax highlighting theme ([PR 8357](https://github.com/spyder-ide/spyder/pull/8357))
* [Issue 8283](https://github.com/spyder-ide/spyder/issues/8283) - AttributeError: 'NoneType' object has no attribute 'raise_' error on startup in latest master ([PR 8349](https://github.com/spyder-ide/spyder/pull/8349))
* [Issue 8270](https://github.com/spyder-ide/spyder/issues/8270) - Simplify Github PR template ([PR 8272](https://github.com/spyder-ide/spyder/pull/8272))
* [Issue 8267](https://github.com/spyder-ide/spyder/issues/8267) - Triple quotes in a code cell breaks runcell ([PR 8276](https://github.com/spyder-ide/spyder/pull/8276))
* [Issue 8244](https://github.com/spyder-ide/spyder/issues/8244) - Runcell traceback line number off by one for every code block it's after  ([PR 8245](https://github.com/spyder-ide/spyder/pull/8245))
* [Issue 8242](https://github.com/spyder-ide/spyder/issues/8242) - Double Quotes at the beginning or end of the a code cell breaks runcell ([PR 8245](https://github.com/spyder-ide/spyder/pull/8245))
* [Issue 8241](https://github.com/spyder-ide/spyder/issues/8241) - Cannot runcell if double backslash is present ([PR 8243](https://github.com/spyder-ide/spyder/pull/8243))
* [Issue 8237](https://github.com/spyder-ide/spyder/issues/8237) - Mitigate Spyder wiping users' files with more robust atomic saves/autosaves ([PR 8347](https://github.com/spyder-ide/spyder/pull/8347))
* [Issue 8213](https://github.com/spyder-ide/spyder/issues/8213) - PyLS hangs if definition cannot be located ([PR 9138](https://github.com/spyder-ide/spyder/pull/9138))
* [Issue 8172](https://github.com/spyder-ide/spyder/issues/8172) - Warnings and errors from PyLS don't go away after fixing them, even when saving file ([PR 8257](https://github.com/spyder-ide/spyder/pull/8257))
* [Issue 8171](https://github.com/spyder-ide/spyder/issues/8171) - Plots plugin is not docked correctly after first start ([PR 8192](https://github.com/spyder-ide/spyder/pull/8192))
* [Issue 8159](https://github.com/spyder-ide/spyder/issues/8159) - PATH problem since updating macOS ([PR 8351](https://github.com/spyder-ide/spyder/pull/8351))
* [Issue 8153](https://github.com/spyder-ide/spyder/issues/8153) - Spyder crashes on launch with PyLS >=0.21 ([PR 8600](https://github.com/spyder-ide/spyder/pull/8600))
* [Issue 8121](https://github.com/spyder-ide/spyder/issues/8121) - Option to show/hide code style analysis warnings does not work ([PR 9182](https://github.com/spyder-ide/spyder/pull/9182))
* [Issue 8087](https://github.com/spyder-ide/spyder/issues/8087) - Add dark theme style to Help pane ([PR 8086](https://github.com/spyder-ide/spyder/pull/8086))
* [Issue 8080](https://github.com/spyder-ide/spyder/issues/8080) - Consider making the dark theme (and corresponding Spyder Dark syntax scheme) the default in Spyder 4 ([PR 8266](https://github.com/spyder-ide/spyder/pull/8266))
* [Issue 8072](https://github.com/spyder-ide/spyder/issues/8072) - Make internal console respect user's syntax highlighting theme ([PR 8251](https://github.com/spyder-ide/spyder/pull/8251))
* [Issue 8071](https://github.com/spyder-ide/spyder/issues/8071) - Centralize remaining theme-related options (like Rstudio does) under a renamed "Themes" pref pane ([PR 8266](https://github.com/spyder-ide/spyder/pull/8266))
* [Issue 8069](https://github.com/spyder-ide/spyder/issues/8069) - Spyder dark theme overrides background color set in syntax highlighting theme, except behind text ([PR 8081](https://github.com/spyder-ide/spyder/pull/8081))
* [Issue 8066](https://github.com/spyder-ide/spyder/issues/8066) - The pyls process opens a black DOS windows under Windows10 ([PR 8360](https://github.com/spyder-ide/spyder/pull/8360))
* [Issue 8056](https://github.com/spyder-ide/spyder/issues/8056) - Shift-Tab moves focus outside of current Editor pane in Spyder 4
* [Issue 8043](https://github.com/spyder-ide/spyder/issues/8043) - Closing a Python file in Spyder cause a LSP error ([PR 8044](https://github.com/spyder-ide/spyder/pull/8044))
* [Issue 8037](https://github.com/spyder-ide/spyder/issues/8037) - DataFrames in Variable Explorer: Missings should have distinctive background color ([PR 8059](https://github.com/spyder-ide/spyder/pull/8059))
* [Issue 8022](https://github.com/spyder-ide/spyder/issues/8022) - KeyboardInterrupt shows up when Spyder starts ([PR 8600](https://github.com/spyder-ide/spyder/pull/8600))
* [Issue 8013](https://github.com/spyder-ide/spyder/issues/8013) - Stop button in the IPython console is not working with Python 3.7 on Windows ([PR 8337](https://github.com/spyder-ide/spyder/pull/8337))
* [Issue 8011](https://github.com/spyder-ide/spyder/issues/8011) - Restore option to open a new editor window ([PR 8192](https://github.com/spyder-ide/spyder/pull/8192))
* [Issue 7996](https://github.com/spyder-ide/spyder/issues/7996) - Cog menu glitch during Spyder setup in master ([PR 8004](https://github.com/spyder-ide/spyder/pull/8004))
* [Issue 7993](https://github.com/spyder-ide/spyder/issues/7993) - Order of root file items in the Outline Explorer should be synced with that of the current EditorStack ([PR 8015](https://github.com/spyder-ide/spyder/pull/8015))
* [Issue 7982](https://github.com/spyder-ide/spyder/issues/7982) - Show files that are not Python files in the Outline Explorer ([PR 7984](https://github.com/spyder-ide/spyder/pull/7984))
* [Issue 7963](https://github.com/spyder-ide/spyder/issues/7963) - TODO labels are missing in Spyder 4 ([PR 8004](https://github.com/spyder-ide/spyder/pull/8004))
* [Issue 7930](https://github.com/spyder-ide/spyder/issues/7930) - UnicodeEncodeError in TextEditor ([PR 8342](https://github.com/spyder-ide/spyder/pull/8342))
* [Issue 7905](https://github.com/spyder-ide/spyder/issues/7905) - Connect to remote kernel: Have a choice between password or keyfile ([PR 7914](https://github.com/spyder-ide/spyder/pull/7914))
* [Issue 7885](https://github.com/spyder-ide/spyder/issues/7885) - numpy.set_printoptions formatter keyword has no effect on output
* [Issue 7883](https://github.com/spyder-ide/spyder/issues/7883) - GNU Emacs Style Key Sequences do not work in master AND shortcut conflicts ([PR 7929](https://github.com/spyder-ide/spyder/pull/7929))
* [Issue 7880](https://github.com/spyder-ide/spyder/issues/7880) - Error when closing dataframe while data is being fetched ([PR 8598](https://github.com/spyder-ide/spyder/pull/8598))
* [Issue 7875](https://github.com/spyder-ide/spyder/issues/7875) - Config is resetted after a CONF_VERSION bump ([PR 8397](https://github.com/spyder-ide/spyder/pull/8397))
* [Issue 7872](https://github.com/spyder-ide/spyder/issues/7872) - The "Next word" and " Previous word" shortcuts do not work as expected ([PR 7874](https://github.com/spyder-ide/spyder/pull/7874))
* [Issue 7865](https://github.com/spyder-ide/spyder/issues/7865) - Multiple `History...` entries in Static Code Analysis context menu ([PR 7866](https://github.com/spyder-ide/spyder/pull/7866))
* [Issue 7854](https://github.com/spyder-ide/spyder/issues/7854) - Problem with shortcuts using the "Shift" and another key ([PR 7929](https://github.com/spyder-ide/spyder/pull/7929))
* [Issue 7845](https://github.com/spyder-ide/spyder/issues/7845) - Select the dark or light version of the Spyder icon in the "About Spyder" dialog window depending on the color of the window background ([PR 8541](https://github.com/spyder-ide/spyder/pull/8541))
* [Issue 7833](https://github.com/spyder-ide/spyder/issues/7833) - Completion not working in Editor due to undeclared dependency on coloredlogs ([PR 7994](https://github.com/spyder-ide/spyder/pull/7994))
* [Issue 7798](https://github.com/spyder-ide/spyder/issues/7798) - Outline explorer do not sync correctly when closing/re-opening a file in master ([PR 7799](https://github.com/spyder-ide/spyder/pull/7799))
* [Issue 7760](https://github.com/spyder-ide/spyder/issues/7760) - Run unsaved file in Editor without needing to save ([PR 7310](https://github.com/spyder-ide/spyder/pull/7310))
* [Issue 7754](https://github.com/spyder-ide/spyder/issues/7754) - Saving a new file or renaming an existing file in master is broken ([PR 7758](https://github.com/spyder-ide/spyder/pull/7758))
* [Issue 7751](https://github.com/spyder-ide/spyder/issues/7751) - 'ClientWidget' object has no attribute 'show_time_action' ([PR 8062](https://github.com/spyder-ide/spyder/pull/8062))
* [Issue 7744](https://github.com/spyder-ide/spyder/issues/7744) - Go to line is not working in the outline explorer when clicking on the last item of a file ([PR 7745](https://github.com/spyder-ide/spyder/pull/7745))
* [Issue 7743](https://github.com/spyder-ide/spyder/issues/7743) - The "Redo" shortcut in the Editor is not working in Spyder4.0.0.dev0 ([PR 7768](https://github.com/spyder-ide/spyder/pull/7768))
* [Issue 7736](https://github.com/spyder-ide/spyder/issues/7736) - Add the outline explorer option "Group code cells" to config and make it False by default ([PR 7738](https://github.com/spyder-ide/spyder/pull/7738))
* [Issue 7729](https://github.com/spyder-ide/spyder/issues/7729) - The "Go to cursor position" feature of the outline explorer  is broken in master ([PR 7730](https://github.com/spyder-ide/spyder/pull/7730))
* [Issue 7726](https://github.com/spyder-ide/spyder/issues/7726) - Go to definition in the Editor stopped working after the introspection services migration to use the LSP ([PR 7975](https://github.com/spyder-ide/spyder/pull/7975))
* [Issue 7704](https://github.com/spyder-ide/spyder/issues/7704) - No cog menu in variable explorer widget toolbar when more than one Ipython console is opened ([PR 7710](https://github.com/spyder-ide/spyder/pull/7710))
* [Issue 7680](https://github.com/spyder-ide/spyder/issues/7680) - Use a separate configuration directory for beta and dev releases to avoid contaminating user settings ([PR 8837](https://github.com/spyder-ide/spyder/pull/8837))
* [Issue 7629](https://github.com/spyder-ide/spyder/issues/7629) - DataFrame viewer resizes the index column wrongly ([PR 8550](https://github.com/spyder-ide/spyder/pull/8550))
* [Issue 7518](https://github.com/spyder-ide/spyder/issues/7518) - Creating a new project makes the path with mixed slashes ([PR 7698](https://github.com/spyder-ide/spyder/pull/7698))
* [Issue 7339](https://github.com/spyder-ide/spyder/issues/7339) - Indent guides going too far down ([PR 8469](https://github.com/spyder-ide/spyder/pull/8469))
* [Issue 7338](https://github.com/spyder-ide/spyder/issues/7338) - Outline explorer not synchronized at startup ([PR 7968](https://github.com/spyder-ide/spyder/pull/7968))
* [Issue 7235](https://github.com/spyder-ide/spyder/issues/7235) - Outliner has no options in the "gear" menu ([PR 7866](https://github.com/spyder-ide/spyder/pull/7866))
* [Issue 7224](https://github.com/spyder-ide/spyder/issues/7224) - Clearing the variables in a console also clears Pylab and SymPy name spaces and variables ([PR 7876](https://github.com/spyder-ide/spyder/pull/7876))
* [Issue 7214](https://github.com/spyder-ide/spyder/issues/7214) - Outline pane, clicking on file name should move to start of file ([PR 7962](https://github.com/spyder-ide/spyder/pull/7962))
* [Issue 7146](https://github.com/spyder-ide/spyder/issues/7146) - MacOS displaying Windows icons and shortcuts ([PR 8212](https://github.com/spyder-ide/spyder/pull/8212))
* [Issue 7113](https://github.com/spyder-ide/spyder/issues/7113) - Make a function that runs cell blocks instead of copying cell contents into the console ([PR 7310](https://github.com/spyder-ide/spyder/pull/7310))
* [Issue 7111](https://github.com/spyder-ide/spyder/issues/7111) - Master: There is an area in the top left of spyder that is unclickable ([PR 8104](https://github.com/spyder-ide/spyder/pull/8104))
* [Issue 7109](https://github.com/spyder-ide/spyder/issues/7109) - Allow keyboard shorcuts to be cleared in preferences ([PR 7929](https://github.com/spyder-ide/spyder/pull/7929))
* [Issue 7091](https://github.com/spyder-ide/spyder/issues/7091) - QtWebEngineProcess stays open after closing ipython tab ([PR 8740](https://github.com/spyder-ide/spyder/pull/8740))
* [Issue 6827](https://github.com/spyder-ide/spyder/issues/6827) - Enable automatic insertion of closing quotes inside function calls ([PR 8659](https://github.com/spyder-ide/spyder/pull/8659))
* [Issue 5911](https://github.com/spyder-ide/spyder/issues/5911) - Feature Request: Sort tabs alphabetically
* [Issue 5907](https://github.com/spyder-ide/spyder/issues/5907) - Buttons not displayed in mac OS ([PR 8364](https://github.com/spyder-ide/spyder/pull/8364))
* [Issue 5543](https://github.com/spyder-ide/spyder/issues/5543) - Variable explorer column widths are re-generated in every console evaluation ([PR 5764](https://github.com/spyder-ide/spyder/pull/5764))
* [Issue 5515](https://github.com/spyder-ide/spyder/issues/5515) - Enhancements proposal related to the undocking and docking of plugins in the Main Window ([PR 8192](https://github.com/spyder-ide/spyder/pull/8192))
* [Issue 5326](https://github.com/spyder-ide/spyder/issues/5326) - Improve debug logging ([PR 7734](https://github.com/spyder-ide/spyder/pull/7734))
* [Issue 5323](https://github.com/spyder-ide/spyder/issues/5323) - Ctrl+K does not kill to line end
* [Issue 5005](https://github.com/spyder-ide/spyder/issues/5005) - Toggle breakpoints by single click
* [Issue 4936](https://github.com/spyder-ide/spyder/issues/4936) - Feature request: automatic generation of docstring template ([PR 8700](https://github.com/spyder-ide/spyder/pull/8700))
* [Issue 4742](https://github.com/spyder-ide/spyder/issues/4742) - Adapt code introspection, autocompletion and linting to comply with the Language Server Protocol ([PR 4751](https://github.com/spyder-ide/spyder/pull/4751))
* [Issue 4591](https://github.com/spyder-ide/spyder/issues/4591) - Split all plugins to be in their own modules ([PR 7725](https://github.com/spyder-ide/spyder/pull/7725))
* [Issue 4580](https://github.com/spyder-ide/spyder/issues/4580) - Missing "x" on tab for open files in editor ([PR 8363](https://github.com/spyder-ide/spyder/pull/8363))
* [Issue 3689](https://github.com/spyder-ide/spyder/issues/3689) - How to remember the configurations of connecting to remote kernel? ([PR 8222](https://github.com/spyder-ide/spyder/pull/8222))
* [Issue 3414](https://github.com/spyder-ide/spyder/issues/3414) - Add encapsulate with parentheses (quotes, brackets, braces) function ([PR 8637](https://github.com/spyder-ide/spyder/pull/8637))
* [Issue 3064](https://github.com/spyder-ide/spyder/issues/3064) - Allow users to configure PEP8 options ([PR 8647](https://github.com/spyder-ide/spyder/pull/8647))
* [Issue 2855](https://github.com/spyder-ide/spyder/issues/2855) - Hide the titlebar from panes/dockwidgets if locked ([PR 8192](https://github.com/spyder-ide/spyder/pull/8192))
* [Issue 2854](https://github.com/spyder-ide/spyder/issues/2854) - Add custom title bar to dockwidgets/panes ([PR 8192](https://github.com/spyder-ide/spyder/pull/8192))
* [Issue 2641](https://github.com/spyder-ide/spyder/issues/2641) - Enhancement: insert filename as compatible path ([PR 8606](https://github.com/spyder-ide/spyder/pull/8606))
* [Issue 2550](https://github.com/spyder-ide/spyder/issues/2550) - Dock matplotlib figures ([PR 6430](https://github.com/spyder-ide/spyder/pull/6430))
* [Issue 2350](https://github.com/spyder-ide/spyder/issues/2350) - Add a Spyder dark theme
* [Issue 2264](https://github.com/spyder-ide/spyder/issues/2264) - "TODO" should not be labeled with checkmark ([PR 8058](https://github.com/spyder-ide/spyder/pull/8058))
* [Issue 2111](https://github.com/spyder-ide/spyder/issues/2111) - Enhancement: Implement autosave of editor files every X minutes ([PR 7660](https://github.com/spyder-ide/spyder/pull/7660))
* [Issue 1634](https://github.com/spyder-ide/spyder/issues/1634) - Support for current element highlighting when "." appears in selection ([PR 5676](https://github.com/spyder-ide/spyder/pull/5676))
* [Issue 528](https://github.com/spyder-ide/spyder/issues/528) - Add an arrow to point to the current line being debugged in the Editor

In this release 173 issues were closed.

### Pull Requests Merged

* [PR 9355](https://github.com/spyder-ide/spyder/pull/9355) - PR: Add fix for calltips with args and kwargs
* [PR 9348](https://github.com/spyder-ide/spyder/pull/9348) - PR: Fix code editor background color ([9248](https://github.com/spyder-ide/spyder/issues/9248))
* [PR 9345](https://github.com/spyder-ide/spyder/pull/9345) - PR: Remove CodeEditor instances from LSP client when split editor is closed ([9341](https://github.com/spyder-ide/spyder/issues/9341))
* [PR 9334](https://github.com/spyder-ide/spyder/pull/9334) - PR: Fix showing signatures in the IPython console after an open paren
* [PR 9333](https://github.com/spyder-ide/spyder/pull/9333) - PR: Fix fileswitcher search and improve tests ([9332](https://github.com/spyder-ide/spyder/issues/9332))
* [PR 9330](https://github.com/spyder-ide/spyder/pull/9330) - PR: Fix about dialog missing breaks
* [PR 9327](https://github.com/spyder-ide/spyder/pull/9327) - PR: Remove autosaves on successful file close to partially mitigate spurious creation bugs
* [PR 9324](https://github.com/spyder-ide/spyder/pull/9324) - PR: Have LSP update after closequotes and closebrackets ([9323](https://github.com/spyder-ide/spyder/issues/9323))
* [PR 9322](https://github.com/spyder-ide/spyder/pull/9322) - PR: Fix some hover and calltip issues ([9311](https://github.com/spyder-ide/spyder/issues/9311))
* [PR 9310](https://github.com/spyder-ide/spyder/pull/9310) - PR: Restrict PyLS version to be less than 0.25
* [PR 9309](https://github.com/spyder-ide/spyder/pull/9309) - PR: Mark test_update_warnings_after_delete_line as slow and second
* [PR 9306](https://github.com/spyder-ide/spyder/pull/9306) - PR: Fix About dialog format on macOS ([9298](https://github.com/spyder-ide/spyder/issues/9298))
* [PR 9301](https://github.com/spyder-ide/spyder/pull/9301) - PR: Fix hover/calltip for Python objects without signature ([9294](https://github.com/spyder-ide/spyder/issues/9294))
* [PR 9300](https://github.com/spyder-ide/spyder/pull/9300) - PR: Request a didChange when deleting a line in the Editor ([9299](https://github.com/spyder-ide/spyder/issues/9299))
* [PR 9293](https://github.com/spyder-ide/spyder/pull/9293) - PR: Fix window flags for linux calltips ([9287](https://github.com/spyder-ide/spyder/issues/9287))
* [PR 9289](https://github.com/spyder-ide/spyder/pull/9289) - PR: Hide debugger panel for files that are not Python ones ([9208](https://github.com/spyder-ide/spyder/issues/9208))
* [PR 9288](https://github.com/spyder-ide/spyder/pull/9288) - PR: Reorganize LSP server editor dialog
* [PR 9282](https://github.com/spyder-ide/spyder/pull/9282) - PR: Fix update calls of status bars for new Editor windows ([9236](https://github.com/spyder-ide/spyder/issues/9236))
* [PR 9280](https://github.com/spyder-ide/spyder/pull/9280) - PR: Avoid the possibility of duplicate preferences dialogs ([9281](https://github.com/spyder-ide/spyder/issues/9281))
* [PR 9266](https://github.com/spyder-ide/spyder/pull/9266) - PR: Show PyLS server errors in Spyder's error report dialog ([9211](https://github.com/spyder-ide/spyder/issues/9211))
* [PR 9260](https://github.com/spyder-ide/spyder/pull/9260) - PR: Improvements to autocompletion ([9273](https://github.com/spyder-ide/spyder/issues/9273), [9269](https://github.com/spyder-ide/spyder/issues/9269), [9268](https://github.com/spyder-ide/spyder/issues/9268), [9267](https://github.com/spyder-ide/spyder/issues/9267), [9257](https://github.com/spyder-ide/spyder/issues/9257))
* [PR 9243](https://github.com/spyder-ide/spyder/pull/9243) - PR: Remove unused Pyflakes and Pep8 check functions ([9242](https://github.com/spyder-ide/spyder/issues/9242))
* [PR 9237](https://github.com/spyder-ide/spyder/pull/9237) - PR: Rename plugins to have a simpler interface ([9207](https://github.com/spyder-ide/spyder/issues/9207))
* [PR 9231](https://github.com/spyder-ide/spyder/pull/9231) - PR: Handle empty options in pycodestyle and pydocstyle preferences ([9209](https://github.com/spyder-ide/spyder/issues/9209))
* [PR 9230](https://github.com/spyder-ide/spyder/pull/9230) - PR: Display extension type icons and create entry as files are opened in "Open recent" menu ([9150](https://github.com/spyder-ide/spyder/issues/9150))
* [PR 9229](https://github.com/spyder-ide/spyder/pull/9229) - PR: Fix typo on PR template
* [PR 9228](https://github.com/spyder-ide/spyder/pull/9228) - PR: Add icon for Latex files ([9151](https://github.com/spyder-ide/spyder/issues/9151))
* [PR 9224](https://github.com/spyder-ide/spyder/pull/9224) - PR: Ask for animations in pull request template
* [PR 9210](https://github.com/spyder-ide/spyder/pull/9210) - PR: Add a syntax highlighter for Python log files
* [PR 9205](https://github.com/spyder-ide/spyder/pull/9205) - PR: Prevent rehighlight() from setting changed_since_autosave_flag ([8654](https://github.com/spyder-ide/spyder/issues/8654))
* [PR 9203](https://github.com/spyder-ide/spyder/pull/9203) - PR: Add option to connect to external PyLS servers ([9195](https://github.com/spyder-ide/spyder/issues/9195))
* [PR 9191](https://github.com/spyder-ide/spyder/pull/9191) - PR: Enable hover hints ([9187](https://github.com/spyder-ide/spyder/issues/9187))
* [PR 9186](https://github.com/spyder-ide/spyder/pull/9186) - PR: Use a single LSP manager instance per module in our tests
* [PR 9182](https://github.com/spyder-ide/spyder/pull/9182) - PR: Fix Source menu entry to show code style warnings ([8121](https://github.com/spyder-ide/spyder/issues/8121))
* [PR 9176](https://github.com/spyder-ide/spyder/pull/9176) - PR: Avoid running introspection in tests unless we require it
* [PR 9175](https://github.com/spyder-ide/spyder/pull/9175) - PR: Remove sig_lsp_notification and improve introspection tests ([9173](https://github.com/spyder-ide/spyder/issues/9173))
* [PR 9174](https://github.com/spyder-ide/spyder/pull/9174) - PR: Apply dark theme to help icon of arraybuilder
* [PR 9155](https://github.com/spyder-ide/spyder/pull/9155) - PR: Simplify custom layout definition with the new features in Qt 5.6 ([8613](https://github.com/spyder-ide/spyder/issues/8613))
* [PR 9154](https://github.com/spyder-ide/spyder/pull/9154) - PR: Reorganize preferences entry for the Editor
* [PR 9152](https://github.com/spyder-ide/spyder/pull/9152) - PR: Scroll to the selected item after go next thumbnail in Plots plugin
* [PR 9142](https://github.com/spyder-ide/spyder/pull/9142) - PR: Correctly log errors when handling LSP responses for Python 2
* [PR 9140](https://github.com/spyder-ide/spyder/pull/9140) - PR: Use calltip widget to display calltips and tooltips
* [PR 9138](https://github.com/spyder-ide/spyder/pull/9138) - PR: Catch errors generated when handling LSP responses in CodeEditor ([8213](https://github.com/spyder-ide/spyder/issues/8213))
* [PR 9121](https://github.com/spyder-ide/spyder/pull/9121) - PR: Force darkstyle style on status bar ([9120](https://github.com/spyder-ide/spyder/issues/9120))
* [PR 9109](https://github.com/spyder-ide/spyder/pull/9109) - PR: Add an option to sort editor tabs alphabetically
* [PR 9104](https://github.com/spyder-ide/spyder/pull/9104) - PR: Remove "Code Introspection/Analysis" tab of Editor Preferences ([8815](https://github.com/spyder-ide/spyder/issues/8815), [8609](https://github.com/spyder-ide/spyder/issues/8609))
* [PR 9088](https://github.com/spyder-ide/spyder/pull/9088) - PR: Update simplified chinese translation
* [PR 9075](https://github.com/spyder-ide/spyder/pull/9075) - PR: Make completion work in split panels again ([8865](https://github.com/spyder-ide/spyder/issues/8865))
* [PR 9057](https://github.com/spyder-ide/spyder/pull/9057) - PR: Fix completion popup dismissed after typing delimeters or operators ([8859](https://github.com/spyder-ide/spyder/issues/8859))
* [PR 9054](https://github.com/spyder-ide/spyder/pull/9054) - PR: Add an "Fit plots to window" option to the plots pane
* [PR 9048](https://github.com/spyder-ide/spyder/pull/9048) - PR: Add basic active git branch display on status bar
* [PR 9046](https://github.com/spyder-ide/spyder/pull/9046) - PR: Fix bold editor issues when setting bold status widgets ([9044](https://github.com/spyder-ide/spyder/issues/9044))
* [PR 9040](https://github.com/spyder-ide/spyder/pull/9040) - PR: Fix getting Rope completions from the latest PyLS
* [PR 9036](https://github.com/spyder-ide/spyder/pull/9036) - PR: Add Ctrl+Shift+G to switch to plots plugin ([8640](https://github.com/spyder-ide/spyder/issues/8640))
* [PR 9034](https://github.com/spyder-ide/spyder/pull/9034) - PR: Disable status timers if widget is not visible
* [PR 9033](https://github.com/spyder-ide/spyder/pull/9033) - PR: Fix error when PyLS completions response is None
* [PR 9031](https://github.com/spyder-ide/spyder/pull/9031) - PR: Automatically unbind conflicting shortcuts when pressing okay in shortcut manager ([8293](https://github.com/spyder-ide/spyder/issues/8293))
* [PR 9029](https://github.com/spyder-ide/spyder/pull/9029) - PR: Fix error at startup when updating warnings menu
* [PR 9024](https://github.com/spyder-ide/spyder/pull/9024) - PR: Add single click to open files on file and project explorer ([8930](https://github.com/spyder-ide/spyder/issues/8930))
* [PR 9011](https://github.com/spyder-ide/spyder/pull/9011) - PR: Reconnect warning menu with PyLS output ([8985](https://github.com/spyder-ide/spyder/issues/8985))
* [PR 9010](https://github.com/spyder-ide/spyder/pull/9010) - PR: Simplify status bar content and reorganize code ([9006](https://github.com/spyder-ide/spyder/issues/9006))
* [PR 8972](https://github.com/spyder-ide/spyder/pull/8972) - PR: Disable parameter inclusion in the PyLS ([8828](https://github.com/spyder-ide/spyder/issues/8828))
* [PR 8932](https://github.com/spyder-ide/spyder/pull/8932) - PR: Catch error in Outline explorer when renaming file ([8813](https://github.com/spyder-ide/spyder/issues/8813))
* [PR 8911](https://github.com/spyder-ide/spyder/pull/8911) - PR: Fix Windows tests with pip
* [PR 8877](https://github.com/spyder-ide/spyder/pull/8877) - PR: Adjust font sizes to look better for Linux and Windows
* [PR 8854](https://github.com/spyder-ide/spyder/pull/8854) - PR: Fix stuck arrow and conditional breakpoints in the debugger panel ([8846](https://github.com/spyder-ide/spyder/issues/8846))
* [PR 8842](https://github.com/spyder-ide/spyder/pull/8842) - PR: Change default root_path for PyLS and refactor LSP related code
* [PR 8839](https://github.com/spyder-ide/spyder/pull/8839) - PR: Improve logging of PyLS server and our client in debug mode
* [PR 8837](https://github.com/spyder-ide/spyder/pull/8837) - PR: Automatically use a separate but persistent configuration directory for non-stable releases ([7680](https://github.com/spyder-ide/spyder/issues/7680))
* [PR 8836](https://github.com/spyder-ide/spyder/pull/8836) - PR: Don't show a file in the Editor immediately after it's selected in the switcher.
* [PR 8821](https://github.com/spyder-ide/spyder/pull/8821) - PR: Handle async functions and methods properly in Outline Explorer ([8556](https://github.com/spyder-ide/spyder/issues/8556))
* [PR 8810](https://github.com/spyder-ide/spyder/pull/8810) - PR: Fix failing Sympy test
* [PR 8782](https://github.com/spyder-ide/spyder/pull/8782) - PR: Enclose logger.debug call in a try/except ([8749](https://github.com/spyder-ide/spyder/issues/8749))
* [PR 8769](https://github.com/spyder-ide/spyder/pull/8769) - PR: Add new font size for file switcher according to the OS
* [PR 8754](https://github.com/spyder-ide/spyder/pull/8754) - PR: Fix spelling errors in test_mainwindow.py comments
* [PR 8740](https://github.com/spyder-ide/spyder/pull/8740) - PR: Use a single infowidget in the IPython console ([7091](https://github.com/spyder-ide/spyder/issues/7091))
* [PR 8733](https://github.com/spyder-ide/spyder/pull/8733) - PR: Remove autosave file if user chooses not to save when asked ([8655](https://github.com/spyder-ide/spyder/issues/8655))
* [PR 8724](https://github.com/spyder-ide/spyder/pull/8724) - PR: Add position to text completion ([8727](https://github.com/spyder-ide/spyder/issues/8727), [8723](https://github.com/spyder-ide/spyder/issues/8723))
* [PR 8719](https://github.com/spyder-ide/spyder/pull/8719) - PR: Show a place holder text in the file switcher
* [PR 8717](https://github.com/spyder-ide/spyder/pull/8717) - PR: Change the max number of files in the file switcher to 15
* [PR 8716](https://github.com/spyder-ide/spyder/pull/8716) - PR: Put section header rows in the file switcher at item level
* [PR 8704](https://github.com/spyder-ide/spyder/pull/8704) - PR: Update README's sponsors section
* [PR 8700](https://github.com/spyder-ide/spyder/pull/8700) - PR: Automatic docstring generation for functions ([4936](https://github.com/spyder-ide/spyder/issues/4936))
* [PR 8691](https://github.com/spyder-ide/spyder/pull/8691) - PR: Improve appearance of breakpoint icon
* [PR 8678](https://github.com/spyder-ide/spyder/pull/8678) - PR:  Use file type icons in the File Switcher
* [PR 8665](https://github.com/spyder-ide/spyder/pull/8665) - PR: Move config pages of missing plugins to their own modules
* [PR 8664](https://github.com/spyder-ide/spyder/pull/8664) - PR: Move ConsoleBaseWidget to the console plugin from the editor
* [PR 8661](https://github.com/spyder-ide/spyder/pull/8661) - PR: Simplify the way to import Editor extensions and panels
* [PR 8659](https://github.com/spyder-ide/spyder/pull/8659) - PR: Close quotes inside brackets and before commas, colons and semi-colons ([6827](https://github.com/spyder-ide/spyder/issues/6827))
* [PR 8657](https://github.com/spyder-ide/spyder/pull/8657) - PR: Change font size for file name and path in the file switcher
* [PR 8653](https://github.com/spyder-ide/spyder/pull/8653) - PR: Move some preferences entries to their own modules
* [PR 8650](https://github.com/spyder-ide/spyder/pull/8650) - PR: Fall back to copy and delete if replace fails when restoring autosave ([8631](https://github.com/spyder-ide/spyder/issues/8631))
* [PR 8648](https://github.com/spyder-ide/spyder/pull/8648) - PR: Add validation for blank spaces while doing completion ([8628](https://github.com/spyder-ide/spyder/issues/8628))
* [PR 8647](https://github.com/spyder-ide/spyder/pull/8647) - PR: Provide graphical options to configure the PyLS ([8816](https://github.com/spyder-ide/spyder/issues/8816), [3064](https://github.com/spyder-ide/spyder/issues/3064))
* [PR 8644](https://github.com/spyder-ide/spyder/pull/8644) - PR: Add ability to paste auto-formatted file paths into the Editor from the system file manager
* [PR 8643](https://github.com/spyder-ide/spyder/pull/8643) - PR: Assign a keyboard shortcut for "next figure" and "previous figure" of the Plots pane ([8641](https://github.com/spyder-ide/spyder/issues/8641))
* [PR 8642](https://github.com/spyder-ide/spyder/pull/8642) - PR: Rewrite LSPManager to inherit from QObject instead of SpyderPluginWidget
* [PR 8637](https://github.com/spyder-ide/spyder/pull/8637) - PR: Make a closebrackets extension for smarter brackets ([3414](https://github.com/spyder-ide/spyder/issues/3414))
* [PR 8627](https://github.com/spyder-ide/spyder/pull/8627) - PR: Fix printing warning about rendering of plots below the new prompt ([8626](https://github.com/spyder-ide/spyder/issues/8626))
* [PR 8616](https://github.com/spyder-ide/spyder/pull/8616) - PR: Use single row for file name and path and use gray for paths in file switcher
* [PR 8606](https://github.com/spyder-ide/spyder/pull/8606) - PR: Add the ability to copy/paste files and their paths in the File/Project Explorers ([8321](https://github.com/spyder-ide/spyder/issues/8321), [2641](https://github.com/spyder-ide/spyder/issues/2641))
* [PR 8604](https://github.com/spyder-ide/spyder/pull/8604) - PR: Fix missing IPython prompt ([8603](https://github.com/spyder-ide/spyder/issues/8603))
* [PR 8600](https://github.com/spyder-ide/spyder/pull/8600) - PR: Fix LSP consumer reading block on Windows ([8565](https://github.com/spyder-ide/spyder/issues/8565), [8153](https://github.com/spyder-ide/spyder/issues/8153), [8022](https://github.com/spyder-ide/spyder/issues/8022))
* [PR 8599](https://github.com/spyder-ide/spyder/pull/8599) - PR: Add ability to delete long nested directories on Windows from File/Project Explorers ([8567](https://github.com/spyder-ide/spyder/issues/8567))
* [PR 8598](https://github.com/spyder-ide/spyder/pull/8598) - PR: Enclose contents of load_more_data method in try/except NameError Block ([7880](https://github.com/spyder-ide/spyder/issues/7880))
* [PR 8593](https://github.com/spyder-ide/spyder/pull/8593) - PR: Fix code completion in the Internal Console ([8579](https://github.com/spyder-ide/spyder/issues/8579))
* [PR 8590](https://github.com/spyder-ide/spyder/pull/8590) - PR: Adjust attribute icons size on Linux and Windows
* [PR 8584](https://github.com/spyder-ide/spyder/pull/8584) - PR: Enclose console warning about rendering of plots ([8520](https://github.com/spyder-ide/spyder/issues/8520))
* [PR 8578](https://github.com/spyder-ide/spyder/pull/8578) - PR: Restructure console menus ([8478](https://github.com/spyder-ide/spyder/issues/8478))
* [PR 8571](https://github.com/spyder-ide/spyder/pull/8571) - PR: Remove test np_threshold from test_mainwindow.py
* [PR 8569](https://github.com/spyder-ide/spyder/pull/8569) - PR: Prevent pasting non-text data from clipboard into the editor ([8566](https://github.com/spyder-ide/spyder/issues/8566))
* [PR 8559](https://github.com/spyder-ide/spyder/pull/8559) - PR: Avoid KeyError when closing Variable Explorer editors ([8557](https://github.com/spyder-ide/spyder/issues/8557))
* [PR 8558](https://github.com/spyder-ide/spyder/pull/8558) - PR: Add parent reference to QLineEdit of EditTabNamePopup
* [PR 8552](https://github.com/spyder-ide/spyder/pull/8552) - PR: Improve layout of Appearance entry in Preferences (2)
* [PR 8550](https://github.com/spyder-ide/spyder/pull/8550) - PR: Improve index column resize in dataframe editor ([7629](https://github.com/spyder-ide/spyder/issues/7629))
* [PR 8548](https://github.com/spyder-ide/spyder/pull/8548) - PR: Improve layout of Appearance entry in Preferences
* [PR 8546](https://github.com/spyder-ide/spyder/pull/8546) - PR : Fix full screen action in dual monitor enviroment for Windows ([8545](https://github.com/spyder-ide/spyder/issues/8545))
* [PR 8541](https://github.com/spyder-ide/spyder/pull/8541) - PR: Use dark logo for the light theme ([7845](https://github.com/spyder-ide/spyder/issues/7845))
* [PR 8529](https://github.com/spyder-ide/spyder/pull/8529) - PR: Pin pytest to a version less than 4.1
* [PR 8528](https://github.com/spyder-ide/spyder/pull/8528) - PR: Make the directory tree view proxy model case insensitive on Windows
* [PR 8525](https://github.com/spyder-ide/spyder/pull/8525) - PR: Add tests for the Plots plugin
* [PR 8524](https://github.com/spyder-ide/spyder/pull/8524) - PR: Fix bad context menu stylesheet and figure blinking in the Plots plugin ([8523](https://github.com/spyder-ide/spyder/issues/8523))
* [PR 8517](https://github.com/spyder-ide/spyder/pull/8517) - PR: Fix go to cursor position in Outline for newly created files ([8510](https://github.com/spyder-ide/spyder/issues/8510))
* [PR 8516](https://github.com/spyder-ide/spyder/pull/8516) - PR: Fix delete project by moving the code from the project explorer to the plugin ([8515](https://github.com/spyder-ide/spyder/issues/8515))
* [PR 8512](https://github.com/spyder-ide/spyder/pull/8512) - PR: Fix the "Copy Figure" shortcut of Plots pane with multiple consoles ([8511](https://github.com/spyder-ide/spyder/issues/8511))
* [PR 8508](https://github.com/spyder-ide/spyder/pull/8508) - PR: Fix handling background color of Webview when using QWebView ([8506](https://github.com/spyder-ide/spyder/issues/8506))
* [PR 8497](https://github.com/spyder-ide/spyder/pull/8497) - PR: Set dark background color for webview in the Help and IPython Console plugins ([8477](https://github.com/spyder-ide/spyder/issues/8477))
* [PR 8489](https://github.com/spyder-ide/spyder/pull/8489) - PR: Fix actions shown on the Editor Options menu for undocked and new windows ([8486](https://github.com/spyder-ide/spyder/issues/8486))
* [PR 8481](https://github.com/spyder-ide/spyder/pull/8481) - PR: Add cursor position bookmarks in Editor
* [PR 8471](https://github.com/spyder-ide/spyder/pull/8471) - PR: Show tests for plugins that use a mocked main window
* [PR 8470](https://github.com/spyder-ide/spyder/pull/8470) - PR: Add the ability to copy a figure from the plot widget ([8468](https://github.com/spyder-ide/spyder/issues/8468))
* [PR 8469](https://github.com/spyder-ide/spyder/pull/8469) - PR: Make indentation guides to go up to last line with text ([7339](https://github.com/spyder-ide/spyder/issues/7339))
* [PR 8460](https://github.com/spyder-ide/spyder/pull/8460) - PR: Handle non-existing saved editor layout when loading projects ([8458](https://github.com/spyder-ide/spyder/issues/8458))
* [PR 8456](https://github.com/spyder-ide/spyder/pull/8456) - PR: Setup proxy filter before setting the root index ([8455](https://github.com/spyder-ide/spyder/issues/8455))
* [PR 8452](https://github.com/spyder-ide/spyder/pull/8452) - PR: Fix Recent Project submenu actions in Projects menu. ([8450](https://github.com/spyder-ide/spyder/issues/8450))
* [PR 8446](https://github.com/spyder-ide/spyder/pull/8446) - PR: Add kwarg for FigureCanvas background color ([8443](https://github.com/spyder-ide/spyder/issues/8443))
* [PR 8441](https://github.com/spyder-ide/spyder/pull/8441) - PR: Fix translation error in the Brazilian Portuguese translation ([8309](https://github.com/spyder-ide/spyder/issues/8309))
* [PR 8440](https://github.com/spyder-ide/spyder/pull/8440) - PR: Change image logos for several programming language type files ([8388](https://github.com/spyder-ide/spyder/issues/8388))
* [PR 8434](https://github.com/spyder-ide/spyder/pull/8434) - PR: Fix completion insertion in the Editor ([8297](https://github.com/spyder-ide/spyder/issues/8297))
* [PR 8431](https://github.com/spyder-ide/spyder/pull/8431) - PR: Fix macOS tests by pinning to Qt 5.9.6 for now
* [PR 8429](https://github.com/spyder-ide/spyder/pull/8429) - PR: Set projet filenames correctly when closing a project ([8375](https://github.com/spyder-ide/spyder/issues/8375))
* [PR 8419](https://github.com/spyder-ide/spyder/pull/8419) - PR: Increase width of the ThumbnailScrollBar and add render message ([8320](https://github.com/spyder-ide/spyder/issues/8320))
* [PR 8416](https://github.com/spyder-ide/spyder/pull/8416) - PR: Fix error when Editor's dockwidget is not yet initialized
* [PR 8403](https://github.com/spyder-ide/spyder/pull/8403) - PR: Fix dark CSS for tables and add custom dark scrollbar for the Help plugin
* [PR 8402](https://github.com/spyder-ide/spyder/pull/8402) - PR: Run Windows tests on Azure
* [PR 8399](https://github.com/spyder-ide/spyder/pull/8399) - PR: Disable Qt windows style if using the dark UI theme
* [PR 8397](https://github.com/spyder-ide/spyder/pull/8397) - PR: Change handling of server host and port config placeholders ([7875](https://github.com/spyder-ide/spyder/issues/7875))
* [PR 8396](https://github.com/spyder-ide/spyder/pull/8396) - PR: Start testing with Azure pipelines
* [PR 8390](https://github.com/spyder-ide/spyder/pull/8390) - PR: Change method/function/class icons ([8386](https://github.com/spyder-ide/spyder/issues/8386))
* [PR 8387](https://github.com/spyder-ide/spyder/pull/8387) - PR: Modify test_introspection to test module completion
* [PR 8378](https://github.com/spyder-ide/spyder/pull/8378) - PR: Set right size of error dialog title field in macOS ([8344](https://github.com/spyder-ide/spyder/issues/8344))
* [PR 8364](https://github.com/spyder-ide/spyder/pull/8364) - PR: Add dark background to the light theme buttons on macOS ([5907](https://github.com/spyder-ide/spyder/issues/5907))
* [PR 8363](https://github.com/spyder-ide/spyder/pull/8363) - PR: Add close tab buttons to the light theme on macOS ([4580](https://github.com/spyder-ide/spyder/issues/4580))
* [PR 8360](https://github.com/spyder-ide/spyder/pull/8360) - PR: Change creationflags to prevent showing a cmd for pyls ([8066](https://github.com/spyder-ide/spyder/issues/8066))
* [PR 8357](https://github.com/spyder-ide/spyder/pull/8357) - PR: Improve Spyder Dark syntax highlighting theme ([8284](https://github.com/spyder-ide/spyder/issues/8284))
* [PR 8351](https://github.com/spyder-ide/spyder/pull/8351) - PR: Improve robustness when starting pyls ([8159](https://github.com/spyder-ide/spyder/issues/8159))
* [PR 8349](https://github.com/spyder-ide/spyder/pull/8349) - PR: Validation of dockwidget existence before raising it ([8283](https://github.com/spyder-ide/spyder/issues/8283))
* [PR 8348](https://github.com/spyder-ide/spyder/pull/8348) - PR: Stop using ci-helpers to simplify testing
* [PR 8347](https://github.com/spyder-ide/spyder/pull/8347) - PR: Do atomic writes when saving files ([8237](https://github.com/spyder-ide/spyder/issues/8237))
* [PR 8342](https://github.com/spyder-ide/spyder/pull/8342) - PR: Transform texteditor title to unicode ([7930](https://github.com/spyder-ide/spyder/issues/7930))
* [PR 8340](https://github.com/spyder-ide/spyder/pull/8340) - PR: Increase minimal QtAwesome version to 0.5.2 ([8330](https://github.com/spyder-ide/spyder/issues/8330))
* [PR 8337](https://github.com/spyder-ide/spyder/pull/8337) - PR: Specify close_fds=False on Windows ([8013](https://github.com/spyder-ide/spyder/issues/8013))
* [PR 8300](https://github.com/spyder-ide/spyder/pull/8300) - PR: Add qdarkstyle to dependencies dialog ([8291](https://github.com/spyder-ide/spyder/issues/8291))
* [PR 8299](https://github.com/spyder-ide/spyder/pull/8299) - PR: Improve contributing guide
* [PR 8276](https://github.com/spyder-ide/spyder/pull/8276) - PR: Add additional escape slashes instead of a raw string in runcell ([8267](https://github.com/spyder-ide/spyder/issues/8267))
* [PR 8272](https://github.com/spyder-ide/spyder/pull/8272) - PR: Greatly simplify and clarify Github pull request template ([8270](https://github.com/spyder-ide/spyder/issues/8270))
* [PR 8266](https://github.com/spyder-ide/spyder/pull/8266) - PR: Centralize theme-related preferences under an 'Appearance' entry ([8080](https://github.com/spyder-ide/spyder/issues/8080), [8071](https://github.com/spyder-ide/spyder/issues/8071))
* [PR 8265](https://github.com/spyder-ide/spyder/pull/8265) - PR: Close scrollflag tests after they run
* [PR 8257](https://github.com/spyder-ide/spyder/pull/8257) - PR: LSP fixes, debugging, and minor code cleanup ([8172](https://github.com/spyder-ide/spyder/issues/8172))
* [PR 8251](https://github.com/spyder-ide/spyder/pull/8251) - PR: Make the internal console use the same theme as the other widgets ([8072](https://github.com/spyder-ide/spyder/issues/8072))
* [PR 8245](https://github.com/spyder-ide/spyder/pull/8245) - PR: Fix quotes and traceback lines in runcell ([8244](https://github.com/spyder-ide/spyder/issues/8244), [8242](https://github.com/spyder-ide/spyder/issues/8242))
* [PR 8243](https://github.com/spyder-ide/spyder/pull/8243) - PR : Fix for escaped string in runcell ([8241](https://github.com/spyder-ide/spyder/issues/8241))
* [PR 8222](https://github.com/spyder-ide/spyder/pull/8222) - PR: Save last accepted kernel settings in config ([3689](https://github.com/spyder-ide/spyder/issues/3689))
* [PR 8212](https://github.com/spyder-ide/spyder/pull/8212) - PR: Add system-specific shortcut names on macOS to the Shortcuts summary dialog ([7146](https://github.com/spyder-ide/spyder/issues/7146))
* [PR 8202](https://github.com/spyder-ide/spyder/pull/8202) - PR: Mark some tests as slow and skip others that are failing locally
* [PR 8201](https://github.com/spyder-ide/spyder/pull/8201) - PR: Missing dark style for QMenus, Tour, Pylint, Profiler and DataFrameEditor
* [PR 8197](https://github.com/spyder-ide/spyder/pull/8197) - PR: Add parent reference to dialogs to ensure correct setup of the dark theme
* [PR 8192](https://github.com/spyder-ide/spyder/pull/8192) - PR: Remove dockwidget title bars by default and improve dock/undock behavior ([8171](https://github.com/spyder-ide/spyder/issues/8171), [8011](https://github.com/spyder-ide/spyder/issues/8011), [5515](https://github.com/spyder-ide/spyder/issues/5515), [2855](https://github.com/spyder-ide/spyder/issues/2855), [2854](https://github.com/spyder-ide/spyder/issues/2854))
* [PR 8158](https://github.com/spyder-ide/spyder/pull/8158) - PR: Fix font color in dark theme for several widgets
* [PR 8104](https://github.com/spyder-ide/spyder/pull/8104) - PR: Hide plugins that do not have a layout ([7111](https://github.com/spyder-ide/spyder/issues/7111))
* [PR 8086](https://github.com/spyder-ide/spyder/pull/8086) - PR: Add dark css for the Help and IPython Console plugins ([8087](https://github.com/spyder-ide/spyder/issues/8087))
* [PR 8081](https://github.com/spyder-ide/spyder/pull/8081) - PR: Make all editor's background color to be applied correctly ([8069](https://github.com/spyder-ide/spyder/issues/8069))
* [PR 8079](https://github.com/spyder-ide/spyder/pull/8079) - PR: Accept event if Shift+Tab is pressed in the CodeEditor keyPressEvent to avoid losing focus
* [PR 8062](https://github.com/spyder-ide/spyder/pull/8062) - PR: Fix setting elapsed time for all consoles ([7751](https://github.com/spyder-ide/spyder/issues/7751))
* [PR 8059](https://github.com/spyder-ide/spyder/pull/8059) - Variable Explorer: Use distinctive background for missings in DataFrames ([8037](https://github.com/spyder-ide/spyder/issues/8037))
* [PR 8058](https://github.com/spyder-ide/spyder/pull/8058) - PR: Change the TODO checkmark ([2264](https://github.com/spyder-ide/spyder/issues/2264))
* [PR 8044](https://github.com/spyder-ide/spyder/pull/8044) - PR: Fix error in LSP when closing file ([8043](https://github.com/spyder-ide/spyder/issues/8043))
* [PR 8020](https://github.com/spyder-ide/spyder/pull/8020) - PR: Initial support for Spyder's dark theme
* [PR 8015](https://github.com/spyder-ide/spyder/pull/8015) - PR: Add the option to sync file order between the Outline Explorer and the current EditorStack ([7993](https://github.com/spyder-ide/spyder/issues/7993))
* [PR 8004](https://github.com/spyder-ide/spyder/pull/8004) - PR: Remove old code completion architecture ([7996](https://github.com/spyder-ide/spyder/issues/7996), [7963](https://github.com/spyder-ide/spyder/issues/7963))
* [PR 7994](https://github.com/spyder-ide/spyder/pull/7994) - PR: Refactor LSP response callback communication ([7833](https://github.com/spyder-ide/spyder/issues/7833))
* [PR 7992](https://github.com/spyder-ide/spyder/pull/7992) - PR: Add LSP client tests
* [PR 7984](https://github.com/spyder-ide/spyder/pull/7984) - PR: Show the root file item of files that are not Python files in the Outline Explorer ([7982](https://github.com/spyder-ide/spyder/issues/7982))
* [PR 7975](https://github.com/spyder-ide/spyder/pull/7975) - PR: Fix Go to definition feature in the Editor in Windows after the changes introduced with the new LSP ([7726](https://github.com/spyder-ide/spyder/issues/7726))
* [PR 7968](https://github.com/spyder-ide/spyder/pull/7968) - PR: Sync Outline Explorer at startup and preserve the file order in the tabbar ([7338](https://github.com/spyder-ide/spyder/issues/7338))
* [PR 7962](https://github.com/spyder-ide/spyder/pull/7962) - PR: Improvement to navigation and file switching in the Outline Explorer ([7214](https://github.com/spyder-ide/spyder/issues/7214))
* [PR 7954](https://github.com/spyder-ide/spyder/pull/7954) - PR: Improve how keyboard shortcuts are handled in the Editor (Take 2) ([7883](https://github.com/spyder-ide/spyder/issues/7883))
* [PR 7929](https://github.com/spyder-ide/spyder/pull/7929) - PR: Improve the Shortcut Editor and fix and extend emacs shortcut support ([7883](https://github.com/spyder-ide/spyder/issues/7883), [7854](https://github.com/spyder-ide/spyder/issues/7854), [7109](https://github.com/spyder-ide/spyder/issues/7109))
* [PR 7927](https://github.com/spyder-ide/spyder/pull/7927) - PR: Convert and optimize tutorial PNGs and profiler/pylint icons
* [PR 7914](https://github.com/spyder-ide/spyder/pull/7914) - PR: Have a choice between password or keyfile in "Connect to remote kernel" dialog ([7905](https://github.com/spyder-ide/spyder/issues/7905))
* [PR 7876](https://github.com/spyder-ide/spyder/pull/7876) - PR: Reinitialize Pylab, Sympy and Cython after clearing all variables ([7224](https://github.com/spyder-ide/spyder/issues/7224))
* [PR 7874](https://github.com/spyder-ide/spyder/pull/7874) - PR: Correct next/previous word shortcut callback in Spyder 4 ([7872](https://github.com/spyder-ide/spyder/issues/7872))
* [PR 7866](https://github.com/spyder-ide/spyder/pull/7866) - PR: Add OneColumnTree context menu item to the plugins that use it in their Options menu ([7865](https://github.com/spyder-ide/spyder/issues/7865), [7865](https://github.com/spyder-ide/spyder/issues/7865), [7235](https://github.com/spyder-ide/spyder/issues/7235))
* [PR 7852](https://github.com/spyder-ide/spyder/pull/7852) - PR: Remove '--cov-report=term-missing' from pytest args
* [PR 7835](https://github.com/spyder-ide/spyder/pull/7835) - PR: Refactor test_autoindent.py to make the pytest logs cleaner
* [PR 7827](https://github.com/spyder-ide/spyder/pull/7827) - PR: Legal, standards conformance and consistency modifications to headers and EOF/EOL
* [PR 7826](https://github.com/spyder-ide/spyder/pull/7826) - PR: Conform short dates dates to be properly ISO 8601
* [PR 7822](https://github.com/spyder-ide/spyder/pull/7822) - PR: Add pyls as a new dependency
* [PR 7799](https://github.com/spyder-ide/spyder/pull/7799) - PR: Remove file from the outline explorer when it is closed ([7798](https://github.com/spyder-ide/spyder/issues/7798))
* [PR 7789](https://github.com/spyder-ide/spyder/pull/7789) - PR: Add "find_replace" widget to qtbot in fixtures of "test_editor.py"
* [PR 7768](https://github.com/spyder-ide/spyder/pull/7768) - PR: Improve how keyboard shortcuts are handled in the Editor ([7743](https://github.com/spyder-ide/spyder/issues/7743))
* [PR 7758](https://github.com/spyder-ide/spyder/pull/7758) - PR: Fix saving a new file or renaming an existing file in master ([7754](https://github.com/spyder-ide/spyder/issues/7754))
* [PR 7745](https://github.com/spyder-ide/spyder/pull/7745) - PR: Make the "Go to cursor position" button of the outline explorer work also when the cursor is in the last item of the Editor ([7744](https://github.com/spyder-ide/spyder/issues/7744))
* [PR 7738](https://github.com/spyder-ide/spyder/pull/7738) - PR: Make Group cells setting persistent when restarting spyder ([7736](https://github.com/spyder-ide/spyder/issues/7736))
* [PR 7734](https://github.com/spyder-ide/spyder/pull/7734) - PR: Replace debug_print for the logging module and deprecate its use ([5326](https://github.com/spyder-ide/spyder/issues/5326))
* [PR 7730](https://github.com/spyder-ide/spyder/pull/7730) - PR: Add a "get_cursor_line_number" method to OutlineExplorerProxyEditor ([7729](https://github.com/spyder-ide/spyder/issues/7729))
* [PR 7725](https://github.com/spyder-ide/spyder/pull/7725) - PR: Split all plugins into their own modules ([4591](https://github.com/spyder-ide/spyder/issues/4591))
* [PR 7714](https://github.com/spyder-ide/spyder/pull/7714) - PR: Fix variable explorer actions are disabled when undocked in a new window
* [PR 7710](https://github.com/spyder-ide/spyder/pull/7710) - PR: Fix cog menu not showing in the variable explorer when more than one IPython console is opened ([7704](https://github.com/spyder-ide/spyder/issues/7704))
* [PR 7698](https://github.com/spyder-ide/spyder/pull/7698) - PR: Show normalized paths in "Create Project" dialog ([7518](https://github.com/spyder-ide/spyder/issues/7518))
* [PR 7660](https://github.com/spyder-ide/spyder/pull/7660) - PR: Implement an autosave and recover system in the Editor ([2111](https://github.com/spyder-ide/spyder/issues/2111))
* [PR 7310](https://github.com/spyder-ide/spyder/pull/7310) - PR: Run cells through a function instead of pasting their contents to the console ([7760](https://github.com/spyder-ide/spyder/issues/7760), [7113](https://github.com/spyder-ide/spyder/issues/7113))
* [PR 6791](https://github.com/spyder-ide/spyder/pull/6791) - PR: Final update to split-plugins
* [PR 6679](https://github.com/spyder-ide/spyder/pull/6679) - PR: Update split-plugins branch with master (take 3)
* [PR 6430](https://github.com/spyder-ide/spyder/pull/6430) - PR: Add a Plots plugin to browse figures generated by the IPython console ([2550](https://github.com/spyder-ide/spyder/issues/2550))
* [PR 5764](https://github.com/spyder-ide/spyder/pull/5764) - PR: Handle namespace browser column width ([5543](https://github.com/spyder-ide/spyder/issues/5543))
* [PR 5676](https://github.com/spyder-ide/spyder/pull/5676) - PR: Change word highlighting to support dot notation ([1634](https://github.com/spyder-ide/spyder/issues/1634))
* [PR 5438](https://github.com/spyder-ide/spyder/pull/5438) - PR: Merge translations from former external plugins
* [PR 5283](https://github.com/spyder-ide/spyder/pull/5283) - PR: Add a debugger panel ([8560](https://github.com/spyder-ide/spyder/issues/8560))
* [PR 5276](https://github.com/spyder-ide/spyder/pull/5276) - PR: Move external plugins inside the main package again
* [PR 5263](https://github.com/spyder-ide/spyder/pull/5263) - PR: Revert change of name for Variable Explorer editors
* [PR 5219](https://github.com/spyder-ide/spyder/pull/5219) - PR: Split Working Directory module
* [PR 5216](https://github.com/spyder-ide/spyder/pull/5216) - PR: Move preferences out of the plugins module
* [PR 5214](https://github.com/spyder-ide/spyder/pull/5214) - PR: Split Projects module
* [PR 5207](https://github.com/spyder-ide/spyder/pull/5207) - PR: Split Internal Console module
* [PR 5206](https://github.com/spyder-ide/spyder/pull/5206) - PR: Split IPython Console module
* [PR 4975](https://github.com/spyder-ide/spyder/pull/4975) - PR: Split Editor module
* [PR 4974](https://github.com/spyder-ide/spyder/pull/4974) - PR: Split Explorer module
* [PR 4812](https://github.com/spyder-ide/spyder/pull/4812) - PR: Split Outline explorer module
* [PR 4772](https://github.com/spyder-ide/spyder/pull/4772) - PR: Merge master into split-plugins
* [PR 4751](https://github.com/spyder-ide/spyder/pull/4751) - PR: Migrate introspection services to use the Language Server Protocol (LSP) ([4742](https://github.com/spyder-ide/spyder/issues/4742))
* [PR 4593](https://github.com/spyder-ide/spyder/pull/4593) - PR: Split History module
* [PR 4569](https://github.com/spyder-ide/spyder/pull/4569) - PR: Split Find in Files module
* [PR 4565](https://github.com/spyder-ide/spyder/pull/4565) - PR: Split Online Help module
* [PR 4557](https://github.com/spyder-ide/spyder/pull/4557) - PR: Split Variable Explorer module
* [PR 4548](https://github.com/spyder-ide/spyder/pull/4548) - PR: Split Help plugin

In this release 246 pull requests were closed.


----


## Version 4.0beta1 (2018-08-12)

### Issues Closed

* [Issue 7078](https://github.com/spyder-ide/spyder/issues/7078) - Shortcuts to open pylab and sympy consoles  ([PR 7099](https://github.com/spyder-ide/spyder/pull/7099))
* [Issue 6516](https://github.com/spyder-ide/spyder/issues/6516) - AttributeError in jedi_plugin.py:102 ([PR 6523](https://github.com/spyder-ide/spyder/pull/6523))
* [Issue 6474](https://github.com/spyder-ide/spyder/issues/6474) - test_completions_custom_path fails with jedi 0.9.0 (Spyder 4) ([PR 6497](https://github.com/spyder-ide/spyder/pull/6497))
* [Issue 5821](https://github.com/spyder-ide/spyder/issues/5821) - Outline Explorer: disable `if/else/try/for` statements ([PR 5842](https://github.com/spyder-ide/spyder/pull/5842))
* [Issue 5763](https://github.com/spyder-ide/spyder/issues/5763) - Make arrow-key selection in multiple-option tab-completion dialogs "roll over" ([PR 5771](https://github.com/spyder-ide/spyder/pull/5771))
* [Issue 5756](https://github.com/spyder-ide/spyder/issues/5756) - Ctrl-PageUp/Down does not go through tabs in Spyder 4.x
* [Issue 5721](https://github.com/spyder-ide/spyder/issues/5721) - Update obsolete QMessageBox Standard Button values ([PR 5722](https://github.com/spyder-ide/spyder/pull/5722))
* [Issue 5711](https://github.com/spyder-ide/spyder/issues/5711) - "Show blank spaces" with split view editor
* [Issue 5678](https://github.com/spyder-ide/spyder/issues/5678) - Fix Indentation always uses 4 spaces instead of the selected number of spaces ([PR 6063](https://github.com/spyder-ide/spyder/pull/6063))
* [Issue 5667](https://github.com/spyder-ide/spyder/issues/5667) - Strange font rendering in the splash ([PR 5706](https://github.com/spyder-ide/spyder/pull/5706))
* [Issue 5652](https://github.com/spyder-ide/spyder/issues/5652) - Improved dependency dialog ([PR 5691](https://github.com/spyder-ide/spyder/pull/5691))
* [Issue 5639](https://github.com/spyder-ide/spyder/issues/5639) - Use argparse instead of optparse ([PR 5689](https://github.com/spyder-ide/spyder/pull/5689))
* [Issue 5594](https://github.com/spyder-ide/spyder/issues/5594) - Right-clicking in empty Project Explorer shows error ([PR 5603](https://github.com/spyder-ide/spyder/pull/5603))
* [Issue 5488](https://github.com/spyder-ide/spyder/issues/5488) - Code style (pep8) toggle in source menu ([PR 5497](https://github.com/spyder-ide/spyder/pull/5497))
* [Issue 5486](https://github.com/spyder-ide/spyder/issues/5486) - Spyder crash when dragging a plugin with the mouse ([PR 5487](https://github.com/spyder-ide/spyder/pull/5487))
* [Issue 5458](https://github.com/spyder-ide/spyder/issues/5458) - Can't indent code blocks more than once (using tab) on Spyder 4 ([PR 5468](https://github.com/spyder-ide/spyder/pull/5468))
* [Issue 5454](https://github.com/spyder-ide/spyder/issues/5454) - Toggle comment (ctrl+1) does not always preserve indentation with 2 spaces ([PR 5470](https://github.com/spyder-ide/spyder/pull/5470))
* [Issue 5365](https://github.com/spyder-ide/spyder/issues/5365) - Add "Save all files with <eol> EOL characters" option ([PR 5367](https://github.com/spyder-ide/spyder/pull/5367))
* [Issue 5256](https://github.com/spyder-ide/spyder/issues/5256) - Update spyder splash for spyder4 ([PR 5262](https://github.com/spyder-ide/spyder/pull/5262))
* [Issue 5176](https://github.com/spyder-ide/spyder/issues/5176) - Unify how extra selection are added to the editor
* [Issue 5171](https://github.com/spyder-ide/spyder/issues/5171) - Variable explorer showing different format when using MultiIndex ([PR 3873](https://github.com/spyder-ide/spyder/pull/3873))
* [Issue 5131](https://github.com/spyder-ide/spyder/issues/5131) - Sources checkable preferences aren't sync with preferences
* [Issue 5116](https://github.com/spyder-ide/spyder/issues/5116) - Internal console error when selecting Source -> Next warning/error (or Previous warning/error) ([PR 5117](https://github.com/spyder-ide/spyder/pull/5117))
* [Issue 5085](https://github.com/spyder-ide/spyder/issues/5085) - There are two scroll bars in the Editor ([PR 5215](https://github.com/spyder-ide/spyder/pull/5215))
* [Issue 4963](https://github.com/spyder-ide/spyder/issues/4963) - Open project error ([PR 4968](https://github.com/spyder-ide/spyder/pull/4968))
* [Issue 4948](https://github.com/spyder-ide/spyder/issues/4948) - Class function dropdown should be deactivated by default
* [Issue 4884](https://github.com/spyder-ide/spyder/issues/4884) - prefix 'b' of bytes is not highlighting in the editor window ([PR 5011](https://github.com/spyder-ide/spyder/pull/5011))
* [Issue 4854](https://github.com/spyder-ide/spyder/issues/4854) - Error when trying to show indentation guidelines ([PR 4889](https://github.com/spyder-ide/spyder/pull/4889))
* [Issue 4787](https://github.com/spyder-ide/spyder/issues/4787) - Show spaces bug at start ([PR 4788](https://github.com/spyder-ide/spyder/pull/4788))
* [Issue 4778](https://github.com/spyder-ide/spyder/issues/4778) - Code folding does not open the correct line from the backtrace of the ipython window
* [Issue 4777](https://github.com/spyder-ide/spyder/issues/4777) - Code folding does not support clicking left to the line numbers (editor)
* [Issue 4709](https://github.com/spyder-ide/spyder/issues/4709) - Find does not open code-folded blocks ([PR 4731](https://github.com/spyder-ide/spyder/pull/4731))
* [Issue 4708](https://github.com/spyder-ide/spyder/issues/4708) - Code folding is wrong on commented lines ([PR 4728](https://github.com/spyder-ide/spyder/pull/4728))
* [Issue 4705](https://github.com/spyder-ide/spyder/issues/4705) - Unable to vertically split window
* [Issue 4590](https://github.com/spyder-ide/spyder/issues/4590) - Improve floating panels in the editor  ([PR 5132](https://github.com/spyder-ide/spyder/pull/5132))
* [Issue 4543](https://github.com/spyder-ide/spyder/issues/4543) - Code completion widget misplaced in the Editor ([PR 4545](https://github.com/spyder-ide/spyder/pull/4545))
* [Issue 4463](https://github.com/spyder-ide/spyder/issues/4463) - Code folding does not work on indentation level 0
* [Issue 4423](https://github.com/spyder-ide/spyder/issues/4423) - Missing manpage for spyder ([PR 4506](https://github.com/spyder-ide/spyder/pull/4506))
* [Issue 4376](https://github.com/spyder-ide/spyder/issues/4376) - Tab switcher dialog is not populated completely ([PR 4392](https://github.com/spyder-ide/spyder/pull/4392))
* [Issue 4153](https://github.com/spyder-ide/spyder/issues/4153) - vertical end-of-line in wrong place
* [Issue 4147](https://github.com/spyder-ide/spyder/issues/4147) - Improve visual style of code folding
* [Issue 4124](https://github.com/spyder-ide/spyder/issues/4124) - language reset to japanese on reboot ([PR 4159](https://github.com/spyder-ide/spyder/pull/4159))
* [Issue 4081](https://github.com/spyder-ide/spyder/issues/4081) - Add keyboard shortcuts for Source > Next|Previous Warning/Error ([PR 5126](https://github.com/spyder-ide/spyder/pull/5126))
* [Issue 4018](https://github.com/spyder-ide/spyder/issues/4018) - Add multiindex header support for the Variable Explorer ([PR 3873](https://github.com/spyder-ide/spyder/pull/3873))
* [Issue 3942](https://github.com/spyder-ide/spyder/issues/3942) - Error when deleting the file with last focus in a project ([PR 3953](https://github.com/spyder-ide/spyder/pull/3953))
* [Issue 3923](https://github.com/spyder-ide/spyder/issues/3923) - Profiler error when no filename is passed to it ([PR 3909](https://github.com/spyder-ide/spyder/pull/3909))
* [Issue 3887](https://github.com/spyder-ide/spyder/issues/3887) - Menus "File",  "Edit" and "Search" in master not available for mouse click ([PR 3892](https://github.com/spyder-ide/spyder/pull/3892))
* [Issue 3857](https://github.com/spyder-ide/spyder/issues/3857) - Go to line doesn't correspond to the correct file ([PR 5321](https://github.com/spyder-ide/spyder/pull/5321))
* [Issue 3790](https://github.com/spyder-ide/spyder/issues/3790) - Create new windows when undocking all plugins ([PR 3824](https://github.com/spyder-ide/spyder/pull/3824))
* [Issue 3758](https://github.com/spyder-ide/spyder/issues/3758) - Variable explorer should show variables of type pandas.indexes.base.Index ([PR 5149](https://github.com/spyder-ide/spyder/pull/5149))
* [Issue 3721](https://github.com/spyder-ide/spyder/issues/3721) - DataFrame viewer should display tooltips for truncated column headers ([PR 3873](https://github.com/spyder-ide/spyder/pull/3873))
* [Issue 3645](https://github.com/spyder-ide/spyder/issues/3645) - Autocompletion on Python consoles is crashing in master ([PR 3650](https://github.com/spyder-ide/spyder/pull/3650))
* [Issue 3592](https://github.com/spyder-ide/spyder/issues/3592) - Add multiple edgelines options in settings window ([PR 3607](https://github.com/spyder-ide/spyder/pull/3607))
* [Issue 3591](https://github.com/spyder-ide/spyder/issues/3591) - DataFrame viewer should use custom index name
* [Issue 3585](https://github.com/spyder-ide/spyder/issues/3585) - Editor grabs focus when opening files at startup ([PR 3858](https://github.com/spyder-ide/spyder/pull/3858))
* [Issue 3571](https://github.com/spyder-ide/spyder/issues/3571) - Help fails to produce Rich Text on annotated functions ([PR 3577](https://github.com/spyder-ide/spyder/pull/3577))
* [Issue 3563](https://github.com/spyder-ide/spyder/issues/3563) - Docks confusion when pressing undocking button ([PR 3824](https://github.com/spyder-ide/spyder/pull/3824))
* [Issue 3448](https://github.com/spyder-ide/spyder/issues/3448) - Break plugin creation into a spyder/api module for better decoupling and organization ([PR 3468](https://github.com/spyder-ide/spyder/pull/3468))
* [Issue 3345](https://github.com/spyder-ide/spyder/issues/3345) - Feature suggestion:  scroll over the end of file in the editor ([PR 5122](https://github.com/spyder-ide/spyder/pull/5122))
* [Issue 2987](https://github.com/spyder-ide/spyder/issues/2987) - Add feature that shows vertical lines to help identifying indentation structure
* [Issue 2845](https://github.com/spyder-ide/spyder/issues/2845) - Comment out lines according to indentation ([PR 3958](https://github.com/spyder-ide/spyder/pull/3958))
* [Issue 2627](https://github.com/spyder-ide/spyder/issues/2627) - Add optional display of current class/function that you're in. ([PR 4225](https://github.com/spyder-ide/spyder/pull/4225))
* [Issue 2553](https://github.com/spyder-ide/spyder/issues/2553) - Share code with gtabview
* [Issue 2419](https://github.com/spyder-ide/spyder/issues/2419) - Shortcuts for splitting and closing panels ([PR 5512](https://github.com/spyder-ide/spyder/pull/5512))
* [Issue 2406](https://github.com/spyder-ide/spyder/issues/2406) - File explorer enhancements ([PR 4939](https://github.com/spyder-ide/spyder/pull/4939))
* [Issue 2355](https://github.com/spyder-ide/spyder/issues/2355) - Variable Explorer does not show sets ([PR 5230](https://github.com/spyder-ide/spyder/pull/5230))
* [Issue 1785](https://github.com/spyder-ide/spyder/issues/1785) - Spyder comments (Ctrl+1 and Ctrl+4) generate pep8 warnings ([PR 3958](https://github.com/spyder-ide/spyder/pull/3958))
* [Issue 1778](https://github.com/spyder-ide/spyder/issues/1778) - Add a 72-char vertical line for docstrings ([PR 3512](https://github.com/spyder-ide/spyder/pull/3512))
* [Issue 1754](https://github.com/spyder-ide/spyder/issues/1754) - No undo for Source->Fix identation
* [Issue 1584](https://github.com/spyder-ide/spyder/issues/1584) - Newline added to default file ([PR 5797](https://github.com/spyder-ide/spyder/pull/5797))
* [Issue 1396](https://github.com/spyder-ide/spyder/issues/1396) - Autocomplete doesnt work in undocked Editor window
* [Issue 970](https://github.com/spyder-ide/spyder/issues/970) - History plugin: add an option to show/hide line numbers ([PR 5363](https://github.com/spyder-ide/spyder/pull/5363))
* [Issue 877](https://github.com/spyder-ide/spyder/issues/877) - Quote by select + ' or "
* [Issue 706](https://github.com/spyder-ide/spyder/issues/706) - Code folding missing in the Editor ([PR 3833](https://github.com/spyder-ide/spyder/pull/3833))

In this release 74 issues were closed.

### Pull Requests Merged

* [PR 7597](https://github.com/spyder-ide/spyder/pull/7597) - PR: Separate startup run_lines with semicolon instead of comma
* [PR 7410](https://github.com/spyder-ide/spyder/pull/7410) - PR: Remove manpage
* [PR 7262](https://github.com/spyder-ide/spyder/pull/7262) - PR: Update donation/funding status message in Readme
* [PR 7167](https://github.com/spyder-ide/spyder/pull/7167) - PR: Remove missing PyQt4 references in our tests
* [PR 7107](https://github.com/spyder-ide/spyder/pull/7107) - PR: Show group cells in Outline Explorer ([7086](https://github.com/spyder-ide/spyder/issues/7086))
* [PR 7099](https://github.com/spyder-ide/spyder/pull/7099) - PR: Add new menu entries to open Pylab, Sympy and Cython consoles ([7078](https://github.com/spyder-ide/spyder/issues/7078))
* [PR 6923](https://github.com/spyder-ide/spyder/pull/6923) - PR: Improve and update wording of funding announcement, and put screenshot above it
* [PR 6523](https://github.com/spyder-ide/spyder/pull/6523) - PR: Fix AttributeError in jedi_plugin ([6516](https://github.com/spyder-ide/spyder/issues/6516))
* [PR 6497](https://github.com/spyder-ide/spyder/pull/6497) - PR: Bump required version for Jedi to 0.11.0  ([6474](https://github.com/spyder-ide/spyder/issues/6474))
* [PR 6440](https://github.com/spyder-ide/spyder/pull/6440) - PR: Skip test_window_title in PyQt4 and PY3 because it's failing
* [PR 6340](https://github.com/spyder-ide/spyder/pull/6340) - PR: Fix EditorStack and EditorSplitter not closing correctly.
* [PR 6296](https://github.com/spyder-ide/spyder/pull/6296) - PR: Fix tests on Travis
* [PR 6151](https://github.com/spyder-ide/spyder/pull/6151) - PR: Hide unneeded Options buttons
* [PR 6133](https://github.com/spyder-ide/spyder/pull/6133) - PR: Fix test_dataframemodel_set_data_overflow
* [PR 6079](https://github.com/spyder-ide/spyder/pull/6079) - PR: Fix flaky test_find_in_files_search
* [PR 6063](https://github.com/spyder-ide/spyder/pull/6063) - PR: Change fix_indentation to use preference for number of spaces ([5678](https://github.com/spyder-ide/spyder/issues/5678))
* [PR 5842](https://github.com/spyder-ide/spyder/pull/5842) - PR: Remove `if/else/try/for` statements from the outline explorer tree ([5821](https://github.com/spyder-ide/spyder/issues/5821))
* [PR 5836](https://github.com/spyder-ide/spyder/pull/5836) - PR: Give a more modern appearence to the tour
* [PR 5797](https://github.com/spyder-ide/spyder/pull/5797) - PR: Don't add extra newline when using new file template ([1584](https://github.com/spyder-ide/spyder/issues/1584))
* [PR 5771](https://github.com/spyder-ide/spyder/pull/5771) - PR: Make arrow-key selection in completion widget "roll over" ([5763](https://github.com/spyder-ide/spyder/issues/5763))
* [PR 5768](https://github.com/spyder-ide/spyder/pull/5768) - PR: Fix broken shortcuts for changing editor tabs (Ctrl+PageUp, Ctrl+PageDown)
* [PR 5722](https://github.com/spyder-ide/spyder/pull/5722) - PR: Update obsolete enums in QMessageBox ([5721](https://github.com/spyder-ide/spyder/issues/5721))
* [PR 5706](https://github.com/spyder-ide/spyder/pull/5706) - PR: Splash SVG font change and convert font to path ([5667](https://github.com/spyder-ide/spyder/issues/5667))
* [PR 5691](https://github.com/spyder-ide/spyder/pull/5691) - PR: Improve dependencies dialog ([5652](https://github.com/spyder-ide/spyder/issues/5652))
* [PR 5689](https://github.com/spyder-ide/spyder/pull/5689) - PR: Convert command line options from optparse to argparse ([5639](https://github.com/spyder-ide/spyder/issues/5639))
* [PR 5657](https://github.com/spyder-ide/spyder/pull/5657) - PR: Allow undo/redo on Source > Fix indentation
* [PR 5603](https://github.com/spyder-ide/spyder/pull/5603) - PR: Fix crash on empty project explorer context menu ([5594](https://github.com/spyder-ide/spyder/issues/5594))
* [PR 5512](https://github.com/spyder-ide/spyder/pull/5512) - PR: Add shortcuts for splitting and closing panels ([2419](https://github.com/spyder-ide/spyder/issues/2419))
* [PR 5497](https://github.com/spyder-ide/spyder/pull/5497) - PR: Add option to toggle code style checks from Source menu ([5488](https://github.com/spyder-ide/spyder/issues/5488))
* [PR 5487](https://github.com/spyder-ide/spyder/pull/5487) - PR: Handle 'unlocked panes' state for undocking without generating a new window ([5486](https://github.com/spyder-ide/spyder/issues/5486))
* [PR 5471](https://github.com/spyder-ide/spyder/pull/5471) - PR: Fix test_sort_dataframe_with_category_dtypes
* [PR 5470](https://github.com/spyder-ide/spyder/pull/5470) - PR: Use indentation preferences to comment/uncomment. ([5454](https://github.com/spyder-ide/spyder/issues/5454))
* [PR 5468](https://github.com/spyder-ide/spyder/pull/5468) - PR: Fix indentation with selection ([5458](https://github.com/spyder-ide/spyder/issues/5458))
* [PR 5367](https://github.com/spyder-ide/spyder/pull/5367) - PR: Add an option to the Editor to convert EOL characters on save ([5365](https://github.com/spyder-ide/spyder/issues/5365))
* [PR 5363](https://github.com/spyder-ide/spyder/pull/5363) - PR: Add an option to show/hide line numbers to History ([970](https://github.com/spyder-ide/spyder/issues/970))
* [PR 5321](https://github.com/spyder-ide/spyder/pull/5321) - PR: Rearrange line count when opening files to correspond to the correct one ([3857](https://github.com/spyder-ide/spyder/issues/3857))
* [PR 5309](https://github.com/spyder-ide/spyder/pull/5309) - PR: Update font decorations when adding them to the editor.
* [PR 5274](https://github.com/spyder-ide/spyder/pull/5274) - PR: Remove duplicated logic in Editor checkable Actions
* [PR 5262](https://github.com/spyder-ide/spyder/pull/5262) - PR: Update version in splash screen ([5256](https://github.com/spyder-ide/spyder/issues/5256))
* [PR 5230](https://github.com/spyder-ide/spyder/pull/5230) - PR: Support for sets in the Variable Explorer ([2355](https://github.com/spyder-ide/spyder/issues/2355))
* [PR 5215](https://github.com/spyder-ide/spyder/pull/5215) - PR: Scroll flag area improvements ([5085](https://github.com/spyder-ide/spyder/issues/5085))
* [PR 5203](https://github.com/spyder-ide/spyder/pull/5203) - PR: Unify how extra selections are added to the Editor
* [PR 5159](https://github.com/spyder-ide/spyder/pull/5159) - PR: Make Ctrl+C to quit Spyder on Posix systems ([5305](https://github.com/spyder-ide/spyder/issues/5305))
* [PR 5149](https://github.com/spyder-ide/spyder/pull/5149) - PR: Support for all Pandas indexes in Variable Explorer ([3758](https://github.com/spyder-ide/spyder/issues/3758))
* [PR 5139](https://github.com/spyder-ide/spyder/pull/5139) - PR: Fix error Editor loosing focus
* [PR 5132](https://github.com/spyder-ide/spyder/pull/5132) - PR: Improve how floating panels are painted ([4590](https://github.com/spyder-ide/spyder/issues/4590))
* [PR 5130](https://github.com/spyder-ide/spyder/pull/5130) - PR: Deactivate class/function dropdown by default
* [PR 5126](https://github.com/spyder-ide/spyder/pull/5126) - PR: Add keyboard shortcuts for Next|Previous Warning/Error ([4081](https://github.com/spyder-ide/spyder/issues/4081))
* [PR 5122](https://github.com/spyder-ide/spyder/pull/5122) - PR: Enable scrolling past the end of the document ([3345](https://github.com/spyder-ide/spyder/issues/3345))
* [PR 5117](https://github.com/spyder-ide/spyder/pull/5117) - PR: Fix traceback error when selecting Next/Previous warning/error ([5116](https://github.com/spyder-ide/spyder/issues/5116))
* [PR 5083](https://github.com/spyder-ide/spyder/pull/5083) - PR: Fix unable to split editor
* [PR 5011](https://github.com/spyder-ide/spyder/pull/5011) - PR: Add all possible string prefixes for syntax highlighting ([4884](https://github.com/spyder-ide/spyder/issues/4884))
* [PR 5002](https://github.com/spyder-ide/spyder/pull/5002) - PR: Add Editor extensions
* [PR 4968](https://github.com/spyder-ide/spyder/pull/4968) - PR: Fix error when threre are no layout settings ([4963](https://github.com/spyder-ide/spyder/issues/4963))
* [PR 4939](https://github.com/spyder-ide/spyder/pull/4939) - PR: Some File Explorer Enhancements ([2406](https://github.com/spyder-ide/spyder/issues/2406))
* [PR 4889](https://github.com/spyder-ide/spyder/pull/4889) - PR: Fix error at startup when trying to set indent_guides. ([4854](https://github.com/spyder-ide/spyder/issues/4854))
* [PR 4804](https://github.com/spyder-ide/spyder/pull/4804) - PR: Fix some code folding related errors
* [PR 4788](https://github.com/spyder-ide/spyder/pull/4788) - PR: Add validation for editorstacks in showing spaces function ([4787](https://github.com/spyder-ide/spyder/issues/4787))
* [PR 4762](https://github.com/spyder-ide/spyder/pull/4762) - PR: Add missing QMessageBox import
* [PR 4731](https://github.com/spyder-ide/spyder/pull/4731) - PR: Make searching text to expand folded blocks ([4709](https://github.com/spyder-ide/spyder/issues/4709))
* [PR 4728](https://github.com/spyder-ide/spyder/pull/4728) - PR: Make folding to ignore indented comments ([4708](https://github.com/spyder-ide/spyder/issues/4708))
* [PR 4627](https://github.com/spyder-ide/spyder/pull/4627) - PR: Add pyopengl to Linux wheels only
* [PR 4618](https://github.com/spyder-ide/spyder/pull/4618) - PR: Add German translation
* [PR 4572](https://github.com/spyder-ide/spyder/pull/4572) - PR: Add indentation guidelines
* [PR 4545](https://github.com/spyder-ide/spyder/pull/4545) - PR: Take panels widths into account when calculating positions in the Editor  ([4543](https://github.com/spyder-ide/spyder/issues/4543))
* [PR 4540](https://github.com/spyder-ide/spyder/pull/4540) - PR: Fix update title signal
* [PR 4538](https://github.com/spyder-ide/spyder/pull/4538) - PR: Add Shift+Del shortcut to delete lines in the Editor  ([4496](https://github.com/spyder-ide/spyder/issues/4496), [3405](https://github.com/spyder-ide/spyder/issues/3405))
* [PR 4506](https://github.com/spyder-ide/spyder/pull/4506) - PR: Add manpage for Spyder ([4423](https://github.com/spyder-ide/spyder/issues/4423))
* [PR 4505](https://github.com/spyder-ide/spyder/pull/4505) - PR: Fix links to Fedora and openSUSE in docs
* [PR 4503](https://github.com/spyder-ide/spyder/pull/4503) - PR: Fold improvements
* [PR 4470](https://github.com/spyder-ide/spyder/pull/4470) - PR: Fix error in Find in Files because of changes in master
* [PR 4392](https://github.com/spyder-ide/spyder/pull/4392) - PR: Update StackHistory when focus isn't given to the Editor ([4376](https://github.com/spyder-ide/spyder/issues/4376))
* [PR 4286](https://github.com/spyder-ide/spyder/pull/4286) - PR: Only show removal message in Python consoles ([4284](https://github.com/spyder-ide/spyder/issues/4284))
* [PR 4265](https://github.com/spyder-ide/spyder/pull/4265) - PR: Improvements to visual style of code-folding
* [PR 4234](https://github.com/spyder-ide/spyder/pull/4234) - PR: Fix test that looks for print statements
* [PR 4225](https://github.com/spyder-ide/spyder/pull/4225) - PR: Add a new panel to show/explore class and methods/functions present in the current file ([2627](https://github.com/spyder-ide/spyder/issues/2627))
* [PR 4210](https://github.com/spyder-ide/spyder/pull/4210) - PR: Fix syntax highlighter missing Cython keywords
* [PR 4198](https://github.com/spyder-ide/spyder/pull/4198) - PR : Add Cython files import and run support
* [PR 4164](https://github.com/spyder-ide/spyder/pull/4164) - PR: Fix error edgeline offset, take code folding panel width in account. ([4163](https://github.com/spyder-ide/spyder/issues/4163))
* [PR 4162](https://github.com/spyder-ide/spyder/pull/4162) - PR: Fix wrong usage of is_text_string
* [PR 4159](https://github.com/spyder-ide/spyder/pull/4159) - PR: Try to eval string setting values after decoding in python2.7 ([4124](https://github.com/spyder-ide/spyder/issues/4124))
* [PR 4155](https://github.com/spyder-ide/spyder/pull/4155) - PR: Fix error edge line in python2.7
* [PR 3958](https://github.com/spyder-ide/spyder/pull/3958) - PR: Comment lines taking into account code indentation and pep8 ([2845](https://github.com/spyder-ide/spyder/issues/2845), [1785](https://github.com/spyder-ide/spyder/issues/1785))
* [PR 3953](https://github.com/spyder-ide/spyder/pull/3953) - PR: Prevent error when file with last focus is deleted from project ([3942](https://github.com/spyder-ide/spyder/issues/3942))
* [PR 3937](https://github.com/spyder-ide/spyder/pull/3937) - PR: Change ScrollFlagArea panel to use panel API
* [PR 3909](https://github.com/spyder-ide/spyder/pull/3909) - PR: Fix "TypeError: got multiple values for argument" in Profiler ([3923](https://github.com/spyder-ide/spyder/issues/3923))
* [PR 3892](https://github.com/spyder-ide/spyder/pull/3892) - PR: Raise the menu bar to the top of the main window widget's stack. ([3887](https://github.com/spyder-ide/spyder/issues/3887))
* [PR 3873](https://github.com/spyder-ide/spyder/pull/3873) - PR: Add multi-index display support to the Dataframe editor ([5171](https://github.com/spyder-ide/spyder/issues/5171), [4018](https://github.com/spyder-ide/spyder/issues/4018), [3721](https://github.com/spyder-ide/spyder/issues/3721))
* [PR 3858](https://github.com/spyder-ide/spyder/pull/3858) - PR: Load files in the background and set focus to the last one with focus in the previous session ([3585](https://github.com/spyder-ide/spyder/issues/3585))
* [PR 3833](https://github.com/spyder-ide/spyder/pull/3833) - PR: Add code folding to the Editor ([706](https://github.com/spyder-ide/spyder/issues/706))
* [PR 3824](https://github.com/spyder-ide/spyder/pull/3824) - PR: Create a separate window when undocking plugins ([3790](https://github.com/spyder-ide/spyder/issues/3790), [3563](https://github.com/spyder-ide/spyder/issues/3563))
* [PR 3803](https://github.com/spyder-ide/spyder/pull/3803) - PR: Add CircleCI to run pytest, ciocheck and coveralls
* [PR 3778](https://github.com/spyder-ide/spyder/pull/3778) - PR: Add Panels and PanelsManager, and use it to add LineNumberArea to editor
* [PR 3727](https://github.com/spyder-ide/spyder/pull/3727) - PR: Remove SpyderPluginMixin and improve external API
* [PR 3676](https://github.com/spyder-ide/spyder/pull/3676) - PR: Refactor and simplify NamespaceBrowser widget
* [PR 3650](https://github.com/spyder-ide/spyder/pull/3650) - PR: Revert error introduced by linenumber migration ([3645](https://github.com/spyder-ide/spyder/issues/3645))
* [PR 3607](https://github.com/spyder-ide/spyder/pull/3607) - PR: Multiple edge lines preferences ([3592](https://github.com/spyder-ide/spyder/issues/3592), [1778](https://github.com/spyder-ide/spyder/issues/1778))
* [PR 3577](https://github.com/spyder-ide/spyder/pull/3577) - PR: Use inspect.getfullargspec() in getdoc for PY3 to support annotated functions. ([3571](https://github.com/spyder-ide/spyder/issues/3571))
* [PR 3574](https://github.com/spyder-ide/spyder/pull/3574) - PR: Improve style of scientific startup script
* [PR 3534](https://github.com/spyder-ide/spyder/pull/3534) - PR: Added the Solarized color scheme
* [PR 3512](https://github.com/spyder-ide/spyder/pull/3512) - PR: Move edge line code out of editor to EdgeLine class ([1778](https://github.com/spyder-ide/spyder/issues/1778))
* [PR 3468](https://github.com/spyder-ide/spyder/pull/3468) - PR: Move plugin creation to spyder/api/plugins.py for decoupling  ([3448](https://github.com/spyder-ide/spyder/issues/3448))
* [PR 3463](https://github.com/spyder-ide/spyder/pull/3463) - PR: Migrate line number area to a panel widget
* [PR 2431](https://github.com/spyder-ide/spyder/pull/2431) - PR: Use right python.exe to run Spyder when multiple versions of Python are installled on Windows

In this release 104 pull requests were closed.
