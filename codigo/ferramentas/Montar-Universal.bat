@echo off
rem TucoTeca — monta o pacote universal (Windows + Linux + Mac) em dist/.
rem Precisa dos artefatos prontos: Setup.exe (montar_portatil.py --setup)
rem e .run (montar_linux.py). O payload Mac é gerado na hora.
setlocal
cd /d "%~dp0..\.."
py -3.14 codigo\ferramentas\montar_universal.py %*
if errorlevel 1 pause
