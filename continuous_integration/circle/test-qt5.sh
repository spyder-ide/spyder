#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

conda install -q qt=5.* pyqt=5.* qtconsole matplotlib

python runtests.py
