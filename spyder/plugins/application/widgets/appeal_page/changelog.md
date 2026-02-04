# History of changes

## Version 6.1.2 (2025-12-17)

### New features

* Set a maximum number of plots in the Plots pane to prevent a memory leak when generating many of them.
* Simplify UX to create directories and files from the files/project explorer.
* Add support for Pylint 4.

### Important fixes

* Fix update process for installer based installations that require admin permissions on Windows.
* Fix Profiler error when the IPython console kernel takes time to start.
* General fixes to the API module (`spyder.api`) docstrings and typings.
