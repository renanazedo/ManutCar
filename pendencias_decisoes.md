# PENDÊNCIAS E DECISÕES ARQUITETURAIS — ManutCar

**Código do Documento:** MC-DOC-DEC-001  
**Status:** Consolidado para Revisão Final  
**Versão:** 2.0  
**Referências:**  
* `MC-DOC-VIS-001` (`VISÃO_DO_PRODUTO.md`)  
* `MC-DOC-ESP-001` (`ESPECIFICACAO_FUNCIONAL.md` v2.0)  
* `MC-DOC-RN-001` (`REGRAS_DE_NEGOCIO.md` v2.0)  
* `MC-DOC-RDM-001` (`ROADMAP.md` v2.0)  

---

## 1. Decisões Arquiteturais Consolidadas (ADR — Architectural Decision Records)

As decisões abaixo estão **fechadas e congeladas** para orientar a modelagem técnica e os agentes de código (Aider):

| ID | Tema | Decisão Tomada | Rastreabilidade |
| :--- | :--- | :--- | :--- |
| **DEC-001** | **Arquitetura Multi-Tenant Híbrida** | O sistema nasce **multiorganização, multiusuário e multiproprietário** desde a Sprint 1, mapeando todas as **34 entidades conceituais** no schema inicial para evitar refatorações futuras. | `RF-FLT-01` a `05`, `ROADMAP` Sec. 1 e 5 |
| **DEC-002** | **Titularidade Perpétua do Ativo** | O prontuário técnico (`WorkOrder`, `MaintenancePlan`, `OdometerReading`, `ChecklistExecution`) pertence ao **Veículo**, acompanhando-o em trocas de motorista, gestor ou proprietário. | `RF-FLT-11`, `RN-FLT-03` |
| **DEC-003** | **Separação Contábil (Caixa vs. DRE)** | Todo lançamento financeiro (`FinancialLedgerEntry`) exige separação entre **Pagador** (`payer_entity`) e **Responsável Econômico** (`economic_owner_entity`), gerando reembolsos automáticos e evitando dupla contagem. | `RF-FLT-13`, `RN-FIN-01` a `03` |
| **DEC-004** | **Governança de Veículos de Terceiros** | Acesso a veículos de terceiros exige vínculo formal (`VehicleManagementAgreement`) e escopo granular (`VehicleAccessPermission`). O conhecimento da placa não concede acesso. | `RF-FLT-06`, `RN-FLT-01`, `RN-FLT-02` |
| **DEC-005** | **Privacidade LGPD (Uber/99)** | Contas pessoais Uber/99 pertencem exclusivamente ao motorista. Gestores e proprietários só acessam dados financeiros mediante `DataConsent` explícito e revogável. | `RF-FLT-18`, `RN-FLT-04`, `RN-AUD-03` |
| **DEC-006** | **Fonte Única e Monotônica de Odômetro** | Todas as leituras de quilometragem convergem para `OdometerReading`, impondo ordem estritamente crescente (`RN-ABS-01`) e alerta de salto anômalo (`RN-ABS-02`). | `RF-ABS-02`, `RF-CHK-04` |
| **DEC-007** | **Parametrização por Organização** | Limites numéricos (salto de odômetro, queda de consumo `km/l`, dias de alerta preventivo, exigência de vistoria) ficam armazenados em `OrganizationSettings`, proibindo valores *hardcoded*. | `RN-ABS-02`, `RN-ABS-06`, `RN-MNT-02`, `RN-CHK-06` |
| **DEC-008** | **Estratégia de Entrega por Incrementos** | Execução tática em **3 Incrementos** alinhados a **2 Fases Estratégicas** (Fase 1: Base + Governança; Fase 2: Avançado). Incremento 1 atende os 4 perfis (B2C, B2B, B2B2C, Gestor) com fluxo operacional e CSV/manual. | `VISÃO` Sec. 3, `ROADMAP` Sec. 1 e 2 |
| **DEC-009** | **Onboarding B2C — Organization Pessoal Automática** | **Opção A adotada:** No cadastro do motorista autônomo, o sistema cria automaticamente uma `Organization` pessoal ("Minha Operação") com o usuário como `Admin`, mantendo `organization_id` obrigatório (NOT NULL) em todas as tabelas transacionais e simplificando 100% do RBAC e queries. | `PEND-001`, `ROADMAP` Sprint 1, `RF-FLT-01`, `RF-FLT-02` |
| **DEC-010** | **Entidade `VehicleModel` para Planos Preventivos** | Inclusão da entidade `VehicleModel` (marca, modelo, ano, motor, combustível) para suportar associação flexível de `MaintenancePlan` (Veículo Específico / Modelo / Global) conforme `RN-MNT-02`. | `RF-MNT-02`, `RN-MNT-02`, `ROADMAP` Sprint 2 |

