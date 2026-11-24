# Especificação Funcional Consolidada — Gestão de Frota (MC-FLT-001)

## Visão Geral
O ManutCar adota modelo **multiorganização, multiusuário e multiproprietário**, permitindo que uma organização administre veículos próprios e de terceiros, mantendo identificação de cada proprietário e direitos de acesso. Atende quatro cenários: motorista autônomo, empresa com frota própria, empresa que administra veículos de motoristas, e gestor independente.

---

## 1. Estrutura Organizacional
Quatro entidades fundamentais independentes:
- **Usuário**: pessoa que acessa o sistema
- **Organização**: empresa/estrutura de gestão (administração operacional)
- **Proprietário**: titular do veículo (pessoa física/jurídica)
- **Veículo**: bem com prontuário e histórico próprio

**Princípio**: propriedade jurídica, responsabilidade operacional e responsabilidade financeira podem pertencer a pessoas diferentes.

---

## 2. Regras de Propriedade e Administração
| Situação | Regra |
|----------|-------|
| Veículo próprio da empresa | Empresa = proprietária |
| Veículo do motorista | Motorista = proprietário |
| Veículo alugado | Proprietário identificado + contrato registrado |
| Veículo de terceiro administrado | Terceiro permanece proprietário; organização recebe autorização |
| Veículo compartilhado | Múltiplos motoristas com períodos registrados |

---

## 3. Autorização de Administração
**Fluxo obrigatório** para veículos de terceiros:
1. Organização convida proprietário
2. Proprietário consulta solicitação e permissões
3. Proprietário autoriza/rejeita
4. Autorização define escopo: manutenção, utilização, financeiro, relatórios, gestão operacional
5. Proprietário pode revogar a qualquer momento

**Regra**: acesso não concedido apenas por conhecimento de placa/identificador.

---

## 4. Papéis e Permissões
| Papel | Responsabilidade |
|-------|------------------|
| Proprietário do veículo | Titularidade e autorizações |
| Administrador da organização | Organização, usuários, permissões |
| Gestor de frota | Veículos, motoristas, operação |
| Financeiro | Receitas, despesas, rentabilidade |
| Motorista | Própria utilização e informações permitidas |
| Manutenção | Serviços, inspeções, necessidades |

- Usuário pode acumular papéis
- **Segurança**: papel de gestor **não** concede acesso a contas Uber/99 (autorização específica e independente)

---

## 5. Veículos Compartilhados e Transferência
- **Histórico acompanha o veículo** (não motorista nem organização)
- Manutenção permanece no prontuário após mudança de proprietário
- Troca de motorista não apaga viagens/registros
- Saída da frota encerra vínculo administrativo, preserva histórico
- Transferência registra data efetiva
- Novo proprietário **não** recebe dados financeiros/pessoais do anterior
- Encerramento de contrato revoga acessos

---

## 6. Gestão Financeira por Responsabilidade
**Conceito-chave**: separar **quem pagou** (pagador) de **quem suportou o custo** (responsável econômico).

**Exemplo**: Organização paga R$ 800 manutenção, mas contrato define Proprietário como responsável pelo custo.

**Cada lançamento registra**:
- Veículo, categoria, valor, data
- Responsável pelo pagamento
- Responsável econômico pelo custo
- Quem lançou
- Classificação: profissional, particular ou compartilhado

**Relatórios** por perspectiva (operação, veículo, proprietário) sem dupla contagem.

---

## 7. Relatórios Gerenciais (4 Níveis)
| Nível | Foco |
|-------|------|
| 1 — Organização | Receita/despesa consolidada, resultado operacional/econômico, km frota, veículos ativos/inativos |
| 2 — Proprietário | Veículos administrados, custos atribuídos, receitas autorizadas, histórico manutenção |
| 3 — Veículo | Utilização, manutenções, receitas/despesas, rentabilidade, situação operacional |
| 4 — Motorista | Veículos utilizados, períodos, km profissional, receitas/despesas sob responsabilidade |

**Consolidação** considera período e responsabilidade econômica, não soma simples.

---

## 8. Requisitos Funcionais (RF-FLT-01 a 18)
Principais:
- RF-FLT-01/02: Criar organizações, usuários em múltiplas orgs
- RF-FLT-03/04: Cadastrar proprietários, vincular veículos
- RF-FLT-05/06/07: Administrar veículos terceiros, solicitar/registrar/revogar autorização
- RF-FLT-08: Atribuir papéis/permissões específicas
- RF-FLT-09/10: Múltiplos motoristas/períodos, uso compartilhado
- RF-FLT-11/17: Preservar histórico, encerrar vínculos sem apagar
- RF-FLT-12/13: Responsáveis financeiros, separar pagador/responsável econômico
- RF-FLT-14: Relatórios por org/proprietário/veículo/motorista
- RF-FLT-15: Isolamento entre organizações
- RF-FLT-16: Trilha de auditoria
- RF-FLT-18: Autorização individual para integrações externas

---

## 9. Entidades de Dados Previstas
- **Organization** / **OrganizationMember**
- **VehicleOwner** / **VehicleOwnershipHistory**
- **VehicleManagementAgreement** (autorização gestão)
- **VehicleAssignment** (veículo-motorista)
- **VehicleFinancialResponsibility**
- **VehicleAccessPermission**
- **OrganizationInvitation**
- **AuditLog**
- **DataConsent** (LGPD/integrações)

Integração com: veículos, manutenções, receitas, despesas, quilometragem, Uber/99.

---

## 10. Critérios de Aceitação
Funcional quando possível:
1. Criar organização
2. Cadastrar veículos próprios/terceiros
3. Vincular diferentes proprietários à mesma org
4. Solicitar autorização ao proprietário
5. Vincular motoristas a veículos
6. Alterar motoristas sem perder histórico
7. Registrar diferentes responsáveis (pagamento/custo)
8. Consultar relatórios por permissão
9. Encerrar vínculos preservando prontuário
10. Impedir acesso não autorizado entre organizações

---

## 11. Estratégia de Implementação (Duas Etapas)

### Etapa 1 — Base da Gestão de Frota (Prioridade Estrutural)
- Organizações e usuários
- Cadastro de proprietários
- Veículos próprios e de terceiros
- Autorizações e permissões
- Vínculos com motoristas
- Histórico e auditoria

### Etapa 2 — Gestão Avançada
- Consolidação financeira de frotas
- Rateio entre responsáveis
- Comparação de rentabilidade
- Relatórios gerenciais avançados
- Integrações Uber/99

**Decisão arquitetural**: nascer preparado para múltiplas organizações/proprietários, mesmo com funcionalidades avançadas graduais. Evita reconstrução do modelo de dados na evolução de produto individual → plataforma de frotas.

---

## Conclusão
O ManutCar evolui para **plataforma de gestão veicular** com três dimensões:
1. **Prontuário veicular** (manutenção, histórico, procedência)
2. **Gestão de rentabilidade** (receitas, despesas, km, fluxo de caixa, resultado econômico)
3. **Gestão de frotas** (múltiplas orgs, proprietários, motoristas, permissões, responsabilidades)

**Risco**: complexidade. **Mitigação**: construção modular, arquitetura preparada para expansão, visão de produto mantida.
