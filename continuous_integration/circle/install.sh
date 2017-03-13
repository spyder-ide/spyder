#!/bin/bash

# We use container 3 to run our tests with pip packages
if [ "$CIRCLE_NODE_INDEX" = "3" ]; then
    export PIP_DEPENDENCIES_FLAGS="-q"
    export PIP_DEPENDENCIES="coveralls"
    export CONDA_DEPENDENCIES=""
else
    export CONDA_DEPENDENCIES_FLAGS="--quiet"
    export CONDA_DEPENDENCIES="rope pyflakes sphinx pygments pylint pep8 psutil nbconvert \
                               qtawesome pickleshare qtpy pyzmq chardet mock nomkl pandas \
                               pytest pytest-cov numpydoc scipy"
    export PIP_DEPENDENCIES="coveralls pytest-qt pytest-xvfb flaky jedi"
fi


# Download and install miniconda and conda/pip dependencies
# with astropy helpers
export PY_VERSIONS=($PY_VERSIONS)
export TRAVIS_PYTHON_VERSION=${PY_VERSIONS[$CIRCLE_NODE_INDEX]}
echo -e "PYTHON = $TRAVIS_PYTHON_VERSION \n============"
git clone git://github.com/astropy/ci-helpers.git > /dev/null
source ci-helpers/travis/setup_conda_$TRAVIS_OS_NAME.sh
export PATH="$HOME/miniconda/bin:$PATH"
source activate test


# Install Spyder
if [ "$CIRCLE_NODE_INDEX" = "3" ]; then
    pip install -q -e .[test]
else
    conda install -q ciocheck -c spyder-ide --no-update-deps
    python setup.py install > /dev/null
fi
