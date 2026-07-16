# ============================================================
# uji_firebase.py — Uji PUT/GET ke URL di config.json
# ============================================================

import sys
from datetime import datetime

import requests

from modul.config_firebase import baca_firebase_url, mode_cloud

TIMEOUT = 15


def utama():
    url = baca_firebase_url()
    print("=" * 60)
    print(" Uji koneksi Firebase — NME Guardian")
    print(f" URL: {url}")
    print(f" Mode: {'CLOUD (https)' if mode_cloud(url) else 'LOKAL / non-https'}")
    print("=" * 60)

    if "PROYEK-ANDA" in url:
        print("[GAGAL] URL masih placeholder di config.")
        print("Edit config.json dengan URL Realtime Database Anda.")
        print("Lihat CARA_FIREBASE.txt")
        sys.exit(2)

    # GET status_blokir
    try:
        r = requests.get(f"{url}/status_blokir.json", timeout=TIMEOUT)
        print(f"[GET] status_blokir -> HTTP {r.status_code} | isi={r.json()}")
        if r.status_code != 200:
            raise RuntimeError(f"GET gagal: {r.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[GAGAL] Tidak bisa terhubung: {e}")
        if not mode_cloud(url):
            print("Tips lokal: jalankan dulu python firebase_lokal.py")
        else:
            print("Tips cloud: cek URL, Rules (.read/.write), dan internet")
        sys.exit(1)

    # PUT ping uji
    payload = {
        "ok": True,
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sumber": "uji_firebase.py",
    }
    try:
        r = requests.put(f"{url}/uji_koneksi.json", json=payload, timeout=TIMEOUT)
        print(f"[PUT] uji_koneksi -> HTTP {r.status_code}")
        if r.status_code != 200:
            raise RuntimeError(f"PUT gagal: {r.status_code} {r.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"[GAGAL] PUT: {e}")
        sys.exit(1)

    # Seed ringan status_blokir jika null
    try:
        r = requests.get(f"{url}/status_blokir.json", timeout=TIMEOUT)
        if r.json() is None:
            requests.put(f"{url}/status_blokir.json", json=False, timeout=TIMEOUT)
            print("[OK] status_blokir di-set false (sebelumnya null)")
    except requests.exceptions.RequestException:
        pass

    print("=" * 60)
    print(" SEMUA UJI BERHASIL — Firebase siap dipakai")
    print("=" * 60)


if __name__ == "__main__":
    utama()
