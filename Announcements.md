# Minor release to list

**Subject**: [ANN] Spyder 3.3.1 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **3.3.1** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes one month after version 3.3.0 and it adds the following new
features:

- Preferences
    * Save the list of custom interpreters introduced in
      `Preferences > Python interpreter`.

- IPython console
    * Do not save pdb commands in debugging history.

In this release we fixed 19 issues and merged 31 pull requests that amount
to more than 120 commits. For a full list of fixes, please see our
[Changelog](https://github.com/spyder-ide/spyder/blob/3.x/CHANGELOG.md).

Don't forget to follow Spyder updates/news on the project
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

**Subject**: [ANN] Spyder 4.0 first public beta release


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the first beta of our next major version: Spyder **4.0**.

We've been working on this version for almost two years now and as far as we know
it's working very well. There are still several bugs to squash but we encourage all
people who like the bleeding edge to give it a try. This beta version is released
23 months after Spyder 3.0 and it includes more than 680 commits.

Spyder 4.0 comes with several interesting and exciting new features. The most
important ones are:

- Main Window
    * Create a separate window when undocking all panes.
    * Add translations for Simplified Chinese and German.

- Editor
    * Code folding.
    * Indentation guides.
    * A class/method/function lookup “context panel”.

- IPython Console
    * Add menu options to start consoles in Pylab, Sympy and Cython modes.

- Variable Explorer
    * Add MultiIndex display support to the Dataframe viewer.
    * Add support for all Pandas indexes.
    * Add support for sets.

- Outline Explorer
    * Show cells grouped in sections.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/wiki/Beta-version-changelog)

You can easily install this beta if you use Anaconda by running:

    conda update qt pyqt
    conda install -c spyder-ide spyder=4.0.0b1

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Carlos
