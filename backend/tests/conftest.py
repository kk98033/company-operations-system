"""Safe process defaults applied before the application module is imported."""

from __future__ import annotations

import os

os.environ["APP_ENV"] = "test"
os.environ["APP_HOST"] = "127.0.0.1"
os.environ["APP_PORT"] = "8000"
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://company_system_test:test-only@127.0.0.1/"
    "company_system_test"
)
os.environ["APP_PUBLIC_ORIGIN"] = "http://testserver"
os.environ["CSRF_HMAC_KEY"] = "dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE"
