# ROADMAP OFICIAL DE DESENVOLVIMENTO — ManutCar

**Código do Documento:** MC-DOC-RDM-001  
**Status:** Consolidado para Aprovação  
**Versão:** 2.2 (Atualizado com Infraestrutura Inicial e Adiamentos)  
**Referências:**  
* `MC-DOC-VIS-001` (`VISÃO_DO_PRODUTO.md` v1.1)  
* `MC-DOC-ESP-001` (`ESPECIFICACAO_FUNCIONAL.md` v2.1)  
* `MC-DOC-RN-001` (`REGRAS_DE_NEGOCIO.md` v2.1)  
* `MC-DOC-DEC-001` (`PENDENCIAS_E_DECISOES.md` v3.1)  

---

## 1. Estratégia de Entrega (Duas Fases Estratégicas em Incrementos)

Conforme diretriz arquitetural da `ESPECIFICACAO_FUNCIONAL.md` (Seção 11), o ManutCar adota **Duas Fases Estratégicas** para mitigação de risco e entrega de valor contínuo, nascendo com arquitetura **multiorganização, multiusuário e multiproprietário** desde o Incremento 1.

A execução tática é dividida em **3 Incrementos de Entrega** alinhados às Fases:

| Fase Estratégica | Incremento | Foco | Entrega de Valor |
| :--- | :--- | :--- | :--- |
| **Fase 1: Base da Gestão de Frota** (Prioridade Estrutural) | **Incremento 1 — MVP Operacional e Financeiro (Core)** | Organizações, Frota Própria, Odômetro, Manutenção Essencial, Checklist, Abastecimento, Documentação Básica, Financeiro Manual/CSV, Relatórios DRE/Fluxo de Caixa. | Motorista autônomo e Empresa com frota própria operam ciclo diário completo com contabilidade limpa (Pagador vs Responsável Econômico). |
| | **Incremento 2 — Governança Multiproprietário, LGPD e Rateios** | Autorização de Gestão de Terceiros, Convites/Escopos, Consentimento LGPD (Uber/99), Rateio `SHARED` (Híbrido: Variáveis por KM, Fixas por Dias), Fechamento `SettlementStatement`, Identificação Automática de Infrator (com UI Manual para conflitos), Vistorias Handover/Return, Garantias. | Gestor independente administra veículos de terceiros com prestação de contas transparente, privacidade garantida e acerto financeiro automatizado. |
| **Fase 2: Gestão Avançada** | **Incremento 3 — Automação Externa, Offline e Inteligência** | Modo Offline-First, Conectores API Uber/99/SENATRAN (Caronte.io), TCO Preditivo (Python/Scikit-learn/TimescaleDB), Ranking de Eficiência, Curva de Depreciação. | Redução drástica de trabalho manual, inteligência preditiva para substituição de frota e operação resiliente em campo. |

---

## 2. Incremento 1 — MVP Operacional e Financeiro (Core)

### 2.1. Escopo Funcional e Rastreabilidade (Incremento 1)

