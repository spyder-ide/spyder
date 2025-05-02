#!/bin/bash -ex

# *** DON'T remove this line! ***
# It's necessary to make this script error out in case the pipes below fail.
set -o pipefail

# Add CONDA_EXE to the environment for our conda tests
if [ "$OS" = "win" ]; then
    export CONDA_EXE=$CONDA\\Scripts\\conda
else
    export CONDA_EXE=$CONDA/bin/conda
fi

# To know what's the current run (some tests don't pass on the first one)
while getopts "n:" option; do
    case "$option" in
        (n) export CI_RUN_NUMBER=$OPTARG ;;
    esac
done

# Run tests
if [ "$SPYDER_TEST_REMOTE_CLIENT" = "true" ]; then
    xvfb-run --auto-servernum python runtests.py --color=yes --remote-client | tee -a pytest_log.txt
else
    if [ "$OS" = "linux" ]; then
        xvfb-run --auto-servernum python runtests.py --color=yes | tee -a pytest_log.txt
    else
        python runtests.py --color=yes | tee -a pytest_log.txt
    fi
fi
