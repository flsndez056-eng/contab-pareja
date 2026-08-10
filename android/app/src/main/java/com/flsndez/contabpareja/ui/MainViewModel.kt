package com.flsndez.contabpareja.ui

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.flsndez.contabpareja.ContabApplication
import com.flsndez.contabpareja.data.local.CategoryEntity
import com.flsndez.contabpareja.data.local.ExpenseRequestEntity
import com.flsndez.contabpareja.data.remote.CoupleHistoryItemDto
import com.flsndez.contabpareja.data.remote.CoupleStateDto
import com.flsndez.contabpareja.data.remote.CategoryBudgetInputDto
import com.flsndez.contabpareja.data.remote.CreateExpenseBody
import com.flsndez.contabpareja.data.remote.InvitationDto
import com.flsndez.contabpareja.data.remote.InvitationPreviewDto
import com.flsndez.contabpareja.data.remote.MonthlyBudgetDto
import com.flsndez.contabpareja.data.remote.MonthlyBudgetUpdateBody
import com.flsndez.contabpareja.data.remote.ReportSummaryDto
import com.flsndez.contabpareja.data.remote.UserDto
import com.google.firebase.messaging.FirebaseMessaging
import java.time.Instant
import java.time.YearMonth
import java.time.ZoneId
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

enum class AppScreen {
    AUTH,
    FORGOT_PASSWORD,
    RESET_PASSWORD,
    COUPLE_SETUP,
    INVITE_PREVIEW,
    RELATIONSHIP_HISTORY,
    HOME,
    CREATE_EXPENSE,
    EXPENSE_HISTORY,
    ACCOUNT_SECURITY,
    MONTHLY_CONTROL,
}

internal fun accountActionPath(scheme: String?, host: String?, path: String?): String? {
    val actionPath = when {
        scheme == "contabpareja" && host == "auth" -> path
        scheme == "https" && host == "contab.siptrapollo.online" &&
            path?.startsWith("/auth/") == true -> path.removePrefix("/auth")
        else -> null
    }
    return actionPath?.takeIf { it in setOf("/reset-password", "/verify-email") }
}

internal fun isInvitationLink(scheme: String?, host: String?, path: String?): Boolean =
    (scheme == "contabpareja" && host == "invite") ||
        (scheme == "https" && host == "contab.siptrapollo.online" && path == "/invite")

data class MainUiState(
    val screen: AppScreen = AppScreen.AUTH,
    val loading: Boolean = true,
    val busy: Boolean = false,
    val user: UserDto? = null,
    val coupleState: CoupleStateDto? = null,
    val requests: List<ExpenseRequestEntity> = emptyList(),
    val categories: List<CategoryEntity> = emptyList(),
    val report: ReportSummaryDto? = null,
    val selectedMonth: String = YearMonth.now().toString(),
    val monthlyBudget: MonthlyBudgetDto? = null,
    val monthlyReport: ReportSummaryDto? = null,
    val monthlyExpenses: List<ExpenseRequestEntity> = emptyList(),
    val expenseHistory: List<ExpenseRequestEntity> = emptyList(),
    val historyReport: ReportSummaryDto? = null,
    val historyPeriodDays: Int = 90,
    val historyStatus: String? = null,
    val historySearch: String = "",
    val historyCategoryId: String? = null,
    val lastSyncedAt: String? = null,
    val invitation: InvitationDto? = null,
    val pendingInviteToken: String = "",
    val invitePreview: InvitationPreviewDto? = null,
    val coupleHistory: List<CoupleHistoryItemDto> = emptyList(),
    val resetToken: String = "",
    val passwordResetRequestSent: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
)

internal fun shouldPreservePasswordReset(screen: AppScreen): Boolean =
    screen == AppScreen.RESET_PASSWORD

internal fun signedOutStateAfterBootstrap(current: MainUiState): MainUiState =
    if (shouldPreservePasswordReset(current.screen)) {
        current.copy(loading = false, busy = false)
    } else {
        MainUiState(
            loading = false,
            pendingInviteToken = current.pendingInviteToken,
            notice = current.notice,
        )
    }

internal fun passwordResetRequestSucceeded(
    current: MainUiState,
    message: String,
): MainUiState = current.copy(
    passwordResetRequestSent = true,
    notice = message,
)

