import { create } from 'zustand'

let toastId = 0

export const useToastStore = create((set) => ({
  toasts: [],

  addToast: ({ type = 'info', title, message, duration = 5000 }) => {
    const id = ++toastId
    set((state) => ({
      toasts: [...state.toasts, { id, type, title, message }],
    }))

    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }))
      }, duration)
    }

    return id
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },
}))

// Helper functions
export const toast = {
  success: (title, message) =>
    useToastStore.getState().addToast({ type: 'success', title, message }),
  error: (title, message) =>
    useToastStore.getState().addToast({ type: 'error', title, message }),
  warning: (title, message) =>
    useToastStore.getState().addToast({ type: 'warning', title, message }),
  info: (title, message) =>
    useToastStore.getState().addToast({ type: 'info', title, message }),
}
