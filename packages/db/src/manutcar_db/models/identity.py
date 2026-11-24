import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from manutcar_db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from manutcar_db.enums import AgreementStatus, ConsentStatus, OrgRole

if TYPE_CHECKING:
    from manutcar_db.models.fleet import (
        Vehicle,
        VehicleAssignment,
        VehicleFinancialResponsibility,
        VehicleManagementAgreement,
        VehicleOwner,
    )


class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="ID do usuário no Clerk",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="E-mail principal do usuário",
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome completo do usuário",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Telefone do usuário",
    )
    is_anonymized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica se o usuário foi anonimizado (LGPD)",
    )

    # Relacionamentos
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    data_consents: Mapped[list["DataConsent"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    vehicle_assignments: Mapped[list["VehicleAssignment"]] = relationship(
        back_populates="driver_user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, clerk_user_id={self.clerk_user_id}, email={self.email})>"


class Organization(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome da organização",
    )
    document_number: Mapped[Optional[str]] = mapped_column(
        String(18),
        nullable=True,
        index=True,
        comment="CPF ou CNPJ da organização",
    )
    is_personal_workspace: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica se é workspace pessoal do motorista autônomo",
    )

    # Relacionamentos
    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization",
        lazy="selectin",
    )
    settings: Mapped[Optional["OrganizationSettings"]] = relationship(
        back_populates="organization",
        uselist=False,
        lazy="selectin",
    )
    invitations: Mapped[list["OrganizationInvitation"]] = relationship(
        back_populates="organization",
        lazy="selectin",
    )
    data_consents_granted: Mapped[list["DataConsent"]] = relationship(
        back_populates="grantee_organization",
        lazy="selectin",
    )
    vehicle_owners: Mapped[list["VehicleOwner"]] = relationship(
        back_populates="organization",
        lazy="selectin",
    )
    management_agreements: Mapped[list["VehicleManagementAgreement"]] = relationship(
        back_populates="organization",
        lazy="selectin",
    )
    vehicle_assignments: Mapped[list["VehicleAssignment"]] = relationship(
        back_populates="organization",
        lazy="selectin",
    )
    financial_responsibilities: Mapped[list["VehicleFinancialResponsibility"]] = relationship(
        back_populates="organization",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class OrganizationMember(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organization_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do usuário",
    )
    role: Mapped[OrgRole] = mapped_column(
        nullable=False,
        default=OrgRole.DRIVER,
        comment="Papel do membro na organização",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica se o membro está ativo na organização",
    )

    # Relacionamentos
    organization: Mapped["Organization"] = relationship(
        back_populates="members",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        back_populates="memberships",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_members_org_user",
        ),
        Index("ix_organization_members_org_id", "organization_id"),
        Index("ix_organization_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember(org_id={self.organization_id}, user_id={self.user_id}, role={self.role})>"


class OrganizationSettings(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organization_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="ID da organização",
    )
    max_daily_odometer_delta_km: Mapped[int] = mapped_column(
        default=1500,
        nullable=False,
        comment="Delta máximo de quilometragem diária permitida",
    )
    fuel_anomaly_threshold_pct: Mapped[float] = mapped_column(
        NUMERIC(5, 2),
        default=15.00,
        nullable=False,
        comment="Limite percentual para anomalia de combustível",
    )
    preventive_alert_days: Mapped[int] = mapped_column(
        default=15,
        nullable=False,
        comment="Dias de antecedência para alerta de manutenção preventiva",
    )
    preventive_alert_km_pct: Mapped[float] = mapped_column(
        NUMERIC(5, 2),
        default=10.00,
        nullable=False,
        comment="Percentual de KM para alerta de manutenção preventiva",
    )
    require_handover_checklist: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Exige checklist de entrega/recebimento do veículo",
    )

    # Relacionamentos
    organization: Mapped["Organization"] = relationship(
        back_populates="settings",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<OrganizationSettings(org_id={self.organization_id})>"


class OrganizationInvitation(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organization_invitations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização",
    )
    invited_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="E-mail do convidado",
    )
    target_role: Mapped[Optional[OrgRole]] = mapped_column(
        nullable=True,
        comment="Papel alvo do convidado na organização",
    )
    vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID do veículo associado ao convite (opcional)",
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Hash do token de convite",
    )
    status: Mapped[AgreementStatus] = mapped_column(
        nullable=False,
        default=AgreementStatus.PENDING,
        comment="Status do convite",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora de expiração do convite",
    )

    # Relacionamentos
    organization: Mapped["Organization"] = relationship(
        back_populates="invitations",
        lazy="selectin",
    )
    vehicle: Mapped[Optional["Vehicle"]] = relationship(
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<OrganizationInvitation(id={self.id}, email={self.invited_email}, status={self.status})>"


class DataConsent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_consents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do usuário que concedeu o consentimento",
    )
    grantee_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID da organização beneficiária do consentimento",
    )
    scope: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Escopo do consentimento (dados permitidos, finalidades, etc.)",
    )
    status: Mapped[ConsentStatus] = mapped_column(
        nullable=False,
        default=ConsentStatus.GRANTED,
        comment="Status do consentimento",
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Data/hora da concessão do consentimento",
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da revogação do consentimento",
    )

    # Relacionamentos
    user: Mapped["User"] = relationship(
        back_populates="data_consents",
        lazy="selectin",
    )
    grantee_organization: Mapped["Organization"] = relationship(
        back_populates="data_consents_granted",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_data_consents_user_id", "user_id"),
        Index("ix_data_consents_grantee_org_id", "grantee_organization_id"),
        Index("ix_data_consents_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<DataConsent(user_id={self.user_id}, org_id={self.grantee_organization_id}, status={self.status})>"
