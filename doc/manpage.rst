:orphan:

spyder manual
=============


Synopsis
--------

**spyder** [*options*] [*filenames*]


Description
-----------

Spyder provides:

* a powerful interactive development environment for the Python language with
  advanced editing, interactive testing, debugging and introspection features,

* and a numerical computing environment thanks to the support of `IPython`
  (enhanced interactive Python interpreter) and popular Python libraries such
  as `NumPy` (linear algebra), `SciPy` (signal and image processing) or
  `matplotlib` (interactive 2D/3D plotting).


Options
-------

-h, --help              show this help message and exit

--new-instance          run a new instance of Spyder, even if the single
                        instance mode has been turned on (default)

--defaults              reset configuration settings to defaults

--reset                 remove all configuration files

--optimize              optimize the Spyder bytecode (may require
                        administrative privileges)

-w WORKING_DIRECTORY, --workdir=WORKING_DIRECTORY
                        set the default working directory

--show-console          do not hide parent console window (Windows)

--multithread           execute the internal console in a separate thread
                        (from the main application thread)

--profile               run spyder in profile mode (for internal testing, not
                        related with Python profiling)

--window-title=WINDOW_TITLE
                        show this string in the main window title

-p OPEN_PROJECT, --project=OPEN_PROJECT
                        open a Spyder project (directory with a .spyproject
                        folder)

Bugs
----

If you find a bug, please consider reporting it to the Spyder issue tracker at
<https://github.com/spyder-ide/spyder/issues>.
