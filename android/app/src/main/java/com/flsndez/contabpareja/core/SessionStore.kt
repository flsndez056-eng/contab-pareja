package com.flsndez.contabpareja.core

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.core.content.edit
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SessionMemory {
    @Volatile
    var accessToken: String? = null
}

class SecureSessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("secure_session", Context.MODE_PRIVATE)

    fun saveRefreshToken(token: String) {
        saveEncrypted(REFRESH_TOKEN, token)
    }

    fun refreshToken(): String? = readEncrypted(REFRESH_TOKEN)

    fun clearRefreshToken() {
        clearEncrypted(REFRESH_TOKEN)
    }

    fun savePendingInviteToken(token: String) {
        saveEncrypted(INVITE_TOKEN, token)
    }

    fun pendingInviteToken(): String? = readEncrypted(INVITE_TOKEN)

    fun clearPendingInviteToken() {
        clearEncrypted(INVITE_TOKEN)
    }

    fun clearAll() {
        preferences.edit { clear() }
    }

    private fun saveEncrypted(key: String, value: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        preferences.edit {
            putString(key, Base64.encodeToString(encrypted, Base64.NO_WRAP))
            putString(ivKey(key), Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
        }
    }

    private fun readEncrypted(key: String): String? = runCatching {
        val encrypted = preferences.getString(key, null) ?: return null
        val iv = preferences.getString(ivKey(key), null) ?: return null
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            secretKey(),
            GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)),
        )
        cipher.doFinal(Base64.decode(encrypted, Base64.NO_WRAP)).toString(Charsets.UTF_8)
    }.getOrNull()

    private fun clearEncrypted(key: String) {
        preferences.edit {
            remove(key)
            remove(ivKey(key))
        }
    }

    private fun ivKey(key: String) = "${key}_iv"

    private fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build(),
            )
            generateKey()
        }
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "contab_pareja_refresh_token"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val REFRESH_TOKEN = "refresh_token"
        const val INVITE_TOKEN = "pending_invite_token"
    }
}
