# Minor release to list

**Subject**: [ANN] Spyder 3.3.4 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **3.3.4** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes seven weeks after version 3.3.2 and it adds the
following new features:

* Fix several incompatibilities with PyQt5 5.12.
* Avoid errors when running `turtle` programs in the IPython console
  multiple times.
* Avoid the UMR to reload modules installed in the user site-packages
  directory.

In this release we fixed 13 issues and merged 23 pull requests that amount
to 57 commits. For a full list of fixes, please see our
[Changelog](https://github.com/spyder-ide/spyder/blob/3.x/CHANGELOG.md).

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development and computing environment. Join us to help
creating your favorite environment!

Enjoy!
Carlos


----


# Major release to list

**Subject**: [ANN] Spyder 3.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **3.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release represents more than two years of development since version 2.3.0 was
released, and it introduces major enhancements and new features. The most important ones
are:

* Third-party plugins: External developers can now create plugins that extend Spyder in
  novel and interesting ways. For example, we already have plugins for the line-profiler
  and memory-profiler projects, and also a graphical frontend for the conda package
  manager. These plugins can be distributed as pip and/or conda packages for authors
  convenience.
* Improved projects support: Projects have been revamped and improved significantly in
  Spyder 3.0. With our new projects support, people will have the possibility of easily
  working on different coding efforts at the same time. That's because projects save the
  state of open files in the Editor and allow Python packages created as part of the
  project to be imported in our consoles.
* Support for much more programming languages: Spyder relies now on the excellent Pygments
  library to provide syntax highlight and suggest code completions in the Editor, for all
  programming languages supported by it.
* A new file switcher: Spyder 3.0 comes with a fancy file switcher, very similar in
  spirit to the one present in Sublime Text. This is a dialog to select among the open
  files in the Editor, by doing a fuzzy search through their names. It also lets users to
  view the list of classes, methods and functions defined in the current file, and select
  one of them. This dialog is activated with `Ctrl+P`.
* A Numpy array graphical builder: Users who need to create NumPy arrays in Spyder for
  matrices and vectors can do it now in a graphical way by pressing `Ctrl+M` in the Editor
  or the Consoles. This will open an empty 2D table widget to be filled with the data
  required by the user.
* A new icon theme based on FontAwesome.
* A new set of default pane layouts for those coming from Rstudio or Matlab (under
  `View > Window layouts`).
* A simpler and more intuitive way to introduce keyboard shortcuts.
* Support for PyQt5, which fixes problems in MacOS X and in high definition screens.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/3.x/CHANGELOG.md)

Spyder 2.3 has been a huge success (being downloaded almost 550,000 times!) and
we hope 3.0 will be as successful as it. For that we fixed 203 important bugs,
merged 218 pull requests from about 40 authors and added almost 2850 commits
between these two releases.

Don't forget to follow Spyder updates/news on the project Github website:
https://github.com/spyder-ide/spyder

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development/computing environment. Join us to help creating
your favorite environment!

Enjoy!
-Carlos


----


# Major release to others

**Note**: Leave this free of Markdown because it could go to mailing lists that
don't support hmtl.

**Subject**: [ANN] Spyder 3.0 is released!


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

**Subject**: [ANN] Spyder 4.0 second public beta release


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the second beta of our next major version: Spyder **4.0**.

We've been working on this version for almost three years now and as far as we know
it's working very well. There are still several bugs to squash but we encourage all
people who like the bleeding edge to give it a try. This beta version is released
10 months after Spyder 4.0 beta1 and it includes 2150 commits.

Spyder 4.0 comes with several interesting and exciting new features. The most
important ones are:

- Main Window
    * Dark theme for the entire application.
    * A new Plots pane to browse all inline figures generated by the
      IPython console.
    * Create a separate window when undocking all panes.
    * Add translations for Simplified Chinese and German.

- Editor
    * Code folding.
    * Indent guides.
    * A class/method/function lookup “context panel”.
    * Autosave functionality to recover unsaved files after a crash.
    * Code completion and linting are provided by the Language Server Protocol.

- IPython Console
    * Add menu options to start consoles in Pylab, Sympy and Cython modes.
    * Cells are run through a function called runcell.

- Variable Explorer
    * Add MultiIndex display support to the Dataframe viewer.
    * Add support for all Pandas indexes.
    * Add support for sets.

- File Explorer

    * Add `Open With OS` context menu action to all files, to open any file or
      directory externally.
    * Add multi-select functionality (Ctrl/Shift+click).
    * Add the ability to copy/paste files and their absolute or relative paths.
    * Use special icons for different file types.
    * Add an option to open files and directories with a single click.

- Outline Explorer
    * Show cells grouped in sections.


For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/wiki/Beta-version-changelog)

You can easily install this beta if you use Anaconda by running:

    conda update qt pyqt
    conda install -c spyder-ide spyder=4.0.0b2

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Carlos
