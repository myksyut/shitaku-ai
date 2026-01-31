# NextJS 技術仕様

## プロジェクト構造
```
frontend/
├── src/
│   ├── app/                 # App Router
│   │   ├── layout.tsx       # ルートレイアウト
│   │   ├── page.tsx         # ホームページ
│   │   └── globals.css      # グローバルスタイル
│   ├── components/
│   │   ├── ui/              # 基本UIコンポーネント
│   │   └── features/        # 機能コンポーネント
│   ├── hooks/               # カスタムフック
│   ├── lib/                 # ユーティリティ
│   │   └── api.ts           # APIクライアント
│   └── types/               # 型定義
├── public/                  # 静的ファイル
├── tests/                   # テスト
├── package.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.ts
└── Dockerfile
```

## App Router

### Server Components（デフォルト）
```tsx
// サーバーコンポーネント（デフォルト）
export default async function Page() {
  const data = await fetchData()
  return <div>{data}</div>
}
```

### Client Components
```tsx
'use client'

import { useState } from 'react'

export function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(count + 1)}>{count}</button>
}
```

## コンポーネント設計

### 命名規則
- コンポーネント: PascalCase
- フック: `use`プレフィックス
- ユーティリティ: camelCase

### Props設計
```tsx
type ButtonProps = {
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

export function Button({ variant = 'primary', size = 'md', children }: ButtonProps) {
  ...
}
```

## API通信

### APIクライアント
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

export async function apiClient<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`)
  if (!response.ok) throw new Error('API request failed')
  return response.json()
}
```

## スタイリング

### Tailwind CSS + clsx + tailwind-merge
```tsx
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

<button className={cn('px-4 py-2', variant === 'primary' && 'bg-blue-500')} />
```

## 品質チェック
```bash
npm run lint          # ESLint
npm run type-check    # TypeScript
npm run check         # Biome
npm run test          # Vitest
```
