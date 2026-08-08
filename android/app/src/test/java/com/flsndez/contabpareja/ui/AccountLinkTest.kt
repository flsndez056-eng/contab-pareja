package com.flsndez.contabpareja.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AccountLinkTest {
    @Test
    fun acceptsCustomSchemeAndVerifiedHttpsOrigins() {
        assertEquals(
            "/reset-password",
            accountActionPath("contabpareja", "auth", "/reset-password"),
        )
        assertEquals(
            "/verify-email",
            accountActionPath(
                "https",
                "contab.siptrapollo.online",
                "/verify-email",
            ),
        )
    }

    @Test
    fun rejectsUnknownOriginsAndPaths() {
        assertNull(accountActionPath("https", "example.com", "/reset-password"))
        assertNull(accountActionPath("https", "contab.siptrapollo.online", "/other"))
    }
}
