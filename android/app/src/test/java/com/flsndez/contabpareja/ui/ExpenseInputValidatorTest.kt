package com.flsndez.contabpareja.ui

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExpenseInputValidatorTest {
    @Test
    fun acceptsPositiveAmountWithTwoDecimals() {
        assertTrue(ExpenseInputValidator.isValid("1250.50", "Compra del supermercado"))
    }

    @Test
    fun rejectsZeroNegativeOrExcessDecimals() {
        assertFalse(ExpenseInputValidator.isValid("0", "Cena"))
        assertFalse(ExpenseInputValidator.isValid("-1", "Cena"))
        assertFalse(ExpenseInputValidator.isValid("10.999", "Cena"))
    }

    @Test
    fun rejectsTooShortDescription() {
        assertFalse(ExpenseInputValidator.isValid("10.00", "x"))
    }
}
