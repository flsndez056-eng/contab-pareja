package com.flsndez.contabpareja.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.flsndez.contabpareja.data.local.CategoryEntity
import com.flsndez.contabpareja.data.local.ExpenseRequestEntity
import com.flsndez.contabpareja.data.remote.UserDto

@Composable
fun ContabApp(viewModel: MainViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(state.error) {
        state.error?.let {
            snackbar.showSnackbar(it)
            viewModel.clearError()
        }
    }

    val showsInlineNotice = state.screen == AppScreen.AUTH ||
        state.screen == AppScreen.FORGOT_PASSWORD
    LaunchedEffect(state.notice, state.screen) {
        state.notice?.takeUnless { showsInlineNotice }?.let {
            snackbar.showSnackbar(it)
            viewModel.clearNotice()
        }
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                state.loading -> LoadingScreen()
                state.screen == AppScreen.AUTH -> AuthScreen(
                    busy = state.busy,
                    notice = state.notice,
                    onLogin = viewModel::login,
                    onRegister = viewModel::register,
                    onForgotPassword = viewModel::showForgotPassword,
                )
                state.screen == AppScreen.FORGOT_PASSWORD -> ForgotPasswordScreen(
                    busy = state.busy,
                    notice = state.notice,
                    requestSent = state.passwordResetRequestSent,
                    onRequest = viewModel::requestPasswordReset,
                    onHaveCode = { viewModel.showResetPassword() },
                    onBack = viewModel::showAuth,
                )
                state.screen == AppScreen.RESET_PASSWORD -> ResetPasswordScreen(
                    initialToken = state.resetToken,
                    busy = state.busy,
                    onSubmit = viewModel::resetPassword,
                    onBack = viewModel::showAuth,
                )
                state.screen == AppScreen.COUPLE_SETUP -> CoupleSetupScreen(
                    busy = state.busy,
                    onCreate = viewModel::createCouple,
                    onJoin = viewModel::joinCouple,
                    onLogout = viewModel::logout,
                    onSecurity = viewModel::showAccountSecurity,
                )
                state.screen == AppScreen.CREATE_EXPENSE -> CreateExpenseScreen(
                    categories = state.categories,
                    currency = state.coupleState?.couple?.defaultCurrency ?: "DOP",
                    busy = state.busy,
                    onBack = viewModel::showHome,
                    onSubmit = viewModel::createExpense,
                )
                state.screen == AppScreen.ACCOUNT_SECURITY -> AccountSecurityScreen(
                    user = state.user,
                    busy = state.busy,
                    onRequestVerification = viewModel::requestEmailVerification,
                    onConfirmEmail = viewModel::confirmEmail,
                    onChangePassword = viewModel::changePassword,
                    onRevokeAllSessions = viewModel::revokeAllSessions,
                    onBack = viewModel::closeAccountSecurity,
                )
                else -> HomeScreen(
                    state = state,
                    onRefresh = viewModel::refresh,
                    onInvite = viewModel::createInvitation,
                    onCreateExpense = viewModel::showCreateExpense,
                    onDecide = viewModel::decide,
                    onCancel = viewModel::cancel,
                    onLogout = viewModel::logout,
                    onSecurity = viewModel::showAccountSecurity,
                )
            }
            if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth().align(Alignment.TopCenter))
        }
    }
}

@Composable
private fun LoadingScreen() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator()
            Spacer(Modifier.height(16.dp))
            Text("Preparando tus cuentas…")
        }
    }
}

