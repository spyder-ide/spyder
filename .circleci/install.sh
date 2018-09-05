#!/bin/bash

export TRAVIS_OS_NAME="linux"
export CONDA_DEPENDENCIES_FLAGS="--quiet"
export CONDA_DEPENDENCIES="rope pyflakes sphinx pygments pylint psutil nbconvert \
                           qtawesome pickleshare qtpy pyzmq chardet mock nomkl pandas \
                           pytest pytest-cov numpydoc scipy cython pillow cloudpickle \
                           keyring qtconsole matplotlib"
export PIP_DEPENDENCIES="coveralls pytest-qt pytest-mock pytest-xvfb flaky jedi pycodestyle"

# Download and install miniconda and conda/pip dependencies
# with astropy helpers

echo -e "PYTHON = $PYTHON_VERSION \n============"
git clone git://github.com/astropy/ci-helpers.git > /dev/null
source ci-helpers/travis/setup_conda_$TRAVIS_OS_NAME.sh
source $HOME/miniconda/etc/profile.d/conda.sh
conda activate test

# Install spyder-kernels
pip install --no-deps git+https://github.com/spyder-ide/spyder-kernels@0.x
