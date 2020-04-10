#!/bin/bash -ex

source activate tests

# Run tests
python bootstrap.py -- --reset
python runtests.py
