// Buka folder "android" ini di Android Studio (Open).
// Sesuaikan firebaseUrl di MainActivity.kt:
// - Emulator: http://10.0.2.2:8765
// - HP nyata + PC satu WiFi: http://IP_PC_ANDA:8765
// - Cloud: URL Realtime Database Firebase Anda
//
// Fitur kerangka:
// 1. Pantau aplikasi foreground (Usage Access)
// 2. Kirim aktivitas ke /aktivitas_online/android
// 3. Baca /link_diblokir
// 4. Ajukan izin install APK ke /izin_instal (disetujui di panel admin)
//
// Catatan produksi:
// Blokir install APK penuh biasanya butuh Device Owner / MDM.
// Kerangka ini sudah menyiapkan alur izin online ke pengasuh.
