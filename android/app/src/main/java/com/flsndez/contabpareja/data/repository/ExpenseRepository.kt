package com.flsndez.contabpareja.data.repository

import com.flsndez.contabpareja.data.local.ContabDao
import com.flsndez.contabpareja.data.local.ExpenseRequestEntity
import com.flsndez.contabpareja.data.local.toEntity
import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.CreateExpenseBody
import com.flsndez.contabpareja.data.remote.DecisionBody
import com.flsndez.contabpareja.data.remote.ReportSummaryDto
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID
import kotlinx.coroutines.flow.Flow

class ExpenseRepository(
    private val api: ContabApi,
    private val dao: ContabDao,
) {
    val requests: Flow<List<ExpenseRequestEntity>> = dao.observeRequests()
    val categories = dao.observeCategories()

    suspend fun sync() {
        val requests = api.expenseRequests(limit = 100)
        val categories = api.categories()
        dao.upsertRequests(requests.map { it.toEntity() })
        dao.replaceAllCategories(categories.map { it.toEntity() })
    }

    suspend fun create(body: CreateExpenseBody) {
        val result = api.createExpense(UUID.randomUUID().toString(), body)
        dao.upsertRequest(result.toEntity())
    }

    suspend fun decide(requestId: String, approve: Boolean, reason: String? = null) {
        val result = api.decideExpense(
            requestId,
            DecisionBody(if (approve) "approve" else "reject", reason?.trim()),
        )
        dao.upsertRequest(result.toEntity())
    }

    suspend fun cancel(requestId: String) {
        dao.upsertRequest(api.cancelExpense(requestId).toEntity())
    }

    suspend fun currentMonthReport(): ReportSummaryDto {
        val to = Instant.now().plus(1, ChronoUnit.DAYS)
        val from = to.minus(31, ChronoUnit.DAYS)
        return api.reportSummary(from.toString(), to.toString())
    }
}
