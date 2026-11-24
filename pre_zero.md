# Prompt de Execução: Pré-Sprint 0 (Inception & Setup) — ManutCar

**Contexto:** Implementação do **Incremento 1 (MVP Core)** sobre a **Infraestrutura Inicial Camada B (Custo Zero)** conforme `DEC-020` e `DEC-021`.
**Referências Obrigatórias:** `visao.md`, `especificacao_funcional.md`, `regra_negocio.md`, `pendencias_decisoes.md` (ADRs), `roadmap.md`, `muda_regra.md`.

---

## 1. Validação de Pré-requisitos (Definition of Ready para Pré-Sprint)
> **Ação:** Confirmar se os artefatos abaixo estão **congelados (versão 2.1/3.1)** e alinhados. Se houver divergência, pare e alinhe com PO/Arquiteto.

- [ ] `visao.md` v1.1: Visão, Personas (B2C, B2B, B2B2C, Gestor), Princípios (Multi-tenancy, Privacy by Design), **Estratégia Duas Camadas (Sec 8)**.
- [ ] `especificacao_funcional.md` v2.1: 6 Módulos (FLT, MNT, ABS, FIN, DOC, CHK), RFs, Entidades, CAs. **Contexto Infra Sec 1**.
- [ ] `regra_negocio.md` v2.1: 10 Capítulos de RNs (Governança, Matriz RBAC, Financeiro, Odômetro, Manutenção, Docs/Multas, Checklist, Auditoria, Parâmetros OrgSettings, Critérios de Teste CT-RN-01 a 13).
- [ ] `pendencias_decisoes.md` v3.1: **23 ADRs (DEC-001 a DEC-023) RESOLVIDOS**. Stack definida (DEC-011), Infra Inicial (DEC-020), Adiamentos (DEC-021), Gatilhos Migração (DEC-022).
- [ ] `roadmap.md` v2.2: 3 Incrementos, 5 Sprints para Inc 1, **Pré-Sprint 0 detalhado (Sec 5.0)**.
- [ ] `muda_regra.md`: Verificar se há mudanças *pós* v2.1 que impactem o escopo do Inc 1.

---

## 2. Atividades Técnicas: Provisionamento Camada B (Custo Zero) — `DEC-020` / `roadmap.md` Sec 5.0

> **Responsável:** Tech Lead + DevOps. **Prazo:** 1-2 dias antes da Sprint 1.
> **Objetivo:** Ambiente `main` deployável, healthcheck verde, auth sincronizando, DB migrado.

### 2.1. Repositório Monorepo & Tooling (`DEC-011`)
- [ ] **Estrutura:** `apps/api` (FastAPI), `apps/web` (Next.js 14 App Router), `packages/db` (SQLAlchemy 2.0 + Alembic), `packages/schemas` (Pydantic), `packages/ui` (Shadcn/UI), `packages/config` (ESLint, TSConfig, Tailwind).
- [ ] **Gerenciador:** `pnpm` (workspaces) + `poetry`/`uv` (python) ou `rye`/`uv` para monorepo python/js unificado. **Recomendação:** `Turborepo` ou `Nx`.
- [ ] **Git Hooks:** `lefthook` (pre-commit: `ruff`, `mypy`, `eslint`, `prettier`, `gitleaks`; commit-msg: `conventional commits`).

### 2.2. Frontend: Vercel Hobby (`apps/web`)
- [ ] Importar repo no Vercel. Root: `apps/web`. Framework: Next.js.
- [ ] **Env Vars (Preview/Prod):**
  - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
  - `NEXT_PUBLIC_API_URL` (URL Render)
  - `NEXT_PUBLIC_FCM_VAPID_KEY` (Push PWA)
  - `NEXT_PUBLIC_APP_URL` (Domínio Vercel)
- [ ] **PWA Config:** `next-pwa` (Workbox) + `manifest.json` + Service Worker offline-first (IndexedDB/Dexie.js para Checklist/Abastecimento `RN-CHK-02`, `RF-ABS-01`).
- [ ] **Shadcn/UI + Tailwind:** Instalado e tema base (Light/Dark) configurado.

