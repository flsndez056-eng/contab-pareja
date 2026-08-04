package com.flsndez.contabpareja.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface PublicApi {
    @POST("api/v1/auth/register")
    suspend fun register(@Body body: RegisterBody): AuthResponseDto

    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginBody): AuthResponseDto

    @POST("api/v1/auth/refresh")
    suspend fun refresh(@Body body: RefreshBody): TokenPairDto

    @POST("api/v1/auth/logout")
    suspend fun logout(@Body body: LogoutBody): Response<Unit>
}

interface ContabApi {
    @GET("api/v1/auth/me")
    suspend fun me(): UserDto

    @GET("api/v1/couples/current")
    suspend fun currentCouple(): CoupleStateDto

    @POST("api/v1/couples")
    suspend fun createCouple(@Body body: CreateCoupleBody): CoupleDto

    @POST("api/v1/couples/invitations")
    suspend fun createInvitation(): InvitationDto

    @POST("api/v1/couples/join")
    suspend fun joinCouple(@Body body: JoinCoupleBody): CoupleDto

    @GET("api/v1/categories")
    suspend fun categories(): List<CategoryDto>

    @POST("api/v1/expense-requests")
    suspend fun createExpense(
        @Header("Idempotency-Key") idempotencyKey: String,
        @Body body: CreateExpenseBody,
    ): ExpenseRequestDto

    @GET("api/v1/expense-requests")
    suspend fun expenseRequests(
        @Query("box") box: String = "all",
        @Query("status") status: String? = null,
        @Query("limit") limit: Int = 30,
        @Query("offset") offset: Int = 0,
    ): List<ExpenseRequestDto>

    @POST("api/v1/expense-requests/{requestId}/decision")
    suspend fun decideExpense(
        @Path("requestId") requestId: String,
        @Body body: DecisionBody,
    ): ExpenseRequestDto

    @POST("api/v1/expense-requests/{requestId}/cancel")
    suspend fun cancelExpense(@Path("requestId") requestId: String): ExpenseRequestDto

    @GET("api/v1/reports/summary")
    suspend fun reportSummary(
        @Query("from_date") fromDate: String,
        @Query("to_date") toDate: String,
    ): ReportSummaryDto

    @PUT("api/v1/devices/current")
    suspend fun registerDevice(@Body body: RegisterDeviceBody): DeviceDto

    @DELETE("api/v1/devices/{installationId}")
    suspend fun disableDevice(@Path("installationId") installationId: String): Response<Unit>
}
