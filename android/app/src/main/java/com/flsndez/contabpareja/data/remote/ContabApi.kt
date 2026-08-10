package com.flsndez.contabpareja.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.HTTP
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

    @POST("api/v1/auth/password/forgot")
    suspend fun forgotPassword(@Body body: ForgotPasswordBody): MessageDto

    @POST("api/v1/auth/password/reset")
    suspend fun resetPassword(@Body body: ResetPasswordBody)

    @POST("api/v1/auth/email/verification/confirm")
    suspend fun confirmEmail(@Body body: ConfirmEmailBody): UserDto

    @GET("api/v1/couples/invitations/preview")
    suspend fun previewInvitation(@Query("token") token: String): InvitationPreviewDto
}

interface ContabApi {
    @GET("api/v1/auth/me")
    suspend fun me(): UserDto

    @POST("api/v1/auth/password/change")
    suspend fun changePassword(@Body body: ChangePasswordBody): AuthResponseDto

    @POST("api/v1/auth/email/verification/request")
    suspend fun requestEmailVerification(): MessageDto

    @POST("api/v1/auth/sessions/revoke-all")
    suspend fun revokeAllSessions(@Body body: ReauthenticateBody): AuthResponseDto

    @HTTP(method = "DELETE", path = "api/v1/account", hasBody = true)
    suspend fun deleteAccount(@Body body: DeleteAccountBody): Response<Unit>

    @GET("api/v1/couples/current")
    suspend fun currentCouple(): CoupleStateDto

    @GET("api/v1/couples/history")
    suspend fun coupleHistory(): List<CoupleHistoryItemDto>

    @POST("api/v1/couples")
    suspend fun createCouple(@Body body: CreateCoupleBody): CoupleDto

    @POST("api/v1/couples/invitations")
    suspend fun createInvitation(): InvitationDto

    @POST("api/v1/couples/join")
    suspend fun joinCouple(@Body body: JoinCoupleBody): CoupleDto

    @POST("api/v1/couples/current/end")
    suspend fun endCouple(@Body body: EndCoupleBody): Response<Unit>

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
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null,
        @Query("category_id") categoryId: String? = null,
        @Query("q") search: String? = null,
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

    @GET("api/v1/budgets/{month}")
    suspend fun monthlyBudget(@Path("month") month: String): MonthlyBudgetDto

    @PUT("api/v1/budgets/{month}")
    suspend fun updateMonthlyBudget(
        @Path("month") month: String,
        @Body body: MonthlyBudgetUpdateBody,
    ): MonthlyBudgetDto

    @POST("api/v1/diagnostics/client-errors")
    suspend fun submitClientError(@Body body: ClientErrorBody): Response<Unit>

    @PUT("api/v1/devices/current")
    suspend fun registerDevice(@Body body: RegisterDeviceBody): DeviceDto

    @DELETE("api/v1/devices/{installationId}")
    suspend fun disableDevice(@Path("installationId") installationId: String): Response<Unit>
}
