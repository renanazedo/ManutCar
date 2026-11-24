"""
Schemas Pydantic v2 para validação de Payloads de Webhook (Clerk).
"""
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClerkEmailAddress(BaseModel):
    id: str
    email_address: EmailStr
    verification: Optional[dict] = None


class ClerkPhoneNumber(BaseModel):
    id: str
    phone_number: str
    verification: Optional[dict] = None


class ClerkUserData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    external_id: Optional[str] = None
    username: Optional[str] = None
    email_addresses: List[ClerkEmailAddress] = []
    phone_numbers: List[ClerkPhoneNumber] = []
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    unsafe_metadata: dict = Field(default_factory=dict)
    public_metadata: dict = Field(default_factory=dict)
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class ClerkOrganizationData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    slug: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class ClerkPublicUserData(BaseModel):
    user_id: str
    identifier: str


class ClerkOrganizationMembershipData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    role: str  # 'admin' | 'member'
    organization: ClerkOrganizationData
    public_user_data: ClerkPublicUserData
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class ClerkWebhookPayload(BaseModel):
    """Wrapper genérico para o payload bruto se necessário."""
    type: str
    data: dict
    object: str = "event"
