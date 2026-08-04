package com.flsndez.contabpareja.core

import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val session: SessionMemory) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = session.accessToken
        val request = if (token.isNullOrBlank()) {
            chain.request()
        } else {
            chain.request().newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        }
        return chain.proceed(request)
    }
}
