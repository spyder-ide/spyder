#!/bin/bash -ex

# -- Install Miniconda
#MINICONDA=Miniconda3-latest-Linux-x86_64.sh
#wget https://repo.continuum.io/miniconda/$MINICONDA -O miniconda.sh
#bash miniconda.sh -b -p $HOME/miniconda
#source $HOME/miniconda/etc/profile.d/conda.sh


# -- Make new conda environment with required Python version
#if [ "$PYTHON_VERSION" = "3.8-dev" ]; then
#    conda create -y -n test -c conda-forge/label/pre-3.8 python
#else
#    conda create -y -n test python=$PYTHON_VERSION
#fi
#conda activate test


# -- Installl dependencies
#if [ "$USE_CONDA" = "yes" ]; then
#    # Install nomkl to avoid installing Intel MKL libraries
 #   conda install -q -y nomkl
#
#    # Install main dependencies
#    conda install -q -y -c spyder-ide --file requirements/conda.txt
#
#    # Install test ones
#    conda install -q -y -c spyder-ide --file requirements/tests.txt
#
#    # Install coveralls
#    pip install -q coveralls
#
#    # Install spyder-kernels from Github with no deps
#    pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
#else
     # pip uninstall -y Cython
     pip install Cython
    # Install Spyder and its dependencies from our setup.py
     pip install pyzmq
     pip install tornado
     pip install qtconsole
     pip install pyqt5
     pip install PyQtWebEngine
    # pip install nomkl


     pip install pygments
     pip install qdarkstyle
     pip install sphinx
     pip install python-language-server
     pip install nbconvert
     pip install IPython

    # Install qtpy from Github
     pip install git+https://github.com/spyder-ide/qtpy.git

    # Install qtconsole from Github
     pip install git+https://github.com/jupyter/qtconsole.git

    # Install spyder-kernels from Github
     pip install git+https://github.com/oscargus/spyder-kernels.git@removeddeprecatedimport

    # Downgrade Jedi because 0.14 broke the PyLS
     pip install jedi==0.13.3

     pip install atomicwrites
     pip install Pillow
     pip install qtawesome
     pip install diff_match_patch
     pip install chardet>=2.0
     pip install 'pytest<5.0'
     pip install pytest-cov
     pip install pytest-mock
     pip install pytest-qt
     pip install pytest-ordering
     pip install pytest-lazy-fixture
     pip install mock
     pip install numpy
     pip install pandas
#    pip install scipy
    pip install  sympy
    pip install matplotlib
    pip install flaky
    pip install keyring
    pip install numpydoc
    pip install pexpect
    pip install pickleshare
    pip install psutil
    pip install pylint
    pip install watchdog
    pip install xdg
    # Remove pytest-xvfb because it causes hangs
     pip uninstall -q -y pytest-xvfb
#fi
