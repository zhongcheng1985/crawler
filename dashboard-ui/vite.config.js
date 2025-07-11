import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteMockServe } from 'vite-plugin-mock'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    // viteMockServe({
    //   mockPath: 'src/mock',
    //   localEnabled: false,
    //   prodEnabled: false,
    //   logger: true,
    //   supportTs: true
    // })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  css: {
    preprocessorOptions: {
      less: {
        javascriptEnabled: true,
        modifyVars: {
          'primary-color': '#1890ff'
        }
      }
    }
  },
  server: {
    port: 8060,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8050',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, '/')
      }
    }
  }
})