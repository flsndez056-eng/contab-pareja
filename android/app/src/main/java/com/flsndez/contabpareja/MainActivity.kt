package com.flsndez.contabpareja

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.provider.Settings
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import androidx.core.net.toUri
import androidx.fragment.app.FragmentActivity
import com.flsndez.contabpareja.core.AppLockMode
import com.flsndez.contabpareja.core.AppLockStore
import com.flsndez.contabpareja.ui.ContabApp
import com.flsndez.contabpareja.ui.MainViewModel
import com.flsndez.contabpareja.ui.theme.ContabTheme

class MainActivity : FragmentActivity() {
    private val viewModel by viewModels<MainViewModel>()
    private var notificationsEnabled by mutableStateOf(true)
    private lateinit var appLockStore: AppLockStore
    private var lockMode by mutableStateOf(AppLockMode.NONE)
    private var appUnlocked by mutableStateOf(true)
    private var backgroundedAt: Long? = null
    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { notificationsEnabled = notificationsAreEnabled() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        appLockStore = AppLockStore(this)
        lockMode = appLockStore.mode
        appUnlocked = lockMode == AppLockMode.NONE
        enableEdgeToEdge()
        notificationsEnabled = notificationsAreEnabled()
        viewModel.handleDeepLink(intent?.data)
        setContent {
            ContabTheme {
                ContabApp(
                    viewModel = viewModel,
                    notificationsEnabled = notificationsEnabled,
                    onRequestNotifications = ::requestNotificationAccess,
                    lockMode = lockMode,
                    appUnlocked = appUnlocked,
                    onUnlockWithPin = ::unlockWithPin,
                    onUnlockWithBiometric = { authenticateBiometric { appUnlocked = true } },
                    onSetPin = ::setAppPin,
                    onEnableBiometric = ::enableBiometricLock,
                    onDisableAppLock = ::disableAppLock,
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        viewModel.handleDeepLink(intent.data)
    }

    override fun onResume() {
        super.onResume()
        notificationsEnabled = notificationsAreEnabled()
        viewModel.onForeground()
    }

    override fun onStart() {
        super.onStart()
        val elapsed = backgroundedAt?.let { SystemClock.elapsedRealtime() - it }
        if (lockMode != AppLockMode.NONE && elapsed != null && elapsed >= LOCK_AFTER_MILLIS) {
            appUnlocked = false
        }
    }

    override fun onStop() {
        backgroundedAt = SystemClock.elapsedRealtime()
        super.onStop()
    }

    private fun unlockWithPin(pin: String): Boolean = appLockStore.verifyPin(pin).also {
        if (it) appUnlocked = true
    }

    private fun setAppPin(pin: String) {
        appLockStore.setPin(pin)
        lockMode = AppLockMode.PIN
        appUnlocked = true
    }

    private fun enableBiometricLock() {
        authenticateBiometric {
            appLockStore.enableBiometric()
            lockMode = AppLockMode.BIOMETRIC
            appUnlocked = true
        }
    }

    private fun disableAppLock() {
        appLockStore.disable()
        lockMode = AppLockMode.NONE
        appUnlocked = true
    }

    private fun authenticateBiometric(onSuccess: () -> Unit) {
        val authenticators = BiometricManager.Authenticators.BIOMETRIC_WEAK or
            BiometricManager.Authenticators.DEVICE_CREDENTIAL
        if (BiometricManager.from(this).canAuthenticate(authenticators) !=
            BiometricManager.BIOMETRIC_SUCCESS
        ) {
            return
        }
        val prompt = BiometricPrompt(
            this,
            ContextCompat.getMainExecutor(this),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    onSuccess()
                }
            },
        )
        prompt.authenticate(
            BiometricPrompt.PromptInfo.Builder()
                .setTitle("Desbloquear Contab Pareja")
                .setSubtitle("Confirma tu identidad para proteger tus finanzas")
                .setAllowedAuthenticators(authenticators)
                .build(),
        )
    }

    private fun requestNotificationAccess() {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            val preferences = getSharedPreferences("contab_user_experience", MODE_PRIVATE)
            val requestedBefore = preferences.getBoolean("notifications_requested", false)
            if (!requestedBefore || shouldShowRequestPermissionRationale(Manifest.permission.POST_NOTIFICATIONS)) {
                preferences.edit { putBoolean("notifications_requested", true) }
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                return
            }
        }
        val settingsIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            }
        } else {
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, "package:$packageName".toUri())
        }
        startActivity(settingsIntent)
    }

    private fun notificationsAreEnabled(): Boolean =
        NotificationManagerCompat.from(this).areNotificationsEnabled() &&
            (
                Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                    ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) ==
                    PackageManager.PERMISSION_GRANTED
                )

    private companion object {
        const val LOCK_AFTER_MILLIS = 30_000L
    }
}
