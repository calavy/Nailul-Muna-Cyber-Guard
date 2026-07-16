package com.nailulmuna.nmeguardian

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast

/**
 * Menerima event paket ditambahkan.
 * Di produksi, gabungkan dengan Device Owner / play protect policy.
 * Di sini kita beri peringatan dan arahkan ke alur izin Firebase.
 */
class PackageInstallReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_PACKAGE_ADDED ||
            intent.action == Intent.ACTION_PACKAGE_REPLACED
        ) {
            val pkg = intent.data?.schemeSpecificPart ?: "?"
            Toast.makeText(
                context,
                "NME Guardian: paket terpasang ($pkg). Pastikan sudah ada izin pengasuh.",
                Toast.LENGTH_LONG
            ).show()
        }
    }
}
