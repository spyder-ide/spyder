# Contributing to Spyder-IDE

:+1::tada: First off, thanks for taking the time to contribute to Spyder! :tada::+1:

## General Guidelines

This page documents at a very high level how to contribute to Spyder.
Please Check the
[Spyder IDE Contributor Documentation](https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder)
for a more detailed guide on how to contribute to the Spyder.


## Setting Up a Development Environment


### Cloning the repo

```bash
  $ git clone https://github.com/spyder-ide/spyder.git
```

### Creating a conda environment or virtualenv

If you use Anaconda you can create a conda environment with
these instructions

```bash
  $ conda create -n spyder-dev python=3
  $ source activate spyder-dev
```

You can also use `virtualenv` on Linux, but `conda` is preferred:

```bash
  $ mkvirtualenv spyder-dev
  $ workon spyder-dev
```

### Installing dependencies

After you have created your development environment, you need to install
Spyder necessary dependencies. For that you need to go to the directory
where your git clone is placed and run:

```bash
  $ conda install --file requirements/requirements.txt
```

or using pip and virtualenv:

```bash
  $ pip install -r requirements/requirements.txt
```

*Note*: If you are using pip, you also need to install a Qt binding
package. This can be achieved by running

```bash
  $ pip install pyqt5
```

### Running Spyder

To start Spyder directly from your clone, i.e. without installing it to your
environment, you need to run

```bash
  $ python bootstrap.py
```

**Important Note**: You need to restart Spyder after any change you do to its
source code. This is the only way to test your new code.

## Spyder Branches

When you start to work on a new pull request (PR), you need to be sure that your
feature branch is a child of the right Spyder branch, and also that you make
your PR on Github against it.

Besides, issues are marked with a milestone that indicates the correct branch
to use, like this:

* Use the `3.1.x` branch for bugfixes only (milestones `v3.1.1`, `v3.1.2`, `v3.1.3`,
  etc)

* Use the `3.x` branch to introduce new features that don't require major internal
  changes (milestones `v3.1`, `v3.2`, `v3.3`, etc).

* Use `master` to introduce new features that break compatibility with previous
  Spyder versions (Milestone `v4.0beta1`, `v4.0beta2`, etc).


You can also submit bugfixes to `3.x` or `master` for errors that are only present in
those branches.

So to start working on a new PR, you need to follow these commands:

```bash
  $ git checkout <branch>
  $ git pull upstream <branch>
  $ git checkout -b name-new-branch
```

##  Running Tests

Install our test dependencies:

```bash
  $ conda install --file requirements/test_requirements.txt -c spyder-ide
```

or using pip
```bash
  $ pip install -r requirements/test_requirements.txt
```

To run Spyder test suite, please use:
```bash
  $ python runtests.py
```
