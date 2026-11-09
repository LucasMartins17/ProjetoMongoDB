@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Resolve Campus
echo.
echo   RESOLVE CAMPUS - Cuidar faz parte.
echo.
if exist ".venv\Scripts\python.exe" goto dependencies
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.10 ou superior com o Python Launcher py.
  pause
  exit /b 1
)
py -m venv .venv
if errorlevel 1 goto failed
:dependencies
".venv\Scripts\python.exe" -c "import flask, pymongo" >nul 2>nul
if not errorlevel 1 goto run
echo Instalando Flask e PyMongo no ambiente virtual...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
echo Abra http://127.0.0.1:5000 no navegador.
echo O sistema avisara se o servico MongoDB estiver desligado.
echo Para encerrar, pressione Ctrl+C nesta janela.
echo.
py app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Nao foi possivel iniciar. Confira a mensagem acima.
pause
exit /b 1