| Módulo | Requisitos Funcionais (`RF`) | Regras de Negócio (`RN`) | Entidades Ativadas |
| :--- | :--- | :--- | :--- |
| **Núcleo, Auditoria & Config** | `RF-FLT-01`, `RF-FLT-02`, `RF-FLT-08`, `RF-FLT-15`, `RF-FLT-16` | `RN-FLT-01`, `RN-FLT-07`, `RN-FLT-08`, `RN-AUD-01`, `RN-AUD-02` | `User`, `Organization`, `OrganizationMember`, `OrganizationSettings`, `AuditLog` |
| **MC-FLT (Base Própria)** | `RF-FLT-03`, `RF-FLT-04`, `RF-FLT-05`, `RF-FLT-09`, `RF-FLT-12`, `RF-FLT-13` | `RN-FLT-02`, `RN-FLT-03`, `RN-FLT-06`, `RN-FIN-06` | `VehicleOwner`, `Vehicle`, `VehicleOwnershipHistory`, `VehicleAssignment`, `VehicleFinancialResponsibility` |
| **MC-ABS (Completo)** | `RF-ABS-01` a `RF-ABS-06` | `RN-ABS-01` a `RN-ABS-08` | `FuelLog`, `OdometerReading`, `ConsumptionAnomalyAlert` |
| **MC-MNT (Essencial + Garantia)** | `RF-MNT-01` a `RF-MNT-08` | `RN-MNT-01` a `RN-MNT-08` | `MaintenancePlan`, `VehicleMaintenanceSchedule`, `MaintenanceRequest`, `WorkOrder`, `WorkOrderItem`, `ServiceProvider` |
| **MC-FIN (Manual + CSV + Rateio Base)** | `RF-FIN-01`, `RF-FIN-03`, `RF-FIN-04`, `RF-FIN-05`, `RF-FIN-06`, `RF-FIN-07` | `RN-FIN-01`, `RN-FIN-02`, `RN-FIN-03`, `RN-FIN-04`, `RN-FIN-05`, `RN-FIN-06`, `RN-FIN-07`, `RN-FIN-08`, `RN-FIN-09` | `RevenueEntry`, `PlatformImportBatch`, `FinancialLedgerEntry`, `SettlementStatement` (estrutura) |
| **MC-DOC (Básico + CNH)** | `RF-DOC-01` a `RF-DOC-04`, `RF-DOC-07`, `RF-DOC-02`, `RF-DOC-03`, `RF-DOC-08` | `RN-DOC-01` a `RN-DOC-04`, `RN-DOC-07`, `RN-DOC-08`, `RN-DOC-02`, `RN-DOC-03` | `VehicleObligation`, `ObligationInstallment`, `DriverLicense`, `TrafficTicket` |
| **MC-CHK (Diário + Odômetro)** | `RF-CHK-01` a `RF-CHK-06` | `RN-CHK-01`, `RN-CHK-02`, `RN-CHK-03`, `RN-CHK-04`, `RN-CHK-05` | `ChecklistTemplate`, `ChecklistTemplateItem`, `ChecklistExecution`, `ChecklistResponseItem` |

### 2.2. Critérios de Pronto do Incremento 1 (Definition of Done)
* **Segregação Multi-Tenant:** Nenhuma consulta vaza dados entre organizações distintas (`CT-RN-01`, `CT-RN-08`).
* **Odômetro Blindado:** Todos os módulos alimentam `OdometerReading` respeitando monotonicidade estrita e alerta de salto (`CT-RN-05`, `RN-ABS-01`, `RN-ABS-02`).
* **Contabilidade Limpa (Dupla Perspectiva):** Pagador e Responsável Econômico registrados separadamente em **todas** as despesas (OS, Abastecimento, Obrigações) e receitas. Relatórios DRE (Competência Econômica) e Fluxo de Caixa (Caixa) gerados sem dupla contagem (`CT-RN-02`, `CT-RN-03`, `RN-FIN-01`, `RN-FIN-02`, `RN-FIN-03`).
* **Operação Diária Completa:** Motorista executa Checklist (com foto obrigatória em falha crítica `CT-RN-06`), Abastecimento (com cálculo `km/l` e alerta anomalia), Lança Receita Manual/CSV (idempotente `CT-RN-04`).
*   **Manutenção Integrada:** OS encerrada gera lançamento financeiro automático com Pagador/Responsável Econômico (`CT-RN-02`, `RN-MNT-06`). Alerta de garantia ativo (`CT-RN-07`, `RN-MNT-07`). Anexo obrigatório > R$ 500 (`RN-MNT-08`).
*   **Documentação Bloqueante:** CNH vencida impede alocação (`CT-RN-01`, `RN-DOC-08`). Alertas escalonados (30/15/7/1 dias) funcionando (`RN-DOC-03`).

---

