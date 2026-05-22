@echo off
setlocal

echo [1/3] Building standard onedir distribution...
pyinstaller --noconfirm --onedir --windowed --name StyleSwitcherGUI --add-data "StyleSwitcher.ini;." --add-data "documentation.html;." styleswitcher_gui.py
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [2/3] Creating no-zip variant folder...
if exist "dist\StyleSwitcherGUI_nozip" rmdir /s /q "dist\StyleSwitcherGUI_nozip"
xcopy "dist\StyleSwitcherGUI" "dist\StyleSwitcherGUI_nozip" /e /i /y >nul
if errorlevel 1 (
  echo Copy step failed.
  exit /b 1
)

echo [3/3] Expanding base_library.zip into a directory with same name...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path 'dist\StyleSwitcherGUI_nozip\_internal\base_library.zip' -DestinationPath 'dist\StyleSwitcherGUI_nozip\_internal\base_library_unpacked' -Force; Remove-Item 'dist\StyleSwitcherGUI_nozip\_internal\base_library.zip' -Force; Rename-Item 'dist\StyleSwitcherGUI_nozip\_internal\base_library_unpacked' 'base_library.zip'"
if errorlevel 1 (
  echo Failed to expand/convert base_library.zip.
  exit /b 1
)

echo Done.
echo Standard build: dist\StyleSwitcherGUI\
echo No-zip build: dist\StyleSwitcherGUI_nozip\
exit /b 0
