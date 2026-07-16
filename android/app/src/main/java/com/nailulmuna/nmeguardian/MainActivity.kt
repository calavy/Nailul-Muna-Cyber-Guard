package com.nailulmuna.nmeguardian

import android.app.AppOpsManager
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import java.util.concurrent.Executors

/**
 * NME Guardian (Android) — pantau aplikasi foreground,
 * kirim aktivitas ke Firebase, cek link diblokir,
 * dan ajukan izin saat santri mencoba memasang APK.
 */
class MainActivity : AppCompatActivity() {

    // URL Firebase dibaca dari assets/config.json (samakan dengan config.json di PC).
    private lateinit var firebaseUrl: String

    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var txtStatus: TextView
    private lateinit var txtAktivitas: TextView
    private val idPerangkat: String by lazy {
        "android-" + (Build.MODEL ?: "hp").replace(" ", "-").lowercase(Locale.ROOT)
    }

    private fun bacaFirebaseUrl(): String {
        return try {
            assets.open("config.json").bufferedReader().use { reader ->
                val json = JSONObject(reader.readText())
                json.optString("firebase_url", "http://10.0.2.2:8765").trimEnd('/')
            }
        } catch (e: Exception) {
            "http://10.0.2.2:8765"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        firebaseUrl = bacaFirebaseUrl()
        // Emulator lokal: jika config masih 127.0.0.1, arahkan ke host PC emulator
        if (firebaseUrl.contains("127.0.0.1") || firebaseUrl.contains("localhost")) {
            firebaseUrl = firebaseUrl
                .replace("127.0.0.1", "10.0.2.2")
                .replace("localhost", "10.0.2.2")
        }

        txtStatus = findViewById(R.id.txtStatus)
        txtAktivitas = findViewById(R.id.txtAktivitas)
        val btnUsage = findViewById<Button>(R.id.btnUsage)
        val btnMulai = findViewById<Button>(R.id.btnMulai)
        val btnIzinApk = findViewById<Button>(R.id.btnIzinApk)

        btnUsage.setOnClickListener {
            startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
        }

        btnMulai.setOnClickListener {
            if (!punyaAksesUsage()) {
                Toast.makeText(this, "Aktifkan akses Usage Stats dulu", Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            mulaiPantauBerkala()
            Toast.makeText(this, "Pemantauan Android dimulai", Toast.LENGTH_SHORT).show()
        }

        btnIzinApk.setOnClickListener {
            ajukanIzinInstalContoh()
        }

        txtStatus.text = "Perangkat: $idPerangkat\nFirebase: $firebaseUrl"
    }

    private fun punyaAksesUsage(): Boolean {
        val appOps = getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                "android:get_usage_stats",
                android.os.Process.myUid(),
                packageName
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                "android:get_usage_stats",
                android.os.Process.myUid(),
                packageName
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun aplikasiForeground(): String {
        val usm = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val akhir = System.currentTimeMillis()
        val awal = akhir - 60_000
        val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, awal, akhir)
        if (stats.isNullOrEmpty()) return "(tidak diketahui)"
        val teratas = stats.maxByOrNull { it.lastTimeUsed }
        return teratas?.packageName ?: "(tidak diketahui)"
    }

    private fun mulaiPantauBerkala() {
        handler.post(object : Runnable {
            override fun run() {
                executor.execute {
                    try {
                        val app = aplikasiForeground()
                        val linkBlokir = getJson("$firebaseUrl/link_diblokir.json")
                        val payload = JSONObject()
                        payload.put("id_perangkat", idPerangkat)
                        payload.put("platform", "android")
                        payload.put(
                            "terakhir_update",
                            SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
                        )
                        payload.put("aplikasi_foreground", app)
                        payload.put("jumlah_link_diblokir", linkBlokir?.length() ?: 0)
                        payload.put(
                            "catatan",
                            "Blokir link aktif di sisi DNS/hosts perangkat atau browser bawaan pesantren."
                        )
                        putJson("$firebaseUrl/aktivitas_online/android.json", payload)

                        val perangkat = JSONObject()
                        perangkat.put("nama", Build.MODEL)
                        perangkat.put("platform", "android")
                        perangkat.put("terakhir_online", payload.getString("terakhir_update"))
                        putJson("$firebaseUrl/perangkat/$idPerangkat.json", perangkat)

                        handler.post {
                            txtAktivitas.text =
                                "App aktif: $app\nLink diblokir: ${linkBlokir?.length() ?: 0}\nUpdate: ${payload.getString("terakhir_update")}"
                        }
                    } catch (e: Exception) {
                        handler.post {
                            txtAktivitas.text = "Error: ${e.message}"
                        }
                    }
                }
                handler.postDelayed(this, 8000)
            }
        })
    }

    /**
     * Contoh alur: santri ingin install APK → kirim permintaan pending ke Firebase.
     * Pengasuh setujui/tolak lewat panel admin.
     */
    private fun ajukanIzinInstalContoh() {
        executor.execute {
            try {
                val id = "req_" + UUID.randomUUID().toString().take(10)
                val data = JSONObject()
                data.put("id", id)
                data.put("nama_file", "aplikasi-santri.apk")
                data.put("ekstensi", ".apk")
                data.put("perangkat", idPerangkat)
                data.put("platform", "android")
                data.put("status", "pending")
                data.put(
                    "waktu_ajuan",
                    SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
                )
                data.put("pesan_santri", "Santri meminta izin memasang APK")
                putJson("$firebaseUrl/izin_instal/$id.json", data)
                handler.post {
                    Toast.makeText(this, "Permintaan izin APK dikirim ($id)", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                handler.post {
                    Toast.makeText(this, "Gagal: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun getJson(urlStr: String): JSONObject? {
        val conn = (URL(urlStr).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 8000
            readTimeout = 8000
        }
        conn.inputStream.bufferedReader().use { reader ->
            val body = reader.readText()
            if (body == "null" || body.isBlank()) return null
            return JSONObject(body)
        }
    }

    private fun putJson(urlStr: String, json: JSONObject) {
        val conn = (URL(urlStr).openConnection() as HttpURLConnection).apply {
            requestMethod = "PUT"
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            connectTimeout = 8000
            readTimeout = 8000
        }
        conn.outputStream.use { it.write(json.toString().toByteArray()) }
        conn.inputStream.bufferedReader().use { it.readText() }
        conn.disconnect()
    }
}
