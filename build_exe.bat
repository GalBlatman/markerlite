@echo off
rem Build markerlite.exe - run this ON WINDOWS. PyInstaller cannot cross-compile,
rem so a Windows binary has to be produced on a Windows machine (or by the
rem GitHub Actions workflow in .github\workflows\build-windows.yml).
setlocal

echo Installing build dependencies...
python -m pip install --quiet --upgrade pyinstaller pymupdf scikit-learn rapidfuzz regex numpy tkinterdnd2
if errorlevel 1 goto :fail

echo.
echo Building (this takes a couple of minutes)...
python -m PyInstaller --noconfirm --onedir --windowed ^
  --name markerlite ^
  --collect-all tkinterdnd2 ^
  --collect-submodules sklearn ^
  --add-data "markerlite.py;." ^
  --add-data "table_recon.py;." ^
  "%~dp0markerlite_gui.py"
if errorlevel 1 goto :fail

echo.
echo Done. The app is the folder:  %~dp0dist\markerlite\
echo Run markerlite.exe inside it. Keep the folder together - the DLLs beside it are needed.
echo.
echo NOTE: scanned PDFs still need Tesseract installed separately and on PATH.
echo Digital PDFs - which is nearly everything from a publisher - work without it.
pause
exit /b 0

:fail
echo.
echo Build failed. Check that "python" is on PATH and try again.
pause
exit /b 1
