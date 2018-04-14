# Contributing to Spyder

:+1::tada: First off, thanks for taking the time to contribute to Spyder! :tada::+1:


## General Guidelines

This page documents at a very high level how to contribute to Spyder.
Please check the
[Spyder IDE Contributor Documentation](
https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder)
for a more detailed guide on how to do so.


## Troubleshooting

Before posting a report, *please* carefully read our
**[Troubleshooting Guide](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)**
and search the [issue tracker](https://github.com/spyder-ide/spyder/issues)
for your error message and problem description, as the great majority of bugs
are either duplicates, or can be fixed on the user side with a few easy steps.
Thanks!


## Submitting a Helpful Issue

Submitting useful, effective and to-the-point issue reports can go a long
way toward improving Spyder for everyone. Accordingly, please read the
[relevant section](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ#calling-for-help-still-have-a-problem)
of the Spyder Troubleshooting Guide, which describes in detail how to do
just that.

Most importantly, aside from the error message/traceback and the requested
environment/dependency information, *please* be sure you include a detailed,
step by step description of exactly what triggered the problem. Otherwise,
we likely won't be able to find and fix it, and your issue will have to be
closed after a week (7 days). Thanks!


## Setting Up a Development Environment


### Cloning the repo

```bash
  $ git clone https://github.com/spyder-ide/spyder.git
```

### Creating a conda environment or virtualenv

If you use Anaconda you can create a conda environment with
the following commands:

```bash
  $ conda create -n spyder-dev python=3
  $ source activate spyder-dev
```

On Windows, you'll want to run the commands with the Anaconda Prompt,
and use just ```activate spyder-dev``` for the second command.

You can also use `virtualenv` on Linux, but `conda` is strongly
recommended:

```bash
  $ mkvirtualenv spyder-dev
  $ workon spyder-dev
```

### Installing dependencies

After you have created your development environment, you need to install
Spyder's necessary dependencies. The easiest way to do so (with Anaconda) is

```bash
  $ conda install spyder
  $ conda remove spyder
```

This installs all of Spyder's dependencies into the environment along with
the stable/packaged version of Spyder itself, and then removes the latter.

If using `pip` and `virtualenv` (not recommended), you need to `cd` to
the directory where your git clone is stored and run:

```bash
  $ pip install -r requirements/requirements.txt
```

If you are using `pip` and Python 3, you also need to install a Qt binding
package (PyQt5). This can be achieved by running:

```bash
  $ pip install pyqt5
```

### Running Spyder

To start Spyder directly from your clone, i.e. without installing it into
your environment, you need to run
(from the directory you cloned it to e.g. `spyder`):

```bash
  $ python bootstrap.py
```

To start Spyder in debug mode, useful for tracking down an issue, you can run:

```bash
  $ python bootstrap.py --debug
```

**Important Note**: To test any changes you've made to the Spyder source code,
you need to restart Spyder or start a fresh instance (you can run multiple
copies simultaneously by unchecking the Preferences option
<kbd>Use a single instance</kbd> under
<kbd>General</kbd> > <kbd>Advanced Settings</kbd> .


## Spyder Branches

When you start to work on a new pull request (PR), you need to be sure that your
work is done on top of the correct Spyder branch, and that you base your
PR on Github against it.

To guide you, issues on Github are marked with a milestone that indicates
the correct branch to use. If not, follow these guidelines:

* Use the `3.x` branch for bugfixes only (*e.g.* milestones `v3.2.1`, `v3.2.2`,
  or `v3.2.3`)
* Use `master` to introduce new features or break compatibility with previous
  Spyder versions (*e.g.* milestones `v4.0beta1` or `v4.0beta2`).

You should also submit bugfixes to `3.x` or `master` for errors that are
only present in those respective branches.

To start working on a new PR, you need to execute these commands, filling in
the branch names where appropriate:

```bash
  $ git checkout <SPYDER-BASE-BRANCH>
  $ git pull upstream <SPYDER-BASE-BRANC>
  $ git checkout -b NAME-NEW-BRANCH
```

### Changing the base branch

If you started your work in the wrong base branch, or want to backport it,
you can change the base branch using `git rebase --onto`, like this:

```bash
  $ git rebase --onto <NEW-BASE-BRANCH> <OLD-BASE-BRANCH> <YOUR-BRANCH>
```

For example, backporting `my_branch` from `master` to `3.x`:

```bash
  $ git rebase --onto 3.x master my_branch
```


##  Running Tests

To install our test dependencies under Anaconda:

```bash
  $ conda install --file requirements/test_requirements.txt -c spyder-ide
```

If using `pip` (for experts only), run the following from the directory
where your git clone is stored:
```bash
  $ pip install -r requirements/test_requirements.txt
```

To run the Spyder test suite, please use (from the `spyder` root directory):
```bash
  $ python runtests.py
```


## More information

[Download Spyder (with Anaconda)](https://www.anaconda.com/download/)

[Spyder Github](https://github.com/spyder-ide/spyder)

[Troubleshooting Guide and FAQ](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ')

[Development Wiki](https://github.com/spyder-ide/spyder/wiki/Dev:-Index)

[Gitter Chatroom](https://gitter.im/spyder-ide/public)

[Google Group](http://groups.google.com/group/spyderlib)

[Support Spyder on OpenCollective](https://opencollective.com/spyder/)
