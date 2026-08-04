package com.flsndez.contabpareja.data.repository

import android.content.Context
import androidx.core.content.edit
import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.RegisterDeviceBody
import java.util.UUID

class DeviceRepository(context: Context, private val api: ContabApi) {
    private val preferences = context.getSharedPreferences("installation", Context.MODE_PRIVATE)

    val installationId: String
        get() = preferences.getString(KEY_INSTALLATION_ID, null) ?: UUID.randomUUID().toString().also {
            preferences.edit { putString(KEY_INSTALLATION_ID, it) }
        }

    suspend fun register(fcmRegistrationId: String) {
        api.registerDevice(RegisterDeviceBody(installationId, fcmRegistrationId))
    }

    private companion object {
        const val KEY_INSTALLATION_ID = "installation_id"
    }
}
