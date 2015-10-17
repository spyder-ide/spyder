#!/usr/bin/env bash

set -ex

PY_VERSION=$TRAVIS_PYTHON_VERSION
WHEELHOUSE_URI=http://travis-wheels.scikit-image.org/

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
    conda install jinja2;
    conda install conda-build;

    conda create -q -n test-environment python=$PY_VERSION;

    # Test environments for different Qt bindings
    if [ "$USE_QT_API" = "PyQt5" ]; then
        conda config --add channels spyder-ide;
    fi
}


install_pyside()
{
    # Currently support for python 2.7, 3.3, 3.4
    # http://stackoverflow.com/questions/24489588/how-can-i-install-pyside-on-travis
    sudo apt-get install libqt4-dev;
    pip install --upgrade pip;
    pip install PySide --no-index --find-links=$WHEELHOUSE_URI;  
    # Travis CI servers use virtualenvs, so we need to finish the install by the following
    POSTINSTALL=$(find ~/virtualenv/ -type f -name "pyside_postinstall.py";)
    python $POSTINSTALL -install;
}


install_qt4()
{
    # Install Qt and then update the Matplotlib settings
    sudo apt-get install -q libqt4-dev pyqt4-dev-tools;

    if [[ $PY_VERSION == 2.7* ]]; then
        sudo apt-get install python-dev
        sudo apt-get install -q python-qt4
    else  
        sudo apt-get install python3-dev
    fi

    # http://stackoverflow.com/a/9716100
    LIBS=( PyQt4 sip.so )

    VAR=( $(which -a python$PY_VERSION) )

    GET_PYTHON_LIB_CMD="from distutils.sysconfig import get_python_lib; print (get_python_lib())"
    LIB_VIRTUALENV_PATH=$(python -c "$GET_PYTHON_LIB_CMD")
    LIB_SYSTEM_PATH=$(${VAR[-1]} -c "$GET_PYTHON_LIB_CMD")

    for LIB in ${LIBS[@]}
    do
        sudo ln -sf $LIB_SYSTEM_PATH/$LIB $LIB_VIRTUALENV_PATH/$LIB
    done
}


install_qt5()
{
    echo "Not supported yet"
}


install_apt_pip()
{  
    # Test for different Qt bindings
    if [ "$USE_QT_API" = "PyQt5" ]; then
        #sudo apt-get install -qq python-sip python-qt5 python-sphinx --fix-missing;
        #sudo apt-get install -qq python3-sip python3-pyqt5 --fix-missing;
        install_qt5
    elif [ "$USE_QT_API" = "PyQt4" ]; then
        install_qt4;
    elif [ "$USE_QT_API" = "PySide" ]; then
        install_pyside;
    fi

    pip install -U pip;
    pip install -U setuptools;
    pip install --no-index --find-links=$WHEELHOUSE_URI $EXTRA_PACKAGES;
}


#==============================================================================
# Main
#==============================================================================
download_code;

if [ "$USE_CONDA" = true ] ; then
    export SOURCE=`source activate test-environment`
    install_conda;
else
    export EXTRA_PACKAGES="matplotlib pandas sympy pyzmq pillow"
    install_apt_pip;
fi
