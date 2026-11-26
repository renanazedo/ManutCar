import Link from 'next/link';
import { Button } from '@manutcar/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@manutcar/ui/card';

type FeaturePlaceholderProps = {
  title: string;
  description: string;
};

export function FeaturePlaceholder({ title, description }: FeaturePlaceholderProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <p className="text-sm font-medium text-primary">Protótipo em desenvolvimento</p>
          <CardTitle className="text-2xl">{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-gray-600 dark:text-gray-400">{description}</p>
          <p className="text-sm text-gray-500">
            Este módulo ainda não está disponível nesta versão.
          </p>
          <Button asChild>
            <Link href="/">Voltar ao início</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
