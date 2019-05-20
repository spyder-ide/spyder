:: Install dependencies
if %USE_CONDA% == yes (
    conda install -q -y -c spyder-ide --file requirements/conda.txt
    if errorlevel 1 exit 1

    conda install -q -y -c spyder-ide --file requirements/tests.txt
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
)

:: The newly introduced changes to the Python packages in Anaconda
:: are breaking our tests. Reverting to known working builds.
::if %PYTHON_VERSION% == 2.7 (
::    conda install -q -y python=2.7.15=hcb6e200_5
::) else if %PYTHON_VERSION% == 3.6 (
::    conda install -q -y python=3.6.8=h9f7ef89_0
::)

:: Install spyder-kernels from master
pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
if errorlevel 1 exit 1

:: Install codecov
pip install -q codecov
if errorlevel 1 exit 1
