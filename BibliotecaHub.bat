@echo off
rem TucoTeca atualizada: runtime local e coleção desta pasta.
setlocal
if not defined BIBLIOTECA_HOME set "BIBLIOTECA_HOME=%~dp0"
if exist "%~dp0programa\windows-x64\python\pythonw.exe" (
  start "TucoTeca" "%~dp0programa\windows-x64\python\pythonw.exe" "%~dp0codigo\ferramentas\abrir_hub.py" %*
  exit /b
)
set PYW=
for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set PYW=%%P
if not defined PYW for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYW if exist "%%~dpPpythonw.exe" set PYW=%%~dpPpythonw.exe
if not defined PYW set PYW=python
start "TucoTeca" "%PYW%" "%~dp0codigo\ferramentas\abrir_hub.py" %*
