package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.CoupleStateDto
import com.flsndez.contabpareja.data.remote.CreateCoupleBody
import com.flsndez.contabpareja.data.remote.InvitationDto
import com.flsndez.contabpareja.data.remote.JoinCoupleBody

class CoupleRepository(private val api: ContabApi) {
    suspend fun state(): CoupleStateDto = api.currentCouple()

    suspend fun create(name: String): CoupleStateDto {
        api.createCouple(CreateCoupleBody(name.trim()))
        return state()
    }

    suspend fun join(code: String): CoupleStateDto {
        api.joinCouple(JoinCoupleBody(code.trim().uppercase()))
        return state()
    }

    suspend fun invite(): InvitationDto = api.createInvitation()
}
