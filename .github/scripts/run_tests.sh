#!/bin/bash -ex

# Adjust PATH in macOS
if [ "$OS" = "macos" ]; then
    PATH=/Users/runner/miniconda3/envs/test/bin:/Users/runner/miniconda3/condabin:$PATH
fi

# Rename log file before running the test suite. Its contents will be read
# before the next run (see conftest.py in the root of the repo).
mv log.txt pytest_log.txt

# Run tests
if [ "$OS" = "linux" ]; then
    xvfb-run --auto-servernum python runtests.py --color=yes | tee log.txt
else
    python runtests.py --color=yes | tee log.txt
fi
