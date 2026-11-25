import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EntityRoleType = Literal["ORG", "OWNER", "DRIVER"]


class VehicleAssignmentCreate(BaseModel):
    vehicle_id: uuid.UUID
    driver_user_id: uuid.UUID
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    shift_label: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_interval(self) -> "VehicleAssignmentCreate":
        if self.end_datetime is not None and self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime deve ser posterior a start_datetime.")
        return self


class VehicleAssignmentUpdate(BaseModel):
    end_datetime: Optional[datetime] = None
    shift_label: Optional[str] = Field(default=None, max_length=50)


class VehicleAssignmentClose(BaseModel):
    end_datetime: Optional[datetime] = None


class VehicleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    organization_id: uuid.UUID
    driver_user_id: uuid.UUID
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    shift_label: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VehicleFinancialResponsibilityUpsert(BaseModel):
    vehicle_id: uuid.UUID
    expense_category: str = Field(..., min_length=2, max_length=100)
    default_payer_type: EntityRoleType
    default_economic_owner_type: EntityRoleType

    @field_validator("expense_category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        return v.strip().upper()


class VehicleFinancialResponsibilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    organization_id: uuid.UUID
    expense_category: str
    default_payer_type: str
    default_economic_owner_type: str
    created_at: datetime
    updated_at: datetime
