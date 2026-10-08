@echo off
chcp 65001 > nul
title TarımDestekRAG — PC Başlatıcı

echo ======================================================================
echo 🌾 TarımDestekRAG — 2026 Resmî Tarım Destek Asistanı (PC Sürümü)
echo    Deterministik Kural Motoru & Sıfır Halüsinasyon (Zero-LLM)
echo    Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [1/2] Sanal ortam bulundu (.venv). Başlatılıyor...
    ".venv\Scripts\python.exe" run_pc.py
) else (
    echo [1/2] Sistem Python ile başlatılıyor...
    python run_pc.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Bir hata oluştu! Çıkmak için bir tuşa basınız...
    pause > nul
)
