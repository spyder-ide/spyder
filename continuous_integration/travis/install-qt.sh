#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

if [ "$USE_CONDA" = "no" ]; then
    pip uninstall -q -y pytest-xvfb
    # 5.10 is giving segfaults while collecting tests
    pip install -q pyqt5==5.9.2

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git
    pip install -q git+https://github.com/spyder-ide/spyder-kernels
elif [ "$USE_PYQT" = "pyqt5" ]; then
    conda install -q qt=5.* pyqt=5.* qtconsole matplotlib
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
else
    conda install -q qt=4.* pyqt=4.* qtconsole matplotlib
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
fi
