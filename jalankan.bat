@echo off
REM ============================================================
REM Skrip cepat menjalankan NME Guardian (uji lokal)
REM ============================================================
cd /d "%~dp0"

set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

echo [1/2] Menjalankan Firebase Lokal di jendela baru...
start "Firebase Lokal NME" cmd /k python firebase_lokal.py

timeout /t 2 /nobreak >nul

echo [2/2] Menjalankan NME Guardian Windows...
echo Panel admin: http://localhost/Nailul%%20Muna%%20Cyber%%20Guard/admin/
python pantau.py
