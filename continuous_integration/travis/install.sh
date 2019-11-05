#!/bin/bash -ex

# -- Install Miniconda
MINICONDA=Miniconda3-latest-Linux-x86_64.sh
wget https://repo.continuum.io/miniconda/$MINICONDA -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
source $HOME/miniconda/etc/profile.d/conda.sh


# -- Make new conda environment with required Python version
conda create -y -n test python=$PYTHON_VERSION
conda activate test


# -- Installl dependencies
if [ "$USE_CONDA" = "yes" ]; then
    # Avoid problems with invalid SSL certificates
    if [ "$PYTHON_VERSION" = "2.7" ]; then
        conda install -q -y python=2.7.16=h9bab390_0
    fi

    # Install nomkl to avoid installing Intel MKL libraries
    conda install -q -y nomkl

    # Install main dependencies
    conda install -q -y -c spyder-ide --file requirements/conda.txt

    # Install test ones
    conda install -q -y -c spyder-ide --file requirements/tests.txt

    # Github backend tests are failing with 1.1.1d
    conda install -q -y openssl=1.1.1c

    # Install coveralls
    pip install -q coveralls

    # Install spyder-kernels from Github with no deps
    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels

    # Install python-language-server from Github with no deps
    pip install -q --no-deps git+https://github.com/palantir/python-language-server
else
    # Downgrade to Python 3.7.3 because 3.7.4 is not pulling
    # wheels for all packages
    if [ "$PYTHON_VERSION" = "3.7" ]; then
        conda install -q -y python=3.7.3
    fi

    # Github backend tests are failing with 1.1.1d
    conda install -q -y openssl=1.1.1c

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

    # Install python-language-server from Github
    pip install -q git+https://github.com/palantir/python-language-server

    # Install coveralls
    pip install -q coveralls
fi
