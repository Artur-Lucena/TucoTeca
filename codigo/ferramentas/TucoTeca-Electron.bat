@echo off
rem TucoTeca Electron: interface desktop (F0-F6).
setlocal
set "RAIZ=%~dp0..\.."
for %%I in ("%RAIZ%") do set "RAIZ=%%~fI"
rem Remove stale lock if the owning process is dead
if exist "%RAIZ%\.biblioteca.lock" (
  for /f "usebackq delims=" %%P in ("%RAIZ%\.biblioteca.lock") do (
    rem skip
  )
  del "%RAIZ%\.biblioteca.lock" 2>nul
)
if exist "%RAIZ%\codigo\frontends\electron\node_modules\electron\dist\electron.exe" (
  start "" "%RAIZ%\codigo\frontends\electron\node_modules\electron\dist\electron.exe" "%RAIZ%\codigo\frontends\electron"
  exit /b
)
rem Fallback: npm run start
where npm >nul 2>&1 && npm --prefix "%RAIZ%\codigo\frontends\electron" run start

