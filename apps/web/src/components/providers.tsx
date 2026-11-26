'use client';

import { useAuth } from '@clerk/nextjs';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@manutcar/ui/toaster';
import { ReactNode, useEffect, useState } from 'react';
import { clearPrivatePwaCaches } from '@/lib/pwa-cache';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  const { userId } = useAuth();

  useEffect(() => {
    queryClient.clear();

    if ('caches' in window) {
      void clearPrivatePwaCaches(window.caches).catch((error: unknown) => {
        console.error('Failed to clear private PWA caches after account change.', error);
      });
    }
  }, [queryClient, userId]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster />
    </QueryClientProvider>
  );
}