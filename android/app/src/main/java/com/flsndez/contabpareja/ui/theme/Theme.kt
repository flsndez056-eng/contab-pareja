package com.flsndez.contabpareja.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.shape.RoundedCornerShape

private val ContabLightColors = lightColorScheme(
    primary = Color(0xFF5B4BDB),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE8E5FF),
    onPrimaryContainer = Color(0xFF21165D),
    secondary = Color(0xFF008EA3),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFC6F3FA),
    onSecondaryContainer = Color(0xFF00363E),
    tertiary = Color(0xFFF05A7E),
    tertiaryContainer = Color(0xFFFFD9E1),
    background = Color(0xFFF7F7FC),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFE9E9F2),
    outline = Color(0xFF777680),
    error = Color(0xFFBA1A1A),
)

private val ContabDarkColors = darkColorScheme(
    primary = Color(0xFFC8BFFF),
    onPrimary = Color(0xFF2C2175),
    primaryContainer = Color(0xFF443A93),
    onPrimaryContainer = Color(0xFFE7E1FF),
    secondary = Color(0xFF6ED8ED),
    onSecondary = Color(0xFF00363E),
    secondaryContainer = Color(0xFF004E5A),
    tertiary = Color(0xFFFFB1C3),
    background = Color(0xFF111118),
    surface = Color(0xFF191920),
    surfaceVariant = Color(0xFF45454F),
    error = Color(0xFFFFB4AB),
)

private val ContabTypography = Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.ExtraBold,
        fontSize = 34.sp,
        lineHeight = 40.sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 24.sp,
        lineHeight = 30.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 20.sp,
        lineHeight = 26.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 16.sp,
        lineHeight = 22.sp,
    ),
    bodyLarge = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 14.sp,
    ),
)

private val ContabShapes = Shapes(
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(28.dp),
)

@Composable
fun ContabTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) ContabDarkColors else ContabLightColors,
        typography = ContabTypography,
        shapes = ContabShapes,
        content = content,
    )
}