### 2.3. Backend: Render Free Web Service (`apps/api`)
- [ ] **Dockerfile:** Multi-stage (builder -> runtime python 3.12-slim). Non-root user. Healthcheck endpoint `GET /health` (DB connection + Redis ping se houver).
- [ ] **Env Vars (Secrets no Render):**
  - `DATABASE_URL` (Neon Pooled Connection String `pgbouncer`)
  - `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET` (`svix` verification)
  - `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`
  - `RESEND_API_KEY`
  - `FCM_SERVICE_ACCOUNT_JSON` (Base64 encoded) ou `FIREBASE_CREDENTIALS_PATH`
  - `SETTINGS_TZ=America/Sao_Paulo` (`DEC-014`, `RN-AUD-04`)
  - `APP_ENV=development`
- [ ] **Start Command:** `gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT app.main:app` (Ajustar workers p/ RAM free tier).
- [ ] **Healthcheck Path:** `/health` (Render config).

### 2.4. Banco de Dados: Neon Free Tier (PostgreSQL 16)
- [ ] Criar Projeto `manutcar-dev`. Branch `main`.
- [ ] **Extensões Obrigatórias (SQL/Console Neon):** `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "pg_trgm";` (Para busca trigram em placas, nomes).
- [ ] **Connection Pooling:** Habilitar PgBouncer (Session Mode). Usar *Pooled URL* no Render/Vercel.
- [ ] **RLS (Row Level Security):** **CRÍTICO `DEC-001`, `RN-FLT-07`, `RN-FLT-15`**. Preparar script SQL para habilitar RLS em *todas* tabelas transacionais (`organization_id` NOT NULL) e criar policies `USING (organization_id = current_setting('app.current_org_id')::uuid)`. *Pode ser aplicado na Sprint 1 via Migration, mas testar conexão agora.*
- [ ] **Backup/Point-in-Time:** Verificar janela de retenção (Free tier = 7 dias).

### 2.5. Autenticação: Clerk Hobby (Organizations Enabled)
- [ ] Criar Aplicação "ManutCar Dev". Habilitar **Organizations** (Multi-tenancy nativo `DEC-009`).
- [ ] **Configurações:** Email/Phone + Passwordless (Magic Link) + OAuth (Google, Apple). MFA opcional.
- [ ] **Webhooks (Endpoint: `https://<api-render>/api/v1/webhooks/clerk`):**
  - `user.created` -> Sync `User` local (PF/PJ), criar `Organization` Pessoal ("Minha Operação") `DEC-009`, `RF-FLT-01`.
  - `organization.created` -> Sync `Organization` local, criar `OrganizationSettings` defaults (`DEC-007`, `RN-AUD-04`).
  - `organizationMembership.created` -> Sync `OrganizationMember` (Role default: `admin` se owner, `member` se convidado).
- [ ] **JWT Template:** Custom claim `org_id` (active organization) para facilitar middleware FastAPI.

### 2.6. Storage: Cloudflare R2 (Free Tier)
- [ ] Bucket: `manutcar-dev`.
- [ ] **CORS Policy (JSON):**
  ```json
  [
    {"AllowedOrigins": ["https://*.vercel.app", "https://*.onrender.com", "http://localhost:3000"], "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"], "AllowedHeaders": ["*"], "ExposeHeaders": ["ETag"], "MaxAgeSeconds": 3600}
  ]
  ```
- [ ] **API Token:** Permissions: `Object Read`, `Object Write`, `Object List`. Restrict to Bucket `manutcar-dev`.
- [ ] **Teste:** `curl -X PUT -H "Authorization: Bearer <TOKEN>" --upload-file test.txt "https://<account>.r2.cloudflarestorage.com/manutcar-dev/test.txt"`.

