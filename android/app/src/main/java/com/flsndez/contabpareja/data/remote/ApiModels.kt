package com.flsndez.contabpareja.data.remote

import com.google.gson.annotations.SerializedName

data class RegisterBody(
    val email: String,
    val password: String,
    @SerializedName("display_name") val displayName: String,
)

data class LoginBody(val email: String, val password: String)
data class ForgotPasswordBody(val email: String)
data class ResetPasswordBody(
    val token: String,
    @SerializedName("new_password") val newPassword: String,
)
data class ConfirmEmailBody(val token: String)
data class ChangePasswordBody(
    @SerializedName("current_password") val currentPassword: String,
    @SerializedName("new_password") val newPassword: String,
)
data class ReauthenticateBody(val password: String)
data class RefreshBody(@SerializedName("refresh_token") val refreshToken: String)
data class LogoutBody(@SerializedName("refresh_token") val refreshToken: String)
data class MessageDto(val message: String)

data class TokenPairDto(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("access_expires_at") val accessExpiresAt: String,
)

data class UserDto(
    val id: String,
    val email: String,
    @SerializedName("display_name") val displayName: String,
    @SerializedName("email_verified") val emailVerified: Boolean,
    @SerializedName("created_at") val createdAt: String,
)

data class AuthResponseDto(val user: UserDto, val tokens: TokenPairDto)

data class CreateCoupleBody(
    val name: String,
    @SerializedName("default_currency") val defaultCurrency: String = "DOP",
    val timezone: String = "America/Santo_Domingo",
)

data class JoinCoupleBody(val code: String)

data class CoupleDto(
    val id: String,
    val name: String,
    @SerializedName("default_currency") val defaultCurrency: String,
    val timezone: String,
    @SerializedName("created_at") val createdAt: String,
)

data class MemberDto(
    @SerializedName("user_id") val userId: String,
    @SerializedName("display_name") val displayName: String,
    val email: String,
    val slot: Int,
    val role: String,
    @SerializedName("joined_at") val joinedAt: String,
)

data class CoupleStateDto(val couple: CoupleDto?, val members: List<MemberDto>)
data class InvitationDto(val code: String, @SerializedName("expires_at") val expiresAt: String)

data class CategoryDto(val id: String, val slug: String, val name: String, val icon: String?)

data class CreateExpenseBody(
    val amount: String,
    val currency: String,
    val description: String,
    val merchant: String?,
    @SerializedName("category_id") val categoryId: String?,
    @SerializedName("payment_source") val paymentSource: String,
    @SerializedName("paid_by_user_id") val paidByUserId: String?,
    @SerializedName("occurred_at") val occurredAt: String,
)

data class DecisionBody(val decision: String, val reason: String?)

data class ExpenseRequestDto(
    val id: String,
    @SerializedName("couple_id") val coupleId: String,
    @SerializedName("requested_by") val requestedBy: String,
    @SerializedName("paid_by_user_id") val paidByUserId: String?,
    @SerializedName("payment_source") val paymentSource: String,
    @SerializedName("category_id") val categoryId: String?,
    val amount: String,
    val currency: String,
    val description: String,
    val merchant: String?,
    @SerializedName("occurred_at") val occurredAt: String,
    val status: String,
    @SerializedName("rejection_reason") val rejectionReason: String?,
    @SerializedName("resolved_by") val resolvedBy: String?,
    @SerializedName("resolved_at") val resolvedAt: String?,
    val version: Int,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
)

data class CategoryTotalDto(
    @SerializedName("category_id") val categoryId: String?,
    @SerializedName("category_name") val categoryName: String,
    val total: String,
)

data class ReportSummaryDto(
    val currency: String,
    @SerializedName("from_date") val fromDate: String,
    @SerializedName("to_date") val toDate: String,
    val total: String,
    @SerializedName("personal_total") val personalTotal: String,
    @SerializedName("joint_total") val jointTotal: String,
    @SerializedName("expense_count") val expenseCount: Int,
    val categories: List<CategoryTotalDto>,
)

data class RegisterDeviceBody(
    @SerializedName("installation_id") val installationId: String,
    @SerializedName("fcm_registration_id") val fcmRegistrationId: String,
    val platform: String = "android",
)

data class DeviceDto(
    val id: String,
    @SerializedName("installation_id") val installationId: String,
    val platform: String,
    val enabled: Boolean,
    @SerializedName("last_seen_at") val lastSeenAt: String,
)
