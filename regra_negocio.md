# REGRAS DE NEGÓCIO OFICIAIS — ManutCar

**Código do Documento:** MC-DOC-RN-001  
**Status:** Consolidado para Revisão Final  
**Versão:** 2.1  
**Referências:** MC-DOC-VIS-001 (`VISÃO_DO_PRODUTO.md`), MC-DOC-ESP-001 (`ESPECIFICACAO_FUNCIONAL.md`), MC-DOC-DEC-001 (`PENDENCIAS_E_DECISOES.md` v3.0)  

---

## 1. Regras de Governança, Identidade e Acesso (MC-FLT)

### 1.1. Precedência e Validação de Acesso ao Veículo
* **`RN-FLT-01` (Regra de Ouro do Acesso):** Um usuário vinculado a uma Organização só pode acessar dados de um `Vehicle` se, cumulativamente:
  1. O veículo pertencer à própria Organização (`owner_organization_id == org_id`) **OU** existir um `VehicleManagementAgreement` com status `ACTIVE` entre a Organização e o Proprietário do veículo;
  2. A ação solicitada estiver contida no escopo aprovado em `VehicleAccessPermission`;
  3. O papel do usuário (`OrganizationMember.role`) permitir a ação.
  * *Rastreabilidade: RF-FLT-05, RF-FLT-06, RF-FLT-08, RF-FLT-15*

* **`RN-FLT-02` (Isolamento Temporal):** O acesso concedido por um `VehicleManagementAgreement` aplica-se estritamente aos registros operacionais e financeiros gerados dentro do intervalo `[start_date, end_date]`. Dados financeiros anteriores ao início da gestão ou posteriores à revogação são invisíveis para a Organização.
  * *Rastreabilidade: RF-FLT-06, RF-FLT-07, RF-FLT-17*

* **`RN-FLT-03` (Preservação do Prontuário Técnico):** Registros técnicos (`WorkOrder`, `MaintenancePlan`, `OdometerReading`, `ChecklistExecution` sem dados financeiros privados) são vinculados ao `vehicle_id` de forma permanente e permanecem visíveis ao proprietário atual e a gestores autorizados, independentemente de transferências de titularidade (`VehicleOwnershipHistory`).
  * *Rastreabilidade: RF-FLT-11, RF-FLT-17*

* **`RN-FLT-04` (Consentimento LGPD para Contas Externas):** Dados originados de integrações pessoais do motorista (ex.: extratos Uber/99) só podem ser lidos por uma Organização ou Proprietário se houver um registro `DataConsent` com status `GRANTED` e escopo compatível, assinado pelo motorista titular. A revogação tem efeito imediato sobre consultas futuras.
  * *Rastreabilidade: RF-FLT-18, RF-FIN-02*

* **`RN-FLT-05` (Autorização Granular por Escopo):** O `VehicleAccessPermission` deve permitir controle independente para os domínios: `MAINTENANCE_READ`, `MAINTENANCE_WRITE`, `OPERATION_READ`, `OPERATION_WRITE`, `FINANCIAL_READ`, `FINANCIAL_WRITE`, `REPORTS_READ`, `DOCUMENTS_READ`. O convite (`OrganizationInvitation`) deve detalhar esses escopos antes do aceite.
  * *Rastreabilidade: RF-FLT-06, RF-FLT-08*

* **`RN-FLT-06` (Múltiplos Motoristas e Turnos):** Um veículo pode possuir múltiplos `VehicleAssignment` ativos simultaneamente (turnos), desde que os intervalos `[start_datetime, end_datetime]` não se sobreponham para o mesmo motorista e a soma das alocações não viole regras de jornada configuradas pela organização.
  * *Rastreabilidade: RF-FLT-09, RF-FLT-10*

* **`RN-FLT-07` (Isolamento de Tenant - Multi-organização):** Dados de uma `Organization` (veículos próprios, membros, lançamentos financeiros internos) são logicamente isolados. Queries SQL devem sempre filtrar por `organization_id` do contexto da sessão, exceto para `SuperAdmin` de plataforma (fora do escopo de negócio padrão).
  * *Rastreabilidade: RF-FLT-15*

* **`RN-FLT-08` (Trilha de Auditoria Obrigatória):** Toda operação de `CREATE`, `UPDATE`, `DELETE`, `APPROVE`, `REVOKE`, `ASSIGN`, `UNASSIGN` nas entidades `Vehicle`, `VehicleManagementAgreement`, `VehicleAssignment`, `VehicleFinancialResponsibility`, `VehicleAccessPermission`, `OrganizationMember`, `DataConsent` deve gerar registro em `AuditLog` com `old_values` e `new_values` (JSON).
  * *Rastreabilidade: RF-FLT-16, RN-AUD-01*

