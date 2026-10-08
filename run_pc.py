"""TarımDestekRAG — PC Başlatıcı (Tek Komutla Backend + Gradio UI).

Kullanım:
    python run_pc.py

Özellikler:
- Sanal ortamı (.venv) otomatik tespit eder
- PYTHONPATH değişkenlerini eksiksiz ayarlar
- Arka uç FastAPI (8000) zaten açıksa tekrar başlatmaya çalışmaz
- Gradio hazır olur olmaz varsayılan web tarayıcısını otomatik açar
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Windows konsolunda Unicode/Türkçe karakter ve emoji çökmesini engelle
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

BACKEND_HOST = os.getenv("API_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("API_PORT", "8000"))
GRADIO_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

# Kullanılacak Python yorumlayıcısını belirle
PYTHON_BIN = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def get_subproc_env() -> dict[str, str]:
    """Tüm modüllerin import edilebilmesi için PYTHONPATH'i hazırlar."""
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{PROJECT_ROOT};{BACKEND_SRC};{existing_pp}" if existing_pp else f"{PROJECT_ROOT};{BACKEND_SRC}"
    )
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def is_service_ready(url: str, timeout: float = 2.0) -> bool:
    """Belirtilen URL yanıt veriyor mu?"""
    try:
        r = httpx.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def wait_for_service(url: str, timeout: float = 30.0, step: float = 0.5) -> bool:
    """Servis 200 dönene kadar bekler."""
    start = time.time()
    while time.time() - start < timeout:
        if is_service_ready(url):
            return True
        time.sleep(step)
    return False


def open_browser_window(url: str) -> None:
    """Windows'ta tarayıcıyı öne getirerek açmayı garanti eder."""
    try:
        if sys.platform == "win32":
            os.system(f"start {url}")
        else:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)


def main() -> None:
    print("=" * 70)
    print("🌾 TarımDestekRAG — 2026 Resmî Tarım Destek Asistanı (PC Sürümü)")
    print("   Deterministik Kural Motoru & Sıfır Halüsinasyon (Zero-LLM)")
    print("   Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas) — Tüm Hakları Saklıdır")
    print("=" * 70)

    env = get_subproc_env()
    api_url = f"http://127.0.0.1:{BACKEND_PORT}"
    gradio_url = f"http://127.0.0.1:{GRADIO_PORT}"

    api_proc = None
    gradio_proc = None

    # 1. FastAPI Kontrol ve Başlatma
    if is_service_ready(f"{api_url}/health"):
        print(f"\n[1/2] ✅ FastAPI arka uç servisi zaten çalışıyor: {api_url}")
    else:
        print(f"\n[1/2] 🚀 FastAPI arka uç servisi başlatılıyor: {api_url}")
        api_cmd = [
            PYTHON_BIN,
            "-m",
            "uvicorn",
            "tarim_destek_rag.api.main:app",
            "--host",
            BACKEND_HOST,
            "--port",
            str(BACKEND_PORT),
        ]
        api_proc = subprocess.Popen(api_cmd, env=env)

        print("     Vektör veri tabanı ve modeller hazırlanıyor, lütfen bekleyin...")
        if not wait_for_service(f"{api_url}/health", timeout=35.0):
            print("❌ FastAPI arka uç servisi başlatılamadı!")
            if api_proc:
                api_proc.terminate()
            sys.exit(1)
        print("     ✅ FastAPI arka uç servisi hazır!")

    # 2. Gradio Arayüzü Kontrol ve Başlatma
    if is_service_ready(gradio_url):
        print(f"\n[2/2] ✅ Gradio PC Arayüzü zaten çalışıyor: {gradio_url}")
        print("🌐 Tarayıcı açılıyor...")
        open_browser_window(gradio_url)
    else:
        print(f"\n[2/2] 🖥️ Gradio PC Arayüzü başlatılıyor: {gradio_url}")
        gradio_cmd = [PYTHON_BIN, "frontend_pc/app.py"]
        gradio_proc = subprocess.Popen(gradio_cmd, env=env)


        # Gradio ayağa kalkınca tarayıcıyı aç
        if wait_for_service(gradio_url, timeout=25.0):
            print("\n" + "=" * 70)
            print("🎉 TARIM DESTEK RAG PC ARAYÜZÜ BAŞARIYLA AÇILDI!")
            print(f"👉 Web Arayüzü Adresi : {gradio_url}")
            print(f"👉 REST API Dokümanı   : {api_url}/docs")
            print("=" * 70)
            print("🌐 Tarayıcınız açılıyor, açılmazsa yukarıdaki adresi tarayıcınıza yapıştırın.\n")
            open_browser_window(gradio_url)
        else:
            print(f"⚠️ Gradio başlatıldı ancak port kontrolü zaman aşımına uğradı. Manuel açınız: {gradio_url}")


    # 3. Süreci Canlı Tut
    try:
        if gradio_proc:
            gradio_proc.wait()
        else:
            print("Çıkmak için Ctrl+C tuşlarına basınız...")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Sistem kapatılıyor...")
    finally:
        if gradio_proc:
            gradio_proc.terminate()
        if api_proc:
            api_proc.terminate()
        print("✅ Servisler temiz bir şekilde sonlandırıldı.")


if __name__ == "__main__":
    main()
