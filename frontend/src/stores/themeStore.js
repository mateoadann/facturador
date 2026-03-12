import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useThemeStore = create(
  persist(
    (set) => ({
      darkMode: false,
      toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
      setDarkMode: (enabled) => set({ darkMode: !!enabled }),
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({ darkMode: state.darkMode }),
    }
  )
)
