/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@manutcar/ui', '@manutcar/schemas'],
  experimental: {
    optimizePackageImports: ['@manutcar/ui', 'lucide-react'],
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.r2.cloudflarestorage.com',
      },
      {
        protocol: 'https',
        hostname: 'img.clerk.com',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
};

// Wrapper PWA (next-pwa / @ducanh2912/next-pwa)
// Usamos import dinâmico para não quebrar build se não instalado ainda
let withPWA = (config) => config;
try {
  // Tentativa 1: @ducanh2912/next-pwa (moderno, suporta Next 14+ App Router bem)
  const { default: nextPwa } = await import('@ducanh2912/next-pwa');
  withPWA = nextPwa({
    dest: 'public',
    register: true,
    skipWaiting: true,
    disable: process.env.NODE_ENV === 'development',
    // Workbox options
    workboxOptions: {
      // Estratégias customizadas conforme ADR 0002
      runtimeCaching: [
        {
          // Static Assets (JS, CSS, Fonts) - CacheFirst
          urlPattern: ({ url }) => url.pathname.startsWith('/_next/static/'),
          handler: 'CacheFirst',
          options: {
            cacheName: 'static-assets',
            expiration: { maxEntries: 200, maxAgeSeconds: 365 * 24 * 60 * 60 },
            cacheableResponse: { statuses: [0, 200] },
          },
        },
        {
          // API GET (Templates, Veículos, Config) - StaleWhileRevalidate
          urlPattern: ({ url }) => url.pathname.startsWith('/api/') && url.searchParams.get('cache') === 'true',
          handler: 'StaleWhileRevalidate',
          options: {
            cacheName: 'api-get-cache',
            expiration: { maxEntries: 100, maxAgeSeconds: 24 * 60 * 60 }, // 24h
            cacheableResponse: { statuses: [0, 200] },
          },
        },
        {
          // Navigation (HTML) - NetworkFirst fallback offline.html
          urlPattern: ({ request }) => request.mode === 'navigate',
          handler: 'NetworkFirst',
          options: {
            cacheName: 'navigation-cache',
            networkTimeoutSeconds: 3,
            cacheableResponse: { statuses: [0, 200] },
          },
        },
        {
          // Imagens R2 / Clerk - CacheFirst
          urlPattern: ({ url }) =>
            url.hostname.endsWith('.r2.cloudflarestorage.com') ||
            url.hostname === 'img.clerk.com',
          handler: 'CacheFirst',
          options: {
            cacheName: 'external-images',
            expiration: { maxEntries: 50, maxAgeSeconds: 30 * 24 * 60 * 60 },
            cacheableResponse: { statuses: [0, 200] },
          },
        },
      ],
    },
  });
} catch (e) {
  try {
    // Fallback: next-pwa (clássico)
    const { default: nextPwa } = await import('next-pwa');
    withPWA = nextPwa({
      dest: 'public',
      register: true,
      skipWaiting: true,
      disable: process.env.NODE_ENV === 'development',
    });
  } catch (e2) {
    console.warn('[next.config] PWA plugin não encontrado. Instale @ducanh2912/next-pwa ou next-pwa.');
  }
}

export default withPWA(nextConfig);
