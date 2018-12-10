:: Install dependencies
conda install -q -y -c spyder-ide --file requirements/conda.txt
conda install -q -y -c spyder-ide --file requirements/tests.txt

:: Install spyder-kernels from master
pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels
