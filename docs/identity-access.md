# Acceso, recuperación y sesiones

## Capacidades

- Verificación del correo con un código aleatorio de un solo uso.
- Recuperación de contraseña sin revelar si una dirección está registrada.
- Cambio de contraseña desde una sesión autenticada.
- Revocación de todas las sesiones y dispositivos autenticados.
- Invalidación inmediata de access tokens mediante `auth_version`.

Los códigos vencen, tienen un tiempo mínimo entre emisiones y solo se guarda su hash SHA-256. Al restablecer o cambiar la contraseña se revocan todos los refresh tokens anteriores.

## Rutas

- `POST /api/v1/auth/password/forgot`
- `POST /api/v1/auth/password/reset`
- `POST /api/v1/auth/password/change`
- `POST /api/v1/auth/email/verification/request`
- `POST /api/v1/auth/email/verification/confirm`
- `POST /api/v1/auth/sessions/revoke-all`

Android admite los enlaces `contabpareja://auth/verify-email?token=...` y `contabpareja://auth/reset-password?token=...`. También permite pegar manualmente el código.

## Correo en Oracle Cloud

Producción usa SMTP con STARTTLS. OCI Email Delivery forma parte de Always Free y requiere:

1. Crear un usuario IAM exclusivo para SMTP y concederle permisos de Email Delivery.
2. Crear credenciales SMTP; no son la contraseña normal del usuario IAM.
3. Crear el dominio de correo para `siptrapollo.online` en la región Ashburn.
4. Publicar en DNS los registros SPF y DKIM indicados por Oracle.
5. Crear un remitente aprobado, por ejemplo `no-reply@siptrapollo.online`.
6. Configurar el endpoint SMTP público de Ashburn, puerto `587` y STARTTLS.

Referencias oficiales:

- https://docs.oracle.com/en-us/iaas/Content/Email/Reference/gettingstarted.htm
- https://docs.oracle.com/en-us/iaas/Content/Email/Reference/gettingstarted_topic-Begin_sending_email.htm
- https://docs.oracle.com/en-us/iaas/Content/Email/Tasks/managingapprovedsenders.htm

Variables privadas de producción:

```dotenv
EMAIL_DELIVERY_MODE=smtp
EMAIL_FROM_ADDRESS=no-reply@siptrapollo.online
SMTP_HOST=smtp.email.us-ashburn-1.oci.oraclecloud.com
SMTP_PORT=587
SMTP_USERNAME=<credencial SMTP de OCI>
SMTP_PASSWORD=<contraseña SMTP de OCI>
SMTP_STARTTLS=true
ANDROID_DEEP_LINK_BASE=contabpareja://auth
```

No guardes las credenciales SMTP en Git. Deben existir únicamente en `.env.production`, con permisos `600`.

## Baja de cuenta

La eliminación y anonimización se implementará sobre este sistema de reautenticación. No se deben borrar directamente los gastos compartidos: el correo y el nombre pueden anonimizarse, pero el historial contable aprobado debe seguir siendo consistente para la otra persona.
