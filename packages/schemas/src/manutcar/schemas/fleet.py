import re
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from manutcar_db.enums import AgreementStatus, FuelType, VehicleOperationalStatus

_PLATE_RE = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
_DIGITS_RE = re.compile(r"\D")


def _clean_digits(v: str) -> str:
    return _DIGITS_RE.sub("", v)


class VehicleOwnerCreate(BaseModel):
    owner_type: Literal["PF", "PJ"]
    legal_name: str = Field(..., min_length=2, max_length=255)
    document_number: str = Field(..., min_length=11, max_length=18)
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None

    @field_validator("legal_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        c = v.strip()
        if len(c) < 2:
            raise ValueError("Nome legal deve ter pelo menos 2 caracteres.")
        return c

    @field_validator("document_number")
    @classmethod
    def check_doc(cls, v: str) -> str:
        d = _clean_digits(v)
        if len(d) not in (11, 14):
            raise ValueError("Documento deve ter 11 (CPF) ou 14 (CNPJ) d?gitos.")
        return d

    @model_validator(mode="after")
    def check_type_doc(self) -> "VehicleOwnerCreate":
        if self.owner_type == "PF" and len(self.document_number) != 11:
            raise ValueError("PF exige CPF de 11 d?gitos.")
        if self.owner_type == "PJ" and len(self.document_number) != 14:
            raise ValueError("PJ exige CNPJ de 14 d?gitos.")
        return self


class VehicleOwnerUpdate(BaseModel):
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    user_id: Optional[uuid.UUID] = None


class VehicleOwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    owner_type: str
    legal_name: str
    document_number: str
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    plate: str = Field(..., min_length=7, max_length=10)
    renavam: Optional[str] = Field(default=None, max_length=11)
    chassis: Optional[str] = Field(default=None, max_length=17)
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year_manufacture: int = Field(..., ge=1900, le=2100)
    year_model: int = Field(..., ge=1900, le=2100)
    fuel_type: FuelType
    current_odometer: int = Field(default=0, ge=0)
    operational_status: VehicleOperationalStatus = VehicleOperationalStatus.ACTIVE
    current_owner_id: uuid.UUID
    agreement_start_date: Optional[datetime] = None

    @field_validator("plate")
    @classmethod
    def check_plate(cls, v: str) -> str:
        p = v.strip().upper().replace("-", "")
        if not _PLATE_RE.match(p):
            raise ValueError("Placa inv?lida (use AAA0000 ou AAA0A00).")
        return p

    @field_validator("renavam")
    @classmethod
    def check_renavam(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        d = _clean_digits(v)
        if len(d) not in (9, 11):
            raise ValueError("RENAVAM deve ter 9 ou 11 d?gitos.")
        return d.zfill(11)

    @field_validator("chassis")
    @classmethod
    def check_chassis(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        c = v.strip().upper()
        if len(c) != 17:
            raise ValueError("Chassi deve ter 17 caracteres.")
        return c

    @model_validator(mode="after")
    def check_years(self) -> "VehicleCreate":
        if self.year_model < self.year_manufacture:
            raise ValueError("Ano do modelo n?o pode ser menor que o de fabrica??o.")
        return self


class VehicleUpdate(BaseModel):
    brand: Optional[str] = Field(default=None, min_length=1, max_length=100)
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    fuel_type: Optional[FuelType] = None
    operational_status: Optional[VehicleOperationalStatus] = None
    renavam: Optional[str] = Field(default=None, max_length=11)
    chassis: Optional[str] = Field(default=None, max_length=17)
    reason: Optional[str] = Field(default=None, max_length=500)


class VehicleOdometerUpdate(BaseModel):
    new_odometer: int = Field(..., ge=0)
    reason: Optional[str] = Field(default=None, max_length=500)


class VehicleTransferOwnership(BaseModel):
    new_owner_id: uuid.UUID
    transfer_date: Optional[datetime] = None
    reason: Optional[str] = Field(default=None, max_length=500)


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    plate: str
    renavam: Optional[str]
    chassis: Optional[str]
    brand: str
    model: str
    year_manufacture: int
    year_model: int
    fuel_type: FuelType
    current_odometer: int
    operational_status: VehicleOperationalStatus
    current_owner_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class VehicleOwnershipHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    vehicle_id: uuid.UUID
    owner_id: uuid.UUID
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime


class VehicleManagementAgreementCreate(BaseModel):
    vehicle_id: uuid.UUID
    owner_id: uuid.UUID
    start_date: datetime
    end_date: Optional[datetime] = None
    status: AgreementStatus = AgreementStatus.ACTIVE

    @model_validator(mode="after")
    def check_dates(self) -> "VehicleManagementAgreementCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("Data de fim n?o pode ser anterior ao in?cio.")
        return self


class VehicleManagementAgreementStatusUpdate(BaseModel):
    status: AgreementStatus
    end_date: Optional[datetime] = None
    reason: Optional[str] = Field(default=None, max_length=500)


class VehicleManagementAgreementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    vehicle_id: uuid.UUID
    organization_id: uuid.UUID
    owner_id: uuid.UUID
    status: AgreementStatus
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
