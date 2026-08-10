# Despliegue en una instancia OCI compartida

Esta variante mantiene costo cero al reutilizar la VM, la IP pública, Nginx y Certbot existentes. Contab Pareja conserva su propio PostgreSQL y su propia red Docker, pero no ocupa directamente los puertos públicos `80` y `443`.

## Diseño

- Nginx del host recibe `https://contab.siptrapollo.online`.
- La API solo escucha en `127.0.0.1:8100`.
- PostgreSQL y el worker no publican puertos.
- Caddy queda desactivado mediante el perfil `standalone`.
- Los tres contenedores tienen límites de CPU, memoria, procesos y rotación de logs.

## 1. DNS

Crea un registro `A`:

```text
Host: contab
Valor: 150.136.75.94
TTL: Automatic
```

Espera hasta que este comando devuelva la IP anterior:

```bash
getent ahostsv4 contab.siptrapollo.online
```

## 2. Publicar la imagen

La imagen `ghcr.io/flsndez056-eng/contab-pareja-api:0.1.0` debe existir y ser pública. El workflow `Publicar API` construye `linux/amd64` y `linux/arm64` al publicar la etiqueta `v0.1.0`.

## 3. Preparar el proyecto

```bash
sudo mkdir -p /opt/contab-pareja
sudo chown "$USER":"$USER" /opt/contab-pareja
git clone https://github.com/flsndez056-eng/contab-pareja.git /opt/contab-pareja
cd /opt/contab-pareja
mkdir -p secrets backups
cp .env.production.example .env.production
chmod 600 .env.production
```

Genera valores únicos para `POSTGRES_PASSWORD` y `JWT_SECRET`, y deja `API_HOST_PORT=8100`. Copia la credencial FCM restringida a `secrets/firebase-service-account.json` y protégela:

```bash
sudo chown 10001:10001 secrets/firebase-service-account.json
sudo chmod 600 secrets/firebase-service-account.json
```

El contenedor se ejecuta como el usuario no privilegiado `10001`. El propietario anterior debe
ser `10001`; de lo contrario, el worker arrancará pero Firebase rechazará cada entrega por falta
de acceso a la credencial.

## 4. Validar y levantar

Usa siempre ambos archivos Compose:

```bash
docker compose --env-file .env.production \
  -f compose.oci.yaml -f compose.oci-shared.yaml config --quiet
docker compose --env-file .env.production \
  -f compose.oci.yaml -f compose.oci-shared.yaml pull
docker compose --env-file .env.production \
  -f compose.oci.yaml -f compose.oci-shared.yaml up -d
docker compose --env-file .env.production \
  -f compose.oci.yaml -f compose.oci-shared.yaml ps
curl --fail http://127.0.0.1:8100/health/ready
```

El servicio `caddy` no se inicia en esta modalidad.

## 5. Integrar Nginx y TLS

Después de que DNS apunte a la VM:

```bash
sudo cp deploy/oci/nginx-contab-pareja.conf /etc/nginx/sites-available/contab-pareja
sudo ln -s /etc/nginx/sites-available/contab-pareja /etc/nginx/sites-enabled/contab-pareja
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d contab.siptrapollo.online --redirect
sudo nginx -t
curl --fail https://contab.siptrapollo.online/health/ready
```

Certbot modifica únicamente el bloque del nuevo dominio y mantiene su renovación automática.

## 6. Operación

Para actualizar:

```bash
cd /opt/contab-pareja
git pull --ff-only
docker compose --env-file .env.production \
  -f compose.oci.yaml -f compose.oci-shared.yaml pull
docker compose --env-file .env.production \
  -f compose.oci.yaml -f compose.oci-shared.yaml up -d
```

Para respaldar PostgreSQL:

```bash
cd /opt/contab-pareja
sh deploy/oci/backup.sh
sh deploy/oci/verify-backup.sh
```

Los scripts solo operan sobre el servicio `postgres` del proyecto Compose `contab-pareja-production`:
no reinician ni modifican los contenedores de Fondo. Para automatizar la copia y una restauración
temporal diaria, instala las unidades de `deploy/oci/systemd/` como se explica en
[`deployment-oci.md`](deployment-oci.md#7-copias-de-seguridad).

Para consultar el monitoreo privado sin exponer datos a servicios externos:

```bash
sh deploy/oci/diagnostics-report.sh 7
```

El resultado agrupa tipo, versión y huella del error. No contiene correos, mensajes de excepción
ni contenido de solicitudes o gastos.

No abras los puertos `8100`, `8000` ni `5432` en OCI o en el sistema operativo. Revisa periódicamente `docker stats`, `df -h` y la fecha de expiración del certificado.
