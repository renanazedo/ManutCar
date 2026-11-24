Você é o Arquiteto de Software sênior do projeto **ManutCar** (plataforma SaaS multi-tenant, multiusuário e multiproprietário de gestão veicular).
Leia o arquivo de contexto `pre_zero_jRSB23.md` (se presente na raiz) e execute estritamente o **Bloco 1: Estrutura do Monorepo, Quality Gates e Infraestrutura como Código (IaC)**.

### Tarefas a Executar Agora:

1. **Estrutura de Diretórios do Monorepo (`pnpm workspaces` + `Turborepo`):**
   Crie a seguinte árvore de pastas com arquivos iniciais válidos (`README.md`, `__init__.py` ou `package.json`):
   - `apps/api` (Backend Python 3.12 + FastAPI)
   - `apps/web` (Frontend Next.js 14 App Router + TypeScript)
   - `packages/db` (Camada de persistência: SQLAlchemy 2.0 + Alembic)
   - `packages/schemas` (Contratos Pydantic v2 compartilhados)
   - `packages/ui` (Componentes compartilhados React / Shadcn)
   - `packages/config` (Configurações compartilhadas ESLint, TypeScript e Tailwind)
   - `docs/adr` (Registros de Decisão Arquitetural, incluindo `0001-stack-inicial.md` e `0002-offline-sync-strategy.md`)

2. **Configuração Raiz do Monorepo:**
   - `pnpm-workspace.yaml` mapeando `apps/*` e `packages/*`.
   - `package.json` na raiz com scripts globais (`dev`, `build`, `lint`, `typecheck`, `test`) usando `turbo`.
   - `turbo.json` configurando pipeline de tarefas (`build`, `lint`, `typecheck`, `test`, `dev`).
   - `.gitignore` completo para Python (`__pycache__`, `.venv`, `.mypy_cache`, `.ruff_cache`), Node/Next.js (`node_modules`, `.next`, `.turbo`) e arquivos `.env`.
   - `.env.example` documentando todas as variáveis necessárias (PostgreSQL/Neon, Clerk, Cloudflare R2, Resend, Firebase FCM e URLs da aplicação).

3. **Quality Gates e Git Hooks (`Lefthook`):**
   - `lefthook.yml` configurado para rodar em `pre-commit`:
     - `ruff check .` e `mypy app` em `apps/api`
     - `pnpm lint` e `pnpm typecheck` em `apps/web`
     - `gitleaks detect --source . -v` para bloqueio de vazamento de segredos.

4. **Configuração Inicial do Backend (`apps/api`):**
   - `apps/api/pyproject.toml` gerenciado via `uv`, incluindo dependências core (`fastapi`, `uvicorn[standard]`, `gunicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `svix`, `boto3`, `resend`, `firebase-admin`) e dev (`pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`).
   - Configurar `ruff` e `mypy` (modo estrito) dentro de `pyproject.toml`.
   - Criar `apps/api/app/main.py` com instância FastAPI, configuração de CORS via `pydantic-settings` e endpoint de healthcheck `GET /api/v1/health` retornando `{"status": "ok", "service": "manutcar-api"}`.
   - Criar `apps/api/Dockerfile` multi-stage otimizado com `python:3.12-slim` rodando `gunicorn` com workers `uvicorn`.

5. **Configuração Inicial do Frontend (`apps/web`):**
   - `apps/web/package.json`, `tsconfig.json` (strict mode), `next.config.mjs` e estrutura inicial `src/app/layout.tsx` e `src/app/page.tsx`.

6. **Infraestrutura e CI/CD:**
   - `render.yaml` na raiz configurando o Web Service da API (`apps/api`) para deploy no Render.
   - `.github/workflows/ci.yml` executando lint, typecheck e pytest em cada Pull Request.

### Regras Restritivas:
- **NÃO** implemente ainda os modelos de banco de dados das 34 entidades nem endpoints de negócio (isso será feito no Bloco 2 e Bloco 3).
- Garanta que todos os arquivos criados tenham sintaxe válida e zero placeholders quebrados.
- Ao finalizar, liste exatamente os comandos que devo rodar no terminal para instalar as dependências e validar o healthcheck local.
