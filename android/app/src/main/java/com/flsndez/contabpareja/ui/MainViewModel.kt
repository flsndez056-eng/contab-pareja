package com.flsndez.contabpareja.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.flsndez.contabpareja.ContabApplication
import com.flsndez.contabpareja.data.local.CategoryEntity
import com.flsndez.contabpareja.data.local.ExpenseRequestEntity
import com.flsndez.contabpareja.data.remote.CoupleStateDto
import com.flsndez.contabpareja.data.remote.CreateExpenseBody
import com.flsndez.contabpareja.data.remote.ReportSummaryDto
import com.flsndez.contabpareja.data.remote.UserDto
import com.google.firebase.messaging.FirebaseMessaging
import java.time.Instant
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

enum class AppScreen { AUTH, COUPLE_SETUP, HOME, CREATE_EXPENSE }

data class MainUiState(
    val screen: AppScreen = AppScreen.AUTH,
    val loading: Boolean = true,
    val busy: Boolean = false,
    val user: UserDto? = null,
    val coupleState: CoupleStateDto? = null,
    val requests: List<ExpenseRequestEntity> = emptyList(),
    val categories: List<CategoryEntity> = emptyList(),
    val report: ReportSummaryDto? = null,
    val invitationCode: String? = null,
    val error: String? = null,
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val container = (application as ContabApplication).container
    private val _state = MutableStateFlow(MainUiState())
    val state: StateFlow<MainUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                container.expenseRepository.requests,
                container.expenseRepository.categories,
            ) { requests, categories -> requests to categories }
                .collect { (requests, categories) ->
                    _state.update { it.copy(requests = requests, categories = categories) }
                }
        }
        bootstrap()
    }

    fun bootstrap() = launchTask(showBusy = false) {
        if (!container.authRepository.restoreSession()) {
            _state.update { MainUiState(loading = false) }
            return@launchTask
        }
        loadAuthenticatedState()
    }

    fun login(email: String, password: String) = launchTask {
        container.authRepository.login(email, password)
        loadAuthenticatedState()
    }

    fun register(name: String, email: String, password: String) = launchTask {
        container.authRepository.register(name, email, password)
        loadAuthenticatedState()
    }

    fun createCouple(name: String) = launchTask {
        val couple = container.coupleRepository.create(name)
        _state.update { it.copy(coupleState = couple, screen = AppScreen.HOME) }
        refreshData()
    }

    fun joinCouple(code: String) = launchTask {
        val couple = container.coupleRepository.join(code)
        _state.update { it.copy(coupleState = couple, screen = AppScreen.HOME) }
        refreshData()
    }

    fun createInvitation() = launchTask {
        val invitation = container.coupleRepository.invite()
        _state.update { it.copy(invitationCode = invitation.code) }
    }

    fun refresh() = launchTask { refreshData() }

    fun onForeground() {
        if (state.value.user != null && state.value.coupleState?.couple != null && !state.value.busy) {
            refresh()
        }
    }

    fun showCreateExpense() = _state.update { it.copy(screen = AppScreen.CREATE_EXPENSE) }
    fun showHome() = _state.update { it.copy(screen = AppScreen.HOME) }

    fun createExpense(
        amount: String,
        description: String,
        merchant: String,
        categoryId: String?,
        paymentSource: String,
    ) = launchTask {
        val userId = state.value.user?.id ?: error("Sesión inválida")
        val currency = state.value.coupleState?.couple?.defaultCurrency ?: "DOP"
        container.expenseRepository.create(
            CreateExpenseBody(
                amount = amount.trim(),
                currency = currency,
                description = description.trim(),
                merchant = merchant.trim().ifBlank { null },
                categoryId = categoryId,
                paymentSource = paymentSource,
                paidByUserId = if (paymentSource == "personal") userId else null,
                occurredAt = Instant.now().toString(),
            ),
        )
        _state.update { it.copy(screen = AppScreen.HOME) }
        refreshData()
    }

    fun decide(requestId: String, approve: Boolean, reason: String? = null) = launchTask {
        container.expenseRepository.decide(requestId, approve, reason)
        refreshData()
    }

    fun cancel(requestId: String) = launchTask {
        container.expenseRepository.cancel(requestId)
        refreshData()
    }

    fun logout() = launchTask {
        container.authRepository.logout()
        _state.value = MainUiState(loading = false)
    }

    fun clearError() = _state.update { it.copy(error = null) }

    private suspend fun loadAuthenticatedState() {
        val user = container.accountRepository.me()
        val couple = container.coupleRepository.state()
        _state.update {
            it.copy(
                loading = false,
                user = user,
                coupleState = couple,
                screen = if (couple.couple == null) AppScreen.COUPLE_SETUP else AppScreen.HOME,
            )
        }
        if (couple.couple != null) refreshData()
        registerForPush()
    }

    private suspend fun refreshData() {
        container.expenseRepository.sync()
        val report = runCatching { container.expenseRepository.currentMonthReport() }.getOrNull()
        val couple = container.coupleRepository.state()
        _state.update { it.copy(report = report, coupleState = couple) }
    }

    private fun registerForPush() {
        runCatching { FirebaseMessaging.getInstance().register() }
    }

    private fun launchTask(showBusy: Boolean = true, block: suspend () -> Unit) {
        viewModelScope.launch {
            if (showBusy) _state.update { it.copy(busy = true, error = null) }
            runCatching { block() }
                .onFailure { throwable ->
                    if (throwable is HttpException && throwable.code() == 401) {
                        container.authRepository.clearSession()
                        _state.value = MainUiState(
                            loading = false,
                            error = "Tu sesión venció. Inicia sesión nuevamente.",
                        )
                    } else {
                        _state.update { it.copy(error = throwable.userMessage()) }
                    }
                }
            _state.update { it.copy(loading = false, busy = false) }
        }
    }
}

private fun Throwable.userMessage(): String = when (this) {
    is HttpException -> when (code()) {
        400 -> "Revisa los datos enviados."
        403 -> "No tienes permiso para realizar esta acción."
        404 -> "No encontramos el recurso solicitado."
        409 -> "La operación entra en conflicto con el estado actual. Actualiza e intenta otra vez."
        422 -> "Hay datos inválidos o incompletos."
        429 -> "Demasiados intentos. Espera un momento."
        else -> "El servidor respondió con un error (${code()})."
    }
    else -> localizedMessage ?: "No fue posible completar la operación."
}
