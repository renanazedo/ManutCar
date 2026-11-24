import os, sys

# Adiciona packages/db/src ao path para importar manutcar_db diretamente
sys.path.insert(0, os.path.abspath("packages/db/src"))

print("=" * 60)
print("AUDITORIA BLOCO 2 - MODELOS SQLALCHEMY 2.0 MANUTCAR")
print("=" * 60)

errors = []

# 1. Testar importação de base, session, enums e models
try:
    import manutcar_db.base as base_mod
    import manutcar_db.enums as enums_mod
    import manutcar_db.session as session_mod
    import manutcar_db.models as models_mod
    print("[OK] Imports de base, enums, session e models executados sem erros.")
except Exception as e:
    print(f"[FALHA] Erro crítico de importação: {e}")
    sys.exit(1)

# 2. Listar tabelas registradas no Base.metadata
tables = sorted(base_mod.Base.metadata.tables.keys())
print(f"\n[INFO] Total de tabelas mapeadas no Metadata: {len(tables)}")
for t in tables:
    print(f"  - {t}")

# 3. Validar tabelas obrigatórias esperadas
expected_tables = [
    "users", "organizations", "organization_members", "organization_settings",
    "organization_invitations", "data_consents", "vehicle_owners", "vehicles",
    "vehicle_ownership_history", "vehicle_management_agreements",
    "vehicle_access_permissions", "vehicle_assignments",
    "vehicle_financial_responsibilities", "odometer_readings", "fuel_logs",
    "consumption_anomaly_alerts", "checklist_templates", "checklist_template_items",
    "checklist_executions", "checklist_response_items", "service_providers",
    "maintenance_plans", "vehicle_maintenance_schedules", "maintenance_requests",
    "work_orders", "work_order_items", "driver_licenses", "vehicle_obligations",
    "obligation_installments", "traffic_tickets", "platform_import_batches",
    "revenue_entries", "financial_ledger_entries", "settlement_statements",
    "audit_logs", "processed_webhook_events"
]

missing_tables = [t for t in expected_tables if t not in tables]
if missing_tables:
    errors.append(f"Tabelas ausentes ({len(missing_tables)}): {', '.join(missing_tables)}")

# 4. Compilar DDL completo para o dialeto PostgreSQL (valida FKs, tipos e constraints)
try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable, CreateIndex

    dialect = postgresql.dialect()
    for table in base_mod.Base.metadata.sorted_tables:
        _ = str(CreateTable(table).compile(dialect=dialect))
        for idx in table.indexes:
            _ = str(CreateIndex(idx).compile(dialect=dialect))
    print("\n[OK] Compilação DDL PostgreSQL (tabelas, FKs, tipos e índices) validada com sucesso.")
except Exception as e:
    errors.append(f"Erro na compilação DDL / Chaves Estrangeiras: {e}")

print("\n" + "=" * 60)
print("RELATÓRIO FINAL BLOCO 2")
print("=" * 60)
if errors:
    for err in errors:
        print(f"[FALHA] {err}")
    print("\nAUDITORIA_BLOCO2_REPROVADA")
    sys.exit(1)
else:
    print("Todas as 36 tabelas, chaves estrangeiras e tipos PostgreSQL estão íntegros.")
    print("\nAUDITORIA_BLOCO2_APROVADA")
    sys.exit(0)
