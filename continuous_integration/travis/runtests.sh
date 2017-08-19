#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

python bootstrap.py -- --reset

python runtests.py
