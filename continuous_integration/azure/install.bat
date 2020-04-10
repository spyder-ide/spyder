call activate test

:: Install dependencies
if %USE_CONDA% == yes (
    conda install -q -y --file requirements/conda.txt
    if errorlevel 1 exit 1

    conda install -q -y -c spyder-ide --file requirements/tests.txt
    if errorlevel 1 exit 1

    :: Remove spyder-kernels to be sure that we use its subrepo
    conda remove -q -y --force spyder-kernels
    if errorlevel 1 exit 1

    :: Create environment for Jedi environments tests
    conda create -n jedi-test-env -q -y python=3.6 flask spyder-kernels
    if errorlevel 1 exit 1

    conda list -n jedi-test-env
    if errorlevel 1 exit 1

    :: Create environment to test conda activation before launching a spyder kernel
    conda create -n spytest-ž -q -y python=3.6 spyder-kernels
    if errorlevel 1 exit 1

    conda list -n spytest-ž
    if errorlevel 1 exit 1
) else (
    :: Install Spyder and its dependencies from our setup.py
    pip install -e .[test]
    if errorlevel 1 exit 1

    :: Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git
    if errorlevel 1 exit 1

    :: Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git
    if errorlevel 1 exit 1

    :: Remove spyder-kernels to be sure that we use its subrepo
    pip uninstall -q -y spyder-kernels
    if errorlevel 1 exit 1
)

where python

:: To check our manifest
python -m pip install check-manifest
if errorlevel 1 exit 1

:: Install python-language-server from master
python -m pip install -q --no-deps git+https://github.com/palantir/python-language-server
if errorlevel 1 exit 1

:: Install codecov
python -m pip install -q codecov
if errorlevel 1 exit 1
