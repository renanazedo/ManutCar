import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manutcar_db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from manutcar_db.enums import (
    AgreementStatus,
    FuelType,
    VehicleOperationalStatus,
)

if TYPE_CHECKING:
    from manutcar_db.models.identity import (
        Organization,
        OrganizationInvitation,
        User,
    )


class VehicleOwner(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vehicle_owners"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID da organização proprietária (se PJ)",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID do usuário proprietário (se PF)",
    )
    owner_type: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="Tipo de proprietário: PF ou PJ",
    )
    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome legal do proprietário (nome completo ou razão social)",
    )
    document_number: Mapped[str] = mapped_column(
        String(18),
        nullable=False,
    #    index=True,
        comment="CPF ou CNPJ do proprietário",
    )

    # Relacionamentos
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="vehicle_owners",
        lazy="selectin",
    )
    user: Mapped[Optional["User"]] = relationship(
        lazy="selectin",
    )
    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="current_owner",
        lazy="selectin",
    )
    ownership_history: Mapped[list["VehicleOwnershipHistory"]] = relationship(
        back_populates="owner",
        lazy="selectin",
    )
    management_agreements: Mapped[list["VehicleManagementAgreement"]] = relationship(
        back_populates="owner",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vehicle_owners_org_id", "organization_id"),
        Index("ix_vehicle_owners_user_id", "user_id"),
        Index("ix_vehicle_owners_document", "document_number"),
    )

    def __repr__(self) -> str:
        return f"<VehicleOwner(id={self.id}, type={self.owner_type}, document={self.document_number})>"


class Vehicle(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vehicles"

    plate: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
     #   index=True,
        comment="Placa do veículo (formato Mercosul ou antigo)",
    )
    renavam: Mapped[Optional[str]] = mapped_column(
        String(11),
        unique=True,
        nullable=True,
    #    index=True,
        comment="RENAVAM do veículo",
    )
    chassis: Mapped[Optional[str]] = mapped_column(
        String(17),
        unique=True,
        nullable=True,
    #    index=True,
        comment="Chassi do veículo",
    )
    brand: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Marca do veículo",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Modelo do veículo",
    )
    year_manufacture: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ano de fabricação",
    )
    year_model: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ano do modelo",
    )
    fuel_type: Mapped[FuelType] = mapped_column(
        nullable=False,
        comment="Tipo de combustível do veículo",
    )
    current_odometer: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quilometragem atual do veículo",
    )
    operational_status: Mapped[VehicleOperationalStatus] = mapped_column(
        nullable=False,
        default=VehicleOperationalStatus.ACTIVE,
        comment="Status operacional do veículo",
    )
    current_owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_owners.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID do proprietário atual do veículo",
    )

    # Relacionamentos
    current_owner: Mapped[Optional["VehicleOwner"]] = relationship(
        back_populates="vehicles",
        lazy="selectin",
    )
    ownership_history: Mapped[list["VehicleOwnershipHistory"]] = relationship(
        back_populates="vehicle",
        lazy="selectin",
    )
    management_agreements: Mapped[list["VehicleManagementAgreement"]] = relationship(
        back_populates="vehicle",
        lazy="selectin",
    )
    assignments: Mapped[list["VehicleAssignment"]] = relationship(
        back_populates="vehicle",
        lazy="selectin",
    )
    financial_responsibilities: Mapped[list["VehicleFinancialResponsibility"]] = relationship(
        back_populates="vehicle",
        lazy="selectin",
    )
    invitations: Mapped[list["OrganizationInvitation"]] = relationship(
        back_populates="vehicle",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vehicles_plate", "plate"),
        Index("ix_vehicles_renavam", "renavam"),
        Index("ix_vehicles_chassis", "chassis"),
        Index("ix_vehicles_owner_id", "current_owner_id"),
        Index("ix_vehicles_status", "operational_status"),
    )

    def __repr__(self) -> str:
        return f"<Vehicle(id={self.id}, plate={self.plate}, brand={self.brand}, model={self.model})>"


class VehicleOwnershipHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_ownership_history"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_owners.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do proprietário",
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de início da posse",
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de fim da posse (null = posse atual)",
    )

    # Relacionamentos
    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="ownership_history",
        lazy="selectin",
    )
    owner: Mapped["VehicleOwner"] = relationship(
        back_populates="ownership_history",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vehicle_ownership_history_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_ownership_history_owner_id", "owner_id"),
        Index("ix_vehicle_ownership_history_dates", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<VehicleOwnershipHistory(vehicle_id={self.vehicle_id}, owner_id={self.owner_id}, start={self.start_date})>"


class VehicleManagementAgreement(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vehicle_management_agreements"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização gestora",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_owners.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do proprietário do veículo",
    )
    status: Mapped[AgreementStatus] = mapped_column(
        nullable=False,
        default=AgreementStatus.PENDING,
        comment="Status do acordo de gestão",
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de início do acordo",
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de fim do acordo (null = vigente)",
    )
    consented_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID do usuário que consentiu com o acordo",
    )
    consented_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do consentimento do proprietário",
    )
    consent_revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da revogação do consentimento",
    )

    # Relacionamentos
    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="management_agreements",
        lazy="selectin",
    )
    organization: Mapped["Organization"] = relationship(
        back_populates="management_agreements",
        lazy="selectin",
    )
    owner: Mapped["VehicleOwner"] = relationship(
        back_populates="management_agreements",
        lazy="selectin",
    )
    access_permissions: Mapped[Optional["VehicleAccessPermission"]] = relationship(
        back_populates="agreement",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vehicle_mgmt_agreements_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_mgmt_agreements_org_id", "organization_id"),
        Index("ix_vehicle_mgmt_agreements_owner_id", "owner_id"),
        Index("ix_vehicle_mgmt_agreements_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<VehicleManagementAgreement(vehicle_id={self.vehicle_id}, org_id={self.organization_id}, status={self.status})>"


class VehicleAccessPermission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_access_permissions"

    agreement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_management_agreements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="ID do acordo de gestão",
    )
    can_view_maintenance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pode visualizar manutenções",
    )
    can_edit_maintenance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pode editar manutenções",
    )
    can_view_financial: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pode visualizar financeiro",
    )
    can_edit_financial: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pode editar financeiro",
    )
    can_view_telemetry: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pode visualizar telemetria",
    )
    can_manage_drivers: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pode gerenciar motoristas",
    )

    # Relacionamentos
    agreement: Mapped["VehicleManagementAgreement"] = relationship(
        back_populates="access_permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<VehicleAccessPermission(agreement_id={self.agreement_id})>"


class VehicleAssignment(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vehicle_assignments"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    driver_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do usuário motorista",
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data/hora de início da designação",
    )
    end_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Data/hora de fim da designação (null = vigente)",
    )
    shift_label: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Rótulo do turno (ex: 'Manhã', 'Noturno', 'Plantão')",
    )

    # Relacionamentos
    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="assignments",
        lazy="selectin",
    )
    organization: Mapped["Organization"] = relationship(
        back_populates="vehicle_assignments",
        lazy="selectin",
    )
    driver_user: Mapped["User"] = relationship(
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vehicle_assignments_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_assignments_org_id", "organization_id"),
        Index("ix_vehicle_assignments_driver_id", "driver_user_id"),
        Index("ix_vehicle_assignments_dates", "start_datetime", "end_datetime"),
    )

    def __repr__(self) -> str:
        return f"<VehicleAssignment(vehicle_id={self.vehicle_id}, driver_id={self.driver_user_id}, start={self.start_datetime})>"


class VehicleFinancialResponsibility(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_financial_responsibilities"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    expense_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Categoria da despesa (ex: 'combustivel', 'manutencao', 'seguro', 'ipva')",
    )
    default_payer_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Pagador padrão: ORG, OWNER ou DRIVER",
    )
    default_economic_owner_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Dono econômico padrão: ORG, OWNER ou DRIVER",
    )

    # Relacionamentos
    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="financial_responsibilities",
        lazy="selectin",
    )
    organization: Mapped["Organization"] = relationship(
        back_populates="financial_responsibilities",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "vehicle_id",
            "organization_id",
            "expense_category",
            name="uq_vehicle_fin_resp_vehicle_org_category",
        ),
        Index("ix_vehicle_fin_resp_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_fin_resp_org_id", "organization_id"),
    )

    def __repr__(self) -> str:
        return f"<VehicleFinancialResponsibility(vehicle_id={self.vehicle_id}, category={self.expense_category}, payer={self.default_payer_type})>"
