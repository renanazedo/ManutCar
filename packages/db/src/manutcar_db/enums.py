import enum


class OrgRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    FLEET_MANAGER = "FLEET_MANAGER"
    FINANCIAL = "FINANCIAL"
    DRIVER = "DRIVER"
    MAINTENANCE = "MAINTENANCE"


class AgreementStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ConsentStatus(str, enum.Enum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"


class ExpenseNature(str, enum.Enum):
    PROFESSIONAL = "PROFESSIONAL"
    PERSONAL = "PERSONAL"
    SHARED = "SHARED"


class SettlementStatus(str, enum.Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING_REIMBURSEMENT = "PENDING_REIMBURSEMENT"
    SETTLED = "SETTLED"


class LedgerEntryType(str, enum.Enum):
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"
    SETTLEMENT_TRANSFER = "SETTLEMENT_TRANSFER"


class MaintenanceType(str, enum.Enum):
    PREVENTIVE = "PREVENTIVE"
    CORRECTIVE = "CORRECTIVE"
    PREDICTIVE = "PREDICTIVE"


class WorkOrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FuelType(str, enum.Enum):
    GASOLINE = "GASOLINE"
    ETHANOL = "ETHANOL"
    DIESEL = "DIESEL"
    CNG = "CNG"
    ELECTRIC = "ELECTRIC"


class ChecklistType(str, enum.Enum):
    DAILY = "DAILY"
    HANDOVER = "HANDOVER"
    RETURN = "RETURN"


class ChecklistItemStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class VehicleOperationalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    RESTRICTED_SAFETY_ALERT = "RESTRICTED_SAFETY_ALERT"
    INACTIVE = "INACTIVE"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
    REVOKE = "REVOKE"
    ANONYMIZE = "ANONYMIZE"
