import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '');

  // Determine port based on environment
  // Test environment uses 5889, development uses 5888
  const isTest = mode === 'test' || process.env.NODE_ENV === 'test';
  const isDev = mode === 'development';
  const port = isTest ? 5889 : 5888;

  return {
  plugins: [
    react({
      include: "**/*.{jsx,js,ts,tsx}",
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json']
  },
  server: {
    host: '0.0.0.0', // Listen on all addresses
    port: port, // Dynamic port based on environment
    strictPort: true,
    hmr: {
      host: 'localhost',
      clientPort: port // Use same port for HMR WebSocket
    },
    watch: {
      usePolling: true, // This can help in containerized environments
      interval: 1000, // Polling interval for better performance in containers
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    sourcemap: false, // Disable sourcemaps for production builds
    minify: 'esbuild', // Use esbuild for minification
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  esbuild: {
    // In non-development environments, drop all console statements except console.error
    drop: isDev ? [] : ['console'],
    pure: isDev ? [] : ['console.log', 'console.info', 'console.debug', 'console.warn'],
  },
  preview: {
    port: port,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      'app.dev.agentleague.app'
    ]
  }
  };
});