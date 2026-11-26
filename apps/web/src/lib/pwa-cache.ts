const privateCacheNames = new Set([
  'api-get-cache',
  'navigation-cache',
  'external-images',
  'apis',
  'pages',
  'pages-rsc',
  'pages-rsc-prefetch',
  'next-data',
  'next-image',
  'static-image-assets',
  'static-data-assets',
  'cross-origin',
  'start-url',
]);

export async function clearPrivatePwaCaches(
  cacheStorage: Pick<CacheStorage, 'keys' | 'delete'>,
): Promise<void> {
  const cacheNames = await cacheStorage.keys();
  const privateCaches = cacheNames.filter(
    (cacheName) => privateCacheNames.has(cacheName) || cacheName.startsWith('workbox-precache-'),
  );

  await Promise.all(privateCaches.map((cacheName) => cacheStorage.delete(cacheName)));
}
