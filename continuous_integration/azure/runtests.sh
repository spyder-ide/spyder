#!/bin/bash -ex

# Azure doesn't define CI
export CI=True

# Run tests
python bootstrap.py -- --reset
python runtests.py