@Composable
private fun AuthScreen(
    busy: Boolean,
    notice: String?,
    onLogin: (String, String) -> Unit,
    onRegister: (String, String, String) -> Unit,
    onForgotPassword: () -> Unit,
) {
    var registering by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val valid = email.contains('@') && password.isNotBlank() &&
        (!registering || (name.trim().length >= 2 && password.length >= 12))

    Column(
        Modifier.fillMaxSize().padding(28.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Contab Pareja", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
        Text(
            "Cada gasto importante, decidido entre los dos.",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.secondary,
        )
        notice?.let {
            Spacer(Modifier.height(20.dp))
            SuccessMessage(it)
        }
        Spacer(Modifier.height(32.dp))
        if (registering) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Tu nombre") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
        }
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Correo electrónico") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Contraseña") },
            supportingText = if (registering) ({ Text("Mínimo 12 caracteres") }) else null,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(20.dp))
        Button(
            onClick = {
                if (registering) onRegister(name, email, password) else onLogin(email, password)
            },
            enabled = valid && !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (registering) "Crear cuenta" else "Entrar") }
        TextButton(
            onClick = { registering = !registering },
            enabled = !busy,
            modifier = Modifier.align(Alignment.CenterHorizontally),
        ) {
            Text(if (registering) "Ya tengo una cuenta" else "Crear una cuenta nueva")
        }
        if (!registering) {
            TextButton(
                onClick = onForgotPassword,
                enabled = !busy,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            ) { Text("Olvidé mi contraseña") }
        }
    }
}

@Composable
private fun ForgotPasswordScreen(
    busy: Boolean,
    notice: String?,
    requestSent: Boolean,
    onRequest: (String) -> Unit,
    onHaveCode: () -> Unit,
    onBack: () -> Unit,
) {
    var email by remember { mutableStateOf("") }
    LaunchedEffect(requestSent) {
        if (requestSent) email = ""
    }
    Column(
        Modifier.fillMaxSize().padding(28.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Recupera tu acceso", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("Te enviaremos un código temporal si el correo está registrado.")
        if (requestSent && notice != null) {
            Spacer(Modifier.height(20.dp))
            SuccessMessage(notice)
        }
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Correo electrónico") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { onRequest(email) },
            enabled = email.contains('@') && !busy,
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
        ) { Text(if (requestSent) "Enviar de nuevo" else "Enviar instrucciones") }
        TextButton(onClick = onHaveCode, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            Text("Ya tengo un código")
        }
        TextButton(onClick = onBack, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            Text("Volver al inicio de sesión")
        }
    }
}

