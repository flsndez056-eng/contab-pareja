# Arquitectura

## Estilo

Monolito modular con una base PostgreSQL. La consistencia del gasto y su aprobación se resuelve en una única transacción de base de datos. No se usan microservicios para el núcleo contable.

## Flujo de una solicitud

1. El solicitante crea una `expense_request` con clave de idempotencia.
2. La API confirma que pertenece a una pareja activa de exactamente dos miembros.
3. La solicitud y el evento `expense.requested` se guardan en la misma transacción.
4. El worker toma el evento de `outbox_events` y envía FCM al otro miembro.
5. El otro miembro aprueba o rechaza.
6. La decisión usa bloqueo de fila y una transición condicional desde `pending`.
7. Una aprobación crea exactamente un registro en `expenses`; un rechazo nunca lo crea.
8. La decisión, auditoría y notificación de resultado se confirman en la misma transacción.

## Límites de confianza

- Android nunca decide si una operación está autorizada; solo el backend lo hace.
- FCM es una señal de actualización, no la fuente de verdad.
- PostgreSQL es la fuente canónica y Room es la fuente local de lectura en Android.
- Los tokens de acceso son breves; los refresh tokens se rotan y solo se almacena su hash.
- Los secretos se inyectan en ejecución y nunca se incluyen en imágenes Docker.

## Módulos backend

- `auth`: registro, login, refresh y cierre de sesión.
- `couples`: pareja, miembros e invitaciones.
- `accounts`: baja, anonimización y revocación total de acceso.
- `expenses`: solicitudes, decisiones y libro aprobado.
- `reports`: agregaciones exclusivamente de gastos aprobados.
- `devices`: instalaciones Android y Firebase Installation IDs (FID).
- `outbox`: entrega recuperable de eventos.

## Modelo de concurrencia

- Una pareja acepta como máximo dos miembros activos.
- Un usuario solo puede tener una relación activa, pero puede conservar varias relaciones finalizadas.
- Cerrar una relación cancela solicitudes pendientes, revoca invitaciones y no modifica gastos aprobados.
- Una invitación usa un token aleatorio de un solo uso almacenado únicamente como hash; el código corto es un respaldo manual.
- Una solicitud solo cambia desde `pending` una vez.
- `expense.request_id` es único, por lo que una aprobación no puede duplicar el gasto.
- Las escrituras móviles repetidas usan `Idempotency-Key`.

## Historial y reportes

- El historial de solicitudes admite rangos de hasta 366 días, paginación, estado, categoría y búsqueda por descripción o comercio.
- Android pagina las consultas extensas y carga historial y resumen contable en paralelo.
- Los totales usan el libro inmutable `expenses`; las solicitudes rechazadas o canceladas aparecen en el historial, pero nunca alteran la contabilidad.
- Los desgloses conservan precisión decimal en PostgreSQL y se agrupan por categoría y origen del pago.
