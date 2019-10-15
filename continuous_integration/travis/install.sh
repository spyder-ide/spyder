#!/bin/bash -ex

# -- Install Miniconda
MINICONDA=Miniconda3-latest-Linux-x86_64.sh
wget https://repo.continuum.io/miniconda/$MINICONDA -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
source $HOME/miniconda/etc/profile.d/conda.sh


# -- Make new conda environment with required Python version
conda create -y -c conda-forge -n test python=$PYTHON_VERSION
conda activate test


# -- Installl dependencies
if [ "$USE_CONDA" = "yes" ]; then
    # Install main dependencies
    conda install -q -y -c conda-forge/label/beta -c conda-forge --file requirements/conda.txt

    # Install test dependencies
    conda install -q -y -c conda-forge -c spyder-ide --file requirements/tests.txt

    # Install coveralls
    pip install -q coveralls

    # Install spyder-kernels from Github with no deps
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
else
    # Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    # Downgrade PyQt5 to 5.11 in Circle.
    # Else our tests give segfaults
    if [ "$CIRCLECI" = "true" ]; then
        pip install pyqt5==5.11.*
    fi

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
