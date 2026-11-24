# PENDÊNCIAS E DECISÕES ARQUITETURAIS — ManutCar

**Código do Documento:** MC-DOC-DEC-001  
**Status:** **Todas Pendências Resolvidas — Pronto para Sprint 1**  
**Versão:** 3.0 (Final)  
**Referências:**  
* `MC-DOC-VIS-001` (`VISÃO_DO_PRODUTO.md` v1.0)  
* `MC-DOC-ESP-001` (`ESPECIFICACAO_FUNCIONAL.md` v2.0)  
* `MC-DOC-RN-001` (`REGRAS_DE_NEGOCIO.md` v2.1)  
* `MC-DOC-RDM-001` (`ROADMAP.md` v2.1)  

---

## 1. Decisões Arquiteturais Consolidadas (ADR — Architectural Decision Records)

As decisões abaixo estão **fechadas, congeladas e prontas para implementação**.

| ID | Tema | Decisão Tomada | Justificativa Resumida | Rastreabilidade |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-001** | **Arquitetura Multi-Tenant Híbrida** | Sistema nasce **multiorganização, multiusuário, multiproprietário** desde a Sprint 1. Schema único com `organization_id` (NOT NULL) em todas as tabelas transacionais. RLS (Row Level Security) no PostgreSQL para isolamento físico. | Evita refatoração futura; atende 4 perfis (B2C, B2B, B2B2C, Gestor) no mesmo código base. | `RF-FLT-01` a `05`, `ROADMAP` Sec. 1 e 5 |
| **DEC-002** | **Titularidade Perpétua do Ativo** | Prontuário técnico (`WorkOrder`, `MaintenancePlan`, `OdometerReading`, `ChecklistExecution`) pertence ao **Veículo**. Acompanha trocas de motorista, gestor ou proprietário. Dados financeiros privados não vazam. | Garante valor do ativo (histórico de manutenção) e conformidade LGPD. | `RF-FLT-11`, `RN-FLT-03` |
| **DEC-003** | **Separação Contábil (Caixa vs. DRE)** | Todo lançamento (`FinancialLedgerEntry`) exige `payer_entity` (Pagador) e `economic_owner_entity` (Responsável Econômico). Reembolso automático (`PENDING_REIMBURSEMENT`) se diferentes. Relatórios DRE somam por `economic_owner`; Fluxo de Caixa por `payer`. | Elimina dupla contagem; permite lucro real por veículo/proprietário/motorista. | `RF-FLT-13`, `RN-FIN-01` a `03` |
| **DEC-004** | **Governança de Veículos de Terceiros** | Acesso exige `VehicleManagementAgreement` (status `ACTIVE`) + `VehicleAccessPermission` (escopo granular). Placa sozinha não concede acesso. | Segurança jurídica e isolamento de dados sensíveis. | `RF-FLT-06`, `RN-FLT-01`, `RN-FLT-02` |
| **DEC-005** | **Privacidade LGPD (Uber/99)** | Contas Uber/99 pertencem ao motorista. Gestor/Proprietário acessa apenas com `DataConsent` `GRANTED` (escopo `FINANCIAL_READ`). Revogação imediata. | Conformidade LGPD Art. 7º/18; "Privacy by Design". | `RF-FLT-18`, `RN-FLT-04`, `RN-AUD-03` |
| **DEC-006** | **Fonte Única e Monotônica de Odômetro** | Todas leituras convergem para `OdometerReading` (imutável). Validação estrita: `odometer_value >= last_valid` (bloqueia `ODOMETER_REGRESSION`). Alerta salto > 1.500km/24h (`WARNING_ODOMETER_JUMP`). | Integridade do cálculo de consumo (`km/l`), TCO e manutenção preventiva. | `RF-ABS-02`, `RF-CHK-04`, `RN-ABS-01/02` |
| **DEC-007** | **Parametrização por Organização** | Limites numéricos em `OrganizationSettings` (JSONB): `odometer_jump_alert_km`, `consumption_alert_threshold_pct`, `preventive_due_soon_km_pct`, `os_attachment_threshold`, `handover_mandatory_hours`, `settlement_periodicity`, `timezone`, `document_numbering_strategy`, `subscription_plan_id`. Zero *hardcoding*. | Flexibilidade para diferentes perfis (autônomo vs frota grande) sem deploy. | `RN-ABS-02`, `RN-MNT-02`, `RN-CHK-06`, `PEND-005/006` |
| **DEC-008** | **Estratégia de Entrega: 3 Incrementos / 2 Fases** | **Fase 1 (Base):** Inc. 1 (MVP Core: 5 Sprints) + Inc. 2 (Governança/LGPD/Rateios). **Fase 2 (Avançado):** Inc. 3 (Offline, APIs Externas, IA). | Mitigação de risco; entrega valor contínuo; arquitetura preparada desde o Inc. 1. | `VISÃO` Sec. 3, `ROADMAP` Sec. 1 e 2 |
| **DEC-009** | **Onboarding B2C — Org Pessoal Automática** | **Opção A:** Cadastro de motorista autônomo cria `Organization` ("Minha Operação") com user como `Admin`. `organization_id` obrigatório em tudo. | Simplifica 100% RBAC e queries (sem `NULL` checks); unifica B2C e B2B no mesmo modelo. | `PEND-001`, `ROADMAP` Sprint 1, `RF-FLT-01/02` |
| **DEC-010** | **Entidade `VehicleModel` para Planos Preventivos** | Entidade `VehicleModel` (`make`, `model`, `year`, `engine`, `fuel_type`, `consumption_reference_km_l`). `MaintenancePlan` associa a: 1. Veículo Específico, 2. Modelo, 3. Global. | Reutilização de planos por frota homogênea; baseline de consumo para alerta `RN-ABS-07`. | `RF-MNT-02`, `RN-MNT-02`, `PEND-013` |
| **DEC-011** | **Stack Tecnológico Definido (PEND-007/008/009/010/011/012)** | **Backend:** **Python 3.12 + FastAPI** (Async, Tipagem Pydantic, OpenAPI nativo, ecossistema Data/IA).<br>**Frontend Web (Gestores):** **Next.js 14 (App Router) + TypeScript + Tailwind + Shadcn/UI** (SSR/ISR, SEO, DX).<br>**Mobile Motorista (Inc. 1):** **PWA (Progressive Web App)** via Next.js + Service Workers (Workbox) + IndexedDB (Dexie.js) para Offline-First em Checklist/Abastecimento. App Nativo (React Native/Expo) planejado para Inc. 3.<br>**Banco:** **PostgreSQL 16** (UUID PKs, JSONB, Partial Indexes `deleted_at`, RLS nativo, Extensões `pg_trgm`, `uuid-ossp`).<br>**ORM:** **SQLAlchemy 2.0 (Async) + Alembic** (Migrations).<br>**Auth:** **Clerk** (Managed Auth, MFA, Organizações nativas, Webhooks para sync `User`/`Organization` local).<br>**Storage:** **Cloudflare R2** (Compatível S3, Zero Egress Fee, Buckets por Org via Prefixo/Policy).<br>**Hospedagem:** **Vercel (Frontend/Edge)** + **Railway/Render (Backend Python/Worker)** + **Upstash Redis** (Cache/Fila BullMQ).<br>**Notificações:** **Resend (E-mail)** + **Firebase Cloud Messaging (Push PWA)** + **Evolution API (WhatsApp - Self-hosted na Railway)**.<br>**Testes/QA:** **Vitest (Unit/Integration)**, **Playwright (E2E)**, **Pact (Contract)**, **GitHub Actions (CI/CD)**, Cobertura Mínima **80% Regras de Negócio (RN)**. | Stack moderna, type-safe end-to-end, serverless-friendly, custo previsível, foco em DX e performance. PWA atende Offline-First Inc. 1 sem complexidade nativa imediata. | `PEND-007` a `PEND-012` |
| **DEC-012** | **Modelo SaaS e Planos (PEND-004)** | Entidade `SubscriptionPlan` no schema inicial. **Planos:** `FREE` (1 Org Pessoal, 2 Veículos, 1 Usuário, 100MB Anexos), `PRO` (R$ 49/mês/org, Veículos/Users ilimitados, 10GB, Relatórios Avançados, API), `ENTERPRISE` (Contrato, SSO/SAML, Auditoria Estendida, Suporte Dedicado). `OrganizationSettings.subscription_plan_id` faz gating de features via Middleware/Policy. | Monetização clara desde o dia 1; `FREE` viabiliza B2C viral; `PRO` alvo B2B/B2B2C. | `PEND-004`, `ROADMAP` Sprint 1 |
| **DEC-013** | **Estratégia de Numeração Fiscal (PEND-005)** | **Padrão:** `PREFIX_ORG_YYYY_SEQ` (Ex: `OS-ACME-2025-0001`, `ABST-ACME-2025-0042`, `MUL-ACME-2025-0003`).<br>Configurável em `OrganizationSettings.document_numbering_strategy` (opções: `SEQUENTIAL_ORG`, `SEQUENTIAL_GLOBAL`, `PREFIX_ORG_YYYY`).<br>Implementação: Sequence PostgreSQL por Organização + Ano (`CREATE SEQUENCE org_<id>_year_<yyyy>`). Unicidade garantida por `(organization_id, year, number)`. | Atende contabilidade brasileira (sequencial por estabelecimento/ano); rastreabilidade auditoria; flexível para matriz/filial. | `PEND-005`, `RN-FLT-09` (atualizado) |
| **DEC-014** | **Tratamento de Fusos Horários (PEND-006)** | **Armazenamento:** **UTC** obrigatório em todos `TIMESTAMPTZ` (PostgreSQL).<br>**Apresentação/Jobs:** Conversão para `OrganizationSettings.timezone` (IANA TZ, padrão `America/Sao_Paulo`).<br>**Jobs Diários (Alertas, Fechamento):** Executam às 03:00 **no fuso da Organização** (via `pg_cron` ou Worker com TZ awareness).<br>**Input Mobile:** App envia `local_datetime` + `tz_offset`; Backend converte para UTC na borda. | Suporte nativo a multi-região (futuro); consistência absoluta de dados; jobs corretos para "dia útil" e "vencimento". | `PEND-006`, `RN-FLT-10`, `RN-AUD-04` |
| **DEC-015** | **Rateio Híbrido: Variáveis por KM, Fixas por Dias (PEND-003)** | **Regra `RN-FIN-10` Oficial:**<br>• **Variáveis** (Combustível, Pedágio, Lavagem, Manutenção Corretiva/Preventiva não contratual): Rateio **KM Profissional / KM Total** (`RN-FIN-05`).<br>• **Fixas/Periódicas** (IPVA, Licenciamento, Seguro, Proteção, Aluguel/Depreciação, Parcela Financiamento): Rateio **Dias Alocação Motorista / Dias Período**.<br>Implementação: Campo `rateio_base` ENUM (`KM`, `DIAS`) em `VehicleFinancialResponsibility` com default por `expense_category`. | Justiça econômica: Custo fixo dilui no tempo de uso; custo variável dilui na intensidade de uso. Resolve compartilhamento de veículo em turnos. | `PEND-003`, `RN-FIN-10`, `SettlementStatement` Inc. 2 |
| **DEC-016** | **Layouts CSV Uber/99 para Parser Inicial (PEND-002)** | **Definição de Contrato de Entrada (`PlatformImportBatch.parser_version`):**<br>**Uber Motorista (CSV Exportado App):** Colunas: `data_viagem`, `hora_inicio`, `hora_fim`, `distancia_km`, `ganho_bruto`, `taxa_uber`, `gorjeta`, `bonus`, `origem`, `destino`, `placa_veiculo`.<br>**99 Motorista (CSV Portal/Email):** Colunas: `data_corrida`, `hora_inicio`, `hora_fim`, `km_rodado`, `valor_corrida`, `taxa_99`, `gorjeta`, `bonus`, `categoria`, `placa`.<br>**Estratégia:** Parser configurável via JSON Schema (colunas mapeáveis). Validação: `placa` + `data/hora` → `VehicleAssignment` → `vehicle_id`. Hash SHA-256 do **conteúdo bruto do arquivo** (`file_hash`) para idempotência (`RN-FIN-08`). | Permite iniciar Sprint 5 com parser funcional; mapeamento flexível para mudanças de layout das plataformas. | `PEND-002`, `RF-FIN-03`, `RN-FIN-08` |
| **DEC-017** | **Anonimização LGPD: Escopo Explícito (PEND-019)** | **Tabela `User` (PF):** Anonimizar: `full_name`→"Usuário Removido", `cpf`/`cnh_number`→`SHA256(val)||'_ANON'`, `email`→`anon_<id>@manutcar.local`, `phone`/`address`/`bank_account`/`avatar_url`→`NULL`. **Preservar:** `id`, `auth_provider_id`, `created_at`, `updated_at`, `status`, `role_global`.<br>**Tabela `VehicleOwner` (PF):** Mesma regra para `name`, `cpf`, `cnh`, `contact_info`. **Preservar:** `id`, `owner_type`, `created_at`.<br>**Ação:** Revogar `DataConsent`; Log `ANONYMIZE_LGPD` em `AuditLog`. | Conformidade Art. 18 LGPD (Direito à Eliminação) mantendo integridade referencial (FKs `User.id` em `VehicleAssignment`, `WorkOrder.executor_id` intactas). | `PEND-019`, `RN-AUD-03` (atualizado) |
| **DEC-018** | **Conflito de Turno em Multa: UI de Seleção Manual (PEND-016)** | Se `VehicleAssignment` sobreposto na hora da infração (`>1 motorista`): `TrafficTicket.identification_method = MANUAL`. UI (Modal) lista motoristas conflitantes com `start/end` do turno. Usuário (Gestor/Admin) seleciona um → `selected_driver_id`. Bloqueia salvamento sem seleção. | Resolve ambiguidade legal; responsabiliza gestor pela indicação correta; rastreabilidade (`MANUAL` vs `AUTO`). | `PEND-016`, `RN-DOC-05` (atualizado) |
| **DEC-019** | **Integrações Futuras: SENATRAN & IA (PEND-017/018)** | **SENATRAN/Detran (Inc. 3):** Provedor **Caronte.io** (API Unificada Brasil) como padrão; Fallback APIs Estaduais. Requer homologação CNPJ.<br>**Motor Preditivo TCO (Inc. 3):** Stack **Python (FastAPI Worker) + Scikit-learn/XGBoost + TimescaleDB** (extensão PostgreSQL para séries temporais de odômetro/custos). Features: Depreciação Fipe (API Tabela Fipe), Curva Manutenção Acumulada, Consumo Real vs Modelo. Output: "Ponto de Virada (KM/Data)" + Score Substituição. | Decisão técnica antecipada evita vendor lock-in; TimescaleDB nativo no PostgreSQL simplifica stack. | `PEND-017`, `PEND-018`, `ROADMAP` Inc. 3 |

