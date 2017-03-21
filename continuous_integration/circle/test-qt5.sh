#!/bin/bash

export PATH="$HOME/miniconda/bin:$PATH"
source activate test

# We use container 3 to test with pip
if [ "$CIRCLE_NODE_INDEX" != "3" ]; then
    conda install -q qt=5.* pyqt=5.* qtconsole matplotlib
else
    pip install -q pyqt5
fi

python runtests.py

# Force quitting if exit status of runtests.py was not 0
if [ $? -ne 0 ]; then
    exit 1
fi

# Run coveralls also here because there are errors if run
# as an independent command
coveralls

# Don't stop if coveralls fails for whatever reason
if [ $? -ne 0 ]; then
    exit 0
fi
