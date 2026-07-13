# History of changes

## Version 6.2.0a1 (2026-07-09)

### New features

* Add a new set of interface themes for the entire application, including popular
  ones from other IDEs such as Dracula, Miami Nights and Grubvox. They can be
  set in `Preferences > Appearance`.
* Support Polars series in the Variable Explorer.
* Add button to close all open viewers to the Variable Explorer and its viewers.
* Add shortcuts and menu entries to expand/collapse all foldable regions in the
  Editor to the `Source` menu.
* Add support to introduce inline (or ghost) completions to the Editor.

### Important fixes

* Automatically disable plugins when users disable the ones they depend on (e.g.
  the Variable Explorer, Debugger and Plots will be auto-disabled if the
  IPython Console is disabled because they can't do anything without it).
* Drop support for Python 3.9 and 3.10.
