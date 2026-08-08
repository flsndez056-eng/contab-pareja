package com.flsndez.contabpareja.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
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

    @Test
    fun preservesPasswordResetLinkWhileSignedOutBootstrapFinishes() {
        val result = signedOutStateAfterBootstrap(
            MainUiState(
                screen = AppScreen.RESET_PASSWORD,
                loading = true,
                resetToken = "recovery-token",
            ),
        )

        assertEquals(AppScreen.RESET_PASSWORD, result.screen)
        assertEquals("recovery-token", result.resetToken)
        assertFalse(result.loading)
    }

    @Test
    fun recordsVisiblePasswordResetRequestConfirmation() {
        val result = passwordResetRequestSucceeded(
            MainUiState(screen = AppScreen.FORGOT_PASSWORD),
            "Correo enviado.",
        )

        assertTrue(result.passwordResetRequestSent)
        assertEquals("Correo enviado.", result.notice)
    }

    @Test
    fun returnsToLoginWithVisibleConfirmationAfterPasswordChange() {
        val result = passwordResetSucceeded()

        assertEquals(AppScreen.AUTH, result.screen)
        assertFalse(result.loading)
        assertEquals("Contraseña actualizada. Ya puedes iniciar sesión.", result.notice)
    }
}
