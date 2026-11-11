@echo off
setlocal
title TucoTeca - Git ao vivo
where git >nul 2>nul
if errorlevel 1 (
    echo Git nao encontrado no PATH.
    pause
    exit /b 1
)
rem Repositorio = pasta pai deste workspace (biblioteca). Pelo caminho da junction
rem IA\TucoTeca o pai lexico nao tem .git: cai no caminho absoluto.
set "REPO=%~dp0.."
if not exist "%REPO%\.git" set "REPO=D:\Tuco-Compartilhado\Jogos\biblioteca"
git -C "%REPO%" rev-parse --git-dir >nul 2>nul
if errorlevel 1 (
    echo Repositorio do Hub nao encontrado: %REPO%
    pause
    exit /b 1
)
:atualizar
if /I not "%~1"=="--uma-vez" cls
echo QoL 1.5 - Git do projeto
echo %REPO%
echo.
git --no-optional-locks -C "%REPO%" status --short --branch
echo.
git --no-optional-locks -C "%REPO%" diff --stat
echo.
git --no-pager -C "%REPO%" log --oneline -5 --decorate
if /I "%~1"=="--uma-vez" exit /b 0
echo.
echo Atualiza a cada 3 segundos. Ctrl+C para sair.
timeout /t 3 /nobreak >nul
goto atualizar
