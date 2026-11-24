import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manutcar_db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from manutcar_db.enums import (
    ChecklistItemStatus,
    ChecklistType,
    ExpenseNature,
    FuelType,
)

if TYPE_CHECKING:
    from manutcar_db.models.fleet import Vehicle
    from manutcar_db.models.identity import Organization, User


class OdometerReading(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "odometer_readings"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do veículo",
    )
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="ID do usuário que registrou a leitura",
    )
    source_module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Módulo de origem do registro (ex: fuel_log, checklist, manual)",
    )
    source_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="ID do registro de origem no módulo fonte",
    )
    odometer_km: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
        comment="Quilometragem registrada (km)",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data/hora do registro (UTC)",
    )
    is_anomaly_flagged: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Flag indicando se a leitura foi marcada como anomalia",
    )

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(back_populates="odometer_readings")
    recorded_by: Mapped["User"] = relationship(back_populates="odometer_readings")

    def __repr__(self) -> str:
        return f"<OdometerReading(vehicle_id={self.vehicle_id}, odometer_km={self.odometer_km}, recorded_at={self.recorded_at})>"


class FuelLog(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "fuel_logs"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID da organização",
    )
    driver_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="ID do motorista que abasteceu",
    )
    odometer_km: Mapped[int] = mapped_column(
        nullable=False,
        comment="Quilometragem no momento do abastecimento",
    )
    fuel_type: Mapped[FuelType] = mapped_column(
        nullable=False,
        comment="Tipo de combustível",
    )
    liters: Mapped[Decimal] = mapped_column(
        nullable=False,
        comment="Litros abastecidos",
    )
    price_per_liter: Mapped[Decimal] = mapped_column(
        nullable=False,
        comment="Preço por litro",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        nullable=False,
        comment="Valor total do abastecimento",
    )
    is_full_tank: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Indica se foi abastecimento completo (tanque cheio)",
    )
    expense_nature: Mapped[ExpenseNature] = mapped_column(
        default=ExpenseNature.PROFESSIONAL,
        nullable=False,
        comment="Natureza da despesa",
    )
    receipt_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL do comprovante/nota fiscal",
    )
    fueled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data/hora do abastecimento (UTC)",
    )

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(back_populates="fuel_logs")
    organization: Mapped["Organization"] = relationship(back_populates="fuel_logs")
    driver: Mapped["User"] = relationship(back_populates="fuel_logs")
    anomalies: Mapped[list["ConsumptionAnomalyAlert"]] = relationship(
        back_populates="fuel_log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FuelLog(vehicle_id={self.vehicle_id}, liters={self.liters}, total_amount={self.total_amount}, fueled_at={self.fueled_at})>"


class ConsumptionAnomalyAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "consumption_anomaly_alerts"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do veículo",
    )
    fuel_log_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("fuel_logs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="ID do abastecimento que gerou o alerta",
    )
    expected_km_per_liter: Mapped[Decimal] = mapped_column(
        nullable=False,
        comment="Consumo esperado (km/l)",
    )
    actual_km_per_liter: Mapped[Decimal] = mapped_column(
        nullable=False,
        comment="Consumo real calculado (km/l)",
    )
    deviation_pct: Mapped[Decimal] = mapped_column(
        nullable=False,
        comment="Desvio percentual em relação ao esperado",
    )
    is_resolved: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Indica se o alerta foi resolvido/tratado",
    )

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(back_populates="consumption_anomalies")
    fuel_log: Mapped["FuelLog"] = relationship(back_populates="anomalies")

    def __repr__(self) -> str:
        return f"<ConsumptionAnomalyAlert(vehicle_id={self.vehicle_id}, fuel_log_id={self.fuel_log_id}, deviation_pct={self.deviation_pct})>"


class ChecklistTemplate(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "checklist_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID da organização",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nome do template",
    )
    checklist_type: Mapped[ChecklistType] = mapped_column(
        nullable=False,
        comment="Tipo de checklist",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Indica se o template está ativo",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="checklist_templates")
    items: Mapped[list["ChecklistTemplateItem"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="ChecklistTemplateItem.order_index"
    )
    executions: Mapped[list["ChecklistExecution"]] = relationship(back_populates="template")

    def __repr__(self) -> str:
        return f"<ChecklistTemplate(organization_id={self.organization_id}, name={self.name}, type={self.checklist_type})>"


class ChecklistTemplateItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "checklist_template_items"

    template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("checklist_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do template",
    )
    label: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Rótulo/descrição do item",
    )
    order_index: Mapped[int] = mapped_column(
        nullable=False,
        comment="Ordem de exibição do item",
    )
    is_safety_critical: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Indica se o item é crítico para segurança",
    )
    require_photo_on_fail: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Exige foto quando o item falhar",
    )

    # Relationships
    template: Mapped["ChecklistTemplate"] = relationship(back_populates="items")
    responses: Mapped[list["ChecklistResponseItem"]] = relationship(back_populates="template_item")

    __table_args__ = (
        Index("ix_checklist_template_items_template_order", "template_id", "order_index"),
    )

    def __repr__(self) -> str:
        return f"<ChecklistTemplateItem(template_id={self.template_id}, label={self.label}, order={self.order_index})>"


class ChecklistExecution(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "checklist_executions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("checklist_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do template utilizado",
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do veículo",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID da organização",
    )
    driver_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="ID do motorista que executou",
    )
    odometer_km: Mapped[int] = mapped_column(
        nullable=False,
        comment="Quilometragem no momento da execução",
    )
    has_critical_failure: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Indica se houve falha em item crítico de segurança",
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data/hora da execução (UTC)",
    )

    # Relationships
    template: Mapped["ChecklistTemplate"] = relationship(back_populates="executions")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="checklist_executions")
    organization: Mapped["Organization"] = relationship(back_populates="checklist_executions")
    driver: Mapped["User"] = relationship(back_populates="checklist_executions")
    responses: Mapped[list["ChecklistResponseItem"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChecklistExecution(template_id={self.template_id}, vehicle_id={self.vehicle_id}, executed_at={self.executed_at})>"


class ChecklistResponseItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "checklist_response_items"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("checklist_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID da execução",
    )
    template_item_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("checklist_template_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do item do template",
    )
    status: Mapped[ChecklistItemStatus] = mapped_column(
        nullable=False,
        comment="Status do item na execução",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Observações sobre o item",
    )
    photo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL da foto (se aplicável)",
    )

    # Relationships
    execution: Mapped["ChecklistExecution"] = relationship(back_populates="responses")
    template_item: Mapped["ChecklistTemplateItem"] = relationship(back_populates="responses")

    __table_args__ = (
        Index("uq_checklist_response_execution_item", "execution_id", "template_item_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ChecklistResponseItem(execution_id={self.execution_id}, template_item_id={self.template_item_id}, status={self.status})>"
