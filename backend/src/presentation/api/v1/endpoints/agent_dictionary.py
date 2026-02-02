"""Agent Dictionary API endpoints.

REST API endpoints for managing dictionary entries associated with agents.
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.domain.entities.dictionary_entry import DictionaryCategory, DictionaryEntry
from src.infrastructure.external.supabase_client import get_supabase_client
from src.infrastructure.repositories.agent_repository_impl import AgentRepositoryImpl
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

router = APIRouter(prefix="/agents/{agent_id}/dictionary", tags=["agent-dictionary"])


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


def get_dictionary_repository() -> DictionaryRepositoryImpl:
    """Get dictionary repository instance."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return DictionaryRepositoryImpl(client)


def get_agent_repository() -> AgentRepositoryImpl:
    """Get agent repository instance."""
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return AgentRepositoryImpl(client)


async def verify_agent_access(
    agent_id: UUID,
    user_id: UUID,
    agent_repository: AgentRepositoryImpl,
) -> None:
    """Verify that the agent exists and belongs to the user."""
    if not agent_repository.exists(agent_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


@router.get("", response_model=list[DictionaryEntryResponse])
async def get_agent_dictionary_entries(
    agent_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    dictionary_repository: DictionaryRepositoryImpl = Depends(get_dictionary_repository),
    agent_repository: AgentRepositoryImpl = Depends(get_agent_repository),
) -> list[DictionaryEntryResponse]:
    """Get all dictionary entries for a specific agent."""
    await verify_agent_access(agent_id, user_id, agent_repository)
    entries = await dictionary_repository.find_by_agent_id(agent_id, user_id)
    return [_entry_to_response(e) for e in entries]


@router.post("", response_model=DictionaryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_dictionary_entry(
    agent_id: UUID,
    data: DictionaryEntryCreate,
    user_id: UUID = Depends(get_current_user_id),
    dictionary_repository: DictionaryRepositoryImpl = Depends(get_dictionary_repository),
    agent_repository: AgentRepositoryImpl = Depends(get_agent_repository),
) -> DictionaryEntryResponse:
    """Create a new dictionary entry associated with an agent."""
    await verify_agent_access(agent_id, user_id, agent_repository)

    # Check for duplicate canonical_name
    if await dictionary_repository.exists_by_canonical_name(user_id, data.canonical_name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entry with canonical_name '{data.canonical_name}' already exists",
        )

    entry = DictionaryEntry(
        id=uuid4(),
        user_id=user_id,
        agent_id=agent_id,
        canonical_name=data.canonical_name,
        category=data.category.value if data.category else None,
        aliases=data.aliases,
        description=data.description,
        created_at=datetime.now(),
        updated_at=None,
    )

    created_entry = await dictionary_repository.create(entry)
    return _entry_to_response(created_entry)


@router.put("/{entry_id}", response_model=DictionaryEntryResponse)
async def update_agent_dictionary_entry(
    agent_id: UUID,
    entry_id: UUID,
    data: DictionaryEntryUpdate,
    user_id: UUID = Depends(get_current_user_id),
    dictionary_repository: DictionaryRepositoryImpl = Depends(get_dictionary_repository),
    agent_repository: AgentRepositoryImpl = Depends(get_agent_repository),
) -> DictionaryEntryResponse:
    """Update a dictionary entry associated with an agent."""
    await verify_agent_access(agent_id, user_id, agent_repository)

    entry = await dictionary_repository.get_by_id(entry_id, user_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )

    # Verify entry belongs to this agent
    if entry.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found for this agent",
        )

    # Update fields
    if data.canonical_name is not None and data.canonical_name != entry.canonical_name:
        if await dictionary_repository.exists_by_canonical_name(user_id, data.canonical_name, entry_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Entry with canonical_name '{data.canonical_name}' already exists",
            )
        entry.canonical_name = data.canonical_name

    if data.category is not None:
        entry.category = data.category.value

    if data.aliases is not None:
        entry.aliases = data.aliases

    if data.description is not None:
        entry.description = data.description

    entry.updated_at = datetime.now()
    updated_entry = await dictionary_repository.update(entry)
    return _entry_to_response(updated_entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_dictionary_entry(
    agent_id: UUID,
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    dictionary_repository: DictionaryRepositoryImpl = Depends(get_dictionary_repository),
    agent_repository: AgentRepositoryImpl = Depends(get_agent_repository),
) -> None:
    """Delete a dictionary entry associated with an agent."""
    await verify_agent_access(agent_id, user_id, agent_repository)

    # First verify entry exists and belongs to this agent
    entry = await dictionary_repository.get_by_id(entry_id, user_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )

    if entry.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found for this agent",
        )

    deleted = await dictionary_repository.delete(entry_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
