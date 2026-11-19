# Changes in version 6.2.0a4 (2026-11-12)

## New features

* Add a new set of interface themes for the entire application, including popular
  ones from other IDEs such as Dracula, Miami Nights and Grubvox. They can be
  set in `Preferences > Appearance`.
* Add a button to export Pandas dataframes to Excel, CSV or Json to the dataframe
  viewer.
* Support Polars series in the Variable Explorer.
* Add submenu `File > Export` to export the current file in the Editor to HTML or
  RTF.
* Make copy/paste text in the Editor to Microsoft Word or similar programs grab
  the syntax highlighting theme too.
* Add `Ctrl+Alt+Up/Down` shortcuts to move to the next/previous prompt in the
  IPython console.
* Add button to close all open viewers to the Variable Explorer and its viewers.
* Add shortcuts and menu entries to expand/collapse all foldable regions in the
  Editor to the `Source` menu.
* Allow Editor and IPython console tabs to be reordered from the browse tabs menu
  (i.e. the one to the left of tabs) by keeping `Shift` pressed and dragging its
  entries with the left mouse button.
* The position for the close button in tabs (left, right or automatic) can be
  configured in `Preferences > Application > Panes`.
* Add `--reset-hdpi-settings` command line option to reset incorrect high
  resolution screen settings without altering other options.
* Add support to introduce inline (or ghost) completions to the Editor.
* Add a `LanguageServices` plugin that merges completions, hover, linting,
  formatting and the other language features from several providers per
  language, with per-feature request policies configurable in
  `Preferences > Completion and linting`. Its LSP client provider runs any
  number of language servers described only by configuration and detects the
  languages a server registers.

## Important fixes

* Add support for PyQt6 and drop it for PyQt5.
* Base the standalone installers in Python 3.13.
* Sign the Windows standalone installer so it's not flagged as untrusted.
* Greatly improve support to work with Windows network share folders in the
  Files pane.
* Make Spyder projects automatically ignore files in `.gitignore` when tracking
  changes.
* Add support for PySide6 6.9+.
* Automatically disable plugins when users disable the ones they depend on (e.g.
  the Variable Explorer, Debugger and Plots will be auto-disabled if the
  IPython Console is disabled because they can't do anything without it).
* Drop support for Python 3.9 and 3.10.

## Full changelog

* View the complete changelog [on GitHub](https://github.com/spyder-ide/spyder/blob/master/changelogs/Spyder-6.md#version-620a4-2026-11-12).