## 3. Incremento 2 — Governança Multiproprietário, Privacidade LGPD e Rateios Avançados

### 3.1. Escopo Funcional e Rastreabilidade (Incremento 2)

| Módulo | Requisitos Funcionais (`RF`) | Regras de Negócio (`RN`) | Entidades / Recursos Ativados |
| :--- | :--- | :--- | :--- |
| **MC-FLT (Terceiros & LGPD)** | `RF-FLT-06`, `RF-FLT-07`, `RF-FLT-10`, `RF-FLT-11`, `RF-FLT-14`, `RF-FLT-17`, `RF-FLT-18` | `RN-FLT-02` (completo), `RN-FLT-04`, `RN-FLT-05` | `OrganizationInvitation`, `VehicleManagementAgreement`, `VehicleAccessPermission`, `DataConsent` |
| **MC-FIN (Acerto & Rateio `SHARED` Híbrido)** | `RF-FIN-02`, `RF-FIN-03` (CSV/PDF), `RF-FLT-13`, `RF-FLT-14` | `RN-FIN-02`, `RN-FIN-04`, `RN-FIN-05`, `RN-FIN-10` | `SettlementStatement` (execução), Parser CSV/PDF Uber/99, Rateio Híbrido (`RN-FIN-10`), Reembolso Automático (`RN-FIN-02`). |
| **MC-DOC (Infrator Auto & Workflow)** | `RF-DOC-05`, `RF-DOC-06` | `RN-DOC-05`, `RN-DOC-06` | Cruzamento automático `TrafficTicket` x `VehicleAssignment` (data/hora), Workflow de Indicação (Pendente → Indicado → Confirmado/Recurso), UI Modal para conflito de turno (`identification_method = MANUAL`). |
| **MC-CHK (Vistorias Handover/Return)** | `RF-CHK-07` | `RN-CHK-06`, `RN-CHK-07` | Vistorias obrigatórias de `HANDOVER` (Entrega) e `RETURN` (Devolução) com comparativo de avarias (`NEW_DAMAGE_DETECTED`). |
| **MC-MNT (Garantia Avançada)** | `RF-MNT-06` | `RN-MNT-07` | Verificação automática de garantia por km e dias na adição de `WorkOrderItem` (alerta bloqueante `WARRANTY_COVERAGE_POSSIBLE`). |
| **Privacidade (LGPD - Art. 18)** | Transversal (`RF-FLT-18`) | `RN-AUD-03` | Fluxo de anonimização irreversível de PII (`User`, `VehicleOwner` PF) mantendo integridade referencial (`VehicleAssignment`, `WorkOrder`) e revogação `DataConsent`. |

### 3.2. Critérios de Pronto do Incremento 2
* **Gestão de Terceiros:** Gestor convida proprietário, define escopo granular (`MAINTENANCE_READ`, `FINANCIAL_WRITE`, etc.), proprietário aceita/revoga. Acesso imediato revogado (`CT-RN-07`, `RN-FLT-02`, `RN-FLT-05`).
* **Privacidade Uber/99:** Motorista autoriza (`DataConsent=GRANTED`) leitura de receitas por Org/Proprietário. Revogação imediata bloqueia consultas (`CT-RN-09`, `RN-FLT-04`, `RN-AUD-03`).
* **Fechamento Financeiro (`SettlementStatement`):** Execução periódica (Mensal/Semanal) consolida `PENDING_REIMBURSEMENT`, gera lançamentos de `settlement_transfer` (Caixa) sem afetar DRE (`RN-FIN-02`, `RN-FIN-03`).
* **Rateio `SHARED` Híbrido:** Cálculo proporcional `KM Profissional / KM Total` para variáveis; `Dias Alocação / Dias Período` para fixas (`RN-FIN-10`). Tratamento `DIVISION_BY_ZERO` (`CT-RN-10`, `CT-RN-11`).
* **Multas Automatizadas:** Cadastro de multa com data/hora sugere infrator via `VehicleAssignment` (`RN-DOC-05`). Conflito de turno (`>1 motorista`) → `identification_method = MANUAL` + UI Modal seleção (`DEC-018`). Workflow de indicação controla prazos e status (`RN-DOC-06`).
* **Vistorias Jurídicas:** Alocação > 24h exige `HANDOVER`/`RETURN` com fotos. Comparativo automático detecta avarias novas (`RN-CHK-06`, `RN-CHK-07`).
* **LGPD Anonimização:** Fluxo completo `RN-AUD-03` / `DEC-017` funcional (User + VehicleOwner PF, preservação FKs, revogação consentimento, log auditoria).
* **Todos os 13 Casos de Teste (`CT-RN-01` a `CT-RN-13`)** aprovados em suíte automatizada (CI/CD).

