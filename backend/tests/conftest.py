import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://contab:test@localhost:5432/contab_pareja_test"
)
os.environ.setdefault(
    "JWT_SECRET", "test-secret-test-secret-test-secret-test-secret-test-secret-test-secret-1234"
)
os.environ.setdefault("APP_ENV", "test")
