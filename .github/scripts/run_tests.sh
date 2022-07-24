#!/bin/bash -ex

# Adjust PATH in macOS
if [ "$OS" = "macos" ]; then
    PATH=/Users/runner/miniconda3/envs/test/bin:/Users/runner/miniconda3/condabin:$PATH
fi

# Run tests
if [ "$OS" = "linux" ]; then
    xvfb-run --auto-servernum python runtests.py --color=yes | tee log.txt
else
    python runtests.py --color=yes | tee -a pytest_log.txt
fi
