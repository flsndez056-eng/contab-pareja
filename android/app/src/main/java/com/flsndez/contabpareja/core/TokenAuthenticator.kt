package com.flsndez.contabpareja.core

import com.flsndez.contabpareja.data.repository.AuthRepository
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

class TokenAuthenticator(
    private val session: SessionMemory,
    private val authRepository: AuthRepository,
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= 2) return null
        val failedToken = response.request.header("Authorization")?.removePrefix("Bearer ")
        val current = session.accessToken
        val token = if (!current.isNullOrBlank() && current != failedToken) {
            current
        } else {
            runBlocking { authRepository.refreshAccessToken() }
        } ?: return null

        return response.request.newBuilder()
            .header("Authorization", "Bearer $token")
            .build()
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count++
            prior = prior.priorResponse
        }
        return count
    }
}
