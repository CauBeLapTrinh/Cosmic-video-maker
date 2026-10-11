@echo off
title Cosmic Video Maker Studio
echo ========================================================
echo           Starting Cosmic Video Maker Studio
echo ========================================================
echo.

IF EXIST .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    streamlit run app.py
) ELSE (
    python -m streamlit run app.py
)

pause
