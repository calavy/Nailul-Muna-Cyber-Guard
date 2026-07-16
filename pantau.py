# ============================================================
# NME Guardian - Aplikasi Parental Control untuk Santri
# Pesantren API Nailul Muna
# ============================================================
# File ini memantau aplikasi yang dibuka di Windows,
# mengirim datanya ke Firebase, lalu memblokir aplikasi
# terlarang jika status_blokir di Firebase bernilai true.
# Dilengkapi tampilan grafis (GUI) yang menarik.
# ============================================================

# Mengimpor library psutil untuk membaca daftar proses Windows
import psutil

# Mengimpor library requests untuk mengirim/ambil data dari internet (Firebase)
import requests

# Mengimpor library time agar program bisa menunggu (delay) antar siklus pantau
import time

# Mengimpor library datetime agar kita bisa mencatat waktu aplikasi dibuka
from datetime import datetime

# Mengimpor threading agar pemantauan berjalan di belakang tanpa membekukan tampilan
import threading

# Mengimpor tkinter untuk membuat jendela aplikasi (GUI)
import tkinter as tk

# Mengimpor widget tambahan dari tkinter (tombol, label, bingkai, dll.)
from tkinter import ttk

# Mengimpor socket untuk membuat ID perangkat unik dari nama komputer
import socket

# Modul pantau detail: website, unduhan, blokir link, izin instal
from modul.browser_aktivitas import ambil_riwayat_website, ambil_riwayat_unduhan
from modul.blokir_link import ambil_link_diblokir, filter_riwayat_terblokir, terapkan_hosts
from modul.izin_instal import proses_unduhan_berbahaya

# Membaca URL Firebase dari config.json (cloud atau lokal)
from modul.config_firebase import baca_firebase_url

# ------------------------------------------------------------
# PENGATURAN UTAMA — URL diambil dari config.json
# Salin config.contoh.json → config.json, lalu isi URL cloud Anda
# ------------------------------------------------------------

# Alamat dasar Firebase Realtime Database (tanpa / di akhir)
FIREBASE_URL = baca_firebase_url()

# ID unik perangkat Windows ini (muncul di panel admin)
ID_PERANGKAT = "windows-" + socket.gethostname().replace(" ", "-").lower()

# URL lengkap untuk mengirim data aplikasi yang sedang dibuka
# .json di akhir wajib ada agar Firebase menerima data format JSON
URL_APLIKASI_DIBUKA = FIREBASE_URL + "/aplikasi_dibuka.json"

# URL lengkap untuk membaca status blokir (true atau false)
URL_STATUS_BLOKIR = FIREBASE_URL + "/status_blokir.json"

# URL untuk mengirim ringkasan aktivitas online detail
URL_AKTIVITAS_WINDOWS = FIREBASE_URL + "/aktivitas_online/windows.json"

# Daftar nama proses aplikasi yang dilarang untuk santri
# Nama harus sama dengan nama proses di Task Manager Windows
APLIKASI_TERLARANG = [
    "chrome.exe",   # Google Chrome
    "msedge.exe",   # Microsoft Edge
    "vlc.exe",      # VLC Media Player
]

# Jeda waktu (dalam detik) sebelum memantau lagi
# Semakin kecil angkanya, semakin cepat deteksi, tapi lebih berat untuk komputer
INTERVAL_PANTAU = 5

# Batas waktu tunggu request ke Firebase (detik)
# Jika Firebase lambat/tidak merespons, program tidak akan menunggu terlalu lama
TIMEOUT_REQUEST = 10

# ------------------------------------------------------------
# PALET WARNA TAMPILAN
# Nuansa hijau zamrud + krem lembut (kesan aman & pesantren)
# ------------------------------------------------------------

# Warna latar utama jendela
WARNA_LATAR = "#EEF4F1"

# Warna hijau tua untuk identitas merek
WARNA_MERK = "#0B5C4C"

# Warna hijau sedang untuk aksen tombol dan status aktif
WARNA_AKSEN = "#1F8A70"

# Warna hijau muda untuk highlight lembut
WARNA_HIGHLIGHT = "#C8E6D8"

# Warna teks utama
WARNA_TEKS = "#1A2E28"

# Warna teks sekunder (lebih redup)
WARNA_TEKS_REDUP = "#5A7268"

# Warna peringatan (saat blokir aktif / ada ancaman)
WARNA_WASPADA = "#C45C26"

# Warna sukses / aman
WARNA_AMAN = "#2E7D5B"

# Warna kartu / panel isi
WARNA_KARTU = "#F7FBF9"

# Warna garis tipis
WARNA_GARIS = "#D0E3DA"


