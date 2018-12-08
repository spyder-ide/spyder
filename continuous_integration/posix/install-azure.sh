#!/bin/bash

# -- Installl dependencies
if [ "$USE_CONDA" = "yes" ]; then
    # Activate env
    conda activate test

    # Install main dependencies
    conda install -q -y -c spyder-ide --file requirements/conda.txt

    # Install test ones
    conda install -q -y -c spyder-ide --file requirements/tests.txt

    # Install coveralls
    pip install -q coveralls

    # Install spyder-kernels from Github with no deps
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
else
    # Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    # Remove pytest-xvfb because it causes hangs
    pip uninstall -q -y pytest-xvfb

    # Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    # Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git

    # Install spyder-kernels from Github
    pip install -q git+https://github.com/spyder-ide/spyder-kernels

    # Install coveralls
    pip install -q coveralls
fi
