package com.flsndez.contabpareja

import android.content.Context
import androidx.room.Room
import com.flsndez.contabpareja.core.AuthInterceptor
import com.flsndez.contabpareja.core.SecureSessionStore
import com.flsndez.contabpareja.core.SessionMemory
import com.flsndez.contabpareja.core.TokenAuthenticator
import com.flsndez.contabpareja.data.local.ContabDatabase
import com.flsndez.contabpareja.data.remote.ContabApi
import com.flsndez.contabpareja.data.remote.PublicApi
import com.flsndez.contabpareja.data.repository.AuthRepository
import com.flsndez.contabpareja.data.repository.AccountRepository
import com.flsndez.contabpareja.data.repository.CoupleRepository
import com.flsndez.contabpareja.data.repository.DeviceRepository
import com.flsndez.contabpareja.data.repository.ExpenseRepository
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AppContainer(context: Context) {
    private val session = SessionMemory()
    private val secureStore = SecureSessionStore(context)
    private val logging = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BASIC
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
        redactHeader("Authorization")
    }

    private val publicClient = OkHttpClient.Builder()
        .addInterceptor(logging)
        .build()

    private val publicApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(publicClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(PublicApi::class.java)

    val authRepository = AuthRepository(publicApi, secureStore, session)

    private val authenticatedClient = publicClient.newBuilder()
        .addInterceptor(AuthInterceptor(session))
        .authenticator(TokenAuthenticator(session, authRepository))
        .build()

    private val api = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(authenticatedClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(ContabApi::class.java)

    private val database = Room.databaseBuilder(
        context,
        ContabDatabase::class.java,
        "contab-pareja.db",
    ).build()

    val coupleRepository = CoupleRepository(api, publicApi)
    val accountRepository = AccountRepository(api)
    val expenseRepository = ExpenseRepository(api, database.dao())
    val deviceRepository = DeviceRepository(context, api)
}
