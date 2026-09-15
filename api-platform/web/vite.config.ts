import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import portfinder from 'portfinder'

// 自动检测可用端口
portfinder.basePort = 3000
portfinder.highestPort = 9999

const getPort = async () => {
  try {
    const port = await portfinder.getPortPromise()
    return port
  } catch {
    return 3000
  }
}

export default defineConfig(async () => {
  const port = await getPort()
  const portChanged = port !== 3000
  
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port,
      host: '0.0.0.0',
      onPortWarn: () => {},  // 禁用默认端口警告
      // 允许外部访问的域名（Cloudflare Tunnel 等内网穿透）
      allowedHosts: true,  // 允许所有主机
      // 禁用 HMR（Cloudflare Tunnel 下 WebSocket 有问题）
      hmr: false,
      // API 代理配置
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          logLevel: 'silent',
        },
        // 【L5】存活探针（含环境标识）—— 前端环境徽标据此判断当前环境
        '/health': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          logLevel: 'silent',
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'antd-vendor': ['antd', '@ant-design/icons'],
          },
        },
      },
    },
  }
})
