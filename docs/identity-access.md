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

Los correos usan enlaces HTTPS en `https://contab.siptrapollo.online/auth/`. Android los reconoce como App Links verificados y el servidor ofrece una página de respaldo con un botón para abrir `contabpareja://auth/...` y el código para copiar manualmente.

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
ACCOUNT_ACTION_BASE_URL=https://contab.siptrapollo.online/auth
ANDROID_APP_CERT_SHA256=<huella SHA-256 del certificado que firma el APK>
```

No guardes las credenciales SMTP en Git. Deben existir únicamente en `.env.production`, con permisos `600`.

## Baja de cuenta

La eliminación y anonimización se implementará sobre este sistema de reautenticación. No se deben borrar directamente los gastos compartidos: el correo y el nombre pueden anonimizarse, pero el historial contable aprobado debe seguir siendo consistente para la otra persona.