---

## 2. Matriz Oficial de Permissões (RBAC × Escopo)

**Legenda:** **C** = Criar | **R** = Ler/Consultar | **U** = Editar | **D** = Excluir/Cancelar | **A** = Aprovar/Autorizar | **—** = Sem Acesso.  
*Nota: Permissões "R" em dados de terceiros dependem de `VehicleAccessPermission` ativo.*

| Recurso / Operação | Proprietário do Veículo | Admin da Org. | Gestor de Frota | Financeiro | Motorista | Manutenção |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dados da Organização e Membros** | — | C R U D | R | R | — | — |
| **Cadastro de Veículo Próprio (da Org)** | C R U D | C R U D | R U | R | R (vinculado) | R |
| **Autorização de Gestão de Terceiro** | **A / Revogar** | Solicitar / R | Solicitar / R | R | — | — |
| **Alocação de Motorista (`Assignment`)** | R | C R U D | C R U D | R | R (própria) | — |
| **Planos de Manutenção (`MaintenancePlan`)** | R | R | C R U | — | — | C R U |
| **Ordens de Serviço (`WorkOrder`)** | R (se escopo) | R | C R U A | R (custos) | Solicitar / R | C R U |
| **Checklist e Inspeção (`MC-CHK`)** | R | R | C R U | — | C R (próprio) | R |
| **Abastecimento (`MC-ABS`)** | R (se escopo) | R | C R U | R | C R (próprio) | — |
| **Multas e Obrigações (`MC-DOC`)** | R | R | C R U | C R U | R (própria) | — |
| **Lançamentos Financeiros (`MC-FIN`)** | R (seu veículo) | R (se escopo) | R (se escopo) | C R U A | C R (próprio) | — |
| **Extratos Uber/99 do Motorista** | R (só c/ Consent) | R (só c/ Consent) | R (só c/ Consent) | R (só c/ Consent) | C R U D (titular) | — |
| **Templates de Checklist (`ChecklistTemplate`)** | — | R | C R U D | — | — | R |
| **Importação de Plataformas (`PlatformImportBatch`)** | — | — | — | R (só c/ Consent) | C R U D (titular) | — |

---

## 3. Regras Financeiras, Rateio e Contabilidade (MC-FIN / MC-FLT)

### 3.1. Princípio da Dupla Perspectiva (Caixa vs. Competência Econômica)
* **`RN-FIN-01` (Separação Obrigatória):** Todo lançamento em `FinancialLedgerEntry` com valor > 0 deve obrigatoriamente preencher dois campos distintos:
  * `payer_entity` (**Pagador**): Quem desembolsou o recurso financeiro (impacta o Fluxo de Caixa / Reembolsos).
  * `economic_owner_entity` (**Responsável Econômico**): Quem deve arcar com o custo conforme contrato ou regra de negócio (impacta a DRE / Rentabilidade).
  * *Rastreabilidade: RF-FLT-12, RF-FLT-13, RF-MNT-08, RF-DOC-07, RF-ABS-05*

* **`RN-FIN-02` (Geração Automática de Reembolso / Acerto):** Sempre que `payer_entity != economic_owner_entity`, o sistema deve marcar o lançamento com `settlement_status = PENDING_REIMBURSEMENT`, gerando um crédito a receber para o `payer_entity` e um débito a pagar para o `economic_owner_entity` no fechamento periódico (`SettlementStatement`).
  * *Rastreabilidade: RF-FLT-13, RF-FIN-07*

* **`RN-FIN-03` (Prevenção de Dupla Contagem):**
  * Nos relatórios de **Rentabilidade / DRE**, somam-se apenas receitas onde a entidade consultada é beneficiária e despesas onde `economic_owner_entity == entidade_consultada`.
  * Nos relatórios de **Fluxo de Caixa**, somam-se entradas e saídas efetivas onde `payer_entity == entidade_consultada`.
  * Lançamentos de reembolso interno (`settlement_transfer`) movimentam apenas o Fluxo de Caixa, nunca alterando o Resultado Econômico (evitando contar a mesma despesa duas vezes).
  * *Rastreabilidade: RF-FLT-14, RF-FIN-07*

### 3.2. Natureza de Uso e Rateio de Custos Mistos
* **`RN-FIN-04` (Classificação de Natureza):** Toda despesa operacional (abastecimento, pedágio, lavagem, manutenção variável) deve ser classificada em uma de três naturezas:
  1. `PROFESSIONAL`: 100% atribuída à operação profissional (conforme regra contratual).
  2. `PERSONAL`: 100% atribuída ao `economic_owner_entity = Motorista` (não onera a organização nem o proprietário).
  3. `SHARED`: Rateada proporcionalmente com base na quilometragem rodada no período (`km_profissional / km_total`).
  * *Rastreabilidade: RF-ABS-05, RF-FLT-12*

