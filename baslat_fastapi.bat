@echo off
chcp 65001 > nul
title TarımDestekRAG — FastAPI REST Servisi (Port 8000)

echo ======================================================================
echo 🌾 TarımDestekRAG — FastAPI REST Servisi (Port 8000)
echo    Ana Sayfa: http://127.0.0.1:8000/
echo    Swagger UI: http://127.0.0.1:8000/docs
echo    Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
echo ======================================================================
echo.

cd /d "%~dp0"

set "PYTHONPATH=%~dp0;%~dp0backend\src;%PYTHONPATH%"
set "PYTHONIOENCODING=utf-8"

if exist ".venv\Scripts\uvicorn.exe" (
    echo [1/1] FastAPI Uvicorn başlatılıyor (0.0.0.0:8000)...
    ".venv\Scripts\uvicorn.exe" tarim_destek_rag.api.main:app --host 0.0.0.0 --port 8000
) else (
    echo [1/1] Sistem Uvicorn ile başlatılıyor...
    uvicorn tarim_destek_rag.api.main:app --host 0.0.0.0 --port 8000
)

pause
