package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.CoupleStateDto
import com.flsndez.contabpareja.data.remote.CoupleHistoryItemDto
import com.flsndez.contabpareja.data.remote.CreateCoupleBody
import com.flsndez.contabpareja.data.remote.EndCoupleBody
import com.flsndez.contabpareja.data.remote.InvitationDto
import com.flsndez.contabpareja.data.remote.InvitationPreviewDto
import com.flsndez.contabpareja.data.remote.JoinCoupleBody
import com.flsndez.contabpareja.data.remote.PublicApi

class CoupleRepository(
    private val api: ContabApi,
    private val publicApi: PublicApi,
) {
    suspend fun state(): CoupleStateDto = api.currentCouple()

    suspend fun create(name: String): CoupleStateDto {
        api.createCouple(CreateCoupleBody(name.trim()))
        return state()
    }

    suspend fun joinCode(code: String): CoupleStateDto {
        api.joinCouple(JoinCoupleBody(code = code.trim().uppercase()))
        return state()
    }

    suspend fun joinToken(token: String): CoupleStateDto {
        api.joinCouple(JoinCoupleBody(token = token.trim()))
        return state()
    }

    suspend fun invite(): InvitationDto = api.createInvitation()

    suspend fun preview(token: String): InvitationPreviewDto =
        publicApi.previewInvitation(token.trim())

    suspend fun end(password: String) {
        api.endCouple(EndCoupleBody(password))
    }

    suspend fun history(): List<CoupleHistoryItemDto> = api.coupleHistory()
}
