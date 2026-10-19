import { defineConfig, loadEnv } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiPort = env.API_PORT || '8000'

  return {
    plugins: [svelte(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: `http://127.0.0.1:${apiPort}`,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
