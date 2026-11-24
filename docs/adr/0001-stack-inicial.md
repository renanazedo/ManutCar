# ADR 0001: Stack Tecnológica Inicial

**Status:** Aceito  
**Data:** 2024-01-15  
**Decisores:** Tech Lead, Arquiteto de Software  

## Contexto
Definição da stack tecnológica para o MVP do ManutCar (Incremento 1), considerando:
- Arquitetura multi-tenant, multi-usuário, multi-proprietário desde o dia 1
- Necessidade de type-safety end-to-end (Backend ↔ Frontend)
- Experiência de desenvolvedor (DX) e produtividade
- Custo operacional zero na fase de validação (Camada B)
- Escalabilidade para produção comercial (Camada A)

## Decisão

### Backend (API)
- **Python 3.12** + **FastAPI** (Async, OpenAPI nativo, Pydantic v2)
- **SQLAlchemy 2.0** (Async) + **Alembic** (Migrations)
- **PostgreSQL 16** (Neon Free Tier) com RLS nativo
- **Clerk** (Auth gerenciado, Organizations nativo, Webhooks)
- **Pydantic Settings** (Configuração tipada via `.env`)
- **Uvicorn/Gunicorn** (Produção)
- **uv** (Gerenciador de dependências rápido)

### Frontend Web (Gestores)
- **Next.js 14** (App Router, Server Components, SSR/ISR)
- **TypeScript 5** (Strict mode)
- **Tailwind CSS** + **Shadcn/UI** (Radix UI primitives)
- **React Query (TanStack Query)** (Server state)
- **Zustand** (Client state simples)
- **React Hook Form + Zod** (Formulários + Validação)
- **Dexie.js** (IndexedDB para PWA Offline-First)
- **next-pwa (Workbox)** (Service Worker)

### Mobile Motorista (Incremento 1)
- **PWA** via Next.js (mesmo codebase web)
- **Service Workers** + **IndexedDB** (Offline-First para Checklist/Abastecimento)

### Infraestrutura Inicial (Camada B - Custo Zero)
- **Vercel Hobby** (Frontend)
- **Render Free** (Backend Web Service Docker)
- **Neon Free** (PostgreSQL Serverless + PgBouncer)
- **Clerk Hobby** (Auth)
- **Cloudflare R2** (Storage S3-compatível, Zero Egress)
- **Resend Free** (E-mail transacional)
- **Firebase FCM Spark** (Push Notifications)
- **GitHub Actions** (CI/CD)

### Monorepo & Tooling
- **pnpm 9** (Workspaces)
- **Turborepo** (Build pipeline, cache remoto)
- **Lefthook** (Git hooks: ruff, mypy, eslint, prettier, gitleaks)
- **Prettier** (Formatação unificada)
- **Vitest** (Testes unitários Frontend)
- **Pytest** (Testes unitários/integração Backend)

### Arquitetura de Dados
- **Monorepo** com packages compartilhados:
  - `@manutcar/db` (SQLAlchemy models + Alembic)
  - `@manutcar/schemas` (Pydantic v2 contracts)
  - `@manutcar/ui` (Componentes React/Shadcn)
  - `@manutcar/config` (ESLint, TSConfig, Tailwind presets)

## Consequências

### Positivas
- Type-safety completo: Pydantic (Backend) → TypeScript (Frontend) via schemas compartilhados
- DX excelente: Hot reload, type hints, autocompletion em toda a stack
- Multi-tenancy nativo: Clerk Organizations + PostgreSQL RLS + `organization_id` NOT NULL
- Custo zero para validação: Todos os serviços têm tiers gratuitos generosos
- Portabilidade: Stack 100% cloud-agnostic, migração Camada B → A sem reescrita

### Negativas/Riscos
- **Render Free:** Cold starts (>30s), suspensão por inatividade, sem VPC
- **Neon Free:** Limite ~0.5-1GB, compute hours limitados, suspensão por inatividade
- **Clerk Hobby:** Limite de MAUs/Organizações, sem DPA assinado padrão
- **PWA vs Nativo:** Limitações de APIs nativas (Bluetooth, Background Sync avançado) no Inc 1
- **Sem Redis/Workers:** Processamentos assíncronos adiados (pg_cron ou síncrono no Inc 1)

## Alternativas Consideradas
| Opção | Backend | Frontend | Auth | Banco | Veredito |
|-------|---------|----------|------|-------|----------|
| Node.js/NestJS | ❌ Menos type-safe p/ Data/IA | ✅ | Clerk | PostgreSQL | Rejeitado: Python superior p/ ecossistema Data/IA futuro |
| Go/Fiber | ✅ Performance | ❌ DX inferior p/ Fullstack | Clerk | PostgreSQL | Rejeitado: Curva de aprendizado, ecossistema menor |
| Next.js API Routes | ❌ Não escala p/ workers complexos | ✅ | NextAuth | PostgreSQL | Rejeitado: Separação Backend/Frontend necessária |
| Supabase Auth | ✅ | ✅ | ❌ Menos maduro p/ Organizations | Supabase (PG) | Rejeitado: Vendor lock-in, Clerk superior p/ B2B |

## Próximos Passos
1. Implementar Fase 1 (Estrutura Monorepo) ✅
2. Implementar Fase 2 (Configurações Compartilhadas)
3. Implementar Fase 3 (Backend API: FastAPI + Healthcheck + Docker)
4. Implementar Fase 4 (Frontend Web: Next.js + Clerk + PWA)
5. Implementar Fase 5 (Infraestrutura: render.yaml, CI/CD, Git Hooks)
6. Validar `pnpm install` + `turbo run build` + Healthcheck local
