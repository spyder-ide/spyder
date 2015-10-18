#!/usr/bin/env bash

set -ex

PY_VERSION=$TRAVIS_PYTHON_VERSION
WHEELHOUSE_URI=travis-wheels.scikit-image.org

#==============================================================================
# Utility functions
#==============================================================================
download_code()
{
    PR=$TRAVIS_PULL_REQUEST
    mkdir ~/spy-clone
    git clone https://github.com/spyder-ide/spyder.git ~/spy-clone
    if [ "$PR" != "false" ] ; then
        cd ~/spy-clone
        git fetch origin pull/$PR/head:travis_pr_$PR
    fi
}


install_conda()
{
  # Define the value to download
    if [ "$TRAVIS_OS_NAME" = "linux" ]; then
        MINICONDA_OS=$MINICONDA_LINUX;
    elif [ "$TRAVIS_OS_NAME" = "osx" ]; then
        MINICONDA_OS=$MINICONDA_OSX;
    fi

    # You may want to periodically update this, although the conda update
    # conda line below will keep everything up-to-date.  We do this
    # conditionally because it saves us some downloading if the version is
    # the same.
    if [ "$PY_VERSION" = "2.7" ]; then
        wget "http://repo.continuum.io/miniconda/Miniconda-$MINICONDA_VERSION-$MINICONDA_OS.sh" -O miniconda.sh;
    else
        wget "http://repo.continuum.io/miniconda/Miniconda3-$MINICONDA_VERSION-$MINICONDA_OS.sh" -O miniconda.sh;
    fi

    bash miniconda.sh -b -p "$HOME/miniconda";
    export PATH="$HOME/miniconda/bin:$PATH";
    hash -r;
    conda config --set always_yes yes --set changeps1 no;

    # Pinning conda to this version because installing from tarballs is not
    # pulling deps in 3.18.2 and that breaks all our tests!!
    echo 'conda ==3.18.1' > $HOME/miniconda/conda-meta/pinned;
    conda update -q conda;

    # Installing conda-build and jinja2 to do build tests
    if [ "$USE_CONDA" = true ]; then
        conda install jinja2;
        conda install conda-build;
    fi

    conda create -q -n test-environment python=$PY_VERSION;

    # Test environments for different Qt bindings
    if [ "$USE_QT_API" = "PyQt5" ]; then
        conda config --add channels spyder-ide;
    fi
}


install_pyside()
{
    # Currently support Python 2.7 and 3.4
    # http://stackoverflow.com/questions/24489588/how-can-i-install-pyside-on-travis

    pip install -U setuptools;
    pip install -U pip;
    pip install --no-index --trusted-host $WHEELHOUSE_URI --find-links=http://$WHEELHOUSE_URI/ pyside;

    # Travis CI servers use virtualenvs, so we need to finish the install by the following
    POSTINSTALL=$(find ~/virtualenv/ -type f -name "pyside_postinstall.py";)
    python $POSTINSTALL -install;
}


install_qt5()
{
    echo "Not supported yet"
}


install_pip()
{
    # Test for different Qt bindings
    #if [ "$USE_QT_API" = "PyQt5" ]; then
    #    install_qt5
    #elif [ "$USE_QT_API" = "PySide" ]; then
    #    install_pyside;
    #fi

    if [ "$USE_QT_API" = "PyQt4" ]; then
        conda install pyqt;
    else
        conda install pyqt5;

    pip install --no-index --trusted-host $WHEELHOUSE_URI --find-links=http://$WHEELHOUSE_URI/ $EXTRA_PACKAGES;
}


#==============================================================================
# Main
#==============================================================================
download_code;

# Use conda even to test pip!
install_conda;

if [ "$USE_CONDA" = false ]; then
    export EXTRA_PACKAGES="matplotlib pandas sympy pyzmq pillow"
    install_pip;
fi
