package com.flsndez.contabpareja.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MonthlyControlScreen(
    state: MainUiState,
    onBack: () -> Unit,
    onChangeMonth: (Long) -> Unit,
    onSaveBudget: (String?, Map<String, String>) -> Unit,
) {
    val context = LocalContext.current
    val report = state.monthlyReport
    val categoryNames = remember(state.categories) { state.categories.associate { it.id to it.name } }
    var exportMessage by remember { mutableStateOf<String?>(null) }
    var editBudget by remember { mutableStateOf(false) }
    val csvLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if (uri != null && report != null) runCatching {
            ReportExporter.writeCsv(
                context,
                uri,
                ReportExporter.csv(state.selectedMonth, report, state.monthlyExpenses, categoryNames),
            )
        }.onSuccess { exportMessage = "CSV guardado correctamente." }
            .onFailure { exportMessage = "No se pudo guardar el CSV." }
    }
    val pdfLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
        if (uri != null && report != null) runCatching {
            ReportExporter.writePdf(
                context, uri, state.selectedMonth, report, state.monthlyExpenses, categoryNames,
            )
        }.onSuccess { exportMessage = "PDF guardado correctamente." }
            .onFailure { exportMessage = "No se pudo guardar el PDF." }
    }
    val month = YearMonth.parse(state.selectedMonth)
    val monthLabel = month.format(DateTimeFormatter.ofPattern("MMMM yyyy", Locale("es", "DO")))

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Control mensual") },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Volver") } },
                actions = { IconButton(onClick = { editBudget = true }) { Icon(Icons.Default.Edit, "Editar presupuesto") } },
            )
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    IconButton(onClick = { onChangeMonth(-1) }) { Icon(Icons.Default.ChevronLeft, "Mes anterior") }
                    Text(monthLabel.replaceFirstChar(Char::uppercase), style = MaterialTheme.typography.titleLarge)
                    IconButton(
                        onClick = { onChangeMonth(1) },
                        enabled = month < YearMonth.now(),
                    ) { Icon(Icons.Default.ChevronRight, "Mes siguiente") }
                }
            }
            item {
                val total = state.monthlyBudget?.total
                BudgetCard(
                    title = "Presupuesto total",
                    spent = total?.spent ?: report?.total ?: "0",
                    limit = total?.limit,
                    currency = state.monthlyBudget?.currency ?: report?.currency ?: "DOP",
                    percent = total?.usedPercent?.toFloatOrNull(),
                    exceeded = total?.exceeded == true,
                )
            }
            item { Text("Límites por categoría", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold) }
            if (state.monthlyBudget?.categories.isNullOrEmpty()) {
                item { Text("Aún no hay límites por categoría. Puedes agregarlos con el botón editar.") }
            } else {
                items(state.monthlyBudget!!.categories, key = { it.categoryId ?: it.categoryName }) { category ->
                    BudgetCard(
                        category.categoryName,
                        category.spent,
                        category.limit,
                        state.monthlyBudget.currency,
                        category.usedPercent?.toFloatOrNull(),
                        category.exceeded,
                    )
                }
            }
            item {
                Text("Exportar informe", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text("Incluye el resumen y todos los gastos aprobados del mes. Tú eliges dónde guardarlo.")
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(
                        onClick = { csvLauncher.launch("contab-${state.selectedMonth}.csv") },
                        enabled = report != null,
                        modifier = Modifier.weight(1f),
                    ) { Text("Exportar CSV") }
                    Button(
                        onClick = { pdfLauncher.launch("contab-${state.selectedMonth}.pdf") },
                        enabled = report != null,
                        modifier = Modifier.weight(1f),
                    ) { Text("Exportar PDF") }
                }
                exportMessage?.let { Text(it, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 8.dp)) }
            }
        }
    }
    if (editBudget) {
        BudgetEditDialog(
            state = state,
            onDismiss = { editBudget = false },
            onSave = { total, categories -> editBudget = false; onSaveBudget(total, categories) },
        )
    }
}

@Composable
private fun BudgetCard(
    title: String,
    spent: String,
    limit: String?,
    currency: String,
    percent: Float?,
    exceeded: Boolean,
) {
    val accent = if (exceeded) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
    Card(colors = CardDefaults.cardColors(containerColor = accent.copy(alpha = .09f))) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("$spent $currency gastados" + (limit?.let { " de $it $currency" } ?: " · sin límite"))
            if (limit != null) {
                Spacer(Modifier.height(10.dp))
                LinearProgressIndicator(
                    progress = { ((percent ?: 0f) / 100f).coerceIn(0f, 1f) },
                    color = accent,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(if (exceeded) "Límite superado" else "${percent ?: 0f}% utilizado", color = accent)
            }
        }
    }
}

@Composable
private fun BudgetEditDialog(
    state: MainUiState,
    onDismiss: () -> Unit,
    onSave: (String?, Map<String, String>) -> Unit,
) {
    var total by remember { mutableStateOf(state.monthlyBudget?.total?.limit.orEmpty()) }
    var limits by remember(state.monthlyBudget, state.categories) {
        mutableStateOf(
            state.monthlyBudget?.categories.orEmpty()
                .filter { it.categoryId != null && it.limit != null }
                .associate { it.categoryId!! to it.limit!! },
        )
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Presupuesto de ${state.selectedMonth}") },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    OutlinedTextField(
                        value = total,
                        onValueChange = { total = monetaryInput(it) },
                        label = { Text("Límite total (opcional)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        singleLine = true,
                    )
                }
                items(state.categories, key = { it.id }) { category ->
                    OutlinedTextField(
                        value = limits[category.id].orEmpty(),
                        onValueChange = { value -> limits = limits + (category.id to monetaryInput(value)) },
                        label = { Text(category.name) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        singleLine = true,
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { onSave(total.ifBlank { null }, limits.filterValues { it.isNotBlank() }) },
                enabled = !state.busy,
            ) { Text("Guardar") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancelar") } },
    )
}

private fun monetaryInput(value: String): String {
    val normalized = value.replace(',', '.').filter { it.isDigit() || it == '.' }
    val parts = normalized.split('.', limit = 2)
    return if (parts.size == 1) parts[0].take(12) else "${parts[0].take(12)}.${parts[1].take(2)}"
}
