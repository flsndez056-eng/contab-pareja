package com.flsndez.contabpareja.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val ContabColors = lightColorScheme(
    primary = Color(0xFF102A43),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD9EAF7),
    onPrimaryContainer = Color(0xFF071A2B),
    secondary = Color(0xFFB7791F),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFFFE6B0),
    background = Color(0xFFFFF9F0),
    surface = Color(0xFFFFFCF7),
    surfaceVariant = Color(0xFFF2ECE3),
    error = Color(0xFFB3261E),
)

@Composable
fun ContabTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = ContabColors, content = content)
}
