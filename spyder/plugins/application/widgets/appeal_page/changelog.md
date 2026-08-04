# History of changes

## Version 6.1.6 (2026-07-28)

### New features

* Add support for Jedi 0.20.0
* Add support for python-lsp-server 1.15.0

### Important fixes

* Prevent Variable Explorer viewers for arrays and dataframes to go to the
  background on macOS.
* Prevent Spyder to steal focus from other applications at startup.
* Prevent duplicate key sequences when changing shortcuts in Preferences.
* Fix syntax highlighting of `match` and `case` builtins.
* Fix running batch scripts with spaces in their path on Windows.
* Fix docstring generation for nested functions.
