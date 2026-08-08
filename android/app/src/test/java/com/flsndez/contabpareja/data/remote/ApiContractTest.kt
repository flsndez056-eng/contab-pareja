package com.flsndez.contabpareja.data.remote

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.http.HTTP

class ApiContractTest {
    private val gson = Gson()

    @Test
    fun deviceRegistrationUsesFidContract() {
        val json = gson.toJson(RegisterDeviceBody("installation-123", "firebase-installation-123"))
        assertTrue(json.contains("fcm_registration_id"))
        assertFalse(json.contains("fcm_token"))
    }

    @Test
    fun expenseUsesBackendSnakeCaseFields() {
        val json = gson.toJson(
            CreateExpenseBody(
                amount = "100.00",
                currency = "DOP",
                description = "Cena",
                merchant = null,
                categoryId = "category-id",
                paymentSource = "joint",
                paidByUserId = null,
                occurredAt = "2026-08-03T20:00:00Z",
            ),
        )
        assertTrue(json.contains("payment_source"))
        assertTrue(json.contains("occurred_at"))
        assertTrue(json.contains("category_id"))
    }

    @Test
    fun passwordActionsUseBackendSnakeCaseFields() {
        val resetJson = gson.toJson(ResetPasswordBody("token", "new-password"))
        val changeJson = gson.toJson(ChangePasswordBody("current", "new-password"))
        assertTrue(resetJson.contains("new_password"))
        assertTrue(changeJson.contains("current_password"))
        assertTrue(changeJson.contains("new_password"))
    }

    @Test
    fun invitationAndDeletionUseSecureLifecycleContracts() {
        val joinJson = gson.toJson(JoinCoupleBody(token = "secure-invite-token"))
        val deleteJson = gson.toJson(DeleteAccountBody("password-123"))
        assertTrue(joinJson.contains("secure-invite-token"))
        assertFalse(joinJson.contains("code"))
        assertTrue(deleteJson.contains("ELIMINAR"))
    }

    @Test
    fun accountDeletionAllowsAnHttpRequestBody() {
        val method = ContabApi::class.java.declaredMethods.single { it.name == "deleteAccount" }
        val annotation = requireNotNull(method.getAnnotation(HTTP::class.java))

        assertEquals("DELETE", annotation.method)
        assertEquals("api/v1/account", annotation.path)
        assertTrue(annotation.hasBody)
    }
}
