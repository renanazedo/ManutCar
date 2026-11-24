import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClerkProvider } from '@clerk/nextjs';
import { ReactNode, useState } from 'react';
import { Toaster } from '@manutcar/ui/toaster';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'ManutCar - Gestão Veicular Inteligente',
  description: 'Plataforma SaaS multi-tenant para gestão de frota, manutenção, abastecimento e finanças.',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: 'ManutCar' },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

function getQueryClient() {
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

export default function RootLayout({ children }: { children: ReactNode }) {
  const [queryClient] = useState(getQueryClient);
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  if (!publishableKey) {
    return (
      <html lang="pt-BR">
        <body className="flex h-screen items-center justify-center bg-background">
          <div className="text-center p-4">
            <h1 className="text-xl font-semibold text-destructive">Configuração Faltando</h1>
            <p className="mt-2 text-muted-foreground">
              Variável <code>NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> não definida.
            </p>
          </div>
        </body>
      </html>
    );
  }

  return (
    <html lang="pt-BR" suppressHydrationWarning className={inter.variable}>
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#2563eb" />
      </head>
      <body className={`${inter.className} antialiased bg-background text-foreground`}>
        <ClerkProvider publishableKey={publishableKey}>
          <QueryClientProvider client={queryClient}>
            {children}
            <Toaster />
          </QueryClientProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
