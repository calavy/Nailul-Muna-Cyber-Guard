# ============================================================
# modul/browser_aktivitas.py
# Membaca riwayat website & unduhan dari Chrome / Edge (Windows)
# ============================================================

import os
import sqlite3
import shutil
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse


def _chrome_time_ke_datetime(chrome_time):
    # Waktu Chrome: mikrodetik sejak 1601-01-01 UTC
    if not chrome_time:
        return None
    try:
        epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        return (epoch.timestamp() + (chrome_time / 1_000_000))
    except (OverflowError, ValueError, TypeError):
        return None


def _format_waktu(chrome_time):
    ts = _chrome_time_ke_datetime(chrome_time)
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _jalur_profil_browser():
    # Mengembalikan daftar (nama_browser, folder_profil)
    lokal = os.environ.get("LOCALAPPDATA", "")
    daftar = []
    kandidat = [
        ("chrome", os.path.join(lokal, "Google", "Chrome", "User Data", "Default")),
        ("msedge", os.path.join(lokal, "Microsoft", "Edge", "User Data", "Default")),
    ]
    for nama, jalur in kandidat:
        if os.path.isdir(jalur):
            daftar.append((nama, jalur))
    return daftar


def _salin_db(jalur_asli):
    # Menyalin DB agar tidak terkunci saat browser terbuka
    if not os.path.isfile(jalur_asli):
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    try:
        shutil.copy2(jalur_asli, tmp.name)
        return tmp.name
    except OSError:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        return None


def ambil_riwayat_website(batas=15):
    # Mengambil URL terakhir dari riwayat Chrome/Edge
    hasil = []
    for browser, profil in _jalur_profil_browser():
        history = os.path.join(profil, "History")
        salinan = _salin_db(history)
        if not salinan:
            continue
        try:
            conn = sqlite3.connect(salinan)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT url, title, last_visit_time
                FROM urls
                ORDER BY last_visit_time DESC
                LIMIT ?
                """,
                (batas,),
            )
            for url, title, visit_time in cur.fetchall():
                hasil.append({
                    "browser": browser,
                    "url": url or "",
                    "judul": title or "",
                    "waktu": _format_waktu(visit_time),
                    "domain": urlparse(url or "").netloc.replace("www.", ""),
                })
            conn.close()
        except sqlite3.Error:
            pass
        finally:
            try:
                os.unlink(salinan)
            except OSError:
                pass
    # Urutkan gabungan (string waktu) dan potong
    hasil.sort(key=lambda x: x["waktu"], reverse=True)
    return hasil[:batas]


def ambil_riwayat_unduhan(batas=15):
    # Mengambil unduhan terakhir dari Chrome/Edge
    hasil = []
    for browser, profil in _jalur_profil_browser():
        history = os.path.join(profil, "History")
        salinan = _salin_db(history)
        if not salinan:
            continue
        try:
            conn = sqlite3.connect(salinan)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT target_path, tab_url, start_time, total_bytes, mime_type
                FROM downloads
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (batas,),
            )
            for path, tab_url, start_time, total_bytes, mime_type in cur.fetchall():
                nama_file = os.path.basename(path or "") if path else ""
                ekstensi = os.path.splitext(nama_file)[1].lower()
                hasil.append({
                    "browser": browser,
                    "nama_file": nama_file,
                    "jalur": path or "",
                    "url_sumber": tab_url or "",
                    "waktu": _format_waktu(start_time),
                    "ukuran": total_bytes or 0,
                    "tipe": mime_type or "",
                    "ekstensi": ekstensi,
                    "perlu_izin": ekstensi in (".apk", ".exe", ".msi", ".bat", ".cmd", ".msix"),
                })
            conn.close()
        except sqlite3.Error:
            pass
        finally:
            try:
                os.unlink(salinan)
            except OSError:
                pass
    hasil.sort(key=lambda x: x["waktu"], reverse=True)
    return hasil[:batas]
