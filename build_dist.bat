@echo off
REM Build standalone Windows distribution using PyInstaller
pyinstaller --noconfirm --onedir --windowed --name StyleSwitcherGUI --add-data "StyleSwitcher.ini;." --add-data "documentation.html;." styleswitcher_gui.py

echo Build complete. Browse the 'dist\StyleSwitcherGUI' folder for the distributable.
pause
