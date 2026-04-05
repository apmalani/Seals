import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Mapbox GL v3 workers expect modern syntax; older targets can break the worker bundle.
export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext',
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'esnext',
    },
  },
})