internal fun passwordResetSucceeded(): MainUiState = MainUiState(
    screen = AppScreen.AUTH,
    loading = false,
    notice = "Contraseña actualizada. Ya puedes iniciar sesión.",
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
        val storedInvite = container.authRepository.pendingInviteToken().orEmpty()
        if (_state.value.pendingInviteToken.isBlank() && storedInvite.isNotBlank()) {
            _state.update { it.copy(pendingInviteToken = storedInvite) }
        }
        val restored = container.authRepository.restoreSession()
        if (shouldPreservePasswordReset(_state.value.screen)) {
            _state.update { it.copy(loading = false) }
            return@launchTask
        }
        if (!restored) {
            _state.update(::signedOutStateAfterBootstrap)
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

    fun showAuth() = _state.update {
        MainUiState(
            screen = AppScreen.AUTH,
            loading = false,
            pendingInviteToken = it.pendingInviteToken,
            notice = it.notice,
        )
    }

    fun showForgotPassword() = _state.update {
        it.copy(
            screen = AppScreen.FORGOT_PASSWORD,
            passwordResetRequestSent = false,
            error = null,
            notice = null,
        )
    }

    fun showResetPassword(token: String = "") = _state.update {
        it.copy(
            screen = AppScreen.RESET_PASSWORD,
            loading = false,
            resetToken = token,
            passwordResetRequestSent = false,
            error = null,
            notice = null,
        )
    }

    fun requestPasswordReset(email: String) = launchTask {
        val message = container.authRepository.forgotPassword(email)
        _state.update { passwordResetRequestSucceeded(it, message) }
    }

    fun resetPassword(token: String, newPassword: String) = launchTask {
        container.authRepository.resetPassword(token, newPassword)
        _state.value = passwordResetSucceeded()
    }

    fun handleDeepLink(uri: Uri?) {
        val safeUri = uri ?: return
        val token = safeUri.getQueryParameter("token")?.trim().orEmpty()
        if (token.isBlank()) return
        if (isInvitationLink(safeUri.scheme, safeUri.host, safeUri.path)) {
            container.authRepository.rememberPendingInvite(token)
            _state.update {
                it.copy(
                    pendingInviteToken = token,
                    loading = it.loading && it.user == null,
                    notice = if (it.user == null) {
                        "Inicia sesión o crea una cuenta para revisar la invitación."
                    } else {
                        it.notice
                    },
                )
            }
            if (_state.value.user != null) {
                launchTask { loadAuthenticatedState() }
            }
            return
        }
        when (accountActionPath(safeUri.scheme, safeUri.host, safeUri.path)) {
            "/reset-password" -> showResetPassword(token)
            "/verify-email" -> confirmEmail(token)
        }
    }

    fun showAccountSecurity() = _state.update {
        it.copy(screen = AppScreen.ACCOUNT_SECURITY, error = null)
    }

    fun closeAccountSecurity() = _state.update {
        it.copy(screen = destinationForCurrentRelationship(it))
    }

    fun requestEmailVerification() = launchTask {
        val message = container.accountRepository.requestEmailVerification()
        _state.update { it.copy(notice = message) }
    }

    fun confirmEmail(token: String) = launchTask {
        val user = container.authRepository.confirmEmail(token)
        _state.update {
            it.copy(user = if (it.user?.id == user.id) user else it.user, notice = "Correo verificado.")
        }
        if (_state.value.user?.id == user.id) loadAuthenticatedState()
    }

    fun changePassword(currentPassword: String, newPassword: String) = launchTask {
        val response = container.accountRepository.changePassword(currentPassword, newPassword)
        container.authRepository.accept(response)
        _state.update {
            it.copy(user = response.user, notice = "Contraseña actualizada y sesiones anteriores cerradas.")
        }
    }

    fun revokeAllSessions(password: String) = launchTask {
        val response = container.accountRepository.revokeAllSessions(password)
        container.authRepository.accept(response)
        _state.update {
            it.copy(user = response.user, notice = "Las demás sesiones fueron cerradas.")
        }
    }

    fun createCouple(name: String) = launchTask {
        val couple = container.coupleRepository.create(name)
        val invitation = container.coupleRepository.invite()
        _state.update {
            it.copy(coupleState = couple, invitation = invitation, screen = AppScreen.HOME)
        }
        refreshData()
    }

    fun joinCouple(code: String) = launchTask {
        val couple = container.coupleRepository.joinCode(code)
        container.authRepository.clearPendingInvite()
        _state.update {
            it.copy(
                coupleState = couple,
                pendingInviteToken = "",
                invitePreview = null,
                screen = AppScreen.HOME,
            )
        }
        refreshData()
    }

    fun createInvitation() = launchTask {
        val invitation = container.coupleRepository.invite()
        _state.update { it.copy(invitation = invitation) }
    }

    fun acceptInvitation() = launchTask {
        val token = _state.value.pendingInviteToken.ifBlank {
            error("La invitación ya no está disponible.")
        }
        val couple = container.coupleRepository.joinToken(token)
        container.authRepository.clearPendingInvite()
        _state.update {
            it.copy(
                coupleState = couple,
                pendingInviteToken = "",
                invitePreview = null,
                screen = AppScreen.HOME,
                notice = "Ya estás conectado con tu pareja.",
            )
        }
        refreshData()
    }

    fun declineInvitation() {
        container.authRepository.clearPendingInvite()
        _state.update {
            it.copy(
                pendingInviteToken = "",
                invitePreview = null,
                screen = AppScreen.COUPLE_SETUP,
                notice = "Invitación descartada.",
            )
        }
    }

    fun endCouple(password: String) = launchTask {
        container.coupleRepository.end(password)
        container.expenseRepository.clear()
        _state.update {
            it.copy(coupleState = null, report = null, invitation = null)
        }
        loadAuthenticatedState()
        _state.update { it.copy(notice = "La relación se cerró y quedó guardada en tu historial.") }
    }

    fun deleteAccount(password: String) = launchTask {
        container.accountRepository.deleteAccount(password)
        container.expenseRepository.clear()
        container.authRepository.clearAllSessionData()
        _state.value = MainUiState(
            loading = false,
            notice = "Tu cuenta fue eliminada y el correo quedó disponible para registrarte otra vez.",
        )
    }

    fun showHistory() = launchTask {
        val history = container.coupleRepository.history()
        _state.update { it.copy(coupleHistory = history, screen = AppScreen.RELATIONSHIP_HISTORY) }
    }

    fun closeHistory() = _state.update {
        it.copy(screen = destinationForCurrentRelationship(it))
    }

    fun refresh() = launchTask { refreshData() }

    fun onForeground() {
        if (state.value.user != null && state.value.coupleState?.couple != null && !state.value.busy) {
            refresh()
        }
    }

    fun showCreateExpense() = _state.update { it.copy(screen = AppScreen.CREATE_EXPENSE) }
    fun showHome() = _state.update { it.copy(screen = AppScreen.HOME) }

    fun showMonthlyControl() = loadMonthlyControl(_state.value.selectedMonth)

    fun changeMonthlyControlMonth(delta: Long) {
        val current = YearMonth.now()
        val candidate = YearMonth.parse(_state.value.selectedMonth).plusMonths(delta)
        if (candidate > current || candidate < current.minusMonths(23)) return
        loadMonthlyControl(candidate.toString())
    }

    fun saveMonthlyBudget(totalLimit: String?, categoryLimits: Map<String, String>) = launchTask {
        val month = _state.value.selectedMonth
        val body = MonthlyBudgetUpdateBody(
            totalLimit = totalLimit?.trim()?.ifBlank { null },
            categories = categoryLimits.mapNotNull { (categoryId, limit) ->
                limit.trim().takeIf { it.isNotBlank() }?.let {
                    CategoryBudgetInputDto(categoryId, it)
                }
            },
        )
        val budget = container.expenseRepository.updateMonthlyBudget(month, body)
        _state.update { it.copy(monthlyBudget = budget, notice = "Presupuesto mensual actualizado.") }
    }

    fun showExpenseHistory() = loadExpenseHistory(
        periodDays = state.value.historyPeriodDays,
        status = state.value.historyStatus,
        search = state.value.historySearch,
        categoryId = state.value.historyCategoryId,
        openScreen = true,
    )

    fun applyExpenseHistoryFilters(
        periodDays: Int,
        status: String?,
        search: String,
        categoryId: String?,
    ) = loadExpenseHistory(periodDays, status, search, categoryId, openScreen = false)

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

    private fun loadExpenseHistory(
        periodDays: Int,
        status: String?,
        search: String,
        categoryId: String?,
        openScreen: Boolean,
    ) = launchTask {
        val safePeriod = periodDays.takeIf { it in setOf(30, 90, 180, 365) } ?: 90
        val safeStatus = status?.takeIf { it == "approved" || it == "rejected" }
        val to = Instant.now().plus(1, java.time.temporal.ChronoUnit.DAYS)
        val from = Instant.now().minus(safePeriod.toLong(), java.time.temporal.ChronoUnit.DAYS)
        val (history, report) = coroutineScope {
            val historyCall = async {
                container.expenseRepository.history(
                    from = from,
                    to = to,
                    status = safeStatus,
                    search = search,
                    categoryId = categoryId,
                )
            }
            val reportCall = async { container.expenseRepository.report(from, to) }
            historyCall.await() to reportCall.await()
        }
        _state.update {
            it.copy(
                screen = if (openScreen) AppScreen.EXPENSE_HISTORY else it.screen,
                expenseHistory = history,
                historyReport = report,
                historyPeriodDays = safePeriod,
                historyStatus = safeStatus,
                historySearch = search.trim(),
                historyCategoryId = categoryId,
            )
        }
    }

    private fun loadMonthlyControl(monthValue: String) = launchTask {
        val month = YearMonth.parse(monthValue)
        val zone = runCatching {
            ZoneId.of(_state.value.coupleState?.couple?.timezone ?: "America/Santo_Domingo")
        }.getOrDefault(ZoneId.systemDefault())
        val from = month.atDay(1).atStartOfDay(zone).toInstant()
        val to = month.plusMonths(1).atDay(1).atStartOfDay(zone).toInstant()
        val (budget, report, expenses) = coroutineScope {
            val budgetCall = async { container.expenseRepository.monthlyBudget(monthValue) }
            val reportCall = async { container.expenseRepository.report(from, to) }
            val expensesCall = async {
                container.expenseRepository.history(from, to, "approved", "", null)
            }
            Triple(budgetCall.await(), reportCall.await(), expensesCall.await())
        }
        _state.update {
            it.copy(
                screen = AppScreen.MONTHLY_CONTROL,
                selectedMonth = monthValue,
                monthlyBudget = budget,
                monthlyReport = report,
                monthlyExpenses = expenses,
            )
        }
    }

    fun logout() = launchTask {
        container.authRepository.logout()
        container.expenseRepository.clear()
        _state.value = MainUiState(
            loading = false,
            pendingInviteToken = container.authRepository.pendingInviteToken().orEmpty(),
        )
    }

    fun clearError() = _state.update { it.copy(error = null) }
    fun clearNotice() = _state.update { it.copy(notice = null) }

    private suspend fun loadAuthenticatedState() {
        val user = container.accountRepository.me()
        runCatching { container.privateDiagnostics.uploadPending() }
        val couple = container.coupleRepository.state()
        if (shouldPreservePasswordReset(_state.value.screen)) {
            _state.update { it.copy(loading = false) }
            return
        }
        var token = _state.value.pendingInviteToken.ifBlank {
            container.authRepository.pendingInviteToken().orEmpty()
        }
        val preview = if (token.isNotBlank() && couple.couple == null) {
            try {
                container.coupleRepository.preview(token)
            } catch (error: HttpException) {
                if (error.code() != 404) throw error
                container.authRepository.clearPendingInvite()
                token = ""
                _state.update { it.copy(notice = "La invitación venció o ya fue utilizada.") }
                null
            }
        } else {
            null
        }
        _state.update {
            it.copy(
                loading = false,
                user = user,
                coupleState = couple,
                pendingInviteToken = token,
                invitePreview = preview,
                screen = when {
                    couple.couple != null -> AppScreen.HOME
                    preview != null -> AppScreen.INVITE_PREVIEW
                    else -> AppScreen.COUPLE_SETUP
                },
                notice = if (couple.couple != null && token.isNotBlank()) {
                    "Para aceptar otra invitación, primero debes cerrar tu relación actual."
                } else {
                    it.notice
                },
            )
        }
        if (couple.couple != null) refreshData() else container.expenseRepository.clear()
        registerForPush()
    }

    private suspend fun refreshData() {
        val couple = container.coupleRepository.state()
        if (couple.couple == null) {
            container.expenseRepository.clear()
            _state.update {
                it.copy(coupleState = couple, report = null, invitation = null, screen = AppScreen.COUPLE_SETUP)
            }
            return
        }
        container.expenseRepository.sync()
        val report = runCatching { container.expenseRepository.currentMonthReport() }.getOrNull()
        _state.update {
            it.copy(
                report = report,
                coupleState = couple,
                lastSyncedAt = Instant.now().toString(),
            )
        }
    }

    private fun registerForPush() {
        runCatching { FirebaseMessaging.getInstance().register() }
    }

    private fun launchTask(showBusy: Boolean = true, block: suspend () -> Unit) {
        viewModelScope.launch {
            if (showBusy) {
                _state.update { it.copy(busy = true, error = null, notice = null) }
            }
            try {
                block()
            } catch (throwable: Throwable) {
                if (throwable is CancellationException) throw throwable
                if (throwable is HttpException && throwable.code() == 401) {
                    container.authRepository.clearSession()
                    container.expenseRepository.clear()
                    _state.value = MainUiState(
                        loading = false,
                        pendingInviteToken = container.authRepository.pendingInviteToken().orEmpty(),
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

private fun destinationForCurrentRelationship(state: MainUiState): AppScreen =
    if (state.coupleState?.couple == null) AppScreen.COUPLE_SETUP else AppScreen.HOME

private fun Throwable.userMessage(): String = when (this) {
    is HttpException -> when (code()) {
        400 -> "Revisa los datos enviados."
        403 -> "Verifica tu correo o confirma tu contraseña para continuar."
        404 -> "No encontramos el recurso solicitado."
        409 -> "La operación entra en conflicto con el estado actual. Actualiza e intenta otra vez."
        422 -> "Hay datos inválidos o incompletos."
        429 -> "Demasiados intentos. Espera un momento."
        else -> "El servidor respondió con un error (${code()})."
    }
    else -> localizedMessage ?: "No fue posible completar la operación."
}
