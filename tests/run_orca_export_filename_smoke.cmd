@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /EHsc /std:c++17 /I C:\Users\justw\OrcaClean\OrcaSlicer\src\slic3r\GUI tests\orca_export_filename_smoke.cpp /Foartifacts\orca-export-check\filename.obj /Feartifacts\orca-export-check\filename.exe
if errorlevel 1 exit /b 1
artifacts\orca-export-check\filename.exe
exit /b %errorlevel%