# ------------------------------------------------------------
# FUNGSI: ambil_aplikasi_yang_berjalan
# Tujuan: membaca semua proses yang sedang aktif di Windows
# ------------------------------------------------------------
def ambil_aplikasi_yang_berjalan():
    # Membuat daftar kosong untuk menampung nama aplikasi
    daftar_aplikasi = []

    # Melakukan perulangan ke setiap proses yang sedang berjalan di komputer
    # attrs membatasi data yang diambil supaya lebih ringan (hanya pid dan name)
    for proses in psutil.process_iter(["pid", "name"]):
        try:
            # Mengambil nama proses, contoh: chrome.exe
            nama_proses = proses.info["name"]

            # Mengambil nomor PID (Process ID) proses tersebut
            pid_proses = proses.info["pid"]

            # Melewati proses yang namanya kosong/tidak ada
            if not nama_proses:
                # continue artinya lanjut ke proses berikutnya
                continue

            # Menyimpan data proses ke dalam bentuk dictionary (kamus data)
            data_proses = {
                "nama": nama_proses,          # Nama file aplikasi
                "pid": pid_proses,            # Nomor identitas proses
                "waktu_terdeteksi": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Waktu deteksi
            }

            # Menambahkan data proses ke daftar aplikasi
            daftar_aplikasi.append(data_proses)

        # Jika proses sudah tertutup sebelum sempat dibaca, lewati saja
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Tidak melakukan apa-apa, lanjut ke proses berikutnya
            continue

    # Mengembalikan daftar aplikasi yang berhasil dikumpulkan
    return daftar_aplikasi


# ------------------------------------------------------------
# FUNGSI: kirim_ke_firebase
# Tujuan: mengirim daftar aplikasi yang sedang dibuka ke Firebase
# Mengembalikan True jika sukses, False jika gagal
# ------------------------------------------------------------
def kirim_ke_firebase(daftar_aplikasi):
    try:
        # Menyiapkan data yang akan dikirim ke Firebase
        data_kirim = {
            "jumlah_aplikasi": len(daftar_aplikasi),  # Jumlah total aplikasi terdeteksi
            "daftar": daftar_aplikasi,                # Isi daftar aplikasi
            "terakhir_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Waktu update terakhir
        }

        # Mengirim data ke Firebase dengan metode PUT
        # PUT akan menimpa isi /aplikasi_dibuka dengan data terbaru
        respons = requests.put(
            URL_APLIKASI_DIBUKA,   # Alamat tujuan Firebase
            json=data_kirim,      # Data dikirim dalam format JSON
            timeout=TIMEOUT_REQUEST,  # Batas waktu menunggu respons
        )

        # Mengembalikan True hanya jika kode respons 200 (sukses)
        return respons.status_code == 200

    # Jika tidak ada internet atau Firebase tidak bisa dihubungi
    except requests.exceptions.RequestException:
        # Mengembalikan False agar tampilan bisa menampilkan status gagal
        return False


# ------------------------------------------------------------
# FUNGSI: ambil_status_blokir
# Tujuan: membaca nilai status_blokir dari Firebase (true/false)
# Mengembalikan tuple: (status_blokir, berhasil_terhubung)
# ------------------------------------------------------------
def ambil_status_blokir():
    try:
        # Mengambil data dari Firebase dengan metode GET (membaca data)
        respons = requests.get(
            URL_STATUS_BLOKIR,     # Alamat status_blokir di Firebase
            timeout=TIMEOUT_REQUEST,  # Batas waktu menunggu respons
        )

        # Jika pembacaan gagal, anggap status blokir masih false
        if respons.status_code != 200:
            # return (False, False) = blokir nonaktif + koneksi gagal
            return False, False

        # Mengubah isi respons Firebase menjadi data Python (true/false/null)
        status = respons.json()

        # Firebase bisa mengembalikan true, false, atau null
        if status is True:
            # Status blokir aktif, koneksi berhasil
            return True, True

        # Jika nilainya string "true" (kadang terjadi jika diisi manual), anggap True juga
        if isinstance(status, str) and status.lower() == "true":
            # Status blokir aktif dalam bentuk teks
            return True, True

        # Status blokir nonaktif, tetapi koneksi tetap berhasil
        return False, True

    # Jika terjadi error jaringan saat membaca Firebase
    except requests.exceptions.RequestException:
        # return (False, False) agar program tidak sembarangan memblokir saat offline
        return False, False


# ------------------------------------------------------------
# FUNGSI: kirim_aktivitas_detail
# Tujuan: mengirim riwayat web, unduhan, dan event izin ke Firebase
# ------------------------------------------------------------
def kirim_aktivitas_detail(payload):
    try:
        respons = requests.put(
            URL_AKTIVITAS_WINDOWS,
            json=payload,
            timeout=TIMEOUT_REQUEST,
        )
        return respons.status_code == 200
    except requests.exceptions.RequestException:
        return False


