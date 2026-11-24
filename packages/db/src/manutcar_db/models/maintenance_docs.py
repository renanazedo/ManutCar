import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manutcar_db.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from manutcar_db.enums import MaintenanceType, WorkOrderStatus


class ServiceProvider(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_providers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização proprietária",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome do prestador de serviço",
    )
    document_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="CNPJ/CPF do prestador",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Telefone de contato",
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="service_providers",
        lazy="raise",
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(
        "WorkOrder",
        back_populates="service_provider",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<ServiceProvider(id={self.id}, name={self.name!r})>"


class MaintenancePlan(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "maintenance_plans"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização proprietária",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome do plano de manutenção",
    )
    interval_km: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Intervalo em quilômetros",
    )
    interval_days: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Intervalo em dias",
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="maintenance_plans",
        lazy="raise",
    )
    vehicle_schedules: Mapped[list["VehicleMaintenanceSchedule"]] = relationship(
        "VehicleMaintenanceSchedule",
        back_populates="plan",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<MaintenancePlan(id={self.id}, name={self.name!r})>"


class VehicleMaintenanceSchedule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_maintenance_schedules"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("maintenance_plans.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do plano de manutenção",
    )
    last_executed_km: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Quilometragem da última execução",
    )
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da última execução",
    )
    next_due_km: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Próxima quilometragem prevista",
    )
    next_due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Próxima data prevista",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="maintenance_schedules",
        lazy="raise",
    )
    plan: Mapped["MaintenancePlan"] = relationship(
        "MaintenancePlan",
        back_populates="vehicle_schedules",
        lazy="raise",
    )

    __table_args__ = (
        UniqueConstraint("vehicle_id", "plan_id", name="uq_vehicle_maintenance_schedule_vehicle_plan"),
    )

    def __repr__(self) -> str:
        return f"<VehicleMaintenanceSchedule(vehicle_id={self.vehicle_id}, plan_id={self.plan_id})>"


class MaintenanceRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_requests"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do usuário que solicitou",
    )
    source_checklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("checklist_executions.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID da execução de checklist que originou a solicitação",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Descrição da solicitação",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NORMAL",
        comment="Prioridade: LOW, NORMAL, HIGH, URGENT",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OPEN",
        comment="Status: OPEN, IN_PROGRESS, COMPLETED, CANCELLED",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="maintenance_requests",
        lazy="raise",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="maintenance_requests",
        lazy="raise",
    )
    requested_by: Mapped["User"] = relationship(
        "User",
        back_populates="maintenance_requests",
        lazy="raise",
    )
    source_checklist: Mapped[Optional["ChecklistExecution"]] = relationship(
        "ChecklistExecution",
        back_populates="maintenance_requests",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<MaintenanceRequest(id={self.id}, vehicle_id={self.vehicle_id}, status={self.status!r})>"


class WorkOrder(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "work_orders"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    service_provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("service_providers.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID do prestador de serviço",
    )
    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        nullable=False,
        comment="Tipo de manutenção",
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        nullable=False,
        default=WorkOrderStatus.OPEN,
        comment="Status da ordem de serviço",
    )
    odometer_km: Mapped[int] = mapped_column(
        nullable=False,
        comment="Quilometragem no momento da abertura",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Valor total da ordem",
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora de abertura",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora de conclusão",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="work_orders",
        lazy="raise",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="work_orders",
        lazy="raise",
    )
    service_provider: Mapped[Optional["ServiceProvider"]] = relationship(
        "ServiceProvider",
        back_populates="work_orders",
        lazy="raise",
    )
    items: Mapped[list["WorkOrderItem"]] = relationship(
        "WorkOrderItem",
        back_populates="work_order",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WorkOrder(id={self.id}, vehicle_id={self.vehicle_id}, status={self.status.value})>"


class WorkOrderItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "work_order_items"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da ordem de serviço",
    )
    item_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo do item: PART, LABOR, SERVICE, OTHER",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Descrição do item",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Quantidade",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Preço unitário",
    )
    warranty_days: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Garantia em dias",
    )
    warranty_km: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Garantia em quilômetros",
    )

    work_order: Mapped["WorkOrder"] = relationship(
        "WorkOrder",
        back_populates="items",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<WorkOrderItem(id={self.id}, work_order_id={self.work_order_id}, item_type={self.item_type!r})>"


class DriverLicense(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "driver_licenses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="ID do usuário (motorista)",
    )
    license_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número da CNH",
    )
    category: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Categoria da CNH (A, B, C, D, E, AB, etc.)",
    )
    expiration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de validade da CNH",
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="driver_license",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<DriverLicense(user_id={self.user_id}, license_number={self.license_number!r})>"


class VehicleObligation(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vehicle_obligations"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    obligation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo de obrigação: IPVA, LICENSING, INSPECTION, INSURANCE, OTHER",
    )
    reference_year: Mapped[int] = mapped_column(
        nullable=False,
        comment="Ano de referência",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor total da obrigação",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="obligations",
        lazy="raise",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="vehicle_obligations",
        lazy="raise",
    )
    installments: Mapped[list["ObligationInstallment"]] = relationship(
        "ObligationInstallment",
        back_populates="obligation",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("vehicle_id", "obligation_type", "reference_year", name="uq_vehicle_obligation_vehicle_type_year"),
    )

    def __repr__(self) -> str:
        return f"<VehicleObligation(id={self.id}, vehicle_id={self.vehicle_id}, type={self.obligation_type!r}, year={self.reference_year})>"


class ObligationInstallment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "obligation_installments"

    obligation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicle_obligations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da obrigação",
    )
    installment_number: Mapped[int] = mapped_column(
        nullable=False,
        comment="Número da parcela",
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de vencimento",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor da parcela",
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do pagamento",
    )

    obligation: Mapped["VehicleObligation"] = relationship(
        "VehicleObligation",
        back_populates="installments",
        lazy="raise",
    )

    __table_args__ = (
        UniqueConstraint("obligation_id", "installment_number", name="uq_obligation_installment_obligation_number"),
    )

    def __repr__(self) -> str:
        return f"<ObligationInstallment(id={self.id}, obligation_id={self.obligation_id}, number={self.installment_number})>"


class TrafficTicket(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "traffic_tickets"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    suggested_driver_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID do condutor sugerido para indicação",
    )
    infraction_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Código da infração",
    )
    infraction_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora da infração",
    )
    indication_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Prazo para indicação do condutor",
    )
    points: Mapped[int] = mapped_column(
        nullable=False,
        comment="Pontos na CNH",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor da multa",
    )
    indication_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="Status da indicação: PENDING, INDICATED, PAID, CONTESTED, EXPIRED",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="traffic_tickets",
        lazy="raise",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="traffic_tickets",
        lazy="raise",
    )
    suggested_driver: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="suggested_traffic_tickets",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<TrafficTicket(id={self.id}, vehicle_id={self.vehicle_id}, code={self.infraction_code!r})>"
