#!/bin/bash -ex

python bootstrap.py -- --reset
python runtests.py
