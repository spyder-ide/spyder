#!/bin/bash

# We test with pip packages in Python 3.5 and PyQt5
if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ] && [ "$USE_PYQT" = "pyqt5" ]; then
    export PIP_DEPENDENCIES_FLAGS="-q"
    export PIP_DEPENDENCIES="coveralls"
    export CONDA_DEPENDENCIES=""
else
    export CONDA_DEPENDENCIES_FLAGS="--quiet"
    export CONDA_DEPENDENCIES="rope pyflakes sphinx pygments pylint psutil nbconvert \
                               qtawesome cloudpickle pickleshare qtpy pyzmq chardet mock nomkl pandas \
                               pytest pytest-cov numpydoc scipy cython pillow jedi pycodestyle"
    export PIP_DEPENDENCIES="coveralls pytest-qt pytest-mock pytest-timeout flaky"
fi


# Download and install miniconda and conda/pip dependencies
# with astropy helpers
echo -e "PYTHON = $TRAVIS_PYTHON_VERSION \n============"
git clone git://github.com/astropy/ci-helpers.git > /dev/null
source ci-helpers/travis/setup_conda_$TRAVIS_OS_NAME.sh
export PATH="$HOME/miniconda/bin:$PATH"
source activate test


# We test with pip packages in Python 3.5 and PyQt5
if [ "$TRAVIS_PYTHON_VERSION" = "3.5" ] && [ "$USE_PYQT" = "pyqt5" ]; then
    # Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git

    # Install Spyder and its dependencies
    pip install -q -e .[test]

    # Run with tornado < 5.0 for now
    pip install tornado==4.5.3
fi
