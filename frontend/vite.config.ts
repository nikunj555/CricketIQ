import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/videos': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/thumbnails': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 5173,
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'lucide-react', 'three', '@react-three/fiber', '@react-three/drei', 'recharts', 'framer-motion'],
  },
  build: {
    chunkSizeWarningLimit: 1200,
  },
})