---

## 2. Questões e Decisões Pendentes (A Resolver Antes do Código)

### 2.1. Pendências de Produto e Regra de Negócio (Bloqueantes para Sprint 1–5)

| ID | Questão / Pendência | Alternativas e Impacto Técnico | Status |
| :--- | :--- | :--- | :--- |
| **PEND-001** | **Onboarding do Motorista Autônomo (B2C)** | **RESOLVIDO → DEC-009.** Criação automática de `Organization` pessoal transparente. | **Fechado (DEC-009)** |
| **PEND-002** | **Formatos de Extrato Uber e 99 (Incremento 1)** | Definir quais arquivos reais de CSV (estrutura de colunas: data, valor bruto, taxas, gorjetas, bônus, km, ID da corrida) da Uber Motorista e 99 Motorista serão suportados pelo parser inicial (`PlatformImportBatch`) na Sprint 5, além do lançamento manual. Necessário obter amostras reais. | **Em Aberto (Crítico p/ Sprint 5)** |
| **PEND-003** | **Rateio de Despesas Fixas em Uso Compartilhado (Incremento 2)** | A regra `RN-FIN-05` define rateio por KM para despesas variáveis (`SHARED`). Para despesas fixas (IPVA, Seguro, Licenciamento, Aluguel) de veículo compartilhado por múltiplos motoristas no mês, o rateio será **por dias de alocação** (`dias_motorista / dias_mês`) ou **proporcional ao KM rodado**? Impacta `VehicleFinancialResponsibility` e `SettlementStatement`. | **Em Aberto (Incremento 2)** |
| **PEND-004** | **Modelo de Planos e Limites do SaaS (Comercial)** | Definir se haverá entidade `SubscriptionPlan` no banco desde a Sprint 1 (ex.: limite de veículos ativos no plano gratuito vs. planos pagos por frota, limite de usuários, armazenamento de anexos). Necessário para `OrganizationSettings` e gating de features. | **Em Aberto (Pré-Sprint 1)** |
| **PEND-005** | **Estratégia de Numeração de Documentos Fiscais** | Definir padrão para `WorkOrder.number`, `FuelLog.document_number`, `TrafficTicket.infraction_auto_number`: sequencial por organização? Global? Com prefixo? Impacta unicidade e auditoria. | **Em Aberto (Sprint 1)** |
| **PEND-006** | **Tratamento de Fusos Horários (Multi-região)** | O sistema atenderá apenas Brasil (UTC-3) na Fase 1 ou suportará múltiplos fusos? Impacta `OdometerReading.timestamp`, `ChecklistExecution.started_at`, `TrafficTicket.infraction_datetime`, jobs de alerta (`RN-DOC-03`). Recomendação: armazenar tudo em UTC, exibir no fuso da `OrganizationSettings.timezone`. | **Em Aberto (Sprint 1)** |

### 2.2. Pendências de Arquitetura Técnica e Infraestrutura (Item 4 do Plano — Pré-Requisito para Sprint 1)