* **`RN-FIN-05` (Fórmula de Rateio Proporcional por KM):**
  $$\text{Custo Profissional} = \text{Valor Total} \times \left(\frac{\text{KM Profissional no Período}}{\text{KM Total no Período}}\right)$$
  $$\text{Custo Particular} = \text{Valor Total} - \text{Custo Profissional}$$
  *O "Período" para cálculo do rateio deve ser o mês calendário ou o período do `SettlementStatement`.*
  * *Rastreabilidade: RF-FLT-13, RF-FIN-07*

* **`RN-FIN-06` (Responsabilidade Financeira por Categoria):** A entidade `VehicleFinancialResponsibility` define regras padrão por `vehicle_id` e `expense_category` (ex.: `INSURANCE` -> Proprietário, `FUEL` -> Motorista, `MAINTENANCE_CORRECTIVE` -> Contrato). Lançamentos manuais podem sobrescrever a regra padrão com justificativa.
  * *Rastreabilidade: RF-FLT-12*

* **`RN-FIN-10` (Rateio Híbrido: Variáveis por KM, Fixas por Dias — DEC-015):**
  * **Despesas Variáveis** (Combustível, Pedágio, Lavagem, Manutenção Corretiva/Preventiva não contratual): Rateio **KM Profissional / KM Total** (conforme `RN-FIN-05`). Campo `rateio_base = 'KM'`.
  * **Despesas Fixas/Periódicas** (IPVA, Licenciamento, Seguro, Proteção Veicular, Aluguel/Depreciação, Parcela Financiamento): Rateio **Dias Alocação Motorista / Dias Período**. Campo `rateio_base = 'DIAS'`.
  * **Fórmula Rateio por Dias:**
    $$\text{Custo Profissional} = \text{Valor Total} \times \left(\frac{\text{Dias Alocação Motorista no Período}}{\text{Dias Totais no Período}}\right)$$
  * Implementação: Campo `rateio_base` ENUM (`KM`, `DIAS`) em `VehicleFinancialResponsibility` com default por `expense_category`.
  * *Rastreabilidade: `DEC-015`, `PEND-003`, `SettlementStatement` Inc. 2*

### 3.3. Regra de Alocação de Receitas (Uber/99)
* **`RN-FIN-07` (Vínculo por Turno):** Quando um motorista operar mais de um veículo no mesmo dia/semana, as receitas importadas ou lançadas devem ser vinculadas ao `vehicle_id` ativo em `VehicleAssignment` cujo intervalo `[start_datetime, end_datetime]` contenha o carimbo de data/hora da corrida ou turno. Caso não haja horário granular no extrato, o motorista deverá selecionar o veículo correspondente antes de confirmar o lote (`PlatformImportBatch`).
  * *Rastreabilidade: RF-FIN-05, RF-FIN-04*

* **`RN-FIN-08` (Importação Idempotente):** A importação de arquivos CSV/PDF (Uber/99) deve gerar hash do conteúdo (`file_hash`). Tentativa de importar arquivo com mesmo `file_hash` e `driver_id` para o mesmo período deve ser bloqueada com erro `DUPLICATE_IMPORT`.
  * *Rastreabilidade: RF-FIN-03, CA-FIN-01*

* **`RN-FIN-09` (Receitas Contratuais):** Valores de locação/diária pagos pelo motorista à organização/proprietário (`RF-FIN-06`) são lançados como `RevenueEntry` com `revenue_type = CONTRACTUAL`, creditando o `economic_owner_entity` (Proprietário/Org) e debitando o motorista, sem passar pelo rateio de km.
  * *Rastreabilidade: RF-FIN-06*

---

## 4. Regras de Odômetro e Consumo (MC-ABS)

### 4.1. Integridade do Odômetro
* **`RN-ABS-01` (Monotonicidade Estrita):** O odômetro é uma grandeza estritamente crescente. Para qualquer registro (`FuelLog`, `ChecklistExecution`, `WorkOrder`), o valor informado (`odometer_value`) deve satisfazer:
  $$\text{odometer\_value} \ge \text{último odômetro válido anterior à data/hora do registro}$$
  Caso seja inferior, o sistema bloqueia o salvamento com erro `ODOMETER_REGRESSION`.
  * *Rastreabilidade: RF-ABS-02, RF-CHK-03, CA-ABS-01, CA-CHK-03*

