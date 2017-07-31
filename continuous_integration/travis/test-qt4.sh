#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

pip uninstall -q -y pytest-xvfb
conda install -q qt=4.* pyqt=4.* qtconsole matplotlib

# Install qtconsole from Github
conda remove -q -y qtconsole
pip install git+https://github.com/jupyter/qtconsole.git

python runtests.py
