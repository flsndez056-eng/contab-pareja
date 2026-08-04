package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.UserDto

class AccountRepository(private val api: ContabApi) {
    suspend fun me(): UserDto = api.me()
}
