package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.AuthResponseDto
import com.flsndez.contabpareja.data.remote.ChangePasswordBody
import com.flsndez.contabpareja.data.remote.ReauthenticateBody
import com.flsndez.contabpareja.data.remote.UserDto

class AccountRepository(private val api: ContabApi) {
    suspend fun me(): UserDto = api.me()

    suspend fun requestEmailVerification(): String = api.requestEmailVerification().message

    suspend fun changePassword(currentPassword: String, newPassword: String): AuthResponseDto =
        api.changePassword(ChangePasswordBody(currentPassword, newPassword))

    suspend fun revokeAllSessions(password: String): AuthResponseDto =
        api.revokeAllSessions(ReauthenticateBody(password))
}
