#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"

source activate test

conda install -q qt=4.* pyqt=4.*

python runtests.py
