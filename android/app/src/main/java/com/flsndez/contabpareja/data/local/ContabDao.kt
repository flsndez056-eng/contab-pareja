package com.flsndez.contabpareja.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ContabDao {
    @Query("SELECT * FROM expense_requests ORDER BY createdAt DESC")
    fun observeRequests(): Flow<List<ExpenseRequestEntity>>

    @Query("SELECT * FROM expense_requests WHERE status = 'pending' ORDER BY createdAt DESC")
    fun observePendingRequests(): Flow<List<ExpenseRequestEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertRequests(requests: List<ExpenseRequestEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertRequest(request: ExpenseRequestEntity)

    @Query("DELETE FROM expense_requests")
    suspend fun clearRequests()

    @Query("SELECT * FROM categories ORDER BY name")
    fun observeCategories(): Flow<List<CategoryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun replaceCategories(categories: List<CategoryEntity>)

    @Query("DELETE FROM categories")
    suspend fun clearCategories()

    @androidx.room.Transaction
    suspend fun replaceAllCategories(categories: List<CategoryEntity>) {
        clearCategories()
        replaceCategories(categories)
    }
}
