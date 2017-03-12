#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

# We use container 3 to test with pip
if [ "$CIRCLE_NODE_INDEX" != "3" ]; then
    conda install -q qt=5.* pyqt=5.* qtconsole matplotlib
fi

python runtests.py

# Run coveralls also here because there are errors if run
# as an independent command
coveralls