@Composable
private fun SuccessMessage(message: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Default.Check, contentDescription = null)
            Spacer(Modifier.width(12.dp))
            Text(message, modifier = Modifier.weight(1f), fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ResetPasswordScreen(
    initialToken: String,
    busy: Boolean,
    onSubmit: (String, String) -> Unit,
    onBack: () -> Unit,
) {
    var token by remember(initialToken) { mutableStateOf(initialToken) }
    var password by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    val valid = token.length >= 32 && password.length >= 12 && password == confirmation

    Column(
        Modifier.fillMaxSize().padding(28.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Nueva contraseña", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("El código solo puede utilizarse una vez.")
        Spacer(Modifier.height(20.dp))
        OutlinedTextField(
            value = token,
            onValueChange = { token = it.trim() },
            label = { Text("Código de recuperación") },
            minLines = 2,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        PasswordField(password, { password = it }, "Contraseña nueva")
        Spacer(Modifier.height(12.dp))
        PasswordField(confirmation, { confirmation = it }, "Repetir contraseña")
        Button(
            onClick = { onSubmit(token, password) },
            enabled = valid && !busy,
            modifier = Modifier.fillMaxWidth().padding(top = 18.dp),
        ) { Text("Cambiar contraseña") }
        TextButton(onClick = onBack, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            Text("Cancelar")
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AccountSecurityScreen(
    user: UserDto?,
    busy: Boolean,
    onRequestVerification: () -> Unit,
    onConfirmEmail: (String) -> Unit,
    onChangePassword: (String, String) -> Unit,
    onRevokeAllSessions: (String) -> Unit,
    onBack: () -> Unit,
) {
    var verificationCode by remember { mutableStateOf("") }
    var currentPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    var revokePassword by remember { mutableStateOf("") }

    Scaffold(topBar = { TopAppBar(title = { Text("Seguridad de la cuenta") }) }) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(20.dp).verticalScroll(rememberScrollState()),
        ) {
            Text(user?.email.orEmpty(), style = MaterialTheme.typography.titleMedium)
            Text(if (user?.emailVerified == true) "Correo verificado" else "Correo pendiente de verificar")
            if (user?.emailVerified != true) {
                FilledTonalButton(
                    onClick = onRequestVerification,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                ) { Text("Enviar código de verificación") }
                OutlinedTextField(
                    value = verificationCode,
                    onValueChange = { verificationCode = it.trim() },
                    label = { Text("Código de verificación") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                )
                Button(
                    onClick = { onConfirmEmail(verificationCode) },
                    enabled = verificationCode.length >= 32 && !busy,
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                ) { Text("Confirmar correo") }
            }

            HorizontalDivider(Modifier.padding(vertical = 24.dp))
            Text("Cambiar contraseña", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            PasswordField(currentPassword, { currentPassword = it }, "Contraseña actual")
            Spacer(Modifier.height(10.dp))
            PasswordField(newPassword, { newPassword = it }, "Contraseña nueva")
            Spacer(Modifier.height(10.dp))
            PasswordField(confirmation, { confirmation = it }, "Repetir contraseña")
            Button(
                onClick = { onChangePassword(currentPassword, newPassword) },
                enabled = currentPassword.isNotBlank() && newPassword.length >= 12 &&
                    newPassword == confirmation && !busy,
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            ) { Text("Actualizar contraseña") }

            HorizontalDivider(Modifier.padding(vertical = 24.dp))
            Text("Cerrar otras sesiones", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Los demás teléfonos deberán iniciar sesión otra vez.")
            PasswordField(revokePassword, { revokePassword = it }, "Confirma tu contraseña")
            OutlinedButton(
                onClick = { onRevokeAllSessions(revokePassword) },
                enabled = revokePassword.isNotBlank() && !busy,
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            ) { Text("Cerrar las demás sesiones") }
            TextButton(onClick = onBack, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                Text("Volver")
            }
        }
    }
}

@Composable
private fun PasswordField(value: String, onValueChange: (String) -> Unit, label: String) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        supportingText = { Text("Mínimo 12 caracteres") },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun CoupleSetupScreen(
    busy: Boolean,
    onCreate: (String) -> Unit,
    onJoin: (String) -> Unit,
    onLogout: () -> Unit,
    onSecurity: () -> Unit,
) {
    var coupleName by remember { mutableStateOf("Nuestra pareja") }
    var code by remember { mutableStateOf("") }
    Column(
        Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Conecta a tu pareja", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("Crea un espacio nuevo o introduce el código que recibiste.")
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(
            value = coupleName,
            onValueChange = { coupleName = it },
            label = { Text("Nombre del espacio") },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { onCreate(coupleName) },
            enabled = coupleName.trim().length >= 2 && !busy,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        ) { Text("Crear espacio") }
        Row(Modifier.fillMaxWidth().padding(vertical = 24.dp), verticalAlignment = Alignment.CenterVertically) {
            HorizontalDivider(Modifier.weight(1f))
            Text("  o  ")
            HorizontalDivider(Modifier.weight(1f))
        }
        OutlinedTextField(
            value = code,
            onValueChange = { code = it.uppercase().take(9) },
            label = { Text("Código de invitación") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedButton(
            onClick = { onJoin(code) },
            enabled = code.length == 9 && !busy,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        ) { Text("Unirme") }
        TextButton(onClick = onLogout, modifier = Modifier.align(Alignment.CenterHorizontally)) {
            Text("Cerrar sesión")
        }
        TextButton(onClick = onSecurity, modifier = Modifier.align(Alignment.CenterHorizontally)) {
            Text("Seguridad de la cuenta")
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HomeScreen(
    state: MainUiState,
    onRefresh: () -> Unit,
    onInvite: () -> Unit,
    onCreateExpense: () -> Unit,
    onDecide: (String, Boolean, String?) -> Unit,
    onCancel: (String) -> Unit,
    onLogout: () -> Unit,
    onSecurity: () -> Unit,
) {
    var rejectTarget by remember { mutableStateOf<ExpenseRequestEntity?>(null) }
    val userId = state.user?.id
    val pendingForMe = state.requests.count { it.status == "pending" && it.requestedBy != userId }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Column { Text(state.coupleState?.couple?.name ?: "Contab Pareja"); Text("Hola, ${state.user?.displayName.orEmpty()}", style = MaterialTheme.typography.labelMedium) } },
                actions = {
                    IconButton(onClick = onRefresh, enabled = !state.busy) { Icon(Icons.Default.Refresh, "Actualizar") }
                    IconButton(onClick = onSecurity) { Icon(Icons.Default.Settings, "Seguridad") }
                    IconButton(onClick = onLogout) { Icon(Icons.AutoMirrored.Filled.Logout, "Cerrar sesión") }
                },
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onCreateExpense,
                icon = { Icon(Icons.Default.Add, null) },
                text = { Text("Solicitar gasto") },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 100.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                SummaryCard(state, pendingForMe)
            }
            if ((state.coupleState?.members?.size ?: 0) < 2) {
                item {
                    InvitationCard(state.invitationCode, onInvite)
                }
            }
            item {
                Text("Actividad", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            }
            if (state.requests.isEmpty()) {
                item {
                    Text(
                        "Todavía no hay solicitudes. El primer gasto aparecerá aquí.",
                        modifier = Modifier.fillMaxWidth().padding(24.dp),
                        textAlign = TextAlign.Center,
                    )
                }
            }
            items(state.requests, key = { it.id }) { request ->
                ExpenseRequestCard(
                    request = request,
                    incoming = request.requestedBy != userId,
                    onApprove = { onDecide(request.id, true, null) },
                    onReject = { rejectTarget = request },
                    onCancel = { onCancel(request.id) },
                )
            }
        }
    }

    rejectTarget?.let { request ->
        RejectDialog(
            onDismiss = { rejectTarget = null },
            onConfirm = { reason ->
                onDecide(request.id, false, reason)
                rejectTarget = null
            },
        )
    }
}

@Composable
private fun SummaryCard(state: MainUiState, pendingForMe: Int) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.fillMaxWidth().padding(20.dp)) {
            Text("Resumen de los últimos 31 días", style = MaterialTheme.typography.titleMedium)
            Text(
                money(state.report?.total ?: "0", state.report?.currency ?: "DOP"),
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold,
            )
            Text("${state.report?.expenseCount ?: 0} gastos aprobados · $pendingForMe esperando tu decisión")
        }
    }
}

@Composable
private fun InvitationCard(code: String?, onInvite: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)) {
        Column(Modifier.fillMaxWidth().padding(18.dp)) {
            Text("Falta conectar a tu pareja", fontWeight = FontWeight.Bold)
            Text("Genera un código temporal y compártelo de forma privada.")
            if (code == null) {
                FilledTonalButton(onClick = onInvite, modifier = Modifier.padding(top = 10.dp)) {
                    Text("Generar código")
                }
            } else {
                Text(code, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 10.dp))
            }
        }
    }
}

@Composable
private fun ExpenseRequestCard(
    request: ExpenseRequestEntity,
    incoming: Boolean,
    onApprove: () -> Unit,
    onReject: () -> Unit,
    onCancel: () -> Unit,
) {
    Card {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(request.description, modifier = Modifier.weight(1f), fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.width(12.dp))
                Text(money(request.amount, request.currency), fontWeight = FontWeight.Bold)
            }
            request.merchant?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            Text(
                "${if (incoming) "Recibida" else "Enviada"} · ${statusLabel(request.status)} · ${if (request.paymentSource == "joint") "Cuenta conjunta" else "Cuenta personal"}",
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.labelMedium,
            )
            request.rejectionReason?.let { Text("Motivo: $it", color = MaterialTheme.colorScheme.error) }
            if (request.status == "pending") {
                Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.End) {
                    if (incoming) {
                        OutlinedButton(onClick = onReject) {
                            Icon(Icons.Default.Close, null)
                            Text("Rechazar")
                        }
                        Spacer(Modifier.width(8.dp))
                        Button(onClick = onApprove) {
                            Icon(Icons.Default.Check, null)
                            Text("Aprobar")
                        }
                    } else {
                        TextButton(onClick = onCancel) { Text("Cancelar solicitud") }
                    }
                }
            }
        }
    }
}

