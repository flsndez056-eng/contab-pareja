package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.core.SecureSessionStore
import com.flsndez.contabpareja.core.SessionMemory
import com.flsndez.contabpareja.data.remote.AuthResponseDto
import com.flsndez.contabpareja.data.remote.ConfirmEmailBody
import com.flsndez.contabpareja.data.remote.ForgotPasswordBody
import com.flsndez.contabpareja.data.remote.LoginBody
import com.flsndez.contabpareja.data.remote.LogoutBody
import com.flsndez.contabpareja.data.remote.PublicApi
import com.flsndez.contabpareja.data.remote.RefreshBody
import com.flsndez.contabpareja.data.remote.RegisterBody
import com.flsndez.contabpareja.data.remote.ResetPasswordBody
import com.flsndez.contabpareja.data.remote.UserDto
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

    suspend fun forgotPassword(email: String): String =
        api.forgotPassword(ForgotPasswordBody(email.trim())).message

    suspend fun resetPassword(token: String, newPassword: String) {
        api.resetPassword(ResetPasswordBody(token.trim(), newPassword))
        clearSession()
    }

    suspend fun confirmEmail(token: String): UserDto =
        api.confirmEmail(ConfirmEmailBody(token.trim()))

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
        secureStore.clearRefreshToken()
    }

    fun rememberPendingInvite(token: String) = secureStore.savePendingInviteToken(token.trim())

    fun pendingInviteToken(): String? = secureStore.pendingInviteToken()

    fun clearPendingInvite() = secureStore.clearPendingInviteToken()

    fun clearAllSessionData() {
        session.accessToken = null
        secureStore.clearAll()
    }

    fun accept(response: AuthResponseDto) = persist(response)

    private fun persist(response: AuthResponseDto) {
        session.accessToken = response.tokens.accessToken
        secureStore.saveRefreshToken(response.tokens.refreshToken)
    }
}
