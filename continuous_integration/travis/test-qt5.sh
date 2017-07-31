#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

pip uninstall -q -y pytest-xvfb

# We test with pip packages in Python 3.5 and PyQt5
if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ] && [ "$USE_PYQT" = "pyqt5" ]; then
    pip install -q pyqt5
else
    conda install -q qt=5.* pyqt=5.* qtconsole matplotlib

    # Install qtconsole from Github
    conda remove -q -y qtconsole
    pip install git+https://github.com/jupyter/qtconsole.git
fi

python runtests.py
