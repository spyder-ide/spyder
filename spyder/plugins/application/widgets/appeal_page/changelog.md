# History of changes

## Version 6.1.4 (2026-04-06)

### New features

* Add option to disable `Enter` for accepting code completions in the Editor.
  The option is available in `Preferences > Completion and linting > General`.
* Support SSH config files to create connections in
  `Tools > Manage remote connections`.
* Add support to delete, upload and download multiple files when working with
  remote filesystems in Files.
* Add button to Files to go to the directory of the current file in the Editor.

### Important fixes

* Docstring generation has been massively overhauled to:
    * Parse and incorporate the sections of the function's existing docstring.
    * Support generating return types from the function body for Sphinxdoc.
    * Fix dozens of bugs and limitations with the existing docstring generation.
    * Resolve numerous formatting issues and follow the relevant specifications.
* Default shortcut for docstring generation was changed to `Ctrl/Cmd+Alt+Shift+D`
  to avoid a conflict on macOS.
* Allow macOS standalone app to access the microphone and camera.
* Include `pyarrow` in the standalone installers to allow viewing dataframes
  created with Pandas 3.0+.
* Remove the deprecated `atomicwrites` package as a dependency.
* Constraint `chardet` version for licensing reasons in the standalone installers
  and fix compatibility with its latest versions.
* Several fixes for remote connections:
    * Fix errors when stopping SSH connections.
    * Fix some misspelling in error messages.
    * Handle keyring backend load failures on Linux.
    * Fix connections to JupyterHub servers.
