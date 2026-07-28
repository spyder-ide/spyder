# History of changes

## Version 6.1.6 (2026-07-28)

### New features

* Add support for Jedi 0.20.0
* Add support for python-lsp-server 1.15.0

### Important fixes

* Prevent Variable Explorer editors for arrays and dataframes to go to the background.
* Prevent IPython Console to steal focus on startup.
* Improvements to shortcuts dialog UI and prevent duplicated key sequences additions.
* Fix syntax highlighting of `match` and `case` builtins.
* Show error message for lack of disk space while updating.
* Fix batch script run when a space is present in the file path.
* Fix docstring generation with nested functions.
