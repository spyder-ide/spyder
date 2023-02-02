
## How to build the Spyder MacOS X application

**Important note**: These instructions have only been tested on MacOS X 10.14 and above

To build the Spyder standalone Mac application you need:
* Python 3.x installed, *not* from Anaconda
* A local clone of the [spyder](https://github.com/spyder-ide/spyder) repository

Once you have the above requirements, you will create a virtual environment from which to build the application.

### Python 3.x installation

In principle, it doesn't matter where your Python installation comes from except that it cannot come from Anaconda.
I do not know exactly why an Anaconda installation does not work except that it has something to do with hardlinks.

I recommend using [Homebrew](http://brew.sh/) to install `pyenv` and `pyenv-virtualenv` (if you plan to use these for virtual environment management).
If you plan to use `pyenv`, you don't even need to install Python from Homebrew, since `pyenv` will install whatever python version you request.
If you don't plan to use `pyenv`, then you will need to install Python from Homebrew or elsewhere.

After installing Homebrew, run:

```
$ brew install pyenv, pyenv-virtualenv, xz, tcl-tk
```

`xz` is a package that provides compression algorithms that Python should be built with to satisfy some packages, namely `pandas`.

The Python frameworks must be copied to the stand-alone application, so if you use `pyenv` you must enable frameworks in any Python installation that you plan to use to build the Spyder app.
Additionally, the `tcl-tk` libraries must be referenced.
The following commands install Python with these considerations.

```
$ TKPREFIX=$(brew --prefix tcl-tk)
$ export PYTHON_CONFIGURE_OPTS="--enable-framework --with-tcltk-includes=-I${TKPREFIX}/include --with-tcltk-libs='-L${TKPREFIX}/lib -ltcl8.6 -ltk8.6'"
$ pyenv install <python version>
```

### Create Virtual Environment

Create the virtual environment and populate it with the necessary package requirements.
If you are using `pyenv` with `pyenv-virtualenv`, it will look like this:

```
$ pyenv virtualenv <python version> spy-build
$ pyenv activate spy-build
```

If you are using `venv`, creating the environment will look like this:

```
$ python -m venv --clear --copies spy-build
$ source spy-build/bin/activate
```

It's also a good idea to update `pip` and `setuptools`

```
$ (spy-build) $ python -m pip install -U pip setuptools wheel
```

Now change your working directory to the `installers/macOS` directory of your local Spyder repo and install the necessary packages.

```
(spy-build) $ cd <path>/<to>/spyder/installers/macOS
(spy-build) $ python -m pip install -r req-build.txt -r req-extras.txt -r req-plugins.txt -r req-scientific.txt -e ../../
```

This will install Spyder, the packages required for building Spyder, and extra packages like matplotlib.
`req-build.txt` contains only those packages required to build the stand-alone application.
`req-extras.txt` contains optional packages that can be used by the Python language server.
`req-plugins.txt` contains optional third party plugins.
`req-scientific.txt` contains optional packages to include for use in IPython consoles launched from the "Same as Spyder" environment.
If you use external environments, such as conda, for your IPython consoles, you don't need `req-scientific.txt`.
The build command also provides an option to exclude these packages, so you may install them and still build the application without them.

If your Spyder repo is checked out at a release commit or a commit that does not require synchronized commits for `python-lsp-server`, `qtconsole`, or `spyder-kernels`, then you should be able to proceed to building the application in the next section.
However, if you need to synchronize the commits of these packages, then you must install them from Spyder's `external-deps` subrepo directory.

```
(spy-build) $ python -m pip install --no-deps -e ../../external-deps/qtconsole
(spy-build) $ python -m pip install --no-deps -e ../../external-deps/spyder-kernels
(spy-build) $ export SETUPTOOLS_SCM_PRETEND_VERSION=`../../python pylsp_utils.py`
(spy-build) $ python -m pip install --no-deps -e ../../external-deps/python-lsp-server
```

### Create the Standalone Application

To create the standalone application and package it in a dmg disk image run:

```
(spy-build) $ python setup.py --dmg
```

Documentation on the various build options can be accessed via

```
(spy-build) $ python setup.py -h
```

After a whole lot of screen dump, and if everything went well, you should now have two files in the `installers/macOS/dist` directory of your local Spyder repository:
* Spyder.app
* Spyder.dmg