| ID | Camada Técnica | Decisão Necessária | Impacto nas Sprints |
| :--- | :--- | :--- | :--- |
| **PEND-007** | **Stack Backend e Frontend** | Escolher linguagem/framework principal (ex.: **Python/FastAPI** ou **Node/TypeScript (NestJS/Next.js)**) considerando facilidade de geração de código, tipagem forte, ecossistema de testes e integração com **Aider**. | Define estrutura do repositório, Sprint 1. |
| **PEND-008** | **Estratégia Mobile para Motoristas** | Definir se o acesso do motorista no Incremento 1 será via **Web Responsivo / PWA** (código único, deploy único, offline via Service Worker + IndexedDB) ou aplicativo nativo separado (React Native / Flutter). `RN-CHK-02` exige offline-first. | Impacta Sprint 3 (`ChecklistExecution`, `FuelLog`). |
| **PEND-009** | **Banco de Dados Relacional** | Confirmar **PostgreSQL 15+** como banco oficial (necessário para integridade transacional, chaves estrangeiras rígidas, `JSONB` em `AuditLog`/`OrganizationSettings`, `UUID` PKs, Partial Indexes para `deleted_at`). | Impacta Sprint 1 (Migrations). |
| **PEND-010** | **Storage de Arquivos (Fotos e PDFs)** | Definir provedor compatível com S3 (ex.: **Supabase Storage**, **Cloudflare R2**, **MinIO** local/VPS, AWS S3) para armazenar fotos obrigatórias de checklist (`RN-CHK-04`), notas fiscais de OS, CNH, comprovantes de obrigação. Definir bucket/políticas por organização. | Impacta Sprint 3 e Sprint 4. |
| **PEND-011** | **Hospedagem, Auth e Notificações** | Definir infraestrutura de deploy (ex.: **VPS com Docker / Coolify / Dokploy** ou **Vercel/ Railway / Render**), provedor de autenticação (**Auth.js / NextAuth**, **Clerk**, **Keycloak** self-hosted, ou JWT próprio) e canal de alertas (e-mail: **Resend / SendGrid / SES**; Push: **Firebase / OneSignal**; WhatsApp: **Z-API / Evolution API**). | Impacta Sprint 1 (Auth) e Sprint 4 (Alertas Job). |
| **PEND-012** | **Estratégia de Testes e Qualidade** | Definir ferramentas: Unit/Integration (**Vitest / Pytest**), E2E (**Playwright / Cypress**), Contrato (**Pact**), Cobertura mínima (ex.: 80% regras de negócio), CI/CD (**GitHub Actions / GitLab CI**). `ROADMAP` exige suíte automatizada para `CT-RN-01` a `CT-RN-10`. | Impacta Sprint 1 (Pipeline) e todas. |

---

## 3. Novas Pendências Identificadas na Consolidação v2.0

