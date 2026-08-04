package com.flsndez.contabpareja.data.remote

import com.google.gson.Gson
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

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
}
