@echo off
setlocal
py -3.13 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
curl.exe -L --fail --retry 3 https://www.7-zip.org/a/7zr.exe -o 7zr.exe
python -m PyInstaller --onefile --name vrt_setup_uploader --clean --add-binary "7zr.exe;." main.py
echo Build completata: dist\vrt_setup_uploader.exe
endlocal
