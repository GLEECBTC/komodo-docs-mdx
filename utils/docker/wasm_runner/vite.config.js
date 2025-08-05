import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 3000,
    strictPort: true,
    host: '0.0.0.0'
  },
  preview: {
    port: 3000,
    strictPort: true,
    host: '0.0.0.0'
  },
  build: {
    rollupOptions: {
      external: [
        '/kdf/kdflib.js'
      ]
    }
  }
}); 