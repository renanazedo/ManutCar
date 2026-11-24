import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from manutcar_db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from manutcar_db.enums import (
    AuditAction,
    ExpenseNature,
    LedgerEntryType,
    SettlementStatus,
)


class PlatformImportBatch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "platform_import_batches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="ID do usuário que realizou a importação",
    )
    platform_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nome da plataforma de origem (ex: Uber, 99, iFood)",
    )
    file_hash_sha256: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="Hash SHA-256 do arquivo importado para idempotência",
    )
    records_imported: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Quantidade de registros importados com sucesso",
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora da importação (UTC)",
    )

    def __repr__(self) -> str:
        return f"<PlatformImportBatch(id={self.id}, platform={self.platform_name}, records={self.records_imported})>"


class RevenueEntry(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "revenue_entries"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Veículo que gerou a receita",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Organização proprietária da receita",
    )
    driver_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Motorista que realizou a corrida/entrega",
    )
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_import_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Lote de importação de origem (se aplicável)",
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Fonte da receita (ex: uber, 99, ifood, manual)",
    )
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor bruto da receita",
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor líquido da receita (após taxas da plataforma)",
    )
    professional_km: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Quilometragem profissional associada à receita",
    )
    reference_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data de competência da receita (UTC)",
    )

    def __repr__(self) -> str:
        return f"<RevenueEntry(id={self.id}, vehicle_id={self.vehicle_id}, net_amount={self.net_amount}, ref_date={self.reference_date})>"


class FinancialLedgerEntry(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "financial_ledger_entries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Organização à qual o lançamento pertence",
    )
    vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Veículo relacionado (se aplicável)",
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        nullable=False,
        comment="Tipo de lançamento: REVENUE, EXPENSE, SETTLEMENT_TRANSFER",
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Categoria do lançamento (ex: fuel, maintenance, platform_fee, rental_income)",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor do lançamento (positivo para receita/entrada, negativo para despesa/saída conforme entry_type)",
    )
    expense_nature: Mapped[ExpenseNature] = mapped_column(
        nullable=False,
        default=ExpenseNature.PROFESSIONAL,
        comment="Natureza da despesa: PROFESSIONAL, PERSONAL, SHARED",
    )
    payer_entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo da entidade pagadora (ex: organization, driver, platform, supplier)",
    )
    payer_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="ID da entidade pagadora",
    )
    economic_owner_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo do dono econômico (ex: organization, driver)",
    )
    economic_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="ID do dono econômico (quem arca com o custo ou recebe a receita)",
    )
    settlement_status: Mapped[SettlementStatus] = mapped_column(
        nullable=False,
        default=SettlementStatus.NOT_APPLICABLE,
        comment="Status de liquidação: NOT_APPLICABLE, PENDING_REIMBURSEMENT, SETTLED",
    )
    competence_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data de competência do lançamento (UTC)",
    )
    source_module: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Módulo de origem do lançamento (ex: fuel_log, maintenance, revenue_import)",
    )
    source_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID do registro de origem no módulo fonte",
    )

    __table_args__ = (
        Index(
            "ix_financial_ledger_entries_org_competence",
            "organization_id",
            "competence_date",
        ),
        Index(
            "ix_financial_ledger_entries_source",
            "source_module",
            "source_record_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<FinancialLedgerEntry(id={self.id}, org_id={self.organization_id}, type={self.entry_type}, amount={self.amount})>"


class SettlementStatement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "settlement_statements"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Organização que emitiu o extrato",
    )
    counterparty_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo da contraparte (ex: driver, organization, supplier)",
    )
    counterparty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID da contraparte",
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Início do período de competência (UTC)",
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Fim do período de competência (UTC)",
    )
    net_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Saldo líquido a pagar/receber (positivo = a receber pela org, negativo = a pagar)",
    )
    status: Mapped[SettlementStatus] = mapped_column(
        nullable=False,
        default=SettlementStatus.PENDING_REIMBURSEMENT,
        comment="Status do extrato: PENDING_REIMBURSEMENT, SETTLED",
    )

    __table_args__ = (
        Index(
            "ix_settlement_statements_org_counterparty_period",
            "organization_id",
            "counterparty_type",
            "counterparty_id",
            "period_start",
            "period_end",
        ),
    )

    def __repr__(self) -> str:
        return f"<SettlementStatement(id={self.id}, org_id={self.organization_id}, counterparty={self.counterparty_type}:{self.counterparty_id}, balance={self.net_balance})>"


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Organização relacionada (pode ser nulo para ações globais)",
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuário que realizou a ação (pode ser nulo para ações de sistema)",
    )
    entity_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Nome da entidade afetada (ex: Vehicle, RevenueEntry, OrganizationMember)",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID da entidade afetada",
    )
    action: Mapped[AuditAction] = mapped_column(
        nullable=False,
        comment="Ação realizada: CREATE, UPDATE, DELETE, APPROVE, REVOKE, ANONYMIZE",
    )
    old_values: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Valores anteriores (para UPDATE/DELETE)",
    )
    new_values: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Novos valores (para CREATE/UPDATE)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Data/hora da ação (UTC)",
    )

    __table_args__ = (
        Index(
            "ix_audit_logs_entity",
            "entity_name",
            "entity_id",
        ),
        Index(
            "ix_audit_logs_org_created",
            "organization_id",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, entity={self.entity_name}:{self.entity_id}, action={self.action}, at={self.created_at})>"


class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"

    event_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="ID único do evento do provedor (ex: evt_... do Stripe, msg_... do Clerk)",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Provedor do webhook (ex: clerk, stripe, mercadopago)",
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Data/hora do processamento (UTC)",
    )

    def __repr__(self) -> str:
        return f"<ProcessedWebhookEvent(event_id={self.event_id}, provider={self.provider}, processed_at={self.processed_at})>"
