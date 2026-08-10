@echo off
setlocal
py -3.13 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --onefile --name vrt_setups_downloader --clean main.py
echo Build completata: dist\vrt_setups_downloader.exe
endlocal
