import { describe, expect, it, vi } from 'vitest';
import { clearPrivatePwaCaches } from './pwa-cache';

describe('clearPrivatePwaCaches', () => {
  it('clears session and legacy caches while preserving static runtime assets', async () => {
    const cacheStorage = {
      keys: vi.fn().mockResolvedValue([
        'api-get-cache',
        'navigation-cache',
        'external-images',
        'workbox-precache-v2',
        'static-assets',
      ]),
      delete: vi.fn().mockResolvedValue(true),
    };

    await clearPrivatePwaCaches(cacheStorage);

    expect(cacheStorage.delete.mock.calls.map(([cacheName]) => cacheName)).toEqual([
      'api-get-cache',
      'navigation-cache',
      'external-images',
      'workbox-precache-v2',
    ]);
  });
});
