package com.flsndez.contabpareja.ui

import java.math.BigDecimal

object ExpenseInputValidator {
    fun isValid(amount: String, description: String): Boolean =
        amount.toBigDecimalOrNull()?.let { it > BigDecimal.ZERO && it.scale() <= 2 } == true &&
            description.trim().length in 2..1000
}
