@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title TerraTwin - Earth Analog Explorer
color 0B
echo ===========================================================
echo   TerraTwin v2.1 - NASA + Earth and planetary data
ECHO   Open http://localhost:8546
ECHO ===========================================================
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo Python 3.11+ required.
        pause
        exit /b 1
    )
)
echo [2/3] Checking required packages...
".venv\Scripts\python.exe" -c "import streamlit, streamlit_folium, folium, pandas, plotly, requests" >nul 2>&1
if errorlevel 1 (
    echo Required packages are missing. Installing without pip cache...
    ".venv\Scripts\python.exe" -m pip install --no-cache-dir -r requirements.txt
    if errorlevel 1 (
        echo Installation failed. Check free disk space and internet access.
        pause
        exit /b 1
    )
) else (
    echo Packages already installed - skipping download.
)
echo [3/3] Running http://localhost:8546
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8546 --server.headless false
if errorlevel 1 echo Could not start on port 8546. Close another instance.
pause
