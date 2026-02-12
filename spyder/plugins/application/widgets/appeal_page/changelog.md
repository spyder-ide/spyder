# History of changes

## Version 6.1.3 (2026-02-12)

### New features

* Allow to reconnect to remote kernels after the connection is lost.
* Add ability to explore objects that depend on custom library code to the
  Variable Explorer.

### Important fixes

* Fix memory leak on Linux when getting user's environment variables.
* Fix several issues with the auto-update process of the standalone installers.
* Fix segfault on closing with PyQt6.
* Fix errors when creating new remote connections if credentials are wrong.
* Finish fixing and improving docstrings for modules under `spyder.api`.
