package com.flsndez.contabpareja.notifications

import android.annotation.SuppressLint
import android.app.PendingIntent
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.flsndez.contabpareja.ContabApplication
import com.flsndez.contabpareja.MainActivity
import com.flsndez.contabpareja.R
import com.flsndez.contabpareja.sync.SyncWorker
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

@SuppressLint("MissingFirebaseInstanceTokenRefresh") // FID API replaces deprecated onNewToken.
class ContabMessagingService : FirebaseMessagingService() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onRegistered(installationId: String) {
        val container = (application as ContabApplication).container
        serviceScope.launch {
            if (container.authRepository.restoreSession()) {
                runCatching { container.deviceRepository.register(installationId) }
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        SyncWorker.enqueue(this)
        val title = when (message.data["event_type"]) {
            "expense.requested" -> "Nueva solicitud de gasto"
            "expense.approved" -> "Gasto aprobado"
            "expense.rejected" -> "Solicitud rechazada"
            "expense.cancelled" -> "Solicitud cancelada"
            else -> "Contab Pareja"
        }
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, ContabApplication.NOTIFICATION_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText("Abre la aplicación para revisar los detalles.")
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .build()
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return
        runCatching {
            NotificationManagerCompat.from(this).notify(
                message.messageId?.hashCode() ?: System.currentTimeMillis().toInt(),
                notification,
            )
        }
    }
}
