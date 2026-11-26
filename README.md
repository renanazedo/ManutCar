# ManutCar

Monorepo em desenvolvimento para gestão de frota, manutenção e operação veicular.
O projeto prioriza ferramentas gratuitas e validação local; os módulos ainda não
representam um protótipo funcional completo.

## Requisitos locais

- Node.js 20 ou superior e pnpm 9
- Python 3.12 ou superior e [uv](https://docs.astral.sh/uv/)

Os testes locais usam SQLite em memória e não exigem provisionar serviços cloud.
As telas de autenticação Clerk precisam de uma chave publicável configurada para
funcionar; sem ela, a aplicação informa que a configuração está ausente.

## Instalação

Na raiz do repositório:

```bash
pnpm install --frozen-lockfile
cd apps/api
uv sync --locked
```

## Verificações

```bash
pnpm --filter @manutcar/web lint
pnpm --filter @manutcar/web typecheck
pnpm --filter @manutcar/web test
pnpm --filter @manutcar/web build
```

Para a API, a suíte usa SQLite em memória:

```bash
cd apps/api
DATABASE_URL='sqlite+aiosqlite:///:memory:' uv run pytest
```

O CI também executa testes da API, build da imagem Docker e build do frontend.
Ruff e MyPy estão configurados nos hooks locais, mas ainda não são gates do CI:
as checagens completas encontram pendências preexistentes no código.

## Estrutura

- `apps/api`: API FastAPI e testes pytest
- `apps/web`: aplicação Next.js e testes Vitest
- `packages/db`: modelos SQLAlchemy e migrações Alembic
- `packages/schemas`: contratos Pydantic compartilhados
- `packages/ui`: componentes React compartilhados

Consulte [a visão do produto](./visao.md), [as regras de negócio](./regra_negocio.md)
e o [roadmap](./roadmap.md) para escopo e decisões do projeto.
