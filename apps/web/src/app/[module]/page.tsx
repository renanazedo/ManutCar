import { notFound } from 'next/navigation';
import { FeaturePlaceholder } from '@/components/feature-placeholder';

const modules: Record<string, { title: string; description: string }> = {
  fleet: {
    title: 'Frota',
    description: 'Cadastro e acompanhamento de veículos, proprietários e motoristas.',
  },
  maintenance: {
    title: 'Manutenção',
    description: 'Planos preventivos, solicitações, ordens de serviço e garantias.',
  },
  fuel: {
    title: 'Abastecimento',
    description: 'Registros de abastecimento, odômetro e consumo do veículo.',
  },
  documents: {
    title: 'Documentos',
    description: 'Obrigações, vencimentos, multas e habilitações.',
  },
  checklist: {
    title: 'Checklist',
    description: 'Inspeções diárias e vistorias de veículos.',
  },
  finance: {
    title: 'Financeiro',
    description: 'Receitas, despesas e relatórios da operação.',
  },
};

export default function ModulePlaceholderPage({
  params,
}: {
  params: { module: string };
}) {
  const feature = modules[params.module];
  if (!feature) notFound();

  return <FeaturePlaceholder {...feature} />;
}
