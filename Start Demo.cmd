@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo The project's Python environment was not found. Open this folder in VS Code and check the setup.
    pause
    exit /b 1
)
start "Slicer Profile Lab Demo" ".venv\Scripts\pythonw.exe" -m profilelab.desktop --demo