---

## 4. Incremento 3 — Escala, Integrações Externas e Inteligência Operacional (Fase 2)

### 4.1. Escopo Planejado (Pós-Consolidação B2B/B2C)
* **Modo Offline-First (`RN-CHK-02`, `RF-ABS-01`):** Fila de sincronização local (SQLite/IndexedDB) no app mobile para Checklist, Abastecimento e Odômetro. Reconciliação de timestamps e conflitos de odômetro (`RN-ABS-01`) na sincronização.
* **Conectores Diretos de Receita (`RF-FIN-01`, `RF-FIN-03`):** Integração via APIs oficiais ou agregadores homologados (com `DataConsent` ativo) para sincronização contínua de corridas/repasses Uber/99, eliminando upload manual de CSV/PDF.
* **Integração SENATRAN / Detrans (`RF-DOC-04`, `RF-DOC-05`):** Consulta agendada de infrações, pontuação CNH e situação de licenciamento/IPVA por Placa/RENAVAM. Pré-preenchimento de `TrafficTicket` e `VehicleObligation`. Provedor **Caronte.io** (API Unificada Brasil) como padrão; Fallback APIs Estaduais (`DEC-019`).
* **Inteligência de Frota e TCO Preditivo (`RF-FLT-14`, `RN-ABS-06`):**
    *   *Ranking de Eficiência:* Consumo real vs. Teórico (Fipe/Factory) por Motorista e Modelo.
    *   *Curva de Decisão (TCO/km):* Modelo preditivo cruzando Depreciação (Tabela Fipe), Manutenção Acumulada (Corretiva/Preventiva) e Consumo para recomendar "Ponto de Virada" (Substituir vs Manter).
    *   *Alertas Preditivos de Falha:* Análise de frequência de `WorkOrderItem` (peças) por modelo/frota para antecipar compras/recall interno.
    *   Stack: **Python (FastAPI Worker) + Scikit-learn/XGBoost + TimescaleDB** (`DEC-019`).

---

## 5. Plano de Execução por Sprints (Guia para Agente de Código — Incremento 1)

A implementação do **Incremento 1** deve obedecer estritamente à ordem de dependência de dados abaixo. **Total de Entidades Conceituais Mapeadas: 34.**

### 5.0. Pré-Sprint 0: Provisionamento da Infraestrutura Inicial (Camada B - Custo Zero) — `DEC-020`, `DEC-021`
*Executar antes da Sprint 1. Não implementar código de negócio.*

