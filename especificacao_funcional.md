# ESPECIFICAÇÃO FUNCIONAL OFICIAL — ManutCar

**Código do Documento:** MC-DOC-ESP-001  
**Status:** Consolidado para Revisão Final  
**Versão:** 2.0  
**Referência:** MC-DOC-VIS-001 (`VISÃO_DO_PRODUTO.md`)  

---

## 1. Visão Geral da Arquitetura Funcional
O **ManutCar** opera sob uma arquitetura **multiorganização, multiusuário e multiproprietário**, composta por seis módulos interdependentes que compartilham um núcleo único de identidade, governança de acesso e prontuário veicular. A arquitetura prevê **criação automática de Organização Pessoal ("Minha Operação") no onboarding de Motoristas Autônomos (B2C)**, garantindo `organization_id` obrigatório (NOT NULL) em todas as tabelas transacionais desde o primeiro acesso.

1. **MC-FLT:** Gestão de Frota e Relacionamento com Proprietários
2. **MC-MNT:** Manutenção Preventiva e Corretiva
3. **MC-ABS:** Abastecimento e Controle de Consumo
4. **MC-FIN:** Integração Financeira (Uber e 99) e Receitas
5. **MC-DOC:** Documentação, Multas e IPVA
6. **MC-CHK:** Checklist e Inspeção Diária

---

## 2. Módulo MC-FLT: Gestão de Frota e Proprietários

### 2.1. Objetivo e Escopo
Administrar veículos, proprietários, motoristas, organizações e responsabilidades financeiras em um modelo híbrido (motorista autônomo, frota própria, frota de motoristas e gestor de terceiros), preservando a titularidade jurídica dos dados e o histórico perpétuo de cada veículo.

### 2.2. Regras de Propriedade, Operação e Autorização
* **Separação de Conceitos:** Propriedade jurídica, responsabilidade operacional e responsabilidade financeira são atributos independentes e podem pertencer a entidades distintas.
* **Consentimento Formal:** Administrar veículo de terceiro exige convite formal da organização e aceite explícito do proprietário com escopo definido (manutenção, utilização, financeiro, relatórios, operação). O mero conhecimento da placa não concede acesso.
* **Preservação do Prontuário:** O histórico técnico acompanha o veículo através de trocas de motorista, gestor ou proprietário. Dados financeiros/pessoais privados de titulares anteriores não são expostos a novos titulares.
* **Proteção de Dados (LGPD):** O papel de gestor não concede acesso automático a contas pessoais Uber/99 dos motoristas; a integração exige consentimento individual e revogável.

### 2.3. Papéis e Permissões
* **Proprietário do Veículo:** Controla titularidade, convites e autorizações sobre seus bens.
* **Administrador da Organização:** Gerencia dados da organização, membros e atribuição de papéis.
* **Gestor de Frota:** Administra veículos autorizados, motoristas e operação diária.
* **Financeiro:** Gerencia lançamentos, rateios, contas e relatórios econômicos autorizados.
* **Motorista:** Registra utilização, checklists, abastecimentos e consulta apenas seus registros permitidos.
* **Manutenção:** Registra ordens de serviço, inspeções e planos preventivos.

