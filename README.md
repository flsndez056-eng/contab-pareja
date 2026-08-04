# Contab Pareja

Aplicación móvil para que dos miembros de una pareja soliciten, aprueben y auditen gastos compartidos.

## Principio central

Una solicitud pendiente no es un gasto contable. Solo una decisión válida del otro miembro crea un gasto aprobado. Todas las transiciones quedan auditadas.

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

El cliente usa Kotlin, Jetpack Compose, Room, WorkManager, Retrofit y Firebase Installation IDs. En debug se conecta a `http://10.0.2.2:8000/` desde el emulador.

1. Abre `android/` en Android Studio.
2. Para notificaciones, registra el paquete `com.flsndez.contabpareja` en Firebase y coloca `google-services.json` en `android/app/`.
3. Ejecuta `./gradlew testDebugUnitTest lintDebug assembleDebug`.
4. Para release pasa `-PCONTAB_API_BASE_URL=https://api.tudominio.com/`.

## Producción

- Arquitectura: `docs/architecture.md`.
- Seguridad: `docs/security.md`.
- Despliegue paso a paso en OCI: `docs/deployment-oci.md`.