| Atividade | Detalhamento / Ferramentas | Critério de Pronto |
| :--- | :--- | :--- |
| **0.1 Repositório & Monorepo** | `git init`, Turborepo/Nx structure (`apps/api`, `apps/web`, `packages/db`, `packages/schemas`, `packages/ui`). | Repo no GitHub; `pnpm install` / `pip install` funcionando localmente. |
| **0.2 Frontend (Vercel Hobby)** | Importar repo no Vercel. Framework Preset: Next.js. Root Directory: `apps/web`. Env Vars: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_URL`. | Deploy Preview funcionando; Clerk SDK carrega; PWA `manifest.json` / Service Worker registrado. |
| **0.3 Backend (Render Free)** | New Web Service (Docker). Repo `apps/api`. Env Vars: `DATABASE_URL` (Neon), `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, `R2_*`, `RESEND_API_KEY`, `FCM_*`, `SETTINGS_TZ=America/Sao_Paulo`. Healthcheck `/health`. | Deploy bem-sucedido; Logs mostram startup FastAPI; Swagger UI (`/docs`) acessível. |
| **0.4 Banco de Dados (Neon Free)** | Criar Projeto Neon. Branch `main`. Habilitar extensões: `uuid-ossp`, `pg_trgm`. Connection Pooling (PgBouncer) ativado. `DATABASE_URL` (Pooled) no Render/Vercel. | `psql` conecta; `SELECT version();` retorna PG 16+. `alembic upgrade head` roda sem erro (vazio inicial). |
| **0.5 Auth (Clerk Hobby)** | Criar Aplicação Clerk. Habilitar **Organizations**. Configurar Webhooks: `user.created`, `organization.created`, `organizationMembership.created` → `https://<api-domain>/api/v1/webhooks/clerk`. | Webhook recebido no Render (logs 200); Usuário criado no Clerk aparece no `User` local via sync. |
| **0.6 Storage (Cloudflare R2)** | Criar Bucket `manutcar-dev`. API Token (Object Read/Write). CORS Policy: `AllowedOrigins: ["https://*.vercel.app", "https://*.onrender.com"]`, `AllowedMethods: ["GET", "PUT", "POST", "DELETE"]`. | Upload via Presigned URL (teste `curl`) funciona; Arquivo visível no Dashboard R2. |
| **0.7 E-mail (Resend Free)** | Verificar domínio (ou usar `onrender.com`/`vercel.app` para teste). Criar API Key. Testar envio via `resend.emails.send`. | E-mail de teste recebido na caixa de entrada. |
| **0.8 Push (FCM Spark)** | Criar Projeto Firebase. Project Settings → Cloud Messaging → Web Push Certificates (VAPID Key). Configurar `NEXT_PUBLIC_FCM_VAPID_KEY` no Vercel. | Service Worker recebe push de teste (console FCM). |
| **0.9 CI/CD (GitHub Actions)** | Workflows: `ci.yml` (Lint `ruff`/`eslint`, Typecheck `mypy`/`tsc`, Test `pytest`/`vitest`, Build Docker), `cd-preview.yml` (Deploy Vercel Preview + Render Preview), `cd-prod.yml` (Tag `v*` → Deploy Production). | PR aberta roda CI; Merge em `main` deploya Preview; Tag `v0.1.0` deploya Prod (Vercel/Render). |

---

### 5.1. Sprint 1 a 5: Desenvolvimento Funcional (Incremento 1)