---

## 2. Checklist de Encerramento da Documentação Oficial — **100% CONCLUÍDO**

* [x] `VISÃO_DO_PRODUTO.md` (`MC-DOC-VIS-001` v1.0) — Aprovado
* [x] `ESPECIFICACAO_FUNCIONAL.md` (`MC-DOC-ESP-001` v2.0) — Aprovado
* [x] `REGRAS_DE_NEGOCIO.md` (`MC-DOC-RN-001` v2.1) — Aprovado
* [x] `ROADMAP.md` (`MC-DOC-RDM-001` v2.1) — Aprovado
* [x] `PENDENCIAS_E_DECISOES.md` (`MC-DOC-DEC-001` v3.0) — **Todas Pendências Resolvidas → ADRs**

---

## 3. Rastreabilidade Final: Pendências Originais → Decisões Oficiais

| Pendência Original | Decisão Resultante (ADR) | Status |
| :--- | :--- | :--- |
| `PEND-001` (Onboarding B2C) | `DEC-009` (Org Pessoal Automática) | **Resolvido v2.0** |
| `PEND-002` (Layouts CSV Uber/99) | `DEC-016` (Contrato de Entrada + Parser JSON Schema) | **Resolvido v3.0** |
| `PEND-003` (Rateio Fixos: Dias vs KM) | `DEC-015` (Híbrido: Variáveis=KM, Fixas=Dias) | **Resolvido v3.0** |
| `PEND-004` (Modelo SaaS/Planos) | `DEC-012` (FREE / PRO / ENTERPRISE + Entidade `SubscriptionPlan`) | **Resolvido v3.0** |
| `PEND-005` (Numeração Fiscal) | `DEC-013` (`PREFIX_ORG_YYYY_SEQ` + Sequence PG por Org/Ano) | **Resolvido v3.0** |
| `PEND-006` (Fusos Horários/Timezone) | `DEC-014` (UTC Storage + TZ Org + Jobs no TZ da Org) | **Resolvido v3.0** |
| `PEND-007` (Stack Backend) | `DEC-011` (Python 3.12 + FastAPI + SQLAlchemy 2.0) | **Resolvido v3.0** |
| `PEND-008` (Estratégia Mobile) | `DEC-011` (PWA Next.js + IndexedDB Inc.1; React Native Inc.3) | **Resolvido v3.0** |
| `PEND-009` (Banco de Dados) | `DEC-011` (PostgreSQL 16 + RLS + JSONB + Partial Index) | **Resolvido v3.0** |
| `PEND-010` (Storage Arquivos) | `DEC-011` (Cloudflare R2 - S3 Compatible, Zero Egress) | **Resolvido v3.0** |
| `PEND-011` (Hospedagem/Auth/Notif) | `DEC-011` (Vercel + Railway + Clerk + Resend + FCM + Evolution API) | **Resolvido v3.0** |
| `PEND-012` (Testes/QA) | `DEC-011` (Vitest + Playwright + Pact + GitHub Actions + 80% RN) | **Resolvido v3.0** |
| `PEND-013` (Entidade VehicleModel) | `DEC-010` (Catálogo Modelos + Consumo Referência) | **Resolvido v2.0** |
| `PEND-014` (Baseline Consumo Modelo) | `DEC-010` / `RN-ABS-07` (Usa `VehicleModel.consumption_reference_km_l`) | **Resolvido v2.0** |
| `PEND-015` (Hash Idempotência) | `DEC-011` / `RN-FIN-08` (SHA-256 Conteúdo Bruto) | **Resolvido v2.0** |
| `PEND-016` (Conflito Turno Multa) | `DEC-018` (UI Modal Seleção Manual `MANUAL`) | **Resolvido v3.0** |
| `PEND-017` (Integração SENATRAN) | `DEC-019` (Caronte.io + Fallback Estaduais) | **Resolvido v3.0 (Inc. 3)** |
| `PEND-018` (Motor Preditivo TCO) | `DEC-019` (Python/Scikit-learn + TimescaleDB) | **Resolvido v3.0 (Inc. 3)** |
| `PEND-019` (Escopo Anonimização LGPD) | `DEC-017` (Lista Explícita Campos PII User/VehicleOwner PF) | **Resolvido v3.0** |

