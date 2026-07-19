import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from psycopg2 import OperationalError

from n3mo.mcp.mcp_server import DATABASE_UNREACHABLE_MESSAGE, _get_db_connection


def test_get_db_connection_returns_friendly_error_when_database_is_unreachable():
    run_indexer = SimpleNamespace(
        start_docker_services=lambda: None,
        wait_for_postgres_and_schema=lambda timeout: False,
    )

    with (
        patch(
            "n3mo.core.database.get_connection",
            side_effect=OperationalError("connection refused"),
        ),
        patch.dict(sys.modules, {"n3mo.core.run_indexer": run_indexer}),
    ):
        with pytest.raises(OperationalError, match="N3MO database is unreachable") as exc_info:
            _get_db_connection()

    assert str(exc_info.value) == DATABASE_UNREACHABLE_MESSAGE