| Sprint | Foco Técnico | Entregas Verificáveis (Critérios de Aceitação de Sprint) |
| :--- | :--- | :--- |
| **Sprint 1** | **Fundação, Banco, Auth & Auditoria** | 1. Modelagem física completa (34 entidades) via Migration (evitar migrations destrutivas futuras).<br>2. `AuditLog` imutável (Trigger/Event Sourcing) capturando `old_values`/`new_values` JSONB.<br>3. Auth (JWT/OAuth2), Criação `Organization` (inclui `OrganizationSettings` defaults), `OrganizationMember` com RBAC base.<br>4. `User` pessoal (Autônomo) cria `Organization` própria automaticamente no onboarding (`DEC-009`). |
| **Sprint 2** | **Frota Base, Propriedade & Odômetro Centralizado** | 1. CRUD `VehicleOwner` (PF/PJ), `Vehicle`, `VehicleOwnershipHistory` (data efetiva).<br>2. `VehicleAssignment` (Motorista x Veículo x Período/Turno) com validação de sobreposição (`RN-FLT-06`).<br>3. **Serviço Centralizado `OdometerReading`**: `record_reading(vehicle_id, km, source, datetime)` implementando `RN-ABS-01` (Bloqueio Regressão), `RN-ABS-02` (Alerta Salto 1500km/24h).<br>4. `VehicleFinancialResponsibility` (Regras padrão por Categoria: Seguro->Proprietário, Combustível->Motorista, etc). |
| **Sprint 3** | **Operação Diária: Checklist & Abastecimento** | 1. `ChecklistTemplate` (Tipos: DAILY, HANDOVER, RETURN), `ChecklistTemplateItem` (Tipos input, `is_safety_critical`, `require_photo_on_fail`).<br>2. `ChecklistExecution` Mobile/Offline-ready (estrutura local-first). Validações: `RN-CHK-03` (Item Crítico -> `MaintenanceRequest` + `RESTRICTED_SAFETY_ALERT`), `RN-CHK-04` (Foto Obrigatória bloqueia `COMPLETED`), `RN-CHK-05` (Atualiza `OdometerReading`).<br>3. `FuelLog` completo: Tanque Cheio/Parcial, Natureza (PRO/PER/SHARED), Pagador/Resp.Econômico. Cálculo `km/l` (`RN-ABS-04`) e Alerta Anomalia 15% (`RN-ABS-07`). Upload Comprovante. |
| **Sprint 4** | **Manutenção Essencial & Documentação Base** | 1. `MaintenancePlan` (KM + Dias, "O que ocorrer primeiro" `RN-MNT-01`), Associação Flexível (Veículo/Modelo/Global `RN-MNT-02`), Semáforo Status (`RN-MNT-03`).<br>2. `MaintenanceRequest` (Origens: Driver, Checklist_Auto, Plan, Manual `RN-MNT-04`).<br>3. `WorkOrder` / `WorkOrderItem` (Peça/Serviço, Garantia KM/Dias, Fornecedor). **Encerramento OS:** Exige Pagador/Resp.Econômico (`CT-RN-02`), Gera `FinancialLedgerEntry` automático (`RN-MNT-06`), Alerta Garantia (`CT-RN-07`, `RN-MNT-07`), Anexo Obrigatório > R$ 500 (`RN-MNT-08`).<br>4. `VehicleObligation` / `ObligationInstallment` (IPVA, Licenciamento, Seguro, GNV). `DriverLicense` (Validade, Bloqueio Alocação se Vencida `CT-RN-01`, `RN-DOC-08`). `TrafficTicket` (Registro Completo `RN-DOC-04`). Alertas Escalonados Job Diário (`RN-DOC-03`). |
| **Sprint 5** | **Motor Financeiro, Receitas CSV/PDF & Relatórios MVP** | 1. `FinancialLedgerEntry` (Razão Unificado): Campos `payer_entity`, `economic_owner_entity`, `natureza_uso` (PRO/PER/SHARED), `settlement_status`. Validação `RN-FIN-01`, `RN-FIN-02`, `RN-FIN-03`.<br>2. `RevenueEntry` (Operacional/Contratual). `PlatformImportBatch` (CSV/PDF Uber/99) com Hash SHA-256 Idempotência (`CT-RN-04`, `RN-FIN-08`). Vinculo Receita -> `VehicleAssignment` por Data/Hora (`RN-FIN-07`).<br>3. **Relatórios Gerenciais (4 Perspectivas `RF-FLT-14`):**<br>   - **Org:** DRE Consolidado / Fluxo Caixa.<br>   - **Proprietário:** Resultado Econômico dos seus veículos (apenas escopo autorizado).<br>   - **Veículo:** TCO/km (`RN-ABS-06`), Rentabilidade, Histórico.<br>   - **Motorista:** KM Profissional, Receitas, Despesas Responsáveis.<br>4. `SettlementStatement` (Estrutura pronta para geração no Incremento 2). |

---

## 6. Rastreabilidade Consolidada (Matriz Resumo)

