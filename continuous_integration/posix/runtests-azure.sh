#!/bin/bash

# We have two kinds of tests:
#
# 1. The new ones, based on pytest
# 2. The old ones, present in the main section
#    at the end of several files.
#
# Notes:
# - We always run our new tests in Travis.
# - Circle runs a mix of both for old Python versions or
#   things we can test in macOS.
if [ "$CI_PYTEST" = "true" ]; then
    python bootstrap.py -- --reset
    python runtests.py
else
    ./continuous_integration/posix/modules_test.sh
fi