### 2.4. Requisitos Funcionais (MC-FLT)
* `RF-FLT-01`: Criar organizações de gestão (incluindo criação automática de **Organização Pessoal** para motorista autônomo no cadastro inicial).
* `RF-FLT-02`: Permitir usuários em múltiplas organizações com papéis distintos (o motorista autônomo é `Admin` de sua Organização Pessoal e pode ser `Motorista` em organizações de terceiros).
* `RF-FLT-03`: Cadastrar proprietários pessoa física ou jurídica.
* `RF-FLT-04`: Vincular veículos a proprietários com data efetiva de titularidade.
* `RF-FLT-05`: Permitir administração de veículos próprios e de terceiros pela mesma organização.
* `RF-FLT-06`: Solicitar, consultar escopo e registrar aceite formal de autorização de gestão.
* `RF-FLT-07`: Permitir revogação de autorização pelo proprietário a qualquer momento.
* `RF-FLT-08`: Atribuir papéis e permissões específicas por organização e por veículo.
* `RF-FLT-09`: Permitir múltiplos motoristas por veículo em períodos distintos (histórico cronológico).
* `RF-FLT-10`: Permitir uso compartilhado simultâneo (turnos) conforme autorização.
* `RF-FLT-11`: Preservar histórico de propriedade, gestão e prontuário técnico do veículo em transferências.
* `RF-FLT-12`: Registrar responsáveis financeiros por contrato ou categoria de despesa.
* `RF-FLT-13`: Separar obrigatoriamente **Pagador** (fluxo de caixa) e **Responsável Econômico** (competência do custo).
* `RF-FLT-14`: Gerar relatórios gerenciais sob quatro perspectivas (Organização, Proprietário, Veículo e Motorista) sem dupla contagem.
* `RF-FLT-15`: Impedir acesso não autorizado entre organizações (isolamento de tenant).
* `RF-FLT-16`: Registrar alterações de vínculo, autorização e lançamentos em trilha de auditoria.
* `RF-FLT-17`: Permitir encerramento de vínculo operacional mantendo integridade do histórico anterior.
* `RF-FLT-18`: Exigir autorização individual e específica para integrações externas (LGPD e contas pessoais Uber/99).

### 2.5. Entidades de Dados Previstas (MC-FLT)
* `User` (usuário autenticado no sistema)
* `Organization` (empresa, frota ou estrutura gestora)
* `OrganizationMember` (vínculo e papéis do usuário dentro da organização)
* `VehicleOwner` (proprietário pessoa física ou jurídica)
* `Vehicle` (cadastro mestre do ativo veicular)
* `VehicleOwnershipHistory` (histórico cronológico de titularidade jurídica)
* `VehicleManagementAgreement` (contrato/vínculo de gestão entre organização e veículo)
* `VehicleAssignment` (alocação operacional de motorista ao veículo por período/turno)
* `VehicleFinancialResponsibility` (regras de atribuição econômica por categoria de custo)
* `VehicleAccessPermission` (escopo granular de permissões concedidas pelo proprietário)
* `OrganizationInvitation` (convites de vínculo entre organização, proprietário ou membro)
* `DataConsent` (registro de consentimento LGPD para integrações externas como Uber/99)
* `AuditLog` (trilha imutável de auditoria)

### 2.6. Critérios de Aceitação (MC-FLT)
* **CA-FLT-01:** Uma organização não consegue visualizar ou editar dados de um veículo de terceiro sem um `VehicleManagementAgreement` ativo e aprovado.
* **CA-FLT-02:** Ao revogar uma autorização, a organização perde imediatamente acesso aos dados futuros e restritos, mantendo-se apenas o registro histórico do período em que esteve autorizada.
* **CA-FLT-03:** Ao transferir um veículo para um novo proprietário, o histórico técnico de manutenções permanece visível, mas receitas e despesas privadas do proprietário anterior ficam inacessíveis.
* **CA-FLT-04:** Uma despesa paga pela Organização X cujo responsável econômico é o Proprietário A reflete no caixa da Organização X e no resultado econômico do Proprietário A sem dupla contagem.
* **CA-FLT-05:** Um gestor de frota não consegue acessar dados da conta Uber/99 de um motorista sem um registro ativo em `DataConsent`.

---

## 3. Módulo MC-MNT: Manutenção Preventiva e Corretiva

### 3.1. Objetivo e Escopo
Controlar planos preventivos por quilometragem e/ou tempo, gerenciar ordens de serviço corretivas/preventivas, rastrear garantias de peças e integrar custos ao módulo financeiro.

