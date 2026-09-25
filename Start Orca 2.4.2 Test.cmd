@echo off
setlocal
set "PROFILELAB_TEST_EXE=%ProgramFiles%\OrcaSlicer\orca-slicer.exe"
set "PROFILELAB_TEST_DATA=%~dp0artifacts\orca-2.4.2-test"
if not exist "%PROFILELAB_TEST_EXE%" (
  echo Installed OrcaSlicer was not found.
  pause
  exit /b 1
)
if not exist "%PROFILELAB_TEST_DATA%" mkdir "%PROFILELAB_TEST_DATA%"
if not exist "%PROFILELAB_TEST_DATA%" (
  echo Cannot create the isolated test data folder. Orca was not started.
  pause
  exit /b 1
)
rem Uses the installed stable executable, but never the normal work profile folder.
start "" /D "%ProgramFiles%\OrcaSlicer" "%PROFILELAB_TEST_EXE%" --datadir "%PROFILELAB_TEST_DATA%"
endlocal
