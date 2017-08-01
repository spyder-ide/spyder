#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

# We test with pip packages in Python 3.5 and PyQt5
if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ] && [ "$USE_PYQT" = "pyqt5" ]; then
    pip uninstall -q -y pytest-xvfb
    pip install -q pyqt5

    # Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git
else
    conda install -q qt=5.* pyqt=5.* qtconsole matplotlib
fi

python runtests.py
