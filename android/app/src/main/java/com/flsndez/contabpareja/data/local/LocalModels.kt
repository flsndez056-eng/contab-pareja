package com.flsndez.contabpareja.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.flsndez.contabpareja.data.remote.CategoryDto
import com.flsndez.contabpareja.data.remote.ExpenseRequestDto

@Entity(tableName = "expense_requests")
data class ExpenseRequestEntity(
    @PrimaryKey val id: String,
    val coupleId: String,
    val requestedBy: String,
    val paidByUserId: String?,
    val paymentSource: String,
    val categoryId: String?,
    val amount: String,
    val currency: String,
    val description: String,
    val merchant: String?,
    val occurredAt: String,
    val status: String,
    val rejectionReason: String?,
    val resolvedBy: String?,
    val resolvedAt: String?,
    val version: Int,
    val createdAt: String,
    val updatedAt: String,
)

@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey val id: String,
    val slug: String,
    val name: String,
    val icon: String?,
)

fun ExpenseRequestDto.toEntity() = ExpenseRequestEntity(
    id = id,
    coupleId = coupleId,
    requestedBy = requestedBy,
    paidByUserId = paidByUserId,
    paymentSource = paymentSource,
    categoryId = categoryId,
    amount = amount,
    currency = currency,
    description = description,
    merchant = merchant,
    occurredAt = occurredAt,
    status = status,
    rejectionReason = rejectionReason,
    resolvedBy = resolvedBy,
    resolvedAt = resolvedAt,
    version = version,
    createdAt = createdAt,
    updatedAt = updatedAt,
)

fun CategoryDto.toEntity() = CategoryEntity(id, slug, name, icon)
