"""Dictionary API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.dictionary_use_cases import (
    CreateDictionaryEntryUseCase,
    DeleteDictionaryEntryUseCase,
    GetDictionaryEntriesUseCase,
    GetDictionaryEntryUseCase,
    UpdateDictionaryEntryUseCase,
)
from src.domain.entities.dictionary_entry import DictionaryCategory, DictionaryEntry
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.dictionary_repository_impl import (
    DictionaryRepositoryImpl,
)
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.schemas.dictionary import (
    DictionaryCategoryEnum,
    DictionaryEntryCreate,
    DictionaryEntryResponse,
    DictionaryEntryUpdate,
)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


def _convert_category(category: DictionaryCategory | None) -> DictionaryCategoryEnum | None:
    """Convert domain category literal to schema enum."""
    if category is None:
        return None
    return DictionaryCategoryEnum(category)


def _entry_to_response(entry: DictionaryEntry) -> DictionaryEntryResponse:
    """Convert DictionaryEntry entity to response schema."""
    return DictionaryEntryResponse(
        id=entry.id,
        agent_id=entry.agent_id,
        canonical_name=entry.canonical_name,
        category=_convert_category(entry.category),
        aliases=entry.aliases,
        description=entry.description,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def get_repository() -> DictionaryRepositoryImpl:
    """Get dictionary repository instance."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return DictionaryRepositoryImpl(client)


@router.post("", response_model=DictionaryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_dictionary_entry(
    data: DictionaryEntryCreate,
    user_id: UUID = Depends(get_current_user_id),
    repository: DictionaryRepositoryImpl = Depends(get_repository),
) -> DictionaryEntryResponse:
    """Create a new dictionary entry."""
    use_case = CreateDictionaryEntryUseCase(repository)
    try:
        entry = await use_case.execute(
            user_id=user_id,
            canonical_name=data.canonical_name,
            description=data.description,
        )
        return _entry_to_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get("", response_model=list[DictionaryEntryResponse])
async def get_dictionary_entries(
    user_id: UUID = Depends(get_current_user_id),
    repository: DictionaryRepositoryImpl = Depends(get_repository),
) -> list[DictionaryEntryResponse]:
    """Get all dictionary entries for the authenticated user."""
    use_case = GetDictionaryEntriesUseCase(repository)
    entries = await use_case.execute(user_id)
    return [_entry_to_response(e) for e in entries]


@router.get("/{entry_id}", response_model=DictionaryEntryResponse)
async def get_dictionary_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: DictionaryRepositoryImpl = Depends(get_repository),
) -> DictionaryEntryResponse:
    """Get a specific dictionary entry."""
    use_case = GetDictionaryEntryUseCase(repository)
    entry = await use_case.execute(entry_id, user_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _entry_to_response(entry)


@router.put("/{entry_id}", response_model=DictionaryEntryResponse)
async def update_dictionary_entry(
    entry_id: UUID,
    data: DictionaryEntryUpdate,
    user_id: UUID = Depends(get_current_user_id),
    repository: DictionaryRepositoryImpl = Depends(get_repository),
) -> DictionaryEntryResponse:
    """Update a dictionary entry."""
    use_case = UpdateDictionaryEntryUseCase(repository)
    try:
        entry = await use_case.execute(
            entry_id=entry_id,
            user_id=user_id,
            canonical_name=data.canonical_name,
            description=data.description,
        )
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
        return _entry_to_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dictionary_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: DictionaryRepositoryImpl = Depends(get_repository),
) -> None:
    """Delete a dictionary entry."""
    use_case = DeleteDictionaryEntryUseCase(repository)
    deleted = await use_case.execute(entry_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
