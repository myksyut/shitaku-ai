from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.entities.series import CreatorAccess
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from tests.client_fakes import as_user_client


def test_dictionary_insert_derives_series_from_access_context() -> None:
    client = MagicMock()
    sid, other = uuid4(), uuid4()
    entry = DictionaryEntry(uuid4(), other, "Term", None, datetime.now(UTC))
    DictionaryRepositoryImpl(as_user_client(client)).create(CreatorAccess(sid, uuid4()), entry)
    payload = client.table.return_value.insert.call_args.args[0]
    assert payload["series_id"] == str(sid)
    assert payload["id"] == str(entry.id) and payload["canonical_name"] == "Term"
    assert entry.series_id == other
