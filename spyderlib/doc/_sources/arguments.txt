Command line options
====================

Spyder's command line options are the following:
(type 'python spyder.py --help' to show the text below)

Options:
  -h, --help            show this help message and exit
  -l, --light           Light version (all add-ons are disabled)
  -w WORKING_DIRECTORY, --workdir=WORKING_DIRECTORY
                        Default working directory
  -s STARTUP, --startup=STARTUP
                        Startup script (overrides PYTHONSTARTUP)
  -m MODULE_LIST, --modules=MODULE_LIST
                        Modules to import (comma separated)
  -a, --all             Import all optional modules (options below)
  -p, --pylab           Import pylab in interactive mode and add option
                        --numpy
  --mlab                Import mlab as M (MayaVi's interactive 3D-plotting
                        interface)
  -o, --os              Import os and os.path as osp
  --numpy               Import numpy as N
  --scipy               Import numpy as N, scipy as S
  -d, --debug           Debug mode (stds are not redirected)
  --profile             Profile mode (internal test, not related with Python
                        profiling)
