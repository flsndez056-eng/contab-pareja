from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.config import settings

router = APIRouter(tags=["account-links"])

_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; "
        "img-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _action_page(token: str, action: str) -> HTMLResponse:
    if action == "reset-password":
        title = "Recuperar acceso"
        description = "Abre DúoCuenta para elegir una contraseña nueva."
    else:
        title = "Verificar correo"
        description = "Abre DúoCuenta para confirmar tu dirección de correo."

    encoded_token = quote(token, safe="")
    deep_link = f"{settings.android_deep_link_base}/{action}?token={encoded_token}"
    safe_token = escape(token)
    safe_deep_link = escape(deep_link, quote=True)
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{title} · DúoCuenta</title>
  <style>
    :root {{ font-family: system-ui, sans-serif; color: #172033; background: #f3f6fb; }}
    body {{
      min-height: 100vh; margin: 0; display: grid; place-items: center;
      padding: 24px; box-sizing: border-box;
    }}
    main {{
      width: min(100%, 480px); background: white; border-radius: 20px;
      padding: 32px; box-shadow: 0 18px 60px #1720331f;
    }}
    h1 {{ margin-top: 0; font-size: 1.75rem; }}
    p {{ line-height: 1.55; }}
    a.button {{
      display: block; margin: 24px 0; padding: 14px 18px; border-radius: 12px;
      color: white; background: #3157d5; text-align: center;
      text-decoration: none; font-weight: 700;
    }}
    code {{
      display: block; overflow-wrap: anywhere; padding: 12px; border-radius: 10px;
      background: #eef2f9; color: #172033; user-select: all;
    }}
    small {{ color: #596579; }}
    @media (prefers-color-scheme: dark) {{
      :root {{ color: #eef2f9; background: #101521; }}
      main {{ background: #1a2232; }}
      code {{ color: #eef2f9; background: #101521; }}
      small {{ color: #aeb8ca; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{description}</p>
    <a class="button" href="{safe_deep_link}">Abrir DúoCuenta</a>
    <p>Si la aplicación no se abre, copia este código y pégalo en la pantalla correspondiente:</p>
    <code>{safe_token}</code>
    <p><small>Por seguridad, el código vence y solo puede utilizarse una vez.</small></p>
  </main>
</body>
</html>"""
    return HTMLResponse(html, headers=_SECURITY_HEADERS)


def _invite_page(token: str) -> HTMLResponse:
    encoded_token = quote(token, safe="")
    deep_link = f"contabpareja://invite?token={encoded_token}"
    safe_deep_link = escape(deep_link, quote=True)
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Invitación · DúoCuenta</title>
  <style>
    :root {{ font-family: system-ui, sans-serif; color: #172033; background: #f3f6fb; }}
    body {{
      min-height: 100vh; margin: 0; display: grid; place-items: center;
      padding: 24px; box-sizing: border-box;
    }}
    main {{
      width: min(100%, 480px); background: white; border-radius: 20px;
      padding: 32px; box-shadow: 0 18px 60px #1720331f;
    }}
    h1 {{ margin-top: 0; font-size: 1.75rem; }}
    p {{ line-height: 1.55; }}
    a.button {{
      display: block; margin: 24px 0; padding: 14px 18px; border-radius: 12px;
      color: white; background: #3157d5; text-align: center;
      text-decoration: none; font-weight: 700;
    }}
    small {{ color: #596579; }}
    @media (prefers-color-scheme: dark) {{
      :root {{ color: #eef2f9; background: #101521; }}
      main {{ background: #1a2232; }}
      small {{ color: #aeb8ca; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Te invitaron a DúoCuenta</h1>
    <p>Abre la aplicación para revisar quién te invita antes de conectar las cuentas.</p>
    <a class="button" href="{safe_deep_link}">Abrir DúoCuenta</a>
    <p><small>
      La invitación vence, solo puede utilizarse una vez y siempre requiere tu confirmación.
    </small></p>
  </main>
</body>
</html>"""
    return HTMLResponse(html, headers=_SECURITY_HEADERS)


@router.get("/auth/reset-password", response_class=HTMLResponse, include_in_schema=False)
async def reset_password_link(
    token: str = Query(min_length=16, max_length=512),
) -> HTMLResponse:
    return _action_page(token, "reset-password")


@router.get("/auth/verify-email", response_class=HTMLResponse, include_in_schema=False)
async def verify_email_link(
    token: str = Query(min_length=16, max_length=512),
) -> HTMLResponse:
    return _action_page(token, "verify-email")


@router.get("/invite", response_class=HTMLResponse, include_in_schema=False)
async def invitation_link(
    token: str = Query(min_length=32, max_length=512),
) -> HTMLResponse:
    return _invite_page(token)


@router.get("/.well-known/assetlinks.json", include_in_schema=False)
async def android_asset_links() -> JSONResponse:
    fingerprints = [
        value.strip().upper()
        for value in settings.android_app_cert_sha256.split(",")
        if value.strip()
    ]
    statements = []
    if fingerprints:
        statements.append(
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": "com.flsndez.contabpareja",
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        )
    return JSONResponse(
        statements,
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
