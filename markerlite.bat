@echo off
rem Launch the markerlite GUI with no console window.
rem pythonw is the windowless interpreter; if it isn't on PATH, edit the line
rem below to the full path, e.g. C:\Users\galbl\AppData\Local\Programs\Python\Python312\pythonw.exe
start "" pythonw "%~dp0markerlite_gui.py"