* **`RN-ABS-02` (Alerta de Salto Anômalo):** Se a diferença entre o novo odômetro e o anterior ultrapassar `1.500 km` em menos de 24 horas (parâmetro configurável por organização em `OrganizationSettings.odometer_jump_alert_km`), o sistema exibe alerta de confirmação (`WARNING_ODOMETER_JUMP`) para evitar erro de digitação (ex.: digitar um zero a mais), mas permite prosseguir mediante confirmação explícita.
  * *Rastreabilidade: RF-ABS-02*

* **`RN-ABS-03` (Fonte Única da Verdade):** A tabela `OdometerReading` é o log unificado e imutável de todas as leituras. Módulos `MC-ABS`, `MC-CHK`, `MC-MNT` **não** armazenam odômetro localmente; apenas referenciam ou inserem em `OdometerReading` via trigger/service centralizado.

### 4.2. Fórmulas de Consumo e Custo por KM
* **`RN-ABS-04` (Cálculo de Média `km/l`):** O consumo médio só é calculado quando há dois registros marcados como **Tanque Cheio** (`is_full_tank = true`), somando-se eventuais abastecimentos parciais (`is_full_tank = false`) ocorridos entre eles:
  $$\text{Média (km/l)} = \frac{\text{Odômetro}_{\text{tanque cheio atual}} - \text{Odômetro}_{\text{tanque cheio anterior}}}{\text{Litros}_{\text{atual}} + \sum \text{Litros}_{\text{parciais intermediários}}}$$
  Abastecimentos parciais isolados (sem tanque cheio anterior/posterior válido) não geram média individual.
  * *Rastreabilidade: RF-ABS-03, CA-ABS-02*

* **`RN-ABS-05` (Custo por Quilômetro — Combustível):**
  $$\text{Custo Combustível/km} = \frac{\sum \text{Valor Total Combustível (Natureza PROFESSIONAL + Rateio SHARED) no Período}}{\text{KM Rodado Profissional no Período}}$$
  * *Rastreabilidade: RF-ABS-03, RN-FIN-05*

* **`RN-ABS-06` (Custo Total por Quilômetro — TCO Operacional):**
  $$\text{TCO/km} = \frac{\sum (\text{Combustível Rateado} + \text{Manutenção Rateada} + \text{Obrigações Rateadas} + \text{Seguro Rateado} + \text{Depreciação/Aluguel})}{\text{KM Rodado Profissional no Período}}$$
  * *Rastreabilidade: RF-FLT-14*

* **`RN-ABS-07` (Detecção de Desvio de Consumo):** Se a média calculada (`RN-ABS-04`) for inferior em mais de **15%** (padrão configurável em `VehicleSettings.consumption_alert_threshold_pct`) à média móvel dos últimos 5 ciclos completos daquele veículo com o mesmo combustível, gerar `ConsumptionAnomalyAlert` com severidade `HIGH`.
  * *Rastreabilidade: RF-ABS-06, CA-ABS-03*

* **`RN-ABS-08` (Abastecimento Particular):** Abastecimentos classificados como `PERSONAL` pelo motorista (`RF-ABS-05`) são excluídos dos cálculos de consumo médio da frota/organização e do TCO, impactando apenas o relatório pessoal do motorista.
  * *Rastreabilidade: RF-ABS-05, CA-ABS-03*

---

## 5. Regras de Manutenção Preventiva e Garantias (MC-MNT)

* **`RN-MNT-01` (Gatilho Híbrido — O que ocorrer primeiro):** Para planos preventivos (`MaintenancePlan`) configurados com intervalo de quilometragem ($\Delta KM$) e intervalo de tempo ($\Delta Dias$), o vencimento ocorre na menor data/marcação atingida:
  * $\text{KM Alvo} = \text{KM Última Execução} + \Delta KM$
  * $\text{Data Alvo} = \text{Data Última Execução} + \Delta Dias$
  * *Rastreabilidade: RF-MNT-01, RF-MNT-03*

* **`RN-MNT-02` (Associação Flexível):** Um `MaintenancePlan` pode ser associado a:
  1. Um `Vehicle` específico (sobrescreve padrão do modelo).
  2. Um `VehicleModel` (aplica-se a todos os veículos daquele modelo sem plano específico).
  3. Global (padrão da organização para veículos sem modelo cadastrado).
  * *Rastreabilidade: RF-MNT-02*

