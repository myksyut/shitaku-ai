from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return [UserResponse.model_validate(user) for user in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    created_user = crud_user.create_user(db=db, user=user)
    return UserResponse.model_validate(created_user)


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> UserResponse:
    db_user = crud_user.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(db_user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
) -> UserResponse:
    db_user = crud_user.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(db_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> None:
    success = crud_user.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
