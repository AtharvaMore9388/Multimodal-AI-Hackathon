import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/chat': 'http://localhost:8000',
      '/quiz': 'http://localhost:8000',
      '/learner': 'http://localhost:8000',
      '/topics': 'http://localhost:8000',
      '/evaluation': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/audio': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/docs': 'http://localhost:8000',
      '/openapi.json': 'http://localhost:8000',
    }
  }
});