@Composable
private fun RejectDialog(onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    var reason by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Rechazar solicitud") },
        text = {
            OutlinedTextField(
                value = reason,
                onValueChange = { reason = it },
                label = { Text("Motivo obligatorio") },
                minLines = 2,
            )
        },
        confirmButton = {
            Button(onClick = { onConfirm(reason) }, enabled = reason.isNotBlank()) { Text("Rechazar") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Volver") } },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreateExpenseScreen(
    categories: List<CategoryEntity>,
    currency: String,
    busy: Boolean,
    onBack: () -> Unit,
    onSubmit: (String, String, String, String?, String) -> Unit,
) {
    var amount by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var merchant by remember { mutableStateOf("") }
    var source by remember { mutableStateOf("personal") }
    var selectedCategory by remember { mutableStateOf<CategoryEntity?>(null) }
    var categoryExpanded by remember { mutableStateOf(false) }
    val inputValid = ExpenseInputValidator.isValid(amount, description)

    Scaffold(
        topBar = { TopAppBar(title = { Text("Nueva solicitud") }) },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(20.dp).verticalScroll(rememberScrollState()),
        ) {
            Text("Tu pareja tendrá que aprobarla antes de que sea un gasto.")
            Spacer(Modifier.height(20.dp))
            OutlinedTextField(
                value = amount,
                onValueChange = { amount = it.filter { char -> char.isDigit() || char == '.' || char == ',' }.replace(',', '.') },
                label = { Text("Monto ($currency)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("¿En qué se gastará?") },
                minLines = 2,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = merchant,
                onValueChange = { merchant = it },
                label = { Text("Comercio (opcional)") },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            ExposedDropdownMenuBox(expanded = categoryExpanded, onExpandedChange = { categoryExpanded = it }) {
                OutlinedTextField(
                    value = selectedCategory?.name ?: "Sin categoría",
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Categoría") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(categoryExpanded) },
                    modifier = Modifier
                        .menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable)
                        .fillMaxWidth(),
                )
                ExposedDropdownMenu(expanded = categoryExpanded, onDismissRequest = { categoryExpanded = false }) {
                    DropdownMenuItem(text = { Text("Sin categoría") }, onClick = { selectedCategory = null; categoryExpanded = false })
                    categories.forEach { category ->
                        DropdownMenuItem(text = { Text(category.name) }, onClick = { selectedCategory = category; categoryExpanded = false })
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            Text("Origen del pago", fontWeight = FontWeight.SemiBold)
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = source == "personal", onClick = { source = "personal" })
                Text("Personal")
                Spacer(Modifier.width(16.dp))
                RadioButton(selected = source == "joint", onClick = { source = "joint" })
                Text("Conjunta")
            }
            Spacer(Modifier.height(24.dp))
            Button(
                onClick = { onSubmit(amount, description, merchant, selectedCategory?.id, source) },
                enabled = inputValid && !busy,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Enviar para aprobación") }
            TextButton(onClick = onBack, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("Cancelar") }
        }
    }
}

private fun statusLabel(status: String): String = when (status) {
    "pending" -> "Pendiente"
    "approved" -> "Aprobado"
    "rejected" -> "Rechazado"
    "cancelled" -> "Cancelado"
    "expired" -> "Vencido"
    else -> status
}

private fun money(value: String, currency: String): String {
    val normalized = value.toBigDecimalOrNull()?.setScale(2)?.toPlainString() ?: value
    return "$currency $normalized"
}
