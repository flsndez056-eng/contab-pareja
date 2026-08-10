# Despliegue en Oracle Cloud Infrastructure

Esta guía usa una sola VM de OCI con Docker Compose, PostgreSQL privado, API/worker privados y Caddy como entrada HTTPS. Es una arquitectura adecuada para el primer lanzamiento; cuando el uso crezca, PostgreSQL puede migrarse a un servicio administrado sin cambiar el contrato móvil.

Si la VM ya aloja servicios y tiene Nginx en `80/443`, usa en su lugar [`deployment-oci-shared.md`](deployment-oci-shared.md).

## 1. Preparar servicios externos

1. Compra o utiliza un dominio y reserva un subdominio, por ejemplo `api.tudominio.com`.
2. Usa el proyecto Firebase existente `contab-pareja`.
3. Usa la app Android ya registrada con el paquete `com.flsndez.contabpareja`.
4. Descarga `google-services.json` y colócalo en `android/app/google-services.json`.
5. Para el worker usa la cuenta dedicada `contab-pareja-fcm@contab-pareja.iam.gserviceaccount.com`, limitada al rol `roles/firebasecloudmessaging.admin`, y descarga su JSON una sola vez. No lo subas a Git.

## 2. Crear la VM

1. En OCI crea primero una VCN con conectividad a Internet.
2. Crea una instancia Ubuntu 24.04 o 26.04 LTS. La imagen publicada es multi-arquitectura, por lo que funciona tanto en Ampere A1 (`arm64`) como en shapes AMD/Intel (`amd64`).
3. Asigna una IP pública reservada.
4. Adjunta tu clave SSH.
5. En el Network Security Group permite:
   - TCP 22 únicamente desde tu IP pública.
   - TCP 80 desde `0.0.0.0/0`.
   - TCP 443 desde `0.0.0.0/0`.
   - UDP 443 desde `0.0.0.0/0` para HTTP/3.
6. No abras 5432 ni 8000.
7. Crea un registro DNS `A` (y `AAAA` si usas IPv6) que apunte el subdominio a la VM.

## 3. Instalar Docker

Conéctate por SSH y sigue el repositorio `apt` oficial de Docker. El conjunto final de paquetes debe incluir:

```bash
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Cierra la sesión SSH y vuelve a entrar para que el grupo `docker` tenga efecto. Verifica:

```bash
docker version
docker compose version
```

## 4. Publicar la imagen

1. Empuja el código a `flsndez056-eng/contab-pareja` y espera que el workflow `CI` termine correctamente.
2. Crea una versión:

```bash
git tag v0.1.0
git push origin v0.1.0
```

El workflow `Publicar API` crea imágenes `amd64` y `arm64` en GHCR. En GitHub cambia la visibilidad del paquete a pública, o autentica la VM con un token de solo lectura.

## 5. Instalar la aplicación en la VM

```bash
git clone https://github.com/flsndez056-eng/contab-pareja.git contab-pareja
cd contab-pareja
mkdir -p secrets backups
cp .env.production.example .env.production
chmod 600 .env.production
```

Edita `.env.production`. Usa valores URL-safe porque la contraseña de PostgreSQL forma parte de una URL:

```bash
openssl rand -hex 32
openssl rand -hex 64
```

El primer resultado puede ser `POSTGRES_PASSWORD` y el segundo `JWT_SECRET`. Copia la cuenta Firebase a:

```text
secrets/firebase-service-account.json
```

Protege el archivo:

```bash
chmod 600 secrets/firebase-service-account.json
```

Valida y levanta el conjunto:

```bash
docker compose --env-file .env.production -f compose.oci.yaml config --quiet
docker compose --env-file .env.production -f compose.oci.yaml pull
docker compose --env-file .env.production -f compose.oci.yaml up -d
docker compose --env-file .env.production -f compose.oci.yaml ps
```

Caddy solicitará y renovará automáticamente el certificado TLS cuando DNS y puertos sean correctos. Comprueba:

```bash
curl --fail https://api.tudominio.com/health/ready
docker compose --env-file .env.production -f compose.oci.yaml logs --tail=100 api worker caddy
```

## 6. Construir Android contra producción

Desde tu computadora, con `google-services.json` ya colocado:

```bash
cd android
./gradlew bundleRelease -PCONTAB_API_BASE_URL=https://contab.siptrapollo.online/
```

Para publicar en Google Play configura una clave de carga y Play App Signing. No uses una APK debug para usuarios reales.

Para pruebas controladas en teléfonos físicos, puedes generar temporalmente un APK firmado con la clave de depuración:

```bash
./gradlew assembleDebug -PCONTAB_DEBUG_API_BASE_URL=https://contab.siptrapollo.online/
```

## 7. Copias de seguridad

Haz ejecutable el script y pruébalo:

```bash
chmod +x deploy/oci/backup.sh
chmod +x deploy/oci/verify-backup.sh
./deploy/oci/backup.sh
./deploy/oci/verify-backup.sh
```

Cada copia incluye un SHA-256 y la verificación realiza una restauración real en una base temporal,
ejecuta comprobaciones mínimas y luego la elimina. El último éxito queda en
`backups/last-verified.txt`.

Para programarlo a diario con systemd:

```bash
sudo cp deploy/oci/systemd/contab-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contab-backup.timer
sudo systemctl start contab-backup.service
systemctl status contab-backup.service --no-pager
systemctl list-timers contab-backup.timer --no-pager
```

Copia además los `.dump` y `.sha256` a un destino cifrado fuera de la VM. La restauración
automática detecta respaldos truncados o incompatibles, pero una copia externa sigue siendo
necesaria ante la pérdida total del servidor.

## 8. Actualizaciones y rollback

Para actualizar, cambia `APP_IMAGE` a una etiqueta inmutable concreta y ejecuta:

```bash
docker compose --env-file .env.production -f compose.oci.yaml pull
docker compose --env-file .env.production -f compose.oci.yaml up -d
```

La API ejecuta `alembic upgrade head` antes de iniciar. Para rollback de aplicación, restaura la etiqueta anterior; si una versión incluye una migración no compatible, sigue el procedimiento de downgrade probado para esa versión antes de cambiar la imagen.

## 9. Operación mínima

- Revisa espacio de disco, memoria, reinicios y `/health/ready`.
- Aplica actualizaciones de seguridad del sistema y Docker mensualmente.
- Conserva al menos 14 copias diarias y una copia fuera de la región.
- Prueba recuperación completa antes del lanzamiento y luego de cada cambio de esquema importante.
