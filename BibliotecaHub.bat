@echo off
rem Biblioteca Hub — duplo-clique para abrir (usa o Python do sistema).
rem Portatil pronto p/ levar: dist\BibliotecaHub-portatil-*.zip
setlocal
set BIBLIOTECA_HOME=%~dp0
set PYW=
for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set PYW=%%P
if not defined PYW for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYW if exist "%%~dpPpythonw.exe" set PYW=%%~dpPpythonw.exe
if not defined PYW set PYW=python
start "Biblioteca Hub" "%PYW%" "%~dp0frontends\app_win.py"
