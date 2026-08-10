# Contab Pareja

Aplicación móvil para que dos miembros de una pareja soliciten, aprueben y auditen gastos compartidos.

La conexión se realiza mediante enlace HTTPS de un solo uso, QR o código temporal. Cada usuario puede cerrar una relación, conservar el historial aprobado y conectar una pareja diferente. La eliminación de cuenta anonimiza la identidad y libera el correo para un registro futuro.

## Principio central

Una solicitud pendiente no es un gasto contable. Solo una decisión válida del otro miembro crea un gasto aprobado. Todas las transiciones quedan auditadas.

## Control financiero

- El inicio resume los gastos aprobados de los últimos 31 días y mantiene visibles las solicitudes pendientes.
- Cada solicitud muestra monto, categoría, comercio, origen del dinero y fechas de creación, gasto y resolución.
- El historial permite consultar hasta un año por resultado, categoría, descripción o comercio.
- Los informes suman exclusivamente gastos aprobados y desglosan cada peso entre categorías y fondos personales o conjuntos.
- Cada mes admite un límite total y límites por categoría; son alertas informativas y no alteran la regla de aprobación mutua.
- Los informes mensuales se exportan a PDF o CSV mediante el selector privado de archivos de Android.
- El acceso local puede protegerse con biometría/credencial del teléfono o un PIN que nunca sale del dispositivo.

## Componentes

- `backend/`: API FastAPI, worker de notificaciones y migraciones Alembic.
- `android/`: cliente Android nativo con Kotlin y Jetpack Compose.
- `docs/`: arquitectura, decisiones y operación.
- `compose.yaml`: entorno local reproducible.
- `compose.oci.yaml`: producción en una VM de Oracle Cloud con HTTPS automático.

## Inicio rápido

1. Copia `.env.example` a `.env` y sustituye únicamente los valores locales.
2. Ejecuta `docker compose up --build`.
3. Aplica migraciones con `docker compose exec api alembic upgrade head`.
4. Abre `http://localhost:8000/docs`.

No guardes credenciales reales en Git ni en archivos de ejemplo.

## Android

El cliente usa Kotlin, Jetpack Compose, Room, WorkManager, Retrofit y Firebase Installation IDs. En debug se conecta por defecto a producción; para usar el emulador contra un backend local pasa `-PCONTAB_DEBUG_API_BASE_URL=http://10.0.2.2:8000/`.

1. Abre `android/` en Android Studio.
2. Para notificaciones, usa la app Android ya registrada en el proyecto Firebase `contab-pareja` y coloca `google-services.json` en `android/app/`.
3. Ejecuta `./gradlew testDebugUnitTest lintDebug assembleDebug`.
4. Para instalar una compilación de pruebas en un teléfono real, genera el APK debug; ya apunta a `https://contab.siptrapollo.online/`.
5. Para release pasa `-PCONTAB_API_BASE_URL=https://contab.siptrapollo.online/`.

## Producción

- Arquitectura: `docs/architecture.md`.
- Seguridad: `docs/security.md`.
- Recuperación de acceso y sesiones: `docs/identity-access.md`.
- Despliegue paso a paso en OCI: `docs/deployment-oci.md`.
- Despliegue sin costo en una instancia OCI compartida: `docs/deployment-oci-shared.md`.

Los fallos Android se registran de forma privada en la propia infraestructura, sin mensajes de
excepción ni datos financieros. En OCI, `./deploy/oci/diagnostics-report.sh 7` muestra un resumen
por huella de los últimos siete días. Los respaldos diarios incluyen checksum y restauración real
de verificación.