* **`RN-MNT-03` (Semáforo de Status Preventivo):**
  * **VENCIDO (`OVERDUE`):** $\text{Odômetro Atual} \ge \text{KM Alvo}$ **OU** $\text{Data Atual} > \text{Data Alvo}$.
  * **PRÓXIMO (`DUE_SOON`):** Faltam $\le 10\%$ do $\Delta KM$ (parâmetro `OrganizationSettings.preventive_due_soon_km_pct`, padrão 10%) **OU** $\le 15\text{ dias}$ (parâmetro `OrganizationSettings.preventive_due_soon_days`, padrão 15) para a Data Alvo.
  * **EM DIA (`OK`):** Acima das margens de atenção.
  * *Rastreabilidade: RF-MNT-03, CA-MNT-01*

* **`RN-MNT-04` (Origem da Solicitação):** `MaintenanceRequest` pode ser originado por: `DRIVER_APP` (checklist/reporte), `CHECKLIST_AUTO` (item reprovado crítico - `RN-CHK-01`), `PLAN_SCHEDULED` (preventivo vencido), `MANAGER_MANUAL`. O campo `source` é obrigatório.
  * *Rastreabilidade: RF-MNT-04, RF-CHK-05*

* **`RN-MNT-05` (Estrutura da Ordem de Serviço):** `WorkOrder` agrupa `WorkOrderItem` (Peça ou Serviço). Cada item deve ter: `description`, `quantity`, `unit_price`, `total_price`, `warranty_km`, `warranty_days`, `supplier_id`. O somatório dos itens define `WorkOrder.total_cost`.
  * *Rastreabilidade: RF-MNT-05, RF-MNT-07*

* **`RN-MNT-06` (Lançamento Financeiro Automático):** Ao encerrar `WorkOrder` com `total_cost > 0` e status `COMPLETED`, o sistema **deve** criar `FinancialLedgerEntry` (ou rascunho pendente de aprovação do Financeiro) aplicando `VehicleFinancialResponsibility` (`RN-FIN-06`) para determinar `payer_entity` e `economic_owner_entity`. O `WorkOrder` fica travado para edição financeira após geração do lançamento.
  * *Rastreabilidade: RF-MNT-08, CA-MNT-02*

* **`RN-MNT-07` (Alerta de Reincidência em Garantia):** Ao adicionar um `WorkOrderItem` a uma OS em aberto, o sistema verifica se existe item com mesmo `part_number` ou `service_code` em OS anterior (`COMPLETED`) onde:
  $$\text{Data Atual} \le \text{Data OS Anterior} + \text{Garantia Dias} \quad \text{E} \quad \text{Odômetro Atual} \le \text{Odômetro OS Anterior} + \text{Garantia KM}$$
  Se verdadeiro, exibe alerta bloqueante (`WARRANTY_COVERAGE_POSSIBLE`) informando fornecedor, OS original e dias/km restantes.
  * *Rastreabilidade: RF-MNT-06, CA-MNT-03*

* **`RN-MNT-08` (Anexos Obrigatórios para Valores Altos):** OS com `total_cost` superior a parâmetro `OrganizationSettings.os_attachment_threshold` (padrão R$ 500,00) exigem pelo menos 1 anexo (NF/Orçamento/Foto) para permitir status `COMPLETED`.

---

## 6. Regras de Documentação, Multas e Identificação de Condutor (MC-DOC)

* **`RN-DOC-01` (Cadastro de Obrigações):** `VehicleObligation` suporta tipos: `IPVA`, `LICENSING` (CRLV), `INSURANCE`, `PROTECTION`, `GNV_INSPECTION`, `OTHER`. Cada obrigação gera `ObligationInstallment` (parcelas) com `due_date`, `amount`, `status` (`PENDING`, `PAID`, `OVERDUE`, `WAIVED`). Parcelas pagas exigem comprovante (anexo).
  * *Rastreabilidade: RF-DOC-01*

* **`RN-DOC-02` (Controle de CNH):** `DriverLicense` armazena: `registry_number`, `category`, `expiration_date`, `status` (`VALID`, `EXPIRED`, `SUSPENDED`, `CASSED`). O sistema valida `expiration_date` contra data atual.
  * *Rastreabilidade: RF-DOC-02*

* **`RN-DOC-03` (Alertas Escalonados):** Alertas de vencimento (Obrigações e CNH) são disparados automaticamente via job diário nos marcos: **30, 15, 7, 1 dia(s) antes** e **no dia do vencimento**. Canais: In-app, E-mail, Push (configurável por `UserNotificationPreference`).
  * *Rastreabilidade: RF-DOC-03, CA-DOC-02*

* **`RN-DOC-04` (Registro de Infração Completo):** `TrafficTicket` exige: `infraction_auto_number`, `infraction_datetime`, `infraction_code` (ex.: 501-10), `location`, `speed_limit`/`measured_speed` (se aplicável), `points`, `full_amount`, `discounted_amount`, `indication_deadline`, `status` (`PENDING_INDICATION`, `INDICATED`, `CONFIRMED`, `APPEALED`, `PAID`, `CANCELLED`).
  * *Rastreabilidade: RF-DOC-04*

