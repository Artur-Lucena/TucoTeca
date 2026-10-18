@echo off
rem TucoTeca Electron: interface desktop (F0-F6).
setlocal
cd /d "%~dp0codigo\frontends\electron"
if exist "%~dp0codigo\frontends\electron\node_modules\electron\dist\electron.exe" (
  start "" "%~dp0codigo\frontends\electron\node_modules\electron\dist\electron.exe" .
  exit /b
)
rem Fallback: npm run start
where npm >nul 2>&1 && npm run start

