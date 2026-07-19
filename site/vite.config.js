import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' makes the built site portable (works from any folder / static host)
export default defineConfig({
  base: './',
  plugins: [react()],
})
