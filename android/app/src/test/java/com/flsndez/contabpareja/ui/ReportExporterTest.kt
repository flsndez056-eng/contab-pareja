package com.flsndez.contabpareja.ui

import com.flsndez.contabpareja.data.local.ExpenseRequestEntity
import com.flsndez.contabpareja.data.remote.ReportSummaryDto
import org.junit.Assert.assertTrue
import org.junit.Test

class ReportExporterTest {
    @Test
    fun `csv escapes descriptions and contains approved amount`() {
        val report = ReportSummaryDto("DOP", "a", "b", "120.50", "0", "120.50", 1, emptyList())
        val expense = ExpenseRequestEntity(
            "1", "c", "u", null, "joint", null, "120.50", "DOP",
            "Cena, especial", null, "2026-08-09T20:30:00Z", "approved", null,
            "u2", "2026-08-09T20:31:00Z", 2, "2026-08-09T20:30:00Z", "2026-08-09T20:31:00Z",
        )

        val csv = ReportExporter.csv("2026-08", report, listOf(expense), emptyMap())

        assertTrue(csv.startsWith("Informe mensual,2026-08"))
        assertTrue(csv.contains("\"Cena, especial\""))
        assertTrue(csv.contains("120.50,DOP"))
    }
}