### 3.2. Requisitos Funcionais (MC-MNT)
* `RF-MNT-01`: Criar planos de manutenção preventiva parametrizáveis por km, dias ou ambos (o que ocorrer primeiro).
* `RF-MNT-02`: Associar planos preventivos a veículos específicos ou modelos de frota.
* `RF-MNT-03`: Calcular automaticamente status de vencimento (*Em dia*, *Próximo*, *Vencido*) com base no odômetro atual.
* `RF-MNT-04`: Registrar solicitações/chamados de manutenção originados por motoristas, checklists ou gestores.
* `RF-MNT-05`: Abrir, acompanhar e encerrar Ordens de Serviço (OS) detalhando tipo, oficina, peças, mão de obra e odômetro.
* `RF-MNT-06`: Registrar prazo e/ou km de garantia para peças e serviços, alertando em caso de abertura de OS reincidente dentro da garantia.
* `RF-MNT-07`: Anexar orçamentos, notas fiscais e fotos às Ordens de Serviço.
* `RF-MNT-08`: Gerar lançamento financeiro automático ao encerrar OS, aplicando `Pagador` e `Responsável Econômico` (`RF-FLT-13`).

### 3.3. Entidades de Dados Previstas (MC-MNT)
* `MaintenancePlan` (definição de regras preventivas por km/tempo)
* `VehicleMaintenanceSchedule` (aplicação do plano a um veículo e cálculo de próxima execução)
* `MaintenanceRequest` (solicitação ou alerta de necessidade de reparo)
* `WorkOrder` (ordem de serviço estruturada)
* `WorkOrderItem` (peças e serviços discriminados com valores e prazos de garantia)
* `ServiceProvider` (oficinas, mecânicos e fornecedores)
* `VehicleModel` (catálogo de modelos: marca, modelo, ano, motor, tipo de combustível, consumo de referência `km/l` para baseline de alertas)

### 3.4. Critérios de Aceitação (MC-MNT)
* **CA-MNT-01:** Ao atualizar o odômetro do veículo via abastecimento ou checklist, o sistema recalcula imediatamente o saldo restante para as próximas revisões preventivas.
* **CA-MNT-02:** O encerramento de uma Ordem de Serviço com valor maior que zero exige a definição de Pagador e Responsável Econômico antes da conclusão.
* **CA-MNT-03:** Ao lançar uma peça já substituída dentro do prazo/km de garantia vigente, o sistema exibe alerta visual de cobertura de garantia.

---

## 4. Módulo MC-ABS: Abastecimento e Consumo

### 4.1. Objetivo e Escopo
Registrar abastecimentos, manter a integridade cronológica do odômetro, calcular eficiência energética (`km/l` ou `km/m³`) e detectar desvios anômalos de consumo.

### 4.2. Requisitos Funcionais (MC-ABS)
* `RF-ABS-01`: Registrar abastecimento com data/hora, veículo, motorista, odômetro, combustível, volume, valor unitário, valor total e indicador de tanque cheio.
* `RF-ABS-02`: Validar sequência de odômetro, bloqueando valores inferiores ao último registro validado ou exigindo justificativa para saltos atípicos.
* `RF-ABS-03`: Calcular automaticamente média de consumo (`km/l`) entre abastecimentos de tanque cheio e custo por quilômetro (`R$/km`).
* `RF-ABS-04`: Permitir anexar comprovante fiscal ou foto da bomba.
* `RF-ABS-05`: Classificar o abastecimento quanto à natureza de uso (*Profissional*, *Particular*, *Compartilhado*) e atribuir Pagador e Responsável Econômico.
* `RF-ABS-06`: Gerar alertas automáticos quando a média de consumo apresentar queda percentual acima do limite parametrizado para o veículo.

### 4.3. Entidades de Dados Previstas (MC-ABS)
* `FuelLog` (registro detalhado de abastecimento)
* `OdometerReading` (histórico unificado de leituras de odômetro originadas por módulos)
* `ConsumptionAnomalyAlert` (registro de alertas de desvio de consumo)

