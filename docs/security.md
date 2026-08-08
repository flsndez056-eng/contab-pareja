# Seguridad y privacidad

## Decisiones aplicadas

- El servidor es la única autoridad para aprobar, rechazar o crear un gasto.
- Una aprobación bloquea la solicitud en PostgreSQL y crea un gasto una sola vez.
- Las contraseñas se protegen con Argon2; los refresh tokens se rotan y se guardan como hash.
- Android cifra el refresh token con AES-GCM y una clave no exportable de Android Keystore.
- Los códigos de verificación y recuperación son de un solo uso; solo se almacena su hash.
- Las invitaciones por enlace y QR son de un solo uso, vencen en 24 horas y solo se almacena el hash del token.
- Cambiar o restablecer la contraseña incrementa `auth_version` y revoca todas las sesiones previas.
- La app no incluye secretos del servidor, credenciales de Firebase Admin ni contraseñas de base de datos.
- Las notificaciones muestran texto genérico y privacidad de pantalla bloqueada; los detalles se consultan por HTTPS.
- FCM solo despierta/sincroniza la app. PostgreSQL sigue siendo la fuente de verdad.
- La base de datos y el worker no publican puertos en producción; solo Caddy expone 80/443.
- Auditoría y outbox se escriben en la misma transacción que el cambio contable.

## Baja y cambio de pareja

- Cerrar una relación requiere reautenticación. Cancela solicitudes pendientes y libera a ambos miembros para una relación nueva; los gastos ya aprobados quedan inmutables en el historial de ambos.
- Eliminar la cuenta requiere contraseña y la confirmación explícita `ELIMINAR`. Se cierran las sesiones, se desactivan dispositivos, se consumen enlaces de acción y se anonimiza nombre y correo.
- El correo original queda libre y puede registrarse de nuevo. Ese registro crea una identidad nueva y no recupera automáticamente el historial de la cuenta eliminada.

## Antes de producción

1. Configura un dominio y HTTPS válido.
2. Genera secretos distintos para PostgreSQL y JWT; no reutilices claves del proyecto anterior.
3. Descarga una cuenta de servicio Firebase con el mínimo acceso necesario y guárdala solo en `secrets/` del servidor.
4. Activa copias de seguridad cifradas fuera de la VM y prueba una restauración.
5. Restringe SSH en OCI a tu dirección IP; abre públicamente solo 80 y 443.
6. Activa protección de rama, revisión de Dependabot y alertas de secretos en GitHub.
7. Publica Android mediante Play App Signing y conserva la clave de carga fuera del repositorio.

## Datos sensibles

Los montos, descripciones, comercios y decisiones son información financiera privada. No deben incluirse en registros de aplicación, analítica, informes de errores ni cargas FCM. Los logs HTTP de Android están desactivados en producción y redactan `Authorization` en desarrollo.
