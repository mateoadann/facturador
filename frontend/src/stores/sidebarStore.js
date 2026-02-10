import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useSidebarStore = create(
  persist(
    (set) => ({
      isCollapsed: false,
      toggle: () => set((state) => ({ isCollapsed: !state.isCollapsed })),
      collapse: () => set({ isCollapsed: true }),
      expand: () => set({ isCollapsed: false }),
    }),
    {
      name: 'sidebar-storage',
    }
  )
)