### 4.4. Critérios de Aceitação (MC-ABS)
* **CA-ABS-01:** O sistema impede salvar um abastecimento com odômetro menor que o último registro cronológico válido do veículo.
* **CA-ABS-02:** O cálculo de km/l considera apenas intervalos fechados entre registros marcados como tanque cheio, ignorando abastecimentos parciais isolados para evitar distorção de média.
* **CA-ABS-03:** Abastecimentos classificados como Particular pelo motorista não são cobrados como custo operacional da organização gestora.

---

## 5. Módulo MC-FIN: Integração Financeira (Uber e 99) e Receitas

### 5.1. Objetivo e Escopo
Consolidar receitas operacionais provenientes de aplicativos (Uber, 99) e contratos de locação/repasse, garantindo privacidade ao motorista e apuração exata de lucro líquido.

### 5.2. Requisitos Funcionais (MC-FIN)
* `RF-FIN-01`: Permitir ao motorista importar ou registrar ganhos da Uber e 99 em sua conta pessoal.
* `RF-FIN-02`: Exigir `DataConsent` ativo (`RF-FLT-18`) para que organizações ou proprietários visualizem receitas vinculadas ao motorista.
* `RF-FIN-03`: Importar relatórios/extratos oficiais (CSV/PDF) das plataformas Uber e 99 com validação contra importação duplicada.
* `RF-FIN-04`: Permitir lançamento manual consolidado por turno/dia (ganho bruto, taxas, gorjetas, bônus, km rodado em corrida).
* `RF-FIN-05`: Vincular receitas ao veículo e ao período de alocação (`VehicleAssignment`) correspondente.
* `RF-FIN-06`: Registrar receitas contratuais do veículo (ex.: diária ou semanal de locação paga pelo motorista).
* `RF-FIN-07`: Consolidar demonstrativo de resultado (Receita - Despesas Econômicas) por Organização, Proprietário, Veículo e Motorista.

### 5.3. Entidades de Dados Previstas (MC-FIN)
* `RevenueEntry` (lançamento de receita operacional ou contratual)
* `PlatformImportBatch` (controle de lotes importados de Uber/99 para evitar duplicidade)
* `FinancialLedgerEntry` (razão unificado de receitas e despesas com Pagador, Responsável Econômico e natureza de uso)
* `SettlementStatement` (fechamento/acerto periódico entre organização, proprietário e motorista)

### 5.4. Critérios de Aceitação (MC-FIN)
* **CA-FIN-01:** A importação repetida do mesmo arquivo CSV/PDF da Uber ou 99 é detectada e bloqueada pelo sistema.
* **CA-FIN-02:** Se um motorista utiliza dois veículos na mesma semana, as receitas são atribuídas corretamente a cada veículo conforme o horário/turno registrado em `VehicleAssignment`.
* **CA-FIN-03:** O relatório de rentabilidade do proprietário exibe apenas receitas e despesas vinculadas aos seus veículos e dentro do escopo autorizado.

---

## 6. Módulo MC-DOC: Documentação, Multas e IPVA

### 6.1. Objetivo e Escopo
Gerenciar prazos de obrigações legais, seguros, habilitações e infrações de trânsito, automatizando a identificação do condutor infrator e a atribuição financeira.