* **`RN-DOC-05` (Identificação Automática de Infrator — DEC-018):** Ao registrar `TrafficTicket` com `infraction_datetime`, o sistema consulta `VehicleAssignment` buscando registro onde:
  $$\text{vehicle\_id} = \text{ticket.vehicle\_id} \quad \text{E} \quad \text{start\_datetime} \le \text{infraction\_datetime} \le \text{COALESCE(end\_datetime, NOW)}$$
  * Se encontrar **1 motorista**, preenche `suggested_driver_id`, `identification_method = 'AUTO_ASSIGNMENT'`.
  * Se encontrar **0 motoristas**, preenche `responsible_entity = 'OPERATIONAL_HOLDER'` (Org Gestora ou Proprietário), `identification_method = 'FALLBACK_OWNER'`.
  * Se encontrar **>1 motorista** (sobreposição de turno), `identification_method = 'MANUAL'`. UI (Modal) lista motoristas conflitantes com `start/end` do turno. Usuário (Gestor/Admin) seleciona um → `selected_driver_id`. Bloqueia salvamento sem seleção.
  * *Rastreabilidade: RF-DOC-05, CA-DOC-01, `DEC-018`*

* **`RN-DOC-06` (Fluxo de Indicação de Condutor):** O sistema controla `TrafficTicket.indication_status`:
  1. `PENDING_INDICATION`: Aguardando indicação (prazo `indication_deadline`).
  2. `INDICATED`: Motorista indicado, aguardando confirmação do órgão/condutor.
  3. `CONFIRMED`: Órgão confirmou; multa migrada para o prontuário do motorista.
  4. `APPEALED`: Recurso interposto (suspende pagamento).
  5. `PAID`: Quitada (gera `FinancialLedgerEntry`).
  * *Rastreabilidade: RF-DOC-06*

* **`RN-DOC-07` (Responsabilidade Econômica da Multa):** Por padrão, o `economic_owner_entity` de uma multa é o motorista infrator identificado (`RN-DOC-05`). Caso o Proprietário ou a Organização efetue o pagamento (`payer_entity`) para aproveitar desconto, o sistema registra o pagamento e cria pendência de reembolso (`RN-FIN-02`) contra o motorista infrator.
  * *Rastreabilidade: RF-DOC-07, CA-DOC-03*

* **`RN-DOC-08` (Bloqueio Operacional por CNH):** Se `DriverLicense.expiration_date` < `CURRENT_DATE` (vencida) OU `status` IN (`SUSPENDED`, `CASSED`), o sistema **impede** a criação de novo `VehicleAssignment` (alocação) para esse motorista. Exceção: `Admin` da Organização pode forçar com `override_reason` registrado em `AuditLog`.
  * *Rastreabilidade: RF-DOC-02, RN-DOC-03*

---

## 7. Regras de Checklist e Segurança Operacional (MC-CHK)

* **`RN-CHK-01` (Estrutura de Template):** `ChecklistTemplate` define `type` (`DAILY`, `HANDOVER`, `RETURN`, `CUSTOM`). Itens (`ChecklistTemplateItem`) possuem: `order`, `description`, `input_type` (`OK_NOK`, `NUMERIC`, `TEXT`, `PHOTO`, `SIGNATURE`), `is_mandatory`, `is_safety_critical`, `require_photo_on_fail`, `standard_value` (para numéricos, ex.: pressão pneu).
  * *Rastreabilidade: RF-CHK-01*

* **`RN-CHK-02` (Execução Mobile/Offline):** `ChecklistExecution` registra: `template_id`, `vehicle_id`, `driver_id`, `started_at`, `completed_at`, `odometer_start`, `odometer_end`, `fuel_level_start`, `fuel_level_end`, `signature_driver`, `signature_manager` (opcional), `status` (`IN_PROGRESS`, `COMPLETED`, `CANCELLED`). Deve suportar sincronização offline-first.
  * *Rastreabilidade: RF-CHK-02*

* **`RN-CHK-03` (Bloqueio Preventivo por Item Crítico):** Se qualquer item com `is_safety_critical = true` for respondido como `NOK` (Não Conforme):
  1. O sistema gera automaticamente `MaintenanceRequest` com `source = CHECKLIST_AUTO`, `priority = HIGH`, `description` = "Falha crítica em checklist: [item.description]".
  2. O status operacional do veículo (`Vehicle.operational_status`) muda para `RESTRICTED_SAFETY_ALERT`.
  3. Notificação imediata (Push/Email) para Gestores de Frota e Admin da Organização.
  * *Rastreabilidade: RF-CHK-06, CA-CHK-02, RN-MNT-04*

