package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.core.SecureSessionStore
import com.flsndez.contabpareja.core.SessionMemory
import com.flsndez.contabpareja.data.remote.AuthResponseDto
import com.flsndez.contabpareja.data.remote.LoginBody
import com.flsndez.contabpareja.data.remote.LogoutBody
import com.flsndez.contabpareja.data.remote.PublicApi
import com.flsndez.contabpareja.data.remote.RefreshBody
import com.flsndez.contabpareja.data.remote.RegisterBody
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import retrofit2.HttpException

class AuthRepository(
    private val api: PublicApi,
    private val secureStore: SecureSessionStore,
    private val session: SessionMemory,
) {
    private val refreshMutex = Mutex()

    suspend fun register(name: String, email: String, password: String): AuthResponseDto =
        api.register(RegisterBody(email.trim(), password, name.trim())).also(::persist)

    suspend fun login(email: String, password: String): AuthResponseDto =
        api.login(LoginBody(email.trim(), password)).also(::persist)

    suspend fun restoreSession(): Boolean = refreshAccessToken() != null

    suspend fun refreshAccessToken(): String? = refreshMutex.withLock {
        val refreshToken = secureStore.refreshToken() ?: return@withLock null
        runCatching { api.refresh(RefreshBody(refreshToken)) }
            .onSuccess { tokens ->
                session.accessToken = tokens.accessToken
                secureStore.saveRefreshToken(tokens.refreshToken)
            }
            .onFailure { error ->
                if (error is HttpException && error.code() in listOf(400, 401)) clearSession()
            }
            .getOrNull()
            ?.accessToken
    }

    suspend fun logout() {
        val token = secureStore.refreshToken()
        if (token != null) runCatching { api.logout(LogoutBody(token)) }
        clearSession()
    }

    fun clearSession() {
        session.accessToken = null
        secureStore.clear()
    }

    private fun persist(response: AuthResponseDto) {
        session.accessToken = response.tokens.accessToken
        secureStore.saveRefreshToken(response.tokens.refreshToken)
    }
}
