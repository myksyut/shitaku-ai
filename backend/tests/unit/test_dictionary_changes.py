import pytest
from pydantic import ValidationError

from src.presentation.schemas.dictionary import DictionaryEntryUpdate


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"description": None},
        {"category": None},
        {"aliases": []},
        {"canonical_name": "Name", "category": "term", "aliases": ["Alias"], "description": "Context"},
    ],
)
def test_dictionary_changes_preserve_only_supplied_fields(payload: dict[str, object]) -> None:
    assert DictionaryEntryUpdate.model_validate(payload).changes() == payload


@pytest.mark.parametrize("field", ["canonical_name", "aliases"])
def test_dictionary_changes_still_reject_null_nonnullable_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        DictionaryEntryUpdate.model_validate({field: None})
