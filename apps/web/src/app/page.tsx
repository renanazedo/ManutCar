'use client';

import { useClerk, useUser } from '@clerk/nextjs';
import { Button } from '@manutcar/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@manutcar/ui/card';
import { Truck, Wrench, Fuel, FileText, CheckCircle, BarChart } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

type ServiceStatus = 'checking' | 'online' | 'offline' | 'not-configured';
type PwaStatus = 'checking' | 'registered' | 'not-registered' | 'unsupported';

type HealthResponse = {
  status: string;
  service: string;
  database: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '');

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    typeof value.status === 'string' &&
    'service' in value &&
    typeof value.service === 'string' &&
    'database' in value &&
    typeof value.database === 'string'
  );
}

function indicatorColor(status: ServiceStatus | PwaStatus) {
  if (status === 'online' || status === 'registered') return 'bg-green-500';
  if (status === 'checking') return 'bg-yellow-500';
  if (status === 'not-configured' || status === 'unsupported') return 'bg-gray-400';
  return 'bg-red-500';
}

const modules = [
  { name: 'Frota', icon: Truck, href: '/fleet', description: 'Veículos, proprietários e motoristas' },
  { name: 'Manutenção', icon: Wrench, href: '/maintenance', description: 'Preventiva, corretiva e garantias' },
  { name: 'Abastecimento', icon: Fuel, href: '/fuel', description: 'Consumo, odômetro e anomalias' },
  { name: 'Documentos', icon: FileText, href: '/documents', description: 'IPVA, licenciamento, multas, CNH' },
  { name: 'Checklist', icon: CheckCircle, href: '/checklist', description: 'Inspeção diária e vistorias' },
  { name: 'Financeiro', icon: BarChart, href: '/finance', description: 'Receitas, despesas e relatórios' },
];

export default function DashboardPage() {
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  const [apiStatus, setApiStatus] = useState<ServiceStatus>(
    apiBaseUrl ? 'checking' : 'not-configured',
  );
  const [databaseStatus, setDatabaseStatus] = useState<ServiceStatus>(
    apiBaseUrl ? 'checking' : 'not-configured',
  );
  const [pwaStatus, setPwaStatus] = useState<PwaStatus>('checking');

  useEffect(() => {
    if (!apiBaseUrl) return;

    let active = true;
    const checkApiHealth = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/health`, { cache: 'no-store' });
        const payload: unknown = await response.json();

        if (!isHealthResponse(payload) || payload.service !== 'manutcar-api') {
          throw new Error('API returned an invalid health response.');
        }

        if (active) {
          setApiStatus('online');
          setDatabaseStatus(payload.database === 'ok' ? 'online' : 'offline');
        }
      } catch (error) {
        console.error('API health check failed.', error);
        if (active) {
          setApiStatus('offline');
          setDatabaseStatus('offline');
        }
      }
    };

    void checkApiHealth();
    const interval = window.setInterval(() => void checkApiHealth(), 30_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!('serviceWorker' in navigator)) {
      setPwaStatus('unsupported');
      return;
    }

    let active = true;
    const checkRegistration = async () => {
      try {
        const registration = await navigator.serviceWorker.getRegistration();
        if (active) setPwaStatus(registration ? 'registered' : 'not-registered');
      } catch (error) {
        console.error('PWA registration check failed.', error);
        if (active) setPwaStatus('not-registered');
      }
    };

    navigator.serviceWorker.addEventListener('controllerchange', checkRegistration);
    void checkRegistration();
    const retry = window.setTimeout(() => void checkRegistration(), 1000);
    return () => {
      active = false;
      navigator.serviceWorker.removeEventListener('controllerchange', checkRegistration);
      window.clearTimeout(retry);
    };
  }, []);

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Bem-vindo ao ManutCar</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Faça login ou crie sua conta para começar a gerenciar sua frota.
            </p>
            <Button asChild size="lg">
              <Link href="/sign-in">Entrar com Clerk</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="border-b bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">ManutCar</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {user.fullName || user.primaryEmailAddress?.emailAddress}
            </span>
            <Button
              variant="ghost"
              onClick={() =>
                void signOut({ redirectUrl: '/sign-in' }).catch((error: unknown) => {
                  console.error('Sign out failed.', error);
                })
              }
            >
              Sair
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Olá, {user.firstName || 'Motorista'}! 👋
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Escolha um módulo abaixo para começar a gerenciar sua operação.
          </p>
        </section>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((module) => (
            <Link key={module.name} href={module.href} className="block">
              <Card className="h-full transition-shadow hover:shadow-lg cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <module.icon className="h-8 w-8 text-primary" />
                    <CardTitle className="text-lg">{module.name}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {module.description}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        <section className="mt-16">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Status do Sistema
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              {
                title: 'API',
                status: apiStatus,
                label: {
                  checking: 'Verificando conexão',
                  online: 'API respondendo',
                  offline: 'API indisponível',
                  'not-configured': 'URL não configurada',
                }[apiStatus],
              },
              {
                title: 'Banco de Dados',
                status: databaseStatus,
                label: {
                  checking: 'Verificando conexão',
                  online: 'Banco conectado',
                  offline: 'Banco indisponível',
                  'not-configured': 'Não verificado',
                }[databaseStatus],
              },
              {
                title: 'PWA',
                status: pwaStatus,
                label: {
                  checking: 'Verificando registro',
                  registered: 'Service Worker registrado',
                  'not-registered': 'Service Worker não registrado',
                  unsupported: 'Não suportado neste navegador',
                }[pwaStatus],
              },
            ].map(({ title, status, label }) => (
              <Card key={title}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className={`h-3 w-3 rounded-full ${indicatorColor(status)}`} />
                    <span className="text-sm font-medium">{title}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{label}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
