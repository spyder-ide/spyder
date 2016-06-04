#!/usr/bin/env bash

set -ex

PY_VERSION=$TRAVIS_PYTHON_VERSION
WHEELHOUSE_URI=travis-wheels.scikit-image.org

#==============================================================================
# Utility functions
#==============================================================================
download_code()
{
    # We need to make a full git clone because Travis only does shallow
    # ones, which are useless to build conda packages using git_url
    # and git_tag.
    PR=$TRAVIS_PULL_REQUEST
    mkdir $FULL_SPYDER_CLONE
    git clone https://github.com/spyder-ide/spyder.git $FULL_SPYDER_CLONE
    if [ "$PR" != "false" ] ; then
        cd $FULL_SPYDER_CLONE
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

    # Update conda
    conda update -q conda;

    # Add our own channel for our own packages
    if [ "$USE_CONDA" = true ]; then
        conda config --add channels spyder-ide;
        echo 'conda-build ==1.18.1' > $HOME/miniconda/conda-meta/pinned;
        conda install conda-build;
        conda create -q -n test-environment python=$PY_VERSION;
        conda install -q -y -n test-environment pytest pytest-cov pytest-qt
    fi
}


install_pip()
{
    if [ "$USE_QT_API" = "PyQt5" ]; then
        conda install pyqt5;
    elif [ "$USE_QT_API" = "PyQt4" ]; then
        conda install pyqt;
    fi

    pip install --no-index --trusted-host $WHEELHOUSE_URI --find-links=http://$WHEELHOUSE_URI/ ;
    EXTRA_PACKAGES="matplotlib pandas sympy pyzmq pillow pytest pytest-cov pytest-qt"
    pip install $EXTRA_PACKAGES
}


#==============================================================================
# Main
#==============================================================================
download_code;

# Use conda even to test pip!
install_conda;

if [ "$USE_CONDA" = false ]; then
    install_pip;
fi
