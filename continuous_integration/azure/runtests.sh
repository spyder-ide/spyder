#!/bin/bash -ex

# Run tests
python bootstrap.py -- --reset
python runtests.py
