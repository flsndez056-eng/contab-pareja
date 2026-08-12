package com.flsndez.contabpareja.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
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
import com.flsndez.contabpareja.core.AppLockMode

@Composable
fun AppLockGate(
    mode: AppLockMode,
    onPin: (String) -> Boolean,
    onBiometric: () -> Unit,
) {
    var pin by remember { mutableStateOf("") }
    var invalid by remember { mutableStateOf(false) }
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("DúoCuenta", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
        Text(
            "Tus finanzas están protegidas",
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
        )
        if (mode == AppLockMode.PIN) {
            OutlinedTextField(
                value = pin,
                onValueChange = { pin = it.filter(Char::isDigit).take(8); invalid = false },
                label = { Text("PIN") },
                isError = invalid,
                supportingText = if (invalid) ({ Text("PIN incorrecto") }) else null,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                singleLine = true,
            )
            Button(
                onClick = { invalid = !onPin(pin) },
                enabled = pin.length >= 4,
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            ) { Text("Desbloquear") }
        } else {
            Button(onClick = onBiometric, modifier = Modifier.fillMaxWidth()) {
                Text("Desbloquear con biometría")
            }
        }
    }
}

@Composable
fun AppLockSettings(
    mode: AppLockMode,
    onSetPin: (String) -> Unit,
    onEnableBiometric: () -> Unit,
    onDisable: () -> Unit,
) {
    var showPinDialog by remember { mutableStateOf(false) }
    Text("Bloqueo de la aplicación", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Text(
        when (mode) {
            AppLockMode.NONE -> "Desactivado. Puedes proteger el acceso sin enviar tu PIN al servidor."
            AppLockMode.PIN -> "Activo con PIN local. Se bloquea al dejar la app 30 segundos."
            AppLockMode.BIOMETRIC -> "Activo con biometría o credencial segura del teléfono."
        },
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    FilledTonalButton(
        onClick = onEnableBiometric,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    ) { Text("Usar biometría del teléfono") }
    OutlinedButton(
        onClick = { showPinDialog = true },
        modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
    ) { Text(if (mode == AppLockMode.PIN) "Cambiar PIN" else "Usar PIN de la app") }
    if (mode != AppLockMode.NONE) {
        TextButton(onClick = onDisable, modifier = Modifier.fillMaxWidth()) {
            Text("Desactivar bloqueo")
        }
    }
    if (showPinDialog) {
        PinSetupDialog(
            onDismiss = { showPinDialog = false },
            onSave = { onSetPin(it); showPinDialog = false },
        )
    }
}

@Composable
private fun PinSetupDialog(onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var pin by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Configurar PIN") },
        text = {
            Column {
                Text("Usa entre 4 y 8 dígitos. El PIN solo se guarda como una huella criptográfica local.")
                Spacer(Modifier.height(12.dp))
                PinField(pin, { pin = it }, "Nuevo PIN")
                Spacer(Modifier.height(8.dp))
                PinField(confirmation, { confirmation = it }, "Repetir PIN")
            }
        },
        confirmButton = {
            Button(onClick = { onSave(pin) }, enabled = pin.length >= 4 && pin == confirmation) {
                Text("Activar")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancelar") } },
    )
}

@Composable
private fun PinField(value: String, onChange: (String) -> Unit, label: String) {
    OutlinedTextField(
        value = value,
        onValueChange = { onChange(it.filter(Char::isDigit).take(8)) },
        label = { Text(label) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
        visualTransformation = PasswordVisualTransformation(),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
}
