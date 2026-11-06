from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import main


def test_health_reports_database_connectivity(monkeypatch):
    engine = MagicMock()
    engine.dispose = AsyncMock()
    connection = engine.connect.return_value.__aenter__.return_value
    monkeypatch.setattr(main, "get_engine", lambda: engine)

    with TestClient(main.app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": {"connected": True}}
        assert str(connection.execute.call_args.args[0]) == "SELECT 1"

        connection.execute.side_effect = OperationalError(None, None, OSError())
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "degraded", "database": {"connected": False}}
