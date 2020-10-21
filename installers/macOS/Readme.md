
## How to build the Spyder MacOS X application

**Important note**: These instructions have only been tested on MacOS X 10.14 and above

To build the Spyder standalone Mac application you need:
* Python 3.x installed, *not* from Anaconda
* A local clone of the [spyder](https://github.com/spyder-ide/spyder) repository

Once you have the above requirements, you will create a virtual environment from which to build the application.

### Python 3.x installation

In principle, it doesn't matter where your Python installation comes from except that it cannot come from Anaconda.
I do not know exactly why an Anaconda installation does not work except that it has something to do with hardlinks.

I recommend using [Homebrew](http://brew.sh/) to install pyenv and pyenv-virtualenv (if you plan to use these for virtual environment management).
If you plan to use pyenv, you don't even need to install Python from Homebrew, since pyenv will install whatever python version you request.
If you don't plan to use pyenv, then you will need to install Python from Homebrew or elsewhere.

After installing Homebrew, run:

```
$ brew install pyenv, pyenv-virtualenv, xz
```

`xz` is a package that provides compression algorithms that Python should be built with to satisfy some packages, namely `pandas`.

The Python frameworks must be copied to the stand-alone application, so if you use pyenv you must enable frameworks in any Python installation that you plan to use to build the Spyder app.

```
$ PYTHON_CONFIGURE_OPTS=--enable-framework pyenv install <python version>
```

### Create Virtual Environment

If you currently have any conda environment(s) activated, then deactivate them completely, i.e. you should not be in any conda environment, not even base.

Create the virtual environment and populate it with the necessary package requirements.
If you are using pyenv with pyenv-virtualenv, it will look like this:

```
$ pyenv virtualenv <python version> spy-build
$ pyenv activate spy-build
```

If you are using venv, creating the environment will look like this:

```
$ python -m venv --clear --copies spy-build
$ source spy-build/bin/activate
```

Now change your working directory to `installers/macOS` directory of your local Spyder repo and install the necessary packages.

```
(spy-build) $ cd <path>/<to>/spyder/installers/macOS
(spy-build) $ pip install -r req-build.txt -r req-extras.txt -c req-const.txt -e ../../
(spy-build) $ pip uninstall -q -y spyder
```

This will install the packages required for building Spyder and extra packages like matplotlib.
Spyder is installed from this repository for the sole purpose of getting all of its dependencies.
It must be uninstalled since py2app will use the repository when creating the application bundle.

`req-build.txt` contains only those packages required to build the stand-alone application.
`req-extras.txt` contains optional packages to include, if desired, for use in IPython consoles launched from the "Same as Spyder" environment.
If you use external environments, such as conda, for your IPython consoles, you don't need `req-extras.txt`.
The build command also provides an option to exclude these packages, so you may install them and still build the application without them.
`req-const.txt` contains package constraints that are known to cause problems with the build process if not satisfied.

### Create the Standalone Application

To create the standalone application and package it in a dmg disk image run:

```
(spy-build) $ python setup.py --dmg
```

Further usage documentation can be accessed via

```
(spy-build) $ python setup.py -h
```

After a whole lot of screen dump, and if everything went well, you should now have two files in the `installers/macOS/dist` directory of your local Spyder repository:
* Spyder.app
* Spyder.dmg
