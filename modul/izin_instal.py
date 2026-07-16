# ============================================================
# modul/izin_instal.py
# Memantau file APK/EXE/MSI. Jika belum diizinkan admin,
# file dipindah ke karantina dan permintaan dikirim ke Firebase.
# ============================================================

import os
import hashlib
import shutil
import uuid
from datetime import datetime

import requests

# Ekstensi yang wajib minta izin pengasuh
EKSTENSI_WAJIB_IZIN = {".apk", ".exe", ".msi", ".msix", ".bat", ".cmd"}

# Folder karantina di dalam proyek
FOLDER_KARANTINA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "karantina_instal",
)


def _pastikan_karantina():
    os.makedirs(FOLDER_KARANTINA, exist_ok=True)


def hash_file(jalur, potongan=1024 * 1024):
    # Hash SHA256 sebagian awal file (cepat) + ukuran
    h = hashlib.sha256()
    try:
        ukuran = os.path.getsize(jalur)
        with open(jalur, "rb") as f:
            h.update(f.read(potongan))
        return f"{h.hexdigest()[:16]}_{ukuran}"
    except OSError:
        return None


def ambil_izin_instal(firebase_url, timeout=10):
    try:
        r = requests.get(f"{firebase_url}/izin_instal.json", timeout=timeout)
        if r.status_code != 200:
            return {}
        return r.json() or {}
    except requests.exceptions.RequestException:
        return {}


def kirim_permintaan_izin(firebase_url, data, timeout=10):
    # Membuat node baru di /izin_instal/<id>
    id_req = data.get("id") or ("req_" + uuid.uuid4().hex[:10])
    data["id"] = id_req
    try:
        r = requests.put(
            f"{firebase_url}/izin_instal/{id_req}.json",
            json=data,
            timeout=timeout,
        )
        return r.status_code == 200, id_req
    except requests.exceptions.RequestException:
        return False, id_req


def update_status_izin(firebase_url, id_req, patch, timeout=10):
    try:
        r = requests.patch(
            f"{firebase_url}/izin_instal/{id_req}.json",
            json=patch,
            timeout=timeout,
        )
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def karantina_file(jalur_asli):
    # Memindahkan file ke folder karantina
    _pastikan_karantina()
    if not os.path.isfile(jalur_asli):
        return None
    nama = os.path.basename(jalur_asli)
    tujuan = os.path.join(FOLDER_KARANTINA, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nama}")
    try:
        shutil.move(jalur_asli, tujuan)
        return tujuan
    except OSError:
        try:
            shutil.copy2(jalur_asli, tujuan)
            os.remove(jalur_asli)
            return tujuan
        except OSError:
            return None


def pulihkan_file(jalur_karantina, folder_tujuan=None):
    # Mengembalikan file dari karantina ke Downloads (atau folder_tujuan)
    if not jalur_karantina or not os.path.isfile(jalur_karantina):
        return None
    if not folder_tujuan:
        folder_tujuan = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(folder_tujuan, exist_ok=True)
    nama = os.path.basename(jalur_karantina)
    # Buang prefix timestamp jika ada
    if "_" in nama and nama[:8].isdigit():
        bagian = nama.split("_", 2)
        if len(bagian) >= 3:
            nama = bagian[2]
    tujuan = os.path.join(folder_tujuan, nama)
    try:
        shutil.move(jalur_karantina, tujuan)
        return tujuan
    except OSError:
        return None


def proses_unduhan_berbahaya(daftar_unduhan, firebase_url, id_perangkat="windows-pc"):
    """
    Untuk setiap unduhan .apk/.exe/...:
    - jika belum ada izin / pending -> karantina + kirim permintaan
    - jika ditolak -> pastikan tetap di karantina / hapus
    - jika disetujui -> pulihkan jika masih di karantina
    Mengembalikan daftar event untuk log GUI.
    """
    _pastikan_karantina()
    izin = ambil_izin_instal(firebase_url)
    # Index izin berdasarkan hash atau nama_file
    index = {}
    for id_req, info in (izin or {}).items():
        if not isinstance(info, dict):
            continue
        kunci = info.get("hash_file") or info.get("nama_file")
        if kunci:
            index[kunci] = {**info, "id": id_req}

    event = []
    for unduh in daftar_unduhan:
        if not unduh.get("perlu_izin"):
            continue
        jalur = unduh.get("jalur") or ""
        nama = unduh.get("nama_file") or os.path.basename(jalur)
        h = hash_file(jalur) if jalur and os.path.isfile(jalur) else None
        kunci = h or nama
        existing = index.get(kunci) or index.get(nama)

        if existing:
            status = (existing.get("status") or "pending").lower()
            id_req = existing.get("id")
            if status == "disetujui":
                # Pulihkan dari karantina jika ada
                k = existing.get("jalur_karantina")
                if k and os.path.isfile(k):
                    pulih = pulihkan_file(k)
                    if pulih:
                        update_status_izin(firebase_url, id_req, {
                            "status": "selesai",
                            "jalur_pulih": pulih,
                            "waktu_selesai": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                        event.append(f"Izin disetujui, file dipulihkan: {nama}")
                continue
            if status == "ditolak":
                if jalur and os.path.isfile(jalur):
                    karantina_file(jalur)
                event.append(f"Instal ditolak admin: {nama}")
                continue
            # pending: jika file masih di Downloads, karantina
            if jalur and os.path.isfile(jalur) and FOLDER_KARANTINA not in jalur:
                tujuan = karantina_file(jalur)
                if tujuan:
                    update_status_izin(firebase_url, id_req, {"jalur_karantina": tujuan})
                    event.append(f"Menunggu izin, dikarantina: {nama}")
            continue

        # Belum ada permintaan -> buat baru
        tujuan = None
        if jalur and os.path.isfile(jalur):
            tujuan = karantina_file(jalur)
        data = {
            "nama_file": nama,
            "hash_file": h,
            "url_sumber": unduh.get("url_sumber") or "",
            "ekstensi": unduh.get("ekstensi") or "",
            "perangkat": id_perangkat,
            "platform": "windows",
            "status": "pending",
            "jalur_asli": jalur,
            "jalur_karantina": tujuan,
            "waktu_ajuan": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pesan_santri": f"Santri ingin memasang/mengunduh: {nama}",
        }
        ok, id_req = kirim_permintaan_izin(firebase_url, data)
        if ok:
            event.append(f"Permintaan izin dikirim: {nama} ({id_req})")
        else:
            event.append(f"Gagal kirim izin: {nama}")
    return event
