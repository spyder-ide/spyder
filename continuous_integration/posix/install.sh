#!/bin/bash

if [ "$CIRCLECI" = "true" ]; then
    export TRAVIS_OS_NAME="linux"
fi

if [ "$USE_CONDA" = "no" ]; then
    export PIP_DEPENDENCIES_FLAGS="-q"
    export PIP_DEPENDENCIES="coveralls"
    export CONDA_DEPENDENCIES=""
else
    export CONDA_DEPENDENCIES_FLAGS="--quiet"
    export CONDA_DEPENDENCIES="rope pyflakes sphinx pygments pylint psutil nbconvert \
                               qtawesome cloudpickle pickleshare qtpy pyzmq chardet mock nomkl pandas \
                               pytest pytest-cov numpydoc scipy cython pillow jedi pycodestyle keyring \
                               testpath"
    export TESTPATH_VERSION="0.3.1"
    export PIP_DEPENDENCIES="coveralls pytest-qt pytest-mock pytest-timeout flaky"
fi


# Download and install miniconda and conda/pip dependencies
# with astropy helpers
echo -e "PYTHON = $TRAVIS_PYTHON_VERSION \n============"
git clone git://github.com/astropy/ci-helpers.git > /dev/null
source ci-helpers/travis/setup_conda_$TRAVIS_OS_NAME.sh
source $HOME/miniconda/etc/profile.d/conda.sh
conda activate test


if [ "$USE_CONDA" = "no" ]; then
    # Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git

    # Install Spyder and its dependencies
    pip install -e .[test]
fi
