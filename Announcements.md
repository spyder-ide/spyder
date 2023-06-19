# Minor release to list

**Subject**: [ANN] Spyder 5.4.3 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **5.4.3** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes ten weeks and six days after version 5.4.2 and it contains the
following new features and important fixes:

* Add support for QDarkstyle 3.1
* Add support for Jupyter-client 8
* Add mambaforge and miniforge when searching for conda environments
* Fix IPython Console completions, traceback handling and other issues to better support IPython 8.x
* Fix compatibility issues with PyZMQ 25.x
* Add warning message before loading .spydata files
* Fix web based widgets display by adding the `--no-sandbox` argument for `QtApplication`
* Fix copy and paste shortcuts for the Files and Projects explorer panes
* Fix Windows standalone installer restart mechanism
* Fix keyring backends for the Mac standalone installer
* Fix Editor issues related with handling LSP server failed starts
* Fix Editor issues related with restoring previous session and file changes outside Spyder
* Fix PYTHONPATH manager showing extra paths and other related errors
* Fix update available notification with pip based installations
* Fix some UX/UI issues for the find replace widget when the Editor has a small width
* Removal of Python 2 related code

In this release we fixed 29 issues and merged 47 pull requests that amount
to more than 173 commits. For a full list of fixes, please see our
[Changelog](https://github.com/spyder-ide/spyder/blob/5.x/CHANGELOG.md).

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development and computing environment. Join us to help
creating your favorite environment!

Enjoy!

Daniel


----


# Major release to list

**Subject**: [ANN] Spyder 5.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **5.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release represents more than one year of development since version 4.0 was
released, and it introduces major enhancements and new features. The most important ones
are:

* Improved dark theme based on QDarkstyle 3.0.
* New light theme based on QDarkstyle 3.0.
* New look and feel for toolbars.
* New icon set based on Material Design.
* New API to extend core plugins, with the exception of the Editor, IPython
  console and Projects.
* New plugins to manage menus, toolbars, layouts, shortcuts, preferences and
  status bar.
* New architecture to access and write configuration options.
* New API to declare code completion providers.
* New registries to access actions, tool buttons, toolbars and menus by their
  identifiers.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/5.x/CHANGELOG.md)

Spyder 4.0 has been a huge success and we hope 5.0 will be as successful. For that we
fixed 54 bugs, merged 142 pull requests from about 16 authors and added more than
830 commits between these two releases.

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development/computing environment. Join us to help creating
your favorite environment!

Enjoy!
-Carlos


----


# Major release to others

**Note**: Leave this free of Markdown because it could go to mailing lists that
don't support html.

**Subject**: [ANN] Spyder 4.0 is released!


Hi all,

On the behalf of the Spyder Project Contributors (https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder 3.0 has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

Spyder is a free, open-source (MIT license) interactive development environment
for the Python language with advanced editing, interactive testing, debugging
and introspection features. It was designed to provide MATLAB-like features
(integrated help, interactive console, variable explorer with GUI-based editors
for NumPy arrays and Pandas dataframes), it is strongly oriented towards
scientific computing and software development.

<The rest is the same as for the list>


----


# Beta release

**Subject**: [ANN] Spyder 4.0 third release candidate


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the third release candidate of our next major version: Spyder **4.0**.

We've been working on this version for more than three years now and as far as we know
it's working very well. There are still several bugs to squash but we encourage all
people who like the bleeding edge to give it a try. This beta version is released
one week after Spyder 4.0 rc2 and it includes more than 130 commits.

Spyder 4.0 comes with several interesting and exciting new features. The most
important ones are:

- Main Window
    * Dark theme for the entire application.
    * A new Plots pane to browse all inline figures generated by the
      IPython console.
    * Rename the following panes:
        - `Static code analysis` to `Code Analysis`
        - `File explorer` to `Files`
        - `Find in files` to `Find`
        - `History log` to `History`
        - `Project explorer` to `Project`
    * Create a separate window when undocking all panes.
    * Show current conda environment (if any) in the status bar.

- Editor
    * Code folding.
    * Indentation guides.
    * A class/method/function lookup panel. This can be shown in the menu
      `Source > Show selector for classes and functions`.
    * Autosave functionality to recover unsaved files after a crash.
    * Optional integration with the [Kite](https://kite.com/) completion
      engine.
    * Code completion and linting are provided by the Python Language Server.

- IPython Console
    * Run files in an empty namespace.
    * Open dedicated consoles for Pylab, Sympy and Cython.
    * Run cells through a new function called `runcell`.
    * Run cells by name.

- Debugger
    * Code completion.
    * Execute multi-line statements.
    * Syntax highlighting.
    * Permanent history.
    * `runfile` and `runcell` can be called when the debugger is active.
    * Debug cells with `Alt+Shift+Return`.

- Variable Explorer
    * New viewer to inspect any Python object in a tree-like representation.
    * Filter variables by name or type.
    * MultiIndex support in the Dataframe viewer.
    * Support for all Pandas indexes.
    * Support for sets.
    * Support for Numpy object arrays.
    * Restore the ability to refresh it while code is being executed.

- Files
    * Associate external applications to open specific file extensions.
    * Context menu action to open files externally.
    * Multi-select functionality with `Ctrl/Shift + mouse click`.
    * Copy/paste files and their absolute or relative paths.
    * Use special icons for different file types.

- Outline
    * Show cells grouped in sections.
    * Add default name to all cells.


For a more complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/wiki/Beta-version-changelog)

You can easily install this beta if you use Anaconda by running:

    conda update qt pyqt
    conda install -c spyder-ide spyder=4.0.0rc3

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Carlos
