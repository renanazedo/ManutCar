from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    CORRECTIVE = "CORRECTIVE"
    PREDICTIVE = "PREDICTIVE"


class WorkOrderStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PreventiveTrafficLight(str, Enum):
    OK = "OK"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"


# ---------------------------------------------------------------------------
# ServiceProvider (Oficinas / Fornecedores)
# ---------------------------------------------------------------------------
class ServiceProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    document_number: Optional[str] = Field(default=None, max_length=30)
    phone: Optional[str] = Field(default=None, max_length=30)


class ServiceProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    document_number: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# MaintenancePlan & VehicleMaintenanceSchedule (Preventiva)
# ---------------------------------------------------------------------------
class MaintenancePlanCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    interval_km: Optional[int] = Field(default=None, gt=0)
    interval_days: Optional[int] = Field(default=None, gt=0)


class MaintenancePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    interval_km: Optional[int] = None
    interval_days: Optional[int] = None
    created_at: datetime


class VehicleScheduleUpsert(BaseModel):
    vehicle_id: UUID
    plan_id: UUID
    last_executed_km: Optional[int] = Field(default=None, ge=0)
    last_executed_at: Optional[datetime] = None


class VehicleScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    plan_id: UUID
    last_executed_km: Optional[int] = None
    last_executed_at: Optional[datetime] = None
    next_due_km: Optional[int] = None
    next_due_date: Optional[datetime] = None
    traffic_light: PreventiveTrafficLight = PreventiveTrafficLight.OK


# ---------------------------------------------------------------------------
# MaintenanceRequest (Solicitações de Manutenção)
# ---------------------------------------------------------------------------
class MaintenanceRequestCreate(BaseModel):
    vehicle_id: UUID
    description: str = Field(..., min_length=3, max_length=2000)


class MaintenanceRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    vehicle_id: UUID
    requested_by_user_id: UUID
    description: str
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# WorkOrder & WorkOrderItem (Ordens de Serviço)
# ---------------------------------------------------------------------------
class WorkOrderItemCreate(BaseModel):
    item_type: str = Field(default="PART", pattern="^(PART|LABOR|SERVICE|OTHER)$")
    description: str = Field(..., min_length=2, max_length=500)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    warranty_days: Optional[int] = Field(default=None, ge=0)
    warranty_km: Optional[int] = Field(default=None, ge=0)
    force_warranty_override: bool = Field(
        default=False,
        description="Confirma prosseguimento mesmo havendo item em garantia ativa (RN-MNT-07).",
    )


class WorkOrderItemRead(BaseModel):
    item_type: str = "PART"
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    warranty_days: Optional[int] = None
    warranty_km: Optional[int] = None


class WorkOrderCreate(BaseModel):
    vehicle_id: UUID
    service_provider_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    schedule_id: Optional[UUID] = None
    maintenance_type: MaintenanceType
    odometer_km: int = Field(..., ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    set_vehicle_in_maintenance: bool = Field(default=False)


class WorkOrderStatusTransition(BaseModel):
    status: WorkOrderStatus
    odometer_km: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    has_attachments: bool = Field(
        default=False,
        description="Indica se há nota fiscal/evidência anexada (obrigatório acima do limite RN-MNT-08).",
    )


class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    vehicle_id: UUID
    service_provider_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    maintenance_type: MaintenanceType
    status: WorkOrderStatus
    odometer_km: int
    total_amount: Decimal
    opened_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    items: list[WorkOrderItemRead] = Field(default_factory=list)
