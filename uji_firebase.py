# ============================================================
# uji_firebase.py — Uji PUT/GET ke URL di config.json
# Proyek: nailul-muna-cyber-guard
# ============================================================

import sys
from datetime import datetime

import requests

from modul.config_firebase import baca_firebase_url, mode_cloud

TIMEOUT = 15

# URL cadangan jika firebase_url masih 404 (database baru / region beda)
URL_CADANGAN = [
    "https://nailul-muna-cyber-guard-default-rtdb.asia-southeast1.firebasedatabase.app",
    "https://nailul-muna-cyber-guard-default-rtdb.firebaseio.com",
    "https://nailul-muna-cyber-guard-default-rtdb.us-central1.firebasedatabase.app",
    "https://nailul-muna-cyber-guard-default-rtdb.europe-west1.firebasedatabase.app",
]


def coba_get(url):
    r = requests.get(f"{url}/.json", timeout=TIMEOUT)
    return r


def seed_awal(url):
    """Mengisi node awal jika masih kosong."""
    nodes = {
        "status_blokir": False,
        "link_diblokir": {},
        "izin_instal": {},
        "aktivitas_online": {},
        "perangkat": {},
    }
    for nama, nilai in nodes.items():
        r = requests.get(f"{url}/{nama}.json", timeout=TIMEOUT)
        if r.status_code == 200 and r.json() is None:
            requests.put(f"{url}/{nama}.json", json=nilai, timeout=TIMEOUT)
            print(f"[OK] Seed node {nama}")


def cetak_bantuan_404():
    print()
    print("HTTP 404 = Realtime Database BELUM dibuat di proyek ini.")
    print("Langkah:")
    print("  1. https://console.firebase.google.com/")
    print("  2. Proyek: nailul-muna-cyber-guard")
    print("  3. Build -> Realtime Database -> Create Database")
    print("  4. Region: asia-southeast1 (disarankan)")
    print("  5. Rules uji: read/write true, lalu Publish")
    print("  6. Salin Database URL ke config.json (firebase_url)")
    print("  7. Jalankan lagi: python uji_firebase.py")
    print("Detail: CARA_FIREBASE.txt")


def utama():
    url = baca_firebase_url()
    print("=" * 60)
    print(" Uji koneksi Firebase — NME Guardian")
    print(" Proyek: nailul-muna-cyber-guard")
    print(f" URL config: {url}")
    print(f" Mode: {'CLOUD (https)' if mode_cloud(url) else 'LOKAL / non-https'}")
    print("=" * 60)

    if "PROYEK-ANDA" in url:
        print("[GAGAL] URL masih placeholder di config.")
        print("Lihat CARA_FIREBASE.txt")
        sys.exit(2)

    # Coba URL config, lalu cadangan
    kandidat = [url] + [u for u in URL_CADANGAN if u.rstrip("/") != url.rstrip("/")]
    url_aktif = None
    terakhir_kode = None

    for calon in kandidat:
        try:
            r = coba_get(calon)
            terakhir_kode = r.status_code
            print(f"[CEK] {calon} -> HTTP {r.status_code}")
            if r.status_code == 200:
                url_aktif = calon.rstrip("/")
                break
        except requests.exceptions.RequestException as e:
            print(f"[CEK] {calon} -> ERROR {e}")

    if not url_aktif:
        print("[GAGAL] Tidak ada URL Realtime Database yang merespons 200.")
        if terakhir_kode == 404:
            cetak_bantuan_404()
        else:
            print("Tips: cek internet, Rules, dan URL di Console.")
        sys.exit(1)

    if url_aktif != url.rstrip("/"):
        print(f"[INFO] URL aktif berbeda dari config. Pakai: {url_aktif}")
        print("Update firebase_url di config.json agar sesuai.")

    # GET status_blokir
    r = requests.get(f"{url_aktif}/status_blokir.json", timeout=TIMEOUT)
    print(f"[GET] status_blokir -> HTTP {r.status_code} | isi={r.json()}")
    if r.status_code != 200:
        print(f"[GAGAL] GET status_blokir: {r.status_code} {r.text[:200]}")
        sys.exit(1)

    # PUT ping uji
    payload = {
        "ok": True,
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sumber": "uji_firebase.py",
        "projectId": "nailul-muna-cyber-guard",
    }
    r = requests.put(f"{url_aktif}/uji_koneksi.json", json=payload, timeout=TIMEOUT)
    print(f"[PUT] uji_koneksi -> HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"[GAGAL] PUT: {r.status_code} {r.text[:200]}")
        print("Jika 401/403: buka Rules, izinkan .read/.write untuk uji.")
        sys.exit(1)

    seed_awal(url_aktif)

    print("=" * 60)
    print(" SEMUA UJI BERHASIL — Firebase cloud siap dipakai")
    print(f" URL aktif: {url_aktif}")
    print("=" * 60)


if __name__ == "__main__":
    utama()