* **`RN-CHK-04` (Obrigatoriedade de Evidência Fotográfica):** A `ChecklistExecution` não pode transicionar para `COMPLETED` se houver qualquer `ChecklistResponseItem` onde:
  `response = NOK` **E** `template_item.require_photo_on_fail = true` **E** `response_item.photos.count = 0`.
  Erro: `MISSING_MANDATORY_PHOTO`.
  * *Rastreabilidade: RF-CHK-03, CA-CHK-01*

* **`RN-CHK-05` (Atualização de Odômetro):** Ao finalizar `ChecklistExecution` com `status = COMPLETED`, o `odometer_end` é gravado em `OdometerReading` (source=`CHECKLIST`) se for maior que a última leitura válida. Validação `RN-ABS-01` aplica-se.
  * *Rastreabilidade: RF-CHK-04, RN-ABS-01*

* **`RN-CHK-06` (Vistoria de Troca de Posse - Handover/Return):** Para `VehicleAssignment` com duração prevista > 24h (parâmetro `OrganizationSettings.handover_mandatory_hours`, padrão 24) ou política da org, a criação do `Assignment` (início) exige `ChecklistExecution` de `type = HANDOVER` concluído. O encerramento do `Assignment` (devolução) exige `ChecklistExecution` de `type = RETURN` concluído. O sistema compara respostas de `HANDOVER` vs `RETURN` para detectar novas avarias (`NEW_DAMAGE_DETECTED`).
  * *Rastreabilidade: RF-CHK-07, CA-CHK-03 (parcial)*

* **`RN-CHK-07` (Histórico Comparativo):** O relatório de `VehicleAssignment` deve exibir lado a lado os itens do `HANDOVER` e `RETURN`, destacando diferenças em itens `OK_NOK` e fotos de avarias.

---

## 8. Regras de Auditoria e Integridade de Dados (Transversal)

* **`RN-AUD-01` (Imutabilidade do Log):** Registros na tabela `AuditLog` **nunca** podem ser alterados ou excluídos pela aplicação (apenas `INSERT`). Devem armazenar: `timestamp` (UTC), `actor_user_id`, `organization_id`, `entity_name`, `entity_id`, `action` (`CREATE`, `UPDATE`, `DELETE`, `APPROVE`, `REVOKE`, `ASSIGN`, `UNASSIGN`, `CONSENT_GRANT`, `CONSENT_REVOKE`), `old_values` (JSONB), `new_values` (JSONB), `ip_address`, `user_agent`.
  * *Rastreabilidade: RF-FLT-16*

* **`RN-AUD-02` (Exclusão Lógica / Soft Delete):** Entidades principais (`Vehicle`, `User`, `Organization`, `VehicleOwner`, `WorkOrder`, `FinancialLedgerEntry`, `TrafficTicket`, `VehicleManagementAgreement`, `DataConsent`) **nunca** sofrem exclusão física (`DELETE` no banco) quando possuírem vínculos históricos. Utilizam `deleted_at` (timestamp) + `deletion_reason` (texto obrigatório). Queries padrão filtram `WHERE deleted_at IS NULL`.

* **`RN-AUD-03` (LGPD - Direito ao Esquecimento / Anonimização — DEC-017):** Para `User` (motorista/proprietário PF) que solicitar exclusão de dados pessoais (LGPD Art. 18), o sistema deve:
  1. **Tabela `User` (PF):** Anonimizar campos PII:
     * `full_name` → `"Usuário Removido"`
     * `cpf`, `cnh_number` → `SHA256(val) || '_ANON'`
     * `email` → `anon_<id>@manutcar.local`
     * `phone`, `address`, `bank_account`, `avatar_url` → `NULL`
     * **Preservar:** `id`, `auth_provider_id`, `created_at`, `updated_at`, `status`, `role_global`
  2. **Tabela `VehicleOwner` (PF):** Mesma regra para `name`, `cpf`, `cnh`, `contact_info`. **Preservar:** `id`, `owner_type`, `created_at`.
  3. Manter `User.id` e vínculos operacionais (`VehicleAssignment`, `WorkOrder.executor_id`) para integridade referencial e histórica.
  4. Revogar todos `DataConsent` ativos.
  5. Registrar ação em `AuditLog` com `action = 'ANONYMIZE_LGPD'`.
  * *Rastreabilidade: `DEC-017`, `PEND-019`*

