from uuid import UUID

from fastapi import APIRouter, Depends

from src.application.use_cases.dictionary_use_cases import DictionaryUseCases
from src.domain.entities.series import CreatorAccess, MemberAccess
from src.infrastructure.external.supabase_client import UserClient
from src.infrastructure.repositories.dictionary_repository_impl import DictionaryRepositoryImpl
from src.presentation.api.v1.dependencies import creator_access, get_user_supabase_client, member_access
from src.presentation.schemas.dictionary import DictionaryEntryCreate, DictionaryEntryUpdate, DictionaryEntryView

router = APIRouter(prefix="/series/{series_id}/dictionary", tags=["dictionary"])


def get_dictionary(client: UserClient = Depends(get_user_supabase_client)) -> DictionaryUseCases:
    """Use the caller's JWT for shared vocabulary persistence."""
    return DictionaryUseCases(DictionaryRepositoryImpl(client))


@router.get("")
def list_entries(
    access: MemberAccess = Depends(member_access), use_cases: DictionaryUseCases = Depends(get_dictionary)
) -> list[DictionaryEntryView]:
    """Read the series' shared vocabulary."""
    return [DictionaryEntryView.model_validate(e) for e in use_cases.list_entries(access)]


@router.post("", status_code=201)
def create_entry(
    request: DictionaryEntryCreate,
    access: CreatorAccess = Depends(creator_access),
    use_cases: DictionaryUseCases = Depends(get_dictionary),
) -> DictionaryEntryView:
    """Create a series-scoped vocabulary entry."""
    return DictionaryEntryView.model_validate(
        use_cases.create(access, request.canonical_name, request.category, request.aliases, request.description)
    )


@router.put("/{entry_id}")
def update_entry(
    entry_id: UUID,
    request: DictionaryEntryUpdate,
    access: CreatorAccess = Depends(creator_access),
    use_cases: DictionaryUseCases = Depends(get_dictionary),
) -> DictionaryEntryView:
    """Apply only explicitly supplied vocabulary changes."""
    return DictionaryEntryView.model_validate(use_cases.update(access, entry_id, request.changes()))


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    entry_id: UUID,
    access: CreatorAccess = Depends(creator_access),
    use_cases: DictionaryUseCases = Depends(get_dictionary),
) -> None:
    """Delete only the creator's selected series entry."""
    use_cases.delete(access, entry_id)
