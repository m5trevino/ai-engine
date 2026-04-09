import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: './',
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        apiKey: resolve(__dirname, 'api-key.html'),
        modelGarden: resolve(__dirname, 'model-garden.html'),
        toolSetup: resolve(__dirname, 'tool-setup.html'),
        buildTool: resolve(__dirname, 'build-tool.html'),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/v1': {
        target: 'http://localhost:3099',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:3099',
        changeOrigin: true,
      }
    }
  }
});