---

## 4. Próximos Passos Imediatos (Kickoff Sprint 1)

1.  **Inicializar Repositório Monorepo:**
    ```bash
    # Estrutura sugerida (Turborepo / Nx)
    /apps
      /api          # FastAPI (Backend)
      /web          # Next.js (Frontend Gestor + PWA Motorista)
    /packages
      /db           # SQLAlchemy Models + Alembic Migrations (Shared)
      /schemas      # Pydantic Schemas (Shared API Contract)
      /ui           # Componentes Shadcn/UI (Shared)
      /config       # ESLint, TSConfig, Tailwind Presets
    ```
2.  **Provisionar Infraestrutura (IaC - Terraform/Pulumi ou Manual Inicial):**
    *   PostgreSQL 16 (Railway/Neon/CloudSQL) + Extensões (`uuid-ossp`, `pg_trgm`, `timescaledb` para Inc. 3).
    *   Redis (Upstash) para Cache/Celery/BullMQ.
    *   Buckets R2 (Cloudflare) + Credenciais.
    *   Projeto Clerk (Organizações habilitadas) + Webhooks `user.created`, `organization.created`.
    *   Domínios Vercel + Variáveis de Ambiente.
3.  **Executar Sprint 1 (Conforme `ROADMAP.md` Sec. 5):**
    *   **Dia 1-2:** Models/Alembic (36 Entidades), `AuditLog` Trigger, RLS Policies, `OrganizationSettings` Defaults (incl. `timezone`, `subscription_plan_id=FREE`, `document_numbering_strategy=PREFIX_ORG_YYYY`).
    *   **Dia 3-4:** Auth Integration (Clerk Webhook → Sync `User`/`Organization`/`OrganizationMember`), Middleware RBAC/Permission Guard.
    *   **Dia 5:** Onboarding B2C (Criação `Organization` Pessoal Automática `DEC-009`), Healthchecks, CI/CD Pipeline (GitHub Actions: Lint, Typecheck, Test, Migrate, Deploy Preview).

---

**Status Final:** **Documentação 100% "Definition of Ready" para Desenvolvimento.**  
Todas as decisões técnicas, de produto e de arquitetura estão documentadas, rastreadas e aprovadas. O time pode iniciar a **Sprint 1** imediatamente.

*Fim do Documento MC-DOC-DEC-001 v3.0*
