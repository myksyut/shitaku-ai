import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from src.main import create_app


def test_database_error_handler_logs_provider_details_without_exposing_them(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app()

    @app.get("/database-error-probe")
    def fail() -> None:
        raise APIError(
            {"code": "23505", "message": "Duplicate database value", "details": "Diagnostic details", "hint": ""}
        )

    with caplog.at_level("WARNING"), TestClient(app) as client:
        response = client.get("/database-error-probe")
    assert response.status_code == 409
    assert response.json() == {"detail": "Database operation rejected"}
    assert "23505" in caplog.text and "Duplicate database value" in caplog.text and "Diagnostic details" in caplog.text
