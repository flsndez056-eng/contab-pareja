from app.main import app


def test_openapi_exposes_versioned_product_routes() -> None:
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/couples",
        "/api/v1/couples/join",
        "/api/v1/expense-requests",
        "/api/v1/expense-requests/{request_id}/decision",
        "/api/v1/reports/summary",
        "/api/v1/devices/current",
        "/health/live",
        "/health/ready",
    }
    assert expected <= set(paths)


def test_protected_routes_use_bearer_authentication() -> None:
    operation = app.openapi()["paths"]["/api/v1/expense-requests"]["post"]
    assert operation["security"] == [{"OAuth2PasswordBearer": []}]
