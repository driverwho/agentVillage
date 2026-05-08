import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  visible: boolean
}

let nextId = 0
export const toasts = ref<Toast[]>([])

export function showToast(message: string, duration = 2500): void {
  const id = nextId++
  const toast: Toast = { id, message, visible: true }
  toasts.value.push(toast)
  setTimeout(() => {
    const t = toasts.value.find(t => t.id === id)
    if (t) t.visible = false
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 300)
  }, duration)
}
