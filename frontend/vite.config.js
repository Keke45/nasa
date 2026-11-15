import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/intelligence-api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(/^\/intelligence-api/, '/api'),
      },
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})