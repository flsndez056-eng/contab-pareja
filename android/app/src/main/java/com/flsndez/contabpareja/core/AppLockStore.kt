package com.flsndez.contabpareja.core

import android.content.Context
import android.util.Base64
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

enum class AppLockMode { NONE, PIN, BIOMETRIC }

class AppLockStore(context: Context) {
    private val preferences = context.getSharedPreferences("contab_app_lock", Context.MODE_PRIVATE)

    val mode: AppLockMode
        get() = runCatching {
            AppLockMode.valueOf(preferences.getString(KEY_MODE, AppLockMode.NONE.name).orEmpty())
        }.getOrDefault(AppLockMode.NONE)

    fun setPin(pin: String) {
        require(pin.matches(Regex("^[0-9]{4,8}$"))) { "El PIN debe tener entre 4 y 8 dígitos." }
        val salt = ByteArray(16).also(SecureRandom()::nextBytes)
        val hash = derive(pin, salt)
        preferences.edit()
            .putString(KEY_SALT, Base64.encodeToString(salt, Base64.NO_WRAP))
            .putString(KEY_HASH, Base64.encodeToString(hash, Base64.NO_WRAP))
            .putString(KEY_MODE, AppLockMode.PIN.name)
            .apply()
    }

    fun verifyPin(pin: String): Boolean {
        val salt = preferences.getString(KEY_SALT, null)?.decode() ?: return false
        val expected = preferences.getString(KEY_HASH, null)?.decode() ?: return false
        return MessageDigest.isEqual(expected, derive(pin, salt))
    }

    fun enableBiometric() {
        preferences.edit()
            .remove(KEY_SALT)
            .remove(KEY_HASH)
            .putString(KEY_MODE, AppLockMode.BIOMETRIC.name)
            .apply()
    }

    fun disable() {
        preferences.edit().clear().apply()
    }

    private fun String.decode(): ByteArray? = runCatching {
        Base64.decode(this, Base64.NO_WRAP)
    }.getOrNull()

    private fun derive(pin: String, salt: ByteArray): ByteArray {
        val spec = PBEKeySpec(pin.toCharArray(), salt, ITERATIONS, KEY_BITS)
        return try {
            SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
        } finally {
            spec.clearPassword()
        }
    }

    private companion object {
        const val KEY_MODE = "mode"
        const val KEY_SALT = "pin_salt"
        const val KEY_HASH = "pin_hash"
        const val ITERATIONS = 210_000
        const val KEY_BITS = 256
    }
}
