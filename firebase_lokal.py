# ============================================================
# Firebase Lokal — NME Guardian (Realtime Database simulasi)
# ============================================================
# URL: http://127.0.0.1:8765
# Mendukung path bersarang seperti Firebase asli, contoh:
#   /status_blokir.json
#   /aktivitas_online/windows.json
#   /izin_instal/<id>.json
#   /link_diblokir.json
# ============================================================

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from datetime import datetime

PORT = 8765

# Data awal mirip struktur Firebase cloud
DATA_STORE = {
    "status_blokir": False,
    "aplikasi_dibuka": None,
    # Riwayat aktivitas detail (web, unduhan, instalasi, aplikasi)
    "aktivitas_online": {
        "windows": None,
        "android": None,
    },
    # Daftar domain/URL yang diblokir (bisa diisi dari panel admin)
    "link_diblokir": {
        "tiktok.com": {"alasan": "Hiburan berlebih", "aktif": True},
        "instagram.com": {"alasan": "Media sosial", "aktif": True},
        "youtube.com": {"alasan": "Video (uji)", "aktif": False},
    },
    # Antrian izin instal APK / installer (pending | disetujui | ditolak)
    "izin_instal": {},
    # Perangkat yang terhubung
    "perangkat": {},
}


def _navigasi(path_parts, buat=False):
    """Menavigasi dict bersarang. Jika buat=True, buat key yang belum ada."""
    if not path_parts:
        return DATA_STORE, None
    sekarang = DATA_STORE
    for bagian in path_parts[:-1]:
        if bagian not in sekarang or not isinstance(sekarang.get(bagian), dict):
            if buat:
                sekarang[bagian] = {}
            else:
                return None, path_parts[-1]
        sekarang = sekarang[bagian]
    return sekarang, path_parts[-1]


def _baca_path(path_parts):
    if not path_parts:
        return DATA_STORE
    induk, kunci = _navigasi(path_parts, buat=False)
    if induk is None:
        return None
    return induk.get(kunci)


def _tulis_path(path_parts, data):
    if not path_parts:
        # Menimpa seluruh store tidak diizinkan lewat API biasa
        return False
    induk, kunci = _navigasi(path_parts, buat=True)
    induk[kunci] = data
    return True


def _patch_path(path_parts, data):
    if not path_parts:
        if isinstance(data, dict):
            DATA_STORE.update(data)
            return DATA_STORE
        return None
    induk, kunci = _navigasi(path_parts, buat=True)
    lama = induk.get(kunci)
    if isinstance(lama, dict) and isinstance(data, dict):
        lama.update(data)
        induk[kunci] = lama
        return lama
    induk[kunci] = data
    return data


def _hapus_path(path_parts):
    if not path_parts:
        return False
    induk, kunci = _navigasi(path_parts, buat=False)
    if induk is None or kunci not in induk:
        return False
    del induk[kunci]
    return True


class HandlerFirebaseLokal(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[Firebase Lokal] {args[0]}")

    def _baca_json(self):
        panjang = int(self.headers.get("Content-Length", 0))
        mentah = self.rfile.read(panjang) if panjang else b""
        if not mentah:
            return None
        return json.loads(mentah.decode("utf-8"))

    def _kirim_json(self, kode, data):
        isi = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(kode)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(isi)))
        self.end_headers()
        self.wfile.write(isi)

    def do_OPTIONS(self):
        self._kirim_json(200, {"ok": True})

    def _path_parts(self):
        path = self.path.split("?")[0]
        if path.endswith(".json"):
            path = path[:-5]
        path = path.strip("/")
        if not path:
            return []
        return [p for p in path.split("/") if p]

    def do_GET(self):
        parts = self._path_parts()
        data = _baca_path(parts)
        self._kirim_json(200, data)

    def do_PUT(self):
        parts = self._path_parts()
        data = self._baca_json()
        _tulis_path(parts, data)
        self._kirim_json(200, data)

    def do_PATCH(self):
        parts = self._path_parts()
        data = self._baca_json()
        hasil = _patch_path(parts, data)
        self._kirim_json(200, hasil)

    def do_DELETE(self):
        parts = self._path_parts()
        ok = _hapus_path(parts)
        self._kirim_json(200 if ok else 404, {"ok": ok})


def utama():
    # 0.0.0.0 agar HP Android di WiFi yang sama bisa mengakses
    server = HTTPServer(("0.0.0.0", PORT), HandlerFirebaseLokal)
    print("=" * 60)
    print(" Firebase Lokal — NME Guardian (detail online)")
    print(f" URL lokal PC: http://127.0.0.1:{PORT}")
    print(f" URL LAN/Android: http://IP_PC_ANDA:{PORT}")
    print(f" Siap sejak: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(" Node: status_blokir, aktivitas_online, link_diblokir, izin_instal")
    print(" Panel admin: http://localhost/Nailul%20Muna%20Cyber%20Guard/admin/")
    print(" Tekan Ctrl+C untuk menghentikan")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFirebase Lokal dihentikan.")
        server.server_close()


if __name__ == "__main__":
    utama()
