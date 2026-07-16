# ============================================================
# modul/blokir_link.py
# Mengambil daftar link terlarang dari Firebase & menerapkan
# blokir domain lewat file hosts Windows (butuh Admin).
# ============================================================

import os
import re
import requests

# Marker agar mudah menambah/menghapus blok NME tanpa merusak hosts lain
MARKER_MULAI = "# === NME_GUARDIAN_BLOKIR_MULAI ==="
MARKER_AKHIR = "# === NME_GUARDIAN_BLOKIR_AKHIR ==="
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


def ambil_link_diblokir(firebase_url, timeout=10):
    # Membaca node link_diblokir dari Firebase
    try:
        r = requests.get(f"{firebase_url}/link_diblokir.json", timeout=timeout)
        if r.status_code != 200:
            return {}
        data = r.json() or {}
        if not isinstance(data, dict):
            return {}
        # Hanya yang aktif=true
        aktif = {}
        for domain, info in data.items():
            if isinstance(info, dict) and info.get("aktif", True):
                aktif[domain.lower().strip()] = info
            elif info is True:
                aktif[domain.lower().strip()] = {"aktif": True}
        return aktif
    except requests.exceptions.RequestException:
        return {}


def url_terblokir(url, daftar_blokir):
    # Mengecek apakah URL/domain ada di daftar blokir
    if not url or not daftar_blokir:
        return False
    teks = url.lower()
    for domain in daftar_blokir:
        if domain and domain in teks:
            return True
    return False


def filter_riwayat_terblokir(riwayat_url, daftar_blokir):
    # Mengembalikan item riwayat yang kena blokir
    kena = []
    for item in riwayat_url:
        target = item.get("domain") or item.get("url") or ""
        if url_terblokir(target, daftar_blokir):
            kena.append(item)
    return kena


def terapkan_hosts(daftar_blokir):
    # Menulis domain terlarang ke file hosts -> 127.0.0.1
    # Mengembalikan (sukses: bool, pesan: str)
    if os.name != "nt":
        return False, "Hanya untuk Windows"
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
            isi = f.read()
    except PermissionError:
        return False, "Gagal baca hosts (jalankan sebagai Administrator)"
    except OSError as e:
        return False, f"Gagal baca hosts: {e}"

    # Hapus blok lama NME Guardian
    pola = re.compile(
        re.escape(MARKER_MULAI) + r".*?" + re.escape(MARKER_AKHIR),
        re.DOTALL,
    )
    isi_bersih = re.sub(pola, "", isi).rstrip() + "\n\n"

    baris = [MARKER_MULAI, "# Dikelola otomatis oleh NME Guardian"]
    for domain in sorted(daftar_blokir.keys()):
        domain = domain.strip().lower()
        if not domain:
            continue
        baris.append(f"127.0.0.1 {domain}")
        baris.append(f"127.0.0.1 www.{domain}")
    baris.append(MARKER_AKHIR)
    baris.append("")

    isi_baru = isi_bersih + "\n".join(baris)
    try:
        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.write(isi_baru)
        return True, f"Hosts diperbarui ({len(daftar_blokir)} domain)"
    except PermissionError:
        return False, "Gagal tulis hosts (jalankan sebagai Administrator)"
    except OSError as e:
        return False, f"Gagal tulis hosts: {e}"
