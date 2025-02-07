@echo off
echo Building SanSync with admin privileges...

:: Install requirements
pip install -r requirements.txt

:: Build executable
python setup.py build

echo Build complete! Executable can be found in the build directory.
pause