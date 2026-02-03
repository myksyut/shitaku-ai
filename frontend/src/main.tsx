import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient()

const rootElement = document.getElementById('root')
if (rootElement === null) {
  throw new Error('Root element not found')
}

createRoot(rootElement).render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>,
)
