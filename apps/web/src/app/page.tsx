'use client';

import { useUser } from '@clerk/nextjs';
import { Button } from '@manutcar/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@manutcar/ui/card';
import { Truck, Wrench, Fuel, FileText, CheckCircle, BarChart } from 'lucide-react';
import Link from 'next/link';

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
            <Button variant="ghost" asChild>
              <Link href="/sign-in?redirect_url=/">Sair</Link>
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
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="text-sm font-medium">API Online</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Conexão com backend estabelecida</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="text-sm font-medium">Banco de Dados</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">PostgreSQL (Neon) conectado</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-yellow-500" />
                  <span className="text-sm font-medium">PWA</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Service Worker registrado</p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>
    </div>
  );
}
