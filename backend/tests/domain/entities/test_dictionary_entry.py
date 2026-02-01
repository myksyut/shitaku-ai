"""DictionaryEntry entity tests."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.dictionary_entry import DictionaryEntry


class TestDictionaryEntry:
    """DictionaryEntryエンティティのテスト"""

    def test_create_dictionary_entry(self) -> None:
        """DictionaryEntryが正しくインスタンス化できる"""
        entry_id = uuid4()
        user_id = uuid4()
        now = datetime.now()

        entry = DictionaryEntry(
            id=entry_id,
            user_id=user_id,
            canonical_name="金沢太郎",
            description="フロントエンド担当、チームA所属",
            created_at=now,
            updated_at=None,
        )

        assert entry.id == entry_id
        assert entry.user_id == user_id
        assert entry.canonical_name == "金沢太郎"
        assert entry.description == "フロントエンド担当、チームA所属"
        assert entry.created_at == now
        assert entry.updated_at is None

    def test_create_dictionary_entry_without_description(self) -> None:
        """descriptionなしでDictionaryEntryが作成できる"""
        entry = DictionaryEntry(
            id=uuid4(),
            user_id=uuid4(),
            canonical_name="sitaku.ai",
            description=None,
            created_at=datetime.now(),
            updated_at=None,
        )

        assert entry.canonical_name == "sitaku.ai"
        assert entry.description is None

    def test_dictionary_entry_equality(self) -> None:
        """同じIDを持つDictionaryEntryは等しい"""
        entry_id = uuid4()
        user_id = uuid4()
        now = datetime.now()

        entry1 = DictionaryEntry(
            id=entry_id,
            user_id=user_id,
            canonical_name="テスト",
            description=None,
            created_at=now,
            updated_at=None,
        )
        entry2 = DictionaryEntry(
            id=entry_id,
            user_id=user_id,
            canonical_name="テスト",
            description=None,
            created_at=now,
            updated_at=None,
        )

        assert entry1 == entry2
