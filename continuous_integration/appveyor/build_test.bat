:: Print basic testing info
conda info

:: Moving to where our code is
cd %APPVEYOR_BUILD_FOLDER%

:: We don't need git features because conda-build
:: can't handle them correctly on Windows
rmdir /S /Q .git

:: Build package
cd continuous_integration\conda-recipes

conda build -q spyder
if errorlevel 1 exit 1
