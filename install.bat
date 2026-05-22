@echo off
echo Installing StyleSwitcher GUI dependencies...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Error installing dependencies. Please make sure Python and pip are installed and in your PATH.
    pause
    exit /b 1
)

echo Dependencies installed successfully!
echo.
echo To run the StyleSwitcher GUI, use: python styleswitcher_gui.py
echo.
pause
