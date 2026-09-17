@echo off
setlocal
set "PROFILELAB_TEST_EXE=%USERPROFILE%\OrcaClean\OrcaSlicer-upstream-test\build\src\Release\orca-slicer.exe"
if not exist "%PROFILELAB_TEST_EXE%" (
  echo The pinned Orca test build was not found. See docs\upstream-variant-audit.md.
  pause
  exit /b 1
)
rem Always isolate this development build from normal OrcaSlicer user profiles.
start "" "%PROFILELAB_TEST_EXE%" --datadir "%~dp0artifacts\variant-comparison\development-sender"
endlocal
