@echo off
call .\.venv\scripts\activate.bat
python.exe -m pip install --upgrade pip
pip install -r ./requirements.txt --upgrade
auto-py-to-exe -c ./pyautoinst-config.json
