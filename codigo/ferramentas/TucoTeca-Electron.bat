@echo off
rem TucoTeca Electron pelo checkout (desenvolvimento). Usuario final: instalador.
rem O lock da colecao NAO e apagado aqui: o proprio app recusa lock vivo e
rem assume sozinho lock orfao (pid morto no mesmo host). Apagar as cegas
rem permitiria duas instancias gravando no mesmo banco.
setlocal
set "RAIZ=%~dp0..\.."
for %%I in ("%RAIZ%") do set "RAIZ=%%~fI"
set "APP=%RAIZ%\codigo\frontends\electron"
if not exist "%APP%\out\main\index.js" (
  echo App Electron ainda nao compilado. Rode: npm --prefix "%APP%" run build
  exit /b 1
)
if exist "%APP%\node_modules\electron\dist\electron.exe" (
  start "" "%APP%\node_modules\electron\dist\electron.exe" "%APP%"
  exit /b
)
echo Dependencias ausentes. Rode: npm --prefix "%APP%" install
exit /b 1
