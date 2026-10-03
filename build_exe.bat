@echo off
rem Build markerlite.exe - run this ON WINDOWS. PyInstaller cannot cross-compile,
rem so a Windows binary has to be produced on a Windows machine (or by the
rem GitHub Actions workflow in .github\workflows\build-windows.yml).
rem
rem Every path is quoted and the script works from its own folder (pushd), so
rem it runs from any current directory and from a folder whose name holds
rem spaces or "&".
setlocal
pushd "%~dp0" || (echo Cannot enter the folder of this script. & exit /b 1)

echo Installing build dependencies...
python -m pip install --quiet -c "requirements-lock.txt" -e ".[gui,build]"
if errorlevel 1 goto :fail

echo.
echo Building (this takes a couple of minutes)...
python -m PyInstaller --noconfirm --onedir --windowed ^
  --name markerlite ^
  --collect-all tkinterdnd2 ^
  --collect-submodules sklearn ^
  --icon "assets\icon.ico" ^
  --add-data "assets;assets" ^
  --add-data "markerlite.py;." ^
  --add-data "markerlite/VERSION;markerlite" ^
  --add-data "table_recon.py;." ^
  "markerlite_gui.py"
if errorlevel 1 goto :fail

echo.
echo Done. The app is the folder: "%CD%\dist\markerlite\"
echo Run markerlite.exe inside it. Keep the folder together - the DLLs beside it are needed.
echo.
echo NOTE: scanned PDFs still need Tesseract installed separately and on PATH.
echo Digital PDFs - which is nearly everything from a publisher - work without it.
popd
pause
exit /b 0

:fail
echo.
echo Build failed. Check that "python" is on PATH and try again.
popd
pause
exit /b 1
