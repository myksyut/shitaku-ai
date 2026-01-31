---
name: frontend/vite-react-spec
description: Vite + React SPAの技術仕様。プロジェクト構造、ルーティング、API通信パターンを定義。
---

# Vite + React 技術仕様

## プロジェクト構造
```
frontend/
├── src/
│   ├── main.tsx              # エントリーポイント
│   ├── App.tsx               # ルートコンポーネント
│   ├── index.css             # グローバルスタイル（Tailwind）
│   ├── components/
│   │   ├── ui/               # 基本UIコンポーネント
│   │   └── features/         # 機能コンポーネント
│   ├── hooks/                # カスタムフック
│   ├── lib/                  # ユーティリティ
│   │   └── api.ts            # APIクライアント
│   ├── types/                # 型定義
│   └── test/                 # テストセットアップ
├── public/                   # 静的ファイル
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── biome.json
└── Dockerfile
```

## Vite設定

### vite.config.ts
```typescript
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
  },
})
```

### 環境変数
```typescript
// Viteでは import.meta.env を使用
// VITE_ プレフィックスが必要
const API_URL = import.meta.env.VITE_API_URL

// process.env は使用不可（ブラウザ環境）
```

## コンポーネント設計

### 命名規則
- コンポーネント: PascalCase
- フック: `use`プレフィックス
- ユーティリティ: camelCase

### Props設計
```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

export function Button({ variant = 'primary', size = 'md', children }: ButtonProps) {
  // implementation
}
```

## ルーティング（React Router）

### 基本設定
```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/users/:id" element={<UserDetail />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### パラメータ取得
```tsx
import { useParams } from 'react-router-dom'

function UserDetail() {
  const { id } = useParams<{ id: string }>()
  // ...
}
```

## API通信

### APIクライアント
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL

export async function apiClient<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`)
  if (!response.ok) throw new Error('API request failed')
  return response.json()
}
```

## スタイリング

### Tailwind CSS v4
```css
/* src/index.css */
@import "tailwindcss";
```

### クラス結合（clsx + tailwind-merge）
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
npm run check         # Biome lint/format
npm run type-check    # TypeScript型チェック
npm run test          # Vitest
npm run build         # 本番ビルド
```
