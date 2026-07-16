# ============================================================
# Uji otomatis checklist NME Guardian
# ============================================================
# Menguji: koneksi Firebase lokal, kirim data, status_blokir,
# dan penutupan proses bernama chrome.exe (salinan uji aman).
# ============================================================

import os
import sys
import time
import shutil
import subprocess
import tempfile

import requests

# Memastikan import pantau dari folder yang sama
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pantau import (
    FIREBASE_URL,
    URL_APLIKASI_DIBUKA,
    URL_STATUS_BLOKIR,
    ambil_aplikasi_yang_berjalan,
    kirim_ke_firebase,
    ambil_status_blokir,
    tutup_aplikasi_terlarang,
)


def pastikan_firebase_lokal():
    # Mengecek apakah server lokal sudah hidup
    try:
        r = requests.get(f"{FIREBASE_URL}/status_blokir.json", timeout=2)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def set_status_blokir(nilai):
    # Menulis boolean status_blokir ke Firebase lokal
    r = requests.put(URL_STATUS_BLOKIR, json=nilai, timeout=5)
    r.raise_for_status()
    print(f"[OK] status_blokir = {nilai}")


def uji_online():
    print("--- Uji Online / kirim data ---")
    daftar = ambil_aplikasi_yang_berjalan()
    print(f"[INFO] Proses terdeteksi: {len(daftar)}")
    ok_kirim = kirim_ke_firebase(daftar)
    status, ok_baca = ambil_status_blokir()
    print(f"[INFO] kirim_sukses={ok_kirim}, baca_sukses={ok_baca}, status_blokir={status}")
    if not (ok_kirim and ok_baca):
        raise RuntimeError("Firebase Offline — gagal uji Online")
    # Pastikan data tersimpan
    cek = requests.get(URL_APLIKASI_DIBUKA, timeout=5).json()
    if not cek or "jumlah_aplikasi" not in cek:
        raise RuntimeError("Node aplikasi_dibuka tidak terisi")
    print("[OK] Firebase Online dan aplikasi_dibuka terisi")


def uji_blokir_chrome():
    print("--- Uji blokir chrome.exe (proses uji aman) ---")
    # Menyalin notepad sebagai chrome.exe di folder sementara
    # agar proses bernama chrome.exe tanpa menutup Chrome asli
    folder = tempfile.mkdtemp(prefix="nme_uji_")
    jalur_palsu = os.path.join(folder, "chrome.exe")
    shutil.copy2(r"C:\Windows\System32\notepad.exe", jalur_palsu)

    # Menjalankan proses palsu
    proc = subprocess.Popen([jalur_palsu])
    time.sleep(1)
    print(f"[INFO] Proses uji chrome.exe PID={proc.pid}")

    # Mengaktifkan blokir lalu menutup
    set_status_blokir(True)
    status, ok = ambil_status_blokir()
    if not (ok and status):
        proc.terminate()
        raise RuntimeError("status_blokir tidak aktif")

    ditutup = tutup_aplikasi_terlarang()
    time.sleep(0.5)
    masih_hidup = proc.poll() is None
    if masih_hidup:
        proc.kill()
        raise RuntimeError(f"chrome.exe uji tidak tertutup. ditutup={ditutup}")

    print(f"[OK] Proses uji ditutup: {ditutup}")
    set_status_blokir(False)

    # Membersihkan folder sementara
    try:
        shutil.rmtree(folder, ignore_errors=True)
    except OSError:
        pass


def utama():
    print("=" * 60)
    print(" Uji checklist NME Guardian")
    print(f" FIREBASE_URL = {FIREBASE_URL}")
    print("=" * 60)

    if not pastikan_firebase_lokal():
        print("[GAGAL] Firebase lokal belum jalan.")
        print("Jalankan dulu di terminal lain: python firebase_lokal.py")
        sys.exit(1)

    # Node awal sesuai checklist
    set_status_blokir(False)
    uji_online()
    uji_blokir_chrome()
    print("=" * 60)
    print(" SEMUA UJI BERHASIL")
    print("=" * 60)


if __name__ == "__main__":
    utama()
