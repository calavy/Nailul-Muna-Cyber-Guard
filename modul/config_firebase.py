# ============================================================
# modul/config_firebase.py
# Membaca URL Firebase dari config.json (satu sumber untuk Windows)
# ============================================================

import json
import os

# Folder akar proyek (satu tingkat di atas folder modul)
FOLDER_PROYEK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Jalur file config.json
JALUR_CONFIG = os.path.join(FOLDER_PROYEK, "config.json")

# Fallback jika config.json belum ada
URL_FALLBACK = "http://127.0.0.1:8765"


def baca_firebase_url():
    """
    Membaca firebase_url dari config.json.
    Jika file tidak ada / rusak, kembalikan URL lokal.
    """
    try:
        with open(JALUR_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
        url = (data.get("firebase_url") or "").strip().rstrip("/")
        if not url:
            return URL_FALLBACK
        return url
    except (OSError, json.JSONDecodeError, TypeError):
        return URL_FALLBACK


def mode_cloud(url=None):
    """True jika URL memakai https (Firebase cloud)."""
    u = url or baca_firebase_url()
    return u.lower().startswith("https://")
