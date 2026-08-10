package com.flsndez.contabpareja.core

import android.content.Context
import com.flsndez.contabpareja.BuildConfig
import com.flsndez.contabpareja.data.remote.ClientErrorBody
import com.flsndez.contabpareja.data.remote.ContabApi
import com.google.gson.Gson
import java.security.MessageDigest
import java.time.Instant

class PrivateDiagnostics(context: Context, private val api: ContabApi) {
    private val preferences = context.getSharedPreferences("contab_private_diagnostics", Context.MODE_PRIVATE)
    private val gson = Gson()

    fun install() {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            runCatching { persistSanitized(throwable) }
            previous?.uncaughtException(thread, throwable)
        }
    }

    suspend fun uploadPending() {
        val raw = preferences.getString(KEY_PENDING, null) ?: return
        val report = runCatching { gson.fromJson(raw, ClientErrorBody::class.java) }.getOrNull()
        if (report == null) {
            preferences.edit().remove(KEY_PENDING).apply()
            return
        }
        if (api.submitClientError(report).isSuccessful) {
            preferences.edit().remove(KEY_PENDING).apply()
        }
    }

    private fun persistSanitized(throwable: Throwable) {
        val frames = throwable.stackTrace
            .asSequence()
            .map(StackTraceElement::toString)
            .filter { it.startsWith(APP_PACKAGE) }
            .take(MAX_FRAMES)
            .toList()
        val canonical = buildString {
            append(throwable.javaClass.name)
            frames.forEach { append('|').append(it) }
        }
        val fingerprint = MessageDigest.getInstance("SHA-256")
            .digest(canonical.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        val report = ClientErrorBody(
            appVersion = BuildConfig.VERSION_NAME,
            errorType = throwable.javaClass.name.take(100),
            fingerprint = fingerprint,
            stackFrames = frames,
            screen = null,
            occurredAt = Instant.now().toString(),
        )
        preferences.edit().putString(KEY_PENDING, gson.toJson(report)).commit()
    }

    private companion object {
        const val KEY_PENDING = "pending_report"
        const val APP_PACKAGE = "com.flsndez.contabpareja"
        const val MAX_FRAMES = 20
    }
}