| ID | Origem | Descrição | Prioridade |
| :--- | :--- | :--- | :--- |
| **PEND-013** | `ESPECIFICACAO_FUNCIONAL.md` Sec. 3.3 / `REGRAS_DE_NEGOCIO.md` `RN-MNT-02` | **Entidade `VehicleModel`**: Necessária para associar `MaintenancePlan` a modelos de frota (não apenas veículo específico). Atributos: `make`, `model`, `year`, `engine`, `fuel_type`, `consumption_reference_km_l` (para baseline de alerta `RN-ABS-07`). | **Alta (Sprint 2)** |
| **PEND-014** | `REGRAS_DE_NEGOCIO.md` `RN-ABS-07` | **Baseline de Consumo por Modelo**: O alerta de anomalia (15% abaixo da média móvel dos últimos 5 ciclos) requer um valor inicial para veículos novos/sem histórico. Usar `VehicleModel.consumption_reference_km_l` (tabela Fipe/fábrica) ou permitir cadastro manual no `Vehicle`? | **Média (Sprint 3)** |
| **PEND-015** | `REGRAS_DE_NEGOCIO.md` `RN-FIN-08` | **Algoritmo de Hash para Idempotência**: `PlatformImportBatch.file_hash` — usar SHA-256 do conteúdo bruto do arquivo? Incluir metadados (driver_id, data_import) no hash? Definir colisão como erro 409. | **Alta (Sprint 5)** |
| **PEND-016** | `REGRAS_DE_NEGOCIO.md` `RN-DOC-05` | **Resolução de Conflito de Turno (Múltiplos Motoristas)**: Se `VehicleAssignment` sobreposto (`>1 motorista` no momento da infração), a regra exige seleção manual. A UI deve apresentar lista dos motoristas conflitantes com botão de confirmação. Registrar `identification_method = MANUAL`. | **Média (Incremento 2)** |
| **PEND-017** | `ROADMAP.md` Incremento 3 / `ESPECIFICACAO_FUNCIONAL.md` Sec. 6 | **Integração SENATRAN/Detran**: Para Incremento 3, definir provedor de API (ex.: **Caronte**, **Detran.Digital**, **APIs oficiais estaduais**) para consulta de infrações, pontuação CNH, licenciamento. Requer credenciais/homologação. | **Baixa (Pós-Incremento 2)** |
| **PEND-018** | `ROADMAP.md` Incremento 3 | **Motor Preditivo de TCO**: Definir stack de ML/Analytics (ex.: **Python/Scikit-learn** jobs batch, **TimescaleDB** para séries temporais de odômetro/custos, ou **SQL puro** com window functions) para calcular "Ponto de Virada" (Depreciação Fipe vs Manutenção Acumulada). | **Baixa (Pós-Incremento 2)** |
| **PEND-019** | `REGRAS_DE_NEGOCIO.md` `RN-AUD-03` | **Escopo de Anonimização LGPD**: Lista exata de campos PII em `User` (nome, cpf, cnh, email, phone, address, bank_account?) vs campos operacionais mantidos (id, created_at, avatar?). Definir se `VehicleOwner` (PF) também sofre anonimização. | **Média (Incremento 2)** |

---

## 4. Checklist de Encerramento da Documentação Oficial

* [x] `VISÃO_DO_PRODUTO.md` (`MC-DOC-VIS-001`) — Aprovado
* [x] `ESPECIFICACAO_FUNCIONAL.md` (`MC-DOC-ESP-001` v2.0) — Aprovado
* [x] `REGRAS_DE_NEGOCIO.md` (`MC-DOC-RN-001` v2.0) — Aprovado
* [x] `ROADMAP.md` (`MC-DOC-RDM-001` v2.0) — Aprovado
* [x] `PENDENCIAS_E_DECISOES.md` (`MC-DOC-DEC-001` v2.0) — **Consolidado e Atualizado**

---

## 5. Rastreabilidade das Decisões vs. Pendências Resolvidas

| Pendência Original | Decisão Resultante | Documento de Origem |
| :--- | :--- | :--- |
| `PEND-001` (Onboarding B2C) | `DEC-009` (Org Pessoal Automática) | `ROADMAP` Sprint 1, `RF-FLT-01/02` |
| `PEND-005` (Entidades 27 vs 34) | `DEC-001` Atualizado (34 entidades) | `ROADMAP` Sec. 5 "Total de Entidades Conceituais Mapeadas: 34" |
| `PEND-008` (Terminologia Etapa/Incremento) | `DEC-008` (3 Incrementos / 2 Fases) | `ROADMAP` Sec. 1 |
| `PEND-006` (Offline-first Mobile) | `PEND-008` (Estratégia Mobile) | `RN-CHK-02`, `ROADMAP` Incremento 3 |
| — (VehicleModel ausente) | `DEC-010` (Entidade VehicleModel) | `RF-MNT-02`, `RN-MNT-02` |

*Fim do Documento MC-DOC-DEC-001 v2.0*
