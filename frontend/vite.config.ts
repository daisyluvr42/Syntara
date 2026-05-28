import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const frontendPort = Number(env.FRONTEND_PORT || 5173)
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8888'

  return {
    plugins: [react()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return

            if (
              id.includes('/@codemirror/lang-markdown/') ||
              id.includes('/@codemirror/lang-html/') ||
              id.includes('/@codemirror/lang-css/') ||
              id.includes('/@codemirror/lang-javascript/') ||
              id.includes('/@codemirror/autocomplete/') ||
              id.includes('/@codemirror/lint/') ||
              id.includes('/@lezer/markdown/') ||
              id.includes('/@lezer/html/') ||
              id.includes('/@lezer/css/') ||
              id.includes('/@lezer/javascript/')
            ) {
              return 'editor-language'
            }

            if (
              id.includes('/@codemirror/') ||
              id.includes('/@lezer/') ||
              id.includes('/crelt/') ||
              id.includes('/style-mod/') ||
              id.includes('/w3c-keyname/')
            ) {
              return 'editor-core'
            }

            if (
              id.includes('/react/') ||
              id.includes('/react-dom/') ||
              id.includes('/scheduler/') ||
              id.includes('/react-split-pane/')
            ) {
              return 'react-vendor'
            }
          },
        },
      },
    },
    server: {
      port: frontendPort,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
