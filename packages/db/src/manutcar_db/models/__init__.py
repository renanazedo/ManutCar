"""
ManutCar Database Models Package

This package contains all SQLAlchemy models organized by domain:
- identity: Users, Organizations, Memberships, Invitations, Consents
- fleet: Vehicles, Owners, Agreements, Assignments, Financial Responsibilities
- operations: Odometer, Fuel, Checklists, Anomalies
- maintenance_docs: Work Orders, Documents, Parts, Services
- finance_audit: Revenue, Ledger, Settlements, Audit Logs, Webhooks
"""

# Identity models
from manutcar_db.models.identity import (
    DataConsent,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationSettings,
    User,
)

# Fleet models
from manutcar_db.models.fleet import (
    Vehicle,
    VehicleAccessPermission,
    VehicleAssignment,
    VehicleFinancialResponsibility,
    VehicleManagementAgreement,
    VehicleOwner,
    VehicleOwnershipHistory,
)

# Operations models
from manutcar_db.models.operations import (
    ChecklistExecution,
    ChecklistResponseItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
    ConsumptionAnomalyAlert,
    FuelLog,
    OdometerReading,
)

# Maintenance docs models
from manutcar_db.models.maintenance_docs import (
    MaintenanceDocument,
    MaintenancePart,
    MaintenanceService,
    WorkOrder,
)

# Finance & Audit models
from manutcar_db.models.finance_audit import (
    AuditLog,
    FinancialLedgerEntry,
    PlatformImportBatch,
    ProcessedWebhookEvent,
    RevenueEntry,
    SettlementStatement,
)

__all__ = [
    # Identity
    "User",
    "Organization",
    "OrganizationMember",
    "OrganizationSettings",
    "OrganizationInvitation",
    "DataConsent",
    # Fleet
    "VehicleOwner",
    "Vehicle",
    "VehicleOwnershipHistory",
    "VehicleManagementAgreement",
    "VehicleAccessPermission",
    "VehicleAssignment",
    "VehicleFinancialResponsibility",
    # Operations
    "OdometerReading",
    "FuelLog",
    "ConsumptionAnomalyAlert",
    "ChecklistTemplate",
    "ChecklistTemplateItem",
    "ChecklistExecution",
    "ChecklistResponseItem",
    # Maintenance Docs
    "WorkOrder",
    "MaintenanceDocument",
    "MaintenancePart",
    "MaintenanceService",
    # Finance & Audit
    "PlatformImportBatch",
    "RevenueEntry",
    "FinancialLedgerEntry",
    "SettlementStatement",
    "AuditLog",
    "ProcessedWebhookEvent",
]
