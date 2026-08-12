package com.flsndez.contabpareja.ui

import android.content.Context
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.net.Uri
import com.flsndez.contabpareja.data.local.ExpenseRequestEntity
import com.flsndez.contabpareja.data.remote.ReportSummaryDto
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

object ReportExporter {
    fun csv(
        month: String,
        report: ReportSummaryDto,
        expenses: List<ExpenseRequestEntity>,
        categoryNames: Map<String, String>,
    ): String = buildString {
        appendLine("Informe mensual,$month")
        appendLine("Total,${escape(report.total)},${escape(report.currency)}")
        appendLine()
        appendLine("Fecha,Hora,Descripción,Comercio,Categoría,Tipo,Monto,Moneda")
        expenses.sortedBy { it.occurredAt }.forEach { expense ->
            val instant = runCatching { Instant.parse(expense.occurredAt) }.getOrNull()
            val local = instant?.atZone(ZoneId.systemDefault())
            appendLine(
                listOf(
                    local?.toLocalDate()?.toString().orEmpty(),
                    local?.toLocalTime()?.format(DateTimeFormatter.ofPattern("HH:mm")).orEmpty(),
                    expense.description,
                    expense.merchant.orEmpty(),
                    expense.categoryId?.let(categoryNames::get) ?: "Sin categoría",
                    if (expense.paymentSource == "joint") "Conjunto" else "Personal",
                    expense.amount,
                    expense.currency,
                ).joinToString(",", transform = ::escape),
            )
        }
    }

    fun writeCsv(context: Context, uri: Uri, content: String) {
        context.contentResolver.openOutputStream(uri, "w")!!.bufferedWriter(Charsets.UTF_8).use {
            it.write('\uFEFF'.code)
            it.write(content)
        }
    }

    fun writePdf(
        context: Context,
        uri: Uri,
        month: String,
        report: ReportSummaryDto,
        expenses: List<ExpenseRequestEntity>,
        categoryNames: Map<String, String>,
    ) {
        val document = PdfDocument()
        val title = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 22f
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        }
        val heading = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 14f
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        }
        val body = Paint(Paint.ANTI_ALIAS_FLAG).apply { textSize = 10f }
        var pageNumber = 0
        var page: PdfDocument.Page? = null
        var y = 0f

        fun newPage() {
            page?.let(document::finishPage)
            pageNumber += 1
            page = document.startPage(PdfDocument.PageInfo.Builder(595, 842, pageNumber).create())
            y = 54f
        }

        fun line(text: String, paint: Paint = body, spacing: Float = 18f) {
            if (page == null || y > 800f) newPage()
            page!!.canvas.drawText(text.take(92), 42f, y, paint)
            y += spacing
        }

        newPage()
        line("DúoCuenta", title, 30f)
        line("Informe mensual · $month", heading, 24f)
        line("Total aprobado: ${report.total} ${report.currency}", heading, 24f)
        line("Resumen por categoría", heading, 21f)
        report.categories.forEach { line("• ${it.categoryName}: ${it.total} ${report.currency}") }
        y += 10f
        line("Gastos aprobados (${expenses.size})", heading, 22f)
        expenses.sortedBy { it.occurredAt }.forEach { expense ->
            val date = runCatching { Instant.parse(expense.occurredAt) }.getOrNull()
                ?.atZone(ZoneId.systemDefault())
                ?.format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"))
                ?: expense.occurredAt.take(16)
            val category = expense.categoryId?.let(categoryNames::get) ?: "Sin categoría"
            line("$date · ${expense.description} · $category · ${expense.amount} ${expense.currency}")
        }
        page?.let(document::finishPage)
        context.contentResolver.openOutputStream(uri, "w")!!.use { document.writeTo(it) }
        document.close()
    }

    private fun escape(value: String): String =
        if (value.any { it == ',' || it == '"' || it == '\n' || it == '\r' }) {
            "\"${value.replace("\"", "\"\"")}\""
        } else {
            value
        }
}