* **`RN-AUD-04` (Fuso Horário em Auditoria):** Todos timestamps em `AuditLog` armazenados em **UTC**. Apresentação convertida para `OrganizationSettings.timezone` da organização do ator.

---

## 9. Parâmetros Configuráveis por Organização (OrganizationSettings)

Para evitar *hardcoding* de regras de negócio, os seguintes parâmetros devem ser armazenados em `OrganizationSettings` (JSONB ou tabela dedicada) com valores padrão do sistema:

| Chave | Descrição | Padrão |
| :--- | :--- | :--- |
| `odometer_jump_alert_km` | Limite de salto de odômetro para alerta (km/24h) | 1500 |
| `consumption_alert_threshold_pct` | % de queda de consumo para alerta de anomalia | 15 |
| `preventive_due_soon_km_pct` | % do intervalo KM para status "Próximo" | 10 |
| `preventive_due_soon_days` | Dias para vencimento para status "Próximo" | 15 |
| `os_attachment_threshold` | Valor mínimo da OS para exigir anexo (R$) | 500.00 |
| `handover_mandatory_hours` | Duração mínima do Assignment para exigir Handover/Return | 24 |
| `fuel_full_tank_tolerance_pct` | Tolerância % para considerar "tanque cheio" em bombas (ex.: 95%) | 95 |
| `settlement_periodicity` | Periodicidade do acerto financeiro (`MONTHLY`, `WEEKLY`, `BIWEEKLY`) | MONTHLY |
| `timezone` | Fuso horário da organização (IANA TZ) | `America/Sao_Paulo` |
| `document_numbering_strategy` | Estratégia de numeração fiscal (`SEQUENTIAL_ORG`, `SEQUENTIAL_GLOBAL`, `PREFIX_ORG_YYYY`) | `PREFIX_ORG_YYYY` |
| `subscription_plan_id` | Plano de assinatura ativo (`FREE`, `PRO`, `ENTERPRISE`) | `FREE` |

---

## 10. Critérios de Aceitação das Regras de Negócio (Validação Técnica)

Estes critérios servem como base para Testes Unitários e de Integração (BDD):

* **CT-RN-01:** Tentar criar `VehicleAssignment` para motorista com CNH vencida -> **Erro 403 `DRIVER_LICENSE_INVALID`** (exceto override Admin).
* **CT-RN-02:** Lançar `FinancialLedgerEntry` com `payer_entity == economic_owner_entity` -> `settlement_status = SETTLED`.
* **CT-RN-03:** Lançar `FinancialLedgerEntry` com `payer_entity != economic_owner_entity` -> `settlement_status = PENDING_REIMBURSEMENT` + Lançamento espelho em `SettlementStatement`.
* **CT-RN-04:** Importar CSV Uber duplicado (mesmo hash) -> **Erro 409 `DUPLICATE_IMPORT`**.
* **CT-RN-05:** Registrar abastecimento com odômetro menor que último `OdometerReading` -> **Erro 400 `ODOMETER_REGRESSION`**.
* **CT-RN-06:** Finalizar Checklist com item crítico `NOK` -> `Vehicle.operational_status = RESTRICTED_SAFETY_ALERT` + `MaintenanceRequest` criada.
* **CT-RN-07:** Encerrar `WorkOrder` > R$ 500 sem anexo -> **Erro 400 `MISSING_ATTACHMENT`**.
* **CT-RN-08:** Tentar acessar `Vehicle` de terceiro sem `VehicleManagementAgreement` ativo -> **Erro 403 `UNAUTHORIZED_VEHICLE_ACCESS`**.
* **CT-RN-09:** Revogar `DataConsent` motorista -> Consultas subsequentes a `RevenueEntry` (Uber/99) por Org/Proprietário retornam **vazio/403**.
* **CT-RN-10:** Calcular rateio `SHARED` com KM Total = 0 -> **Erro 400 `DIVISION_BY_ZERO`** (exigir KM manual ou bloquear rateio).
* **CT-RN-11:** Calcular rateio de despesa fixa (`rateio_base = DIAS`) com Dias Período = 0 -> **Erro 400 `DIVISION_BY_ZERO`**.
* **CT-RN-12:** Solicitar anonimização LGPD -> `User` anonimizado conforme `RN-AUD-03`, `DataConsent` revogados, `AuditLog` registra `ANONYMIZE_LGPD`, FKs preservadas.
* **CT-RN-13:** Cadastrar multa com turno sobreposto (`>1 motorista`) -> `identification_method = MANUAL`, UI Modal exige seleção, bloqueia salvamento sem `selected_driver_id`.

---

*Fim do Documento MC-DOC-RN-001 v2.1*
