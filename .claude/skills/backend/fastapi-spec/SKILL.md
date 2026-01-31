# FastAPI 技術仕様

## プロジェクト構造
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPIアプリケーション
│   ├── config.py            # Pydantic Settings
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # APIルーター集約
│   │       └── endpoints/   # エンドポイント
│   ├── core/                # セキュリティ、例外
│   ├── db/                  # データベース設定
│   ├── models/              # SQLAlchemyモデル
│   ├── schemas/             # Pydanticスキーマ
│   ├── crud/                # CRUD操作
│   └── services/            # ビジネスロジック
├── alembic/                 # マイグレーション
├── tests/
├── pyproject.toml           # uv設定
└── Dockerfile
```

## レイヤー構成

### API層 → Service層 → CRUD層 → Model層
```
endpoints/users.py  (HTTP処理)
       ↓
services/user.py    (ビジネスロジック)
       ↓
crud/user.py        (データアクセス)
       ↓
models/user.py      (SQLAlchemyモデル)
```

## 依存性注入パターン
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db

@router.get("/users/{user_id}")
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> UserResponse:
    ...
```

## SQLAlchemy 2.0
```python
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
```

## Alembic マイグレーション
```bash
# マイグレーション生成
uv run alembic revision --autogenerate -m "Add users table"

# マイグレーション適用
uv run alembic upgrade head

# ロールバック
uv run alembic downgrade -1
```

## API設計規約
- RESTful原則に従う
- バージョニング: `/api/v1/`
- ステータスコード:
  - 200: 成功（GET/PATCH）
  - 201: 作成成功（POST）
  - 204: 削除成功（DELETE）
  - 400: バリデーションエラー
  - 404: リソース未発見
  - 500: サーバーエラー