# ------------------------------------------------------------
# FUNGSI: tutup_aplikasi_terlarang
# Tujuan: menutup paksa (kill) aplikasi terlarang yang sedang dibuka
# Mengembalikan daftar nama aplikasi yang berhasil ditutup
# ------------------------------------------------------------
def tutup_aplikasi_terlarang():
    # Membuat daftar untuk menyimpan aplikasi yang berhasil ditutup
    yang_ditutup = []

    # Melakukan perulangan ke setiap proses yang sedang berjalan
    for proses in psutil.process_iter(["pid", "name"]):
        try:
            # Mengambil nama proses dalam huruf kecil agar perbandingan tidak case-sensitive
            nama_proses = (proses.info["name"] or "").lower()

            # Mengecek apakah nama proses ada di daftar aplikasi terlarang
            if nama_proses in APLIKASI_TERLARANG:
                # Menutup paksa proses tersebut (kill)
                proses.kill()

                # Menyimpan nama + PID agar bisa ditampilkan di log
                yang_ditutup.append(f"{nama_proses} (PID {proses.info['pid']})")

        # Jika proses sudah hilang atau tidak boleh diakses, lewati saja
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Lanjut ke proses berikutnya tanpa menghentikan program
            continue

    # Mengembalikan daftar aplikasi yang ditutup
    return yang_ditutup


