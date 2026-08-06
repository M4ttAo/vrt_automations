@echo off
setlocal
py -3.13 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
curl.exe -L --fail --retry 3 https://www.7-zip.org/a/7zr.exe -o 7zr.exe
curl.exe -L --fail --retry 3 https://github.com/ip7z/7zip/releases/download/26.02/7z2602-extra.7z -o 7z-extra.7z
7zr.exe x 7z-extra.7z -o7z-extra -y
copy /Y 7z-extra\7z.exe 7z.exe
copy /Y 7z-extra\7z.dll 7z.dll
python -m PyInstaller --onefile --name vrt_setup_uploader --clean --add-binary "7z.exe;." --add-binary "7z.dll;." main.py
echo Build completata: dist\vrt_setup_uploader.exe
endlocal
