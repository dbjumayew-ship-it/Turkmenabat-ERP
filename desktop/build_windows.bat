@echo off
setlocal
cd /d %~dp0

if not exist .venv (
    py -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "Turkmenabat ERP" ^
  --icon "assets\app.ico" ^
  --add-data "config.json;." ^
  --add-data "assets;assets" ^
  --collect-all PySide6.QtWebEngineCore ^
  --collect-all PySide6.QtWebEngineWidgets ^
  src\main.py

echo.
echo Build completed:
echo %CD%\dist\Turkmenabat ERP\Turkmenabat ERP.exe
pause