# ------------------------------------------------------------
# KELAS: AplikasiNMEGuardian
# Tujuan: membangun jendela GUI yang menarik untuk NME Guardian
# ------------------------------------------------------------
class AplikasiNMEGuardian:
    # Fungsi khusus yang dipanggil otomatis saat objek dibuat
    def __init__(self, jendela):
        # Menyimpan objek jendela utama agar bisa dipakai di seluruh kelas
        self.jendela = jendela

        # Mengatur judul jendela di bilah judul Windows
        self.jendela.title("NME Guardian — Pesantren API Nailul Muna")

        # Mengatur ukuran awal jendela (lebar x tinggi)
        self.jendela.geometry("920x640")

        # Mengatur ukuran minimum supaya tampilan tidak rusak saat diperkecil
        self.jendela.minsize(820, 560)

        # Mengatur warna latar belakang jendela
        self.jendela.configure(bg=WARNA_LATAR)

        # Menandai apakah pemantauan sedang berjalan
        self.sedang_memantau = False

        # Menyimpan objek thread pemantauan (awal: belum ada)
        self.thread_pantau = None

        # Nilai opacity untuk animasi denyut indikator (0.0 sampai 1.0)
        self.nilai_denyut = 0.0

        # Arah animasi denyut: 1 = bertambah terang, -1 = meredup
        self.arah_denyut = 1

        # Posisi garis "scan" di header untuk animasi geser
        self.posisi_scan = 0

        # Opacity teks hero saat animasi muncul pertama kali
        self.opacity_hero = 0

        # Memanggil fungsi untuk merakit seluruh tampilan
        self.bangun_tampilan()

        # Memulai animasi denyut status
        self.animasi_denyut()

        # Memulai animasi garis scan di header
        self.animasi_scan()

        # Memulai animasi munculnya teks merek (fade-in sederhana)
        self.animasi_muncul_hero()

    # ------------------------------------------------------------
    # FUNGSI: bangun_tampilan
    # Tujuan: menyusun semua elemen visual di jendela
    # ------------------------------------------------------------
    def bangun_tampilan(self):
        # Membuat kanvas header penuh lebar sebagai bidang visual utama
        self.kanvas_header = tk.Canvas(
            self.jendela,          # Induknya adalah jendela utama
            height=168,            # Tinggi area merek
            bg=WARNA_MERK,         # Warna dasar hijau merek
            highlightthickness=0,  # Menghilangkan garis tepi bawaan
            bd=0,                  # Menghilangkan border
        )
        # Meletakkan kanvas header di bagian atas, meregang penuh ke samping
        self.kanvas_header.pack(fill="x", side="top")

        # Menggambar gradasi sederhana dengan beberapa persegi panjang bertumpuk
        # (tkinter tidak punya gradient asli, jadi kita buat manual)
        for i in range(0, 168, 4):
            # Menghitung seberapa gelap warna seiring turun ke bawah
            faktor = i / 168
            # Menggabungkan warna hijau merek dengan sedikit lebih gelap
            r = int(11 + (8 * faktor))
            g = int(92 - (20 * faktor))
            b = int(76 - (10 * faktor))
            # Mengubah angka RGB menjadi kode warna hex (#RRGGBB)
            warna = f"#{r:02x}{g:02x}{b:02x}"
            # Menggambar strip horizontal untuk efek gradasi
            self.kanvas_header.create_rectangle(
                0, i, 2000, i + 4,   # Koordinat strip
                fill=warna,          # Warna strip
                outline="",          # Tanpa garis tepi
            )

        # Menggambar lingkaran dekoratif besar di kanan (suasana visual)
        self.kanvas_header.create_oval(
            720, -40, 980, 220,      # Posisi lingkaran
            fill="#0E6B58",          # Warna sedikit lebih terang
            outline="",              # Tanpa garis tepi
        )

        # Menggambar lingkaran dekoratif kedua yang lebih kecil
        self.kanvas_header.create_oval(
            780, 20, 940, 180,       # Posisi lingkaran kecil
            fill="#148F74",          # Warna aksen
            outline="",              # Tanpa garis tepi
        )

        # Garis scan animasi (akan digeser di fungsi animasi_scan)
        self.garis_scan = self.kanvas_header.create_rectangle(
            0, 0, 40, 168,           # Lebar tipis di kiri
            fill="#2BB89A",          # Warna hijau terang
            outline="",              # Tanpa garis tepi
            stipple="gray50",        # Efek transparan sederhana
        )

        # Teks merek besar: NME Guardian (sinyal merek utama)
        self.teks_merek = self.kanvas_header.create_text(
            40, 58,                  # Posisi kiri-atas area header
            text="NME Guardian",     # Nama aplikasi sebagai hero
            anchor="w",              # Rata kiri
            fill="#E8F7F1",          # Warna teks hampir putih hijau
            font=("Bahnschrift", 32, "bold"),  # Font ekspresif di Windows
        )

        # Teks pendukung di bawah merek
        self.teks_tagline = self.kanvas_header.create_text(
            40, 100,                 # Sedikit di bawah merek
            text="Perlindungan digital untuk santri Pesantren API Nailul Muna",
            anchor="w",              # Rata kiri
            fill="#B7E0D2",          # Warna lembut
            font=("Candara", 13),    # Font pendukung yang nyaman dibaca
        )

        # Teks status pantau di pojok kanan header
        self.teks_status_header = self.kanvas_header.create_text(
            880, 140,                # Posisi kanan bawah header
            text="SIAGA",            # Status awal
            anchor="e",              # Rata kanan
            fill="#9FD9C8",          # Warna lembut
            font=("Bahnschrift", 11),
        )

        # Bingkai isi utama di bawah header
        self.bingkai_isi = tk.Frame(self.jendela, bg=WARNA_LATAR)
        # Meletakkan bingkai isi agar mengisi sisa ruang jendela
        self.bingkai_isi.pack(fill="both", expand=True, padx=28, pady=22)

        # Baris atas: tombol kontrol + indikator status
        self.baris_kontrol = tk.Frame(self.bingkai_isi, bg=WARNA_LATAR)
        # Meletakkan baris kontrol di bagian atas area isi
        self.baris_kontrol.pack(fill="x")

        # Tombol mulai / hentikan pemantauan
        self.tombol_pantau = tk.Button(
            self.baris_kontrol,                      # Induk: baris kontrol
            text="Mulai Pantau",                     # Teks tombol awal
            command=self.toggle_pantau,              # Fungsi yang dipanggil saat diklik
            bg=WARNA_AKSEN,                          # Warna latar tombol
            fg="white",                              # Warna teks putih
            activebackground=WARNA_MERK,             # Warna saat tombol ditekan
            activeforeground="white",                # Warna teks saat ditekan
            font=("Bahnschrift", 12, "bold"),        # Font tombol
            relief="flat",                           # Tanpa efek 3D kuno
            cursor="hand2",                          # Kursor tangan saat diarahkan
            padx=22,                                 # Padding kiri-kanan
            pady=10,                                 # Padding atas-bawah
            bd=0,                                    # Tanpa border tebal
        )
        # Meletakkan tombol di kiri baris kontrol
        self.tombol_pantau.pack(side="left")

        # Label kecil di samping tombol
        self.label_petunjuk = tk.Label(
            self.baris_kontrol,
            text="  Tekan untuk mulai mengawasi aplikasi santri secara online",
            bg=WARNA_LATAR,
            fg=WARNA_TEKS_REDUP,
            font=("Candara", 11),
        )
        # Meletakkan petunjuk di samping tombol
        self.label_petunjuk.pack(side="left", padx=(12, 0))

        # Bingkai tiga kartu status (proses, firebase, blokir)
        self.baris_status = tk.Frame(self.bingkai_isi, bg=WARNA_LATAR)
        # Memberi jarak dari baris kontrol
        self.baris_status.pack(fill="x", pady=(22, 0))

        # Membuat kartu status: jumlah proses
        self.kartu_proses, self.nilai_proses = self.buat_kartu_status(
            self.baris_status, "Proses Aktif", "0", 0
        )

        # Membuat kartu status: koneksi Firebase
        self.kartu_firebase, self.nilai_firebase = self.buat_kartu_status(
            self.baris_status, "Firebase", "Belum terhubung", 1
        )

        # Membuat kartu status: mode blokir
        self.kartu_blokir, self.nilai_blokir = self.buat_kartu_status(
            self.baris_status, "Mode Blokir", "Nonaktif", 2
        )

        # Bingkai dua kolom: daftar terlarang + log aktivitas
        self.baris_konten = tk.Frame(self.bingkai_isi, bg=WARNA_LATAR)
        # Meletakkan baris konten agar mengisi sisa tinggi jendela
        self.baris_konten.pack(fill="both", expand=True, pady=(22, 0))

        # Panel kiri: daftar aplikasi terlarang
        self.panel_kiri = tk.Frame(
            self.baris_konten,
            bg=WARNA_KARTU,
            highlightbackground=WARNA_GARIS,
            highlightthickness=1,
        )
        # Meletakkan panel kiri dengan lebar tetap
        self.panel_kiri.pack(side="left", fill="both", padx=(0, 12))

        # Judul panel kiri
        tk.Label(
            self.panel_kiri,
            text="Aplikasi Terlarang",
            bg=WARNA_KARTU,
            fg=WARNA_MERK,
            font=("Bahnschrift", 14, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 4))

        # Subjudul panel kiri
        tk.Label(
            self.panel_kiri,
            text="Akan ditutup otomatis jika mode blokir aktif",
            bg=WARNA_KARTU,
            fg=WARNA_TEKS_REDUP,
            font=("Candara", 10),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 10))

        # Daftar aplikasi terlarang ditampilkan satu per satu
        for nama_app in APLIKASI_TERLARANG:
            # Baris item aplikasi
            baris_app = tk.Frame(self.panel_kiri, bg=WARNA_HIGHLIGHT)
            # Meletakkan baris dengan padding
            baris_app.pack(fill="x", padx=18, pady=4)

            # Titik indikator di kiri nama aplikasi
            tk.Label(
                baris_app,
                text="●",
                bg=WARNA_HIGHLIGHT,
                fg=WARNA_WASPADA,
                font=("Bahnschrift", 10),
            ).pack(side="left", padx=(10, 6), pady=8)

            # Nama file aplikasi terlarang
            tk.Label(
                baris_app,
                text=nama_app,
                bg=WARNA_HIGHLIGHT,
                fg=WARNA_TEKS,
                font=("Consolas", 11),
            ).pack(side="left", pady=8)

        # Label ruang kosong agar panel kiri punya tinggi yang nyaman
        tk.Label(self.panel_kiri, text="", bg=WARNA_KARTU).pack(expand=True)

        # Footer kecil di panel kiri
        tk.Label(
            self.panel_kiri,
            text="Pesantren API Nailul Muna",
            bg=WARNA_KARTU,
            fg=WARNA_TEKS_REDUP,
            font=("Candara", 9),
        ).pack(pady=(0, 14))

        # Panel kanan: log aktivitas
        self.panel_kanan = tk.Frame(
            self.baris_konten,
            bg=WARNA_KARTU,
            highlightbackground=WARNA_GARIS,
            highlightthickness=1,
        )
        # Meletakkan panel kanan agar mengisi sisa lebar
        self.panel_kanan.pack(side="left", fill="both", expand=True)

        # Judul panel log
        tk.Label(
            self.panel_kanan,
            text="Catatan Aktivitas",
            bg=WARNA_KARTU,
            fg=WARNA_MERK,
            font=("Bahnschrift", 14, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 4))

        # Subjudul panel log
        tk.Label(
            self.panel_kanan,
            text="Riwayat pantau, kirim data, dan aksi blokir",
            bg=WARNA_KARTU,
            fg=WARNA_TEKS_REDUP,
            font=("Candara", 10),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 8))

        # Bingkai untuk kotak teks log + scrollbar
        self.bingkai_log = tk.Frame(self.panel_kanan, bg=WARNA_KARTU)
        # Meletakkan bingkai log agar mengisi sisa panel kanan
        self.bingkai_log.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        # Scrollbar vertikal untuk menggulir log
        self.scroll_log = ttk.Scrollbar(self.bingkai_log)
        # Meletakkan scrollbar di sisi kanan
        self.scroll_log.pack(side="right", fill="y")

        # Kotak teks untuk menampilkan log (hanya baca)
        self.kotak_log = tk.Text(
            self.bingkai_log,
            bg="#F2F8F5",                # Latar log sedikit berbeda
            fg=WARNA_TEKS,               # Warna teks utama
            font=("Consolas", 10),       # Font mono agar rapi seperti log
            relief="flat",               # Tanpa bingkai 3D
            height=12,                   # Tinggi awal
            wrap="word",                 # Potong baris per kata
            yscrollcommand=self.scroll_log.set,  # Hubungkan ke scrollbar
            padx=12,                     # Padding dalam kiri-kanan
            pady=10,                     # Padding dalam atas-bawah
            state="disabled",            # Nonaktifkan ketikan pengguna
        )
        # Meletakkan kotak log agar mengisi ruang
        self.kotak_log.pack(side="left", fill="both", expand=True)

        # Menghubungkan scrollbar agar menggulir kotak log
        self.scroll_log.config(command=self.kotak_log.yview)

        # Menyiapkan warna tag untuk jenis pesan log yang berbeda
        self.kotak_log.tag_config("ok", foreground=WARNA_AMAN)
        self.kotak_log.tag_config("error", foreground="#B33A3A")
        self.kotak_log.tag_config("blokir", foreground=WARNA_WASPADA)
        self.kotak_log.tag_config("info", foreground=WARNA_TEKS_REDUP)

        # Menulis pesan selamat datang di log
        self.tambah_log("NME Guardian siap — pantau web, unduhan, & izin instal.", "ok")
        self.tambah_log(f"ID perangkat: {ID_PERANGKAT}", "info")
        self.tambah_log("Panel admin: http://localhost/Nailul%20Muna%20Cyber%20Guard/admin/", "info")

    # ------------------------------------------------------------
    # FUNGSI: buat_kartu_status
    # Tujuan: membuat satu kartu status kecil di baris atas
    # ------------------------------------------------------------
    def buat_kartu_status(self, induk, judul, nilai_awal, urutan):
        # Membuat bingkai kartu dengan latar putih kehijauan
        kartu = tk.Frame(
            induk,
            bg=WARNA_KARTU,
            highlightbackground=WARNA_GARIS,
            highlightthickness=1,
        )
        # Meletakkan kartu secara merata (3 kolom)
        kartu.pack(side="left", fill="both", expand=True, padx=(0 if urutan == 0 else 8, 0))

        # Label judul kartu (teks kecil di atas)
        tk.Label(
            kartu,
            text=judul,
            bg=WARNA_KARTU,
            fg=WARNA_TEKS_REDUP,
            font=("Candara", 10),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 0))

        # Label nilai utama kartu (angka/teks besar)
        label_nilai = tk.Label(
            kartu,
            text=nilai_awal,
            bg=WARNA_KARTU,
            fg=WARNA_MERK,
            font=("Bahnschrift", 18, "bold"),
            anchor="w",
        )
        # Meletakkan nilai dengan padding bawah
        label_nilai.pack(fill="x", padx=16, pady=(2, 14))

        # Mengembalikan bingkai kartu dan label nilai supaya bisa diubah nanti
        return kartu, label_nilai

    # ------------------------------------------------------------
    # FUNGSI: tambah_log
    # Tujuan: menambahkan satu baris pesan ke catatan aktivitas
    # ------------------------------------------------------------
    def tambah_log(self, pesan, jenis="info"):
        # Mengambil jam sekarang untuk ditampilkan di depan pesan
        jam = datetime.now().strftime("%H:%M:%S")

        # Menggabungkan jam + pesan menjadi satu baris log
        baris = f"[{jam}] {pesan}\n"

        # Mengaktifkan kotak log sementara agar bisa ditulis program
        self.kotak_log.config(state="normal")

        # Menyisipkan teks di akhir log dengan warna sesuai jenis
        self.kotak_log.insert("end", baris, jenis)

        # Menggulir otomatis ke baris paling bawah
        self.kotak_log.see("end")

        # Menonaktifkan lagi agar pengguna tidak bisa mengetik manual
        self.kotak_log.config(state="disabled")

    # ------------------------------------------------------------
    # FUNGSI: toggle_pantau
    # Tujuan: menyalakan atau menghentikan pemantauan saat tombol diklik
    # ------------------------------------------------------------
    def toggle_pantau(self):
        # Jika sedang memantau, maka hentikan
        if self.sedang_memantau:
            # Menandai bahwa pemantauan harus berhenti
            self.sedang_memantau = False

            # Mengubah teks tombol kembali ke "Mulai Pantau"
            self.tombol_pantau.config(text="Mulai Pantau", bg=WARNA_AKSEN)

            # Mengubah teks status di header
            self.kanvas_header.itemconfig(self.teks_status_header, text="SIAGA")

            # Menulis ke log bahwa pemantauan dihentikan
            self.tambah_log("Pemantauan dihentikan.", "info")
        else:
            # Menandai bahwa pemantauan mulai berjalan
            self.sedang_memantau = True

            # Mengubah teks tombol menjadi "Hentikan"
            self.tombol_pantau.config(text="Hentikan", bg=WARNA_WASPADA)

            # Mengubah teks status di header
            self.kanvas_header.itemconfig(self.teks_status_header, text="MEMANTAU")

            # Menulis ke log bahwa pemantauan dimulai
            self.tambah_log("Pemantauan dimulai.", "ok")

            # Membuat thread baru agar GUI tidak membeku saat request Firebase
            self.thread_pantau = threading.Thread(
                target=self.siklus_pantau,  # Fungsi yang dijalankan di thread
                daemon=True,                # Thread ikut mati saat aplikasi ditutup
            )

            # Menjalankan thread pemantauan
            self.thread_pantau.start()

    # ------------------------------------------------------------
    # FUNGSI: siklus_pantau
    # Tujuan: loop pemantauan yang berjalan di thread terpisah
    # ------------------------------------------------------------
    def siklus_pantau(self):
        # Loop terus berjalan selama tombol pantau masih aktif
        while self.sedang_memantau:
            try:
                # Langkah 1: ambil daftar aplikasi yang sedang dibuka di Windows
                daftar_aplikasi = ambil_aplikasi_yang_berjalan()

                # Langkah 2: kirim daftar aplikasi tersebut ke Firebase
                kirim_sukses = kirim_ke_firebase(daftar_aplikasi)

                # Langkah 3: ambil status blokir dari Firebase
                status_blokir, firebase_ok = ambil_status_blokir()

                # Langkah 4: pantau website & unduhan (Chrome/Edge)
                riwayat_web = ambil_riwayat_website(batas=20)
                riwayat_unduh = ambil_riwayat_unduhan(batas=15)

                # Langkah 5: ambil daftar link terlarang & terapkan ke hosts
                daftar_blokir = ambil_link_diblokir(FIREBASE_URL, TIMEOUT_REQUEST)
                web_terblokir = filter_riwayat_terblokir(riwayat_web, daftar_blokir)
                hosts_ok, hosts_pesan = terapkan_hosts(daftar_blokir)

                # Langkah 6: unduhan APK/EXE wajib izin pengasuh
                event_izin = proses_unduhan_berbahaya(
                    riwayat_unduh, FIREBASE_URL, ID_PERANGKAT
                )

                # Langkah 7: kirim ringkasan aktivitas detail online
                payload_detail = {
                    "id_perangkat": ID_PERANGKAT,
                    "platform": "windows",
                    "terakhir_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "jumlah_proses": len(daftar_aplikasi),
                    "website_terakhir": riwayat_web[:10],
                    "unduhan_terakhir": riwayat_unduh[:10],
                    "website_kena_blokir": web_terblokir[:10],
                    "jumlah_link_diblokir": len(daftar_blokir),
                    "event_izin": event_izin,
                }
                detail_ok = kirim_aktivitas_detail(payload_detail)

                # Daftarkan perangkat ke node /perangkat
                try:
                    requests.put(
                        f"{FIREBASE_URL}/perangkat/{ID_PERANGKAT}.json",
                        json={
                            "nama": socket.gethostname(),
                            "platform": "windows",
                            "terakhir_online": payload_detail["terakhir_update"],
                        },
                        timeout=TIMEOUT_REQUEST,
                    )
                except requests.exceptions.RequestException:
                    pass

                # Menggabungkan status koneksi
                terhubung = kirim_sukses or firebase_ok or detail_ok

                # Langkah 8: jika status_blokir = true, tutup aplikasi terlarang
                yang_ditutup = []
                if status_blokir:
                    yang_ditutup = tutup_aplikasi_terlarang()

                hasil = {
                    "jumlah": len(daftar_aplikasi),
                    "terhubung": terhubung,
                    "status_blokir": status_blokir,
                    "yang_ditutup": yang_ditutup,
                    "kirim_sukses": kirim_sukses,
                    "jumlah_web": len(riwayat_web),
                    "jumlah_unduh": len(riwayat_unduh),
                    "jumlah_blokir_web": len(web_terblokir),
                    "hosts_pesan": hosts_pesan,
                    "hosts_ok": hosts_ok,
                    "event_izin": event_izin,
                    "web_contoh": [w.get("url", "")[:80] for w in riwayat_web[:3]],
                }

                self.jendela.after(0, lambda h=hasil: self.perbarui_tampilan(h))

                for _ in range(INTERVAL_PANTAU * 5):
                    if not self.sedang_memantau:
                        break
                    time.sleep(0.2)

            except Exception as kesalahan:
                pesan_error = str(kesalahan)
                self.jendela.after(
                    0,
                    lambda p=pesan_error: self.tambah_log(f"Kesalahan: {p}", "error"),
                )
                time.sleep(INTERVAL_PANTAU)

    # ------------------------------------------------------------
    # FUNGSI: perbarui_tampilan
    # Tujuan: mengubah angka/status di kartu dan menambah log
    # ------------------------------------------------------------
    def perbarui_tampilan(self, hasil):
        # Memperbarui angka proses aktif di kartu pertama
        self.nilai_proses.config(text=str(hasil["jumlah"]))

        # Memperbarui teks koneksi Firebase
        if hasil["terhubung"]:
            # Jika terhubung, tampilkan status Online berwarna hijau
            self.nilai_firebase.config(text="Online", fg=WARNA_AMAN)
        else:
            # Jika gagal, tampilkan Offline berwarna waspada
            self.nilai_firebase.config(text="Offline", fg=WARNA_WASPADA)

        # Memperbarui teks mode blokir
        if hasil["status_blokir"]:
            # Mode blokir aktif
            self.nilai_blokir.config(text="AKTIF", fg=WARNA_WASPADA)
        else:
            # Mode blokir nonaktif
            self.nilai_blokir.config(text="Nonaktif", fg=WARNA_MERK)

        # Menulis ringkasan siklus ke log
        if hasil["kirim_sukses"]:
            self.tambah_log(
                f"Online OK | proses:{hasil['jumlah']} web:{hasil.get('jumlah_web', 0)} unduh:{hasil.get('jumlah_unduh', 0)}",
                "ok",
            )
        else:
            self.tambah_log(
                f"Gagal kirim Firebase. Proses lokal: {hasil['jumlah']}.",
                "error",
            )

        # Log website terakhir (cuplikan)
        for url in hasil.get("web_contoh") or []:
            if url:
                self.tambah_log(f"Web: {url}", "info")

        # Log hasil blokir link / hosts
        if hasil.get("jumlah_blokir_web"):
            self.tambah_log(
                f"Ada {hasil['jumlah_blokir_web']} kunjungan ke link terlarang.",
                "blokir",
            )
        pesan_hosts = hasil.get("hosts_pesan") or ""
        if pesan_hosts:
            self.tambah_log(
                pesan_hosts,
                "ok" if hasil.get("hosts_ok") else "error",
            )

        # Log permintaan izin instal APK/EXE
        for ev in hasil.get("event_izin") or []:
            self.tambah_log(ev, "blokir")

        # Menulis status blokir aplikasi ke log
        if hasil["status_blokir"]:
            if hasil["yang_ditutup"]:
                for nama in hasil["yang_ditutup"]:
                    self.tambah_log(f"Ditutup paksa: {nama}", "blokir")
            else:
                self.tambah_log("Blokir aplikasi aktif. Tidak ada target.", "info")
        else:
            self.tambah_log("Mode blokir aplikasi nonaktif.", "info")

    # ------------------------------------------------------------
    # FUNGSI: animasi_denyut
    # Tujuan: membuat teks status di header "berdenyut" pelan
    # ------------------------------------------------------------
    def animasi_denyut(self):
        # Mengubah nilai denyut naik atau turun
        self.nilai_denyut += 0.04 * self.arah_denyut

        # Jika sudah terlalu terang, balik arah menjadi meredup
        if self.nilai_denyut >= 1:
            self.nilai_denyut = 1
            self.arah_denyut = -1

        # Jika sudah terlalu redup, balik arah menjadi bertambah terang
        if self.nilai_denyut <= 0.35:
            self.nilai_denyut = 0.35
            self.arah_denyut = 1

        # Menghitung komponen warna hijau sesuai nilai denyut
        hijau = int(150 + (70 * self.nilai_denyut))
        biru = int(180 + (40 * self.nilai_denyut))
        # Membuat kode warna hex dari komponen RGB
        warna = f"#{90:02x}{hijau:02x}{biru:02x}"

        # Menerapkan warna baru ke teks status header
        self.kanvas_header.itemconfig(self.teks_status_header, fill=warna)

        # Mengulang animasi ini lagi setelah 50 milidetik
        self.jendela.after(50, self.animasi_denyut)

    # ------------------------------------------------------------
    # FUNGSI: animasi_scan
    # Tujuan: menggeser garis cahaya tipis di header (efek "scan")
    # ------------------------------------------------------------
    def animasi_scan(self):
        # Menggeser posisi garis scan ke kanan
        self.posisi_scan += 6

        # Jika sudah keluar dari lebar header, kembalikan ke kiri
        if self.posisi_scan > 960:
            self.posisi_scan = -40

        # Memindahkan objek garis scan ke posisi baru
        self.kanvas_header.coords(
            self.garis_scan,
            self.posisi_scan,       # X kiri
            0,                      # Y atas
            self.posisi_scan + 36,  # X kanan
            168,                    # Y bawah
        )

        # Mengulang animasi geser setiap 40 milidetik
        self.jendela.after(40, self.animasi_scan)

    # ------------------------------------------------------------
    # FUNGSI: animasi_muncul_hero
    # Tujuan: membuat teks merek sedikit bergeser naik saat pertama dibuka
    # ------------------------------------------------------------
    def animasi_muncul_hero(self):
        # Menambah langkah animasi muncul
        self.opacity_hero += 1

        # Menghitung posisi Y yang perlahan naik ke tempat final
        # Mulai dari 78, berakhir di 58
        posisi_y = 78 - min(self.opacity_hero, 20)

        # Memindahkan teks merek ke posisi Y baru
        self.kanvas_header.coords(self.teks_merek, 40, posisi_y)

        # Jika belum selesai 20 langkah, lanjutkan animasi
        if self.opacity_hero < 20:
            # Panggil lagi setelah 25 milidetik
            self.jendela.after(25, self.animasi_muncul_hero)


# ------------------------------------------------------------
# FUNGSI: utama
# Tujuan: membuat jendela dan menjalankan aplikasi GUI
# ------------------------------------------------------------
def utama():
    # Membuat objek jendela utama Tkinter
    jendela = tk.Tk()

    # Membuat objek aplikasi NME Guardian dan menempelkannya ke jendela
    AplikasiNMEGuardian(jendela)

    # Menjalankan loop tampilan (jendela tetap terbuka menunggu aksi pengguna)
    jendela.mainloop()


# ------------------------------------------------------------
# TITIK MULAI PROGRAM
# Kode di dalam if ini hanya dijalankan jika file ini dieksekusi langsung
# (bukan saat diimpor oleh file Python lain)
# ------------------------------------------------------------
if __name__ == "__main__":
    # Memanggil fungsi utama untuk menjalankan NME Guardian
    utama()