| Código | Descrição | Origem | Incremento | Sprint | Casos de Teste (CT) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RF-FLT-01` a `18` | Gestão Frota/Propriedade | Spec v2.1 | 1, 2 | 1, 2, 4 | `CT-RN-01`, `07`, `08` |
| `RF-MNT-01` a `08` | Manutenção/Garantia | Spec v2.1 | 1, 2 | 4 | `CT-RN-02`, `06`, `07` |
| `RF-ABS-01` a `06` | Abastecimento/Consumo | Spec v2.1 | 1 | 3 | `CT-RN-05`, `10` |
| `RF-FIN-01` a `07` | Financeiro/Receitas/Rateio | Spec v2.1 | 1, 2 | 5 | `CT-RN-02`, `03`, `04`, `09`, `10`, `11` |
| `RF-DOC-01` a `08` | Docs/Multas/CNH | Spec v2.1 | 1, 2 | 4 | `CT-RN-01`, `13` |
| `RF-CHK-01` a `07` | Checklist/Segurança | Spec v2.1 | 1, 2 | 3 | `CT-RN-06` |
| `RN-FLT-01` a `08` | Governança/Acesso/Auditoria | Rules v2.1 | 1, 2 | 1, 2 | `CT-RN-01`, `07`, `08` |
| `RN-FIN-01` a `10` | Contabilidade/Rateio/Receita | Rules v2.1 | 1, 2 | 5 | `CT-RN-02`, `03`, `04`, `09`, `10`, `11` |
| `RN-ABS-01` a `08` | Odômetro/Consumo/TCO | Rules v2.1 | 1 | 2, 3 | `CT-RN-05`, `10` |
| `RN-MNT-01` a `08` | Planos/OS/Garantia/Anexos | Rules v2.1 | 1, 2 | 4 | `CT-RN-02`, `06`, `07` |
| `RN-DOC-01` a `08` | Obrigações/Multas/CNH/Infrator | Rules v2.1 | 1, 2 | 4 | `CT-RN-01`, `13` |
| `RN-CHK-01` a `07` | Templates/Execução/Crítico/Handover | Rules v2.1 | 1, 2 | 3 | `CT-RN-06` |
| `RN-AUD-01` a `04` | Log/Soft Delete/LGPD/Timezone | Rules v2.1 | 1, 2 | 1, 2 | `CT-RN-12` |

---

## 7. Resumo de Adiamentos Explícitos (Conforme `DEC-021`)

Os seguintes itens da Arquitetura Definitiva **NÃO** fazem parte do Incremento 1 (MVP Core) e estão formalmente adiados:

| Item Adiado | Incremento Alvo | Dependência / Gatilho |
| :--- | :--- | :--- |
| **Redis / Upstash / BullMQ / Workers Assíncronos** | Inc. 2 | Necessidade de `SettlementStatement` assíncrono, jobs pesados de rateio, notificações em massa. |
| **WhatsApp / Evolution API (Self-hosted)** | Inc. 3 | Necessidade de canal de notificação crítico/transacional; homologação Meta. |
| **App Nativo Mobile (React Native / Expo)** | Inc. 3 | PWA (Next.js + Workbox + Dexie.js) atende Offline-First Inc. 1/2. |
| **Integrações Diretas API (Uber/99, SENATRAN/Caronte.io)** | Inc. 2 / 3 | Parser CSV/PDF (`PlatformImportBatch`) atende Inc. 1. Requer `DataConsent` robusto e homologação. |
| **Motor Preditivo TCO / IA (Scikit-learn, XGBoost, TimescaleDB)** | Inc. 3 | Requer volume histórico de dados (Odômetro, OS, Combustível) para treino. |
| **Extensão TimescaleDB (PostgreSQL)** | Inc. 3 | Instalar no Neon/CloudSQL apenas quando modelo preditivo for iniciado. |

---

*Fim do Documento MC-DOC-RDM-001 v2.2*
