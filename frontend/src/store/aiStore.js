import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * AI provider preference, persisted across sessions.
 *   'auto'   → Ollama first, Groq cloud fallback when local is down (default)
 *   'ollama' → force local Ollama only
 *   'groq'   → force Groq cloud only
 */
export const useAIStore = create(
  persist(
    (set) => ({
      provider: 'auto',
      setProvider: (provider) => set({ provider }),
    }),
    { name: 'xplor-ai-provider' }
  )
)
