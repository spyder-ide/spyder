Command line options
====================

Spyder's command line options are the following:
(type 'python spyder.py --help' to show the text below)

Options:
  -h, --help            show this help message and exit
  -l, --light           Light version (all add-ons are disabled)
  --session=STARTUP_SESSION
                        Startup session
  --reset               Reset to default session
  -w WORKING_DIRECTORY, --workdir=WORKING_DIRECTORY
                        Default working directory
  -s STARTUP, --startup=STARTUP
                        Startup script (overrides PYTHONSTARTUP)
  -m MODULE_LIST, --modules=MODULE_LIST
                        Modules to import (comma separated)
  -b, --basics          Import numpy, scipy and matplotlib following official
                        coding guidelines
  -a, --all             Option 'basics', 'pylab' and import os, sys, re, time,
                        os.path as osp
  -p, --pylab           Import pylab in interactive mode and add option
                        --numpy
  --mlab                Import mlab (MayaVi's interactive 3D-plotting
                        interface)
  -d, --debug           Debug mode (stds are not redirected)
  --profile             Profile mode (internal test, not related with Python
                        profiling)