#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

if [ "$USE_CONDA" = "no" ]; then
    # Remove pytest-xvfb because it causes hangs
    pip uninstall -q -y pytest-xvfb

    # 5.10 is giving segfaults while collecting tests
    pip install -q pyqt5==5.9.2

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    # Install spyder-kernels from Github
    pip install -q git+https://github.com/spyder-ide/spyder-kernels
else
    conda install -q qt=5* pyqt=5.* sip=4.19.8 qtconsole matplotlib

    # Install spyder-kernels from Github
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
fi
