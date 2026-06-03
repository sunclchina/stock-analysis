import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 端口分配约定：开发环境后端 8000，前端 8080；8081 保留给 Docker 调试版本
const apiTarget = process.env.VITE_API_PROXY || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8080,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        timeout: 120000,
        proxyTimeout: 120000,
      },
      '/ws': {
        target: apiTarget.replace('http', 'ws'),
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
