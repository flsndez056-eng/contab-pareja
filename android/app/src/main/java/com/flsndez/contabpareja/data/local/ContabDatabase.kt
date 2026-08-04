package com.flsndez.contabpareja.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [ExpenseRequestEntity::class, CategoryEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class ContabDatabase : RoomDatabase() {
    abstract fun dao(): ContabDao
}
