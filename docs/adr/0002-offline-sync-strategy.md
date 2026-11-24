# ADR 0002: Estratégia de Sincronização Offline-First (PWA)

**Status:** Aceito  
**Data:** 2024-01-15  
**Decisores:** Tech Lead, Arquiteto de Software, PO  

## Contexto
O ManutCar deve funcionar **offline-first** para motoristas em campo (checklists, abastecimentos, odômetro) conforme `RN-CHK-02` e `RF-ABS-01`. A arquitetura PWA (Next.js + Service Worker + IndexedDB) foi escolhida no `ADR 0001` para o Incremento 1.

## Decisão

### Armazenamento Local (IndexedDB via Dexie.js)
- **Banco:** `ManutCarOfflineDB` (Dexie.js v4)
- **Tabelas:**
  - `pendingChecklists` (ChecklistExecution + ChecklistResponseItem + fotos Base64)
  - `pendingFuelLogs` (FuelLog + comprovante Base64)
  - `pendingOdometerReadings` (OdometerReading)
  - `syncQueue` (Fila de operações: `{ id, type, payload, timestamp, retries }`)
  - `cachedTemplates` (ChecklistTemplate + Items para renderização offline)
  - `cachedVehicles` (Vehicle resumido para seleção offline)
  - `cachedSettings` (OrganizationSettings para validações offline)

### Service Worker (Workbox via next-pwa)
- **Estratégia de Cache:**
  - `Static Assets` (JS, CSS, Fonts): `CacheFirst` (imutáveis com hash)
  - `API GET` (Templates, Veículos, Configurações): `StaleWhileRevalidate` (max 24h)
  - `API POST/PUT` (Mutations): **Nunca cacheadas** (vão para `syncQueue`)
  - `Navigation` (HTML): `NetworkFirst` (fallback para `offline.html`)

### Fluxo de Sincronização
1. **Online:** Operações vão direto para API → Atualizam cache local → Limpam `syncQueue`
2. **Offline:** Operações salvam no IndexedDB → Adicionam à `syncQueue` → UI mostra badge "Pendente"
3. **Reconexão:** Event `online` + `navigator.onLine` → Processa `syncQueue` sequencialmente
4. **Conflitos:** **Last Write Wins (LWW)** baseado em `updated_at` do servidor
   - **Exceção Crítica:** Odômetro (`RN-ABS-01`) → **Server Wins** (rejeita se regressão)
   - **Fotos:** Upload separado para R2 (Presigned URL) após sync do registro pai

### Resolução de Conflitos Específicos
| Entidade | Estratégia | Justificativa |
|----------|------------|---------------|
| `ChecklistExecution` | LWW (timestamp) | Checklists são instantâneos no tempo |
| `FuelLog` | LWW (timestamp) | Abastecimentos têm data/hora fixa |
| `OdometerReading` | **Server Wins** | `RN-ABS-01`: Monotonicidade estrita é invariante de negócio |
| `VehicleAssignment` | Server Wins | Apenas gestores criam (sempre online) |

### Background Sync
- **Periodic Background Sync API** (quando disponível) para sync automático
- **Fallback:** Sync ao abrir app (`focus` event) + a cada 5 min se online
- **Retry:** Exponencial (1min, 2min, 5min, 10min, max 30min) com `retries` counter
- **Dead Letter:** Após 10 falhas → Move para `failedSync` + Notificação ao usuário

### Validações Offline (Client-Side)
- Odômetro: `km >= lastKnownOdometer` (cache local) + Alerta salto > 1500km
- Checklist: Foto obrigatória em `require_photo_on_fail` (valida Base64 size > 0)
- Combustível: `volume > 0`, `price > 0`, `odometer >= lastKnown`
- Templates: Carregados do cache `cachedTemplates` (atualizados em background)

### Limitações Conhecidas (Incremento 1)
- **Fotos grandes:** Base64 no IndexedDB consome quota (limite ~50-100MB). Compressão client-side (canvas) para max 1.5MB/foto.
- **Sync de arquivos (R2):** Requer Presigned URL do backend → Fluxo: Sync registro → Backend retorna Presigned URL → Upload direto R2 → Confirmação.
- **Concorrência:** Dois dispositivos offline editando mesmo veículo → LWW resolve no servidor.
- **Notificações Push Offline:** FCM não entrega se app fechado e offline. Service Worker mostra notificação local.

## Consequências

### Positivas
- Motorista nunca bloqueado: Checklist/Abastecimento funcionam 100% offline
- Dados nunca perdidos: Persistência local + fila de sync resiliente
- Arquitetura preparada para App Nativo (Inc 3): Mesma lógica de sync/IndexedDB
- Conformidade `RN-CHK-02`, `RF-ABS-01`, `RN-ABS-01`

### Negativas/Riscos
- Complexidade de sync: Requer testes extensivos de cenários offline/online
- Conflitos de odômetro: Server Wins pode frustrar usuário (digitação errada offline)
- Tamanho do IndexedDB: Monitorar quota, implementar limpeza de `synced` items > 30 dias
- Background Sync API não suportada em iOS Safari (PWA limitations) → Fallback manual

## Alternativas Consideradas
| Opção | Veredito |
|-------|----------|
| **RxDB / WatermelonDB** | Rejeitado: Overhead de dependência, Dexie.js é mais leve e simples |
| **Service Worker apenas (sem IndexedDB)** | Rejeitado: Não suporta armazenamento estruturado + query offline |
| **Native App (React Native) no Inc 1** | Rejeitado: `DEC-021` adia para Inc 3. PWA atende MVP. |
| **Optimistic UI sem persistência local** | Rejeitado: Perda de dados se fechar aba/perder conexão antes do POST |

## Próximos Passos
1. Implementar `Dexie.js` schema em `packages/ui/src/lib/db/offline-db.ts`
2. Criar `SyncEngine` class em `packages/ui/src/lib/sync/sync-engine.ts`
3. Configurar `next-pwa` com `workbox` strategies customizadas
4. Implementar UI de status: "Online", "Offline", "Sincronizando...", "X pendentes"
5. Testes E2E: Cypress/Playwright simulando offline (Chrome DevTools Network tab)
