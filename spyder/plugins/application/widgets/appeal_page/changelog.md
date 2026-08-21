# History of changes

## Version 6.2.0a2 (2026-08-19)

### New features

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
* Add button to close all open viewers to the Variable Explorer and its viewers.
* Add shortcuts and menu entries to expand/collapse all foldable regions in the
  Editor to the `Source` menu.
* Add support to introduce inline (or ghost) completions to the Editor.

### Important fixes

* Base the standalone installers in Python 3.13.
* Sign the Windows standalone installer so it's not flagged as untrusted.
* Add support for PySide6 6.9+.
* Automatically disable plugins when users disable the ones they depend on (e.g.
  the Variable Explorer, Debugger and Plots will be auto-disabled if the
  IPython Console is disabled because they can't do anything without it).
* Drop support for Python 3.9 and 3.10.tions.