### 6.2. Requisitos Funcionais (MC-DOC)
* `RF-DOC-01`: Cadastrar obrigações do veículo (IPVA, Licenciamento/CRLV, Seguro, Proteção Veicular, Vistoria GNV) com vencimentos e parcelas.
* `RF-DOC-02`: Controlar vencimento e categoria da CNH dos motoristas cadastrados.
* `RF-DOC-03`: Enviar alertas preventivos escalonados antes do vencimento de documentos, tributos e CNH.
* `RF-DOC-04`: Registrar multas de trânsito com auto de infração, data/hora exata, código, pontos, valor integral, valor com desconto e data limite para indicação de condutor.
* `RF-DOC-05`: Cruzar automaticamente data/hora da infração com `VehicleAssignment` para identificar o motorista ativo no momento da ocorrência.
* `RF-DOC-06`: Controlar fluxo de indicação de real infrator (Pendente, Indicado, Confirmado, Recurso) e status financeiro.
* `RF-DOC-07`: Gerar lançamento financeiro da obrigação ou multa separando Pagador e Responsável Econômico.

### 6.3. Entidades de Dados Previstas (MC-DOC)
* `VehicleObligation` (IPVA, licenciamento, seguros e vistorias)
* `ObligationInstallment` (parcelas individuais com data de vencimento e comprovante de quitação)
* `DriverLicense` (dados e validade da CNH do motorista)
* `TrafficTicket` (registro completo da infração de trânsito e vínculo com o motorista identificado)

### 6.4. Critérios de Aceitação (MC-DOC)
* **CA-DOC-01:** Ao cadastrar uma multa informando placa, data e hora, o sistema identifica e sugere automaticamente o motorista que estava alocado ao veículo naquele exato instante.
* **CA-DOC-02:** O sistema dispara alerta ao gestor quando um motorista vinculado possui CNH vencida ou a vencer em menos de 30 dias.
* **CA-DOC-03:** Uma multa paga pelo proprietário mas atribuída ao motorista aparece como custo econômico do motorista e pendência de reembolso ao proprietário.

---

## 7. Módulo MC-CHK: Checklist e Inspeção Diária

### 7.1. Objetivo e Escopo
Padronizar vistorias diárias e de entrega/devolução de veículos, registrar evidências fotográficas de avarias e acionar manutenções corretivas preventivamente.

### 7.2. Requisitos Funcionais (MC-CHK)
* `RF-CHK-01`: Criar templates de checklist personalizáveis (inspeção diária, entrega, devolução) com itens obrigatórios e regras de foto.
* `RF-CHK-02`: Executar checklist via dispositivo móvel registrando veículo, motorista, data/hora, odômetro e nível de combustível.
* `RF-CHK-03`: Exigir anexo fotográfico obrigatório em itens marcados como Não Conforme ou em vistorias de troca de posse.
* `RF-CHK-04`: Atualizar o odômetro oficial do veículo (`OdometerReading`) após validação do checklist.
* `RF-CHK-05`: Gerar automaticamente uma solicitação de manutenção (`MaintenanceRequest`) sempre que um item for reprovado.
* `RF-CHK-06`: Sinalizar alerta de bloqueio operacional quando um item marcado como Crítico de Segurança (ex.: freios, pneus, iluminação) for reprovado.
* `RF-CHK-07`: Manter histórico comparativo de vistorias de entrega e devolução por período de alocação.

### 7.3. Entidades de Dados Previstas (MC-CHK)
* `ChecklistTemplate` (estrutura configurável do formulário de inspeção)
* `ChecklistTemplateItem` (perguntas/itens, criticidade e obrigatoriedade de foto)
* `ChecklistExecution` (vistoria realizada com assinatura/aceite digital e odômetro)
* `ChecklistResponseItem` (resposta individual de cada item com fotos de evidência)

### 7.4. Critérios de Aceitação (MC-CHK)
* **CA-CHK-01:** O sistema impede a finalização do checklist se um item marcado como Não Conforme exigir foto obrigatória e nenhuma imagem tiver sido anexada.
* **CA-CHK-02:** A reprovação de um item crítico gera imediatamente um registro em `MaintenanceRequest` e exibe status de atenção no painel do gestor de frota.
* **CA-CHK-03:** O odômetro informado no checklist respeita a mesma validação cronológica do módulo de abastecimento (`RF-ABS-02`).
