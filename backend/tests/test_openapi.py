from app.main import app


def test_openapi_exposes_versioned_product_routes() -> None:
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/password/forgot",
        "/api/v1/auth/password/reset",
        "/api/v1/auth/password/change",
        "/api/v1/auth/email/verification/request",
        "/api/v1/auth/email/verification/confirm",
        "/api/v1/auth/sessions/revoke-all",
        "/api/v1/couples",
        "/api/v1/couples/join",
        "/api/v1/couples/current/end",
        "/api/v1/couples/history",
        "/api/v1/couples/invitations/preview",
        "/api/v1/account",
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


def test_expense_history_exposes_bounded_search_filters() -> None:
    operation = app.openapi()["paths"]["/api/v1/expense-requests"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert {"status", "from_date", "to_date", "category_id", "q", "limit", "offset"} <= set(
        parameters
    )
    assert parameters["limit"]["schema"]["maximum"] == 500
    search_schema = parameters["q"]["schema"]
    string_schema = next(
        candidate
        for candidate in search_schema.get("anyOf", [search_schema])
        if candidate.get("type") == "string"
    )
    assert string_schema["maxLength"] == 120
