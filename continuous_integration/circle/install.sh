#!/bin/bash

export CONDA_DEPENDENCIES_FLAGS="--quiet"
export CONDA_DEPENDENCIES="rope pyflakes sphinx pygments pylint psutil nbconvert \
                           qtawesome pickleshare qtpy pyzmq chardet mock nomkl pandas \
                           pytest pytest-cov numpydoc scipy cython pillow cloudpickle"
export PIP_DEPENDENCIES="coveralls pytest-qt pytest-mock pytest-xvfb flaky jedi pycodestyle \
                         coloredlogs python-language-server[all] pydocstyle pexpect"

# Download and install miniconda and conda/pip dependencies
# with astropy helpers
export PY_VERSIONS=($PY_VERSIONS)
export TRAVIS_PYTHON_VERSION=${PY_VERSIONS[$CIRCLE_NODE_INDEX]}

echo -e "PYTHON = $TRAVIS_PYTHON_VERSION \n============"
git clone git://github.com/astropy/ci-helpers.git > /dev/null
source ci-helpers/travis/setup_conda_$TRAVIS_OS_NAME.sh
export PATH="$HOME/miniconda/bin:$PATH"
source activate test

# Install spyder-kernels
pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