### 2.7. E-mail: Resend Free
- [ ] Verificar domínio (ex: `manutcar.app` ou subdomínio `mg.manutcar.app`) ou usar `onrender.com` para testes.
- [ ] Criar API Key. Testar envio `resend.emails.send({ from: 'onboarding@resend.dev', to: ['seu@email.com'], subject: 'Teste', html: '<p>OK</p>' })`.

### 2.8. Push Notifications: Firebase Cloud Messaging (Spark)
- [ ] Projeto Firebase `manutcar-dev`. Project Settings -> Cloud Messaging -> **Web Push Certificates** (Gerar VAPID Key).
- [ ] Configurar `NEXT_PUBLIC_FCM_VAPID_KEY` no Vercel.
- [ ] Backend: Salvar `FCM_SERVICE_ACCOUNT_JSON` (Base64) no Render Secrets.

### 2.9. CI/CD: GitHub Actions (`.github/workflows/`)
- [ ] **`ci.yml`**: Trigger `push`/`pull_request` -> `pnpm install` -> `turbo run lint typecheck test build` (cache turbo). **Docker Build** `apps/api` (push para GHCR ou Render deploy hook).
- [ ] **`cd-preview.yml`**: Trigger `push` to `main`/`develop` -> Deploy Vercel Preview (auto) + Render Deploy (auto via Deploy Hook ou `render.yaml`).
- [ ] **`cd-prod.yml`**: Trigger `workflow_dispatch` ou `tag v*` -> Deploy Vercel Prod + Render Prod (manual approval).
- [ ] **Secrets GH:** `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `RENDER_DEPLOY_HOOK_API`, `RENDER_DEPLOY_HOOK_WEB`.

---

## 3. Atividades de Arquitetura & Dados (Preparação Sprint 1)

### 3.1. Modelo de Dados Físico (34 Entidades `roadmap.md` Sec 5.1)
- [ ] No `packages/db`: Definir **Todas** as tabelas via SQLAlchemy 2.0 (Mapped, Declarative Base).
- [ ] **Convencões:** UUID PK (`uuid-ossp`), `created_at`/`updated_at` (UTC `DEC-014`), `deleted_at` (Soft Delete `RN-AUD-02`), `organization_id` UUID NOT NULL FK (Multi-tenant `DEC-001`).
- [ ] **Tabelas Críticas Inc 1:** `User`, `Organization`, `OrganizationMember`, `OrganizationSettings` (JSONB defaults `DEC-007`), `VehicleOwner`, `Vehicle`, `VehicleOwnershipHistory`, `VehicleAssignment`, `VehicleFinancialResponsibility`, `FuelLog`, `OdometerReading`, `ConsumptionAnomalyAlert`, `MaintenancePlan`, `VehicleMaintenanceSchedule`, `MaintenanceRequest`, `WorkOrder`, `WorkOrderItem`, `ServiceProvider`, `VehicleModel`, `RevenueEntry`, `PlatformImportBatch`, `FinancialLedgerEntry`, `SettlementStatement`, `VehicleObligation`, `ObligationInstallment`, `DriverLicense`, `TrafficTicket`, `ChecklistTemplate`, `ChecklistTemplateItem`, `ChecklistExecution`, `ChecklistResponseItem`, `AuditLog`, `DataConsent`, `OrganizationInvitation`, `VehicleManagementAgreement`, `VehicleAccessPermission`.
- [ ] **Enum Types:** Definir todos enums Python/SQL (`UserRole`, `VehicleStatus`, `AssignmentStatus`, `FuelType`, `ExpenseCategory`, `RateioBase`, `NaturezaUso`, `SettlementStatus`, `TicketStatus`, `ChecklistType`, `ItemCriticity`, `ConsentStatus`, `AgreementStatus`, `PermissionScope`).

### 3.2. Migração Inicial (Alembic)
- [ ] `alembic revision --autogenerate -m "init_schema_inc1"`.
- [ ] **Revisar SQL gerado:** Índices compostos (`organization_id, vehicle_id`), Partial Indexes (`WHERE deleted_at IS NULL`), Checks (`odometer_value >= 0`), Constraints UNIQUE (`organization_id, year, number` para numeração fiscal `DEC-013`).
- [ ] `alembic upgrade head` no Neon (via CI ou local apontando para `DATABASE_URL` pooled).

### 3.3. Serviço Centralizado de Odômetro (`RN-ABS-01`, `RN-ABS-02`, `RN-ABS-03`)
- [ ] Criar módulo `services/odometer.py` com `record_reading(vehicle_id, km, source, dt, org_id)`.
- [ ] **Lógica:** Lock linha `Vehicle` (SELECT FOR UPDATE) -> Buscar `last_valid` em `OdometerReading` -> Validar `km >= last_valid` (Erro `ODOMETER_REGRESSION`) -> Validar salto > `org_settings.odometer_jump_alert_km` (Warning `WARNING_ODOMETER_JUMP`) -> Insert `OdometerReading` -> Return `reading_id`.
- [ ] **Teste Unitário Obrigatório:** `CT-RN-05` (Regressão bloqueia), Salto 1500km alerta.

### 3.4. Auditoria Imutável (`RN-AUD-01`, `RF-FLT-16`)
- [ ] Tabela `AuditLog` (Partition by month? `pg_partman` futuro. Por enquanto tabela única com índice `entity_name, entity_id`).
- [ ] Trigger PG (`pg_trigger` ou SQLAlchemy Event `after_insert/update/delete`) capturando `old_values`/`new_values` (JSONB) + `actor_user_id` + `ip` + `user_agent`.
- [ ] **Ações Auditadas:** `CREATE, UPDATE, DELETE, APPROVE, REVOKE, ASSIGN, UNASSIGN, CONSENT_GRANT, CONSENT_REVOKE`.

---

## 4. Atividades de Produto: Refinamento Sprint 1 (Backlog Pronto)

> **Base:** `roadmap.md` Sec 5.1 (Sprints 1 a 5) + `especificacao_funcional.md` RFs + `regra_negocio.md` CT-RN.

### 4.1. Sprint 1: Fundação, Banco, Auth & Auditoria (`roadmap.md` Sprint 1)
**Histórias Prontas (Exemplos):**
- [ ] **HIST-001:** Como Sistema, quero provisionar schema completo (34 tabelas) via Alembic para ter base versionada. (Critério: `alembic upgrade head` limpo).
- [ ] **HIST-002:** Como Dev, quero `AuditLog` automático em todas entidades sensíveis para rastreabilidade (`RN-AUD-01`).
- [ ] **HIST-003:** Como Motorista Autônomo (B2C), quero me cadastrar e ter minha "Minha Operação" (Org Pessoal) criada automaticamente com `OrganizationSettings` defaults (`DEC-009`, `RF-FLT-01`).
- [ ] **HIST-004:** Como Membro de Org, quero ser convidado e aceitar convite (`OrganizationInvitation`) definindo `Role` (Admin, Gestor, Financeiro, Motorista, Manutenção) para ter acesso RBAC (`RF-FLT-02`, `RF-FLT-08`, Matriz `regra_negocio.md` Sec 2).
- [ ] **HIST-005:** Como Sistema, quero Middleware FastAPI `require_org_context` + `require_permission(scope)` validando `RN-FLT-01` (Regra de Ouro Acesso) via RLS ou App-level.

### 4.2. Sprint 2: Frota Base, Propriedade & Odômetro (`roadmap.md` Sprint 2)
**Histórias Prontas:**
- [ ] **HIST-010:** CRUD `VehicleOwner` (PF/PJ) + `Vehicle` + `VehicleOwnershipHistory` (Data efetiva `RF-FLT-04`).
- [ ] **HIST-011:** `VehicleAssignment` (Motorista x Veículo x Turno) com validação sobreposição `RN-FLT-06` e CNH válida `RN-DOC-08` (`CT-RN-01`).
- [ ] **HIST-012:** `VehicleFinancialResponsibility` (Regras padrão por Categoria `RN-FIN-06`: Seguro->Proprietário, Combustível->Motorista, Manutenção->Contrato).
- [ ] **HIST-013:** Serviço `OdometerReading` centralizado funcionando (`RN-ABS-01`, `RN-ABS-02`, `CT-RN-05`).

### 4.3. Sprint 3: Operação Diária (Checklist & Abastecimento) (`roadmap.md` Sprint 3)
**Histórias Prontas:**
- [ ] **HIST-020:** `ChecklistTemplate` (DAILY, HANDOVER, RETURN) + Itens (`OK_NOK`, `NUMERIC`, `PHOTO`, `is_safety_critical`, `require_photo_on_fail` `RN-CHK-01`).
- [ ] **HIST-021:** `ChecklistExecution` Mobile/Offline (PWA IndexedDB) -> Sync -> Validações: Item Crítico NOK -> `MaintenanceRequest` + `Vehicle.operational_status=RESTRICTED_SAFETY_ALERT` (`RN-CHK-03`, `CT-RN-06`); Foto obrigatória bloqueia `COMPLETED` (`RN-CHK-04`, `CA-CHK-01`); Atualiza `OdometerReading` (`RN-CHK-05`).
- [ ] **HIST-022:** `FuelLog` (Tanque Cheio/Parcial, Natureza PRO/PER/SHARED, Pagador/Resp.Econômico `RN-FIN-04`). Cálculo `km/l` (`RN-ABS-04`). Alerta Anomalia 15% (`RN-ABS-07`, `CT-RN-10`). Upload Comprovante R2.

### 4.4. Sprint 4: Manutenção Essencial & Documentação Base (`roadmap.md` Sprint 4)
**Histórias Prontas:**
- [ ] **HIST-030:** `MaintenancePlan` (KM + Dias, "O que ocorrer primeiro" `RN-MNT-01`), Associação Flexível (Veículo/Modelo/Global `RN-MNT-02`), Semáforo Status (`RN-MNT-03`).
- [ ] **HIST-031:** `WorkOrder` / `WorkOrderItem` (Garantia KM/Dias). Encerramento: Exige Pagador/Resp.Econômico (`CT-RN-02`), Gera `FinancialLedgerEntry` auto (`RN-MNT-06`), Alerta Garantia (`RN-MNT-07`, `CT-RN-07`), Anexo Obrigatório > R$ 500 (`RN-MNT-08`).
- [ ] **HIST-032:** `VehicleObligation` / `ObligationInstallment` (IPVA, Licenciamento, Seguro, GNV). `DriverLicense` (Bloqueio Alocação se Vencida `RN-DOC-08`, `CT-RN-01`). `TrafficTicket` (Registro Completo `RN-DOC-04`). Job Diário Alertas Escalonados 30/15/7/1 dias (`RN-DOC-03`).

### 4.5. Sprint 5: Motor Financeiro, Receitas CSV/PDF & Relatórios MVP (`roadmap.md` Sprint 5)
**Histórias Prontas:**
- [ ] **HIST-040:** `FinancialLedgerEntry` (Razão Unificado): `payer_entity`, `economic_owner_entity`, `natureza_uso`, `settlement_status` (`RN-FIN-01`, `RN-FIN-02`, `RN-FIN-03`, `CT-RN-02`, `CT-RN-03`).
- [ ] **HIST-041:** `PlatformImportBatch` (CSV/PDF Uber/99 `DEC-016`). Parser configurável (JSON Schema). Hash SHA-256 Idempotência (`RN-FIN-08`, `CT-RN-04`). Vinculo Receita -> `VehicleAssignment` por Data/Hora (`RN-FIN-07`).
- [ ] **HIST-042:** Relatórios 4 Perspectivas (`RF-FLT-14`): Org (DRE/Caixa), Proprietário (Resultado Econômico), Veículo (TCO/km `RN-ABS-06`), Motorista (KM Prof, Receitas, Despesas).
- [ ] **HIST-043:** `SettlementStatement` (Estrutura pronta para geração Inc 2).

---

## 5. Riscos, Dependências & Decisões Pendentes (Base `pendencias_decisoes.md`)

| Item | Status (v3.1) | Ação no Pré-Sprint 0 |
| :--- | :--- | :--- |
| **RLS Performance** | `DEC-001` Resolvido | Testar `EXPLAIN ANALYZE` com RLS ativo em queries multi-join (Vehicle + Assignment + User) no Neon Free. Se lento, planejar *Partial Indexes* ou *Materialized Views* para relatórios. |
| **Clerk Webhook Reliability** | `DEC-011` | Configurar `svix` retry policy. Implementar idempotência no endpoint webhook (guardar `svix-id` processados em Redis/DB temp). **Sem Redis no Inc 1 (`DEC-021`)**, usar tabela `ProcessedWebhookEvent` no PG. |
| **PWA Offline Sync Conflict** | `RN-CHK-02`, `RN-ABS-01` | Definir estratégia "Last Write Wins" com `updated_at` server-side? Ou "Server Wins" para Odômetro (crítico `RN-ABS-01`)? **Decidir e documentar em ADR 0002.** |
| **Numeração Fiscal Sequencial** | `DEC-013` | Implementar `CREATE SEQUENCE org_<id>_year_<yyyy>` dinâmico via trigger ou app-service. Testar concorrência (dois usuários emitindo OS simultâneo). |
| **Limites Free Tier (Neon/Render)** | `DEC-020`, `DEC-022` | Monitorar: Neon Storage (< 0.5GB), Render RAM/CPU (Cold Start > 30s). Configurar `pg_cron` no Neon para jobs diários (Alertas `RN-DOC-03`) pois **Workers/BullMQ adiados `DEC-021`**. |
| **LGPD Anonimização** | `DEC-017`, `RN-AUD-03` | Preparar script SQL de anonimização (User + VehicleOwner PF) para validar `CT-RN-12` na Sprint 1/2. |

---

## 6. Checklist Final: Go / No-Go para Sprint 1 (Segunda-feira 09:00)

| Critério Técnico | Validação | Responsável | Status |
| :--- | :--- | :--- | :--- |
| **Monorepo** | `pnpm install` + `turbo run build` passa local/CI | Tech Lead | [ ] |
| **Infra Camada B** | Vercel Preview + Render Service + Neon DB + Clerk + R2 + Resend + FCM **todos conectados e verdes** | DevOps | [ ] |
| **Auth Sync** | Cadastro Clerk -> Webhook -> `User` + `Org Pessoal` + `OrgSettings` criados no Neon em < 5s | Backend Lead | [ ] |
| **DB Schema** | `alembic upgrade head` aplica 34 tabelas + RLS Policies + Triggers Audit + Sequences Fiscais sem erro | Backend Lead | [ ] |
| **Odômetro Service** | Teste `CT-RN-05` (Regressão 400) + Salto 1500km (Warning 200) passando | Backend Lead | [ ] |
| **PWA Offline** | `apps/web` roda offline (Service Worker), IndexedDB abre, Checklist salva local, Sync ao voltar online | Frontend Lead | [ ] |
| **CI/CD** | PR aberta -> CI Verde -> Preview Deploy (Vercel/Render) funcionando | DevOps | [ ] |
| **Backlog Sprint 1** | 15-20 Histórias INVEST refinadas, estimadas, priorizadas, sem bloqueios técnicos no Jira/Linear/GH Projects | PO + Tech Lead | [ ] |
| **DoD Assinada** | `docs/process/definition-of-done.md` revisada e aceita pelo time | Scrum Master | [ ] |

> **DECISÃO FINAL:** Se **TODOS** os itens acima forem **[x]**, **INICIAR SPRINT 1**.
> Se **QUALQUER** item for **[ ]**, **BLOQUEAR SPRINT 1**, registrar impedimento no Daily/Slack e atuar na resolução imediata.

---

## 7. Comandos Úteis (Cheatsheet para o Time)

