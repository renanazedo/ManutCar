# VISÃO DO PRODUTO — ManutCar

**Código do Documento:** MC-DOC-VIS-001  
**Status:** Em Revisão  
**Versão:** 1.0  

---

## 1. Propósito do Produto
O **ManutCar** é uma plataforma de gestão veicular, operacional e financeira projetada para centralizar o ciclo de vida completo de veículos utilizados em operações profissionais, comerciais ou compartilhadas. 

Seu objetivo central é fornecer controle real de custos, manutenção, documentação e rentabilidade, preservando a titularidade jurídica dos bens, o histórico contínuo de cada veículo e a correta atribuição de responsabilidades financeiras entre proprietários, gestores e motoristas.

---

## 2. Problema que Resolve
Na operação de veículos — seja por motoristas de aplicativo, pequenas frotas ou gestores de ativos de terceiros — os dados costumam ficar fragmentados e distorcidos:
* **Falta de visibilidade financeira real:** Mistura entre fluxo de caixa (quem pagou a conta) e competência econômica (quem deve arcar com o custo).
* **Perda de histórico do ativo:** Quando um veículo muda de motorista, de empresa gestora ou de proprietário, o histórico de manutenção e utilização se perde.
* **Gestão reativa de manutenção e obrigações:** Falta de controle preventivo por quilometragem/tempo, vencimento de documentos, seguros e multas.
* **Complexidade na relação entre partes:** Dificuldade em administrar veículos de terceiros sem expor dados pessoais/financeiros sensíveis ou depender de controles informais em planilhas.

---

## 3. Público-Alvo e Perfis de Uso (Modelo Híbrido)
O ManutCar nasce estruturado em arquitetura **multiorganização, multiusuário e multiproprietário**, atendendo simultaneamente a quatro perfis principais:

1. **Motorista Autônomo (B2C):** Profissional (ex.: motorista de aplicativo Uber/99, entregador ou representante) que possui ou aluga seu próprio veículo e precisa controlar receitas, abastecimentos, manutenções preventivas e lucro líquido real por km rodado.
2. **Empresa com Frota Própria (B2B):** Empresa que possui veículos próprios e precisa gerenciar motoristas, checklists diários, manutenção, multas, documentação e custos operacionais.
3. **Empresa que Opera Frota de Motoristas (B2B2C):** Organização que administra ou coordena operações utilizando veículos pertencentes aos próprios motoristas, exigindo regras claras de autorização de acesso e divisão de custos.
4. **Gestor Independente de Ativos (B2B / Investidores):** Gestor ou administradora que opera veículos pertencentes a diversos proprietários (pessoas físicas ou jurídicas), exigindo prestação de contas transparente e segregação de resultados por proprietário e por veículo.

---

## 4. Proposta de Valor
* **Prontuário Único e Perpétuo do Veículo:** O histórico técnico e operacional pertence ao veículo, acompanhando-o independentemente de trocas de motorista, organização gestora ou transferência de propriedade.
* **Separação Contábil Inteligente:** Distinção nativa entre **Propriedade Jurídica**, **Responsabilidade Operacional**, **Pagador** e **Responsável Econômico**, evitando dupla contagem e garantindo apuração exata de rentabilidade.
* **Governança e Privacidade por Autorização:** Nenhum dado de veículo ou conta pessoal (como integrações Uber/99) é acessado por terceiros sem consentimento explícito, granular e revogável pelo titular.
* **Visão 360º da Operação:** Integração nativa entre operação diária (checklist e odômetro), custos variáveis (abastecimento e manutenção), obrigações legais (documentos e multas) e receitas.

---

## 5. Escopo Funcional Macro (Módulos do Ecossistema)
O sistema será composto por seis módulos integrados:

| Código | Módulo | Responsabilidade Principal |
| :--- | :--- | :--- |
| **MC-FLT** | **Gestão de Frota e Proprietários** | Estrutura multiorganização, vínculos de propriedade, autorizações de gestão, papéis/permissões e histórico de posse/uso. |
| **MC-MNT** | **Manutenção Preventiva e Corretiva** | Planos de manutenção por km/tempo, ordens de serviço, histórico técnico do veículo, peças e alertas de vencimento. |
| **MC-ABS** | **Abastecimento e Consumo** | Registro de abastecimentos, controle de odômetro, cálculo de média de consumo (km/l), custo por km e identificação de desvios. |
| **MC-FIN** | **Integração Financeira (Uber e 99)** | Importação/sincronização autorizada de ganhos e repasses das plataformas, conciliação de receitas e apuração de resultado líquido. |
| **MC-DOC** | **Documentação, Multas e IPVA** | Controle de vencimentos (CRLV, IPVA, licenciamento, seguro, CNH), registro de infrações, indicação de condutor e rateio de multas. |
| **MC-CHK** | **Checklist e Inspeção Diária** | Rotinas de vistoria de entrega/devolução e inspeção diária pelo motorista, registro de avarias e bloqueio preventivo por segurança. |

---

## 6. Princípios Arquiteturais e de Negócio (Inegociáveis)
1. **Multitenancy desde a origem:** Toda estrutura de dados deve suportar múltiplas organizações, múltiplos proprietários e múltiplos motoristas sem necessidade de reescrita futura.
2. **Privacidade by Design:** O papel de gestor nunca concede acesso automático a dados pessoais ou contas financeiras externas (Uber/99) de motoristas ou antigos proprietários.
3. **Auditabilidade:** Toda alteração crítica de vínculo, autorização, responsabilidade financeira ou registro operacional deve gerar trilha de auditoria.
4. **Visão Multi-Perspectiva:** Os relatórios financeiros devem consolidar dados sob a ótica da **Organização**, do **Proprietário**, do **Veículo** e do **Motorista** sem distorções.

---

## 7. Critérios de Sucesso do Produto
* Um motorista autônomo consegue operar o sistema de forma simples, sem burocracia corporativa excessiva.
* Um gestor de frota consegue administrar veículos próprios e de terceiros no mesmo painel, com prestação de contas clara para cada proprietário.
* A troca de motorista ou de propriedade de um veículo preserva 100% do histórico técnico sem vazar dados financeiros privados anteriores.
