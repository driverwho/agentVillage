import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/agentVillage/' : '/',
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api/ws': {
        target: 'http://localhost:8000',
        ws: true,
      },
      '/api': 'http://localhost:8000',
      '/world': 'http://localhost:8000',
      '/time': 'http://localhost:8000',
      '/ws': {
        target: 'http://localhost:8000',
        ws: true,
      },
      '/img': 'http://localhost:8000',
    }
  }
}))
