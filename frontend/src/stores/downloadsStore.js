import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useDownloadsStore = create(
  persist(
    (set, get) => ({
      zipTasks: [],
      addZipTask: (task) => {
        const current = get().zipTasks
        if (current.some((t) => t.taskId === task.taskId)) return
        set({ zipTasks: [...current, task] })
      },
      removeZipTask: (taskId) => {
        set((state) => ({
          zipTasks: state.zipTasks.filter((task) => task.taskId !== taskId),
        }))
      },
      clearZipTasks: () => set({ zipTasks: [] }),
    }),
    {
      name: 'downloads-storage',
      partialize: (state) => ({
        zipTasks: state.zipTasks,
      }),
    }
  )
)
