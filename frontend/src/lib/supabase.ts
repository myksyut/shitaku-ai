import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase environment variables: VITE_SUPABASE_URL and VITE_SUPABASE_KEY are required')
}

// Cookieベースのストレージ（localStorageの問題を回避）
const cookieStorage = {
  getItem: (key: string): string | null => {
    const cookies = document.cookie.split(';')
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=')
      if (name === key) {
        return decodeURIComponent(value)
      }
    }
    return null
  },
  setItem: (key: string, value: string): void => {
    // 7日間有効、SameSite=Laxでセキュリティを確保
    document.cookie = `${key}=${encodeURIComponent(value)}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`
  },
  removeItem: (key: string): void => {
    document.cookie = `${key}=; path=/; max-age=0`
  },
}

export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    storage: cookieStorage,
    detectSessionInUrl: false,
  },
})
