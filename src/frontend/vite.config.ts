import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
<<<<<<< HEAD
        target: 'http://127.0.0.1:8000',
=======
        target: 'http://127.0.0.1:8010',
>>>>>>> f20a82dbd64987bf7cbe2877e18d1aa666af4469
        changeOrigin: true,
      },
    },
  },
});
